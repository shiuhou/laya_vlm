"""Read the sealed matched approaches/replays; export descriptive traces only."""
from __future__ import annotations

import json

import numpy as np

from . import task2_point_anchor_approach as probe
from .records import file_hash, load_records

RAW = probe.base.RAW / 'task2-point-anchor-approach-run-01'
OUTPUT = probe.base.ROOT / 'docs/evidence/autonomous_research'
FREEZE = 'fb7899bef22e6473aed30e7dd0051568bd7db7f7'


def produce():
    batch, errors = load_records(RAW / 'episodes.jsonl')
    if errors or batch[-1]['data'].get('reason') != 'both_fixed_conditions_and_replays_complete':
        raise ValueError('The complete fixed pair is required')
    conditions, traces = [], {}
    for name in probe.ORDER:
        directory = RAW / name
        records, errors = load_records(directory / 'episodes.jsonl')
        if errors or any(row['kind'] == 'failure' for row in records):
            raise ValueError('Incomplete condition')
        def rows(kind):
            return [row['data'] for row in records if row['kind'] == kind]
        manifest = rows('run_start')[0]['manifest']
        decisions, endpoints, actions = rows('decision'), rows('endpoint'), rows('action_completed')
        replay = probe.base.read(RAW / (name + '-replay') / 'result.json')
        journal_sha = file_hash(directory / 'episodes.jsonl')
        if (manifest['code']['commit'] != FREEZE or replay['code'] != manifest['code']
                or replay['status'] != 'passed' or replay['source_journal_sha256'] != journal_sha):
            raise ValueError('Source/replay/freeze mismatch')
        terminal = decisions[-1]
        tcp = terminal['canonical']['state']['fields']['robot.tcp_position_m']['value']
        delta = terminal['canonical']['state']['fields']['relations.tcp_target_delta_m']['value']
        distances = [decisions[0]['live_tcp_to_fixed_proxy_m']] + [row['live_tcp_to_fixed_proxy_m'] for row in endpoints]
        changed = [row['step'] for row in decisions
                   if row['selected'] != row['experiment_selection']['unguarded_rule_token_at_same_state']]
        conditions.append({'condition': name, 'goal_anchor': manifest['point'],
            'initial_frame_gate': rows('initial_frame_gate')[0]['array_bytes_exact'],
            'termination': rows('termination')[0], 'actions': [row['token'] for row in actions],
            'action_count': len(actions), 'control_count': len(rows('control_completed')),
            'native_before_count': len(rows('native_before')), 'native_after_count': len(rows('native_after')),
            'capture_count': len(rows('vision_capture')), 'distance_trace_m': distances,
            'initial_distance_m': distances[0], 'final_distance_m': distances[-1],
            'terminal_tcp_world_m': tcp, 'terminal_P_minus_TCP_m': delta,
            'inside_original_axis_stop_cell': bool(np.all(np.abs(delta) <= .005)),
            'guard_changed_selected_token_at_decisions': changed,
            'terminal_decision': terminal, 'execution_contract_violations': sum(
                row['result']['execution_contract_violation'] for row in actions),
            'replay': {key: replay[key] for key in ('status', 'exact_controls', 'exact_native_snapshots', 'exact_captures',
                                                 'policy_or_model_rerun', 'scope')},
            'source_journal_sha256': journal_sha,
            'replay_result_sha256': file_hash(RAW / (name + '-replay') / 'result.json')})
        traces[name] = {'decisions': [{'record_id': row['record_id'], **row['data']} for row in records if row['kind'] == 'decision'],
                       'endpoints': endpoints, 'actions': actions,
                       'source_journal_sha256': journal_sha, 'executor_success_is_evaluator_only': True}
    first = next(i for i, (a, b) in enumerate(zip(traces['whole']['decisions'], traces['neck']['decisions']))
                 if a['selected'] != b['selected'])
    divergence = {name: traces[name]['decisions'][first] for name in probe.ORDER}
    a, b = [divergence[name]['experiment_selection'] for name in probe.ORDER]
    def exclusions(selection):
        return {token: {k: v for k, v in row.items() if k != 'nominal_tcp_to_P_m'}
                for token, row in selection['all_seven_candidates'].items()}
    first_difference = {'decision': first, 'selected': {name: divergence[name]['selected'] for name in probe.ORDER},
        'same_returned_own_packet': a['own_packet'] == b['own_packet'],
        'same_endpoint_geometry_and_exclusions': exclusions(a) == exclusions(b),
        'conditions': divergence}
    endpoints = [np.asarray(row['terminal_tcp_world_m']) for row in conditions]
    cross = {name: {goal: float(np.linalg.norm(tcp-np.asarray(probe.POSITIONS[goal]))) for goal in probe.ORDER}
             for name, tcp in zip(probe.ORDER, endpoints)}
    trace_path = OUTPUT / 'task2_point_anchor_approach_traces.json'
    probe.write(trace_path, {'raw_directory': str(RAW), 'freeze': FREEZE, 'conditions': traces})
    summary = {'raw_directory': str(RAW), 'freeze': FREEZE, 'batch_journal_sha256': file_hash(RAW / 'episodes.jsonl'),
        'admission_sha256': batch[0]['data']['resolved_config']['physical_admission']['admission_sha256'],
        'conditions': conditions, 'first_between_arm_decision_divergence': first_difference,
        'terminal_TCP_separation_m': float(np.linalg.norm(endpoints[1]-endpoints[0])),
        'terminal_TCP_neck_minus_whole_m': (endpoints[1]-endpoints[0]).tolist(),
        'descriptive_cross_anchor_distances_m': cross, 'new_model_calls': 0, 'grasp_attempted': False,
        'task_success_claim': False, 'winner_selected': False, 'traces_sha256': file_hash(trace_path),
        'interpretation': 'Own-anchor distance compares different goals; it does not establish grasp superiority.'}
    plot(conditions, first, OUTPUT / 'task2_point_anchor_approach_curves.png')
    summary['figure_sha256'] = file_hash(OUTPUT / 'task2_point_anchor_approach_curves.png')
    probe.write(OUTPUT / 'task2_point_anchor_approach_summary.json', summary)
    print(json.dumps({'terminal_TCP_separation_m': summary['terminal_TCP_separation_m'],
                     'cross_anchor_distances_m': cross, 'first_divergence': first}, indent=2))


