import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from embodied_runtime.experiments import task2_point_anchor_retention_transfer as transfer


def read_json(path):
    return json.loads(path.read_text())


def synthetic_setup(tmp_path, monkeypatch, count=492, mismatch=False, fail_after=None):
    # No stored frame, surface projection or real LK call is used by this fixture.
    monkeypatch.setattr(transfer.adapter, 'SEED_COUNT', count)
    monkeypatch.setattr(transfer, 'TOTAL_TRACKS', count*4)
    monkeypatch.setattr(transfer, 'TOTAL_ROWS', count*sum(transfer.FRAME_COUNTS.values()))
    for attribute in ('PROTOCOL', 'SOURCE_RECEIPT'):
        path = tmp_path/attribute
        path.write_text('synthetic source, not an archive')
        monkeypatch.setattr(transfer, attribute, path)
    preflight, review = tmp_path/'preflight.json', tmp_path/'review.json'
    preflight.write_text('{}')
    review.write_text('{}')
    packets = {c: {'condition': c, 'frames': [None]*n, 'reference_index': n-17,
        'tcps': [None]*n} for c, n in transfer.FRAME_COUNTS.items()}
    seeds, calls = transfer.adapter.fixed_seeds()[:count], []

    def synthetic_tracks(packet, input_seeds, cv2):
        assert input_seeds == seeds
        for seed_id, seed in enumerate(input_seeds):
            calls.append((packet['condition'], seed_id))
            if fail_after is not None and len(calls) > fail_after:
                raise RuntimeError('injected failure; no retry')
            rows = []
            for i in range(len(packet['frames'])):
                row = {k: None for k in transfer.adapter.prior.NATIVE_FIELDS}
                row.update(frame=i, seed_id=seed_id, capture_id=i, seed_pixel_index_xy=seed,
                    status='seeded' if i == 0 else 'native_failure' if i == 1 else 'unknown_after_native_failure',
                    point_pixel_index_xy=seed if i == 0 else [3., 4.] if i == 1 else None,
                    attempted_backward_point_pixel_index_xy=[8., 9.] if i == 1 else None,
                    surface_point_world_m=None, reference_deltas={'preclose': None}, holding=None)
                if mismatch and packet['condition'] == 'whole-open_hold' and i == 1:
                    row['attempted_backward_point_pixel_index_xy'] = [8., 9.5]
                rows.append(row)
            yield rows

    monkeypatch.setattr(transfer.adapter, 'iter_cell_tracks', synthetic_tracks)
    args = ({'commit': 'synthetic', 'dirty_status': ''}, {'synthetic': True},
            seeds, packets, {'synthetic': True}, preflight, review, SimpleNamespace())
    return args, calls


def assert_seal(output):
    seal = read_json(output/'sensor-seal.json')
    for name, digest in seal['sha256'].items():
        assert transfer.file_hash(output/name) == digest
    for name, digest in read_json(output/'artifacts.json').items():
        assert transfer.file_hash(output/name) == digest
    return seal


def test_complete_synthetic_four_cell_population_failure_rows_prefixes_and_seals(tmp_path, monkeypatch):
    args, calls = synthetic_setup(tmp_path, monkeypatch)
    output = tmp_path/'run'
    transfer.execute(output, *args)
    assert calls == [(c, s) for c in transfer.adapter.CONDITIONS for s in range(492)]
    assert (assert_seal(output)['tracks'], assert_seal(output)['rows']) == (1968, 91512)
    for condition, count in transfer.FRAME_COUNTS.items():
        rows = [json.loads(line) for line in (output/f'{condition}-tracks.jsonl').read_text().splitlines()]
        assert [(r['seed_id'], r['capture_id']) for r in rows] == [(s, i) for s in range(492) for i in range(count)]
        assert rows[1]['status'] == 'native_failure'
        assert rows[1]['point_pixel_index_xy'] == [3., 4.]
        assert rows[1]['attempted_backward_point_pixel_index_xy'] == [8., 9.]
        assert all(r['status'] == 'unknown_after_native_failure' and r['point_pixel_index_xy'] is None
                   for r in rows[2:count])
    summary = read_json(output/'sensor-summary.json')
    assert summary['holding'] is None and not summary['proxy_membership_available']
    for rows in summary['cells'].values():
        assert all(r['denominator'] == 492 for r in rows)
        assert all(m['missing_count'] == 492 and m['count'] == 0
                   for r in rows for m in r['references']['preclose']['metrics'].values())
    prefixes = [json.loads(line) for line in (output/'prefix-agreement.jsonl').read_text().splitlines()]
    assert len(prefixes) == 32964
    assert all(set(p['native_fields_equal']) == set(transfer.adapter.prior.NATIVE_FIELDS)
               and p['exact_agreement'] and all(p['native_fields_equal'].values()) for p in prefixes)
    assert not (output/'failure.json').exists()
    with pytest.raises(FileExistsError):
        transfer.execute(output, *args)


