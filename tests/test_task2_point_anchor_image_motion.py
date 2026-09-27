import copy
import json

import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_anchor_image_motion as motion


def native(i=0, xy=None, status='native_status_ok', seed=0):
    return {**dict.fromkeys(motion.NATIVE_KEYS), 'frame': i, 'seed_id': seed, 'capture_id': i,
            'status': status, 'point_pixel_index_xy': [0., 0.] if xy is None else xy}


def test_projection_index_convention_translation_and_unclipped_tcp():
    calibration = {'intrinsics': np.array([[100., 0., 192.], [0., 100., 192.], [0., 0., 1.]]),
                   'camera_to_world': np.eye(4)}
    a = motion.project_own_tcp([0., 0., 10.], calibration)
    b = motion.project_own_tcp([1., 2., 10.], calibration)
    assert a == {'index_xy': [191.5, 191.5], 'status': 'available'}
    assert np.array_equal(np.array(b['index_xy'])-a['index_xy'], [10., 20.])
    assert motion.project_own_tcp([100., 0., 1.], calibration)['index_xy'][0] > 384
    for tcp, status in ((None, 'missing_own_tcp'), ([0., 0., 0.], 'nonpositive_camera_z'),
                        ([0., 0., -1.], 'nonpositive_camera_z'), ([np.nan, 0., 1.], 'nonfinite_or_invalid_own_tcp')):
        assert motion.project_own_tcp(tcp, calibration) == {'index_xy': None, 'status': status}
    translated = copy.deepcopy(calibration)
    translated['camera_to_world'][:3, 3] = [1., 2., 3.]
    assert motion.project_own_tcp([1., 2., 13.], translated) == a


def test_A_is_native_only_B_adds_projection_and_missing_tcp_never_removes_A():
    rows = [native(0, [0., 0.]), native(1, [3., 4.]), native(2, [6., 8.])]
    projections = [{'index_xy': [10., 20.], 'status': 'available'},
                   {'index_xy': [11., 22.], 'status': 'available'},
                   {'index_xy': None, 'status': 'missing_own_tcp'}]
    result = motion.enrich_track(rows, projections, 0)
    assert np.array_equal(result[1]['image_motion']['rgb_delta_xy_px'], [3., 4.])
    assert result[1]['image_motion']['metrics']['rgb_delta_norm_px'] == 5.
    assert np.array_equal(result[1]['image_motion']['rgb_minus_tcp_delta_xy_px'], [2., 2.])
    assert result[1]['image_motion']['metrics']['rgb_minus_tcp_delta_norm_px'] == np.sqrt(8.)
    assert result[2]['image_motion']['metrics']['rgb_delta_norm_px'] == 10.
    assert result[2]['image_motion']['metrics']['rgb_minus_tcp_delta_norm_px'] is None
    assert result[2]['image_motion']['status_B'] == 'own_projection_current_or_reference_unavailable'
    projections[0] = {'index_xy': None, 'status': 'missing_own_tcp'}
    result = motion.enrich_track(rows, projections, 0)
    assert result[1]['image_motion']['metrics']['rgb_delta_norm_px'] == 5.
    assert result[1]['image_motion']['metrics']['rgb_minus_tcp_delta_norm_px'] is None


def test_native_attempt_failure_unknown_and_before_reference_stay_explicit():
    rows = [native(0), native(1, [1., 1.]), native(2, [2., 2.], 'native_failure'),
            native(3, [3., 3.], 'unknown_after_native_failure')]
    projections = [{'index_xy': [0., 0.], 'status': 'available'}]*4
    result = motion.enrich_track(rows, projections, 1)
    assert all(v is None for v in result[0]['image_motion']['metrics'].values())
    assert result[0]['image_motion']['status_A'] == 'before_preclose'
    assert result[1]['image_motion']['metrics']['rgb_delta_norm_px'] == 0.
    assert result[2]['point_pixel_index_xy'] == [2., 2.]
    assert result[2]['image_motion']['rgb_delta_xy_px'] is None
    assert result[3]['image_motion']['rgb_minus_tcp_delta_xy_px'] is None
    rows[1]['status'] = 'native_failure'
    assert motion.enrich_track(rows, projections, 1)[3]['image_motion']['status_A'] == 'native_current_or_reference_unavailable'


def test_source_loader_whitelists_features_and_decodes_only_K_T(tmp_path, monkeypatch):
    monkeypatch.setattr(motion, 'SOURCE', tmp_path)
    monkeypatch.setattr(motion, 'SEEDS', 2)
    monkeypatch.setattr(motion.prior, 'FRAME_COUNTS', {'whole-close': 3})
    rows = []
    for seed in range(2):
        for i in range(3):
            row = {**dict.fromkeys(motion.INPUT_KEYS), **native(i, [float(i), 0.], seed=seed),
                   'artifact': f'{i}.npz', 'artifact_sha256': 'synthetic', 'own_tcp_world_m': [0., 0., 1.]}
            row.update(depth_m='must not enter', surface_point_world_m='must not enter',
                       reference_deltas='must not enter', evaluator_labels='must not enter')
            rows.append(row)
    (tmp_path/'whole-close-tracks.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    monkeypatch.setattr(motion, 'file_hash', lambda path: 'synthetic')
    read_keys = []
    class CalibrationOnly:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, key):
            assert key in ('intrinsics', 'camera_to_world')
            read_keys.append(key)
            return np.eye(3 if key == 'intrinsics' else 4)
    monkeypatch.setattr(motion.np, 'load', lambda path, allow_pickle: CalibrationOnly())
    tracks, calibrations = motion.load_cell('whole-close')
    assert read_keys == ['intrinsics', 'camera_to_world']*3
    assert len(tracks) == 2 and len(calibrations) == 3
    assert all(set(r) == set(motion.INPUT_KEYS) for t in tracks for r in t)
    projections = [{'index_xy': [0., 0.], 'status': 'available'}]*3
    with pytest.raises(ValueError, match='whitelisted'):
        motion.enrich_track(rows[:3], projections, 0)


def test_complete_492_denominators_ranges_reference_and_missing_rows():
    count, reference = 47, 30
    projections = [{'index_xy': [2.*i, 0.], 'status': 'available'} for i in range(count)]
    tracks = [motion.enrich_track([native(i, [seed+i, float(seed)], seed=seed) for i in range(count)],
                                 projections, reference) for seed in range(492)]
    summaries = motion.summarize(tracks, count, reference)
    assert len(summaries) == count and all(r['denominator'] == 492 for r in summaries)
    assert summaries[reference-1]['metrics']['rgb_delta_norm_px']['missing_count'] == 492
    assert summaries[-1]['metrics']['rgb_delta_norm_px'] == {
        'count': 492, 'median': 16., 'q25': 16., 'q75': 16., 'missing_count': 0, 'min': 16., 'max': 16.}
    assert summaries[-1]['A_available_count'] == summaries[-1]['B_available_count'] == 492
    with pytest.raises(ValueError, match='complete ordered'):
        motion.summarize(tracks[:-1], count, reference)
    tracks[0].pop()
    with pytest.raises(ValueError, match='complete ordered'):
        motion.summarize(tracks, count, reference)
