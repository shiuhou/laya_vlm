"""Fixed original-RGB exports after the four source cells have closed.

Reuses the short-lift report's unscaled Pillow tiles, without its track/mask
dependencies. This library has no CLI and performs no temporal extraction.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import task2_point_anchor_retention_adapter as source
from .records import file_hash


def selected_captures(packet):
    condition = packet['condition']
    if condition not in source.CONDITIONS:
        raise ValueError('registered matrix cell required')
    reference = source.APPROACH_COUNTS[condition.split('-', 1)[0]]
    if packet['reference_index'] != reference or len(packet['frames']) != reference+17:
        raise ValueError('complete fixed source schedule required')
    choices = [('preintervention', reference), ('postclose_or_hold', reference+8)]
    choices += [('lift_control_'+str(control), reference+9+control) for control in range(8)]
    for label, capture in choices:
        row = packet['meta'][capture]
        phase = 'approach' if label == 'preintervention' else 'close_or_hold' if label == 'postclose_or_hold' else 'lift'
        control = 7 if label in ('preintervention', 'postclose_or_hold') else int(label.rsplit('_', 1)[1])
        if (row['capture_id'], row['phase'], row['control']) != (capture, phase, control):
            raise ValueError('fixed RGB boundary metadata differs')
    return choices


def export_cell(packet, target):
    """Paste exact RGB arrays; labels occupy separate 24-pixel header strips."""
    choices = selected_captures(packet)
    target = Path(target)
    target.mkdir(exist_ok=False)
    sheet = Image.new('RGB', (384*5, 408*2), 'white')
    draw, captures = ImageDraw.Draw(sheet), []
    for ordinal, (label, capture) in enumerate(choices):
        rgb, meta = packet['frames'][capture]['rgb'], packet['meta'][capture]
        if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
            raise ValueError('original 384x384 uint8 RGB required')
        image = Image.fromarray(rgb)
        name = label+'.png'
        image.save(target/name)
        with Image.open(target/name) as exported:
            if not np.array_equal(np.asarray(exported), rgb):
                raise ValueError('unmarked RGB export differs from source array')
        x, y = ordinal % 5*384, ordinal // 5*408
        sheet.paste(image, (x, y+24))
        draw.text((x+3, y+4), f"{label}; cap{capture}; t={meta['capture_sim_time']:.6f}s", fill='black')
        captures.append({'label': label, 'capture': meta, 'unmarked_rgb_artifact': name,
                         'unmarked_rgb_sha256': file_hash(target/name)})
    sheet.save(target/'all_fixed_original_rgb.png')
    return {'condition': packet['condition'], 'captures': captures,
            'source_sha256': packet['source_sha256'], 'source_journal_sha256': packet['source_journal_sha256'],
            'sheet_artifact': 'all_fixed_original_rgb.png',
            'sheet_sha256': file_hash(target/'all_fixed_original_rgb.png'),
            'rgb_overlays_crops_or_resampling': False, 'visual_inspection_completed': False}


def produce(matrix, source_hashes, output):
    """Call only after matrix completion and independently reviewed source hashes."""
    _, packets, admission = source.load_inputs(matrix, source_hashes)
    output = Path(output)
    output.mkdir(exist_ok=False)
    cells = [export_cell(packets[c], output/c) for c in source.CONDITIONS]
    report = {'matrix_directory': str(Path(matrix).resolve()), 'source_admission': admission,
              'cells': cells, 'scope': 'fixed original RGB export and sensor-source admission only',
              'new_tracking_model_physics_render_calls': 0, 'mask_data_available': False,
              'holding_grasp_success_or_anchor_superiority_established': False}
    with (output/'rgb-source-report.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report
