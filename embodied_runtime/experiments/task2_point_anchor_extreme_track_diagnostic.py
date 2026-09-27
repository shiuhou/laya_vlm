"""Post-outcome frozen extreme-seed diagnosis from stored outputs and original RGB-D."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import task2_point_anchor_retention_transfer as transfer
from .records import code_identity, file_hash

SOURCE = transfer.OUTPUT
OUTPUT = transfer.base.RAW/'task2-point-anchor-extreme-track-diagnostic-01'
PROTOCOL = transfer.base.ROOT/'docs/research/task2_point_anchor_extreme_track_diagnostic_protocol.md'
HASHES = {
    'sensor-seal.json': '39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60',
    'episodes.jsonl': 'd58bd52625e01a89299cce9581c1d9684ee0467c6a0aaffbd043976147558f4c',
    'whole-close-tracks.jsonl': 'f37c9bd9688175980f0037612b6a5523587b4b207e0f8dd35ded54da032b7010',
    'whole-open_hold-tracks.jsonl': '381847c255d67c65fa34675d14d2e4d82afa1c622dc0ab90296b286900dcd4c5',
    'neck-close-tracks.jsonl': '78e5b4d04697e65cca776266040de2543a3f71cce487822ec189efceb948f8c7',
    'neck-open_hold-tracks.jsonl': '604c025e814aeb7b51a657746863a7a3d3d06d7bc25317fb774e392a806db1a0',
}
AUDIT = transfer.base.RAW/'task2-point-anchor-retention-transfer-independent-audit-01.json'
AUDIT_SHA = 'e188710d477c16ce0bd09d61004293015fe15633c12995abdd9252e9dba21b86'


def select_seed(rows, count):
    if [(r['seed_id'], r['capture_id']) for r in rows] != [(s, i) for s in range(492) for i in range(count)]:
        raise ValueError('complete original four-cell population required')
    final = rows[count-1::count]
    metric = lambda row: None if row['reference_deltas']['preclose'] is None else row['reference_deltas']['preclose']['point_delta_norm_m']
    available = [r for r in final if metric(r) is not None]
    if not available:
        return None, {'selected_seed_id': None, 'unavailable_seed_ids': [r['seed_id'] for r in final]}
    maximum = max(metric(r) for r in available)
    tied = [r['seed_id'] for r in available if metric(r) == maximum]
    selected = min(tied)
    return rows[selected*count:(selected+1)*count], {'selected_seed_id': selected,
        'final_point_delta_norm_m': maximum, 'tied_maximum_seed_ids': tied,
        'available_final_count': len(available), 'unavailable_seed_ids': [r['seed_id'] for r in final if metric(r) is None]}


def describe_changes(rows, reference):
    changes = []
    fields = ('point_pixel_index_xy', 'sample_pixel_xy', 'depth_m')
    for previous, current in zip(rows, rows[1:]):
        a, b = previous['surface_point_world_m'], current['surface_point_world_m']
        changes.append({'previous_capture_id': previous['capture_id'], 'capture_id': current['capture_id'],
            **{key+'_changed': previous[key] != current[key] for key in fields},
            'consecutive_stored_world_distance_m': None if a is None or b is None else float(np.linalg.norm(np.array(b)-a))})
    def events(candidates):
        distances = [r for r in candidates if r['consecutive_stored_world_distance_m'] is not None]
        largest = max(distances, key=lambda r: (r['consecutive_stored_world_distance_m'], -r['capture_id'])) if distances else None
        return {'first_changes': {key: next((r for r in candidates if r[key+'_changed']), None) for key in fields},
                'earliest_largest_consecutive_world_distance': largest}
    return {'adjacent_pairs': changes, 'all_frames': events(changes),
            'after_preclose': events([r for r in changes if r['capture_id'] > reference])}


def neighborhood(array, xy):
    shape = (21, 21)+array.shape[2:]
    result = np.full(shape, np.nan if array.ndim == 2 else 0, dtype=float if array.ndim == 2 else np.uint8)
    if xy is None:
        return result
    x, y = xy
    x0, y0, x1, y1 = max(0, x-10), max(0, y-10), min(array.shape[1], x+11), min(array.shape[0], y+11)
    result[y0-y+10:y1-y+10, x0-x+10:x1-x+10] = array[y0:y1, x0:x1]
    return result


def display(condition, rows, reference, change):
    largest = change['all_frames']['earliest_largest_consecutive_world_distance']
    contexts = [('preclose', reference), ('postclose_or_hold', len(rows)-9), ('postlift', len(rows)-1),
                ('before_largest_jump', None if largest is None else largest['previous_capture_id']),
                ('largest_jump', None if largest is None else largest['capture_id'])]
    loaded, depths, records = [], {}, []
    for label, capture in contexts:
        if capture is None:
            loaded.append(None)
            records.append({'label': label, 'capture_id': None})
            continue
        row = rows[capture]
        path = transfer.SOURCE/condition/row['artifact']
        if file_hash(path) != row['artifact_sha256']:
            raise ValueError('bound original RGB-D source changed')
        with np.load(path, allow_pickle=False) as archive:
            rgb = archive['rgb'].copy()
            depth = neighborhood(archive['depth_m'], row['sample_pixel_xy'])
        loaded.append((rgb, neighborhood(rgb, row['sample_pixel_xy']), depth))
        depths[label] = depth
        records.append({'label': label, 'capture_id': capture, 'artifact': str(path),
            'artifact_sha256': row['artifact_sha256'], 'native_xy': row['point_pixel_index_xy'],
            'sample_pixel_xy': row['sample_pixel_xy'], 'sample_depth_m': row['depth_m'],
            'phase': row['phase'], 'control': row['control']})
    finite = np.concatenate([d[np.isfinite(d)] for d in depths.values()])
    minimum, maximum = (float(finite.min()), float(finite.max())) if len(finite) else (None, None)
    sheet = Image.new('RGB', (5*384, 860), 'white')
    draw = ImageDraw.Draw(sheet)
    from matplotlib import colormaps
    for column, (record, data) in enumerate(zip(records, loaded)):
        offset = column*384
        draw.text((offset+3, 3), f'{condition}; seed {rows[0]["seed_id"]}', fill='black')
        draw.text((offset+3, 19), f'{record["label"]}: capture {record["capture_id"]}', fill='black')
        if data is None:
            draw.text((offset+3, 40), 'Unavailable context', fill='black')
            continue
        rgb, local_rgb, depth = data
        sheet.paste(Image.fromarray(rgb), (offset, 40))
        draw.text((offset+3, 430), f'sample XY {record["sample_pixel_xy"]}; z={record["sample_depth_m"]!r} m', fill='black')
        draw.text((offset+3, 446), '21x21 saved RGB neighborhood; center marked', fill='black')
        local = Image.fromarray(local_rgb).resize((168, 168), Image.Resampling.NEAREST)
        ImageDraw.Draw(local).rectangle((80, 80, 87, 87), outline='orange', width=1)
        sheet.paste(local, (offset+108, 466))
        normalized = (depth-minimum)/(maximum-minimum) if minimum is not None and maximum > minimum else np.zeros_like(depth)
        colors = (colormaps['viridis'](np.nan_to_num(normalized))[:, :, :3]*255).astype(np.uint8)
        colors[~np.isfinite(depth)] = [255, 0, 255]
        local = Image.fromarray(colors).resize((168, 168), Image.Resampling.NEAREST)
        ImageDraw.Draw(local).rectangle((80, 80, 87, 87), outline='orange', width=1)
        sheet.paste(local, (offset+108, 665))
        draw.text((offset+3, 643), f'Depth: shared {minimum:.9g} to {maximum:.9g} m', fill='black')
        draw.text((offset+3, 840), 'Purple=low; yellow=high; magenta=unknown', fill='black')
    sheet.save(OUTPUT/f'{condition}-contexts.png')
    with (OUTPUT/f'{condition}-depth-neighborhoods.npz').open('xb') as stream:
        np.savez_compressed(stream, **depths)
    return {'contexts': records, 'depth_color_range_m': [minimum, maximum], 'neighborhood_size': [21, 21]}


def main():
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('clean committed diagnostic freeze required')
    for name, digest in HASHES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('sealed stored source changed')
    if file_hash(AUDIT) != AUDIT_SHA:
        raise ValueError('independent source audit changed')
    OUTPUT.mkdir(exist_ok=False)
    transfer.base.write_json(OUTPUT/'diagnostic-start.json', {'code': identity,
        'protocol_sha256': file_hash(PROTOCOL), 'source_sha256': HASHES, 'audit_sha256_linkage_only': AUDIT_SHA,
        'post_outcome_exploratory': True, 'new_LK_projection_displacement_estimator_model_physics_render_calls': 0})
    (OUTPUT/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    results = {}
    for condition, count in transfer.FRAME_COUNTS.items():
        with (SOURCE/f'{condition}-tracks.jsonl').open() as stream:
            population = [json.loads(line) for line in stream]
        rows, selection = select_seed(population, count)
        if rows is None:
            results[condition] = {'selection': selection, 'changes': None, 'display': None}
            continue
        reference = count-17
        changes = describe_changes(rows, reference)
        transfer.base.write_json(OUTPUT/f'{condition}-trajectory.json', rows)
        results[condition] = {'selection': selection, 'changes': changes,
            'display': display(condition, rows, reference, changes)}
    transfer.base.write_json(OUTPUT/'diagnostic.json', {'post_outcome_exploratory': True,
        'source_sensor_seal_sha256': HASHES['sensor-seal.json'], 'cells': results,
        'holding': None, 'identity_verified': None, 'reclassified_or_excluded_seeds': 0})
    transfer.base.write_json(OUTPUT/'artifacts.json', {p.name: file_hash(p) for p in sorted(OUTPUT.iterdir()) if p.is_file()})
    print(OUTPUT)


if __name__ == '__main__':
    main()
