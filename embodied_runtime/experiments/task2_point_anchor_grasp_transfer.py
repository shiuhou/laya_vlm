"""Fixed whole/neck × close/open-hold transfer after fresh sensor-selected approaches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from . import interaction_observability as observations
from . import local_grasp_interface as local
from . import task2_point_anchor_approach as approach
from .records import RunRecorder, file_hash, load_records

base = approach.base
VERSION = 'task2-point-anchor-fixed-grasp-transfer-v1'
MODULE = 'embodied_runtime.experiments.task2_point_anchor_grasp_transfer'
PROTOCOL = base.ROOT / 'docs/research/task2_point_anchor_grasp_transfer_protocol.md'
SOURCE = base.RAW / 'task2-point-anchor-approach-run-01'
ORDER = ('whole-close', 'whole-open_hold', 'neck-close', 'neck-open_hold')
SOURCE_SHA = {
    'episodes.jsonl': '36a1a4a15cbbc9a9beb54e4ac63f5362220be075a8fc012a618dc98f9e88e4ad',
    'whole/episodes.jsonl': '690f81aef2fe5b3d2b5aee09d72f269dfbf7f37ee24c1f9a83c061f7ce4b4541',
    'neck/episodes.jsonl': '3e335ff3d4791f43b74750216fd928470145ea0d34d5a03fbeaba3f2ff492ae8',
    'whole-replay/result.json': 'd784b0bc206fcbe07fc376426610b47e9f10fc38ae23d9a67ae3838dc9aaedd0',
    'neck-replay/result.json': '0134e2abf91aeabb8bc36880a77b3e237f7711e2e88ca38bbed0faadbae5326b',
}
AUDIT = Path('/home/junhongli/projects/laya-embodied-runtime/docs/evidence/autonomous_research/task2_point_anchor_approach_independent_audit.json')
AUDIT_SHA = '0cd47a1433ac25d14b45aa942a17d7322e19865804c33b3adb2fee25a2d2d56e'
PRIOR_ADMISSION = base.RAW / 'task2-point-anchor-approach-admission-01.json'
PRIOR_ADMISSION_SHA = '753fd32754c67265956c845db0d689f7ca41e2ad1aa1155cb75ee6aecdb14fef'
PROVENANCE = ('common', 'anchors', 'goal_anchor', 'condition', 'endpoint_guard',
              'support_guard_identity', 'baseline_protocol_sha256', 'transfer')


def split_condition(condition):
    if condition not in ORDER:
        raise ValueError('Only the four registered cells are allowed')
    return condition.split('-', 1)


def source_admission(frozen):
    for name, digest in SOURCE_SHA.items():
        if file_hash(SOURCE / name) != digest:
            raise ValueError('Closed approach artifact changed: ' + name)
    if file_hash(AUDIT) != AUDIT_SHA or file_hash(PRIOR_ADMISSION) != PRIOR_ADMISSION_SHA:
        raise ValueError('Closed independent approach audit/admission changed')
    audit = base.read(AUDIT)
    if (audit['status'] != 'PASS' or audit['freeze'] != 'fb7899bef22e6473aed30e7dd0051568bd7db7f7'
            or audit['pair_journal_sha256'] != SOURCE_SHA['episodes.jsonl']
            or [row['condition'] for row in audit['conditions']] != list(approach.ORDER)
            or Path(audit['raw_directory']).resolve() != SOURCE.resolve()):
        raise ValueError('Closed exact paired approach audit required')
    for name in approach.ORDER:
        replay = base.read(SOURCE / (name + '-replay') / 'result.json')
        if replay['status'] != 'passed' or replay['source_journal_sha256'] != SOURCE_SHA[name + '/episodes.jsonl']:
            raise ValueError('Both closed source replays required')
    return {'source_directory': str(SOURCE), 'source_sha256': SOURCE_SHA,
        'approach_audit': {'path': str(AUDIT), 'sha256': AUDIT_SHA},
        'prior_physical_admission': approach.physical_admission(PRIOR_ADMISSION, frozen)}


def prepare(args):
    anchor, arm = split_condition(args.condition)
    original_args = SimpleNamespace(**{**vars(args), 'condition': anchor})
    frozen, point, frame = approach.condition_preflight(original_args)
    frozen['transfer'] = {'version': VERSION, 'condition': args.condition, 'anchor': anchor, 'arm': arm,
        'order': list(ORDER), 'source_admission': source_admission(frozen),
        'approach_protocol_sha256': frozen['protocol_sha256'], 'approach_max_actions': 40,
        'scripted_tokens': ['GRASP' if arm == 'close' else 'STOP', 'MV_UP'],
        'scripted_control_count': 16, 'scripted_lift_m': .01,
        'source_prefix_is_verification_only': True, 'archived_controls_in_collection': False,
        'auxiliary_control_captures': 16, 'new_holding_classifier': False}
    frozen['protocol_sha256'] = file_hash(PROTOCOL)
    return frozen, point, frame


def verify_prefix(directory, anchor, termination):
    """Compare only after the unchanged policy has stopped; never return source controls."""
    if (termination['reason'] != 'rule_no_strict_nominal_improvement'
            or termination['first_contact_evaluator_only'] is not None):
        raise ValueError('Original no-improvement STOP without approach contact required')
    current, errors = load_records(Path(directory) / 'episodes.jsonl')
    original, old_errors = load_records(SOURCE / anchor / 'episodes.jsonl')
    if errors or old_errors or any(r['kind'] == 'failure' for r in current + original):
        raise ValueError('Complete clean approach prefix required')
    if original[-1]['kind'] != 'termination' or original[-1]['data'] != termination:
        raise ValueError('Fresh approach termination differs from the fixed source')
    expected = [r for r in original if r['kind'] not in ('run_start', 'termination')]
    actual = [r for r in current if r['kind'] != 'run_start']
    if len(actual) != len(expected):
        raise ValueError('Approach prefix record count mismatch')
    for new, old in zip(actual, expected):
        if new['kind'] != old['kind']:
            raise ValueError('Approach prefix record kind mismatch')
        a, b = new['data'], old['data']
        if new['kind'] == 'vision_capture':
            if file_hash(Path(directory) / a['artifact']) != a['artifact_sha256']:
                raise ValueError('Current approach frame hash mismatch')
            if file_hash(SOURCE / anchor / b['artifact']) != b['artifact_sha256']:
                raise ValueError('Source approach frame hash mismatch')
            with np.load(Path(directory) / a['artifact'], allow_pickle=False) as frame:
                with np.load(SOURCE / anchor / b['artifact'], allow_pickle=False) as reference:
                    base.require_exact_frame(frame, reference)
            a = {k: v for k, v in a.items() if k != 'artifact_sha256'}
            b = {k: v for k, v in b.items() if k != 'artifact_sha256'}
        if a != b:
            raise ValueError('Exact approach prefix mismatch: ' + new['kind'])
    if not actual or actual[-1]['kind'] != 'decision' or actual[-1]['data']['selected'] != 'STOP':
        raise ValueError('Approach STOP must execute no hold')
    return {'anchor': anchor, 'source_journal_sha256': SOURCE_SHA[anchor + '/episodes.jsonl'],
        'exact_records': len(actual), 'exact_primary_captures': sum(r['kind'] == 'vision_capture' for r in actual),
        'source_state_restored': False, 'archived_controls_used': False, 'approach_STOP_executed': False}


def sensor_row(condition, phase, step, control, frame, own, artifact, digest, stream):
    anchor, arm = split_condition(condition)
    return {'condition': condition, 'anchor': anchor, 'arm': arm, 'phase': phase,
        'after_step': step, 'control': control, 'source_capture_stream': stream,
        'source_capture_seq': frame['capture_seq'], 'capture_sim_time': frame['capture_sim_time'],
        'capture_read_sim_time_s': frame['capture_sim_time'], 'cached_geometry_sample_time_s': None,
        'exact_observation_sample_time_s': None, 'tcp_read_sim_time_s': frame['capture_sim_time'] if own is not None else None,
        'own_tcp_world_m': None if own is None else own['robot0_eef_pos'],
        'tcp_source_field': 'control_completed.returned_own_observations.robot0_eef_pos',
        'own_observations': own, 'artifact': artifact, 'artifact_sha256': digest,
        'render_preserves_state_and_caches': True}


class Intervention:
    """One fixed suffix; labels are buffered and cannot select the two tokens."""
    def __init__(self, condition, *, schedule=None, after_primitive=None):
        self.condition = condition
        self.anchor, self.arm = split_condition(condition)
        self.sensors, self.labels = [], []
        self.schedule = schedule if schedule is not None else (
            ('close_or_hold', 'GRASP' if self.arm == 'close' else 'STOP'), ('lift', 'MV_UP'))
        self.after_primitive = after_primitive

    def __call__(self, *, backend, executor, camera, recorder, groups, approach):
        from ..adapters.libero_rgbd import LiberoRgbdSource
        world = backend.world
        prefix = verify_prefix(recorder.output, self.anchor, approach)
        recorder.record('approach_prefix_verified', prefix)
        if backend.step_m != .01 or backend._grip_cmd != -1:
            raise ValueError('Unchanged 10 mm executor and open approach jaw required')
        auxiliary = LiberoRgbdSource(world)
        (recorder.output / 'auxiliary').mkdir()
        attempted, completed, grasp_attempted = 0, 0, False
        grip = 1 if self.arm == 'close' else -1
        try:
            for offset, (phase, token) in enumerate(self.schedule):
                step = approach['completed_actions'] + offset
                recorder.record('action_started', {'step': step, 'token': token, 'native_phase': phase,
                    'selection': 'registered_scripted_intervention', 'arm': self.arm})
                attempted += 1
                grasp_attempted |= token == 'GRASP'
                def after_control(row):
                    with local.read_only_measurement(world):
                        frame = auxiliary.capture()
                        label = observations.evaluation(world)
                        snapshot = local.contact_snapshot(world, groups)
                    artifact = f'auxiliary/capture-{frame["capture_seq"]:06d}.npz'
                    with (recorder.output / artifact).open('xb') as stream:
                        np.savez_compressed(stream, **{key: frame[key] for key in base.FRAME_KEYS})
                    sensed = sensor_row(self.condition, phase, step, row['control'], frame,
                        row['returned_own_observations'], artifact, file_hash(recorder.output / artifact), 'auxiliary')
                    sensed['own_source'] = {'journal': 'episodes.jsonl', 'kind': 'control_completed',
                                           'step': step, 'control': row['control']}
                    self.sensors.append(sensed)
                    recorder.record('auxiliary_capture', sensed)
                    self.labels.append({'phase': phase, 'step': step, 'control': row['control'],
                        'label': label, 'raw_contact_snapshot': snapshot})
                tracking = {'control': None}
                with base.observe_controls(world, recorder, step, tracking, expected_grip=grip, after_control=after_control) as controls:
                    with local.native_observer(world, recorder, phase, step, tracking, groups) as native:
                        result = executor.execute(token)
                completed += 1
                recorder.record('action_completed', {'step': step, 'token': token, 'native_phase': phase,
                    'selection': 'registered_scripted_intervention', 'arm': self.arm,
                    'result': result, 'controls': len(controls), 'native_integrations': len(native)})
                with local.read_only_measurement(world):
                    frame, proprio = camera.capture(), backend.proprioception()
                recorder.capture(frame)
                recorder.record('endpoint', {'step': step, 'native_phase': phase, 'proprioception': proprio,
                    'own_observations': {key: np.asarray(world.obs[key]).tolist() for key in base.OBS_KEYS},
                    'capture_seq': frame['capture_seq']})
                local.require_pass(result)
                if len(controls) != 8 or len(native) != 200 or any(sum(r['control'] == c for r in native) != 25 for c in range(8)):
                    raise RuntimeError('Unexpected postapproach native action/control counts')
                if any(c['unexpected_robot_contact'] for r in native for stage in ('before', 'after') for c in r[stage]['contacts']):
                    raise RuntimeError('unexpected_robot_contact_at_native_stage')
                if self.after_primitive is not None:
                    self.after_primitive(recorder, offset, step)
            return {**approach, 'reason': 'fixed_approach_and_scripted_suffix_complete',
                'approach_termination': approach, 'scripted_attempted_actions': attempted,
                'scripted_completed_actions': completed, 'attempted_actions': approach['attempted_actions'] + attempted,
                'completed_actions': approach['completed_actions'] + completed, 'last_step': step,
                'grasp_attempted': grasp_attempted, 'scripted_intervention': True, 'winner_selected': False}
        except BaseException as exc:
            recorder.record('intervention_failure', {'exception': repr(exc), 'scripted_attempted_actions': attempted,
                'scripted_completed_actions': completed, 'grasp_attempted': grasp_attempted,
                'total_attempted_actions': approach['attempted_actions'] + attempted,
                'total_completed_actions': approach['completed_actions'] + completed,
                'phase': phase, 'step': step, 'token': token, 'no_retry': True})
            raise

    def seal(self, directory):
        """Close sensor-only evidence before writing the separate evaluator labels."""
        directory = Path(directory)
        if not (directory / 'episodes.jsonl').exists():
            return
        rows, errors = load_records(directory / 'episodes.jsonl')
        initial = next((r['data'] for r in rows if r['kind'] == 'initial_frame_gate'), None)
        endpoints = {r['data']['capture_seq']: r['data'] for r in rows if r['kind'] == 'endpoint'}
        sensor_rows = []
        for row in rows:
            if row['kind'] == 'vision_capture' and initial is not None:
                frame = row['data']
                endpoint = endpoints.get(frame['capture_seq'])
                if endpoint and 'native_phase' in endpoint:
                    continue  # Same endpoint already retained in the auxiliary chronology.
                reset = frame['capture_seq'] == 1
                own = (initial['initial_own_observations'] if reset else
                       (None if endpoint is None else endpoint['own_observations']))
                sensed = sensor_row(self.condition, 'reset' if reset else 'approach',
                    -1 if reset else (None if endpoint is None else endpoint['step']), None if endpoint is None else 7,
                    frame, own, frame['artifact'], frame['artifact_sha256'], 'primary')
                own_kind = 'initial_frame_gate' if reset else 'endpoint'
                sensed['tcp_source_field'] = (own_kind + '.' +
                    ('initial_own_observations' if reset else 'own_observations') + '.robot0_eef_pos') if own is not None else None
                sensed['own_packet_status'] = 'recorded' if own is not None else 'missing_endpoint_in_partial_run'
                sensed['own_source'] = {'journal': 'episodes.jsonl', 'kind': own_kind,
                                       'step': None if endpoint is None else endpoint['step']}
                sensed['capture_record_id'] = row['record_id']
                sensor_rows.append(sensed)
        sensor_rows.extend(self.sensors)
        for i, row in enumerate(sensor_rows):
            row['capture_id'] = i
        approach.write(directory / 'sensor-captures.json', sensor_rows)
        hashes = {'sensor-captures.json': file_hash(directory / 'sensor-captures.json')}
        hashes.update({row['artifact']: row['artifact_sha256'] for row in sensor_rows})
        approach.write(directory / 'sensor-seal.json', {'sha256': hashes,
            'journal_sha256_linkage_only': file_hash(directory / 'episodes.jsonl'),
            'journal_parse_errors': errors, 'holding': None,
            'policy': 'fresh_sensor_selected_approach_then_fixed_scripted_intervention'})
        (directory / 'evaluator-only').mkdir()
        approach.write(directory / 'evaluator-only' / 'labels.json', self.labels)


class AuxiliaryReplay:
    def __init__(self, directory, *, expected_count=16):
        self.directory = Path(directory)
        rows, errors = load_records(self.directory / 'episodes.jsonl')
        if errors:
            raise ValueError('Complete source journal required')
        captures = [r['data'] for r in rows if r['kind'] == 'auxiliary_capture']
        self.expected = {(r['after_step'], r['control']): r for r in captures}
        if len(captures) != expected_count or len(self.expected) != expected_count:
            raise ValueError(f'All {expected_count} auxiliary captures required')
        self.camera, self.checked = None, []

    def __call__(self, world, action, control):
        if 'native_phase' not in action:
            return
        from ..adapters.libero_rgbd import LiberoRgbdSource
        if self.camera is None:
            self.camera = LiberoRgbdSource(world)
        expected = self.expected.pop((action['step'], control))
        if file_hash(self.directory / expected['artifact']) != expected['artifact_sha256']:
            raise ValueError('Auxiliary source artifact changed')
        with local.read_only_measurement(world):
            frame = self.camera.capture()
        with np.load(self.directory / expected['artifact'], allow_pickle=False) as reference:
            checks = base.require_exact_frame(frame, reference)
        own = {key: np.asarray(world.obs[key]).tolist() for key in base.OBS_KEYS}
        if (frame['capture_seq'] != expected['source_capture_seq'] or frame['capture_sim_time'] != expected['capture_sim_time']
                or own != expected['own_observations'] or action['native_phase'] != expected['phase']):
            raise ValueError('Auxiliary replay timing/own observation/phase mismatch')
        self.checked.append({'step': action['step'], 'control': control, 'array_bytes_exact': checks})


def check_collection(directory, *, scripted_action_count=2):
    rows, errors = load_records(Path(directory) / 'episodes.jsonl')
    if (errors or not rows or rows[-1]['kind'] != 'termination'
            or rows[-1]['data']['reason'] != 'fixed_approach_and_scripted_suffix_complete'
            or rows[-1]['data']['scripted_completed_actions'] != scripted_action_count
            or any(r['kind'] in ('failure', 'intervention_failure') for r in rows)):
        raise ValueError('Collection incomplete; stop matrix without replay or retry')
    for row in rows:
        if row['kind'] == 'action_completed':
            local.require_pass(row['data']['result'])


def execute_stages(recorder, launch, *, order=ORDER):
    for condition in order:
        for stage in ('collect', 'replay'):
            recorder.record('stage_intent', {'condition': condition, 'stage': stage})
            launch(condition, stage)
            recorder.record('stage_complete', {'condition': condition, 'stage': stage})


def verify_review(path, freeze, preflight_sha):
    content = Path(path).read_text()
    if 'PASS' not in content or freeze not in content or preflight_sha not in content:
        raise ValueError('Prospective PASS must bind exact clean freeze and no-world preflight SHA256')


def worker(args, *, preflight_fn=prepare, protocol=PROTOCOL, intervention_factory=Intervention, auxiliary_count=16):
    directory = Path(args.matrix)
    request = base.read(directory / 'request.json')
    rows, errors = load_records(directory / 'episodes.jsonl')
    if errors or rows[-1]['kind'] != 'stage_intent' or rows[-1]['data'] != {'condition': args.condition, 'stage': args.worker_stage}:
        raise ValueError('Matching fixed matrix stage intent required')
    args.review = str(directory / 'review.txt')
    frozen, _, _ = preflight_fn(args)
    verify_review(args.review, frozen['code']['commit'], request['preflight_sha256'])
    if (file_hash(args.review) != request['review_sha256']
            or file_hash(directory / 'preflight.json') != request['preflight_sha256']
            or frozen['transfer']['source_admission'] != request['source_admission']):
        raise ValueError('Reviewed admission changed between stages')
    if args.worker_stage == 'collect':
        args.output = str(directory / args.condition)
        suffix = intervention_factory(args.condition)
        try:
            base.collect(args, preflight_fn=preflight_fn, protocol=protocol,
                selector_factory=lambda f: approach.guard.EndpointSelector(f['endpoint_guard']),
                condition=args.condition, decision_fn=approach.point_decision, after_approach=suffix)
        finally:
            suffix.seal(args.output)
    else:
        args.source, args.output = str(directory / args.condition), str(directory / (args.condition + '-replay'))
        auxiliary = AuxiliaryReplay(args.source, expected_count=auxiliary_count)
        base.replay(args, preflight_fn=preflight_fn, provenance_keys=PROVENANCE, after_control=auxiliary)
        if auxiliary.expected or len(auxiliary.checked) != auxiliary_count:
            raise ValueError('Auxiliary replay incomplete')
        approach.write(Path(args.output) / 'auxiliary-result.json', {'status': 'passed',
            'source_sensor_seal_sha256': file_hash(Path(args.source) / 'sensor-seal.json'), 'captures': auxiliary.checked})


def run_matrix(args, *, preflight_fn=prepare, protocol=PROTOCOL, module=MODULE, order=ORDER,
               version=VERSION, scripted_action_count=2, completion_reason='all_four_fixed_cells_and_replays_complete'):
    frozen, _, _ = preflight_fn(args)
    preflight = base.read(args.preflight_receipt)
    if any(preflight.get(key) != value for key, value in frozen.items()) or preflight['physics_calls'] != 0:
        raise ValueError('Matching no-world preflight required')
    preflight_sha = file_hash(args.preflight_receipt)
    verify_review(args.review, frozen['code']['commit'], preflight_sha)
    request = {'version': version, 'condition_order': list(order), 'fresh_policy_episodes': len(order),
        'source_admission': frozen['transfer']['source_admission'], 'preflight_sha256': preflight_sha,
        'review_sha256': file_hash(args.review), 'new_model_calls': 0, 'retries': 0}
    recorder = RunRecorder(args.output, request, {'run_id': Path(args.output).name, **frozen})
    approach.write(recorder.output / 'request.json', request)
    (recorder.output / 'review.txt').write_bytes(Path(args.review).read_bytes())
    (recorder.output / 'protocol.md').write_bytes(protocol.read_bytes())
    (recorder.output / 'preflight.json').write_bytes(Path(args.preflight_receipt).read_bytes())
    def launch(condition, stage):
        with (recorder.output / f'{condition}-{stage}.log').open('x') as stream:
            subprocess.run([sys.executable, '-m', module, '--worker-stage', stage, '--matrix', str(recorder.output.resolve()),
                '--condition', condition, '--libero-root', args.libero_root, '--config-dir', args.config_dir],
                stdout=stream, stderr=subprocess.STDOUT, check=True)
        if stage == 'collect':
            check_collection(recorder.output / condition, scripted_action_count=scripted_action_count)
        else:
            for name in ('result.json', 'auxiliary-result.json'):
                if base.read(recorder.output / (condition + '-replay') / name)['status'] != 'passed':
                    raise ValueError('Exact verification replay failed')
    try:
        execute_stages(recorder, launch, order=order)
        recorder.record('termination', {'reason': completion_reason,
            'fresh_policy_episodes': len(order), 'verification_replays': len(order), 'winner_selected': False, 'task_success_claim': False})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'no_retry': True, 'unstarted_stages': 'not_run'})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--review')
    parser.add_argument('--preflight-receipt')
    parser.add_argument('--run-matrix', action='store_true')
    parser.add_argument('--worker-stage', choices=('collect', 'replay'))
    parser.add_argument('--matrix')
    parser.add_argument('--condition', choices=ORDER, default=ORDER[0])
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.worker_stage:
        if not args.matrix:
            parser.error('worker requires matrix')
        worker(args)
    elif args.run_matrix:
        if not all((args.output, args.review, args.preflight_receipt)):
            parser.error('matrix requires output, reviewed preflight receipt and prospective review')
        run_matrix(args)
    else:
        if not args.output:
            parser.error('no-world preflight requires output')
        frozen, _, _ = prepare(args)
        approach.write(args.output, {**frozen, 'physics_calls': 0, 'physical_execution_admitted': False,
            'pending_gate': 'prospective_review_of_exact_freeze_and_this_preflight_receipt'})
        print(json.dumps({'preflight': 'passed', 'world_constructed': False, 'physical_execution_admitted': False}))


if __name__ == '__main__':
    main()
