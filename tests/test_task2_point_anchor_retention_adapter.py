import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_anchor_retention_adapter as adapter


def manifest(condition='whole-close'):
    anchor, arm = condition.split('-', 1)
    approach = 30 if anchor == 'whole' else 29
    rows = []
    for i in range(approach+17):
        if i == 0:
            phase, step, control, stream, sequence = 'reset', -1, None, 'primary', 1
            kind, source_step, own_field = 'initial_frame_gate', None, 'initial_own_observations'
        elif i <= approach:
            phase, step, control, stream, sequence = 'approach', i-1, 7, 'primary', i+1
            kind, source_step, own_field = 'endpoint', step, 'own_observations'
        else:
            j = i-approach-1
            phase, step, control, stream, sequence = ('close_or_hold' if j < 8 else 'lift'), approach+j//8, j % 8, 'auxiliary', j+1
            kind, source_step, own_field = 'control_completed', step, 'returned_own_observations'
        tcp = [0., 0., .001*i]
        own = {'robot0_eef_pos': tcp, 'robot0_eef_quat': [0., 0., 0., 1.],
               'robot0_gripper_qpos': [.04, -.04], 'robot0_gripper_qvel': [0., 0.]}
        source = {'journal': 'episodes.jsonl', 'kind': kind, 'step': source_step}
        if stream == 'auxiliary':
            source['control'] = control
        rows.append({'condition': condition, 'anchor': anchor, 'arm': arm, 'capture_id': i,
            'phase': phase, 'after_step': step, 'control': control, 'source_capture_stream': stream,
            'source_capture_seq': sequence, 'capture_sim_time': float(i), 'capture_read_sim_time_s': float(i),
            'cached_geometry_sample_time_s': None, 'exact_observation_sample_time_s': None,
            'tcp_read_sim_time_s': float(i), 'own_tcp_world_m': tcp, 'own_observations': own,
            'tcp_source_field': kind+'.'+own_field+'.robot0_eef_pos', 'own_source': source,
            'artifact': f'{stream}/{i:04d}.npz', 'artifact_sha256': 'synthetic-unwritten',
            'render_preserves_state_and_caches': True})
    return rows


def native_rows(count):
    return [{**{k: None for k in adapter.prior.NATIVE_FIELDS}, 'frame': i,
             'status': 'seeded' if i == 0 else 'native_status_ok',
             'point_pixel_index_xy': [1.-1e-5, 2.+1e-5]} for i in range(count)]


