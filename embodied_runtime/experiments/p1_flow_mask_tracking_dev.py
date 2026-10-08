"""Replay automatic native supports with sparse RGB-D flow and fresh geometry.

This is recorded-source development, not a live freshness or execution claim.
Every eligible native mask has its own lineage; no mask winner is selected.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
from itertools import chain
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.recording import replay_frames, project_base_points
from ..perception.tracked_mask_geometry import fresh_mask_geometry
from ..perception.semantic_prompt import grounding_point_prompt, mask_point_admission
from ..perception.surface_association import sensor_view_identity
from ..perception.opencv_receipt import opencv_process_receipt
from .p1_automatic_patch_tracking import verified_geometry
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import seal, write
from .records import code_identity, file_hash, versions


def native_seeds(records, view):
    """Authenticate eligible masks without asking a rectangle tracker to seed."""
    source = sensor_view_identity(view)
    matched = [r for r in records if r['source_identity'] == source]
    require(matched, 'exact first-frame source required', 'SOURCE_MISMATCH')
    seeds, decisions = [], []
    for r in matched:
        base = dict(input_index=r['input_index'], box_index=r['box_index'], source_identity=source,
                    native_mask_ordinal=None, admitted=False, reason=r.get('failure_stage'))
        if r['status'] != 'COMPLETE':
            decisions.append(base)
            continue
        prompt = grounding_point_prompt(view, r['box_xyxy'], r['input_record']['point_observation'],
            query=r['query'], target_key=r['input_record']['box_observation']['target_key'], config=config())
        require(prompt == r['prompt_admission'] and prompt['admitted'], 'POINT source admission changed')
        require(file_hash(r['artifact_uri']) == r['artifact_sha256'], 'native mask artifact changed')
        with np.load(r['artifact_uri'], allow_pickle=False) as data:
            require(np.array_equal(data['masks'], data['logits'] > 0), 'native mask changed')
            for n, mask in zip(r['native_results'], data['masks']):
                ordinal = n['ordinal']
                digest = hashlib.sha256(mask.tobytes()).hexdigest()
                require(digest == r['raw_mask_sha256'][ordinal], 'native mask hash changed')
                admission = mask_point_admission(mask, prompt, ordinal)
                require(admission == n['mask_point_admission'], 'mask point admission changed')
                patch = n['estimate']['patch']
                accepted = admission['admitted'] and patch['geometry_status'] == 'VALID' and bool(patch['candidates'])
                row = dict(base, native_mask_ordinal=ordinal, admitted=accepted,
                    reason=None if accepted else 'POINT_MASK_CONTRADICTION' if not admission['admitted'] else 'NO_INITIAL_GEOMETRY_CANDIDATE',
                    original_geometry_reasons=patch['reason_codes'], original_candidates=len(patch['candidates']),
                    native_mask_sha256=digest, box_xyxy=r['box_xyxy'], query=r['query'],
                    hypothesis_id=f"box-{r['box_index']}/native-{ordinal}")
                decisions.append(row)
                if accepted:
                    seeds.append(dict(row, mask=mask.copy()))
    return seeds, decisions


def fresh_geometry(view, support, roi, proprio, key):
    """One measurement from CURRENT depth, with an explicitly tracked domain."""
    return fresh_mask_geometry(view,support,roi,geometry_config=config(),
        track_id='drawer_front_pushable/'+key, feature_id='flow-native-support',
        eef_position_base_m=proprio['eef_position_base_m'])


def review_panel(view, rows):
    from PIL import Image, ImageDraw
    w, h = view['rgb'].shape[1], view['rgb'].shape[0]
    panel = Image.new('RGB', (w*(len(rows)+1), h+54), '#171717')
    panel.paste(Image.fromarray(view['rgb']), (0, 54))
    draw = ImageDraw.Draw(panel)
    draw.text((4, 4), f"RAW source frame {view['frame_seq']} | HOLD recording; offline flow; NOT EXECUTABLE", fill='white')
    for i, (row, support) in enumerate(rows):
        rgb = np.array(view['rgb']).copy()
        if support is not None:
            rgb[support] = (rgb[support]*.7 + np.array([60, 120, 255])*.3).astype(np.uint8)
        img = Image.fromarray(rgb)
        ink = ImageDraw.Draw(img)
        if row['patch'] and row['patch']['candidates']:
            pts = project_base_points([c['position_base_m'] for c in row['patch']['candidates']], view['intrinsics_K'], view['T_base_camera'])
            for x, y in pts:
                if np.isfinite([x, y]).all():
                    ink.point((round(x), round(y)), fill='lime')
        offset = (i+1)*w
        panel.paste(img, (offset, 54))
        draw.text((offset+4, 18), f"{row['hypothesis_id']} {row['track']['status']}", fill='white')
        draw.text((offset+4, 34), str(row['first_boundary'] or 'geometry candidates'), fill='white')
    return panel


def run(geometry_root, recording, output):
    import cv2
    from ..perception.sparse_mask_tracker import FlowTrackerConfig, SparseMaskTracker
    # Fixed CPU scheduling condition, avoiding the host's 256-thread default.
    cv2.setNumThreads(1)
    records = verified_geometry(geometry_root)
    stream = iter(replay_frames(recording))
    first = next(stream, None)
    require(first is not None, 'empty recording')
    envelope, views = first
    matching = [dict(v, frame_id=v['canonical_frame_id'], episode_id=envelope.episode_id) for v in views
                if any(sensor_view_identity(v) == r['source_identity'] for r in records)]
    require(len(matching) == 1, 'one exact source camera required', 'SOURCE_MISMATCH')
    source_view = matching[0]
    seeds, decisions = native_seeds(records, source_view)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    (out/'support-masks').mkdir()
    cfg = FlowTrackerConfig()
    write(out/'condition.json', dict(condition='p1-sparse-flow-native-support-development/1', code=code_identity(), versions=versions(),
        geometry_root=str(Path(geometry_root).resolve()), geometry_seal_sha256=file_hash(Path(geometry_root)/'sealed.json'),
        recording=str(Path(recording).resolve()), recording_frames_sha256=file_hash(Path(recording)/'frames.jsonl'),
        flow_config=asdict(cfg), geometry_config=config().to_dict(), measurement_contract='tracked-native-support/1',
        opencv_process=opencv_process_receipt(), opencv_threads_explicit=1,
        source_identity=sensor_view_identity(source_view), processing_clock='offline_capture_clock_original_gaps',
        online_freshness_evaluated=False, continuous_end_to_end_hz_measured=False,
        evaluation_labels_used=False, oracle_inputs=False, robot_commands=0, for_execution=False))
    write(out/'seed-decisions.json', decisions)
    trackers = {s['hypothesis_id']: SparseMaskTracker(envelope.episode_id, config=cfg, track_id=s['hypothesis_id']) for s in seeds}
    counts, boundaries, panels, clocks, timings = Counter(), {}, [], [], []
    frames = 0
    try:
        with (out/'transitions.jsonl').open('x') as log:
            for env, bundle in chain([first], stream):
                require(env.episode_id == envelope.episode_id, 'episode changed', 'SOURCE_MISMATCH')
                matched = [v for v in bundle if v['camera_id'] == source_view['camera_id']]
                require(len(matched) == 1, 'one source camera required')
                view = dict(matched[0], frame_id=matched[0]['canonical_frame_id'], episode_id=env.episode_id)
                displays = []
                for s in seeds:
                    key, tracker = s['hypothesis_id'], trackers[s['hypothesis_id']]
                    start = time.perf_counter()
                    now = dict(now_sim_time_s=view['capture_sim_time_s'], now_monotonic_ns=view['capture_monotonic_ns'])
                    if frames == 0:
                        result = tracker.initialize(view, s['mask'], s['box_xyxy'],
                            source_identity_sha256=content_hash(s['source_identity']), native_mask_sha256=s['native_mask_sha256'],
                            native_mask_ordinal=s['native_mask_ordinal'], **now)
                    else:
                        result = tracker.update(view, **now)
                    flow_s = time.perf_counter()-start
                    patch, geometry_s = None, None
                    if result.status == 'TRACKED':
                        start = time.perf_counter()
                        patch = fresh_geometry(view, result.support_mask, result.current_roi_xyxy_px, env.payload['proprio'], key)
                        geometry_s = time.perf_counter()-start
                    boundary = (result.reason_codes[0] if result.status != 'TRACKED' else
                                patch['reason_codes'][0] if patch['reason_codes'] else
                                'NO_GEOMETRY_CANDIDATE' if not patch['candidates'] else None)
                    if boundary:
                        boundaries.setdefault(key, dict(frame_id=view['frame_id'], reason=boundary))
                    artifact = None
                    if result.support_mask is not None:
                        path = out/'support-masks'/f"frame-{frames:04d}-{key.replace('/', '-')}.npz"
                        np.savez_compressed(path, support_mask=result.support_mask)
                        artifact = dict(uri=str(path.resolve()), sha256=file_hash(path))
                    row = dict(hypothesis_id=key, source_identity=sensor_view_identity(view), track=result.to_dict(), patch=patch,
                        support_mask_artifact=artifact,
                        first_boundary=boundary, flow_s=flow_s, geometry_s=geometry_s, seed_event=frames == 0,
                        geometry_evaluation='EVALUATED' if patch is not None else 'NOT_EVALUATED',
                        candidate_evidence_ids=[] if patch is None else [f"{view['frame_id']}/{key}/generation-{result.track_generation}/{c['point_id']}" for c in patch['candidates']],
                        reference_status='UNKNOWN', verify_status='UNKNOWN', for_execution=False)
                    log.write(canonical_json(row)+'\n')
                    counts[key+'/'+result.status] += 1
                    if patch and patch['candidates']:
                        counts[key+'/WITH_GEOMETRY_CANDIDATES'] += 1
                    timings.append(dict(flow_s=flow_s, geometry_s=geometry_s))
                    displays.append((row, result.support_mask))
                log.flush()
                panels.append(review_panel(view, displays))
                clocks.append(view['capture_monotonic_ns'])
                frames += 1
        stats = {}
        for field in ('flow_s', 'geometry_s'):
            values = [t[field] for t in timings if t[field] is not None]
            stats[field] = dict(count=len(values), p50=float(np.percentile(values, 50)), p95=float(np.percentile(values, 95))) if values else None
        summary = dict(frames=frames, hypotheses=len(seeds), counts=dict(counts), first_boundaries=boundaries,
            timings=stats, online_freshness_evaluated=False, continuous_end_to_end_hz_measured=False,
            evaluation_labels_used=False, independent_heldout=False, p1_pass_claimed=False,
            reference_status='UNKNOWN', verify_status='UNKNOWN', for_execution=False)
        write(out/'summary.json', summary)
        if panels:
            gaps = np.diff(clocks)/1e6
            durations = [max(1, round(float(x))) for x in gaps] + [max(1, round(float(np.median(gaps)))) if len(gaps) else 100]
            panels[0].save(out/'tracked-support.gif', save_all=True, append_images=panels[1:], duration=durations, loop=0)
            for index in sorted({0, len(panels)//2, len(panels)-1}):
                panels[index].save(out/f'review-frame-{index:03d}.png')
        seal(out)
        return summary
    except Exception as exc:
        write(out/'failure.json', dict(error=repr(exc), frames_completed=frames, hidden_retry=False))
        seal(out)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry', required=True)
    p.add_argument('--recording', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    run(a.geometry, a.recording, a.output)


if __name__ == '__main__':
    main()
