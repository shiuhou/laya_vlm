"""Plot sealed rows and all-position overlays on saved RGB; no feature recomputation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import task2_point_anchor_retention_transfer as transfer
from .records import file_hash


def main(output):
    output = Path(output)
    seal = json.loads((output/'sensor-seal.json').read_text())
    if not seal['complete'] or (seal['tracks'], seal['rows']) != (1968, 91512):
        raise ValueError('complete sealed four-cell sensor batch required')
    for name, digest in seal['sha256'].items():
        if file_hash(output/name) != digest:
            raise ValueError('sealed sensor output changed: '+name)
    summary = json.loads((output/'sensor-summary.json').read_text())
    prefix = json.loads((output/'prefix-summary.json').read_text())
    target = output/'report'
    target.mkdir(exist_ok=False)
    cells = {}
    overlays = Image.new('RGB', (768, 4*424), 'white')
    overlay_labels = ImageDraw.Draw(overlays)
    overlay_records = {}
    for condition_index, (condition, count) in enumerate(transfer.FRAME_COUNTS.items()):
        with (output/f'{condition}-tracks.jsonl').open() as stream:
            rows = [json.loads(line) for line in stream]
        if [(r['seed_id'], r['capture_id']) for r in rows] != [(s, i) for s in range(492) for i in range(count)]:
            raise ValueError('complete original row order required')
        groups = [rows[i::count] for i in range(count)]
        reference = count-17
        curves = []
        for i, group in enumerate(groups):
            first = group[0]
            ranges = {}
            for key in transfer.base.METRICS:
                values = [r['reference_deltas']['preclose'][key] for r in group
                          if r['reference_deltas']['preclose'] is not None
                          and r['reference_deltas']['preclose'][key] is not None]
                ranges[key] = {'count': len(values), 'missing_count': 492-len(values),
                               'min': min(values) if values else None, 'max': max(values) if values else None}
            curves.append({**summary['cells'][condition][i], 'metric_ranges_m': ranges,
                **{k: first[k] for k in ('phase', 'control', 'source_capture_stream', 'source_capture_seq',
                    'capture_read_sim_time_s', 'tcp_read_sim_time_s', 'cached_geometry_sample_time_s',
                    'exact_observation_sample_time_s', 'own_tcp_world_m')},
                'tcp_delta_from_preclose_m': None if first['reference_deltas']['preclose'] is None
                    else first['reference_deltas']['preclose']['tcp_delta_m']})
        failures = [r for r in rows if r['status'] == 'native_failure']
        cells[condition] = {'curves': curves, 'reference_capture_id': reference,
            'checkpoints': {label: curves[i] for label, i in
                (('initial', 0), ('preclose', reference), ('postclose_or_hold', count-9), ('postlift', count-1))},
            'first_native_failure': min(failures, key=lambda r: (r['capture_id'], r['seed_id'])) if failures else None,
            'native_failure_rows': len(failures), 'total_rows': len(rows)}
        overlay_records[condition] = []
        for column, capture in enumerate((reference, count-1)):
            group = groups[capture]
            source = transfer.SOURCE/condition/group[0]['artifact']
            if file_hash(source) != group[0]['artifact_sha256']:
                raise ValueError('stored RGB source changed')
            with np.load(source, allow_pickle=False) as archive:
                tile = Image.fromarray(archive['rgb'].copy())
            markers = ImageDraw.Draw(tile)
            points = []
            for row in group:
                point = row['point_pixel_index_xy']
                admitted = row['status'] in transfer.base.ACCEPTED
                inside = point is not None and 0 <= point[0] < 384 and 0 <= point[1] < 384
                if point is not None:
                    markers.point(tuple(point), fill='cyan' if admitted else 'orange')
                points.append({k: row[k] for k in ('seed_id', 'seed_pixel_index_xy', 'status',
                    'point_pixel_index_xy', 'sample_pixel_xy', 'depth_status')} | {'point_inside_image': inside})
            label = 'preclose' if column == 0 else 'postlift'
            overlays.paste(tile, (column*384, condition_index*424+40))
            overlay_labels.text((column*384+3, condition_index*424+3),
                f'{condition}: {label} capture {capture}', fill='black')
            overlay_labels.text((column*384+3, condition_index*424+19),
                f'All 492 seeds; {sum(p["point_inside_image"] for p in points)} points inside; cyan=admitted', fill='black')
            overlay_records[condition].append({'capture_id': capture, 'phase': label,
                'source_artifact': str(source), 'source_sha256': file_hash(source),
                'all_seed_records': points, 'original_resolution': [384, 384],
                'raster_annotation': 'PIL point at every saved native float XY; overlapping marks may coincide'})
    overlays.save(target/'all-current-seed-positions.png')
    transfer.base.write_json(target/'all-current-seed-positions.json', overlay_records)
    compact = {'source_path': str(output), 'sensor_seal_sha256': file_hash(output/'sensor-seal.json'),
        'journal_sha256': file_hash(output/'episodes.jsonl'), 'artifacts_sha256': file_hash(output/'artifacts.json'),
        'prefix_agreement': prefix, 'denominator': 492, 'holding': None, 'identity_verified': None,
        'proxy_membership_available': False, 'reference': 'preclose', 'cells': cells,
        'feature_recomputation': False, 'saved_RGB_arrays_read_for_overlays': 8,
        'evaluator_model_physics_render_calls': 0}
    transfer.base.write_json(target/'portable-summary.json', compact)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, 5, figsize=(23, 13), sharey='col')
    labels = ('Point vertical displacement', 'Point displacement norm',
              'Point minus TCP vertical displacement', 'Point minus TCP displacement norm')
    for row_index, (condition, cell) in enumerate(cells.items()):
        curves, reference = cell['curves'], cell['reference_capture_id']
        times = np.array([r['capture_read_sim_time_s'] for r in curves])
        times -= times[reference]
        for key, label, style in (('native_surviving_count', 'Native status admitted', '-'),
                ('valid_surface_count', 'Valid sampled depth', '--'),
                ('native_failure_count', 'Native failure', ':'),
                ('unknown_after_failure_count', 'Unknown after failure', '-.')):
            axes[row_index, 0].plot(times, [r[key] for r in curves], label=label, linestyle=style)
        axes[row_index, 0].set_ylim(-10, 510)
        axes[row_index, 0].set_ylabel(condition+'\nCount / 492')
        for column, key in enumerate(transfer.base.METRICS, start=1):
            metrics = [r['references']['preclose']['metrics'][key] for r in curves[reference:]]
            def values(field):
                return [r[field]*1000 if r[field] is not None else np.nan for r in metrics]
            axes[row_index, column].plot(times[reference:], values('median'), marker='.', markersize=3)
            axes[row_index, column].fill_between(times[reference:], values('q25'), values('q75'), alpha=.2)
            axes[row_index, column].set_ylabel('mm; median and IQR')
            axes[0, column].set_title(labels[column-1], fontsize=10)
        for ax in axes[row_index]:
            ax.axvline(0., color='gray', linestyle=':')
            ax.axvline(times[-9], color='gray', linestyle='--')
            ax.set_xlabel('Read time from preclose (s)')
            ax.grid(alpha=.2)
    axes[0, 0].set_title('All captures: complete fixed population')
    axes[0, 0].legend(fontsize=7, loc='center left')
    fig.suptitle('Fixed POINT-anchor 2×2: descriptive sensor curves; 492 dependent seeds per cell\n'
                 'Shared scale per column; dotted = preclose, dashed = end close/hold; no identity or holding inference')
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(target/'complete-curves.png', dpi=140)
    plt.close(fig)
    transfer.base.write_json(target/'artifacts.json', {p.name: file_hash(p) for p in sorted(target.iterdir()) if p.is_file()})
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
