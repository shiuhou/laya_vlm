from copy import deepcopy
from itertools import product
import json

import numpy as np
import pytest

from embodied_runtime.experiments import task2_postevent_point_decision as probe


def source_fixture(monkeypatch):
    own = {'robot0_eef_pos': [0., 0., 0.], 'robot0_eef_quat': [0., 0., 0., 1.],
           'robot0_gripper_qpos': [.04, -.04], 'robot0_gripper_qvel': [0., 0.]}
    frame = {'depth_m': np.ones((384, 384), dtype=np.float32),
             'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    raw = {'raw_response': '<box><500><500></box>', 'raw_response_type': 'str',
           'observed_decoded_token_sequences': [[[10, 151645]]]}
    sensor = probe.point_adapter.analyze_rgb_return(raw, 229, 16384, 151645)
    cases = []
    for case_id in probe.ORDER:
        cases.append({'case_id': case_id, 'settings': deepcopy(probe.SLOW),
            'source': {'case_id': case_id, 'local_suffix_capture_id': 0, 'capture_id': 31,
                       'source_capture_stream': 'scene', 'source_capture_seq': 2,
                       'exact_observation_sample_time_s': None, 'capture_read_sim_time_s': 12.1},
            'own': deepcopy(own), 'sensor': deepcopy(sensor), 'frame': deepcopy(frame),
            'provenance': {'synthetic': True}})
    cached = {'point': probe.CACHED_POINT, 'question': probe.QUESTION,
              'settings': deepcopy(probe.HYBRID), 'provenance': {'synthetic': True}}
    packet = {'full_support': [{'position_world_m': [100., 100., 100.]}], 'calibration': {}}
    monkeypatch.setattr(probe, 'GUARD_SHA', probe._sha256_json(packet))
    vertices = np.asarray(list(product((-.001, .001), repeat=3)))
    proxies = {name: vertices+[i*10, 0, 0] for i, name in enumerate(probe.guard.geometry.GEOMS)}
    monkeypatch.setattr(probe.guard.geometry, 'place', lambda *_: (proxies, {'synthetic': True}))
    return cases, cached, packet


def test_known_numeric_rule_preserved_with_unknown_sensor_ages():
    own = {'robot0_eef_pos': [0., 0., 0.], 'robot0_eef_quat': [0., 0., 0., 1.],
           'robot0_gripper_qpos': [.04, -.04]}
    point = [.02, .02, 0.]
    new = probe.decision(point, own, 12.1, 0, 'fresh', {})
    old = probe.base.decision({'position_world_m': point, 'definition': 'native_POINT_containing_pixel_center_depth'},
        {'tcp_pos_world_m': [0., 0., 0.], 'gripper_width_m': .08, 'gripper_command': None}, 12.1, 12.1, 0)
    assert new.rule_token() == old.rule_token() == 'MV_FWD'
    assert new.candidates == old.candidates and len(new.candidates) == 7
    assert {k: v['values'] for k, v in new.effects.effects.items()} == {k: v['values'] for k, v in old.effects.effects.items()}
    assert new.state.fields['quality.geometry_age_s'].value is None
    assert new.state.fields['quality.semantic_age_s'].value is None
    assert new.state.fields['robot.gripper_command'].value is None
    assert new.state.meta['generation_mode'] == 'slow'


def test_all_four_rows_share_pair_guard_and_do_not_share_selector_history(monkeypatch):
    cases, cached, packet = source_fixture(monkeypatch)
    result = probe.compare_two(cases, cached, packet)
    assert [(r['case_id'], r['arm']) for r in result['records']] == [(c, a) for c in probe.ORDER for a in ('cached', 'fresh')]
    assert result['record_count'] == 4 and result['candidate_records'] == 28
    for a, b in (result['records'][:2], result['records'][2:]):
        assert probe.strip_goal_scores(a['selection']) == probe.strip_goal_scores(b['selection'])
        assert a['own'] == b['own'] and len(b['all_seven_candidates']) == 7
        assert a['generation_mode'] == 'hybrid' and b['generation_mode'] == 'slow'
        assert a['selection']['first_policy_divergence'] is None
        assert b['selection']['first_policy_divergence'] is None