def test_mismatch_retains_and_seals_entire_batch_before_failure(tmp_path, monkeypatch):
    args, calls = synthetic_setup(tmp_path, monkeypatch, count=2, mismatch=True)
    output = tmp_path/'mismatch'
    with pytest.raises(ValueError, match='complete batch retained'):
        transfer.execute(output, *args)
    seal = assert_seal(output)
    assert len(calls) == seal['tracks'] == 8 and seal['rows'] == 372
    failed = read_json(output/'failure.json')
    assert failed['complete_sensor_seal_present'] and failed['retries'] == 0
    prefixes = read_json(output/'prefix-summary.json')['comparisons']
    assert len(prefixes[0]['disagreements']) == 2
    assert all(p['exact_agreement'] for p in prefixes[1:])
    journal = [json.loads(line) for line in (output/'episodes.jsonl').read_text().splitlines()]
    assert [r['kind'] for r in journal][-2:] == ['sensor_outputs_sealed', 'failure']


def test_runtime_failure_keeps_partial_rows_and_receipts_without_complete_seal_or_retry(tmp_path, monkeypatch):
    args, calls = synthetic_setup(tmp_path, monkeypatch, count=2, fail_after=3)
    output = tmp_path/'failure'
    with pytest.raises(RuntimeError, match='injected failure'):
        transfer.execute(output, *args)
    failed = read_json(output/'failure.json')
    assert (failed['completed_tracks'], failed['written_rows'], failed['retries']) == (3, 141, 0)
    assert failed['active_condition'] == 'whole-open_hold' and len(calls) == 4
    assert not failed['complete_sensor_seal_present'] and not (output/'sensor-seal.json').exists()
    assert len((output/'whole-close-tracks.jsonl').read_text().splitlines()) == 94
    assert len((output/'whole-open_hold-tracks.jsonl').read_text().splitlines()) == 47
    for name, digest in failed['retained_sha256'].items():
        assert transfer.file_hash(output/name) == digest
    for name, digest in read_json(output/'artifacts.json').items():
        assert transfer.file_hash(output/name) == digest


def test_exact_review_freeze_and_environment_gate_precedes_source_or_tracker(tmp_path, monkeypatch):
    protocol = tmp_path/'protocol.md'
    protocol.write_text('synthetic frozen protocol')
    monkeypatch.setattr(transfer, 'PROTOCOL', protocol)
    identity = {'commit': 'synthetic', 'dirty_status': '', 'source_sha256': {'test': 'hash'}}
    monkeypatch.setattr(transfer, 'code_identity', lambda: copy.deepcopy(identity))
    monkeypatch.setattr(transfer, 'environment', lambda cv: {'synthetic': True})
    source_calls = []
    monkeypatch.setattr(transfer, 'load_inputs', lambda: (source_calls.append(True) or [], {}, {'synthetic': True}))
    preflight, review = tmp_path/'preflight.json', tmp_path/'review.json'
    receipt = {'status': 'pass', 'code': identity, 'environment': {'synthetic': True},
        'protocol_sha256': transfer.file_hash(protocol), 'lk_settings': transfer.jsonable(transfer.base.lk.LK_SETTINGS),
        'total_tracks': 1968, 'total_track_rows': 91512,
        'archived_tracking_projection_displacement_computed': False, 'LK_model_physics_render_calls': 0,
        'admission': {'synthetic': True}}
    preflight.write_text(json.dumps(receipt))
    approved = {'status': 'pass', 'freeze_commit': 'synthetic', 'preflight_sha256': transfer.file_hash(preflight),
        'protocol_sha256': transfer.file_hash(protocol), 'authorized_batches': 1}
    for key, bad in [('status', 'fail'), ('freeze_commit', 'other'), ('preflight_sha256', 'other'),
                     ('protocol_sha256', 'other'), ('authorized_batches', 2)]:
        review.write_text(json.dumps({**approved, key: bad}))
        with pytest.raises(ValueError, match='one-batch PASS'):
            transfer.admit_run(preflight, review, None)
    assert not source_calls
    review.write_text(json.dumps(approved))
    transfer.admit_run(preflight, review, None)
    assert source_calls == [True]
    identity['dirty_status'] = 'changed'
    with pytest.raises(ValueError, match='one-batch PASS'):
        transfer.admit_run(preflight, review, None)
    assert source_calls == [True]


def test_runtime_provenance_rejects_thread_change_without_mutating_settings(monkeypatch):
    cv = SimpleNamespace(__version__='4.11.0', getNumThreads=lambda: 7,
                         getBuildInformation=lambda: 'synthetic build')
    expected = {**transfer.ENVIRONMENT, 'executable': transfer.sys.executable,
        'python': transfer.sys.version, 'numpy': transfer.np.__version__, 'opencv_threads': 7,
        'opencv_build_sha256': transfer.hashlib.sha256(b'synthetic build').hexdigest()}
    monkeypatch.setattr(transfer, 'ENVIRONMENT', expected)
    assert transfer.environment(cv) == expected
    cv.getNumThreads = lambda: 8
    with pytest.raises(ValueError, match='thread provenance'):
        transfer.environment(cv)
