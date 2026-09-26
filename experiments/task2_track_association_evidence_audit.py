"""Check sealed same-track association rows; never run tracking or projection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from task2_box_evidence_audit import canonical, read, require, sha
from task2_box_temporal_evidence_audit import ARMS, ACCEPTED, REFERENCES, METRICS, same

FREEZE = 'dc1ec6c44d84f3337aec2f7fc0f7fc14a03f6d43'
CONVENTION = 'nearest_center_index_floor_xy_plus_half'
CHANGED_FIELDS = {'sample_pixel_xy', 'depth_m', 'surface_point_world_m', 'depth_status',
                  'sampling_convention', 'reference_deltas'}
SOURCE_HASHES = {
    'episodes.jsonl': '0e7bd76d3f6b11244729bc767ec1b1f9a2625aa6069e494adf9743ea5900cf05',
    'sensor-seal.json': 'bae9793115ededab12b6b5bca242af9cdb0c2ed8c1e8d62219af3bbce65cc30b',
    'close-tracks.jsonl': '158e2d376d30450e1e2903a0abf793bb71a3a9a2327055b58aabf49965721f37',
    'open_hold-tracks.jsonl': '5c80ab6500b0ccc7ce7009fff9b364c76c4a7fcc3534aef454704f67f83c41d0',
    'sensor-summary.json': '4b46a6bddaa87b545de1f6d5f31e1aa6f77836e9b904fe5e71877cd47d6ce933',
}


def audit(sources, name):
    run = sources / name
    original = sources / 'task2-box-temporal-run-01'
    source = sources / 'interaction-observability-paired-01'
    manifest, config = read(run/'manifest.json'), read(run/'resolved_config.yaml')
    preflight_path = sources/'task2-track-association-preflight-01.json'
    require(sha(preflight_path) == manifest['preflight_sha256'] == 'b301f53378ff1968a8e0be65f21538880091df4e5124356dee9d0a90a52cd67d', 'reviewed actual preflight')
    preflight = read(preflight_path)
    require(manifest['code'] == preflight['code'] and manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean frozen code')
    require(manifest['python'] == preflight['python'], 'frozen interpreter')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_track_coordinate_association.py'] == 'b95245bab639fac6a54359dd51020b2b40d0fd5e23f71fb7d1b7020b2590c855', 'reviewed adapter')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_box_temporal_probe.py'] == '655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50', 'unchanged baseline helper')
    require(sha(run/'protocol.md') == config['protocol_sha256'] == preflight['protocol_sha256'] == '8f32d642890faeb7d8e78f6ccc8418c540bd2a40d8e54accfd3a4650cde147f6', 'frozen protocol')
    require(sha(run/'review.md') == manifest['review_sha256'] and FREEZE in (run/'review.md').read_text(), 'prospective receipt')
    require(config['convention'] == CONVENTION and config['source_hashes'] == SOURCE_HASHES, 'one registered association condition')
    for relative, expected in SOURCE_HASHES.items():
        require(sha(original/relative) == expected, 'original floor evidence unchanged')
    journal, previous = [], None
    for i, line in enumerate((run/'episodes.jsonl').read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete journal line')
        row = json.loads(line)
        require(row['seq'] == i and row['previous_record_id'] == previous and row['config_hash'] == canonical(config), 'journal identity/link')
        require(row['record_id'] == canonical({k: v for k, v in row.items() if k != 'record_id'}), 'journal hash')
        journal.append(row)
        previous = row['record_id']
    require([r['kind'] for r in journal] == ['run_start', 'arm_association_complete', 'arm_association_complete', 'sensor_outputs_sealed', 'termination'], 'single complete batch')
    require([r['data'] for r in journal[1:3]] == [{'arm': arm, 'native_fields_unchanged': True, 'rows': 22632} for arm in ARMS], 'complete arms')
    require(journal[-1]['data'] == {'LK_model_physics_render_calls': 0, 'reason': 'all_associations_sealed', 'retries': 0, 'tracks': 984}, 'termination counts')
    require(sha(run/'sensor-seal.json') == journal[3]['data']['sha256'], 'journal sensor seal')
    seal = read(run/'sensor-seal.json')
    require(seal['evaluator_read'] is False and set(seal['sha256']) == {'close-tracks.jsonl', 'open_hold-tracks.jsonl', 'sensor-summary.json', 'same-track-changes.json'}, 'all sensor products sealed')
    for relative, expected in seal['sha256'].items():
        require(sha(run/relative) == expected, 'sensor artifact unchanged')
    admission = read(run/'admission.json')
    require(admission == preflight['admission'] == read(original/'admission.json'), 'identical original actual inputs')
    for relative, expected in admission['source_sha256'].items():
        require(sha(source/relative) == expected, 'source receipt hash')
    summary, changes = read(run/'sensor-summary.json'), read(run/'same-track-changes.json')
    require(summary['holding'] is None and summary['references'] == REFERENCES, 'fixed references, no holding label')
    require(changes['LK_calls'] == 0 and changes['source_floor_summary_sha256'] == SOURCE_HASHES['sensor-summary.json'], 'paired change provenance')
    controls = [json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()]
    endpoints = read(source/'endpoints.json')
    tracks_by_arm, outcomes = {}, {}
    for arm in ARMS:
        old = [json.loads(line) for line in (original/f'{arm}-tracks.jsonl').read_text().splitlines()]
        new = [json.loads(line) for line in (run/f'{arm}-tracks.jsonl').read_text().splitlines()]
        require(len(old) == len(new) == 22632, 'every original row retained')
        tracks = [new[i*46:(i+1)*46] for i in range(492)]
        tracks_by_arm[arm] = tracks
        depths, tcps = [], []
        for meta in admission['arms'][arm]['captures']:
            path = source/meta['artifact']
            require(sha(path) == meta['artifact_sha256'], 'exact source capture')
            with np.load(path, allow_pickle=False) as f:
                depths.append(f['depth_m'])
            pool = endpoints if meta['capture_id'] == 0 else controls
            matches = [r for r in pool if r['arm'] == arm and r.get('after_step', r.get('step')) == meta['after_step'] and (meta['capture_id'] == 0 or r['control'] == meta['control'])]
            require(len(matches) == 1 and matches[0]['sensor']['read_sim_time_s'] == meta['tcp_read_sim_time_s'], 'same saved TCP boundary')
            tcps.append(np.asarray(matches[0]['sensor']['tcp_fk_world_m']))
        changed = [{'capture_id': i, 'denominator': 492, 'changed_sample_pixel_count': 0, 'changed_depth_value_count': 0} for i in range(46)]
        for n, (a, b) in enumerate(zip(old, new)):
            require(set(b) == set(a) | {'sampling_convention'}, 'row schema preserved with explicit convention field')
            require({k: v for k, v in a.items() if k not in CHANGED_FIELDS} == {k: v for k, v in b.items() if k not in CHANGED_FIELDS}, 'every native field and metadata exactly preserved')
            seed, i = divmod(n, 46)
            require((b['seed_id'], b['capture_id']) == (seed, i), 'complete stable order')
            require(b['sampling_convention'] == CONVENTION, 'association convention explicit')
            pixel, z, valid, reason = None, None, False, 'RGB_track_not_admitted'
            if b['status'] in ACCEPTED:
                x, y = np.floor(np.asarray(b['point_pixel_index_xy'])+.5).astype(int)
                reason = 'outside_image'
                h, w = depths[i].shape
                if 0 <= x < w and 0 <= y < h:
                    pixel = [int(x), int(y)]
                    raw_z = float(depths[i][y, x])
                    z = raw_z if np.isfinite(raw_z) else None
                    valid = bool(np.isfinite(raw_z) and .01 <= raw_z <= 5.)
                    reason = 'valid' if valid else 'outside_valid_range' if np.isfinite(raw_z) else 'nonfinite'
            require(b['sample_pixel_xy'] == pixel and b['depth_m'] == z and b['depth_status'] == reason, 'center-index association/bounds/depth validity')
            xyz = b['surface_point_world_m']
            require((xyz is not None) == valid, 'depth admission')
            require(xyz is None or (np.asarray(xyz).shape == (3,) and np.isfinite(xyz).all()), 'saved world point schema')
            if pixel == a['sample_pixel_xy']:
                require(xyz == a['surface_point_world_m'], 'unchanged selected pixel has exact original point')
            changed[i]['changed_sample_pixel_count'] += pixel != a['sample_pixel_xy']
            changed[i]['changed_depth_value_count'] += z != a['depth_m']
            for ref, j in REFERENCES.items():
                if i < j:
                    require(b['reference_deltas'][ref] is None, 'no future reference')
                    continue
                dtcp = tcps[i]-tcps[j]
                origin = tracks[seed][j]['surface_point_world_m']
                expected = {'tcp_delta_m': dtcp.tolist(), 'point_delta_m': None, 'point_minus_tcp_delta_m': None, **{k: None for k in METRICS}}
                if xyz is not None and origin is not None:
                    delta = np.asarray(xyz)-origin
                    residual = delta-dtcp
                    expected.update(point_delta_m=delta.tolist(), point_minus_tcp_delta_m=residual.tolist(), point_delta_z_m=float(delta[2]), point_delta_norm_m=float(np.linalg.norm(delta)), point_minus_tcp_delta_z_m=float(residual[2]), point_minus_tcp_delta_norm_m=float(np.linalg.norm(residual)))
                same(b['reference_deltas'][ref], expected, 'all displacement/residual arithmetic')
        require(changes['arms'][arm] == changed, 'every capture paired changes')
        expected_summary = []
        for i in range(46):
            current = [t[i] for t in tracks]
            refs = {}
            for ref, j in REFERENCES.items():
                metrics = {}
                for key in METRICS:
                    values = [r['reference_deltas'][ref][key] for r in current if r['reference_deltas'][ref] is not None and r['reference_deltas'][ref][key] is not None]
                    q = np.percentile(values, [25, 50, 75], method='linear') if values else [None]*3
                    metrics[key] = {'count': len(values), 'q25': q[0], 'median': q[1], 'q75': q[2]}
                refs[ref] = {'reference_capture_id': j, 'reference_surface_valid_count': sum(t[j]['surface_point_world_m'] is not None for t in tracks) if i >= j else None, 'metrics': metrics}
            expected_summary.append({'capture_id': i, 'denominator': 492, 'native_surviving_count': sum(r['status'] in ACCEPTED for r in current), 'valid_surface_count': sum(r['surface_point_world_m'] is not None for r in current), 'native_failure_count': sum(r['status'] == 'native_failure' for r in current), 'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in current), 'references': refs})
        same(summary['arms'][arm], expected_summary, 'all summaries and fixed cohorts')
        outcomes[arm] = {'native_fields_exact_rows': len(new), 'changed_pixels_total': sum(r['changed_sample_pixel_count'] for r in changed), 'changed_depths_total': sum(r['changed_depth_value_count'] for r in changed), 'changed_by_capture': changed, 'final_summary': expected_summary[-1]}
    evaluation = run/'evaluation'
    for relative, expected in read(evaluation/'artifacts.json').items():
        require(sha(evaluation/relative) == expected, 'evaluation artifact hashes')
    require(read(evaluation/'evaluation-start.json') == {'sensor_seal_sha256': sha(run/'sensor-seal.json'), 'journal_sha256': sha(run/'episodes.jsonl'), 'evaluator_read': False}, 'evaluation references sealed complete outputs')
    proxy = read(evaluation/'proxy-membership.json')
    for path, expected in proxy['mask_sha256'].items():
        require(sha(path) == expected, 'same evaluated mask bytes')
    old_proxy = read(original/'evaluation/proxy-membership.json')
    require(proxy['mask_sha256'] == old_proxy['mask_sha256'], 'identical proxy evaluator inputs')
    for arm in ARMS:
        masks = [np.load(source/f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy', allow_pickle=False) for i in range(46)]
        memberships, departures, seen = [], {}, set()
        for track in tracks_by_arm[arm]:
            for row in track:
                pixel = row['sample_pixel_xy']
                member = None if pixel is None or row['status'] not in ACCEPTED else bool(masks[row['capture_id']][pixel[1], pixel[0]])
                item = {'seed_id': row['seed_id'], 'capture_id': row['capture_id'], 'proxy_membership': member, 'tracker_status': row['status'], 'sample_pixel_xy': pixel}
                memberships.append(item)
                key = str(row['seed_id'])
                if member is False and key in seen and key not in departures:
                    departures[key] = item
                if member is True:
                    seen.add(key)
        counts = [{'capture_id': i, 'denominator': 492, 'proxy_true': sum(r['proxy_membership'] is True for r in memberships if r['capture_id'] == i), 'proxy_false': sum(r['proxy_membership'] is False for r in memberships if r['capture_id'] == i), 'proxy_unknown': sum(r['proxy_membership'] is None for r in memberships if r['capture_id'] == i)} for i in range(46)]
        require(proxy['arms'][arm] == {'rows': memberships, 'counts': counts, 'first_observed_departure_after_proxy_true': departures, 'resolved_depth_ownership': None, 'semantic_confidence': None}, 'all proxy rows/counts/departures')
        earliest = min(departures.values(), key=lambda r: (r['capture_id'], r['seed_id'])) if departures else None
        outcomes[arm].update(proxy_counts=counts, departure_seed_count=len(departures), earliest_departure=earliest,
                             seed5_capture1={k: tracks_by_arm[arm][5][1][k] for k in ('point_pixel_index_xy', 'sample_pixel_xy', 'depth_m', 'surface_point_world_m')})
    return {'status': 'pass', 'freeze': FREEZE, 'journal_sha256': sha(run/'episodes.jsonl'), 'journal_records': len(journal), 'sensor_seal_sha256': sha(run/'sensor-seal.json'), 'summary_sha256': sha(run/'sensor-summary.json'), 'proxy_sha256': sha(evaluation/'proxy-membership.json'), 'track_rows': 45264, 'tracks': 984, 'arms': outcomes,
            'limits': ['stored evidence only; no LK/projection/FK/model/physics/render calls', 'changed-pixel world generation source-reviewed, unchanged pixels compare exactly to original stored points', 'same dependent paired trace; no semantic identity, depth ownership, held-out or universal repair claim', 'sensor-before-evaluator code and referenced complete seal checked; no independent evaluator start wall timestamp']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--run', default='task2-track-association-run-01')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'arms'}, indent=2))
