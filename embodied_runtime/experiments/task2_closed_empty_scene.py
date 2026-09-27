"""Fixed NECK present/away scene intervention; experimental collection/replay only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from . import task2_additional_stationary_grasp as previous
from . import task2_pre22_counterfactual as model_source
from .records import file_hash, jsonable, load_records

prior = previous.prior
base = prior.base
VERSION = 'task2-neck-matched-closed-empty-scene-v1'
MODULE = 'embodied_runtime.experiments.task2_closed_empty_scene'
PROTOCOL = base.ROOT / 'docs/research/task2_closed_empty_scene_protocol.md'
ORDER = ('neck-present', 'neck-away')
SCHEDULE = previous.SCHEDULE
EVENT_STEP = 29
JOINT = 'wine_bottle_1_joint0'
DELTA = {'neck-present': [0., 0., 0.], 'neck-away': [.35, 0., 0.]}
STATIC = base.ROOT / 'docs/evidence/autonomous_research/task2_closed_empty_static_bounds.json'
STATIC_SOURCE = STATIC.with_name('task2_closed_empty_static_bounds_source.py')
STATE_FIELDS = ('qpos', 'qvel', 'act', 'ctrl', 'qacc_warmstart', 'qfrc_applied',
                'xfrc_applied', 'mocap_pos', 'mocap_quat', 'userdata', 'eq_active')
CACHE_FIELDS = ('geom_xpos', 'geom_xmat', 'site_xpos', 'site_xmat', 'cam_xpos',
                'cam_xmat', 'sensordata', 'qacc')
SOLVER_FIELDS = ('qfrc_constraint', 'efc_force', 'efc_state')
EVENT_KINDS = ('scene_intervention_intent', 'scene_state', 'scene_boundary',
               'scene_geometry_admission', 'scene_intervention_completed')


def checked_static():
    value = base.read(STATIC)
    if file_hash(STATIC_SOURCE) != value['script_sha256']:
        raise ValueError('Static placement calculation source changed')
    for path_key, hash_key in (('xml', 'xml_sha256'), ('journal', 'journal_sha256'),
            ('static_model_journal', 'static_model_journal_sha256'), ('BDDL', 'BDDL_sha256'),
            ('reset_source', 'reset_source_sha256')):
        if file_hash(value[path_key]) != value[hash_key]:
            raise ValueError('Static placement source changed: ' + path_key)
    for path, digest in value['mesh_sha256'].items():
        if file_hash(path) != digest:
            raise ValueError('Static collision mesh changed')
    if (value['delta_world_m'] != DELTA['neck-away'] or not value['table_XY_contains_relocated_collision_geometry']
            or not value['all_finite_non_table_non_target_X_bounds_disjoint']
            or value['direct_worldbody_collision_geometries'][0]['relocated_bottle_Z_clearance_lower_bound_m'] <= 0
            or not all(v > 0 for v in value['X_separation_lower_bounds_m'].values())):
        raise ValueError('Fixed supported separated placement required')
    return value


def prepare(args):
    if args.condition not in ORDER:
        raise ValueError('Only fixed neck-present / neck-away cells are registered')
    frozen, point, frame = previous.prepare(SimpleNamespace(**{**vars(args), 'condition': 'neck-close'}))
    static = checked_static()
    frozen['condition'] = args.condition
    frozen['transfer'] = {**frozen['transfer'], 'version': VERSION, 'condition': args.condition,
        'order': list(ORDER), 'scene_intervention': {'privileged': True, 'joint': JOINT,
            'step': EVENT_STEP, 'delta_world_m': DELTA[args.condition], 'one_forward': True,
            'one_forced_observation_refresh': True, 'scene_boundary_captures': 2,
            'suffix_frames': 25, 'through_event_primary_tracking': False},
        'first_GRASP_prefix_is_verification_only': False,
        'source_admission': {**frozen['transfer']['source_admission'],
            'placement_bounds_sha256': file_hash(STATIC), 'placement_source_sha256': file_hash(STATIC_SOURCE),
            'neck_additional_journal_sha256': static['journal_sha256']}}
    frozen['protocol_sha256'] = file_hash(PROTOCOL)
    return frozen, point, frame


def own_packet(observations):
    result = {key: np.asarray(observations[key]).tolist() for key in base.OBS_KEYS}
    for key, size in zip(base.OBS_KEYS, (3, 4, 2, 2), strict=True):
        if np.asarray(result[key]).shape != (size,) or not np.isfinite(result[key]).all():
            raise ValueError('Complete finite named own observation required: ' + key)
    return result


def document(value):
    """Stable audit serialization; never fall back to process-specific object repr."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): document(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [document(v) for v in value]
    if callable(value):
        return {'callable': value.__module__ + '.' + value.__qualname__}
    if hasattr(value, '__dict__'):
        return {'class': type(value).__module__ + '.' + type(value).__qualname__,
                'state': document({k: v for k, v in vars(value).items() if k != 'sim'})}
    raise TypeError('Unsupported audit state type: ' + str(type(value)))


