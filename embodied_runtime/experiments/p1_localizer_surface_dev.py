"""Run recorded automatic 2D grounding through frozen SAM and RGB-D geometry.

Development-only, no labels, oracle, motion, or mask winner. SAM and geometry
are separate stages so the existing environments remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import time

import numpy as np

from ..contracts import content_hash, require
from ..perception.grounding_observation import validate_grounding_observation
from ..perception.recording import replay_frames, project_base_points
from ..perception.semantic_prompt import grounding_point_prompt, mask_point_admission
from ..perception.segmented_patch import estimate_segmented_patch
from ..perception.surface_association import sensor_view_identity
from .p1_formal50 import ledger
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import read, write, seal, verify_seal, SAM_SETTINGS, CHECKPOINT_SHA, CONFIG_SHA
from .records import code_identity, file_hash, versions

ASSETS = Path('runs/p1/box-heldout23-20261008/registration.json')


def source_frame(record):
    """Match an exact canonical recorded camera frame, never silently take latest."""
    found = []
    for envelope, views in replay_frames(record['recording']):
        for view in views:
            view = dict(view, frame_id=view['canonical_frame_id'])
            if sensor_view_identity(view) == record['source_identity']:
                found.append((view, envelope.payload['proprio']))
    require(len(found) == 1, 'exactly one matching recorded frame required', 'SOURCE_MISMATCH')
    return found[0]


def input_rows(root):
    verify_seal(root)
    records = read(Path(root)/'outputs.json')['records']
    require(bool(records), 'no input records')
    seen = set()
    for record in records:
        identity = content_hash(record['source_identity'])
        require(identity not in seen, 'duplicate frame')
        seen.add(identity)
        view, _ = source_frame(record)
        if record.get('box_observation') is None and record.get('point_observation') is None:
            coarse = validate_grounding_observation(record['coarse_observation'], view=view)
            require(not coarse.admitted and record['box_status'] == record['point_status'] == 'NOT_ATTEMPTED_COARSE_REJECTED',
                    'missing fine observations require explicit coarse refusal')
            continue
        for mode, key in [('BOX', 'box_observation'), ('POINT', 'point_observation')]:
            obs = record[key]
            reply = validate_grounding_observation(obs, view=view)
            require(reply.mode == mode and obs['source_identity'] == record['source_identity'],
                    'wrong observation mode/source', 'SOURCE_MISMATCH')
    return records


def masks(grounding, output):
    import torch

    records = input_rows(grounding)
    registration = read(ASSETS)
    assets = registration['environment_receipt']
    pinned_roots = [Path(assets['sam_source']).resolve()]
    pinned_files = {Path(assets['dependency_lock_path']).resolve(), Path(assets['environment_record']['freeze_path']).resolve()}
    for name, digest in registration['source_files_sha256'].items():
        path = Path(name).resolve()
        if path in pinned_files or any(path.is_relative_to(root) for root in pinned_roots):
            require(file_hash(path) == digest, 'frozen SAM source/dependency changed: '+name)
    require(Path(sys.executable).absolute() == Path(assets['python_executable']).absolute(), 'use frozen SAM environment')
    require(torch.__version__ == '2.5.1+cu121', 'SAM torch changed')
    require(file_hash(assets['checkpoint_path']) == CHECKPOINT_SHA, 'SAM checkpoint changed')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8', 'deterministic workspace required')
    import sam2
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from .sam2_deterministic_grid import install_and_verify
    from .p1_semantic_grounding import _cuda_allocation, _explicit_gpu_mask

    require(Path(sam2.__file__).resolve().is_relative_to(Path(assets['sam_source']).resolve()), 'SAM source changed')
    require(file_hash(Path(assets['sam_source'])/'sam2/configs/sam2.1/sam2.1_hiera_t.yaml') == CONFIG_SHA, 'SAM config changed')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write(out/'condition.json', dict(code=code_identity(), versions=versions(),
        grounding=str(Path(grounding).resolve()), grounding_seal_sha256=file_hash(Path(grounding)/'sealed.json'),
        allocation=_cuda_allocation(torch, _explicit_gpu_mask()), assets=assets, settings=SAM_SETTINGS,
        development_only=True, evaluation_labels_used=False, for_execution=False))
    torch.manual_seed(1)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    model = build_sam2(assets['sam_config'], assets['checkpoint_path'], device='cuda:0', apply_postprocessing=False)
    write(out/'grid-receipt.json', install_and_verify(model))
    predictor = SAM2ImagePredictor(model, mask_threshold=0., max_hole_area=0., max_sprinkle_area=0.)
    results = []
    with torch.inference_mode():
        for i, record in enumerate(records):
            view, _ = source_frame(record)
            box_obs, point_obs = record['box_observation'], record['point_observation']
            reply = validate_grounding_observation(box_obs, view=view) if box_obs is not None else None
            boxes = reply.ordered_boxes_xyxy_px if reply is not None and reply.admitted else []
            for ordinal, box in enumerate(boxes or [None]):
                row = dict(input_index=i, input_record=record, source_identity=record['source_identity'],
                    box_index=ordinal if box is not None else None, box_xyxy=list(box) if box else None,
                    query=box_obs['query'] if box_obs else record['query'],
                    box_response_sha256=box_obs['raw_output_sha256'] if box_obs else None,
                    status='NOT_EVALUATED', failure_stage=None, mask_count=0,
                    evaluation_labels_used=False, for_execution=False)
                if box is None:
                    row['failure_stage'] = 'BOX_'+str(reply.reason) if reply is not None else 'COARSE_LOCALIZATION_REJECTED'
                else:
                    prompt = grounding_point_prompt(view, box, point_obs, query=box_obs['query'],
                                                     config=config(), target_key=box_obs['target_key'])
                    row['prompt_admission'] = prompt
                    if not prompt['admitted']:
                        row['failure_stage'] = prompt['reason']
                    else:
                        torch.cuda.synchronize()
                        start = time.perf_counter()
                        predictor.set_image(view['rgb'].copy())
                        torch.cuda.synchronize()
                        row['encode_s'] = time.perf_counter()-start
                        start = time.perf_counter()
                        logits, scores, lowres = predictor.predict(
                            point_coords=np.asarray([prompt['point_xy']], dtype=np.float32),
                            point_labels=np.asarray([1], dtype=np.int32), box=np.asarray(box, dtype=np.float32),
                            multimask_output=True, return_logits=True)
                        torch.cuda.synchronize()
                        row['predict_s'] = time.perf_counter()-start
                        native = logits > 0.
                        path = out/f'frame-{i:03d}-box-{ordinal:03d}.npz'
                        np.savez_compressed(path, masks=native, logits=logits, predicted_ious=scores, lowres_logits=lowres)
                        require(logits.shape == (3, *view['depth_m'].shape) and scores.shape == (3,)
                                and all(np.isfinite(x).all() for x in [logits, scores, lowres]), 'invalid native SAM outputs')
                        row.update(status='COMPLETE', mask_count=3, artifact_uri=str(path.resolve()), artifact_sha256=file_hash(path),
                            raw_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in native],
                            predicted_ious=scores.tolist(), mask_pixels=[int(m.sum()) for m in native],
                            sam_input_point_float32=np.asarray([prompt['point_xy']], dtype=np.float32).tolist(),
                            sam_input_box_float32=np.asarray(box, dtype=np.float32).tolist())
                write(out/f'frame-{i:03d}-box-{ordinal:03d}.json', row)
                results.append(row)
            print(f'SAM frame {i}: {results[-1]["status"]}', flush=True)
    write(out/'outputs.json', dict(records=results))
    seal(out)


def draw_native(view, row, native, estimate, ordinal, out):
    from PIL import Image, ImageDraw

    raw = Image.fromarray(view['rgb'])
    pixels = np.array(raw).copy()
    pixels[native] = (pixels[native]*.6 + np.array([60,120,255])*.4).astype(np.uint8)
    overlay = Image.fromarray(pixels)
    d = ImageDraw.Draw(overlay)
    d.rectangle(row['box_xyxy'], outline='cyan', width=1)
    x, y = row['prompt_admission']['point_xy']
    d.ellipse((x-3,y-3,x+3,y+3), outline='yellow', width=2)
    candidates = estimate['patch']['candidates']
    if candidates:
        uv = project_base_points([c['position_base_m'] for c in candidates], view['intrinsics_K'], view['T_base_camera'])
        for x, y in uv:
            if np.isfinite([x,y]).all():
                d.point((int(round(x)),int(round(y))), fill='lime')
    w, h = raw.size
    panel = Image.new('RGB', (2*w,h+42), '#151515')
    panel.paste(raw, (0,42))
    panel.paste(overlay, (w,42))
    draw = ImageDraw.Draw(panel)
    draw.text((4,4), f"frame {row['input_index']} box{row['box_index']} native{ordinal} RAW | mask/BOX/POINT/proposals", fill='white')
    draw.text((4,20), f"{estimate['patch']['reason_codes']} proposals={len(candidates)}; NOT EXECUTABLE", fill='white')
    panel.save(out/f"frame-{row['input_index']:03d}-box-{row['box_index']}-native-{ordinal}.png")


def geometry(masks_root, output):
    verify_seal(masks_root)
    records = read(Path(masks_root)/'outputs.json')['records']
    masks_condition = read(Path(masks_root)/'condition.json')
    grounding = Path(masks_condition['grounding'])
    require(file_hash(grounding/'sealed.json') == masks_condition['grounding_seal_sha256'], 'grounding seal changed')
    admitted_sources = {content_hash(r) for r in input_rows(grounding)}
    require(all(content_hash(r['input_record']) in admitted_sources for r in records), 'mask input changed')
    cfg = config()
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write(out/'condition.json', dict(code=code_identity(), versions=versions(), masks=str(Path(masks_root).resolve()),
        masks_seal_sha256=file_hash(Path(masks_root)/'sealed.json'), geometry_config=cfg.to_dict(),
        measurement_contract='native-mask-depth/2', development_only=True, evaluation_labels_used=False, for_execution=False))
    results = []
    for record in records:
        row = dict(record, native_results=[])
        if record['status'] == 'COMPLETE':
            view, proprio = source_frame(record['input_record'])
            require(file_hash(record['artifact_uri']) == record['artifact_sha256'], 'mask artifact changed')
            with np.load(record['artifact_uri'], allow_pickle=False) as data:
                require(np.array_equal(data['masks'], data['logits'] > 0.) and len(data['masks']) == 3, 'native masks changed')
                for ordinal, native in enumerate(data['masks']):
                    binding = dict(source_identity=record['source_identity'], sensor_view_sha256=content_hash(record['source_identity']),
                        query=record['query'], box_index=record['box_index'], box_xyxy=record['box_xyxy'],
                        box_response_sha256=record['box_response_sha256'], mask_index=ordinal,
                        raw_mask_sha256=record['raw_mask_sha256'][ordinal], mask_artifact_uri=record['artifact_uri'],
                        mask_artifact_sha256=record['artifact_sha256'], coordinate_convention='top-left-origin-pixel-xyxy',
                        mask_input_channels=['rgb'], evaluation_labels_used=False, provenance='learned estimate')
                    start = time.perf_counter()
                    estimate = estimate_segmented_patch(view, record['box_xyxy'], native, mask_binding=binding, config=cfg,
                        track_id='drawer_front_pushable', feature_id=f"box-{record['box_index']}/mask-{ordinal}", seed=0,
                        eef_position_base_m=proprio['eef_position_base_m'], measurement_contract='native-mask-depth/2')
                    result = dict(ordinal=ordinal, estimate=estimate, geometry_s=time.perf_counter()-start,
                        stage_ledger=ledger(estimate['patch']), mask_point_admission=mask_point_admission(native, record['prompt_admission'], ordinal))
                    row['native_results'].append(result)
                    draw_native(view, record, native, estimate, ordinal, out)
        else:
            row['geometry_evaluation'] = 'NOT_EVALUATED'
        write(out/f"frame-{record['input_index']:03d}-box-{record['box_index']}.json", row)
        results.append(row)
        print('geometry', record['input_index'], [(n['ordinal'], len(n['estimate']['patch']['candidates'])) for n in row['native_results']], flush=True)
    write(out/'results.json', dict(records=results))
    seal(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['masks','geometry'])
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        globals()[args.stage](args.input, args.output)
    except Exception as exc:
        out = Path(args.output)
        if out.is_dir() and not (out/'failure.json').exists():
            write(out/'failure.json', dict(error=repr(exc), stage=args.stage, hidden_retry=False))
        raise


if __name__ == '__main__':
    main()
