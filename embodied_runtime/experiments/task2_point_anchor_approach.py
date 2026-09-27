"""Fixed whole/neck POINT goals with the original full-BOX endpoint guard."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from ..decision_interface import CanonicalDecisionInput, evidence, geometric_effects
from ..runtime_core import _sha256_json
from . import task2_box_point_boundary as base
from . import task2_endpoint_containment_veto as guard
from . import task2_point_region_control as points
from .records import RunRecorder, file_hash, load_records

VERSION = 'task2-fixed-point-anchors-original-endpoint-guard-v1'
MODULE = 'embodied_runtime.experiments.task2_point_anchor_approach'
PROTOCOL = base.ROOT / 'docs/research/task2_point_anchor_approach_protocol.md'
SOURCE = base.RAW / 'task2-point-region-control-run-01'
ORDER = ('whole', 'neck')
POINT_AUDIT_SHA = 'c083504fe4574f01a472c4cf957a61ff016055ebc069b4fcb23f752d8bc467d1'
SOURCE_SHA = {
    'episodes.jsonl': '57d9ddcd1348303254d32cf844b0a29e75b90c4eef585a8add4c72afd30b508d',
    'request.json': '762de6e4a955882fb987988cf561eba36cc5edb9f7dbd6e873e3dcd965db7b9e',
    'whole/episodes.jsonl': '100701d36b3bd5c79671d0ec1cb7c8b7b2237b9c0bdaa7ccba4d3305f070e19d',
    'whole/generation-return.json': '84a3ac13640b90d7eca42997e0e1cc8749cdcea68ce27026d44d885bc4e2c5e6',
    'whole/sensor-result.json': '87fb2c2b9587ae1cd08f85d4bf331288c20b4b50b65aa6f0132b78294eb3cef5',
    'whole/native-input.json': '23b610a1662fd6b2c0050961be56770c857c7d95fca17c4dfd827f0411e06e2e',
    'whole/manifest.json': '045556bd775ad38bd000785b92ea46ab0f11b65ab18a733b629478273e21cc82',
    'neck/episodes.jsonl': '014458d3129cea55dded74c434eb1bd8adf854f68055a793f659c453311483a3',
    'neck/generation-return.json': '769b1f87d82636a1b56fa82581e8d805df58e0d7baf79aa5e841521ebc723553',
    'neck/sensor-result.json': 'fd6edea327618a8bb86a52dafe48fe2d857a2e71fa7677bdcadb89d65657fd0d',
    'neck/native-input.json': '1a3f1470ed994660cbfb3aa6958724706df098681c1cd432be5bdeb785f704a8',
    'neck/manifest.json': '042617b9071e6e272ec2c63feef46a98cc947d4cddda2da75557d1cd40f1c1c9',
}
POSITIONS = {
    'whole': [-0.11673469557117522, 0.058971097589474636, 0.9883583307522877],
    'neck': [-0.12337491393454869, 0.05776965007435101, 1.0288145621732854],
}


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_anchors():
    for name, expected in SOURCE_SHA.items():
        if file_hash(SOURCE / name) != expected:
            raise ValueError('Fixed POINT source changed: ' + name)
    rows, errors = load_records(SOURCE / 'episodes.jsonl')
    if errors or rows[-1]['data'].get('reason') != 'fixed_pair_complete':
        raise ValueError('Complete registered two-POINT source required')
    anchors = {}
    for condition in points.CONDITIONS:
        name = condition['condition']
        sensor = points.sealed_condition(SOURCE / name)
        native = base.read(SOURCE / name / 'native-input.json')
        if (sensor['status'] != 'admitted_sensor_point' or sensor['point']['position_world_m'] != POSITIONS[name]
                or sensor['source_frame_sha256'] != base.SOURCE_FILES['interaction-observability-paired-01/close/0000.npz']
                or any(native[k] != condition[k] for k in ('condition', 'query', 'question'))):
            raise ValueError('Admitted fixed native POINT and exact description required')
        anchors[name] = {'position_world_m': sensor['point']['position_world_m'],
            'definition': 'cached_native_POINT_containing_pixel_center_depth',
            'identity_verified': None, 'ownership': None, 'holding': None,
            'provenance': {**condition, 'source_directory': str(SOURCE / name),
                'sensor_sha256': SOURCE_SHA[name + '/sensor-result.json'],
                'raw_return_sha256': SOURCE_SHA[name + '/generation-return.json'],
                'journal_sha256': SOURCE_SHA[name + '/episodes.jsonl'],
                'source_frame_sha256': sensor['source_frame_sha256'],
                'parsed_point': sensor['parsed']['points'][0], 'native_projection': sensor['point'],
                'calibration': sensor['calibration'], 'native_admission': sensor['point']['admission'],
                'semantic_confidence': None, 'resolved_depth_ownership': None,
                'researcher_specified_region': True, 'new_model_calls': 0}}
    return anchors


def prepare(args):
    frozen, original_box, frame = base.preflight(args)
    anchors = source_anchors()
    endpoint_guard = guard.prepare_geometry(frame, original_box)
    common = {'version': VERSION, 'condition_order': list(ORDER),
        'point_source_sha256': SOURCE_SHA, 'source_frame_sha256': points.baseline.FRAME_SHA,
        'full_BOX_bounds_xyxy': original_box['box_xyxy'], 'full_BOX_point_count': len(endpoint_guard['full_support']),
        'full_support_sha256': _sha256_json(endpoint_guard['full_support']),
        'calibration_sha256': _sha256_json(endpoint_guard['calibration']),
        'endpoint_guard_sha256': _sha256_json(endpoint_guard),
        'source_roles': {'goal': 'fixed_admitted_native_POINT', 'guard': 'original_full_BOX_observed_depth_support'},
        'baseline_protocol_sha256': file_hash(base.PROTOCOL), 'protocol_sha256': file_hash(PROTOCOL),
        'new_model_calls': 0, 'archived_controls_in_collection': False,
        'original_BOX_point_is_goal': False, 'gap_objective_used': False}
    frozen.update(common=common, anchors=anchors, endpoint_guard=endpoint_guard,
                  protocol_sha256=file_hash(PROTOCOL), baseline_protocol_sha256=file_hash(base.PROTOCOL))
    # Legacy manifest field now denotes the explicit goal only in condition_preflight.
    frozen.pop('point')
    return frozen, anchors, frame


def point_decision(point, proprio, source_time, current_time, revision, history=()):
    """Change POINT provenance only; reuse baseline relation/rule/effect arithmetic."""
    view = base.decision(point, proprio, source_time, current_time, revision, history)
    fields = {**view.state.fields, 'target.position_m': evidence(point['position_world_m'], 'sensor',
        'unchanged cached native POINT pixel-center depth projection; initial fresh frame exactly matched')}
    state = replace(view.state, fields=fields, meta={**view.state.meta, 'goal_anchor': point['provenance'],
        'guard_support_role': 'separate_original_full_BOX_observed_depth_support'})
    return CanonicalDecisionInput(state, view.candidates, geometric_effects(state, view.candidates), view.history)


def condition_preflight(args):
    frozen, anchors, frame = prepare(args)
    if args.condition not in ORDER:
        raise ValueError('Only the fixed whole/neck conditions are registered')
    point = anchors[args.condition]
    frozen.update(point=point, goal_anchor=point['provenance'], condition=args.condition,
                  support_guard_identity=frozen['common'])
    return frozen, point, frame


def verify_review(path, commit):
    content = Path(path).read_text()
    if commit not in content or 'PASS' not in content:
        raise ValueError('Prospective PASS must name exact clean paired-approach freeze')


def checked_artifact(reference):
    if set(reference) != {'path', 'sha256'} or file_hash(reference['path']) != reference['sha256']:
        raise ValueError('Reviewed admission artifact changed')
    return base.read(reference['path'])


def physical_admission(path, frozen):
    """No world creation: validate independent closures and the fixed neck gate."""
    admission = base.read(path)
    if set(admission) != {'point_audit', 'geometry_directory', 'geometry_seal', 'geometry_audit'}:
        raise ValueError('Exact POINT/geometry admission schema required')
    point_audit = checked_artifact(admission['point_audit'])
    # This already-sealed POINT receipt uses lowercase; do not rewrite that evidence.
    if (admission['point_audit']['sha256'] != POINT_AUDIT_SHA
            or point_audit.get('status') != 'pass' or point_audit.get('source_admission') != 'pass'
            or point_audit.get('freeze') != 'd4045496dc330529eb8f637bd46d556fc9bc0598'):
        raise ValueError('Independent full POINT source audit PASS required')
    audited = point_audit.get('conditions', [])
    if len(audited) != 2 or any(row['condition'] != name or row['sensor_sha256'] != SOURCE_SHA[name + '/sensor-result.json']
                                for row, name in zip(audited, ORDER)):
        raise ValueError('POINT audit must bind both fixed admitted anchors')
    directory = Path(admission['geometry_directory'])
    from . import task2_point_goal_cell as cells
    original, _ = cells.prepare()
    request = base.read(directory / 'request.json')
    common_keys = ('calibration', 'full_support', 'terminal_own_packet', 'nominal_step_m')
    if (set(request) != {*common_keys, 'anchors'} or any(request[k] != original[k] for k in common_keys)
            or request['anchors'] != [{'condition': name, 'point_P_world_m': POSITIONS[name]} for name in ORDER]
            or request['full_support'] != frozen['endpoint_guard']['full_support']
            or request['calibration'] != frozen['endpoint_guard']['calibration']):
        raise ValueError('Geometry request must bind original support/own/calibration and both exact POINT goals')
    seal = checked_artifact(admission['geometry_seal'])
    if Path(admission['geometry_seal']['path']).resolve() != (directory / 'feature-seal.json').resolve():
        raise ValueError('Geometry seal is not from the registered directory')
    for name, expected in seal.items():
        if file_hash(directory / name) != expected:
            raise ValueError('Geometry feature seal changed: ' + name)
    audit = checked_artifact(admission['geometry_audit'])
    if audit.get('status') != 'PASS':
        raise ValueError('Independent 18-placement geometry audit PASS required')
    # The closed geometry audit must bind this exact feature seal, not another run.
    if (audit.get('feature_seal_sha256') != admission['geometry_seal']['sha256']
            or audit.get('request_sha256') != file_hash(directory / 'request.json')
            or audit.get('source_admission_audit_sha256') != POINT_AUDIT_SHA
            or audit.get('source_sensor_sha256') != {name: SOURCE_SHA[name + '/sensor-result.json'] for name in ORDER}
            or Path(audit.get('raw_directory', '')).resolve() != directory.resolve()):
        raise ValueError('Geometry audit does not bind the supplied feature seal')
    combined = base.read(directory / 'features' / 'result.json')
    if ('features/result.json' not in seal or combined['condition_order'] != list(ORDER)
            or combined['tensor_shape'] != [2, 9, 1340, 5]):
        raise ValueError('The complete fixed 18-placement result is required')
    for name in ORDER:
        result = base.read(directory / 'features' / name / 'result.json')
        if (f'features/{name}/result.json' not in seal or result['point_P_world_m'] != POSITIONS[name]
                or result['array_shape'] != [9, 1340, 5] or len(result['placements']) != 9
                or result['geometry_order'] != guard.geometry.GEOMS or result['nominal_step_m'] != .01):
            raise ValueError('Both fixed nine-placement geometry results required')
        if result['placements'][0]['kind'] != 'exact_P' or result['placements'][0]['hypothetical_TCP_world_m'] != POSITIONS[name]:
            raise ValueError('Exact TCP=P placement changed')
        if result['terminal_own_packet'] != request['terminal_own_packet']:
            raise ValueError('Geometry result changed the fixed own orientation/jaw packet')
        tensor_path = directory / 'features' / name / 'containment.npz'
        if (f'features/{name}/containment.npz' not in seal
                or file_hash(tensor_path) != result['containment_artifact_sha256']):
            raise ValueError('Every per-point/per-proxy tensor must be sealed')
        with np.load(tensor_path, allow_pickle=False) as arrays:
            inside = arrays['inside']
            if inside.dtype != np.bool_ or inside.shape != (9, 1340, 5):
                raise ValueError('Unexpected geometry containment tensor')
            exact_inside = bool(inside[0].any())
        if exact_inside != result['exact_P_any_containment'] or exact_inside != result['placements'][0]['any_containment']:
            raise ValueError('Exact P aggregate disagrees with its sealed tensor')
        if name == 'neck' and exact_inside:
            raise ValueError('Physical gate rejected: neck exact TCP=P contains observed support in a solid')
    return {'admission_sha256': file_hash(path), 'artifacts': admission,
        'status': 'pass', 'neck_exact_P_observed_solid_containment': False,
        'absence_is_physical_clearance': False, 'conditions_retained': list(ORDER),
        'support_guard_identity': frozen['common']}


def worker(args):
    pair = Path(args.pair)
    rows, errors = load_records(pair / 'episodes.jsonl')
    if (errors or rows[-1]['kind'] != 'stage_intent'
            or rows[-1]['data'] != {'condition': args.condition, 'stage': args.worker_stage}):
        raise ValueError('A matching fixed pair stage intent is required')
    request = base.read(pair / 'request.json')
    args.review = str(pair / 'review.txt')
    if file_hash(args.review) != request['review_sha256']:
        raise ValueError('Prospective pair review changed')
    frozen, _, _ = condition_preflight(args)
    verify_review(args.review, frozen['code']['commit'])
    checked = physical_admission(request['admission_path'], frozen)
    if checked != request['physical_admission']:
        raise ValueError('Physical admission changed between pair stages')
    if args.worker_stage == 'collect':
        args.output = str(pair / args.condition)
        base.collect(args, preflight_fn=condition_preflight, protocol=PROTOCOL,
            selector_factory=lambda f: guard.EndpointSelector(f['endpoint_guard']),
            condition=args.condition + '_native_POINT_original_full_BOX_endpoint_veto', decision_fn=point_decision)
    else:
        args.source, args.output = str(pair / args.condition), str(pair / (args.condition + '-replay'))
        base.replay(args, preflight_fn=condition_preflight,
            provenance_keys=('common', 'anchors', 'goal_anchor', 'condition', 'endpoint_guard',
                             'support_guard_identity', 'baseline_protocol_sha256'))


def execute_stages(recorder, launch):
    for condition in ORDER:
        for stage in ('collect', 'replay'):
            recorder.record('stage_intent', {'condition': condition, 'stage': stage})
            launch(condition, stage)
            recorder.record('stage_complete', {'condition': condition, 'stage': stage})


def check_collection(path):
    rows, errors = load_records(Path(path) / 'episodes.jsonl')
    allowed = {'rule_no_strict_nominal_improvement', 'endpoint_veto_zero_remaining_pool',
               'new_robot_contact', 'action_budget'}
    if (errors or not rows or rows[-1]['kind'] != 'termination' or rows[-1]['data']['reason'] not in allowed
            or any(row['kind'] == 'failure' for row in rows)
            or any(row['data']['result']['execution_contract_violation']
                   for row in rows if row['kind'] == 'action_completed')):
        raise ValueError('Collection failed or violated an executor invariant; stop pair without replay/retry')


def run_pair(args):
    frozen, _, _ = prepare(args)
    verify_review(args.review, frozen['code']['commit'])
    physical = physical_admission(args.admission, frozen)
    # Prospective execution review also binds the final independently closed admission packet.
    if physical['admission_sha256'] not in Path(args.review).read_text():
        raise ValueError('Prospective PASS must bind the final physical-admission SHA256')
    output = Path(args.output)
    request = {'version': VERSION, 'condition_order': list(ORDER), 'fresh_policy_episodes': 2,
        'separate_verification_replays_per_normally_terminated_condition': 1,
        'admission_path': str(Path(args.admission).resolve()), 'physical_admission': physical,
        'review_sha256': file_hash(args.review), 'new_model_calls': 0, 'retries': 0}
    recorder = RunRecorder(output, request, {'run_id': output.name, **frozen})
    write(output / 'request.json', request)
    (output / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output / 'review.txt').write_bytes(Path(args.review).read_bytes())
    def launch(condition, stage):
        with (output / f'{condition}-{stage}.log').open('x') as stream:
            subprocess.run([sys.executable, '-m', MODULE, '--worker-stage', stage, '--pair', str(output.resolve()),
                '--condition', condition, '--libero-root', args.libero_root, '--config-dir', args.config_dir],
                stdout=stream, stderr=subprocess.STDOUT, check=True)
        if stage == 'collect':
            check_collection(output / condition)
        elif base.read(output / (condition + '-replay') / 'result.json')['status'] != 'passed':
            raise ValueError('Exact verification replay did not pass')
    try:
        execute_stages(recorder, launch)
        recorder.record('termination', {'reason': 'both_fixed_conditions_and_replays_complete',
            'fresh_policy_episodes': 2, 'verification_replays': 2, 'new_model_calls': 0,
            'grasp_attempted': False, 'task_success_claim': False, 'winner_selected': False})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'no_retry': True, 'unstarted_stages': 'not_run'})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--review')
    parser.add_argument('--admission')
    parser.add_argument('--run-pair', action='store_true')
    parser.add_argument('--worker-stage', choices=['collect', 'replay'])
    parser.add_argument('--pair')
    parser.add_argument('--condition', choices=ORDER)
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.worker_stage:
        if not args.pair or not args.condition:
            parser.error('internal worker requires pair and condition')
        worker(args)
    elif args.run_pair:
        if not all((args.output, args.review, args.admission)):
            parser.error('run-pair requires output, prospective review and closed physical admission')
        run_pair(args)
    else:
        if not args.output:
            parser.error('no-world preflight requires output')
        frozen, _, _ = prepare(args)
        write(args.output, {**frozen, 'physical_execution_admitted': False,
            'pending_gates': ['independent_POINT_full_audit', 'reviewed_18_placements_neck_exact_P_no_containment',
                              'prospective_exact_freeze_and_admission_review'], 'physics_calls': 0})
        print(json.dumps({'preflight': 'passed', 'world_constructed': False, 'new_model_calls': 0,
                          'physical_execution_admitted': False}))


if __name__ == '__main__':
    main()