def contact_solver_state(world):
    """Read existing contact/solver buffers without forward or solver reconstruction."""
    rows = []
    for index in range(world.data.ncon):
        contact = world.data.contact[index]
        pair = [int(contact.geom1), int(contact.geom2)]
        force = np.zeros(6)
        world.mujoco.mj_contactForce(world.model, world.data, index, force)
        rows.append({'index': index, 'geom_ids': pair,
            'geom_names': [world.env.sim.model.geom_id2name(g) for g in pair],
            'distance_m': float(contact.dist), 'position_m': contact.pos.tolist(),
            'frame': contact.frame.tolist(), 'dimension': int(contact.dim),
            'efc_address': int(contact.efc_address), 'force_contact_frame': force.tolist()})
    return {'ncon': int(world.data.ncon), 'nefc': int(world.data.nefc), 'contacts': rows,
        'named_solver_buffers': {name: {'shape': list(np.asarray(getattr(world.data, name)).shape),
            'sha256': prior.local.array_hash(getattr(world.data, name))} for name in SOLVER_FIELDS},
        'coverage': 'listed contact fields and named solver buffers only; not every MuJoCo workspace'}


def snapshot(backend):
    world, env = backend.world, backend.world.env.env
    robot = world.env.robots[0]
    return {'sim_time_s': float(world.data.time),
        'state': {name: np.asarray(getattr(world.data, name)).tolist() for name in STATE_FIELDS},
        'integration_fingerprint': prior.local.integration_fingerprint(world),
        'caches': {name: np.asarray(getattr(world.data, name)).tolist() for name in CACHE_FIELDS},
        'contact_solver': contact_solver_state(world),
        'controller': document({k: v for k, v in vars(robot.controller).items() if k != 'sim'}),
        'robot_recent': document({k: v for k, v in vars(robot).items() if k.startswith('recent_') or k == 'torques'}),
        'gripper_current_action': document(robot.gripper.current_action),
        'retained_gripper_command': float(backend._grip_cmd),
        'environment_clock': document({name: getattr(env, name) for name in ('cur_time', 'timestep', 'done')}),
        'observable_state': document({name: vars(value) for name, value in env._observables.items()}),
        'observation_cache': document(env._obs_cache), 'own_observations': own_packet(world.obs),
        'numpy_rng': document(np.random.get_state()), 'python_rng': document(random.getstate())}


def changes(before, after, path=''):
    """Exact changed leaf inventory, with values; shape/key changes remain explicit."""
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [item for key in before for item in changes(before[key], after[key], path + '/' + key)]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [item for i, (a, b) in enumerate(zip(before, after, strict=True))
                for item in changes(a, b, path + '/' + str(i))]
    return [] if before == after else [{'path': path, 'before': before, 'after': after}]


def require_write(before, after, address, delta):
    expected = json.loads(json.dumps(before))
    for i in range(3):
        expected['state']['qpos'][address + i] += delta[i]
    # The integration digest necessarily changes with the explicit qpos write.
    expected['integration_fingerprint'] = after['integration_fingerprint']
    if expected != after:
        raise ValueError('Scene write changed fields outside the named object translation')


