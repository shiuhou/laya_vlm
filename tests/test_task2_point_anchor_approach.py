from contextlib import nullcontext
import inspect
import json
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_box_point_boundary as base
from embodied_runtime.experiments import task2_point_anchor_approach as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


def point(position=(.02, .02, 0)):
    return {'position_world_m': list(position), 'definition': 'cached_native_POINT_containing_pixel_center_depth',
            'provenance': {'condition': 'whole', 'query': 'the wine bottle', 'sensor_sha256': 'fixed'}}


def own():
    return {'tcp_pos_world_m': [0., 0., 0.], 'gripper_width_m': .08, 'gripper_command': 'OPEN'}


def numeric_effects(view):
    return {k: {name: value for name, value in effect.items() if name != 'state_id'}
            for k, effect in view.effects.effects.items()}


def test_metadata_hook_keeps_original_fields_rule_candidates_and_numeric_effects():
    before = base.decision(point(), own(), .5, 1.5, 2)
    after = probe.point_decision(point(), own(), .5, 1.5, 2)
    assert inspect.signature(base.collect).parameters['decision_fn'].default is base.decision
    assert before.rule_token() == after.rule_token() == 'MV_FWD'
    assert before.candidates == after.candidates and len(after.candidates) == 7
    assert before.history == after.history and numeric_effects(before) == numeric_effects(after)
    assert {k: v.value for k, v in before.state.fields.items()} == {k: v.value for k, v in after.state.fields.items()}
    assert 'BOX median-ray' in before.state.fields['target.position_m'].basis
    assert 'native POINT pixel-center' in after.state.fields['target.position_m'].basis
    assert after.state.fields['task.target_identity'].value == 'the wine bottle'
    assert after.state.meta['goal_anchor'] == point()['provenance']
    for name in ('semantic_valid', 'semantic_confidence', 'temporal_consistency_ok'):
        assert after.state.fields['quality.' + name].value is None
    assert after.state.fields['interaction.holding'].value is None
    assert all(e['state_id'] == after.state.identity() for e in after.effects.effects.values() if 'state_id' in e)


def test_same_anchor_and_own_state_preserve_guard_and_selection(monkeypatch):
    from itertools import product
    vertices = np.asarray(list(product((-.001, .001), repeat=3)))
    proxies = {name: vertices + [i*10, 0, 0] for i, name in enumerate(probe.guard.geometry.GEOMS)}
    monkeypatch.setattr(probe.guard.geometry, 'place', lambda *_: (proxies, {'test': 'mount'}))
    packet = {'calibration': {}, 'full_support': [{'position_world_m': [.01, 0, 0]}]}
    returned = {'robot0_eef_pos': [0, 0, 0], 'robot0_eef_quat': [0, 0, 0, 1],
                'robot0_gripper_qpos': [.04, -.04], 'success': True, 'contacts': ['poison']}
    old = base.decision(point(), own(), 0, 0, 0)
    new = probe.point_decision(point(), own(), 0, 0, 0)
    a = probe.guard.EndpointSelector(packet)(old, returned)
    b = probe.guard.EndpointSelector(packet)(new, returned)
    assert a[0] == b[0] == 'MV_LEFT' and a[2] == b[2]
    for key in a[1]:
        if key != 'eligible_canonical':
            assert a[1][key] == b[1][key]
    assert a[1]['eligible_canonical']['candidates'] == b[1]['eligible_canonical']['candidates']