def plot(conditions, first, target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    colors = {'MV_DOWN': '#d98c32', 'MV_FWD': '#4b89c6', 'MV_LEFT': '#649e70'}
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    for row in conditions:
        x = np.arange(len(row['distance_trace_m']))
        y = np.asarray(row['distance_trace_m'])*1000
        line = axes[0].plot(x, y, marker='.', label=row['condition'] + ' → its own fixed anchor')[0]
        steps = row['guard_changed_selected_token_at_decisions']
        axes[0].scatter(steps, y[steps], marker='x', s=60, color=line.get_color())
        axes[0].annotate(f"{y[-1]:.3f} mm; STOP", (x[-1], y[-1]), xytext=(-120, 12),
                         textcoords='offset points', color=line.get_color())
    axes[0].axvline(first, color='gray', linestyle=':', label='first differing decision')
    axes[0].set(xlabel='Completed approach actions', ylabel='TCP to own fixed anchor (mm)',
                title='Different fixed goals; distance alone does not establish grasp quality')
    axes[0].legend()
    axes[0].grid(alpha=.25)
    for i, row in enumerate(conditions):
        for step, token in enumerate(row['actions']):
            axes[1].barh(i, 1, left=step, height=.55, color=colors[token], edgecolor='white', linewidth=.3)
    axes[1].axvline(first, color='gray', linestyle=':')
    axes[1].set(yticks=[0, 1], yticklabels=list(probe.ORDER), xlabel='Action index; each block is one executed primitive')
    axes[1].legend(handles=[Patch(color=color, label=token) for token, color in colors.items()], ncol=3,
                   loc='upper center', bbox_to_anchor=(.5, -.5))
    fig.suptitle('Two fresh fixed-anchor approaches; × marks guard-altered selections')
    fig.tight_layout()
    fig.savefig(target, dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    produce()
