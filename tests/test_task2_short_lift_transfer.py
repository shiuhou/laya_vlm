import copy
import json

import numpy as np
import pytest

from embodied_runtime.experiments import task2_short_lift_transfer as transfer


def packet():
    frame = {'depth_m': np.ones((4, 4)), 'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    return {'frames': [copy.deepcopy(frame) for _ in range(30)],
            'meta': [{'capture_id': i} for i in range(30)],
            'tcps': [None]+[[0., 0., (i-13)*.001] for i in range(1, 30)]}


def native_rows():
    return [{**{k: None for k in transfer.NATIVE_FIELDS}, 'frame': i,
             'status': 'seeded' if i == 0 else 'native_status_ok',
             'point_pixel_index_xy': [1.-1e-5, 2.+1e-5]} for i in range(30)]


def test_no_initial_own_tcp_recovery_or_initial_relative_metric():
    tcp, meta = transfer.tcp_for_capture({'capture_id': 0}, [{'invalid': 'must not be read'}])
    assert tcp is None and meta['tcp_read_sim_time_s'] is None
    rows = transfer.enrich_track(native_rows(), packet(), 0, [1, 2])
    assert rows[0]['own_tcp_world_m'] is None
    assert all(set(r['reference_deltas']) == {'preclose'} for r in rows)
    assert all(r['reference_deltas']['preclose'] is None for r in rows[:13])
    assert rows[13]['reference_deltas']['preclose']['point_minus_tcp_delta_norm_m'] == 0
    assert rows[29]['reference_deltas']['preclose']['point_minus_tcp_delta_z_m'] == -.016
    assert rows[29]['sample_pixel_xy'] == [1, 2]
    assert rows[29]['surface_point_world_m'] == [1.5, 2.5, 1.]
    json.dumps(rows, allow_nan=False)


def test_exact_saved_tcp_mapping_rejects_missing_duplicate_and_nonfinite():
    capture = {'capture_id': 13, 'arm': 'close', 'after_step': 12, 'control': 7}
    row = {'arm': 'close', 'step': 12, 'control': 7,
           'sensor': {'tcp_fk_world_m': [1., 2., 3.], 'read_sim_time_s': 5.7}}
    tcp, meta = transfer.tcp_for_capture(capture, [row])
    assert tcp.tolist() == [1., 2., 3.] and meta['tcp_read_sim_time_s'] == 5.7
    for sensors in ([], [row, row], [{**row, 'arm': 'open_hold'}],
                    [{**row, 'sensor': {**row['sensor'], 'tcp_fk_world_m': [float('nan'), 0., 0.]}}]):
        with pytest.raises(ValueError):
            transfer.tcp_for_capture(capture, sensors)


def test_native_failure_and_invalid_reference_keep_every_missing_row_in_denominator():
    healthy = transfer.enrich_track(native_rows(), packet(), 0, [1, 2])
    failed_native = native_rows()
    for i in range(13, 30):
        failed_native[i]['status'] = 'native_failure' if i == 13 else 'unknown_after_native_failure'
    failed = transfer.enrich_track(failed_native, packet(), 1, [1, 2])
    invalid_packet = packet()
    invalid_packet['frames'][13]['depth_m'][:] = float('nan')
    invalid = transfer.enrich_track(native_rows(), invalid_packet, 2, [1, 2])
    assert invalid[29]['surface_point_world_m'] is not None
    assert invalid[29]['reference_deltas']['preclose']['point_delta_norm_m'] is None
    for original, enriched in zip(failed_native, failed, strict=True):
        assert all(original[k] == enriched[k] for k in transfer.NATIVE_FIELDS)
    summary = transfer.summarize_tracks([healthy, failed, invalid], 3)
    assert summary[12]['references']['preclose']['available'] is False
    assert summary[13]['references']['preclose']['reference_surface_valid_count'] == 1
    assert summary[29]['denominator'] == 3 and summary[29]['unknown_after_failure_count'] == 1
    metric = summary[29]['references']['preclose']['metrics']['point_minus_tcp_delta_norm_m']
    assert metric['count'] == 1 and metric['missing_count'] == 2
    assert len(summary) == 30 and len(failed) == 30
    with pytest.raises(ValueError):
        transfer.summarize_tracks([healthy[:-1]], 1)
    json.dumps(invalid, allow_nan=False)


def test_prefix_check_covers_attempts_errors_status_and_ignores_later_divergence():
    rows = transfer.enrich_track(native_rows(), packet(), 7, [1, 2])
    reference = copy.deepcopy(rows)
    rows[14]['point_pixel_index_xy'] = [99, 99]
    assert transfer.prefix_disagreements(rows, reference) == []
    for key in transfer.NATIVE_FIELDS:
        altered = copy.deepcopy(rows)
        altered[6][key] = 'different'
        assert transfer.prefix_disagreements(altered, reference) == [
            {'seed_id': 7, 'capture_id': 6, 'fields': [key]}]


def test_evaluator_requires_full_ordered_29520_rows_before_masks(monkeypatch, tmp_path):
    incomplete = {a: [{'seed_id': 0, 'capture_id': 0}] for a in transfer.base.ARMS}
    monkeypatch.setattr(transfer.base, 'sealed_tracks', lambda output: incomplete)
    with pytest.raises(ValueError, match='29,520'):
        transfer.evaluate(tmp_path)
    assert not (tmp_path/'evaluation').exists()
