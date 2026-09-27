import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_point_adapter as adapter


def returned(text='<box><500><500></box>', tokens=None):
    return {'raw_response': text, 'raw_response_type': 'str',
            'observed_decoded_token_sequences': [[[10, 99] if tokens is None else tokens]]}


@pytest.mark.parametrize('text,tokens,reason', [
    ('<box><500><500></box>', [10], 'incomplete_or_length_limited'),
    ('<box><500><500></box>', [10]*255+[99], 'incomplete_or_length_limited'),
    ('<box>none</box>', [10, 99], 'none'),
    ('<box><500><500></box><box><250><250></box>', [10, 99], 'multiple_points'),
    ('<box><1000><500></box>', [10, 99], 'point_out_of_frame'),
    ('<box><100><100><600><600></box>', [10, 99], 'single_box'),
    ('<box><500><500></box><box>', [10, 99], 'malformed'),
])
def test_nonadmissions_preserve_raw_output_and_actual_tokens_without_repair(text, tokens, reason):
    value = adapter.analyze_rgb_return(returned(text, tokens), 100, 16384, 99)
    assert value['status'] == 'not_admitted' and value['point'] is None and value['reason'] == reason
    assert value['raw_output'] == text and value['generation_audit']['actual_generated_token_ids'] == tokens
    assert value['holding'] is None and value['semantic_target_identity_verified'] is False


def test_admitted_native_point_has_only_image_coordinates():
    value = adapter.analyze_rgb_return(returned('<box><275><275></box>'), 100, 16384, 99)
    assert value['status'] == 'admitted_rgb_point'
    assert value['point'] == {'normalized': [275, 275], 'continuous_xy': [105.60000000000001]*2,
                             'pixel_index_xy': [105, 105]}
    assert value['depth_read'] is False and value['holding'] is None
    with pytest.raises(ValueError, match='token audit unavailable'):
        adapter.analyze_rgb_return({**returned(), 'observed_decoded_token_sequences': []}, 100, 16384, 99)


def test_four_case_selection_uses_postevent_and_prelift_only(monkeypatch):
    rows = []
    for i in range(25):
        row = {key: None for key in ('phase', 'after_step', 'control', 'source_capture_stream',
            'source_capture_seq', 'capture_read_sim_time_s', 'cached_geometry_sample_time_s',
            'exact_observation_sample_time_s', 'artifact_sha256')}
        rows.append({**row, 'capture_id': 31+i, 'artifact': f'{31+i}.npz', 'own_observations': 'excluded'})
    called = []
    def select(manifest, condition):
        called.append(condition)
        return rows
    monkeypatch.setattr(adapter.suffix, 'selected_manifest', select)
    images = adapter.select_images({'present': object(), 'away': object()})
    assert called == ['neck-present', 'neck-away']
    assert [r['case_id'] for r in images] == ['present-postevent', 'away-postevent', 'away-prelift', 'present-prelift']
    assert [r['capture_id'] for r in images] == [31, 31, 47, 47]
    assert all('own_observations' not in row for row in images)


def test_loader_decodes_RGB_only_and_rejects_changed_archive(tmp_path, monkeypatch):
    directory = tmp_path/'neck-away'
    directory.mkdir()
    path = directory/'scene.npz'
    path.write_bytes(b'synthetic hash-bound image archive')
    image_spec = {'directory': 'neck-away', 'artifact': 'scene.npz', 'artifact_sha256': adapter.file_hash(path)}
    read_keys = []
    class RGBOnly:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, key):
            read_keys.append(key)
            assert key == 'rgb'
            return np.full((384, 384, 3), 7, np.uint8)
    monkeypatch.setattr(adapter.np, 'load', lambda path, allow_pickle: RGBOnly())
    assert np.all(adapter.load_rgb(tmp_path, image_spec) == 7) and read_keys == ['rgb']
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='archive changed'):
        adapter.load_rgb(tmp_path, image_spec)


def test_native_input_receives_unannotated_RGB_and_only_fixed_question(monkeypatch):
    rgb, processor = np.arange(384*384*3, dtype=np.uint8).reshape(384, 384, 3), object()
    seen = []
    def native_input(actual_processor, image, condition):
        assert actual_processor is processor and image is rgb
        seen.append(condition)
        return 'unchanged native processor result'
    monkeypatch.setattr(adapter.native, 'native_input', native_input)
    assert adapter.prepare_native_input(processor, rgb, 'away-prelift') == 'unchanged native processor result'
    assert seen == [{'condition': 'away-prelift', 'query': 'the wine bottle', 'question': 'Point to: the wine bottle.'}]
    with pytest.raises(ValueError, match='registered case'):
        adapter.prepare_native_input(processor, rgb[:200], 'away-prelift')
