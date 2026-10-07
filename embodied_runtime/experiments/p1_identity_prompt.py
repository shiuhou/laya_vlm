"""Bounded development POINT+original-BOX prompting, not acceptance or control."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from ..contracts import content_hash, require
from ..perception.segmented_patch import estimate_segmented_patch
from ..perception.semantic_output import parse_semantic_reply
from ..perception.semantic_prompt import point_prompt, mask_point_admission
from ..perception.surface_association import sensor_view_identity
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import SAM_SETTINGS, read, write, seal, verify_seal
from .p1_semantic_grounding import MODEL_CONTENT_ID, _load_worker, _explicit_gpu_mask, _cuda_allocation
from .point_grounding_probe import SETTINGS, generation_audit
from .records import code_identity, file_hash, versions
from . import p1_formal50 as baseline
from .p1_formal50 import frames, ledger, review

CONDITION = "p1-point-positive-sam-repair/1"
BASELINE = Path("runs/p1/formal50-native-masks-20261007")
PROTOCOL = Path("docs/research/p1_identity_prompt_protocol.md")


def registration(root):
    r = baseline.registration(root)
    require(r['condition'] == CONDITION and r['generation_settings'] == SETTINGS
            and r['sam_settings'] == SAM_SETTINGS and r['model_content_id'] == MODEL_CONTENT_ID
            and r['development_only'] and not r['independent_heldout'], 'repair condition differs')
    return r


def prepare(output):
    b = baseline.registration(BASELINE)
    for stage in ('masks', 'geometry', 'scoring'):
        verify_seal(BASELINE/stage)
    code = code_identity()
    require(code['dirty_status'] == '', 'freeze runner before generation')
    r = dict(b)
    r.pop('registration_content_sha256')
    r.update(condition=CONDITION, baseline_root=str(BASELINE.absolute()),
        baseline_registration_sha256=file_hash(BASELINE/'registration.json'),
        baseline_scoring_seal_sha256=file_hash(BASELINE/'scoring/sealed.json'),
        registered_at_utc=datetime.now(timezone.utc).isoformat(), code=code,
        baseline='34486e3', generation_settings=SETTINGS, model_content_id=MODEL_CONTENT_ID,
        sam_settings=SAM_SETTINGS, LocateAnything_calls=50, planned_native_mask_slots=150,
        point_prompt='Point to: {frozen_drawer_query}.',
        model_inputs=['original_full_RGB','original_sealed_BOX','same_frame_semantic_positive_POINT'],
        scoring_contract='p1-identity-repair-scoring/1',
        annotation_read_stage='new score only after points+masks+geometry seals',
        development_only=True, independent_heldout=False, P1_acceptance=False,
        exposure='Formal-50 labels and outputs inspected previously; matched reused-development diagnostic',
        point_mask_admission='separate from raw prompting/geometry results; no geometry skipping',
        batch_timeout_s=1800, frame_retry_count=0)
    paths = [Path(p) for p in code['source_sha256']] + [PROTOCOL, BASELINE/'registration.json',
        BASELINE/'masks/sealed.json',BASELINE/'geometry/sealed.json',BASELINE/'scoring/sealed.json']
    r['source_files_sha256'] = dict(b['source_files_sha256'])
    r['source_files_sha256'].update({str(p.absolute()):file_hash(p) for p in paths})
    r['registration_content_sha256'] = content_hash(r)
    root=Path(output)
    root.mkdir(parents=True,exist_ok=False)
    write(root/'registration.json',r)
    registration(root)


def infer_point(worker, rgb, query, emit):
    """Only RGB and frozen text reach the original native POINT generator."""
    from PIL import Image
    question = f"Point to: {query}."
    messages=[{'role':'user','content':[{'type':'image','image':Image.fromarray(rgb).convert('RGB')},
                                      {'type':'text','text':question}]}]
    text=worker.processor.py_apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    images,videos=worker.processor.process_vision_info(messages)
    inputs=worker.processor(text=[text],images=images,videos=videos,return_tensors='pt',truncation=False).to(worker.device)
    ids=inputs['input_ids'].detach().cpu().tolist()[0]
    pixels=inputs['pixel_values'].to(worker.dtype)
    grid=inputs.get('image_grid_hws')
    grid=grid.detach().cpu().tolist() if hasattr(grid,'detach') else np.asarray(grid).tolist()
    emit('model-input',dict(query=query,question=question,formatted_text=text,input_token_ids=ids,
        attention_mask=inputs['attention_mask'].detach().cpu().tolist(),image_grid_hws=grid,
        pixel_shape=list(pixels.shape),pixel_dtype=str(pixels.dtype),
        pixel_sha256=hashlib.sha256(pixels.contiguous().view(worker.torch.uint8).cpu().numpy().tobytes()).hexdigest(),
        rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),generator_inputs=['RGB','fixed_query'],
        input_token_count=len(ids),model_max_length=worker.tokenizer.model_max_length,
        reserved_generation_tokens=SETTINGS['max_new_tokens'],processor_truncation=False))
    require(0<len(ids) and len(ids)+SETTINGS['max_new_tokens']<=worker.tokenizer.model_max_length,
            'input leaves insufficient generation budget','INPUT_OR_OUTPUT_TRUNCATED')
    observed=[]
    original=worker.tokenizer.batch_decode
    def decode(sequences,*args,**kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original(sequences,*args,**kwargs)
    worker.tokenizer.batch_decode=decode
    worker.torch.cuda.synchronize()
    start=time.perf_counter()
    try:
        with worker.torch.no_grad():
            raw=worker.model.generate(pixel_values=pixels,input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],image_grid_hws=inputs.get('image_grid_hws'),
                tokenizer=worker.tokenizer,**SETTINGS)
        worker.torch.cuda.synchronize()
    finally:
        worker.tokenizer.batch_decode=original
    raw_text=raw[0] if isinstance(raw,tuple) else raw
    elapsed=time.perf_counter()-start
    emit('raw-output',dict(raw_response=raw_text if isinstance(raw_text,str) else repr(raw_text),
        raw_return_repr=repr(raw),observed_decoded_sequences=observed,inference_s=elapsed))
    require(isinstance(raw_text,str) and len(observed)==1 and len(observed[0])==1,
            'generated token evidence missing','INVALID_OUTPUT')
    audit=generation_audit(observed[0][0],len(ids),worker.tokenizer.model_max_length,
                           worker.tokenizer.convert_tokens_to_ids('<|im_end|>'))
    return raw_text,audit,elapsed


def points(root):
    root=Path(root); r=registration(root)
    out=root/'points'; out.mkdir(exist_ok=False)
    write(out/'condition.json',dict(registration_sha256=file_hash(root/'registration.json'),
        generation_settings=SETTINGS,point_question='Point to: {frozen_drawer_query}.',
        generator_inputs=['original_full_RGB','fixed_query'],evaluation_labels_used=False,
        code=code_identity(),versions=versions(),executable=sys.executable,pid=os.getpid()))
    try:
        worker,model=_load_worker()
        write(out/'model.json',model)
        sensor_frames=frames(r['entry']); records=[]
        for row in r['inputs']:
            i=row['input_index']; image=row['image']
            view,_=sensor_frames[image['frame_id']]
            require(sensor_view_identity(view)==row['source_identity'],'POINT sensor binding changed')
            def emit(name,value):
                write(out/f'frame-{i:03d}-{name}.json',value)
            record=dict(input_index=i,image=image,source_identity=row['source_identity'],query=row['query'],
                raw_output=None,audit=None,typed=None,source_admitted=False,point_xy=None,sample_pixel_xy=None,
                status='FAILURE',reason=None,inference_s=None,response_sha256=None,hidden_retry=False,
                evaluation_labels_used=False,provenance='learned estimate')
            fatal = None
            try:
                raw,audit,elapsed=infer_point(worker,view['rgb'],row['query'],emit)
                record.update(status='COMPLETE',raw_output=raw,audit=audit,inference_s=elapsed,
                    response_sha256=hashlib.sha256(raw.encode()).hexdigest())
                if audit['complete_generation'] and audit['terminal_eos_observed']:
                    typed=parse_semantic_reply(raw,image['width'],image['height'],mode='point',audit=audit)
                    record.update(typed=typed.evidence(),source_admitted=typed.admitted,reason=typed.reason)
                    if typed.admitted:
                        record.update(point_xy=list(typed.selected[0].pixels),
                                      sample_pixel_xy=list(typed.selected[0].sample_pixel_xy))
                else:
                    record['reason']='INCOMPLETE_GENERATION'
            except Exception as exc:
                record.update(reason='POINT_INFERENCE_FAILURE',error=repr(exc))
                if isinstance(exc, (RuntimeError, MemoryError)):
                    fatal = exc
            write(out/f'frame-{i:03d}.json',record); records.append(record)
            if fatal is not None:
                raise fatal
            print(f"POINT frame {i+1}/50 {record['reason'] or 'typed admitted'}",flush=True)
        write(out/'outputs.json',records)
    except Exception as exc:
        write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False)); seal(out); raise
    seal(out)


def _masks(root, r, out):
    import torch
    assets = r["environment_receipt"]
    write(out/"process-environment.json", dict(executable=sys.executable, prefix=sys.prefix,
        base_prefix=sys.base_prefix, torch=torch.__version__, pid=os.getpid()))
    require(os.path.abspath(sys.executable) == os.path.abspath(assets["python_executable"])
            and Path(sys.prefix).absolute() == Path(assets["python_executable"]).absolute().parent.parent,
            "invoke prepared venv without resolving symlink")
    require(torch.__version__ == "2.5.1+cu121" and os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8",
            "locked torch/workspace required")
    gpu = _explicit_gpu_mask()
    require(gpu.startswith("GPU-"), "GPU UUID required")
    allocation = _cuda_allocation(torch, gpu)
    import sam2
    require(Path(sam2.__file__).resolve().is_relative_to(Path(assets["sam_source"]).resolve()),
            "SAM import differs")
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from .sam2_deterministic_grid import install_and_verify
    torch.manual_seed(1)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    write(out/"condition.json", dict(code=code_identity(), allocation=allocation, sam_settings=SAM_SETTINGS,
        compatibility=r["entry"]["SAM_compatibility"], model_inputs=["original_full_RGB", "sealed_BOX_xyxy", "same_frame_positive_POINT"],
        evaluation_labels_used=False, depth_to_SAM=False, registration_sha256=file_hash(root/"registration.json"),
        points_seal_sha256=file_hash(root/"points/sealed.json")))
    start = time.perf_counter()
    model = build_sam2(assets["sam_config"], assets["checkpoint_path"], device="cuda:0", apply_postprocessing=False)
    write(out/"dense-grid-equivalence.json", install_and_verify(model))
    predictor = SAM2ImagePredictor(model, mask_threshold=0.0, max_hole_area=0.0, max_sprinkle_area=0.0)
    torch.cuda.synchronize()
    write(out/"startup.json", dict(model_load_and_overlay_s=time.perf_counter()-start))
    sensor_frames = frames(r["entry"])
    point_records = read(root/"points/outputs.json")
    require([p["input_index"] for p in point_records] == list(range(50)), "complete canonical POINT inputs required")
    require(all(p['image'] == row['image'] and p['source_identity'] == row['source_identity']
                and p['query'] == row['query'] for p,row in zip(point_records,r['inputs'])),
            'canonical POINT frame bindings differ')
    records = []
    with torch.inference_mode():
        for row in r["inputs"]:
            i, image = row["input_index"], row["image"]
            view, _ = sensor_frames[image["frame_id"]]
            require(sensor_view_identity(view) == row["source_identity"], "sensor binding changed")
            if not row["source_admitted"] or not row["ordered_boxes"]:
                record = dict(**row, status="FAILURE", failure_stage="semantic_source_admission",
                              error=row["source_reason"], box_index=None, mask_count=0, hidden_retry=False)
                write(out/f"frame-{i:03d}-failure.json", record)
                records.append(record)
                continue
            point = point_records[i]
            prompts = [point_prompt(view, box, point, query=row['query'], config=config())
                       for box in row['ordered_boxes']]
            if not any(p['admitted'] for p in prompts):
                for index, box in enumerate(row['ordered_boxes']):
                    record = dict(**row, status='FAILURE', failure_stage=prompts[index]['reason'],
                        error=prompts[index]['reason'], box_index=index, box_xyxy=box,
                        mask_count=0, encode_s=None, hidden_retry=False, prompt_admission=prompts[index])
                    write(out/f'frame-{i:03d}-box-{index:03d}.json',record); records.append(record)
                continue
            encode_error, encode_s = None, None
            try:
                torch.cuda.synchronize()
                start = time.perf_counter()
                predictor.set_image(view["rgb"].copy())
                torch.cuda.synchronize()
                encode_s = time.perf_counter()-start
            except Exception as exc:
                if isinstance(exc, (RuntimeError, MemoryError)):
                    raise
                encode_error = repr(exc)
            for index, box in enumerate(row["ordered_boxes"]):
                record = dict(**row, box_index=index, box_xyxy=box, encode_s=encode_s,
                              mask_count=0, selected_mask=None, hidden_retry=False,
                              prompt_admission=prompts[index], point_xy=prompts[index]['point_xy'],
                              sample_pixel_xy=prompts[index]['sample_pixel_xy'], point_response_sha256=point['response_sha256'])
                phase = "image_encoding"
                fatal = None
                try:
                    phase = 'POINT_BOX_PROMPT_ADMISSION'
                    require(prompts[index]['admitted'], prompts[index]['reason'] or 'prompt rejected')
                    phase = 'image_encoding'
                    require(encode_error is None, encode_error or "encoding failed")
                    phase = "mask_prediction"
                    torch.cuda.synchronize()
                    start = time.perf_counter()
                    logits, scores, lowres = predictor.predict(point_coords=np.asarray([prompts[index]['point_xy']], dtype=np.float32),
                        point_labels=np.asarray([1], dtype=np.int32), box=np.asarray(box, dtype=np.float32),
                        multimask_output=True, return_logits=True)
                    torch.cuda.synchronize()
                    record["predict_s"] = time.perf_counter()-start
                    # Retain raw returned arrays even if validation rejects them.
                    native = logits > 0.0
                    path = out/f"frame-{i:03d}-box-{index:03d}.npz"
                    np.savez_compressed(path, logits=logits, predicted_ious=scores, lowres_logits=lowres, masks=native)
                    record.update(artifact_uri=str(path.absolute()), artifact_sha256=file_hash(path))
                    phase = "native_output_validation"
                    require(logits.shape == (3, image["height"], image["width"]) and scores.shape == (3,)
                            and np.isfinite(logits).all() and np.isfinite(scores).all()
                            and np.isfinite(lowres).all(), "invalid native output; no repair")
                    record.update(status="COMPLETE", mask_count=3, predicted_ious=scores.tolist(),
                        native_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in native],
                        sam_input_box_float32=np.asarray(box, dtype=np.float32).tolist(),
                        sam_input_point_float32=np.asarray([prompts[index]['point_xy']],dtype=np.float32).tolist(),
                        sam_input_point_labels=[1],
                        native_mask_pixel_counts=[int(m.sum()) for m in native], calibrated_confidence=None)
                except Exception as exc:
                    record.update(status="FAILURE", failure_stage=phase, error=repr(exc))
                    if isinstance(exc, (RuntimeError, MemoryError)):
                        fatal = exc
                write(out/f"frame-{i:03d}-box-{index:03d}.json", record)
                records.append(record)
                if fatal is not None:
                    raise fatal
            print(f"SAM frame {i+1}/50 {image['camera_id']} preserved", flush=True)
    write(out/"outputs.json", records)


def masks(root):
    root = Path(root)
    r = registration(root)
    verify_seal(root/'points')
    require((root/'points/outputs.json').exists(), 'POINT corpus incomplete; no retry')
    out = root/"masks"
    out.mkdir(exist_ok=False)
    try:
        _masks(root, r, out)
    except Exception as exc:
        write(out/"runtime-failure.json", dict(error=repr(exc), hidden_retry=False))
        seal(out)
        raise
    seal(out)


def geometry(root):
    root = Path(root)
    r = registration(root)
    verify_seal(root/"masks")
    require((root/"masks/outputs.json").exists(), "corpus incomplete after runtime failure; no hidden retry")
    out = root/"geometry"
    out.mkdir(exist_ok=False)
    sensor_frames, cfg, rows = frames(r["entry"]), config(), []
    for record in read(root/"masks/outputs.json"):
        row = dict(input_index=record["input_index"], image=record["image"], box_index=record["box_index"],
                   status=record["status"], native_mask_estimates=[], mask_geometry_s=[], stage_ledger=[], mask_point_admission=[])
        if record["status"] != "COMPLETE":
            row.update(failure_stage=record["failure_stage"], error=record["error"],
                       geometry_evaluation="NOT_EVALUATED")
        else:
            view, proprio = sensor_frames[record["image"]["frame_id"]]
            require(sensor_view_identity(view) == record["source_identity"]
                    and file_hash(record["artifact_uri"]) == record["artifact_sha256"], "mask source changed")
            with np.load(record["artifact_uri"], allow_pickle=False) as data:
                require(data["masks"].dtype == bool and data["masks"].shape == (3, *view["depth_m"].shape)
                        and np.array_equal(data["masks"], data["logits"] > 0.0), "native masks changed")
                for index, native in enumerate(data["masks"]):
                    binding = dict(source_identity=record["source_identity"], sensor_view_sha256=record["sensor_view_sha256"],
                        query=record["query"], box_index=record["box_index"], box_xyxy=record["box_xyxy"],
                        box_response_sha256=record["response_sha256"], mask_index=index,
                        raw_mask_sha256=record["native_mask_sha256"][index], mask_artifact_uri=record["artifact_uri"],
                        mask_artifact_sha256=record["artifact_sha256"], coordinate_convention="top-left-origin-pixel-xyxy",
                        mask_input_channels=["rgb"], evaluation_labels_used=False, provenance="learned estimate")
                    start = time.perf_counter()
                    estimate = estimate_segmented_patch(view, record["box_xyxy"], native, mask_binding=binding,
                        config=cfg, track_id="drawer_front_pushable", feature_id=f"box-{record['box_index']}/mask-{index}",
                        seed=0, eef_position_base_m=proprio["eef_position_base_m"],
                        measurement_contract="native-mask-depth/2")
                    row['mask_point_admission'].append(mask_point_admission(native,record['prompt_admission'],index))
                    row["mask_geometry_s"].append(time.perf_counter()-start)
                    row["native_mask_estimates"].append(estimate)
                    row["stage_ledger"].append(ledger(estimate["patch"]))
        write(out/f"frame-{record['input_index']:03d}-box-{record['box_index']}.json", row)
        rows.append(row)
        print(f"geometry frame {record['input_index']+1}/50 preserved", flush=True)
    write(out/"results.json", rows)
    write(out/"condition.json", dict(code=code_identity(), config=cfg.to_dict(),
        measurement_contract="native-mask-depth/2", masks_seal_sha256=file_hash(root/"masks/sealed.json"),
        registration_sha256=file_hash(root/"registration.json"),
        all_native_masks_evaluated=True, selected_mask=None, evaluation_labels_used=False, for_execution=False))
    seal(out)



def launch(root, gpu, stage):
    root=Path(root); r=registration(root)
    require(gpu.startswith('GPU-') and stage in {'points','masks'},'explicit GPU/stage required')
    executable=('/home/junhongli/miniforge3/envs/locateanything/bin/python' if stage=='points'
                else str(Path(r['environment_receipt']['python_executable']).absolute()))
    cmd=[executable,'-m','embodied_runtime.experiments.p1_identity_prompt',stage,'--output',str(root)]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu,CUBLAS_WORKSPACE_CONFIG=':4096:8',
             HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    start=datetime.now(timezone.utc).isoformat(); timed_out=False; result=None
    with (root/f'{stage}-process.log').open('x') as log:
        try:
            result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=r['batch_timeout_s'])
        except subprocess.TimeoutExpired:
            timed_out=True
    write(root/f'{stage}-process.json',dict(command=cmd,started_at_utc=start,
        ended_at_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode if result else None,
        timeout=timed_out,gpu_uuid=gpu,hidden_retry=False))
    require(not timed_out and result.returncode==0,'first stage process failed; no retry')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','launch-points','points','launch-masks','masks','geometry','score','review'])
    parser.add_argument('--output',required=True); parser.add_argument('--gpu-uuid')
    args=parser.parse_args()
    if args.stage.startswith('launch-'):
        launch(args.output,args.gpu_uuid or '',args.stage.removeprefix('launch-'))
    elif args.stage=='score':
        from .p1_identity_repair_scoring import score
        score(args.output)
    else:
        {'prepare':prepare,'points':points,'masks':masks,'geometry':geometry,'review':review}[args.stage](args.output)

if __name__=='__main__':
    main()
