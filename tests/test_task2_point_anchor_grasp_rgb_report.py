import numpy as np
import pytest
from PIL import Image

from embodied_runtime.experiments import task2_point_anchor_grasp_rgb_report as report


def packet(condition):
    reference = 30 if condition.startswith('whole-') else 29
    frames, meta = [], []
    for capture in range(reference+17):
        phase = 'approach' if capture <= reference else 'close_or_hold' if capture <= reference+8 else 'lift'
        control = 7 if capture <= reference else (capture-reference-1) % 8
        frames.append({'rgb': np.full((384, 384, 3), capture, np.uint8)})
        meta.append({'capture_id': capture, 'phase': phase, 'control': control, 'capture_sim_time': capture*.05})
    return {'condition': condition, 'reference_index': reference, 'frames': frames, 'meta': meta,
            'source_sha256': {}, 'source_journal_sha256': 'synthetic'}


def test_fixed_ten_boundaries_and_unmarked_unscaled_original_exports(tmp_path):
    for condition, expected in [('whole-close', [30, 38, *range(39, 47)]),
                                ('neck-open_hold', [29, 37, *range(38, 46)])]:
        source = packet(condition)
        assert [capture for _, capture in report.selected_captures(source)] == expected
        target = tmp_path/condition
        result = report.export_cell(source, target)
        assert result['visual_inspection_completed'] is False
        with Image.open(target/'all_fixed_original_rgb.png') as image:
            sheet = np.asarray(image)
        assert sheet.shape == (816, 1920, 3)
        for ordinal, (item, capture) in enumerate(zip(result['captures'], expected, strict=True)):
            with Image.open(target/item['unmarked_rgb_artifact']) as image:
                assert np.array_equal(np.asarray(image), source['frames'][capture]['rgb'])
            x, y = ordinal % 5*384, ordinal // 5*408+24
            assert np.array_equal(sheet[y:y+384, x:x+384], source['frames'][capture]['rgb'])
        source['meta'][expected[2]]['control'] = 7
        with pytest.raises(ValueError, match='boundary metadata'):
            report.selected_captures(source)
