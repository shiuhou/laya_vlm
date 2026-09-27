from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_image_motion as assay


def manifest(condition='neck-present'):
    schedule = [('reset', -1, None, 'primary', 1)]
    schedule += [('approach', i, 7, 'primary', i+2) for i in range(29)]
    schedule += [('scene_before', 29, None, 'scene', 1), ('scene_after', 29, None, 'scene', 2)]
    schedule += [(phase, 29+j, c, 'auxiliary', 8*j+c+1)
                 for j, phase in enumerate(('close_or_hold', 'additional_close', 'lift')) for c in range(8)]
    result = []
    for i, (phase, step, control, stream, seq) in enumerate(schedule):
        time = float(i if i < 31 else i-1)
        own = {'robot0_eef_pos': [i*.01, 0., 1.], 'robot0_eef_quat': [0., 0., 0., 1.],
               'robot0_gripper_qpos': [0., 0.], 'robot0_gripper_qvel': [0., 0.]}
        row = {'condition': condition, 'anchor': 'neck', 'arm': 'close', 'phase': phase,
            'after_step': step, 'control': control, 'source_capture_stream': stream,
            'source_capture_seq': seq, 'capture_id': i, 'capture_sim_time': time,
            'capture_read_sim_time_s': time, 'cached_geometry_sample_time_s': None,
            'exact_observation_sample_time_s': None, 'tcp_read_sim_time_s': time,
            'tcp_source_field': 'control_completed.returned_own_observations.robot0_eef_pos',
            'own_tcp_world_m': own['robot0_eef_pos'], 'own_observations': own,
            'own_source': {'journal': 'episodes.jsonl', 'kind': 'control_completed', 'step': step, 'control': control},
            'artifact': f'{i}.npz', 'artifact_sha256': 'pending', 'render_preserves_state_and_caches': True}
        if stream == 'scene':
            boundary = 'before' if seq == 1 else 'after'
            row.update(scene_boundary=boundary,
                tcp_source_field='scene_boundary.own_observations.robot0_eef_pos',
                own_source={'journal': 'episodes.jsonl', 'kind': 'scene_boundary', 'boundary': boundary, 'step': 29})
        result.append(row)
    return result


