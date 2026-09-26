"""Stored-only endpoint-veto comparison; no policy, geometry or physics rerun."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from ..runtime_core import _sha256_json
from .records import file_hash

EXPECTED = '17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b'
BASELINE = 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771'
REPLAY = '341abd1d43e7a7c114cc764cef8506196b7cc8dc1f664d4fdf2f70b602a42def'


def capture_at(captures, sim_time, sequence):
    selected = [capture for capture in captures if capture['capture_sim_time'] == sim_time]
    if len(selected) != 1 or selected[0]['capture_seq'] != sequence:
        raise ValueError('Capture must match exact boundary time and one-based sequence')
    return selected[0]


def read_run(directory, expected):
    if file_hash(directory/'episodes.jsonl') != expected:
        raise ValueError('Sealed journal mismatch')
    counts, kept, signatures, robot_contacts = Counter(), defaultdict(list), {}, defaultdict(list)
    previous = None
    for index, line in enumerate((directory/'episodes.jsonl').open('rb')):
        row = json.loads(line)
        if (not line.endswith(b'\n') or row['seq'] != index or row['previous_record_id'] != previous
                or row['record_id'] != _sha256_json({k: v for k, v in row.items() if k != 'record_id'})):
            raise ValueError('Journal chain mismatch')
        previous = row['record_id']
        kind, data = row['kind'], row['data']
        counts[kind] += 1
        if kind == 'initial_frame_gate':
            robot = set(data['groups_evaluator_only']['robot'])
        if kind in ('native_before', 'native_after', 'control_started', 'control_completed'):
            key = (kind, data['step'], data['control'], data.get('index'))
            if key in signatures:
                raise ValueError('Duplicate sample key')
            signatures[key] = _sha256_json(data)
            if kind.startswith('native_'):
                for contact in data['contacts']:
                    if robot.intersection(contact['geom_ids']):
                        robot_contacts[kind].append({'record_id': row['record_id'],
                            **{k: data[k] for k in ('step', 'control', 'index', 'time_s')}, 'contact': contact})
        else:
            kept[kind].append(data)
    if counts['failure'] or len(kept['termination']) != 1:
        raise ValueError('One complete successful collection required')
    for capture in kept['vision_capture']:
        if file_hash(directory/capture['artifact']) != capture['artifact_sha256']:
            raise ValueError('Capture artifact mismatch')
    return counts, kept, signatures, robot_contacts


def report(source, replay, baseline, output):
    source, replay, baseline, output = map(Path, (source, replay, baseline, output))
    counts, data, signatures, contacts = read_run(source, EXPECTED)
    old_counts, old, old_signatures, old_contacts = read_run(baseline, BASELINE)
    if file_hash(replay/'result.json') != REPLAY:
        raise ValueError('Sealed replay changed')
    replay_result = json.loads((replay/'result.json').read_text())
    if replay_result['status'] != 'passed' or replay_result['source_journal_sha256'] != EXPECTED:
        raise ValueError('Matching exact replay required')
    decisions, actions, endpoints, captures = [data[k] for k in ('decision', 'action_completed', 'endpoint', 'vision_capture')]
    manifest, initial, termination = data['run_start'][0]['manifest'], data['initial_frame_gate'][0], data['termination'][0]
    divergence = next((d for d in decisions if d['selected'] != d['experiment_selection']['unguarded_rule_token_at_same_state']), None)
    if divergence is None:
        raise ValueError('This sealed comparison must contain its recorded divergence')
    boundary = divergence['step']
    prefix = {key: value for key, value in signatures.items() if key[1] < boundary}
    old_prefix = {key: value for key, value in old_signatures.items() if key[1] < boundary}
    if prefix != old_prefix or len(prefix) != boundary*(400+16):
        raise ValueError('Historical prefix native/control equality failed')
    for name in ('action_started', 'action_completed', 'endpoint'):
        if [r for r in data[name] if r['step'] < boundary] != [r for r in old[name] if r['step'] < boundary]:
            raise ValueError('Historical prefix mismatch: '+name)
    if [d['canonical'] for d in decisions[:boundary+1]] != [d['canonical'] for d in old['decision'][:boundary+1]]:
        raise ValueError('Historical original canonical inputs mismatch')
    if [d['selected'] for d in decisions[:boundary]] != [d['selected'] for d in old['decision'][:boundary]]:
        raise ValueError('Historical original choices mismatch')
    for actual, historical in zip(captures[:boundary+1], old['vision_capture'][:boundary+1]):
        if actual['capture_seq'] != historical['capture_seq'] or actual['capture_sim_time'] != historical['capture_sim_time']:
            raise ValueError('Historical capture boundary mismatch')
        with np.load(source/actual['artifact'], allow_pickle=False) as a, np.load(baseline/historical['artifact'], allow_pickle=False) as b:
            for key in ('rgb', 'depth_m', 'intrinsics', 'camera_to_world'):
                if a[key].shape != b[key].shape or a[key].dtype != b[key].dtype or a[key].tobytes() != b[key].tobytes():
                    raise ValueError('Historical prefix capture bytes mismatch')
    trajectory = []
    for choice in decisions:
        step, selection = choice['step'], choice['experiment_selection']
        action = actions[step] if step < len(actions) else None
        before = choice['live_tcp_to_fixed_proxy_m']
        after = endpoints[step]['live_tcp_to_fixed_proxy_m'] if action else before
        trajectory.append({'step': step, 'selected': choice['selected'],
            'unguarded_rule_at_same_state': selection['unguarded_rule_token_at_same_state'],
            'distance_before_m': before, 'distance_after_m': after,
            'nominal_selected_reduction_m': before-selection['all_seven_candidates'][choice['selected']]['nominal_tcp_to_P_m'],
            'actual_reduction_m': before-after, 'executed': action is not None,
            'validator_passed': not action['result']['execution_contract_violation'] if action else None,
            'all_seven_candidates': selection['all_seven_candidates'],
            'eligible_tokens': [c['token'] for c in selection['eligible_canonical']['candidates']]})
    first_common = capture_at(captures, divergence['canonical']['state']['meta']['asof_sim_time'], boundary+1)
    guard_after_divergence = capture_at(captures, actions[boundary]['result']['execution_after']['sim_time'], boundary+2)
    old_after_divergence = capture_at(old['vision_capture'], old['action_completed'][boundary]['result']['execution_after']['sim_time'], boundary+2)
    final = capture_at(captures, actions[-1]['result']['execution_after']['sim_time'], len(actions)+1)
    old_final = capture_at(old['vision_capture'], old['action_completed'][-1]['result']['execution_after']['sim_time'], len(old['action_completed'])+1)
    if final['capture_sim_time'] != decisions[-1]['canonical']['state']['meta']['asof_sim_time'] or decisions[-1]['selected'] != 'STOP':
        raise ValueError('Terminal STOP must share the last completed-action capture boundary')
    initial_capture = capture_at(captures, initial['fresh_capture_sim_time_s'], 1)
    def contact_summary(records):
        return {stage: {'raw_robot_rows': len(records[stage]),
                       'strict_above_005N_rows': sum(row['contact']['normal_force_N'] > .05 for row in records[stage]),
                       'pair_names': dict(Counter(' / '.join(sorted(row['contact']['geom_names'])) for row in records[stage])),
                       'first_raw': records[stage][0] if records[stage] else None}
                for stage in ('native_before', 'native_after')}
    summary = {'raw_directory': str(source), 'producer_commit': manifest['code']['commit'],
        'journal_sha256': EXPECTED, 'journal_records': sum(counts.values()), 'record_counts': dict(counts),
        'protocol_sha256': manifest['protocol_sha256'], 'review_sha256': manifest['review_sha256'],
        'replay_directory': str(replay), 'replay_result_sha256': REPLAY,
        'replay_exact': {key: replay_result[key] for key in ('exact_controls', 'exact_native_snapshots', 'exact_captures')},
        'baseline_directory': str(baseline), 'baseline_journal_sha256': BASELINE,
        'initial_frame_gate': initial, 'fixed_support_point_count': len(manifest['endpoint_guard']['full_support']),
        'geometry_source_sha256': manifest['endpoint_guard']['source_sha256'],
        'geometry_compatibility': manifest['endpoint_guard']['compatibility'],
        'predicted_divergence_step': manifest['predicted_first_policy_divergence_step'],
        'actual_first_divergence': decisions[-1]['experiment_selection']['first_policy_divergence'],
        'historical_prefix_exact': {'completed_actions': boundary, 'controls': boundary*8,
            'native_stage_snapshots': boundary*400, 'captures': boundary+1,
            'canonical_inputs_through_divergence': boundary+1, 'states_own_packets_commands_results_exact': True},
        'initial_distance_m': trajectory[0]['distance_before_m'], 'final_distance_m': trajectory[-1]['distance_after_m'],
        'all_executed_validators_passed': all(t['validator_passed'] for t in trajectory if t['executed']),
        'raw_robot_contacts': contact_summary(contacts),
        'baseline': {'actions': len(old['action_completed']), 'final_distance_m': old['endpoint'][-1]['live_tcp_to_fixed_proxy_m'],
                     'termination': old['termination'][0], 'raw_robot_contacts': contact_summary(old_contacts)},
        'trajectory': trajectory, 'termination': termination,
        'terminal_endpoint': endpoints[-1], 'terminal_original_canonical': decisions[-1]['canonical'],
        'report_capture_boundaries': {'initial': initial_capture, 'common_pre_divergence': first_common,
            'baseline_after_divergence': old_after_divergence, 'guard_after_divergence': guard_after_divergence,
            'baseline_terminal': old_final, 'guard_terminal_STOP': final},
        'limits': ['one fresh exploratory partial-observation guard episode against one sealed baseline',
            'no raw robot contact observed in recorded native stages, not certified clearance',
            'initial cached full BOX support remains static and unsegmented',
            'nominal endpoint containment only; no sweep or physical margin',
            'STOP is terminal without execution; no contact-free grasp-readiness or task-success claim',
            'no policy patch, tuning or additional physical run follows this result']}
    output.mkdir(exist_ok=True, parents=True)
    with (output/'task2_endpoint_containment_veto_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 10))
    panels = [(source, initial_capture, 'Fresh initial; exact cached frame gate', summary['initial_distance_m']),
              (source, first_common, 'Common pre-action 22; exact prefix', trajectory[boundary]['distance_before_m']),
              (baseline, old_after_divergence, 'Baseline after 22: FWD; raw hand contact', old['endpoint'][boundary]['live_tcp_to_fixed_proxy_m']),
              (source, guard_after_divergence, 'Guard after 22: LEFT; no raw robot contact', trajectory[boundary]['distance_after_m']),
              (baseline, old_final, 'Baseline after 24: >0.05 N abort boundary', old['endpoint'][-1]['live_tcp_to_fixed_proxy_m']),
              (source, final, 'Guard after 27 / decision 28: STOP, no execution', summary['final_distance_m'])]
    for ax, (directory, capture, label, distance) in zip(axes.flat, panels):
        with np.load(directory/capture['artifact'], allow_pickle=False) as frame:
            rgb = frame['rgb']
        ax.imshow(rgb)
        ax.set_title(f'{label}\nTCP to fixed P: {distance*1000:.3f} mm; capture {capture["capture_seq"]}', fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle('Task2: full-BOX observed-point containment veto at nominal movement endpoints\n'
                 'Actual RGB; fresh policy rollout, no hidden prefix replay; exploratory approach only, no grasp/task success', fontsize=12)
    fig.subplots_adjust(left=.015, right=.985, bottom=.015, top=.89, hspace=.22, wspace=.05)
    fig.savefig(output/'task2_endpoint_containment_veto_rgb.png', dpi=165)
    plt.close(fig)
    print(json.dumps({'records': sum(counts.values()), 'first_divergence': summary['actual_first_divergence'],
        'initial_distance_m': summary['initial_distance_m'], 'final_distance_m': summary['final_distance_m'],
        'contacts': summary['raw_robot_contacts'], 'prefix_exact': summary['historical_prefix_exact'],
        'terminal_candidates': trajectory[-1]['all_seven_candidates']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'replay', 'baseline', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    report(args.source, args.replay, args.baseline, args.output)
