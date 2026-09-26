"""Stream sealed physical counterfactual evidence into a portable report and RGB panel."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from ..runtime_core import MOVE, _sha256_json
from .records import file_hash

EXPECTED = '35f1dee4edfcf4c3d5e059e6db3533d8df9876d0aff7b6adbbdfad7fda2f76d8'


def capture_at_execution_boundary(captures, branch, execution_state, expected_sequence):
    matches = [c for c in captures if c['branch'] == branch
               and c['capture_sim_time'] == execution_state['sim_time']]
    if len(matches) != 1 or matches[0]['capture_seq'] != expected_sequence:
        raise ValueError('Capture time/sequence does not match declared execution boundary')
    return matches[0]


def report(source, output):
    source, output = Path(source), Path(output)
    journal = source/'episodes.jsonl'
    if file_hash(journal) != EXPECTED:
        raise ValueError('Sealed physical journal changed')
    counts, kept, previous = Counter(), defaultdict(list), None
    for index, line in enumerate(journal.open('rb')):
        if not line.endswith(b'\n'):
            raise ValueError('Incomplete journal line')
        row = json.loads(line)
        if (row['seq'] != index or row['previous_record_id'] != previous
                or row['record_id'] != _sha256_json({k: v for k, v in row.items() if k != 'record_id'})):
            raise ValueError('Journal chain mismatch')
        previous = row['record_id']
        counts[row['kind']] += 1
        if row['kind'] not in ('native_before', 'native_after', 'control_started', 'control_completed'):
            kept[row['kind']].append(row['data'])
    if counts['failure'] or counts['first_mismatch'] or kept['termination'][-1]['reason'] != 'seven_branches_complete':
        raise ValueError('Complete seven-branch evidence required for this reporter')
    manifest = kept['run_start'][0]['manifest']
    point = np.asarray(manifest['point']['position_world_m'])
    for capture in kept['capture']:
        if file_hash(source/capture['artifact']) != capture['sha256']:
            raise ValueError('Physical capture changed')
    raw_root = source.parent
    for relative, expected in manifest['frozen_surface_comparison_sha256'].items():
        if file_hash(raw_root/relative) != expected:
            raise ValueError('Frozen prior geometry changed')
    features = json.loads((raw_root/'task2-observed-surface-sweep-run-01/features/features.json').read_text())
    cloud = features['samples']['sample1']['candidates']
    results = []
    for measured in kept['probe_result']:
        token, result = measured['branch'], measured['result']
        before, after = np.asarray(result['before']), np.asarray(result['after'])
        nominal = before+.01*np.asarray(MOVE.get(token, (0., 0., 0.)))
        d0, dn, da = [float(np.linalg.norm(point-position)) for position in (before, nominal, after)]
        observed = {'raw_robot_contact': any(x['raw_robot_rows'] for x in measured['contact_summary'].values()),
                    'strict_above_005N_robot_contact': any(x['strict_above_005N_rows'] for x in measured['contact_summary'].values())}
        comparison = {group: {mode: {'minimum_m': values['union']['minimum_m'],
                                    'contained_point_count': values['union']['contained_point_count'],
                                    'any_contained_point': values['union']['contained_point_count'] > 0}
                             for mode, values in modes.items()}
                      for group, modes in cloud[token]['supports'].items()}
        endpoint = capture_at_execution_boundary(kept['capture'], token, result['execution_after'],
                                                 manifest['prefix_actions']+2)
        results.append({**measured, **observed, 'tcp_to_fixed_P_before_m': d0,
            'nominal_tcp_to_fixed_P_after_m': dn, 'actual_tcp_to_fixed_P_after_m': da,
            'nominal_fixed_P_reduction_m': d0-dn, 'actual_fixed_P_reduction_m': d0-da,
            'frozen_geometric_comparison': comparison, 'endpoint_capture': endpoint,
            'original_loop_STOP_would_execute_this_hold': False if token == 'STOP' else None})
    summary = {'raw_directory': str(source), 'journal_sha256': EXPECTED, 'journal_chain_valid': True,
        'journal_records': sum(counts.values()), 'record_counts': dict(counts), 'producer_commit': manifest['code']['commit'],
        'protocol_sha256': manifest['protocol_sha256'], 'review_sha256': manifest['review_sha256'],
        'source_approach_sha256': manifest['approach_source_sha256'],
        'prior_geometry_sha256': manifest['frozen_surface_comparison_sha256'],
        'fixed_point': manifest['point'], 'prefix_qualifications': kept['prefix_qualified'],
        'current_model_gates': kept['initial_gates'], 'branch_completions': kept['branch_completed'],
        'canonical_results': results, 'termination': kept['termination'][0],
        'all_capture_hashes_checked': len(kept['capture']),
        'limits': ['single retrospective boundary and one trial per branch',
                   'executed STOP/hold differs from original approach-loop termination',
                   'nominal endpoint and sweep flags identical here',
                   'raw contact presence differs from strict force threshold',
                   'no continuation, fitted margin, policy, clearance or grasp qualification']}
    output.mkdir(exist_ok=True, parents=True)
    with (output/'task2_pre22_counterfactual_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    common = capture_at_execution_boundary(kept['capture'], 'MV_FWD', results[0]['result']['execution_before'],
                                           manifest['prefix_actions']+1)
    panels = [(common, 'Common pre-action 22\nTCP to fixed P: '+f'{results[0]["tcp_to_fixed_P_before_m"]*1000:.3f} mm')]
    for row in results:
        name = row['branch'].removeprefix('MV_')
        if name == 'STOP':
            name = 'STOP / executed hold'
        contacts = 'raw hand–bottle contact' if row['raw_robot_contact'] else 'no raw robot contact'
        panels.append((row['endpoint_capture'], f'{name}: {contacts}\n'
                       f'TCP to P: {row["actual_tcp_to_fixed_P_after_m"]*1000:.3f} mm; reduction {row["actual_fixed_P_reduction_m"]*1000:+.3f} mm'))
    for ax, (capture, title) in zip(axes.flat, panels):
        with np.load(source/capture['artifact'], allow_pickle=False) as frame:
            rgb = frame['rgb']
        ax.imshow(rgb, extent=(0, rgb.shape[1], rgb.shape[0], 0))
        ax.set_title(title, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle('Task2 pre-22 counterfactuals: each fresh reset + exact 176-control prefix + one 0.4 s primitive\n'
                 'Actual RGB captures; all validators pass; no >0.05 N robot contact in any branch; no continuation', fontsize=12)
    fig.subplots_adjust(left=.01, right=.99, bottom=.02, top=.88, hspace=.22, wspace=.04)
    fig.savefig(output/'task2_pre22_counterfactual_rgb.png', dpi=170)
    plt.close(fig)
    print(json.dumps({'records': summary['journal_records'], 'captures': len(kept['capture']),
                      'rows': [{k: r[k] for k in ('branch', 'nominal_fixed_P_reduction_m', 'actual_fixed_P_reduction_m', 'raw_robot_contact')}
                               for r in results]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report(args.source, args.output)