def packet():
    rows = assay.selected_manifest(manifest(), 'neck-present')
    return {'meta': rows, 'frames': [{'rgb': np.full((384, 384, 3), i, np.uint8),
            'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)} for i in range(25)]}


def test_postevent_selection_preserves_all_controls_and_excludes_jump():
    selected = assay.selected_manifest(manifest(), 'neck-present')
    assert [r['capture_id'] for r in selected] == list(range(31, 56))
    assert [selected[i]['capture_id'] for i in assay.ENDPOINTS.values()] == [31, 39, 47, 55]
    assert selected[0]['own_source']['boundary'] == 'after'
    assert [r['source_capture_seq'] for r in selected[1:]] == list(range(1, 25))
    assert assay.SEEDS == [[x, y] for y in range(169, 210) for x in range(212, 224)]


@pytest.mark.parametrize('corrupt', [
    lambda rows: rows.pop(32),
    lambda rows: rows[32].update(source_capture_seq=2),
    lambda rows: rows[31].update(phase='scene_before'),
    lambda rows: rows[31]['own_source'].update(boundary='before'),
    lambda rows: rows[32].update(control=1),
    lambda rows: rows[32].update(capture_read_sim_time_s=rows[31]['capture_read_sim_time_s']),
    lambda rows: rows[31].update(holding=True),
    lambda rows: rows[31].update(artifact=rows[30]['artifact']),
    lambda rows: rows[31].update(own_tcp_world_m=[5., 6., 7.]),
    lambda rows: rows[31].update(exact_observation_sample_time_s=30.),
])
def test_rejects_partial_reordered_cross_event_or_unbound_sources(corrupt):
    rows = manifest()
    corrupt(rows)
    with pytest.raises(ValueError):
        assay.selected_manifest(rows, 'neck-present')


def write_cell(root, condition):
    directory = root/condition
    directory.mkdir()
    rows = manifest(condition)
    for row in rows:
        path = directory/row['artifact']
        path.write_bytes(f'archive-{row["capture_id"]}'.encode())
        row['artifact_sha256'] = assay.file_hash(path)
    (directory/'episodes.jsonl').write_text('evaluator-bearing journal: must never be decoded')
    (directory/'own-controls.json').write_text('source-only linkage: not feature input')
    assay.write_json(directory/'sensor-captures.json', rows)
    hashes = {'sensor-captures.json': assay.file_hash(directory/'sensor-captures.json'),
              'own-controls.json': assay.file_hash(directory/'own-controls.json')}
    hashes.update({r['artifact']: r['artifact_sha256'] for r in rows})
    assay.write_json(directory/'sensor-seal.json', {'sha256': hashes, 'journal_parse_errors': [], 'holding': None,
        'journal_sha256_linkage_only': assay.file_hash(directory/'episodes.jsonl')})
    return {'directory': condition, 'condition': condition,
            'sha256': {name: assay.file_hash(directory/name) for name in ('sensor-captures.json', 'sensor-seal.json')}}


def test_loader_opens_only_postevent_RGB_K_T_and_hashes_mechanical_receipts(tmp_path, monkeypatch):
    source = tmp_path/'source'
    source.mkdir()
    (source/'episodes.jsonl').write_text('mixed matrix journal must not be decoded')
    receipt = tmp_path/'mechanical-review'
    receipt.write_text('non-JSON privileged source admission and review')
    binding = {'schema': 'task2-closed-empty-image-motion-binding-v1', 'source_admitted': True,
        'source_root': str(source), 'matrix_journal_sha256': assay.file_hash(source/'episodes.jsonl'),
        'source_admission': {'path': str(receipt), 'sha256': assay.file_hash(receipt)},
        'source_review': {'path': str(receipt), 'sha256': assay.file_hash(receipt)},
        'cells': {role: write_cell(source, 'neck-'+role) for role in assay.ROLES}}
    path = tmp_path/'binding.json'
    assay.write_json(path, binding)
    keys, opened = [], []
    class SensorArchive:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, key):
            keys.append(key)
            assert key in ('rgb', 'intrinsics', 'camera_to_world')
            return np.zeros((384, 384, 3), np.uint8) if key == 'rgb' else np.eye(3 if key == 'intrinsics' else 4)
    def load(path, *, allow_pickle):
        assert allow_pickle is False
        opened.append(int(path.stem))
        return SensorArchive()
    monkeypatch.setattr(assay.np, 'load', load)
    packets, admission = assay.load_inputs(path)
    assert opened == list(range(31, 56))*2
    assert keys == ['rgb', 'intrinsics', 'camera_to_world']*50
    assert list(packets) == ['present', 'away']
    assert admission['tracks'] == 984 and admission['rows'] == 24600
    assert admission['evaluator_read'] is False
    (source/'neck-away/40.npz').write_bytes(b'changed')
    with pytest.raises(ValueError, match='archive changed'):
        assay.load_inputs(path)


def test_full_population_native_failure_and_missing_TCP_stay_in_output(monkeypatch):
    inputs = packet()
    for key in ('own_observations', 'own_tcp_world_m', 'tcp_read_sim_time_s', 'tcp_source_field'):
        inputs['meta'][0][key] = None
    calls = []
    def track(rgb, seed, cv2):
        calls.append(list(seed))
        assert rgb.shape == (25, 384, 384, 3) and rgb[0, 0, 0, 0] == 0 and rgb[-1, 0, 0, 0] == 24
        rows = []
        for i in range(25):
            row = {key: None for key in assay.motion.NATIVE_KEYS}
            row.update(frame=i, status='seeded' if i == 0 else 'native_status_ok',
                       point_pixel_index_xy=[seed[0]+i, seed[1]+2*i])
            if seed == assay.SEEDS[0] and i >= 3:
                row['status'] = 'native_failure' if i == 3 else 'unknown_after_native_failure'
                if i > 3:
                    row['point_pixel_index_xy'] = None
            rows.append(row)
        return rows
    monkeypatch.setattr(assay.lk, 'track_lk', track)
    tracks = list(assay.iter_tracks(inputs, SimpleNamespace(__version__='4.11.0')))
    summary = assay.summarize(tracks)
    assert calls == assay.SEEDS and len(tracks) == 492 and sum(map(len, tracks)) == 12300
    assert tracks[0][3]['point_pixel_index_xy'] == [215, 175]
    assert tracks[0][3]['image_motion']['rgb_delta_xy_px'] is None
    assert all(r['image_motion']['reference_capture_id'] == 0 for t in tracks for r in t)
    assert summary[0]['A_available_count'] == 492 and summary[0]['B_available_count'] == 0
    assert summary[3]['native_failure_count'] == 1 and summary[4]['unknown_after_failure_count'] == 1
    assert summary[24]['denominator'] == 492 and summary[24]['A_available_count'] == 491
    assert summary[24]['metrics']['rgb_delta_norm_px']['missing_count'] == 1
    assert summary[24]['metrics']['rgb_delta_norm_px']['median'] == np.linalg.norm([24, 48])
    assert all(s['metrics']['rgb_minus_tcp_delta_norm_px']['missing_count'] == 492 for s in summary)
    assert all(set(r) <= set(assay.motion.INPUT_KEYS) | {'own_tcp_image_projection', 'image_motion', 'identity_verified', 'holding'}
               for t in tracks for r in t)


def test_unreviewed_binding_never_loads_sensor_or_calls_tracker(tmp_path, monkeypatch):
    identity = {'dirty_status': '', 'commit': 'synthetic'}
    monkeypatch.setattr(assay, 'code_identity', lambda: identity)
    monkeypatch.setattr(assay.motion.prior, 'environment', lambda cv2: {'runtime': 'synthetic'})
    binding, preflight, review = [tmp_path/name for name in ('binding', 'preflight', 'review')]
    binding.write_text('{}')
    assay.write_json(preflight, {'code': identity, 'status': 'pass', 'environment': {'runtime': 'synthetic'},
        'protocol_sha256': assay.file_hash(assay.PROTOCOL), 'LK_projection_displacement_computed': False,
        'model_physics_render_calls': 0})
    assay.write_json(review, {'status': 'pass', 'freeze_commit': 'synthetic', 'binding_sha256': 'wrong-source-binding'})
    def forbidden(*args, **kwargs):
        pytest.fail('unreviewed source must not reach feature/source access')
    monkeypatch.setattr(assay, 'load_inputs', forbidden)
    monkeypatch.setattr(assay.lk, 'track_lk', forbidden)
    with pytest.raises(ValueError, match='reviewed admitted-source'):
        assay.run(binding, preflight, review, assay.OUTPUT)


def test_source_paths_cannot_escape_bound_cell(tmp_path):
    for path in ('../secret', '/absolute'):
        with pytest.raises(ValueError, match='relative source'):
            assay.relative(tmp_path, path)
