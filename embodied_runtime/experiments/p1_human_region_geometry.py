"""Offline human-region support counterfactual. Never perception/runtime evidence."""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import time
import numpy as np
from ..contracts import content_hash, require
from ..perception.evaluation_annotations import image_binding
from ..perception.recording import project_base_points
from ..perception.rgbd_geometry import estimate_visible_patch
from ..perception.surface_association import sensor_view_identity
from .p1_formal50 import frames, ledger, registration as source_registration
from .p1_formal50_scoring import polygon_mask, _percentiles
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import code_identity, file_hash, versions

CONDITION = 'p1-human-region-geometry-upper-bound/1'
BASELINE = Path('runs/p1/identity-point-sam-20261007')
PROTOCOL = Path('docs/research/p1_human_region_geometry_protocol.md')


def registration(root):
    root = Path(root)
    r = read(root/'registration.json')
    require(content_hash({k:v for k,v in r.items() if k != 'registration_content_sha256'})
            == r['registration_content_sha256'], 'registration changed')
    require(r['condition'] == CONDITION and r['for_execution'] is False
            and r['perception_acceptance'] is False and r['evaluation_labels_used'] is True,
            'explicit offline human-support condition required')
    require(content_hash(config().to_dict()) == content_hash(r['geometry_config']), 'geometry config changed')
    for path,digest in r['source_files_sha256'].items():
        require(file_hash(path) == digest, 'registered source changed', 'SOURCE_MISMATCH')
    require([row['image']['init_index'] for row in r['inputs']] == list(range(25))
            and all(row['image']['camera_id'] == 'robot0_eye_in_hand'
                    and row['human_status'] == 'VISIBLE' for row in r['inputs']),
            'complete canonical wrist25 required')
    verify_seal(root/'inputs')
    return r


def prepare(output):
    b = source_registration(BASELINE)
    for stage in ('points','masks','geometry','scoring','point-review'):
        verify_seal(BASELINE/stage)
    entry = b['entry']
    code = code_identity()
    require(code['dirty_status'] == '', 'freeze diagnostic before evaluation')
    require(file_hash(entry['annotation_path']) == entry['annotation_sha256']
            and file_hash(entry['annotation_seal_path']) == entry['annotation_seal_sha256'],
            'frozen human annotation changed')
    labels = read(entry['annotation_path'])
    require(labels['rules_version'] == 'p1-rgb-annotation-rules/2'
            and labels['rules_sha256'] == entry['rules_sha256'], 'annotation rules differ')
    by_id = {x['image_id']:x for x in labels['annotations']}
    require(len(by_id) == 50, 'original annotation coverage changed')
    sensor = frames(entry)
    root = Path(output); root.mkdir(parents=True, exist_ok=False)
    inputs = root/'inputs'; inputs.mkdir(exist_ok=False)
    selected = []
    for source_row in b['inputs']:
        image = source_row['image']
        if image['camera_id'] != 'robot0_eye_in_hand':
            continue
        annotation = by_id[image['image_id']]
        require(image_binding(annotation) == image_binding(image), 'annotation/frame mismatch')
        truth = annotation['entities']['drawer_front_pushable']
        require(truth['status'] == 'VISIBLE', 'every frozen wrist frame must remain VISIBLE')
        view,_ = sensor[image['frame_id']]
        require(sensor_view_identity(view) == source_row['source_identity'], 'sensor changed')
        mask = polygon_mask(image, truth)  # Frozen half-pixel evaluator convention.
        require(mask.dtype == bool and mask.any(), 'nonempty original human region required')
        path = inputs/f'init-{image["init_index"]:03d}-human-support.npy'
        np.save(path,mask,allow_pickle=False)
        selected.append(dict(input_index=len(selected),original_formal50_index=source_row['input_index'],
            image=image,source_identity=source_row['source_identity'],human_status=truth['status'],
            human_polygons=truth['polygons'],mask_uri=str(path.absolute()),mask_sha256=file_hash(path),
            mask_raw_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),human_region_pixels=int(mask.sum()),
            support_provenance='frozen human annotation: offline target-support counterfactual',
            evaluation_labels_used=True,for_execution=False))
    seal(inputs)
    paths = [Path(p) for p in code['source_sha256']] + [PROTOCOL,Path(entry['annotation_path']),
        Path(entry['annotation_seal_path']),Path(entry['rules_path']),BASELINE/'registration.json',
        BASELINE/'scoring/sealed.json']
    sources = dict(b['source_files_sha256'])
    sources.update({str(p.absolute()):file_hash(p) for p in paths})
    r = dict(condition=CONDITION,baseline_checkpoint='e8cda1e0eaf0c90fc8a5d1ed3d1d57d445c266d3',
        source_baseline_root=str(BASELINE.absolute()),code=code,entry=entry,inputs=selected,
        source_files_sha256=sources,geometry_config=config().to_dict(),seed=0,
        registered_at_utc=datetime.now(timezone.utc).isoformat(),
        rasterization='frozen polygon_mask: pixel centres x+.5,y+.5; polygon union; no morphology',
        ROI='full original frame with depth outside human region UNKNOWN; no model BOX clipping',
        depth_availability='valid_depth_inside_human_region / human_region_pixels',
        input_intervention='human region replaces learned semantic/segmentation support; original sensor samples preserved inside',
        decision_rule='13 or more of25 frames with >=1 raw geometry candidate: semantic identity repair priority; otherwise geometry/tool/viewpoint repair priority. Neither is P1 acceptance.',
        systemic_NO_TOOL_rule='report all25 fraction and conditional fraction among frames reaching candidate gates; >=13/25 is global majority, not a physical impossibility proof',
        process_environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        evaluation_labels_used=True,development_only=True,independent_heldout=False,
        perception_acceptance=False,for_execution=False,feasibility_callback=None,
        new_model_calls=0,tracker_calls=0,controls=0,Qwen_calls=0,Laya_calls=0,
        failure_rule='one evaluation per frozen wrist frame; runtime error stops, no retry/tuning')
    r['registration_content_sha256'] = content_hash(r)
    write(root/'registration.json',r)
    registration(root)


