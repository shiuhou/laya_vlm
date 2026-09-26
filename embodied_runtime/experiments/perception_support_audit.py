"""CPU-only raw-frame support audit; oracle masks are evaluator-only.

This does not change perception, correct sensor supports, or run a policy.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from ..vision import camera_to_world, pixel_to_camera, robust_depth
from .records import code_identity, file_hash, load_records
from .target_referent import (
    _restore_support,
    audit_referent_run,
    bbox_mask,
    surface_centroid,
)


def median_proxy(depth, box, intrinsics, transform):
    """Exact live first-box estimator, no evaluator access.

    Box edges are continuous boundary coordinates. Their midpoint already has
    the same convention as raster centers u+.5,v+.5; do not add another .5.
    """
    box = tuple(int(v) for v in box)
    z, _ = robust_depth(depth, box)
    if z is None:
        return None
    u, v = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return camera_to_world(pixel_to_camera(u, v, z, intrinsics), transform).tolist()


def support_diagnostic(depth, box, intrinsics, transform, oracle_mask, ray_depths):
    """Evaluate separate sensor outputs; never return a corrected estimate."""
    sensor_mask = bbox_mask(depth.shape, box)
    sensor = surface_centroid(depth, sensor_mask, intrinsics, transform)
    proxy = median_proxy(depth, box, intrinsics, transform)
    evaluated = surface_centroid(depth, oracle_mask, intrinsics, transform)
    ray = np.full(depth.shape, np.nan)
    ray[oracle_mask] = ray_depths
    oracle = surface_centroid(ray, oracle_mask, intrinsics, transform)
    s, e, o = (x['position_world_m'] for x in (sensor, evaluated, oracle))
    result = {'sensor_centroid_m': s, 'median_proxy_m': proxy, 'oracle_centroid_m': o,
              'sensor_pixels': int(sensor_mask.sum()), 'oracle_pixels': int(oracle_mask.sum()),
              'intersection_pixels': int((sensor_mask & oracle_mask).sum()),
              'sensor_valid_pixels': sensor['valid_pixel_count'],
              'sensor_estimator_uses_oracle': False,
              'median_to_surface_distance_is_accuracy': False}
    for name, a, b in [('centroid_error_mm', s, o), ('proxy_to_surface_distance_mm', proxy, o),
                       ('support_component_mm', s, e), ('ray_depth_component_mm', e, o)]:
        result[name] = None if a is None or b is None else float(np.linalg.norm(np.asarray(a)-b)*1000)
    if s is not None and e is not None and o is not None:
        support = np.asarray(s)-e
        depth_delta = np.asarray(e)-o
        result['support_delta_mm'] = (support*1000).tolist()
        result['ray_depth_delta_mm'] = (depth_delta*1000).tolist()
        result['vector_decomposition_residual_mm'] = float(np.linalg.norm((np.asarray(s)-o)-support-depth_delta)*1000)
    else:
        result['vector_decomposition_residual_mm'] = None
    result['purity'] = result['intersection_pixels']/result['sensor_pixels'] if result['sensor_pixels'] else None
    return result


def audit_run(path):
    path = Path(path)
    verified = audit_referent_run(path)
    records, diagnostics = load_records(path/'episodes.jsonl')
    if diagnostics:
        raise ValueError(f'raw record errors: {diagnostics}')
    captures = {r['data']['capture_seq']: r for r in records if r['kind']=='vision_capture'}
    completed = {r['data']['capture_seq']: r for r in records if r['kind']=='vision_completed'}
    pairs = {r['data']['physical']['physical_state_id']: r for r in records if r['kind']=='paired_state'}
    checked = {r['capture_seq']: r for r in verified['rows']}
    result, missing = [], []
    for record in records:
        if record['kind'] != 'target_referent':
            continue
        data = record['data']
        seq = data['capture_seq']
        sensor = data['sensor']
        if sensor is None:
            missing.append({'run': path.name, 'capture_seq': seq, 'reason': 'no_sensor_support'})
            continue
        capture, completion = captures[seq], completed.get(seq)
        artifact = path/capture['data']['artifact']
        with np.load(artifact) as frame:
            oracle_mask = _restore_support(data['oracle'], frame['depth_m'].shape)
            row = support_diagnostic(frame['depth_m'], sensor['box_xyxy'], frame['intrinsics'],
                                     frame['camera_to_world'], oracle_mask, data['oracle']['selected_depths_m'])
        # Existing raw audit independently enforces exact centroid/raycast/support reproduction.
        row.update(checked[seq])
        pair = pairs.get(data['physical_state_id'])
        fields = pair['data']['perceptual_state']['fields'] if pair else {}
        raw_event = completion['data'].get('event') if completion else None
        recorded_proxy = raw_event['value'].get('position_world_m') if raw_event else None
        proxy_residual = (None if recorded_proxy is None or row['median_proxy_m'] is None else
                          float(np.linalg.norm(np.asarray(recorded_proxy)-row['median_proxy_m'])))
        if proxy_residual is not None and proxy_residual > 1e-12:
            raise ValueError('live median proxy does not reconstruct')
        row.update(run=path.name, frame_artifact=str(artifact), frame_sha256=file_hash(artifact),
                   capture_record_id=capture['record_id'], referent_record_id=record['record_id'],
                   capture_wall_time=capture['wall_time'], capture_sim_time=capture['data']['capture_sim_time'],
                   median_proxy_reproduction_residual_m=proxy_residual,
                   raw_covariance_source=raw_event['value'].get('position_covariance_source') if raw_event else None,
                   raw_covariance_calibrated=raw_event['value'].get('position_covariance_calibrated') if raw_event else None,
                   fused_covariance_calibrated=fields.get('quality.covariance_calibrated', {}).get('value'),
                   perception_wall_elapsed_s=completion['wall_time']-capture['wall_time'] if completion else None,
                   pair_wall_elapsed_s=pair['wall_time']-capture['wall_time'] if pair else None,
                   geometry_age_sim_s=fields.get('quality.geometry_age_s', {}).get('value'),
                   locateanything_score=completion['data']['result'].get('score') if completion else None,
                   returned_box_count=len(completion['data']['result'].get('boxes_xyxy', [])) if completion else None,
                   box_xyxy=sensor['box_xyxy'])
        result.append(row)
    return {'source': str(path), 'episodes_sha256': file_hash(path/'episodes.jsonl'),
            'manifest_sha256': file_hash(path/'manifest.json'), 'raw_log_diagnostics': diagnostics,
            'complete_collection': verified['complete_collection'], 'rows': result, 'missing': missing}


def summarize(runs):
    rows = [r for run in runs for r in run['rows']]
    summary = {'n': len(rows), 'missing': [r for run in runs for r in run['missing']]}
    for key in ('purity', 'centroid_error_mm', 'proxy_to_surface_distance_mm', 'support_component_mm',
                'ray_depth_component_mm', 'geometry_age_sim_s', 'perception_wall_elapsed_s',
                'pair_wall_elapsed_s', 'median_proxy_reproduction_residual_m',
                'sensor_centroid_reproduction_residual_m', 'oracle_centroid_reproduction_residual_m'):
        values = [r[key] for r in rows if r.get(key) is not None]
        summary[key] = {'n': len(values), 'min': min(values) if values else None,
                        'median': float(np.median(values)) if values else None, 'max': max(values) if values else None}
    comparable = [r for r in rows if r['purity'] is not None and r['centroid_error_mm'] is not None]
    summary['purity_error_pearson_descriptive_only'] = (float(np.corrcoef(
        [r['purity'] for r in comparable], [r['centroid_error_mm'] for r in comparable])[0, 1])
        if len(comparable)>1 and np.std([r['purity'] for r in comparable])>0 else None)
    summary['support_component_larger_than_ray_depth_n'] = sum(
        r['support_component_mm'] is not None and r['ray_depth_component_mm'] is not None
        and r['support_component_mm']>r['ray_depth_component_mm'] for r in rows)
    summary['uncalibrated_covariance_n'] = sum(r['raw_covariance_calibrated'] is False for r in rows)
    summary['frozen_sim_age_zero_n'] = sum(r['geometry_age_sim_s']==0 for r in rows)
    return summary


def render_diagnostics(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    # Deterministic representatives: best support, worst support, worst centroid error.
    indices = list(dict.fromkeys([max(range(len(rows)), key=lambda i: rows[i]['purity']),
                                 min(range(len(rows)), key=lambda i: rows[i]['purity']),
                                 max(range(len(rows)), key=lambda i: rows[i]['centroid_error_mm'])]))
    fig, axes = plt.subplots(len(indices), 2, figsize=(12, 5*len(indices)), squeeze=False)
    for slot, index in enumerate(indices):
        row = rows[index]
        records, _ = load_records(Path(row['frame_artifact']).parents[1]/'episodes.jsonl')
        ref = next(r['data'] for r in records if r['record_id']==row['referent_record_id'])
        with np.load(row['frame_artifact']) as frame:
            depth, rgb = frame['depth_m'], frame['rgb']
            mask = _restore_support(ref['oracle'], depth.shape)
            support = bbox_mask(depth.shape, row['box_xyxy'])
            overlay = rgb.astype(float)/255
            overlay[mask] = overlay[mask]*.45 + np.array([0, 1, 1])*.55
            axes[slot, 0].imshow(overlay)
            x1, y1, x2, y2 = row['box_xyxy']
            axes[slot, 0].add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, color='orange', linewidth=2))
            axes[slot, 0].set_title(f"{row['run']} step {row['environment_step']} | purity {row['purity']:.1%}\nOrange: sensor bbox; cyan: EVALUATOR-only oracle surface")
            axes[slot, 0].axis('off')
            # A 2D camera X/Z view retains all support points; colors are evaluator labels only.
            y, x = np.nonzero(support & np.isfinite(depth) & (depth>=.01) & (depth<=5))
            z = depth[y, x]
            camera_x = (x+.5-frame['intrinsics'][0, 2])*z/frame['intrinsics'][0, 0]
            member = mask[y, x]
            axes[slot, 1].scatter(camera_x[~member]*1000, z[~member]*1000, s=3, c='orange', label='bbox background/other')
            axes[slot, 1].scatter(camera_x[member]*1000, z[member]*1000, s=3, c='teal', label='bbox on true target')
            axes[slot, 1].set(xlabel='Camera X (mm)', ylabel='Optical depth Z (mm)',
                title=f"Raw bbox point cloud (no correction)\nCentroid error {row['centroid_error_mm']:.1f} mm; ray-depth residual {row['ray_depth_component_mm']:.2f} mm")
            axes[slot, 1].legend()
    fig.suptitle('ARCHIVED PERCEPTION DIAGNOSTIC / NO POLICY / ORACLE LABELS EVALUATOR ONLY')
    fig.tight_layout(rect=(0, 0, 1, .98))
    fig.savefig(output/'representative-supports.png', dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for init in sorted(set(r['init_state_id'] for r in rows)):
        subset = [r for r in rows if r['init_state_id']==init]
        axes[0].scatter([100*r['purity'] for r in subset], [r['centroid_error_mm'] for r in subset], label=f'init {init}')
    axes[0].set(xlabel='Target pixel purity (%)', ylabel='Bbox centroid error (mm)', title='18 correlated archived boundaries; descriptive only')
    axes[0].legend()
    axes[1].plot([r['centroid_error_mm'] for r in rows], 'o-', label='Sensor bbox centroid error')
    axes[1].plot([r['ray_depth_component_mm'] for r in rows], 'o-', label='Oracle-support ray/depth residual')
    axes[1].set(xlabel='Archived boundary index', ylabel='Distance (mm)', title='Evaluator decomposition, shared calibration')
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output/'support-vs-depth.png', dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', nargs='+', default=[f'runs/reference-pilot/init{i}-raycast-v02' for i in range(3)])
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Use a fresh evidence directory')
    runs = [audit_run(p) for p in args.runs]
    summary = summarize(runs)
    output.mkdir(parents=True)
    report = {'version': 'perception-support-audit-v1', 'code': code_identity(),
              'source_module_sha256': file_hash(__file__), 'summary': summary, 'runs': runs,
              'limitations': [
                  'No new model call, simulator state, or live decision.',
                  'Median box proxy and visible-surface centroid have different estimands; proxy distance is not a fair accuracy benchmark.',
                  'Sensor support never uses oracle correction; oracle mask and ray depths are evaluator-only.',
                  'Support decomposition includes contamination and missing target coverage; it is not pure causal attribution.',
                  'Camera calibration shared; cannot independently validate calibration or real sensor uncertainty.',
                  'Eighteen correlated archived states are not independent episodes or a held-out test.',
                  'Wall latency with paused simulated time is not asynchronous or real-time robustness.',
                  'Visible-surface centroid is view dependent, not an object pose or a grasp point.']}
    (output/'audit.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    rows = [r for run in runs for r in run['rows']]
    with (output/'metrics.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    render_diagnostics(rows, output)
    lines = ['# Archived perception support audit', '', json.dumps(summary, indent=2), '', *report['limitations'], '',
             'All per-frame source hashes, identities, missing inventory, geometry and latency measurements: audit.json.',
             'Oracle cyan overlays are evaluator labels, never available to the sensor estimator.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    artifacts = {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    (output/'artifact-sha256.json').write_text(json.dumps(artifacts, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
