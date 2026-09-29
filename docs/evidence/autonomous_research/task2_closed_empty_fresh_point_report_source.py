"""Display audited native returns; no model, parser rerun, depth or policy."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
RUN = RAW / 'task2-closed-empty-fresh-point-run-01'
OUT = RAW / 'task2-closed-empty-fresh-point-report-01'
AUDIT = Path('/home/junhongli/projects/laya-information-boundary-review/docs/evidence/autonomous_research/task2_closed_empty_fresh_point_independent_audit.json')
AUDIT_SHA = 'dd6e3e1463e2b6a00d9b4e31d6c16164e0dd471b21ea554b301c60f4bd5964d0'
EXIT_SHA = 'a3d807fb4d90a479e35e8cc0e6d6f615af14b0a76e8a25afcfee43773bd846ad'
PREFLIGHT_SHA = '366b576db8398de8c51425f0e45a3cb1e5eda732e1eeefc677e53aeb8586308a'
ORDER = ('present-postevent', 'away-postevent', 'away-prelift', 'present-prelift')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(path, expected):
    if digest(path) != expected:
        raise ValueError('Changed sealed source: ' + str(path))
    return json.loads(Path(path).read_text())


def main():
    audit = checked(AUDIT, AUDIT_SHA)
    completed = checked(RAW / 'task2-closed-empty-fresh-point-run-01-exit.json', EXIT_SHA)
    preflight = checked(RAW / 'task2-closed-empty-fresh-point-preflight-02.json', PREFLIGHT_SHA)
    if (audit['status'] != 'PASS' or audit['model_calls'] != 4 or audit['fresh_processes'] != 4
            or tuple(row['case_id'] for row in audit['conditions']) != ORDER
            or tuple(row['case_id'] for row in completed['conditions']) != ORDER
            or tuple(row['case_id'] for row in preflight['source']['images']) != ORDER
            or digest(RUN / 'episodes.jsonl') != audit['journal_sha256']):
        raise ValueError('Complete audited four-case source required')
    rows, images = [], []
    for case, a, e, source in zip(ORDER, audit['conditions'], completed['conditions'], preflight['source']['images']):
        sensor = checked(RUN / case / 'sensor-result.json', a['sensor_sha256'])
        native_return = checked(RUN / case / 'generation-return.json', a['raw_return_sha256'])
        if (sensor['raw_output'] != native_return['raw_response'] or sensor['raw_output'] != a['raw_output']
                or any(sensor[k] != a[k] for k in ('status', 'reason', 'point')) or sensor['depth_read']):
            raise ValueError('Audited return or admission differs')
        rgb_path = RUN / case / 'rgb-input.npy'
        if digest(rgb_path) != e['sha256']['rgb-input.npy']:
            raise ValueError('Saved model RGB differs')
        rgb = np.load(rgb_path, allow_pickle=False)
        source_path = Path(preflight['source']['source_root']) / source['directory'] / source['artifact']
        if digest(source_path) != source['artifact_sha256']:
            raise ValueError('Original RGB archive differs')
        with np.load(source_path, allow_pickle=False) as archive:
            original_rgb = archive['rgb']  # No depth, calibration, own state or labels decoded.
        if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3) or not np.array_equal(rgb, original_rgb):
            raise ValueError('Full original RGB required')
        if sensor['status'] != 'admitted_rgb_point' and sensor['point'] is not None:
            raise ValueError('Nonadmitted output must have no marker')
        rows.append({'case_id': case, 'source': source, 'rgb_input_sha256': digest(rgb_path),
            'sensor_sha256': a['sensor_sha256'], 'raw_return_sha256': a['raw_return_sha256'],
            'raw_output': sensor['raw_output'], 'status': sensor['status'], 'reason': sensor['reason'],
            'point': sensor['point'], 'generation_audit': sensor['generation_audit'],
            'original_RGB_bytes_exact': True, 'marker_drawn': sensor['status'] == 'admitted_rgb_point'})
        images.append(rgb)
    OUT.mkdir(exist_ok=False)
    sheet = Image.new('RGB', (872, 2012), 'white')
    draw = ImageDraw.Draw(sheet)
    font_root = Path('/usr/share/fonts/truetype/dejavu')
    regular = ImageFont.truetype(str(font_root / 'DejaVuSans.ttf'), 13)
    title = ImageFont.truetype(str(font_root / 'DejaVuSans-Bold.ttf'), 17)
    mono = ImageFont.truetype(str(font_root / 'DejaVuSansMono.ttf'), 10)
    draw.text((24, 14), 'Four cold native POINT returns: two admitted, two malformed', fill='black', font=title)
    draw.text((24, 42), 'Full 384 x 384 RGB at 1:1 pixels. Away images have no salvaged point or box marker.', fill='black', font=regular)
    for i, (row, rgb) in enumerate(zip(rows, images)):
        top = 78 + i * 480
        ga, point = row['generation_audit'], row['point']
        status = 'admitted RGB POINT' if point is not None else 'not admitted: malformed; point=null'
        draw.text((24, top), f'{i+1}. {row["case_id"]} | local {row["source"]["local_suffix_capture_id"]} | {status}', fill='black', font=title)
        draw.text((24, top+26), 'Original full RGB', fill='black', font=regular)
        draw.text((464, top+26), 'Stored admitted POINT ring' if point else 'Full RGB repeated; no admitted marker', fill='black', font=regular)
        for left in (24, 464):
            sheet.paste(Image.fromarray(rgb), (left, top+48))
        if point is not None:
            u, v = point['continuous_xy']
            x, y = 464+u-.5, top+48+v-.5
            draw.ellipse((x-8, y-8, x+8, y+8), outline='black', width=3)
            draw.ellipse((x-6, y-6, x+6, y+6), outline='#ffef00', width=2)
        raw_text = 'Raw: ' + row['raw_output']
        if draw.textbbox((0, 0), raw_text, font=mono)[2] > 824:
            raise ValueError('Raw return text would be clipped')
        draw.text((24, top+440), raw_text, fill='black', font=mono)
        detail = f'EOS=true; {ga["actual_generated_token_count"]}/256 generated tokens; no length limit reached.'
        if point:
            detail += ' Normalized POINT=' + str(point['normalized']) + '.'
        draw.text((24, top+457), detail, fill='black', font=regular)
    figure = OUT / 'four-case-full-rgb.png'
    sheet.save(figure)
    # Check every original display rectangle and each unmarked away copy byte-exactly.
    saved = np.asarray(Image.open(figure))
    for i, (row, rgb) in enumerate(zip(rows, images)):
        y = 78+i*480+48
        if not np.array_equal(saved[y:y+384, 24:408], rgb):
            raise ValueError('Original RGB panel altered')
        if not row['marker_drawn'] and not np.array_equal(saved[y:y+384, 464:848], rgb):
            raise ValueError('Nonadmitted image has an overlay')
    result = {'source_audit_sha256': AUDIT_SHA, 'source_exit_sha256': EXIT_SHA,
        'preflight02_sha256': PREFLIGHT_SHA, 'report_source_sha256': digest(__file__),
        'figure': {'filename': figure.name, 'sha256': digest(figure), 'size_px': list(sheet.size),
                   'full_original_panels': 4, 'full_repeated_panels': 4, 'admitted_markers': 2,
                   'panel_RGB_byte_checks_passed': True, 'cropping_or_resizing': False,
                   'marker_position': 'stored continuous image-edge coordinate; PIL pixel-center offset -0.5'},
        'cases': rows, 'visual_inspection_at_generation': 'pending', 'root_semantic_inspection': 'pending',
        'new_model_calls': 0, 'depth_reads': 0, 'projections': 0, 'policy_evaluations': 0,
        'physics_calls': 0, 'render_calls': 0, 'salvaged_nonadmitted_candidates': 0}
    with (OUT / 'index.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(OUT), 'figure_sha256': digest(figure), 'index_sha256': digest(OUT / 'index.json')}))


if __name__ == '__main__':
    main()
