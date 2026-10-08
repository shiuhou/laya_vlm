"""Offline automatic-mask hypotheses followed through original recorded RGB-D.

One tracker per admissible native mask, no winner and no automatic reacquisition.
Seed support is the original mask intersected with its original geometry ROI.
Subsequent geometry uses the observed tracked rectangle, an explicit distinct
measurement condition, not a reused or invented current-frame SAM mask.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
from itertools import chain
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require, thaw
from ..perception.recording import replay_frames
from ..perception.rgbd_geometry import _roi, estimate_visible_patch
from ..perception.semantic_prompt import grounding_point_prompt, mask_point_admission
from ..perception.surface_association import sensor_view_identity, tracker_seed_rectangle
from ..perception.visual_tracker import TrackerConfig, VisualTracker
from .p1_formal50 import ledger
from .p1_localizer_surface_dev import input_rows
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import code_identity, file_hash

CONDITION = "p1-automatic-native-patch-capture-clock-tracking/1"


@dataclass(frozen=True)
class _MaskSupport:
    # The existing rectangle algorithm consumes only observed support; no fake
    # plane centroid/normal or semantic identity is supplied for this adapter.
    support_mask: np.ndarray


def verified_geometry(root):
    """Authenticate the whole grounding -> masks -> geometry chain without labels."""
    root = Path(root)
    verify_seal(root)
    condition = read(root/'condition.json')
    require(condition['evaluation_labels_used'] is False and condition['for_execution'] is False,
            'offline sensor-derived geometry required', 'INFORMATION_BOUNDARY')
    require(condition['measurement_contract'] == 'native-mask-depth/2'
            and content_hash(condition['geometry_config']) == content_hash(config().to_dict()),
            'frozen geometry condition changed')
    masks_root = Path(condition['masks'])
    verify_seal(masks_root)
    require(file_hash(masks_root/'sealed.json') == condition['masks_seal_sha256'], 'mask seal changed')
    masks_condition = read(masks_root/'condition.json')
    grounding = Path(masks_condition['grounding'])
    require(file_hash(grounding/'sealed.json') == masks_condition['grounding_seal_sha256'],
            'grounding seal changed')
    source_records = {content_hash(r) for r in input_rows(grounding)}
    records, masks = read(root/'results.json')['records'], read(masks_root/'outputs.json')['records']
    require(len(records) == len(masks), 'geometry/mask slots differ')
    for record, mask in zip(records, masks):
        require(all(record.get(k) == v for k, v in mask.items())
                and content_hash(record['input_record']) in source_records,
                'geometry receipt changed', 'SOURCE_MISMATCH')
        if record['status'] == 'COMPLETE':
            path = Path(record['artifact_uri']).resolve()
            require(path.is_relative_to(masks_root.resolve()) and file_hash(path) == record['artifact_sha256'],
                    'native artifact changed', 'SOURCE_MISMATCH')
            require([n['ordinal'] for n in record['native_results']] == [0, 1, 2],
                    'all canonical native geometry required')
        else:
            require(not record['native_results'], 'upstream failure cannot acquire geometry')
    return records


def seed_hypotheses(records, view, *, tracker_config=TrackerConfig()):
    """Retain every original native rejection and every eligible seed hypothesis."""
    identity = sensor_view_identity(view)
    selected = [r for r in records if r['source_identity'] == identity]
    require(bool(selected), 'grounding must match the first recorded camera frame exactly', 'SOURCE_MISMATCH')
    hypotheses, decisions = [], []
    cfg = config()
    for record in selected:
        common = dict(input_index=record['input_index'], box_index=record['box_index'],
            source_identity=identity, query=record['query'], native_mask_ordinal=None,
            seed_status='NOT_EVALUATED', first_boundary=record.get('failure_stage'))
        if record['status'] != 'COMPLETE':
            decisions.append(common)
            continue
        point = record['input_record']['point_observation']
        prompt = grounding_point_prompt(view, record['box_xyxy'], point, query=record['query'],
            target_key=record['input_record']['box_observation']['target_key'], config=cfg)
        require(prompt == record['prompt_admission'] and prompt['admitted'], 'POINT admission receipt changed')
        require(file_hash(record['artifact_uri']) == record['artifact_sha256'], 'native artifact changed')
        with np.load(record['artifact_uri'], allow_pickle=False) as data:
            masks = data['masks']
            require(masks.dtype == bool and masks.shape == (3, *view['depth_m'].shape)
                    and np.array_equal(masks, data['logits'] > 0), 'native masks changed')
            require([n['ordinal'] for n in record['native_results']] == [0, 1, 2], 'missing native result')
            for native_result, native in zip(record['native_results'], masks):
                ordinal = native_result['ordinal']
                raw_hash = hashlib.sha256(native.tobytes()).hexdigest()
                require(raw_hash == record['raw_mask_sha256'][ordinal], 'native mask hash changed')
                estimate = native_result['estimate']
                binding = estimate['mask_binding']
                require(estimate['source_identity'] == identity and binding['source_identity'] == identity
                        and binding['raw_mask_sha256'] == raw_hash and binding['mask_index'] == ordinal
                        and binding['box_index'] == record['box_index']
                        and binding['box_xyxy'] == record['box_xyxy']
                        and binding['box_response_sha256'] == record['box_response_sha256']
                        and binding['evaluation_labels_used'] is False,
                        'geometry/native binding differs', 'SOURCE_MISMATCH')
                admission = mask_point_admission(native, prompt, ordinal)
                require(admission == native_result['mask_point_admission'], 'mask POINT admission changed')
                patch = estimate['patch']
                row = dict(common, native_mask_ordinal=ordinal, raw_mask_sha256=raw_hash,
                    mask_point_admission=admission, initial_geometry_status=patch['geometry_status'],
                    initial_geometry_reasons=patch['reason_codes'],
                    initial_candidate_count=len(patch['candidates']), seed_status='REJECTED')
                if not admission['admitted']:
                    row['first_boundary'] = 'POINT_MASK_CONTRADICTION'
                elif patch['geometry_status'] != 'VALID' or not patch['candidates']:
                    row['first_boundary'] = 'NO_INITIAL_GEOMETRY_CANDIDATE'
                else:
                    x0, y0, x1, y1 = _roi(record['box_xyxy'], native.shape[1], native.shape[0])
                    support = np.zeros_like(native)
                    support[y0:y1, x0:x1] = native[y0:y1, x0:x1]
                    rectangle = tracker_seed_rectangle(_MaskSupport(support), prompt['point_xy'],
                                                       tracker_config=tracker_config)
                    row.update(seed_support_domain='native_mask_intersection_original_geometry_roi',
                        seed_support_sha256=hashlib.sha256(support.tobytes()).hexdigest(),
                        seed_support_pixels=int(support.sum()), original_geometry_roi=[x0, y0, x1, y1],
                        seed_rectangle_xyxy_px=rectangle)
                    if rectangle is None:
                        row['first_boundary'] = 'NO_SUPPORTED_TRACKER_SEED_RECTANGLE'
                    else:
                        key = f"box-{record['box_index']}/native-{ordinal}"
                        row.update(seed_status='ELIGIBLE_HYPOTHESIS', first_boundary=None, hypothesis_id=key)
                        hypotheses.append(dict(row))
                decisions.append(row)
    require(len({h['hypothesis_id'] for h in hypotheses}) == len(hypotheses), 'duplicate native hypothesis')
    return hypotheses, decisions


def run(geometry_root, recording, output):
    """Replay original capture clocks once; no online freshness/Hz assertion."""
    records = verified_geometry(geometry_root)
    stream = iter(replay_frames(recording))
    first = next(stream, None)
    require(first is not None, 'empty recording')
    env, first_views = first
    views = [dict(v, frame_id=v['canonical_frame_id'], episode_id=env.episode_id) for v in first_views]
    matched = [v for v in views if any(r['source_identity'] == sensor_view_identity(v) for r in records)]
    require(len(matched) == 1, 'one exact first-frame camera grounding required', 'SOURCE_MISMATCH')
    source_view = matched[0]
    hypotheses, decisions = seed_hypotheses(records, source_view)
    tracker_config, geometry_config = TrackerConfig(), config()
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write(out/'condition.json', dict(condition=CONDITION, code=code_identity(),
        geometry_root=str(Path(geometry_root).resolve()), geometry_seal_sha256=file_hash(Path(geometry_root)/'sealed.json'),
        recording=str(Path(recording).resolve()), recording_frames_sha256=file_hash(Path(recording)/'frames.jsonl'),
        tracker_config=asdict(tracker_config), geometry_config=geometry_config.to_dict(),
        measurement_contract='tracked-support-rectangle/1', initial_mask_measurement_contract='native-mask-depth/2',
        source_identity=sensor_view_identity(source_view), processing_clock='offline_capture_clock_original_gaps',
        initial_grounding_latency_not_hidden_but_not_applied_to_offline_capture_clock=True,
        online_freshness_evaluated=False, continuous_end_to_end_hz_measured=False,
        reference_status='UNKNOWN', verify_status='UNKNOWN', automatic_reseed=False,
        evaluation_labels_used=False, oracle_inputs=False, robot_commands=0, for_execution=False))
    write(out/'seed-decisions.json', decisions)
    trackers = {h['hypothesis_id']: VisualTracker(env.episode_id, config=tracker_config,
        track_id='drawer_front_pushable/'+h['hypothesis_id'], feature_id='supported-visible-rectangle') for h in hypotheses}
    counts, first_boundaries, frames = Counter(), {}, 0
    try:
        with (out/'transitions.jsonl').open('x') as log:
            for envelope, bundle_views in chain([first], stream):
                require(envelope.episode_id == env.episode_id, 'episode changed during replay', 'SOURCE_MISMATCH')
                camera_views = [v for v in bundle_views if v['camera_id'] == source_view['camera_id']]
                require(len(camera_views) == 1, 'seed camera missing or duplicated')
                view = dict(camera_views[0], frame_id=camera_views[0]['canonical_frame_id'], episode_id=envelope.episode_id)
                for hypothesis in hypotheses:
                    key = hypothesis['hypothesis_id']
                    tracker = trackers[key]
                    start = time.perf_counter()
                    if frames == 0:
                        track = tracker.initialize(view, hypothesis['seed_rectangle_xyxy_px'], query=hypothesis['query'],
                            seed_source='semantic_query', now_sim_time_s=view['capture_sim_time_s'],
                            now_monotonic_ns=view['capture_monotonic_ns'])
                    else:
                        track = tracker.update(view, now_sim_time_s=view['capture_sim_time_s'],
                                               now_monotonic_ns=view['capture_monotonic_ns'])
                    tracker_s = time.perf_counter()-start
                    lineage = dict(episode_id=track.episode_id, track_id=track.track_id,
                        track_generation=track.track_generation, feature_id=track.feature_id,
                        feature_generation=track.feature_generation)
                    patch, geometry_s = None, None
                    if track.status == 'TRACKED':
                        start = time.perf_counter()
                        patch = estimate_visible_patch(view['depth_m'], view['intrinsics_K'], view['T_base_camera'],
                            roi_xyxy=track.roi_xyxy_px, source_frame_id=view['frame_id'],
                            calibration_version=view['calibration_version'], track_id=track.track_id,
                            feature_id=track.feature_id, capture_sim_time_s=view['capture_sim_time_s'],
                            capture_monotonic_ns=view['capture_monotonic_ns'], config=geometry_config, seed=0,
                            eef_position_base_m=envelope.payload['proprio']['eef_position_base_m']).to_dict()
                        geometry_s = time.perf_counter()-start
                    boundary = (track.reason_codes[0] if track.status != 'TRACKED' else
                                patch['reason_codes'][0] if patch['reason_codes'] else
                                'NO_GEOMETRY_CANDIDATE' if not patch['candidates'] else None)
                    if boundary is not None:
                        first_boundaries.setdefault(key, dict(frame_id=view['frame_id'], reason=boundary))
                    stages = ledger(patch) if patch is not None else None
                    if stages is not None:
                        stages['tracked_source_lineage_admission'] = stages.pop('semantic_source_admission')
                        stages['tracked_roi_depth_availability'] = stages.pop('mask_depth_availability')
                    row = dict(hypothesis_id=key, source_frame_id=view['frame_id'], source_identity=sensor_view_identity(view),
                        seed_event=frames == 0, reseed_event=False, lineage=lineage, track=thaw(track),
                        patch=patch, stage_ledger=stages,
                        geometry_evaluation='EVALUATED' if patch is not None else 'NOT_EVALUATED',
                        first_boundary=boundary, tracker_s=tracker_s, geometry_s=geometry_s,
                        candidate_evidence_ids=[content_hash(dict(lineage=lineage, source_frame_id=view['frame_id'],
                            point_id=c['point_id'])) for c in patch['candidates']] if patch is not None else [],
                        reference_status='UNKNOWN', verify_status='UNKNOWN', for_execution=False)
                    log.write(canonical_json(row)+'\n')
                    counts[key+'/'+track.status] += 1
                if not hypotheses:
                    log.write(canonical_json(dict(source_frame_id=view['frame_id'], track_status='UNSEEDED',
                        geometry_evaluation='NOT_EVALUATED', first_boundary='NO_ELIGIBLE_AUTOMATIC_SEED',
                        reference_status='UNKNOWN', verify_status='UNKNOWN', for_execution=False))+'\n')
                log.flush()
                frames += 1
        summary = dict(frames=frames, hypotheses=len(hypotheses), native_seed_decisions=len(decisions),
            track_counts=dict(counts), first_boundaries=first_boundaries, reseed_events=0,
            reference_status='UNKNOWN', verify_status='UNKNOWN', case_coverage_validated=False,
            online_freshness_evaluated=False, continuous_end_to_end_hz_measured=False,
            semantic_identity_verified=False, p1_pass_claimed=False, for_execution=False)
        write(out/'summary.json', summary)
        seal(out)
        return summary
    except Exception as exc:
        write(out/'failure.json', dict(error=repr(exc), completed_frames=frames, hidden_retry=False))
        seal(out)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', required=True)
    parser.add_argument('--recording', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.geometry, args.recording, args.output)


if __name__ == '__main__':
    main()
