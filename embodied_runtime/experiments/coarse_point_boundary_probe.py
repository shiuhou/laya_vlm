"""One fresh boundary-finding extension of the frozen coarse POINT experiment."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import coarse_point_probe as base
from .predicate_verification import one_record
from .records import file_hash, load_records

VERSION = 'fresh-point-boundary-finding-v1'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/coarse_point_boundary_probe_protocol.md'
BASELINE_COMMIT = 'a1c76d4764ce19ca25ea68042ceb4aebbafe2df8'
BASELINE_SHA256 = '6eb87f1b1e0f69376c9c62f926fcc741cecbf736221977eea00a715868bcd23c'
MATCHED_ARGUMENTS = ('seed', 'init_state_id', 'device', 'locateanything_path', 'libero_root', 'config_dir', 'timeout_s')


def frozen_baseline(directory):
    """Inspect provenance only; never restore a state or execute archived controls."""
    path = Path(directory) / 'episodes.jsonl'
    if file_hash(path) != BASELINE_SHA256:
        raise ValueError('frozen 20-action baseline identity mismatch')
    rows, errors = load_records(path)
    start = one_record(rows, 'run_start')
    config = start['resolved_config']
    actions = [r['data'] for r in rows if r['kind'] == 'action']
    if (errors or start['manifest']['code']['commit'] != BASELINE_COMMIT
            or config['condition'] != 'rule' or config['steps'] != 20
            or config['version'] != base.VERSION
            or len(actions) != 20
            or len([r for r in rows if r['kind'] == 'control_observation']) != 160
            or any(r['kind'] == 'failure' for r in rows)
            or any(a['result']['execution_contract_violation'] or a['new_robot_contact_pairs'] for a in actions)
            or one_record(rows, 'termination') != {
                'reason': 'action_budget', 'executed_primitives': 20, 'boundary': 20,
                'laya_decisions': 0, 'manipulation_success_claim': False}):
        raise ValueError('complete clean 20-action budget baseline required')
    return config


def validate_args(args):
    if (not 1 <= args.steps <= 40 or args.seed != 1 or args.init_state_id != 0
            or args.condition != 'rule' or not 0 < args.timeout_s <= 900):
        raise ValueError('boundary profile requires rule/init0/seed1 and at most 40 primitives/900 seconds')
    if Path(args.output).resolve() == Path(args.baseline_source).resolve():
        raise ValueError('new output required; historical baseline must remain untouched')


def run(args):
    validate_args(args)
    previous = frozen_baseline(args.baseline_source)
    if any(getattr(args, key) != previous[key] for key in MATCHED_ARGUMENTS):
        raise ValueError('physical/model settings differ from frozen 20-action baseline')
    profile = {
        'name': VERSION, 'primary_outcome': 'first_boundary_not_manipulation_success',
        'max_executed_primitives': args.steps, 'absolute_budget_ceiling': 40,
        'fresh_reset': True, 'archived_controls_executed': False, 'archived_state_restored': False,
        'baseline_source': str(Path(args.baseline_source).resolve()),
        'baseline_sha256': BASELINE_SHA256, 'baseline_commit': BASELINE_COMMIT,
        'baseline_protocol_sha256': previous['protocol_sha256'], 'base_policy_version': base.VERSION,
        'changed_behavior': 'execution_budget_only',
        'unchanged': ['POINT query/settings/admission', 'canonical nominal rule', 'seven-action family',
                      'atomic executor', 'external contact abort', 'execution contracts', 'wall limit'],
        'contact_classification': 'posthoc raw existing contact evidence and designated-handle relation; evaluator only',
        'no_automatic_budget_extension': True,
    }
    return base.run(args, protocol=PROTOCOL, experiment_profile=profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-source', default='runs/autonomous-research/coarse-point-rule-01')
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--init-state-id', type=int, default=0)
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--locateanything-path', default='/home/junhongli/models/huggingface/LocateAnything-3B')
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.add_argument('--timeout-s', type=float, default=900.)
    parser.set_defaults(condition='rule')
    print(run(parser.parse_args()))


if __name__ == '__main__':
    main()
