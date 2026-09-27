import copy
import json

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_image_motion_report as report
from embodied_runtime.experiments.records import RunRecorder


def synthetic_cells():
    metadata = [{'artifact': f'{i}.npz', 'artifact_sha256': 'synthetic', 'phase': 'synthetic',
        'after_step': 29+(max(0, i-1)//8), 'control': None if i == 0 else (i-1)%8,
        'source_capture_stream': 'scene' if i == 0 else 'auxiliary',
        'source_capture_seq': 2 if i == 0 else i, 'capture_read_sim_time_s': i*.05} for i in range(25)]
    rows = []
    for seed in range(492):
        for i in range(25):
            status = 'seeded' if i == 0 else 'native_status_ok'
            if seed == 0 and i >= 8:
                status = 'native_failure' if i == 8 else 'unknown_after_native_failure'
            point = [212+seed%12+i*.1, 169+seed//12]
            if seed == 1 and i == 24:
                point[0] = 500.
            if status == 'unknown_after_native_failure':
                point = None
            available = status in report.NATIVE_OK
            metrics = {key: float(i) if available and (ci < 2 or i != 8) else None
                       for ci, key in enumerate(report.assay.motion.METRICS)}
            rows.append({**metadata[i], 'seed_id': seed, 'capture_id': i, 'status': status,
                'point_pixel_index_xy': point, 'image_motion': {'reference_capture_id': 0,
                    'status_A': 'available' if available else 'missing',
                    'status_B': 'available' if available and i != 8 else 'missing', 'metrics': metrics}})
    summaries = []
    for i in range(25):
        available = 492 if i < 8 else 491
        summaries.append({'capture_id': i, 'denominator': 492, 'reference_capture_id': 0,
            'native_admitted_count': available, 'native_failure_count': int(i == 8),
            'unknown_after_failure_count': int(i > 8), 'A_available_count': available,
            'B_available_count': available if i != 8 else 0,
            'metrics': {key: {'count': available if ci < 2 or i != 8 else 0,
                'missing_count': 492-available if ci < 2 or i != 8 else 492,
                **{field: float(i) if ci < 2 or i != 8 else None for field in ('min', 'q25', 'median', 'q75', 'max')}}
                for ci, key in enumerate(report.assay.motion.METRICS)}})
    return {role: {'rows': rows, 'metadata': metadata, 'summaries': summaries} for role in report.assay.ROLES}


def test_report_rejects_missing_rows_changed_binding_and_hidden_missingness():
    cell = synthetic_cells()['present']
    report.validate_rows(cell['rows'], cell['summaries'], cell['metadata'])
    with pytest.raises(ValueError, match='complete ordered'):
        report.validate_rows(cell['rows'][:-1], cell['summaries'], cell['metadata'])
    summaries = copy.deepcopy(cell['summaries'])
    summaries[8]['metrics']['rgb_minus_tcp_delta_v_px']['missing_count'] = 0
    with pytest.raises(ValueError, match='missingness'):
        report.validate_rows(cell['rows'], summaries, cell['metadata'])
    metadata = copy.deepcopy(cell['metadata'])
    metadata[16]['artifact_sha256'] = 'wrong-frame'
    with pytest.raises(ValueError, match='binding'):
        report.validate_rows(cell['rows'], cell['summaries'], metadata)


def test_unreviewed_seal_stops_before_source_or_plot_access(tmp_path, monkeypatch):
    (tmp_path/'sensor-seal.json').write_text('{}')
    def forbidden(*args, **kwargs):
        pytest.fail('unreviewed source must not reach image or plot access')
    monkeypatch.setattr(report, 'load_endpoint_rgb', forbidden)
    monkeypatch.setattr(report, 'curves_figure', forbidden)
    with pytest.raises(ValueError, match='seal changed'):
        report.report(tmp_path, 'not-the-seal-hash')
    assert not (tmp_path/'report').exists()


def test_endpoint_loader_decodes_only_four_full_RGB_arrays(tmp_path, monkeypatch):
    directory = tmp_path/'neck-present'
    directory.mkdir()
    metadata = synthetic_cells()['present']['metadata']
    for i in report.assay.ENDPOINTS.values():
        path = directory/metadata[i]['artifact']
        path.write_bytes(f'synthetic {i}'.encode())
        metadata[i]['artifact_sha256'] = report.file_hash(path)
    keys, opened = [], []
    class RGBOnly:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, key):
            keys.append(key)
            assert key == 'rgb'
            return np.full((384, 384, 3), 42, np.uint8)
    def load(path, *, allow_pickle):
        assert allow_pickle is False
        opened.append(int(path.stem))
        return RGBOnly()
    monkeypatch.setattr(report.np, 'load', load)
    binding = {'source_root': str(tmp_path), 'cells': {'present': {'directory': 'neck-present'}}}
    images = report.load_endpoint_rgb(binding, 'present', metadata)
    assert opened == [0, 8, 16, 24] and keys == ['rgb']*4
    assert all(np.all(image == 42) for image in images.values())


def test_synthetic_figures_keep_all_captures_shared_scales_and_defined_positions(tmp_path):
    cells = synthetic_cells()
    fig, axes = report.curves_figure(cells)
    assert axes.shape == (2, 6)
    for ci in range(6):
        assert axes[0, ci].get_shared_y_axes().joined(axes[0, ci], axes[1, ci])
    assert len(axes[0, 2].lines[0].get_ydata()) == 25
    assert axes[0, 1].lines[2].get_ydata()[8] == 0
    assert axes[0, 1].lines[3].get_ydata()[8] == 492
    fig.savefig(tmp_path/'synthetic-curves.png', dpi=70)
    import matplotlib.pyplot as plt
    plt.close(fig)
    image = np.zeros((384, 384, 3), np.uint8)
    image[:, :, 0] = np.arange(384, dtype=np.uint16)[:, None] % 256
    images = {i: image.copy() for i in report.assay.ENDPOINTS.values()}
    fig, axes, counts = report.endpoints_figure('present', cells['present'], images)
    assert all(np.array_equal(np.asarray(ax.images[0].get_array()), image) for ax in axes.flat)
    assert counts['close1']['native_failure'] == 1 and counts['close1']['defined_positions'] == 492
    assert counts['postlift']['unknown_after_failure'] == 1
    assert counts['postlift']['off_image_positions'] == 1 and counts['postlift']['defined_positions'] == 491
    offsets = axes[1, 3].collections[0].get_offsets()
    assert len(offsets) == 491 and 500. in offsets[:, 0]
    assert axes[1, 3].get_xlim() == (-.5, 383.5)
    fig.savefig(tmp_path/'synthetic-endpoints.png', dpi=70)
    plt.close(fig)


def test_complete_synthetic_report_binds_seal_without_duplicate_metrics(tmp_path, monkeypatch):
    cells = synthetic_cells()
    physical = tmp_path/'physical'
    for role in report.assay.ROLES:
        directory = physical/('neck-'+role)
        directory.mkdir(parents=True)
        for i in report.assay.ENDPOINTS.values():
            path = directory/f'{i}.npz'
            path.write_bytes(f'endpoint {i}'.encode())
            digest = report.file_hash(path)
            cells[role]['metadata'][i]['artifact_sha256'] = digest
            for row in cells[role]['rows'][i::25]:
                row['artifact_sha256'] = digest
    binding = {'source_root': str(physical), 'cells': {r: {'directory': 'neck-'+r} for r in report.assay.ROLES}}
    source = tmp_path/'extraction'
    recorder = RunRecorder(source, {}, {'run_id': 'synthetic'})
    report.assay.write_json(source/'binding.json', binding)
    report.assay.write_json(source/'admission.json', {'binding_sha256': report.file_hash(source/'binding.json'),
        'binding': binding, 'captures': {r: cells[r]['metadata'] for r in report.assay.ROLES}})
    report.assay.write_json(source/'sensor-summary.json', {'reference_capture_id': 0,
        'endpoints': report.assay.ENDPOINTS, 'mechanical_labels_joined': False, 'holding': None,
        'identity_verified': None, 'cells': {r: cells[r]['summaries'] for r in report.assay.ROLES}})
    for role in report.assay.ROLES:
        with (source/f'{role}-tracks.jsonl').open('x') as stream:
            for row in cells[role]['rows']:
                stream.write(json.dumps(row)+'\n')
    report.assay.write_json(source/'sensor-seal.json', {'complete': True, 'tracks': 984, 'rows': 24600,
        'measured_scene_depth_read': False, 'evaluator_read': False,
        'sha256': {p.name: report.file_hash(p) for p in source.iterdir() if p.name != 'episodes.jsonl'}})
    digest = report.file_hash(source/'sensor-seal.json')
    recorder.record('termination', {'reason': 'all_postevent_image_motion_rows_sealed', 'tracks': 984,
        'rows': 24600, 'sensor_seal_sha256': digest, 'retries': 0})
    recorder.close()
    class RGBOnly:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, key):
            assert key == 'rgb'
            return np.zeros((384, 384, 3), np.uint8)
    monkeypatch.setattr(report.np, 'load', lambda path, allow_pickle: RGBOnly())
    target = report.report(source, digest)
    index = json.loads((target/'index.json').read_text())
    assert index['source_summary']['sha256'] == report.file_hash(source/'sensor-summary.json')
    assert index['actual_source_RGB_visual_inspection'] == 'pending'
    assert index['new_features_or_tracking'] is False and 'cells' not in index
    assert len((target/'index.json').read_bytes()) < 6000
    assert {p.name for p in target.glob('*.png')} == {'image-motion-curves.png', 'present-endpoint-rgb.png', 'away-endpoint-rgb.png'}
    with pytest.raises(FileExistsError):
        report.report(source, digest)