def mock_collection(monkeypatch, tmp_path, *, mismatch=False, decision_fn=None):
    from embodied_runtime.experiments.privileged_multistage_task import WineBottleBottomDrawerAdapter
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    sensor = {'rgb': np.zeros((2, 2, 3), np.uint8), 'depth_m': np.zeros((2, 2), np.float32),
              'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    captured = {k: v.copy() for k, v in sensor.items()}
    if mismatch:
        captured['depth_m'][0, 0] = -0.
    captured.update(capture_seq=1, capture_sim_time=.5, camera_name='fake', calibration_id='fake')
    observations = {key: np.zeros(3) for key in base.OBS_KEYS}
    world = SimpleNamespace(model=SimpleNamespace(opt=SimpleNamespace(timestep=.002, integrator=0)),
        data=SimpleNamespace(time=.5), gripper_geoms=[1, 2], scene=SimpleNamespace(geoms=[3]), obs=observations,
        env=SimpleNamespace(sim=SimpleNamespace(model=SimpleNamespace(geom_id2name=lambda g: f'{g}_pad_collision'))))
    calls = []
    backend = SimpleNamespace(world=world, step_m=.01, _grip_cmd=-1,
                              proprioception=own, close=lambda: calls.append('closed'))
    monkeypatch.setattr(WineBottleBottomDrawerAdapter, 'make_backend', lambda *_a, **_k: backend)
    monkeypatch.setattr(LiberoRgbdSource, '__init__', lambda self, _world: None)
    monkeypatch.setattr(LiberoRgbdSource, 'capture', lambda self: captured)
    measurements = ModuleType('jev_libero.measurements')
    measurements.Measurements = lambda _world: SimpleNamespace(ids=lambda _selector: {1, 2})
    monkeypatch.setitem(sys.modules, 'jev_libero.measurements', measurements)
    monkeypatch.setattr(base, 'read_only_measurement', lambda _: nullcontext())
    monkeypatch.setattr(base, 'contact_snapshot', lambda *_: {'contacts': [], 'time_s': .5})
    monkeypatch.setattr(base.AtomicExecutor, 'execute', lambda *_: calls.append('EXECUTION_FORBIDDEN'))
    review = tmp_path/'review.txt'
    review.write_text('synthetic receipt')
    protocol = tmp_path/'protocol.md'
    protocol.write_text('synthetic protocol')
    args = SimpleNamespace(output=str(tmp_path/'run'), review=str(review))
    p = point((0., 0., 0.))
    kwargs = {} if decision_fn is None else {'decision_fn': decision_fn}
    if mismatch:
        with pytest.raises(ValueError, match='Fresh initial RGB/depth/K/T mismatch'):
            base.collect(args, preflight_fn=lambda _: ({}, p, sensor), protocol=protocol, **kwargs)
    else:
        base.collect(args, preflight_fn=lambda _: ({}, p, sensor), protocol=protocol, **kwargs)
    rows, errors = load_records(tmp_path/'run/episodes.jsonl')
    assert not errors and calls == ['closed']
    return rows


def test_collector_legacy_default_matches_explicit_old_decision_without_world(tmp_path, monkeypatch):
    a, b = tmp_path/'a', tmp_path/'b'
    a.mkdir()
    b.mkdir()
    default = mock_collection(monkeypatch, a)
    explicit = mock_collection(monkeypatch, b, decision_fn=base.decision)
    def chosen(rows):
        return [r['data'] for r in rows if r['kind'] in ('decision', 'termination')]
    assert chosen(default) == chosen(explicit)
    assert chosen(default)[-1]['reason'] == 'rule_no_strict_nominal_improvement'
    assert not chosen(default)[-1]['task_success_claim']


def test_initial_mismatched_image_blocks_new_decision_hook_and_approach(tmp_path, monkeypatch):
    hooks = []
    rows = mock_collection(monkeypatch, tmp_path, mismatch=True, decision_fn=lambda *_: hooks.append('called'))
    assert not hooks and not any(r['kind'] in ('decision', 'action_started') for r in rows)
    assert rows[-1]['data']['reason'] == 'runtime_or_admission_failure'


def test_fixed_pair_keeps_both_normal_conditions_and_separate_replays(tmp_path):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    calls = []
    probe.execute_stages(recorder, lambda condition, stage: calls.append((condition, stage)))
    recorder.close()
    assert calls == [('whole', 'collect'), ('whole', 'replay'), ('neck', 'collect'), ('neck', 'replay')]


@pytest.mark.parametrize('failed_stage', ['collect', 'replay'])
def test_failed_collection_or_replay_stops_batch_without_retry(tmp_path, failed_stage):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    calls = []
    def launch(condition, stage):
        calls.append((condition, stage))
        if stage == failed_stage:
            raise RuntimeError('failure')
    with pytest.raises(RuntimeError, match='failure'):
        probe.execute_stages(recorder, launch)
    recorder.close()
    assert calls == [('whole', 'collect')] + ([('whole', 'replay')] if failed_stage == 'replay' else [])


@pytest.mark.parametrize('reason,violation,accepted', [
    ('rule_no_strict_nominal_improvement', False, True), ('new_robot_contact', False, True),
    ('action_budget', False, True), ('wall_limit', False, False),
    ('execution_contract_violation', True, False), ('new_robot_contact', True, False),
])
def test_only_normal_nonviolating_endpoints_advance_pair(tmp_path, reason, violation, accepted):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    recorder.record('action_completed', {'result': {'execution_contract_violation': violation}})
    recorder.record('termination', {'reason': reason})
    recorder.close()
    if accepted:
        probe.check_collection(recorder.output)
    else:
        with pytest.raises(ValueError, match='stop pair'):
            probe.check_collection(recorder.output)


def admission_fixture(tmp_path, monkeypatch, neck_inside):
    from embodied_runtime.experiments import task2_point_goal_cell as cells
    def artifact(name, data):
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {'path': str(path), 'sha256': file_hash(path)}
    point_audit = artifact('point-audit.json', {'status': 'pass', 'source_admission': 'pass',
        'freeze': 'd4045496dc330529eb8f637bd46d556fc9bc0598',
        'conditions': [{'condition': name, 'sensor_sha256': probe.SOURCE_SHA[name+'/sensor-result.json']} for name in probe.ORDER]})
    monkeypatch.setattr(probe, 'POINT_AUDIT_SHA', point_audit['sha256'])
    common = {'calibration': {}, 'full_support': [], 'terminal_own_packet': {}, 'nominal_step_m': .01}
    monkeypatch.setattr(cells, 'prepare', lambda: (common, {}))
    artifact('geometry/request.json', {**common, 'anchors': [
        {'condition': name, 'point_P_world_m': probe.POSITIONS[name]} for name in probe.ORDER]})
    seal = {}
    for name in probe.ORDER:
        directory = tmp_path/'geometry/features'/name
        directory.mkdir(parents=True)
        inside = np.zeros((9, 1340, 5), bool)
        inside[0, 0, 0] = name == 'neck' and neck_inside
        np.savez_compressed(directory/'containment.npz', inside=inside)
        result = {'point_P_world_m': probe.POSITIONS[name], 'array_shape': [9, 1340, 5],
            'geometry_order': probe.guard.geometry.GEOMS, 'nominal_step_m': .01, 'terminal_own_packet': {},
            'exact_P_any_containment': bool(inside[0].any()),
            'placements': [{'kind': 'exact_P', 'hypothetical_TCP_world_m': probe.POSITIONS[name],
                            'any_containment': bool(inside[0].any())}] + [{}]*8,
            'containment_artifact_sha256': file_hash(directory/'containment.npz')}
        artifact(f'geometry/features/{name}/result.json', result)
        for file in ('result.json', 'containment.npz'):
            seal[f'features/{name}/{file}'] = file_hash(directory/file)
    combined = artifact('geometry/features/result.json', {'condition_order': list(probe.ORDER), 'tensor_shape': [2, 9, 1340, 5]})
    seal['features/result.json'] = combined['sha256']
    feature_seal = artifact('geometry/feature-seal.json', seal)
    audit = artifact('geometry-audit.json', {'status': 'PASS', 'feature_seal_sha256': feature_seal['sha256'],
        'request_sha256': file_hash(tmp_path/'geometry/request.json'), 'source_admission_audit_sha256': point_audit['sha256'],
        'source_sensor_sha256': {name: probe.SOURCE_SHA[name+'/sensor-result.json'] for name in probe.ORDER},
        'raw_directory': str(tmp_path/'geometry')})
    admission = artifact('admission.json', {'point_audit': point_audit, 'geometry_directory': str(tmp_path/'geometry'),
                                         'geometry_seal': feature_seal, 'geometry_audit': audit})
    return admission['path'], {'endpoint_guard': {'full_support': [], 'calibration': {}}, 'common': {}}


@pytest.mark.parametrize('neck_inside', [False, True])
def test_neck_exact_point_gate_requires_closed_bound_evidence(tmp_path, monkeypatch, neck_inside):
    path, frozen = admission_fixture(tmp_path, monkeypatch, neck_inside)
    if neck_inside:
        with pytest.raises(ValueError, match='Physical gate rejected'):
            probe.physical_admission(path, frozen)
    else:
        result = probe.physical_admission(path, frozen)
        assert result['status'] == 'pass' and not result['absence_is_physical_clearance']
        assert result['conditions_retained'] == ['whole', 'neck']


def test_geometry_review_or_support_mismatch_cannot_authorize_physics(tmp_path, monkeypatch):
    path, frozen = admission_fixture(tmp_path, monkeypatch, False)
    frozen['endpoint_guard']['full_support'] = ['different support']
    with pytest.raises(ValueError, match='original support'):
        probe.physical_admission(path, frozen)
    frozen['endpoint_guard']['full_support'] = []
    admission = json.loads(open(path).read())
    with open(admission['geometry_audit']['path'], 'a') as stream:
        stream.write(' ')
    with pytest.raises(ValueError, match='admission artifact changed'):
        probe.physical_admission(path, frozen)