def require_sync(before, after):
    for key in ('sim_time_s', 'controller', 'robot_recent', 'gripper_current_action',
                'retained_gripper_command', 'environment_clock', 'numpy_rng', 'python_rng'):
        if before[key] != after[key]:
            raise ValueError('Scene synchronization changed invariant: ' + key)
    for name in STATE_FIELDS:
        if name != 'qacc_warmstart' and before['state'][name] != after['state'][name]:
            raise ValueError('Scene synchronization changed primary state: ' + name)


def model_gate(world, static):
    records, errors = load_records(static['static_model_journal'])
    if errors:
        raise ValueError('Static model journal is incomplete')
    expected = records[static['static_model_identity_record_seq']]['data']['current_model_identity']
    actual = {key: prior.local.array_hash(getattr(world.model, key)) for key in model_source.MODEL_ARRAYS}
    if actual != expected['model_array_sha256']:
        raise ValueError('Compiled scene/robot/controller model differs from reviewed static source')
    joint = world.env.sim.model.joint_name2id(JOINT)
    address = int(world.model.jnt_qposadr[joint])
    if int(world.model.jnt_type[joint]) != 0 or address != 16:
        raise ValueError('Expected named bottle free joint at verified address')
    if world.data.qpos.tolist() != static['qpos']:
        raise ValueError('Fresh neck pre-event qpos differs from the reviewed geometry boundary')
    return address, actual


def geometry_admission(world, condition):
    """Privileged setup gate on synchronized native geometry, never sensor input."""
    groups = {key: [] for key in ('robot', 'bowl', 'bottle', 'cabinet', 'rack', 'table', 'floor')}
    prefixes = {'robot': ('robot0_', 'gripper0_', 'mount0_'), 'bowl': ('akita_black_bowl_1_',),
        'bottle': ('wine_bottle_1_',), 'cabinet': ('white_cabinet_1_',), 'rack': ('wine_rack_1_',)}
    for geom in range(world.model.ngeom):
        if not (world.model.geom_contype[geom] or world.model.geom_conaffinity[geom]):
            continue
        name = world.env.sim.model.geom_id2name(geom)
        group = next((key for key, names in prefixes.items() if name.startswith(names)), None)
        group = {'table_collision': 'table', 'floor': 'floor'}.get(name, group)
        if group is None:
            raise ValueError('Unaccounted scene collision geometry: ' + name)
        if group == 'floor':
            if int(world.model.geom_type[geom]) != 0:
                raise ValueError('Reviewed floor must remain a plane')
            groups[group].append({'name': name, 'position': world.data.geom_xpos[geom].tolist(),
                                  'rotation': world.data.geom_xmat[geom].tolist()})
            continue
        points = world.scene.local_vertices(geom) @ world.data.geom_xmat[geom].reshape(3, 3).T + world.data.geom_xpos[geom]
        groups[group].append({'name': name, 'low': points.min(axis=0).tolist(), 'high': points.max(axis=0).tolist()})
    expected = {'robot': 16, 'bowl': 40, 'bottle': 21, 'cabinet': 36, 'rack': 9, 'table': 1, 'floor': 1}
    if {key: len(value) for key, value in groups.items()} != expected:
        raise ValueError('Collision geometry inventory differs from static placement source')
    bounds = {key: {'low': np.min([g['low'] for g in value], axis=0).tolist(),
                    'high': np.max([g['high'] for g in value], axis=0).tolist()}
              for key, value in groups.items() if key != 'floor'}
    bottle, table = bounds['bottle'], bounds['table']
    floor = groups['floor'][0]
    if (floor['rotation'] != np.eye(3).flatten().tolist() or
            bottle['low'][2] <= floor['position'][2] or
            not np.all(np.asarray(bottle['low'][:2]) > table['low'][:2]) or
            not np.all(np.asarray(bottle['high'][:2]) < table['high'][:2])):
        raise ValueError('Translated bottle footprint/floor support setup mismatch')
    separation = {key: bottle['low'][0] - bounds[key]['high'][0] for key in ('robot', 'bowl', 'cabinet', 'rack')}
    if condition == 'neck-away' and not all(value > 0 for value in separation.values()):
        raise ValueError('Fixed translated bottle is not statically separated; no adjustment allowed')
    return {'evaluator_only': True, 'bounds': bounds, 'floor': floor,
        'X_separation_lower_bounds_m': separation, 'geometry_count': expected,
        'visibility_verified': False, 'dynamic_stability_or_swept_clearance_verified': False}


