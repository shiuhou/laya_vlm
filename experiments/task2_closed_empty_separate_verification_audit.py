"""Admit unchanged collected source only with its explicitly separate away replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import task2_point_anchor_grasp_transfer_evidence_audit as prior

read, sha, require = prior.read, prior.sha, prior.require
PARTIAL_SHA = '338a373bd60f93f7ae32022656a79a09fd491c55bd096f000d6b8b924d49dbaa'
REVIEW_SHA = '6f92d8c51d83f3a8021b71991abd8c2b4d894d60373ef65eef503af7a5550f17'
LAUNCHER_SHA = '16508f4993fde31ea157d211d25de6640527f3a45f8f9aa45003daf6ad61983c'


def reference(path):
    return {'path': str(path.resolve()), 'sha256': sha(path)}


def audit(partial_path, review_path, verification):
    require(sha(partial_path) == PARTIAL_SHA and sha(review_path) == REVIEW_SHA,
            'exact committed partial-source and invocation reviews')
    partial, review = read(partial_path), read(review_path)
    require(partial['status'] == 'PARTIAL_SOURCE_VERIFIED_NOT_ADMITTED'
            and partial['source_admitted'] is False and review['status'] == 'PASS', 'explicit prior incomplete status')
    matrix = Path(partial['raw_directory'])
    execution = verification.with_name(verification.name + '-execution')
    launch, finished = read(execution / 'launch.json'), read(execution / 'exit.json')
    require(launch['launcher_sha256'] == sha(Path(launch['launcher'])) == LAUNCHER_SHA
            and launch['freeze'] == review['freeze_commit'] == partial['freeze'], 'executed exact frozen launcher')
    require(launch['source'] == str(matrix / 'neck-away') and launch['output'] == str(verification)
            and launch['verification_attempt_number'] == 2 and launch['verification_retry_after_interruption']
            and launch['collection_attempts_in_this_invocation'] == 0 and launch['original_matrix_status'] == 'incomplete'
            and launch['original_matrix_will_be_modified'] is False and launch['wall_limit_s'] == 900,
            'separate second verification scope')
    require(launch['cwd'] == review['execution']['cwd'] and launch['command'][0] == review['execution']['python']
            and launch['environment'] == {k: v for k, v in review['execution']['environment'].items() if k != 'PYTHONDONTWRITEBYTECODE'},
            'executed command cwd and GPU environment')
    require(read(execution / 'review.json') == review, 'exact prospective review copy')
    replay_args = read(execution / 'replay-args.json')
    require(replay_args == {'source': str(matrix / 'neck-away'), 'output': str(verification), 'condition': 'neck-away',
            'seed': 1, 'init_state_id': 0, 'libero_root': '/home/junhongli/projects/LIBERO',
            'config_dir': '/home/junhongli/runs/libero-config', 'review': str(matrix / 'neck-away/review.txt')},
            'actual fixed replay arguments')
    tool_exit = read(execution / 'tool-exit.json')
    require(tool_exit['tool_exit_code'] == tool_exit['launcher_returncode'] == 0
            and tool_exit['verification_attempt_number'] == 2 and tool_exit['collection_attempts'] == 0
            and tool_exit['original_matrix_status'] == 'incomplete', 'external exit observation agrees with launcher')
    require(finished['status'] == 'passed' and finished['returncode'] == 0 and finished['signals'] == []
            and finished['error'] is None and 0 < finished['elapsed_s'] < 900
            and finished['pid'] == launch['pid'] and finished['pgid'] == launch['pgid']
            and finished['verification_attempt_number'] == 2 and finished['collection_attempts'] == 0
            and finished['original_matrix_status'] == 'incomplete', 'successful bounded execution receipt')
    events = [json.loads(line) for line in (execution / 'events.jsonl').read_text().splitlines()]
    require([r['kind'] for r in events] == ['started', 'review_admitted', 'verification_started', 'finished']
            and events[0]['data'] == launch and events[-1]['data'] == finished
            and events[1]['data']['sha256'] == REVIEW_SHA
            and events[2]['data'] == {'collection_dispatch_present': False}
            and [r['elapsed_s'] for r in events] == sorted(r['elapsed_s'] for r in events), 'complete ordered execution events')
    before, after = [read(execution / name) for name in
                     ('original-matrix-inventory-before.json', 'original-matrix-inventory-after.json')]
    current = {str(p.relative_to(matrix)): sha(p) for p in sorted(matrix.rglob('*')) if p.is_file()}
    require(before == after == current, 'entire original matrix remained unchanged and matches current files')
    require(all(current[name] == digest for name, digest in launch['input_sha256'].items()), 'all pinned original inputs')
    require(current['episodes.jsonl'] == partial['matrix_journal_sha256'], 'original incomplete matrix identity')
    for cell in partial['conditions']:
        name = cell['condition']
        require(cell['collection_status'] == 'PASS'
                and current[name + '/episodes.jsonl'] == cell['journal_sha256']
                and current[name + '/sensor-captures.json'] == cell['sensor_evidence']['sensor_manifest_sha256']
                and current[name + '/sensor-seal.json'] == cell['sensor_evidence']['sensor_seal_sha256'],
                'unchanged independently audited collection')
    present = next(c for c in partial['conditions'] if c['condition'] == 'neck-present')
    require(present['replay']['status'] == 'PASS' and all(current['neck-present-replay/' + file] == present['replay'][key]
            for file, key in (('result.json', 'result_sha256'), ('auxiliary-result.json', 'auxiliary_result_sha256'),
                              ('scene-result.json', 'scene_result_sha256'))), 'unchanged independently audited present replay')
    source = matrix / 'neck-away'
    rows = prior.load_journal(source / 'episodes.jsonl')
    replay = prior.replay_audit(source, rows, verification, auxiliary_count=24)
    scene = read(verification / 'scene-result.json')
    require(scene == {'status': 'passed', 'events': 1, 'exact_event_records': 9,
        'source_journal_sha256': sha(source / 'episodes.jsonl'), 'state_restore_used': False}, 'separate exact event replay')
    result_hashes = {name: sha(verification / name) for name in ('result.json', 'scene-result.json', 'auxiliary-result.json')}
    require(read(verification / 'verification-result.json') == {'status': 'passed',
        'verification_attempt_number': 2, 'verification_retry_after_interruption': True, 'collection_attempts': 0,
        'original_matrix_status': 'incomplete', 'original_matrix_unchanged': True,
        'source_journal_sha256': sha(source / 'episodes.jsonl'),
        'source_sensor_seal_sha256': sha(source / 'sensor-seal.json'), 'result_sha256': result_hashes},
        'explicit separate verification result and all replay artifacts')
    require(sorted(p.name for p in verification.iterdir()) == sorted([*result_hashes, 'verification-result.json']),
            'only successful verification results, no hidden mismatch artifacts')
    replay.update(status='PASS', scene_result_sha256=result_hashes['scene-result.json'], exact_event_records=9)
    return {'status': 'PASS', 'source_admitted': True, 'source_admission_status': 'observational-source-qualified',
        'qualification_basis': 'Two complete original sealed collections, original present exact replay, and explicitly separate second away exact verification.',
        'freeze': partial['freeze'], 'raw_directory': str(matrix),
        'original_matrix_status': 'interrupted_incomplete', 'original_matrix_journal_sha256': partial['matrix_journal_sha256'],
        'original_matrix_unchanged': True, 'original_away_replay_executed_controls': None,
        'original_present_replay': {'directory': str(matrix / 'neck-present-replay'), **present['replay']},
        'original_away_verification_attempt': {'attempt_number': 1, 'directory': str(matrix / 'neck-away-replay'),
            'intent_record_seq': 7, 'result_files': [], 'executed_controls': None, 'executed_native_steps': None,
            'status': 'interrupted_without_result', 'observed_outer_exit_code': 143, 'driver_returncode': None,
            'termination_origin': 'not established'},
        'partial_source_audit': reference(partial_path), 'separate_verification_prospective_review': reference(review_path),
        'separate_verification': {'directory': str(verification), 'attempt_number': 2,
            'verification_retry_after_interruption': True, 'replay': replay,
            'result': reference(verification / 'verification-result.json'), 'execution': finished, 'tool_exit_observation': tool_exit,
            'execution_file_sha256': {str(p.relative_to(execution)): sha(p) for p in sorted(execution.iterdir()) if p.is_file()}},
        'original_matrix_file_count': len(current), 'collection_journal_sha256': {c['condition']: c['journal_sha256'] for c in partial['conditions']},
        'new_physics_render_model_LK_FK_calls_during_audit': 0,
        'protocol_interpretation': 'Root authorized this explicit composite qualification after external interruption. The image protocol example requiring a complete matrix is superseded only as to orchestration closure: both original collections and their exact replays are required, with separate attempt-2 away replay bound here. The original matrix remains interrupted/incomplete; scientific feature definitions and all source gates are unchanged.',
        'limitations': ['Original matrix has no termination and is never promoted to a completed matrix.',
            'Original interrupted away replay execution amount and termination origin remain unknown.',
            'Both collected suffixes and exact replays are now verified; this is no extra collection.',
            'Admission establishes source integrity for the fixed post-event feature batch; no settled-empty, identity, holding or task-success inference.',
            'Own-observation read times are recorded; exact sample times remain unknown.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial-review', type=Path, required=True)
    parser.add_argument('--invocation-review', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.partial_review, args.invocation_review, args.verification)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'source_admitted': result['source_admitted'],
                      'output': str(args.output), 'sha256': sha(args.output)}, indent=2))