def frame_report(patch):
    m = patch['metrics']
    stages = ledger(patch)
    stages.pop('semantic_source_admission')
    stages['human_region_support'] = 'SUPPLIED_FOR_OFFLINE_UPPER_BOUND'
    return dict(first_rejection=patch['reason_codes'][0] if patch['reason_codes'] else None,
        geometry_status=patch['geometry_status'],tool_interior_candidate_count=len(patch['candidates']),
        component_sizes=m.get('component_sizes'),selected_component_count=m.get('selected_component_count'),
        fitted_point_count=m.get('fitted_point_count'),plane_support_ratio=m.get('plane_support_ratio'),
        plane_rms_m=m.get('plane_rms_m'),tangent_spread_m=m.get('tangent_spread_m'),
        boundary_point_count=m.get('boundary_point_count'),position_sigma_m=m.get('position_sigma_m'),
        erosion_m=m.get('erosion_m'),eroded_support_count=m.get('eroded_support_count'),
        sampling_margin_m=m.get('sampling_margin_m'),grid_cell_count=m.get('grid_cell_count'),
        candidate_rejection_counts=m.get('candidate_rejection_counts'),fit_support=m.get('fit_support'),
        stage_ledger=stages,uncertainty_calibrated=m['uncertainty_calibrated'],for_execution=False)


