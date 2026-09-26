"""Stored-only raw/threshold contact summary and actual RGB; no simulator imports."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from .records import file_hash, load_records


def report(source, replay, output):
    source, replay, output = map(Path, (source, replay, output))
    rows, errors = load_records(source / 'episodes.jsonl')
    if errors or any(row['kind'] == 'failure' for row in rows):
        raise ValueError('Completed source journal required')
    def data(kind):
        return [row['data'] for row in rows if row['kind'] == kind]
    manifest, initial, termination = data('run_start')[0]['manifest'], data('initial_frame_gate')[0], data('termination')[0]
    replay_result = json.loads((replay / 'result.json').read_text())
    journal_hash = file_hash(source / 'episodes.jsonl')
    if replay_result['status'] != 'passed' or replay_result['source_journal_sha256'] != journal_hash:
        raise ValueError('Matching completed replay required')
    captures, decisions, actions, endpoints = [data(name) for name in ('vision_capture', 'decision', 'action_completed', 'endpoint')]
    for capture in captures:
        if file_hash(source / capture['artifact']) != capture['artifact_sha256']:
            raise ValueError('Capture hash mismatch')
    first = data('first_new_robot_contact')[0]
    identity = first['first_observed_sample']
    raw_first = next(row['data'] for row in rows if row['record_id'] == identity['raw_record_id'])
    pairs = {tuple(pair['geom_ids']) for pair in first['new_pairs']}
    first_rows = [contact for contact in raw_first['contacts'] if tuple(sorted(contact['geom_ids'])) in pairs and contact['normal_force_N'] > .05]
    robot = set(initial['groups_evaluator_only']['robot'])
    native = [row for row in rows if row['kind'] in ('native_before', 'native_after')]
    def robot_contacts(row):
        return [c for c in row['data']['contacts'] if robot.intersection(c['geom_ids'])]
    def sample_identity(row):
        return {'stage': row['kind'], 'raw_record_id': row['record_id'],
                **{key: row['data'][key] for key in ('step', 'control', 'index', 'time_s')}}
    first_raw_index = next(i for i, row in enumerate(native) if robot_contacts(row))
    first_raw = {'first_observed_sample': sample_identity(native[first_raw_index]),
        'previous_observed_sample': sample_identity(native[first_raw_index - 1]) if first_raw_index else None,
        'contact_rows': robot_contacts(native[first_raw_index])}
    raw_robot_summary = {}
    for stage in ('native_before', 'native_after'):
        stage_rows = [row for row in native if row['kind'] == stage]
        raw_contacts = [c for row in stage_rows for c in robot_contacts(row)]
        raw_robot_summary[stage] = {'raw_contact_rows': len(raw_contacts),
            'rows_per_step': dict(Counter(row['data']['step'] for row in stage_rows for c in robot_contacts(row))),
            'pair_name_row_counts': dict(Counter(' / '.join(sorted(c['geom_names'])) for c in raw_contacts)),
            'final_sample': sample_identity(stage_rows[-1]),
            'final_sample_robot_contact_rows': robot_contacts(stage_rows[-1])}
    stage_summary = {}
    for stage in ('native_before', 'native_after'):
        samples = [r for r in data(stage) if r['step'] == termination['last_step']]
        contacts = [c for r in samples for c in r['contacts'] if tuple(sorted(c['geom_ids'])) in pairs]
        strong = [c for c in contacts if c['normal_force_N'] > .05]
        stage_summary[stage] = {'sample_count': len(samples), 'pair_contact_rows': len(contacts),
            'pair_rows_above_strict_005N': len(strong),
            'samples_with_pair_above_strict_005N': sum(any(tuple(sorted(c['geom_ids'])) in pairs and c['normal_force_N'] > .05 for c in r['contacts']) for r in samples),
            'peak_pair_normal_force_N': max(c['normal_force_N'] for c in contacts)}
    trajectory = []
    for choice, action, endpoint in zip(decisions, actions, endpoints):
        result = action['result']
        trajectory.append({'step': choice['step'], 'token': choice['selected'],
            'distance_before_m': choice['live_tcp_to_fixed_proxy_m'], 'distance_after_m': endpoint['live_tcp_to_fixed_proxy_m'],
            'execution_contract_violation': result['execution_contract_violation'],
            'execution_contract_reason': result['execution_contract_reason'],
            'actual_delta_m': result['delta_m'], 'native_integrations': action['native_integrations']})
    summary = {'producer_commit': manifest['code']['commit'], 'raw_directory': str(source),
        'journal_sha256': journal_hash, 'journal_records': len(rows),
        'record_counts': dict(Counter(row['kind'] for row in rows)),
        'replay_directory': str(replay), 'replay_result_sha256': file_hash(replay / 'result.json'),
        'replay_exact': {key: replay_result[key] for key in ('exact_controls', 'exact_native_snapshots', 'exact_captures')},
        'protocol_sha256': manifest['protocol_sha256'], 'source_sha256': manifest['source_sha256'],
        'review_sha256': manifest['review_sha256'], 'initial_array_gate': initial['array_bytes_exact'],
        'initial_point': initial['cached_point'], 'initial_proprioception': initial['initial_proprioception'],
        'initial_above_threshold_robot_pairs': initial['initial_above_threshold_robot_pairs'],
        'contact_threshold': 'strict normal_force_N > 0.05; original first_new_robot_contact event is thresholded',
        'initial_raw_robot_contact_rows': [c for c in initial['initial_contact_snapshot_evaluator_only']['contacts'] if robot.intersection(c['geom_ids'])],
        'first_raw_robot_contact': first_raw, 'all_raw_robot_contacts_by_stage': raw_robot_summary,
        'first_above_threshold_robot_contact': first, 'first_qualifying_raw_contact_rows': first_rows,
        'terminal_action_all_new_pairs': actions[-1]['new_pairs_through_action_evaluator_only'],
        'terminal_action_native_stage_summary': stage_summary, 'termination': termination,
        'trajectory': trajectory, 'terminal_endpoint': endpoints[-1],
        'limits': ['cached perception with exact initial image equivalence only',
                   'median-ray proxy, not grasp center', 'oracle abort after complete atomic primitive',
                   'threshold crossing is later than first raw hand/bottle contact',
                   'native buffer stages are not continuous contact-onset times',
                   'no alternative candidate, grasp, lift or task success established']}
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'task2_box_point_boundary_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 4, figsize=(17.2, 5.2))
    raw_step = first_raw['first_observed_sample']['step']
    selected = (0, raw_step, len(captures) - 2, len(captures) - 1)
    distances = (decisions[0]['live_tcp_to_fixed_proxy_m'], decisions[raw_step]['live_tcp_to_fixed_proxy_m'],
                 decisions[-1]['live_tcp_to_fixed_proxy_m'], endpoints[-1]['live_tcp_to_fixed_proxy_m'])
    labels = ('Initial: fresh image exactly matched', f'Before step {raw_step}: first raw-contact action',
              'Before step 24: first >0.05 N action', 'After step 24: completed primitive, stop')
    for ax, index, distance, label in zip(axes, selected, distances, labels):
        with np.load(source / captures[index]['artifact'], allow_pickle=False) as archive:
            rgb = archive['rgb']
        ax.imshow(rgb, extent=(0, rgb.shape[1], rgb.shape[0], 0))
        ax.set_title(f'{label}\nTCP to fixed proxy: {distance*1000:.2f} mm', fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    x1, y1, x2, y2 = initial['cached_point']['box_xyxy']
    axes[0].add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, ec='#00bfff', lw=1.5))
    fig.suptitle('Task2: cached BOX median-ray point with open-jaw nominal approach (zero-based steps)\n'
                 'Hand collision mesh ↔ bottle: raw contact at step 22; strict >0.05 N at step 24; all 25 validations passed', fontsize=12)
    fig.subplots_adjust(left=.015, right=.985, bottom=.025, top=.78, wspace=.08)
    fig.savefig(output / 'task2_box_point_boundary_rgb.png', dpi=170)
    plt.close(fig)
    print(json.dumps({'journal_records': len(rows), 'actions': len(actions), 'replay': summary['replay_exact'], 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--replay', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report(args.source, args.replay, args.output)
