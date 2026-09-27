"""Export original stored RGB arrays at fixed diagnostic boundaries, without rendering."""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import task2_additional_stationary_grasp as probe
from .records import file_hash

RAW = probe.prior.base.RAW / 'task2-additional-stationary-grasp-run-01'
OUTPUT = probe.prior.base.ROOT / 'docs/evidence/autonomous_research'
PREFIX = 'task2_additional_stationary_grasp'


def produce():
    index = {'raw_directory': str(RAW), 'physics_freeze': '945c96d81916f7952d9b40565c52b00085363544',
        'source': 'saved original uint8 RGB arrays; copied at native resolution without masks, crops or rerendering',
        'new_render_calls': 0, 'conditions': {}}
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    for condition in probe.ORDER:
        directory = RAW / condition
        sensors = probe.prior.base.read(directory / 'sensor-captures.json')
        seal = probe.prior.base.read(directory / 'sensor-seal.json')
        if file_hash(directory / 'sensor-captures.json') != seal['sha256']['sensor-captures.json']:
            raise ValueError('Sensor manifest changed')
        pre = [row for row in sensors if row['phase'] == 'approach'][-1]
        first = [row for row in sensors if row['phase'] == 'close_or_hold'][-1]
        additional = [row for row in sensors if row['phase'] == 'additional_close']
        lift = [row for row in sensors if row['phase'] == 'lift']
        if len(additional) != 8 or len(lift) != 8:
            raise ValueError('All eight additional and lift endpoint images required')
        selected = [('Before first GRASP', pre), ('After first GRASP', first)] + [
            (f'Added GRASP: control {row["control"]}', row) for row in additional] + [
            (f'Lift: control {row["control"]}', row) for row in lift]
        width, height, caption, header = 384, 384, 54, 44
        sheet = Image.new('RGB', (6 * width, header + 3 * (height + caption)), '#ffffff')
        draw = ImageDraw.Draw(sheet)
        draw.text((12, 10), condition + ': original stored RGB (18 frames)', fill='#111111', font=title_font)
        ledger = []
        for ordinal, (label, row) in enumerate(selected):
            path = directory / row['artifact']
            if file_hash(path) != row['artifact_sha256'] or seal['sha256'][row['artifact']] != row['artifact_sha256']:
                raise ValueError('Sealed source image changed')
            with np.load(path, allow_pickle=False) as data:
                rgb = data['rgb']
            if rgb.shape != (height, width, 3) or rgb.dtype != np.uint8:
                raise ValueError('Original fixed camera RGB schema required')
            x, y = (ordinal % 6) * width, header + (ordinal // 6) * (height + caption)
            draw.text((x + 6, y + 3), f'{ordinal + 1:02d}  {label}', fill='#111111', font=font)
            draw.text((x + 6, y + 23), f't={row["capture_sim_time"]:.3f}s; capture_id={row["capture_id"]}', fill='#333333', font=font)
            sheet.paste(Image.fromarray(rgb), (x, y + caption))
            ledger.append({'panel': ordinal + 1, 'label': label, 'source_sensor_row': row,
                'sheet_native_RGB_rectangle_xyxy': [x, y + caption, x + width, y + caption + height]})
        path = OUTPUT / (PREFIX + '_' + condition + '_rgb.png')
        if path.exists():
            raise FileExistsError(path)
        sheet.save(path)
        index['conditions'][condition] = {'sheet': path.name, 'sheet_sha256': file_hash(path),
            'sensor_manifest_sha256': file_hash(directory / 'sensor-captures.json'),
            'sensor_seal_sha256': file_hash(directory / 'sensor-seal.json'), 'panels': ledger}
    probe.prior.approach.write(OUTPUT / (PREFIX + '_rgb_sources.json'), index)
    print(json.dumps({'original_RGB_frames_exported': 36, 'new_render_calls': 0,
        'sheets': {condition: row['sheet'] for condition, row in index['conditions'].items()}}))


if __name__ == '__main__':
    produce()
