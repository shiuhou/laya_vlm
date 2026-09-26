"""Registered sensor-only two-layer depth hypothesis; offline development probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .perception_support_audit import audit_run
from .records import code_identity, file_hash, load_records
from .target_referent import _restore_support, bbox_mask, evaluate_mask_overlap, surface_centroid

PROTOCOL = Path('docs/research/depth_support_probe_protocol.md')
TOKENS = ('x+', 'x-', 'y+', 'y-', 'z+', 'z-', 'hold')
DELTAS = np.array([[.01, 0, 0], [-.01, 0, 0], [0, .01, 0], [0, -.01, 0],
                   [0, 0, .01], [0, 0, -.01], [0, 0, 0]])


def separate_depth(depth, box):
    """No simulator, labels, target point, or oracle arguments."""
    depth = np.asarray(depth)
    valid = bbox_mask(depth.shape, box) & np.isfinite(depth) & (depth >= .01) & (depth <= 5)
    indices = np.flatnonzero(valid)
    order = np.argsort(depth.flat[indices], kind='stable')
    sorted_indices = indices[order]
    values = depth.flat[sorted_indices]
    n = len(values)
    minimum = max(3, int(np.ceil(.05*n)))
    result = {'status': 'unknown', 'valid_count': n, 'minimum_group_count': minimum,
              'gap_m': None, 'split_rank': None, 'zero_gap_ambiguous': None,
              'foreground_indices': [], 'background_indices': [],
              'valid_indices': indices.tolist(), 'shape': list(depth.shape),
              'foreground_count': 0, 'background_count': 0, 'oracle_used': False}
    if n < 2*minimum:
        return result
    split_ranks = np.arange(minimum, n-minimum+1)
    gaps = values[split_ranks]-values[split_ranks-1]
    winner = int(np.argmax(gaps))
    split = int(split_ranks[winner])
    gap = float(gaps[winner])
    result.update(status='split', gap_m=gap, split_rank=split,
                  zero_gap_ambiguous=gap == 0, foreground_count=split, background_count=n-split,
                  foreground_indices=sorted_indices[:split].tolist(),
                  background_indices=sorted_indices[split:].tolist())
    return result


def mask_from_indices(shape, indices):
    mask = np.zeros(shape, bool)
    mask.flat[indices] = True
    return mask


def directional_diagnostic(estimate, tcp, oracle):
    if estimate is None or tcp is None or oracle is None:
        return {'status': 'unknown'}
    estimate, tcp, oracle = map(np.asarray, (estimate, tcp, oracle))
    gain = np.linalg.norm(estimate-tcp)-np.linalg.norm(estimate-(tcp+DELTAS), axis=1)
    true_gain = np.linalg.norm(oracle-tcp)-np.linalg.norm(oracle-(tcp+DELTAS), axis=1)
    selected = np.flatnonzero(np.isclose(gain, gain.max(), atol=1e-12, rtol=0))
    best = np.flatnonzero(np.isclose(true_gain, true_gain.max(), atol=1e-12, rtol=0))
    realized = true_gain[selected]
    return {'status': 'evaluated', 'nominal_gain_mm': (gain*1000).tolist(),
            'oracle_nominal_gain_mm': (true_gain*1000).tolist(),
            'preferred_set': [TOKENS[i] for i in selected],
            'oracle_preferred_set': [TOKENS[i] for i in best],
            'preferred_sets_intersect': bool(set(selected) & set(best)),
            'preferred_sets_equal': set(selected)==set(best),
            'all_preferred_improve': bool(np.all(realized > 1e-12)),
            'true_gain_min_mm': float(realized.min()*1000), 'true_gain_max_mm': float(realized.max()*1000),
            'regret_min_mm': float((true_gain.max()-realized.max())*1000),
            'regret_max_mm': float((true_gain.max()-realized.min())*1000),
            'physical_feasibility_evaluated': False}


def evaluate_run(path):
    verified = audit_run(path)
    path = Path(path)
    records, _ = load_records(path/'episodes.jsonl')
    pairs = {r['data']['physical']['physical_state_id']: r['data'] for r in records if r['kind']=='paired_state'}
    refs = {r['record_id']: r['data'] for r in records if r['kind']=='target_referent'}
    rows = []
    for base in verified['rows']:
        ref = refs[base['referent_record_id']]
        pair = pairs[base['physical_state_id']]
        tcp = pair['perceptual_state']['fields']['robot.tcp_position_m']['value']
        with np.load(base['frame_artifact']) as frame:
            depth, k, t = frame['depth_m'], frame['intrinsics'], frame['camera_to_world']
            split = separate_depth(depth, base['box_xyxy'])
            oracle_mask = _restore_support(ref['oracle'], depth.shape)
            support = mask_from_indices(depth.shape, split['foreground_indices'])
            point = surface_centroid(depth, support, k, t)['position_world_m']
            overlap = evaluate_mask_overlap(support, oracle_mask)
        error = None if point is None else float(np.linalg.norm(np.asarray(point)-base['oracle_centroid_m'])*1000)
        rows.append({'run': path.name, 'init_state_id': base['init_state_id'], 'step': base['environment_step'],
                     'capture_seq': base['capture_seq'], 'physical_state_id': base['physical_state_id'],
                     'frame_artifact': base['frame_artifact'], 'frame_sha256': base['frame_sha256'],
                     'referent_record_id': base['referent_record_id'], 'box_xyxy': base['box_xyxy'],
                     'split': split, 'full_bbox_point_m': base['sensor_centroid_m'], 'foreground_point_m': point,
                     'oracle_point_m': base['oracle_centroid_m'], 'tcp_sensor_m': tcp,
                     'full_bbox_error_mm': base['centroid_error_mm'], 'foreground_error_mm': error,
                     'error_change_mm': None if error is None else error-base['centroid_error_mm'],
                     'full_bbox_purity': base['purity'], 'foreground_purity': overlap['sensor_pixel_purity'],
                     'full_bbox_recall': base['visible_handle_recall'], 'foreground_recall': overlap['visible_handle_recall'],
                     'full_bbox_direction': directional_diagnostic(base['sensor_centroid_m'], tcp, base['oracle_centroid_m']),
                     'foreground_direction': directional_diagnostic(point, tcp, base['oracle_centroid_m'])})
    return {'source': str(path), 'source_log_sha256': verified['episodes_sha256'],
            'source_manifest_sha256': verified['manifest_sha256'], 'missing': verified['missing'], 'rows': rows}


def summarize(rows):
    known = [r for r in rows if r['foreground_error_mm'] is not None]
    result = {'n': len(rows), 'known': len(known), 'unknown': len(rows)-len(known),
              'zero_gap_ambiguous': sum(r['split']['zero_gap_ambiguous'] is True for r in rows),
              'error_improved_n': sum(r['error_change_mm'] < -1e-9 for r in known),
              'error_worsened_n': sum(r['error_change_mm'] > 1e-9 for r in known),
              'error_unchanged_n': sum(abs(r['error_change_mm'])<=1e-9 for r in known)}
    for key in ('full_bbox_error_mm', 'foreground_error_mm', 'full_bbox_purity', 'foreground_purity',
                'full_bbox_recall', 'foreground_recall'):
        vals = [r[key] for r in rows if r[key] is not None]
        result[key] = {'n': len(vals), 'min': min(vals) if vals else None,
                       'median': float(np.median(vals)) if vals else None, 'max': max(vals) if vals else None}
    for method in ('full_bbox_direction', 'foreground_direction'):
        entries = [r[method] for r in rows if r[method]['status']=='evaluated']
        result[method] = {'n': len(entries),
                         'preferred_set_intersects_oracle_n': sum(e['preferred_sets_intersect'] for e in entries),
                         'all_preferred_improve_n': sum(e['all_preferred_improve'] for e in entries),
                         'worst_regret_mm': max((e['regret_max_mm'] for e in entries), default=None)}
    return result


def plot(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    for ax, a, b, title in zip(axes, ('full_bbox_error_mm', 'full_bbox_purity', 'full_bbox_recall'),
                              ('foreground_error_mm', 'foreground_purity', 'foreground_recall'),
                              ('Surface centroid error (mm)', 'Target pixel purity', 'Visible target recall')):
        x, y = [r[a] for r in rows], [r[b] for r in rows]
        ax.scatter(x, y)
        maximum = max(max(x), max(y))
        ax.plot([0, maximum], [0, maximum], '--', color='gray')
        ax.set(xlabel='Full bbox', ylabel='Near depth layer', title=title)
    fig.suptitle('Fixed two-layer foreground hypothesis / archived development states / evaluator-only oracle')
    fig.tight_layout()
    fig.savefig(output/'comparison.png', dpi=130)
    plt.close(fig)
    selected = list(dict.fromkeys([min(range(len(rows)), key=lambda i: rows[i]['error_change_mm']),
                                  max(range(len(rows)), key=lambda i: rows[i]['error_change_mm'])]))
    fig, axes = plt.subplots(len(selected), 2, figsize=(10, 5*len(selected)), squeeze=False)
    for slot, i in enumerate(selected):
        row = rows[i]
        records, _ = load_records(Path(row['frame_artifact']).parents[1]/'episodes.jsonl')
        ref = next(r['data'] for r in records if r['record_id']==row['referent_record_id'])
        with np.load(row['frame_artifact']) as frame:
            rgb = frame['rgb'].astype(float)/255
            fg = mask_from_indices(frame['depth_m'].shape, row['split']['foreground_indices'])
            oracle = _restore_support(ref['oracle'], frame['depth_m'].shape)
            sensor_image = rgb.copy()
            sensor_image[fg] = .4*sensor_image[fg]+.6*np.array([1, .5, 0])
            oracle_image = rgb.copy()
            oracle_image[oracle] = .4*oracle_image[oracle]+.6*np.array([0, 1, 1])
            axes[slot, 0].imshow(sensor_image)
            axes[slot, 1].imshow(oracle_image)
        axes[slot, 0].set_title(f"{row['run']} step {row['step']} | SENSOR near layer\nError {row['full_bbox_error_mm']:.1f} -> {row['foreground_error_mm']:.1f} mm")
        axes[slot, 1].set_title(f"EVALUATOR-only oracle target\nNear-layer recall {row['foreground_recall']:.1%}, purity {row['foreground_purity']:.1%}")
        axes[slot, 0].axis('off')
        axes[slot, 1].axis('off')
    fig.tight_layout()
    fig.savefig(output/'representative-best-worst.png', dpi=130)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Use a fresh evidence directory')
    protocol_hash = file_hash(PROTOCOL)
    runs = [evaluate_run(Path(f'runs/reference-pilot/init{i}-raycast-v02')) for i in range(3)]
    rows = [r for run in runs for r in run['rows']]
    report = {'version': 'depth-support-probe-v1', 'code': code_identity(),
              'protocol_sha256': protocol_hash, 'module_sha256': file_hash(__file__),
              'summary': summarize(rows), 'per_init': {str(i): summarize([r for r in rows if r['init_state_id']==i]) for i in range(3)},
              'runs': runs, 'policy_changed': False, 'live_execution': False}
    output.mkdir(parents=True)
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'probe.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    plot(rows, output)
    (output/'artifact-sha256.json').write_text(json.dumps({p.name: file_hash(p) for p in output.iterdir() if p.is_file()}, indent=2)+'\n')
    print(json.dumps(report['summary'], indent=2))


if __name__=='__main__':
    main()