def packet(count=19, reference=2):
    frame = {'rgb': np.zeros((4, 4, 3), np.uint8), 'depth_m': np.ones((4, 4)),
             'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    tcps = [[0., 0., (i-reference)*.001] for i in range(count)]
    return {'frames': [copy.deepcopy(frame) for _ in range(count)], 'tcps': tcps,
            'meta': [{'capture_id': i} for i in range(count)], 'reference_index': reference}


def test_schedule_rejects_partial_reordered_and_duplicate_boundaries_without_repair():
    for condition, reference, length in [('whole-close', 30, 47), ('neck-open_hold', 29, 46)]:
        rows = manifest(condition)
        assert len(rows) == length and adapter.validated_manifest(rows, condition) == reference
        assert (rows[reference]['phase'], rows[reference+1]['control'], rows[-1]['control']) == ('approach', 0, 7)
        assert rows[reference+8]['phase'] == 'close_or_hold' and rows[reference+9]['phase'] == 'lift'
        variants = [rows[:-1], rows[:reference+1]+[rows[reference]]+rows[reference+1:]]
        wrong_control = copy.deepcopy(rows)
        wrong_control[-1]['control'] = 6
        variants.append(wrong_control)
        wrong_order = copy.deepcopy(rows)
        wrong_order[-1], wrong_order[-2] = wrong_order[-2], wrong_order[-1]
        variants.append(wrong_order)
        for bad in variants:
            with pytest.raises(ValueError):
                adapter.validated_manifest(bad, condition)


def test_manifest_keeps_missing_own_unknown_and_rejects_stale_alias_or_evaluator_fields():
    rows = manifest()
    row = rows[30]
    for key in ('own_observations', 'own_tcp_world_m', 'tcp_source_field', 'tcp_read_sim_time_s'):
        row[key] = None
    row['own_packet_status'] = 'missing_endpoint_in_partial_run'
    assert adapter.validated_manifest(rows, 'whole-close') == 30
    changes = [('own_tcp_world_m', [0., 0., 0.]), ('cached_geometry_sample_time_s', 30.),
               ('contact_label', True), ('artifact', '../evaluator-only/labels.json')]
    for key, value in changes:
        bad = copy.deepcopy(rows)
        bad[30][key] = value
        with pytest.raises(ValueError):
            adapter.validated_manifest(bad, 'whole-close')
    bad = manifest()
    bad[31]['tcp_source_field'] = 'world.obs.robot0_eef_pos'
    with pytest.raises(ValueError, match='linkage'):
        adapter.validated_manifest(bad, 'whole-close')
    bad = manifest()
    bad[31]['own_tcp_world_m'] = bad[30]['own_tcp_world_m']
    with pytest.raises(ValueError, match='explicitly saved'):
        adapter.validated_manifest(bad, 'whole-close')


def test_pinned_cell_loader_reads_only_synthetic_sensor_artifacts_and_detects_tampering(tmp_path, monkeypatch):
    rows = manifest()
    payload = io.BytesIO()
    np.savez_compressed(payload, rgb=np.zeros((384, 384, 3), np.uint8),
                        depth_m=np.ones((384, 384), np.float32), intrinsics=np.eye(3), camera_to_world=np.eye(4))
    for row in rows:
        path = tmp_path/row['artifact']
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(payload.getvalue())
        row['artifact_sha256'] = adapter.file_hash(path)
    source = tmp_path/'sensor-captures.json'
    source.write_text(json.dumps(rows))
    journal = tmp_path/'episodes.jsonl'
    journal.write_bytes(b'Intentionally not JSON: hash linkage only, never decode evaluator state.')
    seal = {'sha256': {'sensor-captures.json': adapter.file_hash(source),
            **{r['artifact']: r['artifact_sha256'] for r in rows}}, 'journal_parse_errors': [],
            'journal_sha256_linkage_only': adapter.file_hash(journal), 'holding': None}
    (tmp_path/'sensor-seal.json').write_text(json.dumps(seal))
    hashes = {n: adapter.file_hash(tmp_path/n) for n in ('sensor-captures.json', 'sensor-seal.json')}
    original_open = Path.open
    def sensor_only(path, *args, **kwargs):
        assert 'evaluator-only' not in path.parts
        if path.name == 'episodes.jsonl':
            assert args == ('rb',)  # The existing streaming hash helper only.
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', sensor_only)
    loaded = adapter.load_cell(tmp_path, 'whole-close', hashes)
    assert loaded['reference_index'] == 30 and len(loaded['frames']) == 47
    assert loaded['meta'] == rows and loaded['tcps'][30] == rows[30]['own_tcp_world_m']
    assert loaded['source_journal_sha256'] == seal['journal_sha256_linkage_only']
    (tmp_path/rows[-1]['artifact']).write_bytes(b'altered')
    with pytest.raises(ValueError, match='hash differs'):
        adapter.load_cell(tmp_path, 'whole-close', hashes)
    source.write_text('[]')
    with pytest.raises(ValueError, match='receipt changed'):
        adapter.load_cell(tmp_path, 'whole-close', hashes)


def test_exact_sensor_prefix_comparison_uses_bytes_own_and_only_registered_prefixes():
    packets = {}
    image = {'rgb': np.zeros((2, 2, 3), np.uint8), 'depth_m': np.ones((2, 2), np.float32),
             'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    for condition in adapter.CONDITIONS:
        rows = manifest(condition)
        packets[condition] = {'frames': [copy.deepcopy(image) for _ in rows], 'meta': rows}
    checks = adapter.check_sensor_prefixes(packets, image)
    assert [r['captures'] for r in checks] == [31, 30, 6]
    packets['neck-close']['frames'][6]['rgb'][0, 0, 0] = 1
    packets['neck-open_hold']['frames'][6]['rgb'][0, 0, 0] = 1
    assert adapter.check_sensor_prefixes(packets, image) == checks
    packets['whole-open_hold']['meta'][30]['own_tcp_world_m'] = [999., 0., 0.]
    with pytest.raises(ValueError, match='sensor prefix'):
        adapter.check_sensor_prefixes(packets, image)


def test_reference13_compatibility_and_variable_preclose_missing_values():
    old_packet = packet(30, 13)
    rows = native_rows(30)
    current = adapter.enrich_track(rows, old_packet, 0, [1, 2])
    old = adapter.prior.enrich_track(rows, old_packet, 0, [1, 2])
    assert all(all(b[k] == v for k, v in a.items()) for a, b in zip(old, current, strict=True))
    p = packet(47, 30)
    native = native_rows(47)
    p['frames'][30]['depth_m'][:] = np.nan
    p['tcps'][32] = None
    enriched = adapter.enrich_track(native, p, 7, [1, 2])
    assert all(r['reference_deltas']['preclose'] is None for r in enriched[:30])
    assert enriched[31]['surface_point_world_m'] == [1.5, 2.5, 1.]
    assert enriched[31]['reference_deltas']['preclose']['point_delta_norm_m'] is None
    assert enriched[31]['reference_deltas']['preclose']['tcp_delta_m'] == [0., 0., .001]
    assert enriched[32]['reference_status'] == 'missing_own_tcp'
    assert enriched[32]['reference_deltas']['preclose'] is None and enriched[32]['own_tcp_world_m'] is None
    assert all(all(a[k] == b[k] for k in adapter.prior.NATIVE_FIELDS) for a, b in zip(native, enriched, strict=True))
    json.dumps(enriched, allow_nan=False)


def test_single_call_per_all492_seeds_full_status_rows_and_fixed_denominator(monkeypatch):
    p = packet(4, 1)
    calls = []
    def synthetic_tracker(rgb, seed, cv):
        calls.append(list(seed))
        rows = native_rows(len(rgb))
        if len(calls) == 1:
            rows[1]['status'] = 'native_failure'
            for row in rows[2:]:
                row['status'] = 'unknown_after_native_failure'
        return rows
    monkeypatch.setattr(adapter.base.lk, 'track_lk', synthetic_tracker)
    tracks = list(adapter.iter_cell_tracks(p, adapter.fixed_seeds(), SimpleNamespace(__version__='4.11.0')))
    assert calls == adapter.fixed_seeds() and len(tracks) == 492
    assert all(len(t) == 4 for t in tracks)
    summaries = adapter.summarize_tracks(tracks, p)
    assert summaries[0]['references']['preclose']['available'] is False
    assert summaries[3]['denominator'] == 492 and summaries[3]['unknown_after_failure_count'] == 1
    metric = summaries[3]['references']['preclose']['metrics']['point_minus_tcp_delta_norm_m']
    assert metric['count'] == 491 and metric['missing_count'] == 1 and metric['median'] == .002
    with pytest.raises(ValueError, match='all 492'):
        adapter.summarize_tracks(tracks[1:], p)
    with pytest.raises(ValueError, match='fixed full seed'):
        list(adapter.iter_cell_tracks(p, adapter.fixed_seeds()[1:], SimpleNamespace(__version__='4.11.0')))


def test_native_prefix_comparison_all_nine_fields_accepts_different_total_horizons():
    a = adapter.enrich_track(native_rows(47), packet(47, 30), 9, [1, 2])
    b = adapter.enrich_track(native_rows(46), packet(46, 29), 9, [1, 2])
    b[6]['point_pixel_index_xy'] = [99, 99]
    assert adapter.prefix_disagreements(a, b, 6) == []
    for key in adapter.prior.NATIVE_FIELDS:
        changed = copy.deepcopy(b)
        changed[5][key] = 'changed'
        assert adapter.prefix_disagreements(a, changed, 6) == [{'seed_id': 9, 'capture_id': 5, 'fields': [key]}]
    with pytest.raises(ValueError, match='prefixes'):
        adapter.prefix_disagreements(a, b[:5], 6)
    wrong_seed = copy.deepcopy(b)
    wrong_seed[0]['seed_id'] = 8
    with pytest.raises(ValueError, match='prefixes'):
        adapter.prefix_disagreements(a, wrong_seed, 6)