def event(backend, condition, record, capture):
    if condition not in ORDER or backend._grip_cmd != -1 or backend.step_m != .01:
        raise ValueError('Fixed scene condition/open-jaw original executor required')
    world = backend.world
    static = checked_static()
    address, model = model_gate(world, static)
    record('scene_intervention_intent', {'version': VERSION, 'condition': condition,
        'privileged_scene_intervention': True, 'before_action_step': EVENT_STEP,
        'joint': JOINT, 'qpos_address': address, 'delta_world_m': DELTA[condition],
        'compiled_model_array_sha256': model, 'forward_calls': 1, 'forced_observation_refresh_calls': 1,
        'physics_controls': 0, 'archived_state_restored': False})
    before = snapshot(backend)
    record('scene_state', {'stage': 'before', 'audit': before})
    capture('before', own_packet(world.obs))
    world.data.qpos[address:address + 3] += np.asarray(DELTA[condition])
    written = snapshot(backend)
    record('scene_state', {'stage': 'after_write', 'audit': written, 'changes': changes(before, written)})
    require_write(before, written, address, DELTA[condition])
    world.env.sim.forward()
    forwarded = snapshot(backend)
    record('scene_state', {'stage': 'after_forward', 'audit': forwarded, 'changes': changes(written, forwarded)})
    require_sync(written, forwarded)
    # One refresh only: the inner getter performs _update_observables(force=True).
    world.obs = world.env.env._get_observations(force_update=True)
    refreshed = snapshot(backend)
    record('scene_state', {'stage': 'after_refresh', 'audit': refreshed, 'changes': changes(forwarded, refreshed)})
    require_sync(forwarded, refreshed)
    record('scene_geometry_admission', geometry_admission(world, condition))
    capture('after', own_packet(world.obs))
    record('scene_intervention_completed', {'condition': condition, 'before_action_step': EVENT_STEP,
        'privileged_scene_intervention': True, 'sim_time_before_s': before['sim_time_s'],
        'sim_time_after_s': refreshed['sim_time_s'], 'physics_controls': 0,
        'forward_calls': 1, 'forced_observation_refresh_calls': 1,
        'own_changes': changes(before['own_observations'], refreshed['own_observations']),
        'explicit_write_changed_qpos_indices': [address + i for i, v in enumerate(DELTA[condition]) if v != 0]})


def scene_sensor(condition, stage, frame, own, artifact, digest):
    row = prior.sensor_row(condition, 'scene_' + stage, EVENT_STEP, None, frame, own,
        artifact, digest, 'scene', anchor='neck', arm='close')
    row.update(scene_boundary=stage, tcp_source_field='scene_boundary.own_observations.robot0_eef_pos',
        own_source={'journal': 'episodes.jsonl', 'kind': 'scene_boundary', 'boundary': stage, 'step': EVENT_STEP})
    return row


def robot_bottle_contact(contact):
    names = contact['geom_names']
    return (any(name.startswith(('robot0_', 'gripper0_', 'mount0_')) for name in names)
            and any(name.startswith('wine_bottle_1_') for name in names))