@pytest.mark.parametrize('failure', ['malformed', 'invalid_depth'])
def test_nonadmitted_fresh_goal_retains_null_tokens_and_all_seven_vetoes(monkeypatch, failure):
    cases, cached, packet = source_fixture(monkeypatch)
    if failure == 'malformed':
        cases[1]['sensor'] = probe.point_adapter.analyze_rgb_return(
            {'raw_response': '<box><500><500></box><box>', 'raw_response_type': 'str',
             'observed_decoded_token_sequences': [[[10, 151645]]]}, 229, 16384, 151645)
    else:
        cases[1]['frame']['depth_m'][192, 192] = np.nan
    row = probe.compare_two(cases, cached, packet)['records'][3]
    assert row['point_world_m'] is None and row['unguarded_token'] is None and row['guarded_token'] is None
    assert row['policy_status'] == 'not_evaluated_nonadmitted_goal'
    assert len(row['all_seven_candidates']) == 7
    assert all(v['nominal_tcp_to_P_m'] is None for v in row['all_seven_candidates'].values())
    if failure == 'malformed':
        assert row['depth_sample'] is None and row['native_image_point'] is None
    else:
        assert row['depth_sample']['value_m'] is None and row['depth_sample']['nonfinite_value'] == 'nan'


def test_reversed_or_wrong_mode_second_case_rejected_before_any_feature(monkeypatch):
    cases, cached, packet = source_fixture(monkeypatch)
    monkeypatch.setattr(probe, 'admit_point', lambda *_: pytest.fail('projection ran before full input validation'))
    cases[1]['settings']['generation_mode'] = 'hybrid'
    with pytest.raises(ValueError, match='postevent slow-mode'):
        probe.compare_two(cases, cached, packet)
    with pytest.raises(ValueError, match='Both fixed postevent'):
        probe.compare_two(cases[::-1], cached, packet)


def test_strict_reader_binds_mode_full_return_and_every_supplied_file(tmp_path):
    raw = {'raw_response': '<box><500><500></box>', 'raw_response_type': 'str',
           'observed_decoded_token_sequences': [[[10, 151645]]]}
    native = {'condition': probe.ORDER[0], 'question': probe.QUESTION, 'input_token_ids': [1]*229, 'rgb': {}}
    sensor = probe.point_adapter.analyze_rgb_return(raw, 229, 16384, 151645)
    config = {'case_id': probe.ORDER[0], 'question': probe.QUESTION, 'settings': probe.SLOW, 'image_source': {}}
    data = {'generation-return.json': raw, 'sensor-result.json': sensor, 'native-input.json': native,
            'generation-settings.json': probe.SLOW, 'resolved_config.yaml': config}
    for name, value in data.items():
        (tmp_path/name).write_text(json.dumps(value))
    hashes = {name: probe.file_hash(tmp_path/name) for name in data}
    assert probe.read_slow_return(tmp_path, hashes)['sensor'] == sensor
    (tmp_path/'generation-settings.json').write_text(json.dumps(probe.HYBRID))
    with pytest.raises(ValueError, match='Bound slow source changed'):
        probe.read_slow_return(tmp_path, hashes)
    hashes['generation-settings.json'] = probe.file_hash(tmp_path/'generation-settings.json')
    with pytest.raises(ValueError, match='explicit slow mode'):
        probe.read_slow_return(tmp_path, hashes)


def test_same_frame_join_rejects_model_RGB_mismatch_and_preserves_nonadmission(tmp_path):
    directory = tmp_path/'neck-away'
    directory.mkdir()
    rgb = np.zeros((384, 384, 3), np.uint8)
    # No depth exists in this deliberately nonadmitted source.
    np.savez(directory/'image.npz', rgb=rgb)
    source = {'case_id': 'away-postevent', 'directory': 'neck-away', 'artifact': 'image.npz',
        'capture_id': 31, 'source_capture_stream': 'scene', 'source_capture_seq': 2,
        'capture_read_sim_time_s': 12.1, 'exact_observation_sample_time_s': None,
        'artifact_sha256': probe.file_hash(directory/'image.npz')}
    own = {'condition': 'neck-away', **source, 'own_observations': {}}
    packet = {'case_id': 'away-postevent', 'image_source': source, 'sensor': {'status': 'not_admitted'},
        'settings': probe.SLOW, 'sha256': {}, 'model_RGB_identity': {'shape': [384, 384, 3], 'dtype': 'uint8',
        'bytes_sha256': probe.hashlib.sha256(rgb.tobytes()).hexdigest()}}
    joined = probe.load_same_frame(packet, tmp_path, own)
    assert set(joined['frame']) == {'rgb'}
    packet['model_RGB_identity']['bytes_sha256'] = 'changed'
    with pytest.raises(ValueError, match='actual native model input'):
        probe.load_same_frame(packet, tmp_path, own)