def evaluate(output):
    root=Path(output); r=registration(root)
    expected=r['process_environment']
    require(all(os.environ.get(k)==v for k,v in expected.items()), 'CPU thread environment differs')
    out=root/'geometry';out.mkdir(exist_ok=False)
    write(out/'condition.json',dict(registration_sha256=file_hash(root/'registration.json'),
        code=code_identity(),versions=versions(),executable=sys.executable,prefix=sys.prefix,
        pid=os.getpid(),process_environment=expected,geometry_config=config().to_dict(),
        evaluation_labels_used=True,perception_acceptance=False,for_execution=False))
    rows=[]; cfg=config(); sensor=frames(r['entry'])
    try:
        for row in r['inputs']:
            image=row['image'];view,proprio=sensor[image['frame_id']]
            require(sensor_view_identity(view)==row['source_identity'], 'source sensor changed')
            require(file_hash(row['mask_uri'])==row['mask_sha256'], 'human mask changed')
            mask=np.load(row['mask_uri'],allow_pickle=False)
            require(mask.dtype==bool and mask.shape==view['depth_m'].shape
                    and hashlib.sha256(mask.tobytes()).hexdigest()==row['mask_raw_sha256'], 'mask source changed')
            depth=view['depth_m']; valid=mask & np.isfinite(depth) & (depth>=cfg.min_depth_m) & (depth<=cfg.max_depth_m)
            masked=depth.copy();masked[~mask]=np.nan;masked.setflags(write=False)
            start=time.perf_counter()
            patch=estimate_visible_patch(masked,view['intrinsics_K'],view['T_base_camera'],
                roi_xyxy=[0,0,image['width'],image['height']],source_frame_id=row['source_identity']['frame_id'],
                calibration_version=view['calibration_version'],track_id='offline-human-front-upper-bound',
                feature_id='frozen-human-region',capture_sim_time_s=view['capture_sim_time_s'],
                capture_monotonic_ns=view['capture_monotonic_ns'],config=cfg,seed=0,
                eef_position_base_m=proprio['eef_position_base_m'],depth_availability_mask=mask).to_dict()
            elapsed=time.perf_counter()-start
            report=frame_report(patch)
            require(patch['metrics']['valid_depth_inside_mask']==int(valid.sum()), 'depth support accounting mismatch')
            uv=project_base_points([p['position_base_m'] for p in patch['candidates']],view['intrinsics_K'],view['T_base_camera']) if patch['candidates'] else []
            from ..perception.evaluation_annotations import _inside
            candidates_inside=[bool(x) for x in _inside(np.asarray(uv),row['human_polygons'])] if len(uv) else []
            result=dict(**row,human_region_valid_depth_count=int(valid.sum()),
                human_region_depth_availability=float(valid.sum()/mask.sum()),
                original_sensor_depth_sha256=row['source_identity']['depth_sha256'],
                derived_masked_depth_sha256=hashlib.sha256(masked.tobytes()).hexdigest(),
                derived_depth_provenance='sensor depth restricted by human evaluation annotation; offline counterfactual',
                patch=patch,report=report,geometry_s=elapsed,candidate_image_xy=np.asarray(uv).tolist(),
                candidate_inside_original_human_polygon=candidates_inside,
                calibrated_confidence=None,perception_acceptance=False)
            write(out/f'init-{image["init_index"]:03d}.json',result);rows.append(result)
            print(f'upper-bound init{image["init_index"]}: {report["first_rejection"] or "CANDIDATES"}; n={len(patch["candidates"])}',flush=True)
        write(out/'results.json',rows)
    except Exception as exc:
        write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False));seal(out);raise
    seal(out)
    candidate_frames=sum(x['report']['tool_interior_candidate_count']>0 for x in rows)
    reached=sum(x['report']['stage_ledger']['tool_candidate_gates']!='NOT_EVALUATED' for x in rows)
    no_tool=sum(x['report']['first_rejection']=='NO_TOOL_INTERIOR_CANDIDATE' for x in rows)
    summary=dict(condition=CONDITION,frame_denominator=25,frames_with_geometry_candidates=candidate_frames,
        geometry_candidate_count=sum(len(x['patch']['candidates']) for x in rows),
        outside_human_polygon_candidates=sum(sum(y is False for y in x['candidate_inside_original_human_polygon']) for x in rows),
        first_boundary_counts=dict(Counter(x['report']['first_rejection'] or 'CANDIDATES' for x in rows)),
        tool_candidate_gate_reached_frames=reached,NO_TOOL_INTERIOR_CANDIDATE_frames=no_tool,
        NO_TOOL_all_frame_fraction=no_tool/25,NO_TOOL_reached_fraction=no_tool/reached if reached else None,
        priority='semantic identity repair on new held-out frames' if candidate_frames>=13 else 'geometry/tool/viewpoint repair; deprioritize semantic model',
        geometry_timing=_percentiles([x['geometry_s'] for x in rows]),
        P1_acceptance=False,perception_acceptance=False,independent_heldout=False,for_execution=False,
        reference_VERIFY='UNKNOWN',next_experiment_executed=False,model_calls=0,controls=0,
        note='Human support counterfactual, not a mathematical upper bound on every method or proof of physical impossibility')
    scoring=root/'summary';scoring.mkdir(exist_ok=False);write(scoring/'results.json',summary)
    fields=['init_index','human_region_pixels','valid_depth_count','depth_availability','first_rejection',
        'component_sizes','selected_component_count','fitted_point_count','plane_support_ratio','plane_rms_m',
        'boundary_point_count','position_sigma_m','erosion_m','eroded_support_count','sampling_margin_m',
        'grid_cell_count','candidate_rejection_counts','tool_interior_candidate_count']
    with (scoring/'all25.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for x in rows:
            flat={k:x['report'].get(k) for k in fields}
            flat.update(init_index=x['image']['init_index'],human_region_pixels=x['human_region_pixels'],
                valid_depth_count=x['human_region_valid_depth_count'],depth_availability=x['human_region_depth_availability'])
            writer.writerow(flat)
    seal(scoring)
    print(summary,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','evaluate']);parser.add_argument('--output',required=True)
    args=parser.parse_args();{'prepare':prepare,'evaluate':evaluate}[args.stage](args.output)

if __name__=='__main__':main()