class SceneSuffix(prior.Intervention):
    def __init__(self, condition):
        if condition not in ORDER:
            raise ValueError('Only the fixed scene pair is allowed')
        super().__init__(condition, schedule=SCHEDULE, before_suffix=self.before_scene,
                         after_primitive=self.qualify_empty,
                         anchor='neck', arm='close', extra_sensor_files=('own-controls.json',))

    def qualify_empty(self, recorder, offset, step):
        if self.condition != 'neck-away':
            return
        records, errors = load_records(recorder.output / 'episodes.jsonl')
        native = [r for r in records if r['kind'] in ('native_before', 'native_after')
                  and r['data']['step'] == step]
        labels = [r for r in self.labels if r['step'] == step]
        if errors or len(native) != 400 or len(labels) != 8:
            raise ValueError('Complete native/endpoint evidence required for away qualification')
        violations = []
        for row in native:
            for index, contact in enumerate(row['data']['contacts']):
                if robot_bottle_contact(contact):
                    violations.append({'journal': 'episodes.jsonl', 'seq': row['seq'],
                        'record_id': row['record_id'], 'contact_index': index, 'contact': contact})
        for row in labels:
            for index, contact in enumerate(row['raw_contact_snapshot']['contacts']):
                if robot_bottle_contact(contact):
                    violations.append({'artifact': 'evaluator-only/labels.json', 'step': step,
                        'control': row['control'], 'contact_index': index, 'contact': contact})
        recorder.record('away_contact_qualification', {'condition': self.condition, 'step': step,
            'primitive_offset': offset, 'native_snapshots': len(native), 'endpoint_snapshots': len(labels),
            'raw_robot_bottle_contact_absent': not violations, 'violations': violations,
            'zero_force_contacts_count': True, 'settled_empty_not_inferred': True, 'evaluator_only': True})
        if violations:
            raise RuntimeError('away_robot_bottle_contact_invalidates_empty_comparison')

    def before_scene(self, *, backend, recorder, groups, approach):
        from ..adapters.libero_rgbd import LiberoRgbdSource
        if approach['completed_actions'] != EVENT_STEP:
            raise ValueError('Original 29-action neck prefix required before scene event')
        camera = LiberoRgbdSource(backend.world)
        (recorder.output / 'scene').mkdir()
        def capture(stage, own):
            with prior.local.read_only_measurement(backend.world):
                frame = camera.capture()
            artifact = f'scene/capture-{frame["capture_seq"]:06d}.npz'
            with (recorder.output / artifact).open('xb') as stream:
                np.savez_compressed(stream, **{key: frame[key] for key in base.FRAME_KEYS})
            row = scene_sensor(self.condition, stage, frame, own, artifact, file_hash(recorder.output / artifact))
            self.sensors.append(row)
            recorder.record('scene_boundary', row)
        try:
            event(backend, self.condition, recorder.record, capture)
        except BaseException as exc:
            recorder.record('scene_intervention_failure', {'exception': repr(exc), 'no_retry': True,
                'condition': self.condition, 'before_action_step': EVENT_STEP})
            raise
        return []  # Already appended eagerly so a partial event keeps its saved images.

    def seal(self, directory):
        directory = Path(directory)
        if not (directory / 'episodes.jsonl').exists():
            return
        records, _ = load_records(directory / 'episodes.jsonl')
        phases = {r['data']['step']: r['data']['native_phase'] for r in records
                  if r['kind'] == 'action_started' and 'native_phase' in r['data']}
        own = []
        for row in records:
            data = row['data']
            if row['kind'] == 'control_completed' and data['step'] in phases:
                own.append({'condition': self.condition, 'phase': phases[data['step']],
                    'step': data['step'], 'control': data['control'], 'command': data['command'],
                    'read_sim_time_s': data['state_after'][0], 'exact_observation_sample_time_s': None,
                    'own_observations': own_packet(data['returned_own_observations']),
                    'source': {'journal': 'episodes.jsonl', 'seq': row['seq'], 'record_id': row['record_id'],
                        'own_field': 'data.returned_own_observations', 'clock_field': 'data.state_after[0]'}})
        prior.approach.write(directory / 'own-controls.json', own)
        super().seal(directory)


