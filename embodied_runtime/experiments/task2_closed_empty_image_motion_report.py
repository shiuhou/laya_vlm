"""Post-seal plots of stored motion and full endpoint RGB; no CLI or new features."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import task2_closed_empty_image_motion as assay
from .records import file_hash, load_records

NATIVE_OK = ('seeded', 'native_status_ok')
DISPLAY_FIELDS = ('artifact', 'artifact_sha256', 'phase', 'after_step', 'control',
                  'source_capture_stream', 'source_capture_seq', 'capture_read_sim_time_s')


def validate_rows(rows, summaries, metadata):
    if (len(rows) != 492*25 or [(r['seed_id'], r['capture_id']) for r in rows]
            != [(s, i) for s in range(492) for i in range(25)]
            or len(summaries) != 25 or len(metadata) != 25):
        raise ValueError('complete ordered 492-by-25 population required')
    for i, summary in enumerate(summaries):
        current = rows[i::25]
        if (summary['capture_id'] != i or summary['denominator'] != 492
                or summary['reference_capture_id'] != 0
                or any(r['image_motion']['reference_capture_id'] != 0 for r in current)
                or any(r[k] != metadata[i][k] for r in current for k in DISPLAY_FIELDS)):
            raise ValueError('stored reference, denominator or RGB/frame binding differs')
        counts = {'native_admitted_count': sum(r['status'] in NATIVE_OK for r in current),
            'native_failure_count': sum(r['status'] == 'native_failure' for r in current),
            'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in current),
            'A_available_count': sum(r['image_motion']['status_A'] == 'available' for r in current),
            'B_available_count': sum(r['image_motion']['status_B'] == 'available' for r in current)}
        if (any(summary[k] != v for k, v in counts.items())
                or sum(counts[k] for k in ('native_admitted_count', 'native_failure_count', 'unknown_after_failure_count')) != 492):
            raise ValueError('native/available status counts differ from retained rows')
        for key in assay.motion.METRICS:
            stats = summary['metrics'][key]
            available = sum(r['image_motion']['metrics'][key] is not None for r in current)
            if stats['count'] != available or stats['missing_count'] != 492-available:
                raise ValueError('stored metric missingness differs from retained rows')


def load_report_inputs(source, expected_seal_sha256):
    source = Path(source)
    if file_hash(source/'sensor-seal.json') != expected_seal_sha256:
        raise ValueError('reviewed extraction seal changed')
    seal = json.loads((source/'sensor-seal.json').read_text())
    if (seal['complete'] is not True or (seal['tracks'], seal['rows']) != (984, 24600)
            or seal['measured_scene_depth_read'] is not False or seal['evaluator_read'] is not False):
        raise ValueError('complete sensor-only extraction required')
    required = {'admission.json', 'binding.json', 'sensor-summary.json', 'present-tracks.jsonl', 'away-tracks.jsonl'}
    if not required <= set(seal['sha256']):
        raise ValueError('complete report source artifacts must be sealed')
    for name, digest in seal['sha256'].items():
        if file_hash(assay.relative(source, name)) != digest:
            raise ValueError('sealed extraction artifact changed')
    journal, errors = load_records(source/'episodes.jsonl')
    if (errors or not journal or journal[-1]['kind'] != 'termination'
            or journal[-1]['data'] != {'reason': 'all_postevent_image_motion_rows_sealed',
                'tracks': 984, 'rows': 24600, 'sensor_seal_sha256': expected_seal_sha256, 'retries': 0}):
        raise ValueError('closed complete extraction journal required')
    admission = json.loads((source/'admission.json').read_text())
    binding = json.loads((source/'binding.json').read_text())
    summary = json.loads((source/'sensor-summary.json').read_text())
    if (admission['binding_sha256'] != file_hash(source/'binding.json') or admission['binding'] != binding
            or summary['reference_capture_id'] != 0 or summary['endpoints'] != assay.ENDPOINTS
            or summary['mechanical_labels_joined'] is not False or summary['holding'] is not None
            or summary['identity_verified'] is not None or set(summary['cells']) != set(assay.ROLES)):
        raise ValueError('sealed binding, endpoint or sensor-only summary contract differs')
    cells = {}
    for role in assay.ROLES:
        with (source/f'{role}-tracks.jsonl').open() as stream:
            rows = [json.loads(line) for line in stream]
        summaries, metadata = summary['cells'][role], admission['captures'][role]
        validate_rows(rows, summaries, metadata)
        cells[role] = {'rows': rows, 'summaries': summaries, 'metadata': metadata}
    return cells, binding


def load_endpoint_rgb(binding, role, metadata):
    directory = assay.relative(binding['source_root'], binding['cells'][role]['directory'])
    images = {}
    for i in assay.ENDPOINTS.values():
        row = metadata[i]
        path = assay.relative(directory, row['artifact'])
        if file_hash(path) != row['artifact_sha256']:
            raise ValueError('bound endpoint RGB archive changed')
        with np.load(path, allow_pickle=False) as archive:
            rgb = archive['rgb'].copy()
        if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
            raise ValueError('native uncropped endpoint RGB required')
        images[i] = rgb
    return images


def curves_figure(cells):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 6, figsize=(24, 9), sharex=True, sharey='col')
    labels = ('A: RGB image-down displacement', 'A: RGB displacement norm',
              'B: RGB minus projected TCP, image-down', 'B: RGB minus projected TCP norm')
    for ri, role in enumerate(assay.ROLES):
        cell = cells[role]
        summaries = cell['summaries']
        times = np.array([r['capture_read_sim_time_s'] for r in cell['metadata']])
        times -= times[0]
        for key, label, style in (('native_admitted_count', 'Native admitted', '-'),
                ('native_failure_count', 'Native failure', '--'), ('unknown_after_failure_count', 'Unknown after failure', ':')):
            axes[ri, 0].plot(times, [r[key] for r in summaries], label=label, linestyle=style, marker='.', markersize=3)
        for branch, color in (('A', 'C0'), ('B', 'C1')):
            available = np.array([r[branch+'_available_count'] for r in summaries])
            axes[ri, 1].plot(times, available, color=color, label=branch+' available', marker='.', markersize=3)
            axes[ri, 1].plot(times, 492-available, color=color, label=branch+' missing', linestyle='--', marker='.', markersize=3)
        for ci in (0, 1):
            axes[ri, ci].set_ylim(-10, 502)
            axes[ri, ci].set_ylabel(role+'; count / 492')
        for ci, key in enumerate(assay.motion.METRICS, start=2):
            stats = [r['metrics'][key] for r in summaries]
            def values(field):
                return [r[field] if r[field] is not None else np.nan for r in stats]
            axes[ri, ci].fill_between(times, values('min'), values('max'), color='gray', alpha=.12)
            axes[ri, ci].fill_between(times, values('q25'), values('q75'), color='C0', alpha=.25)
            axes[ri, ci].plot(times, values('median'), marker='.', markersize=3)
            axes[ri, ci].set_ylabel('Pixels; median / IQR / full range')
            axes[0, ci].set_title(labels[ci-2], fontsize=9)
        for ax in axes[ri]:
            for i in (8, 16):
                ax.axvline(times[i], color='gray', linestyle=':' if i == 8 else '--', linewidth=.8)
            ax.set_xlabel('Read time from post-event reference (s)')
            ax.grid(alpha=.2)
    axes[0, 0].set_title('Complete native population')
    axes[0, 1].set_title('Metric availability and missingness')
    for ci in (0, 1):
        axes[0, ci].legend(fontsize=8, loc='center left')
    fig.suptitle('Fixed post-event image region: all 25 captures and 492 dependent seeds per cell\n'
        'A uses RGB coordinates; B adds saved own TCP + calibration; shared scales per column; no holding inference\n'
        'Dotted line: end of first close. Dashed line: end of second close / prelift.')
    fig.tight_layout(rect=(0, 0, 1, .94))
    return fig, axes


def point_groups(rows):
    groups = {'admitted': [], 'attempted_failure': []}
    counts = {'population': len(rows), 'native_admitted': 0, 'native_failure': 0,
              'unknown_after_failure': 0, 'defined_positions': 0, 'off_image_positions': 0}
    for row in rows:
        status = row['status']
        key = 'native_admitted' if status in NATIVE_OK else 'native_failure' if status == 'native_failure' else 'unknown_after_failure'
        counts[key] += 1
        point = row['point_pixel_index_xy']
        if point is None:
            continue
        point = np.asarray(point, float)
        if point.shape != (2,) or not np.isfinite(point).all():
            raise ValueError('defined stored native positions must be finite XY')
        groups['admitted' if status in NATIVE_OK else 'attempted_failure'].append(point)
        counts['defined_positions'] += 1
        # Viewport count only; off-image coordinates remain in the plotted arrays and raw rows.
        counts['off_image_positions'] += int(not np.all((point >= -.5) & (point <= 383.5)))
    return {key: np.asarray(values).reshape(-1, 2) for key, values in groups.items()}, counts


def endpoints_figure(role, cell, images):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    annotations = {}
    for ci, (label, i) in enumerate(assay.ENDPOINTS.items()):
        rows = cell['rows'][i::25]
        groups, counts = point_groups(rows)
        annotations[label] = {'capture_id': i, **counts,
            'A_available': cell['summaries'][i]['A_available_count'], 'B_available': cell['summaries'][i]['B_available_count']}
        rgb = images[i]
        for ax in axes[:, ci]:
            ax.imshow(rgb, interpolation='nearest', extent=(-.5, 383.5, 383.5, -.5))
            ax.set_xlim(-.5, 383.5)
            ax.set_ylim(383.5, -.5)
            ax.set_ylabel('Image row')
        axes[0, ci].set_title(f'{label}; local capture {i}\nActual full RGB', fontsize=10)
        ax = axes[1, ci]
        ax.set_xlabel('Image column')
        for key, color, marker in (('admitted', 'cyan', '.'), ('attempted_failure', 'orange', 'x')):
            points = groups[key]
            if len(points):
                ax.scatter(points[:, 0], points[:, 1], s=5 if marker == '.' else 15,
                           color=color, marker=marker, linewidths=.7)
        ax.add_patch(Rectangle((211.5, 168.5), 12, 41, fill=False, edgecolor='magenta', linewidth=.8))
        ax.set_title(f"Admitted {counts['native_admitted']}/492; failed {counts['native_failure']}; unknown {counts['unknown_after_failure']}\n"
                     f"Defined {counts['defined_positions']}; outside view {counts['off_image_positions']}; "
                     f"A/B {annotations[label]['A_available']}/{annotations[label]['B_available']}", fontsize=8)
    fig.suptitle(role+': all four fixed endpoints, uncropped RGB above and stored native positions below\n'
        'Cyan: admitted; orange: failed forward attempt; magenta: initial pixel region (not ownership). '
        'No thinning; undefined/off-image positions remain explicit.')
    fig.tight_layout(rect=(0, 0, 1, .92), h_pad=3., w_pad=1.2)
    return fig, axes, annotations


def report(source, expected_seal_sha256):
    """Call only after admitted extraction; consumes stored metrics without recomputation."""
    source = Path(source)
    cells, binding = load_report_inputs(source, expected_seal_sha256)
    target = source/'report'
    target.mkdir(exist_ok=False)
    assay.write_json(target/'report-start.json', {'extraction_sensor_seal_sha256': expected_seal_sha256,
        'closed_extraction_journal_sha256': file_hash(source/'episodes.jsonl'), 'report_source_sha256': file_hash(__file__),
        'new_features_or_tracking': False, 'mechanical_labels_read': False})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    try:
        fig, _ = curves_figure(cells)
        fig.savefig(target/'image-motion-curves.png', dpi=140)
        plt.close(fig)
        endpoints = {}
        for role in assay.ROLES:
            images = load_endpoint_rgb(binding, role, cells[role]['metadata'])
            fig, _, annotations = endpoints_figure(role, cells[role], images)
            fig.savefig(target/f'{role}-endpoint-rgb.png', dpi=140)
            plt.close(fig)
            endpoints[role] = annotations
        assay.write_json(target/'index.json', {'source': str(source.resolve()),
            'source_summary': {'path': '../sensor-summary.json', 'sha256': file_hash(source/'sensor-summary.json')},
            'source_tracks_sha256': {role: file_hash(source/f'{role}-tracks.jsonl') for role in assay.ROLES},
            'reference_capture_id': 0, 'captures_per_cell': 25, 'denominator_per_capture': 492,
            'endpoint_display_counts': endpoints, 'new_features_or_tracking': False, 'mechanical_labels_read': False,
            'actual_source_RGB_visual_inspection': 'pending', 'identity_verified': None, 'holding': None})
    except BaseException as exc:
        assay.write_json(target/'failure.json', {'reason': repr(exc), 'feature_recomputation': False})
        raise
    finally:
        plt.close('all')
        assay.write_json(target/'artifacts.json', {p.name: file_hash(p) for p in sorted(target.iterdir()) if p.is_file()})
    return target
