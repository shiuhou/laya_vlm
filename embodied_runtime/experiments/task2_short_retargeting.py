"""Fixed two-arm fresh-reset retargeting collection and exact verification."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from . import task2_short_retargeting_callback as suffix
from .records import RunRecorder, code_identity, file_hash, load_records

scene, prior, base, approach = suffix.scene, suffix.prior, suffix.base, suffix.approach
MODULE = 'embodied_runtime.experiments.task2_short_retargeting'
VERSION = 'task2-fixed-away-two-move-retargeting-v1'
PROTOCOL = base.ROOT / 'docs/research/task2_short_retargeting_protocol.md'
RAW = base.RAW
ORDER = suffix.ORDER
SUPPORT = RAW / 'task2-postevent-box-support-run-01'
POINTS = RAW / 'task2-postevent-slow-point-decision-run-01/result.json'
INPUT_SHA = {
    str(SUPPORT / 'result.json'): '27de4407329ce72ebc520a81f2e56bf63b0cd9834aa5618c437866d781c19440',
    str(SUPPORT / 'source-binding.json'): '75e290803f79b8d82959c14b3358719ad406a5ba55700687af46f1d5d03bd87c',
    str(SUPPORT / 'feature-seal.json'): 'a42204c7b2a1a159c40a858efb494a99a7af9a9ab7bcc937a85b7cd8243bc64f',
    str(POINTS): '126a8f18bfd9f9b8ef716c2977e1c7df7cafea8af03748f428250ad3b4a25901',
}
PROVENANCE = ('common', 'anchors', 'goal_anchor', 'condition', 'endpoint_guard',
    'support_guard_identity', 'baseline_protocol_sha256', 'retargeting')
_STARTED = False


def fixed_inputs(frozen, arm):
    for path, sha in INPUT_SHA.items():
        if file_hash(path) != sha:
            raise ValueError('Qualified retargeting input changed: ' + path)
    binding = base.read(SUPPORT / 'source-binding.json')
    for path, sha in binding['source_hashes'].items():
        if file_hash(path) != sha:
            raise ValueError('Support source binding changed: ' + path)
    sealed = base.read(SUPPORT / 'feature-seal.json')
    if sealed['status'] != 'complete' or sealed['result_sha256'] != INPUT_SHA[str(SUPPORT / 'result.json')]:
        raise ValueError('Complete fixed support result required')
    support = base.read(SUPPORT / 'result.json')['support_packets']['away-postevent']
    if (support['status'] != 'admitted_full_rectangle_observed_support'
            or support['valid_point_count'] != 2250 or len(support['full_support']) != 2250
            or support['integer_full_ROI_xyxy'] != [213, 291, 243, 366]):
        raise ValueError('Exact preselected away current full-BOX support required')
    rows = base.read(POINTS)['records']
    cached, fresh = rows[2], rows[3]
    if (cached['case_id'] != 'away-postevent' or fresh['case_id'] != 'away-postevent'
            or cached['arm'] != 'cached' or fresh['arm'] != 'fresh' or cached['own'] != fresh['own']
            or cached['point_world_m'] != frozen['anchors']['whole']['position_world_m']):
        raise ValueError('Same-question fixed cached/current goals and same own source required')
    source = fresh['source']
    frame = RAW / 'task2-closed-empty-scene-run-01' / source['directory'] / source['artifact']
    if file_hash(frame) != source['artifact_sha256']:
        raise ValueError('Exact archived away RGB-D required')
    selected = cached if arm == 'cached' else fresh
    goal = {'position_world_m': selected['point_world_m'],
        'definition': 'native_POINT_containing_pixel_center_depth', 'holding': None}
    guard_packet = {'calibration': frozen['endpoint_guard']['calibration'], 'full_support': support['full_support']}
    kwargs = {'goal': goal, 'goal_source_read_time_s': .5 if arm == 'cached' else source['capture_read_sim_time_s'],
        'goal_provenance': selected['canonical']['state']['meta']['goal_provenance'],
        'guard_packet': guard_packet, 'postevent_frame': str(frame),
        'postevent_frame_sha256': source['artifact_sha256'],
        'postevent_read_time_s': source['capture_read_sim_time_s'], 'postevent_own': fresh['own'],
        'common_evaluation_point': fresh['point_world_m']}
    own = kwargs['postevent_own']
    proprio = {'tcp_pos_world_m': own['robot0_eef_pos'], 'gripper_width_m': float(np.abs(own['robot0_gripper_qpos']).sum()),
        'gripper_command': 'OPEN'}
    view = suffix.retarget_decision(goal, proprio, kwargs['goal_source_read_time_s'],
        kwargs['postevent_read_time_s'], scene.EVENT_STEP, (), arm, kwargs['goal_provenance'])
    token, selection, reason = approach.guard.EndpointSelector(guard_packet)(view, own)
    if token != {'cached': 'MV_DOWN', 'refreshed': 'MV_FWD'}[arm] or any(
            r['excluded'] for r in selection['all_seven_candidates'].values()):
        raise ValueError('Reviewed first-boundary rule result differs; never script a replacement')
    return kwargs, {'canonical': asdict(view), 'selected': token, 'selection': selection, 'reason': reason}


def prepare(args):
    if args.condition not in ORDER:
        raise ValueError('Only cached then refreshed away arms registered')
    frozen, neck, initial_frame = scene.prepare(SimpleNamespace(**{**vars(args), 'condition': 'neck-away'}))
    source_admission = frozen.pop('transfer')['source_admission']
    kwargs, predicted = fixed_inputs(frozen, args.condition)
    frozen.update(condition=args.condition, protocol_sha256=file_hash(PROTOCOL), retargeting={
        'version': VERSION, 'arm': args.condition, 'order': list(ORDER), 'away_fixture_predeclared': True,
        'source_admission': source_admission, 'input_sha256': INPUT_SHA, 'callback_inputs': kwargs,
        'boundary0_no_world_prediction': predicted, 'max_moves_per_arm': 2,
        'source_prefix_verification_only': True, 'archived_controls_in_collection': False,
        'support_fixed_during_suffix': True, 'force_abort_baseline': 'original_initial_frame_gate',
        'force_threshold_N': .05, 'contact_or_execution_abort_halts_remaining_batch': True,
        'world_constructors': 0, 'new_model_calls': 0})
    return frozen, neck, initial_frame


def preflight(args):
    conditions = []
    for arm in ORDER:
        conditions.append(prepare(SimpleNamespace(**{**vars(args), 'condition': arm}))[0])
    value = {'version': VERSION, 'code': code_identity(), 'protocol_sha256': file_hash(PROTOCOL),
        'conditions': conditions, 'order': list(ORDER), 'input_sha256': INPUT_SHA,
        'physics_calls': 0, 'render_calls': 0, 'world_constructions': 0, 'model_calls': 0}
    approach.write(args.output, value)
    return value


def check_review(path, preflight_sha, frozen):
    review = base.read(path)
    expected = {'status': 'PASS', 'freeze_commit': frozen['code']['commit'],
        'preflight_sha256': preflight_sha, 'protocol_sha256': file_hash(PROTOCOL),
        'condition_order': list(ORDER), 'fresh_collection_episodes': 2, 'verification_replays': 2,
        'max_moves_per_arm': 2, 'new_model_calls': 0, 'input_sha256': INPUT_SHA,
        'original_initial_contact_baseline_preserved': True, 'zero_move_STOP_event_replay_verified': True}
    if any(review.get(key) != value for key, value in expected.items()):
        raise ValueError('Exact retargeting code/input/mechanics review PASS required')


def check_collection(path):
    rows, errors = load_records(Path(path) / 'episodes.jsonl')
    term = rows[-1]['data']
    if (errors or rows[-1]['kind'] != 'termination' or any(r['kind'] in ('failure', 'retarget_failure') for r in rows)
            or term.get('first_contact_evaluator_only') is not None
            or term.get('reason') in ('new_robot_contact', 'execution_contract_violation')
            or term.get('reason') not in ('retarget_two_move_budget', 'rule_no_strict_nominal_improvement',
                'endpoint_veto_zero_remaining_pool')):
        raise ValueError('Collection failed or externally aborted; remaining batch not run')
    actions = [r['data'] for r in rows if r['kind'] == 'action_completed']
    suffix_actions = [a for a in actions if a.get('native_phase') == suffix.PHASE]
    if (len(actions) != 29 + len(suffix_actions) or len(suffix_actions) > 2
            or len(suffix_actions) != term['retarget_completed_actions']
            or any(a['token'] not in base.MOVE or a['result']['execution_contract_violation'] for a in suffix_actions)
            or sum(r['kind'] == 'retarget_input_equivalence' for r in rows) != 1):
        raise ValueError('Exact prefix and at most two existing retarget primitives required')
    return term


def worker(args):
    global _STARTED
    if _STARTED:
        raise RuntimeError('One stage per fresh process')
    _STARTED = True
    matrix = Path(args.matrix)
    request = base.read(matrix / 'request.json')
    rows, errors = load_records(matrix / 'episodes.jsonl')
    stage = {'condition': args.condition, 'stage': args.worker_stage}
    expected_order = [{'condition': arm, 'stage': s} for arm in ORDER for s in ('collect', 'replay')]
    intents = [r['data'] for r in rows if r['kind'] == 'stage_intent']
    if errors or rows[-1]['kind'] != 'stage_intent' or intents != expected_order[:len(intents)] or intents[-1] != stage:
        raise ValueError('Exact single-use stage order required')
    args.review = str(matrix / 'review.json')
    frozen, _, _ = prepare(args)
    preflight = base.read(matrix / 'preflight.json')
    if (file_hash(matrix / 'preflight.json') != request['preflight_sha256']
            or file_hash(args.review) != request['review_sha256']
            or frozen != preflight['conditions'][ORDER.index(args.condition)]):
        raise ValueError('Exact reviewed stage configuration changed')
    check_review(args.review, request['preflight_sha256'], frozen)
    if args.worker_stage == 'collect':
        args.output = str(matrix / args.condition)
        callback = suffix.RetargetingCallback(args.condition, **frozen['retargeting']['callback_inputs'])
        base.collect(args, preflight_fn=prepare, protocol=PROTOCOL,
            selector_factory=lambda f: approach.guard.EndpointSelector(f['endpoint_guard']),
            condition=args.condition, decision_fn=approach.point_decision, after_approach=callback)
    else:
        args.source, args.output = str(matrix / args.condition), str(matrix / (args.condition + '-replay'))
        check_collection(args.source)
        event = suffix.RetargetReplay(args.source, args.output)
        def timeout(_signal, _frame):
            raise TimeoutError('Single replay exceeded inherited 900-second wall budget; no retry')
        previous = signal.signal(signal.SIGALRM, timeout)
        signal.alarm(900)
        try:
            base.replay(args, preflight_fn=prepare, provenance_keys=PROVENANCE,
                before_action=event, after_replay=event.finish)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)


def execute_stages(recorder, launch):
    for arm in ORDER:
        for stage in ('collect', 'replay'):
            spec = {'condition': arm, 'stage': stage}
            recorder.record('stage_intent', spec)
            launch(arm, stage)
            recorder.record('stage_complete', spec)


def run_pair(args):
    stored = base.read(args.preflight_receipt)
    frozen, _, _ = prepare(SimpleNamespace(**{**vars(args), 'condition': ORDER[0]}))
    if (stored['conditions'][0] != frozen or stored['code'] != code_identity()
            or stored['order'] != list(ORDER) or stored['physics_calls'] != 0 or stored['world_constructions'] != 0):
        raise ValueError('Matching clean no-world preflight required')
    sha = file_hash(args.preflight_receipt)
    check_review(args.review, sha, frozen)
    request = {'version': VERSION, 'condition_order': list(ORDER), 'preflight_sha256': sha,
        'review_sha256': file_hash(args.review), 'fresh_collection_episodes': 2, 'verification_replays': 2,
        'max_moves_per_arm': 2, 'new_model_calls': 0, 'retries': 0}
    recorder = RunRecorder(args.output, request, {'run_id': Path(args.output).name, 'code': code_identity()})
    approach.write(recorder.output / 'request.json', request)
    for name, path in (('preflight.json', args.preflight_receipt), ('review.json', args.review), ('protocol.md', PROTOCOL)):
        (recorder.output / name).write_bytes(Path(path).read_bytes())
    def launch(arm, stage):
        with (recorder.output / f'{arm}-{stage}.log').open('x') as stream:
            subprocess.run([sys.executable, '-m', MODULE, '--worker-stage', stage, '--matrix', str(recorder.output.resolve()),
                '--condition', arm, '--libero-root', args.libero_root, '--config-dir', args.config_dir],
                stdout=stream, stderr=subprocess.STDOUT, check=True)
        if stage == 'collect':
            check_collection(recorder.output / arm)
        else:
            for name in ('result.json', 'scene-result.json'):
                if base.read(recorder.output / (arm + '-replay') / name)['status'] != 'passed':
                    raise ValueError('Exact replay failed; remaining stages not run')
    try:
        execute_stages(recorder, launch)
        recorder.record('termination', {'reason': 'two_fixed_away_arms_and_exact_replays_complete',
            'fresh_collection_episodes': 2, 'verification_replays': 2, 'new_model_calls': 0, 'retries': 0})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'remaining_stages': 'not_run',
            'contrast_may_be_partial': True, 'winner_selected': False, 'no_retry': True})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--preflight-receipt')
    parser.add_argument('--review')
    parser.add_argument('--condition', choices=ORDER, default=ORDER[0])
    parser.add_argument('--worker-stage', choices=('collect', 'replay'))
    parser.add_argument('--matrix')
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.worker_stage:
        if not args.matrix:
            parser.error('worker requires exact matrix stage intent')
        worker(args)
    elif args.preflight:
        if not args.output:
            parser.error('preflight requires fresh output path')
        preflight(args)
    else:
        if not args.output or not args.preflight_receipt or not args.review:
            parser.error('pair requires output, no-world preflight and exact review')
        run_pair(args)


if __name__ == '__main__':
    main()