class SceneReplay:
    def __init__(self, source, output):
        self.source, self.output = Path(source), Path(output)
        records, errors = load_records(self.source / 'episodes.jsonl')
        if errors or any(r['kind'] == 'scene_intervention_failure' for r in records):
            raise ValueError('Complete scene event required before replay')
        if any(r['kind'].startswith('scene_') and r['kind'] not in EVENT_KINDS for r in records):
            raise ValueError('Unknown scene mutation record; replay admission denied')
        self.expected = [r for r in records if r['kind'] in EVENT_KINDS]
        sequence = ('scene_intervention_intent', 'scene_state', 'scene_boundary', 'scene_state',
                    'scene_state', 'scene_state', 'scene_geometry_admission', 'scene_boundary',
                    'scene_intervention_completed')
        if tuple(r['kind'] for r in self.expected) != sequence:
            raise ValueError('Exactly one complete ordered scene event required')
        intents = [r['data'] for r in self.expected if r['kind'] == 'scene_intervention_intent']
        if len(intents) != 1 or sum(r['kind'] == 'scene_intervention_completed' for r in self.expected) != 1:
            raise ValueError('Exactly one complete scene event required')
        self.condition = intents[0]['condition']
        if self.condition not in ORDER or intents[0]['before_action_step'] != EVENT_STEP:
            raise ValueError('Fixed scene event identity required')
        self.index, self.invocations = 0, 0

    def record(self, kind, data):
        expected = self.expected[self.index] if self.index < len(self.expected) else None
        actual = {'kind': kind, 'data': jsonable(data)}
        if expected is None or expected['kind'] != kind or expected['data'] != actual['data']:
            self.output.mkdir(exist_ok=True)
            prior.approach.write(self.output / 'scene-event-mismatch.json', {'expected': expected, 'actual': actual})
            raise ValueError('Exact scene-event replay mismatch')
        self.index += 1

    def __call__(self, backend, action):
        if action['step'] < EVENT_STEP:
            if 'native_phase' in action:
                raise ValueError('Unexpected suffix action before scene boundary')
            return
        if self.invocations:
            if action['step'] == EVENT_STEP:
                raise ValueError('Duplicate scene-event dispatch')
            return
        if action['step'] != EVENT_STEP or action.get('native_phase') != SCHEDULE[0][0]:
            raise ValueError('Scene event not dispatched before first suffix control')
        from ..adapters.libero_rgbd import LiberoRgbdSource
        self.invocations += 1
        camera = LiberoRgbdSource(backend.world)
        def capture(stage, own):
            expected = self.expected[self.index]
            if expected['kind'] != 'scene_boundary':
                raise ValueError('Scene replay capture order mismatch')
            row = expected['data']
            if file_hash(self.source / row['artifact']) != row['artifact_sha256']:
                raise ValueError('Scene source image changed')
            with prior.local.read_only_measurement(backend.world):
                frame = camera.capture()
            with np.load(self.source / row['artifact'], allow_pickle=False) as reference:
                base.require_exact_frame(frame, reference)
            self.record('scene_boundary', scene_sensor(self.condition, stage, frame, own,
                                                      row['artifact'], row['artifact_sha256']))
        event(backend, self.condition, self.record, capture)

    def finish(self):
        if self.invocations != 1 or self.index != len(self.expected):
            raise ValueError('Unconsumed or absent scene event')
        prior.approach.write(self.output / 'scene-result.json', {'status': 'passed',
            'events': self.invocations, 'exact_event_records': self.index,
            'source_journal_sha256': file_hash(self.source / 'episodes.jsonl'), 'state_restore_used': False})


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
        prior.worker(args, preflight_fn=prepare, protocol=PROTOCOL, intervention_factory=SceneSuffix,
                     auxiliary_count=24, before_action_factory=SceneReplay)
    elif args.run_matrix:
        if not all((args.output, args.review, args.preflight_receipt)):
            parser.error('matrix requires exact freeze review and no-world preflight receipt')
        prior.run_matrix(args, preflight_fn=prepare, protocol=PROTOCOL, module=MODULE, order=ORDER,
            version=VERSION, scripted_action_count=3, completion_reason='fixed_neck_scene_pair_and_replays_complete',
            replay_result_files=('result.json', 'auxiliary-result.json', 'scene-result.json'))
    else:
        if not args.output:
            parser.error('no-world preflight requires output')
        frozen, _, _ = prepare(args)
        prior.approach.write(args.output, {**frozen, 'physics_calls': 0, 'physical_execution_admitted': False,
            'pending_gate': 'independent_exact_freeze_and_preflight_review'})
        print(json.dumps({'preflight': 'passed', 'world_constructed': False, 'physical_execution_admitted': False}))


if __name__ == '__main__':
    main()
