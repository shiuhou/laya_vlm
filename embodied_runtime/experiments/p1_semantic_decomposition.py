"""Offline human-assisted decomposition; never runtime perception evidence."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from ..contracts import content_hash, require
from ..perception.rgbd_geometry import estimate_visible_patch, _roi
from ..perception.semantic_prompt import mask_point_admission
from ..perception.surface_association import sensor_view_identity
from .p1_formal50 import frames, ledger
from .p1_formal50_scoring import score_mask, _percentiles
from .p1_human_region_geometry import registration as human_registration
from .p1_identity_prompt import registration as model_registration
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import SAM_SETTINGS, read, write, seal, verify_seal
from .records import code_identity, file_hash, versions

HUMAN = Path('runs/p1/human-region-geometry-20261007')
MODEL = Path('runs/p1/identity-point-sam-20261007')
PROTOCOL = Path('docs/research/p1_semantic_decomposition_protocol.md')
CONDITION = 'offline-semantic-decomposition/1'


def human_prompt(mask):
    """Exact padded-mask EDT maximum using bounded-memory squared distances."""
    require(mask.dtype == bool and mask.ndim == 2 and mask.any(), 'nonempty bool mask required')
    yy,xx=np.where(mask); x0,x1=int(xx.min()),int(xx.max())+1; y0,y1=int(yy.min()),int(yy.max())+1
    local=np.pad(mask[y0:y1,x0:x1],1,constant_values=False)
    # Only complement pixels adjacent to support can be nearest to support.
    adjacent=np.zeros_like(local)
    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
        adjacent |= np.roll(np.roll(local,dy,axis=0),dx,axis=1)
    outside=np.argwhere(adjacent & ~local)
    inside=np.argwhere(local)
    distances=[]
    for batch in np.array_split(inside,max(1,(len(inside)+127)//128)):
        distances.extend(np.min(np.sum((batch[:,None,:]-outside[None,:,:])**2,axis=2),axis=1).tolist())
    best=int(np.argmax(distances)); v,u=inside[best]; u=int(u+x0-1);v=int(v+y0-1)
    return dict(box_xyxy=[x0,y0,x1,y1],point_xy=[u+.5,v+.5],sample_pixel_xy=[u,v],
                annotation_clearance_pixels=float(np.sqrt(distances[best])),evaluation_labels_used=True)


def admit(view,box,prompt):
    x,y=prompt['point_xy'];u,v=prompt['sample_pixel_xy'];h,w=view['depth_m'].shape
    roi=_roi(box,w,h); cfg=config()
    result=dict(prompt,admitted=False,reason=None,geometry_roi_xyxy=list(roi),sampled_depth_m=None,
                calibrated_confidence=None,for_execution=False)
    if not(box[0]<=x<box[2] and box[1]<=y<box[3]):
        return dict(result,reason='POINT_OUTSIDE_ORIGINAL_BOX')
    if not(roi[0]<=u<roi[2] and roi[1]<=v<roi[3]):
        return dict(result,reason='POINT_SAMPLE_OUTSIDE_GEOMETRY_ROI')
    d=float(view['depth_m'][v,u])
    if not np.isfinite(d) or not cfg.min_depth_m<=d<=cfg.max_depth_m:
        return dict(result,reason='POINT_DEPTH_UNAVAILABLE')
    return dict(result,admitted=True,sampled_depth_m=d)


def registration(root):
    root=Path(root);r=read(root/'registration.json')
    model_registration(MODEL)
    require(content_hash({k:v for k,v in r.items() if k!='registration_content_sha256'})==r['registration_content_sha256'],'registration changed')
    require(r['condition']==CONDITION and r['evaluation_labels_used'] and not r['for_execution'],'offline condition required')
    require(content_hash(config().to_dict())==content_hash(r['geometry_config']),'geometry changed')
    for p,d in r['source_files_sha256'].items():
        require(file_hash(p)==d,'source changed: '+p)
    verify_seal(root/'inputs')
    return r


def prepare(root):
    h=human_registration(HUMAN);b=model_registration(MODEL);code=code_identity()
    require(not code['dirty_status'],'commit execution code first')
    for source,stages in ((HUMAN,('geometry','summary')),(MODEL,('points','masks','geometry','scoring'))):
        for stage in stages:verify_seal(source/stage)
    sensor=frames(b['entry']);root=Path(root);root.mkdir(exist_ok=False);(root/'inputs').mkdir()
    rows=[]
    for human in h['inputs']:
        original=b['inputs'][human['original_formal50_index']]
        require(original['image']==human['image'] and original['source_identity']==human['source_identity'],'frame binding differs')
        require(file_hash(human['mask_uri'])==human['mask_sha256'],'human support changed')
        prompt=human_prompt(np.load(human['mask_uri'],allow_pickle=False))
        view,_=sensor[human['image']['frame_id']]
        require(len(original['ordered_boxes'])==1 and original['source_admitted'],'expected frozen single admitted BOX')
        for condition,box in (('C2',prompt['box_xyxy']),('C3',original['ordered_boxes'][0])):
            row=dict(condition=condition,input_index=len(rows),init_index=human['image']['init_index'],
                image=human['image'],source_identity=human['source_identity'],box_xyxy=box,
                original_formal50_index=human['original_formal50_index'],human_support_sha256=human['mask_sha256'],
                original_box_record=original,prompt_admission=admit(view,box,prompt),
                evaluation_labels_used=True,for_execution=False)
            rows.append(row)
    write(root/'inputs/prompts.json',rows);seal(root/'inputs')
    sources=dict(h['source_files_sha256']);sources.update(b['source_files_sha256'])
    paths=[Path(p) for p in code['source_sha256']]+[PROTOCOL,HUMAN/'registration.json',MODEL/'registration.json']
    for source in (HUMAN,MODEL):
        paths.extend(p for p in source.rglob('*') if p.is_file() and p.suffix in ('.json','.npy','.npz'))
    sources.update({str(p.absolute()):file_hash(p) for p in paths})
    r=dict(condition=CONDITION,code=code,entry=b['entry'],environment_receipt=b['environment_receipt'],
        geometry_config=config().to_dict(),sam_settings=SAM_SETTINGS,inputs=rows,source_files_sha256=sources,
        registered_at_utc=datetime.now(timezone.utc).isoformat(),evaluation_labels_used=True,for_execution=False,
        independent_heldout=False,perception_acceptance=False,LocateAnything_calls=0,planned_SAM_slots=50,
        protocol_sha256=file_hash(PROTOCOL),frame_retry_count=0)
    r['registration_content_sha256']=content_hash(r);write(root/'registration.json',r)
    registration(root)


def masks(root):
    root=Path(root);r=registration(root);out=root/'masks';out.mkdir(exist_ok=False)
    try:
        import torch
        from .p1_semantic_grounding import _explicit_gpu_mask,_cuda_allocation
        assets=r['environment_receipt']
        require(os.path.abspath(sys.executable)==os.path.abspath(assets['python_executable']),'SAM venv differs')
        require(torch.__version__=='2.5.1+cu121' and os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8','locked environment required')
        import sam2
        require(Path(sam2.__file__).resolve().is_relative_to(Path(assets['sam_source']).resolve()),'SAM import changed')
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        from .sam2_deterministic_grid import install_and_verify
        torch.manual_seed(1);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
        write(out/'condition.json',dict(code=code_identity(),versions=versions(),pid=os.getpid(),executable=sys.executable,
            prefix=sys.prefix,allocation=_cuda_allocation(torch,_explicit_gpu_mask()),sam_settings=SAM_SETTINGS,
            evaluation_labels_used=True,depth_to_SAM=False,for_execution=False,calibrated_confidence=None,
            registration_sha256=file_hash(root/'registration.json'),inputs_seal_sha256=file_hash(root/'inputs/sealed.json')))
        model=build_sam2(assets['sam_config'],assets['checkpoint_path'],device='cuda:0',apply_postprocessing=False)
        write(out/'dense-grid-equivalence.json',install_and_verify(model))
        predictor=SAM2ImagePredictor(model,mask_threshold=0.,max_hole_area=0.,max_sprinkle_area=0.)
        sensor=frames(r['entry']);records=[]
        with torch.inference_mode():
            for row in r['inputs']:
                record=dict(row,status='FAILURE',mask_count=0,hidden_retry=False,encode_s=None,predict_s=None)
                prompt=row['prompt_admission'];phase='prompt_admission'
                if not prompt['admitted']:
                    record.update(failure_stage=prompt['reason'],error=prompt['reason'])
                else:
                    try:
                        view,_=sensor[row['image']['frame_id']]
                        require(sensor_view_identity(view)==row['source_identity'],'sensor changed')
                        phase='image_encoding';torch.cuda.synchronize();start=time.perf_counter()
                        predictor.set_image(view['rgb'].copy());torch.cuda.synchronize();record['encode_s']=time.perf_counter()-start
                        phase='mask_prediction';start=time.perf_counter()
                        logits,scores,lowres=predictor.predict(point_coords=np.asarray([prompt['point_xy']],dtype=np.float32),
                            point_labels=np.asarray([1],dtype=np.int32),box=np.asarray(row['box_xyxy'],dtype=np.float32),
                            multimask_output=True,return_logits=True)
                        torch.cuda.synchronize();record['predict_s']=time.perf_counter()-start
                        native=logits>0.;path=out/f"input-{row['input_index']:03d}.npz"
                        np.savez_compressed(path,logits=logits,predicted_ious=scores,lowres_logits=lowres,masks=native)
                        record.update(artifact_uri=str(path.absolute()),artifact_sha256=file_hash(path))
                        phase='native_output_validation'
                        require(logits.shape==(3,*view['depth_m'].shape) and scores.shape==(3,) and
                            all(np.isfinite(x).all() for x in (logits,scores,lowres)),'invalid native outputs')
                        record.update(status='COMPLETE',mask_count=3,predicted_ious=scores.tolist(),
                            sam_input_box_float32=np.asarray(row['box_xyxy'],dtype=np.float32).tolist(),
                            sam_input_point_float32=np.asarray([prompt['point_xy']],dtype=np.float32).tolist(),
                            native_mask_pixel_counts=[int(m.sum()) for m in native],
                            native_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in native])
                    except Exception as exc:
                        record.update(failure_stage=phase,error=repr(exc))
                        write(out/f"input-{row['input_index']:03d}.json",record);records.append(record)
                        raise
                write(out/f"input-{row['input_index']:03d}.json",record);records.append(record)
                print(row['condition'],row['init_index'],record['status'],flush=True)
        write(out/'outputs.json',records)
    except Exception as exc:
        write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False));seal(out);raise
    seal(out)


def launch(root,gpu):
    root=Path(root);r=registration(root);require(gpu.startswith('GPU-'),'UUID required')
    command=[r['environment_receipt']['python_executable'],'-m',__name__ if __name__!='__main__' else
             'embodied_runtime.experiments.p1_semantic_decomposition','masks','--output',str(root)]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu,CUBLAS_WORKSPACE_CONFIG=':4096:8',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    started=datetime.now(timezone.utc).isoformat()
    result=None; timed_out=False
    with (root/'sam-process.log').open('x') as log:
        try:
            result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        except subprocess.TimeoutExpired:
            timed_out=True
    write(root/'sam-process.json',dict(command=command,gpu_uuid=gpu,started_at_utc=started,
        ended_at_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode if result else None,timeout=timed_out,hidden_retry=False))
    require(not timed_out and result is not None and result.returncode==0,'first process failed; no retry')


def geometry(root):
    root=Path(root);r=registration(root);verify_seal(root/'masks');out=root/'geometry';out.mkdir(exist_ok=False)
    sensor=frames(r['entry']);cfg=config();results=[]
    for record in read(root/'masks/outputs.json'):
        row=dict(record,native_results=[])
        if record['status']=='COMPLETE':
            view,proprio=sensor[record['image']['frame_id']]
            require(sensor_view_identity(view)==record['source_identity'] and file_hash(record['artifact_uri'])==record['artifact_sha256'],'source mismatch')
            with np.load(record['artifact_uri'],allow_pickle=False) as data:
                require(np.array_equal(data['masks'],data['logits']>0.),'native masks changed')
                for ordinal,native in enumerate(data['masks']):
                    masked=view['depth_m'].copy();masked[~native]=np.nan
                    start=time.perf_counter()
                    patch=estimate_visible_patch(masked,view['intrinsics_K'],view['T_base_camera'],
                        roi_xyxy=record['box_xyxy'],source_frame_id=record['source_identity']['frame_id'],
                        calibration_version=view['calibration_version'],track_id='offline-human-assisted',
                        feature_id=f"{record['condition']}/mask-{ordinal}",capture_sim_time_s=view['capture_sim_time_s'],
                        capture_monotonic_ns=view['capture_monotonic_ns'],config=cfg,seed=0,
                        eef_position_base_m=proprio['eef_position_base_m'],depth_availability_mask=native).to_dict()
                    elapsed=time.perf_counter()-start;stages=ledger(patch);stages.pop('semantic_source_admission')
                    stages['offline_human_prompt']='SUPPLIED_NOT_RUNTIME_ADMISSION'
                    row['native_results'].append(dict(ordinal=ordinal,patch=patch,source_identity=record['source_identity'],
                        geometry_s=elapsed,stage_ledger=stages,mask_point_admission=mask_point_admission(native,record['prompt_admission'],ordinal),
                        derived_masked_depth_sha256=hashlib.sha256(masked.tobytes()).hexdigest(),evaluation_labels_used=True,for_execution=False))
        else:row['geometry_evaluation']='NOT_EVALUATED'
        write(out/f"input-{record['input_index']:03d}.json",row);results.append(row)
        print('geometry',record['condition'],record['init_index'],flush=True)
    write(out/'results.json',results)
    write(out/'condition.json',dict(code=code_identity(),versions=versions(),config=cfg.to_dict(),
        measurement_contract='native-mask-depth/2',evaluation_labels_used=True,for_execution=False,
        registration_sha256=file_hash(root/'registration.json'),masks_seal_sha256=file_hash(root/'masks/sealed.json'),
        process_environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')}))
    seal(out)


def score(root):
    root=Path(root);r=registration(root);verify_seal(root/'geometry');out=root/'scoring';out.mkdir(exist_ok=False)
    labels={x['image_id']:x for x in read(r['entry']['annotation_path'])['annotations']};rows=[]
    for record in read(root/'geometry/results.json'):
        row=dict(condition=record['condition'],init_index=record['init_index'],status=record['status'],
            failure_stage=record.get('failure_stage'),masks=[],raw_inside=0,admitted_inside=0,raw_outside=0,admitted_outside=0)
        if record['status']=='COMPLETE':
            with np.load(record['artifact_uri'],allow_pickle=False) as data:
                for result,native in zip(record['native_results'],data['masks']):
                    scored=score_mask(record['image'],labels[record['image']['image_id']]['entities']['drawer_front_pushable'],
                        native,result,ordinal=result['ordinal'],box=record['box_xyxy'],stage_ledger=result['stage_ledger'])
                    scored.update(mask_point_admission=result['mask_point_admission'],geometry_s=result['geometry_s'])
                    row['masks'].append(scored);row['raw_inside']+=scored['task_valid_candidate_count'];row['raw_outside']+=scored['outside_region_candidate_count']
                    if result['mask_point_admission']['admitted']:
                        row['admitted_inside']+=scored['task_valid_candidate_count'];row['admitted_outside']+=scored['outside_region_candidate_count']
        rows.append(row)
    summaries={}
    for c in ('C2','C3'):
        selected=[x for x in rows if x['condition']==c];native=[m for x in selected for m in x['masks']]
        summaries[c]=dict(frames=25,completed_frames=sum(x['status']=='COMPLETE' for x in selected),native_masks=len(native),
            raw_candidate_frames=sum(x['raw_inside']>0 for x in selected),admitted_candidate_frames=sum(x['admitted_inside']>0 for x in selected),
            raw_inside=sum(x['raw_inside'] for x in selected),raw_outside=sum(x['raw_outside'] for x in selected),
            admitted_inside=sum(x['admitted_inside'] for x in selected),admitted_outside=sum(x['admitted_outside'] for x in selected),
            failures=dict(Counter(x['failure_stage'] for x in selected if x['status']!='COMPLETE')),
            first_boundary=dict(Counter(m['reason_codes'][0] if m['reason_codes'] else 'CANDIDATES' for m in native)),
            point_contradictions=sum(not m['mask_point_admission']['admitted'] for m in native),
            geometry_timing=_percentiles([m['geometry_s'] for m in native]))
    write(out/'rows.json',rows);write(out/'summary.json',summaries);seal(out);print(summaries,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','launch','masks','geometry','score'])
    p.add_argument('--output',required=True);p.add_argument('--gpu-uuid');a=p.parse_args()
    if a.stage=='launch':launch(a.output,a.gpu_uuid or '')
    else:
        try:
            globals()[a.stage](a.output)
        except Exception as exc:
            out=Path(a.output)/a.stage
            if out.is_dir() and not (out/'sealed.json').exists():
                write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False));seal(out)
            raise
if __name__=='__main__':main()
