"""Post-seal image-motion report with the already sealed 3D comparison; no new features."""
from __future__ import annotations

import json

import numpy as np

from . import task2_point_anchor_image_motion as motion
from .records import file_hash

EXTREMES = dict(zip(motion.prior.FRAME_COUNTS, (3, 11, 3, 17)))


def main():
    source = motion.OUTPUT
    seal = json.loads((source/'sensor-seal.json').read_text())
    if not seal['complete'] or (seal['tracks'], seal['rows']) != (1968, 91512):
        raise ValueError('complete new sensor seal required before old 3D join')
    for name, digest in seal['sha256'].items():
        if file_hash(source/name) != digest:
            raise ValueError('sealed image-motion source changed')
    target = source/'report'
    target.mkdir(exist_ok=False)
    motion.prior.base.write_json(target/'report-start.json', {'new_sensor_seal_sha256': file_hash(source/'sensor-seal.json'),
        'source_journal_sha256': file_hash(source/'episodes.jsonl'), 'new_features_complete_before_old_3D_read': True,
        'report_code_sha256': file_hash(__file__)})
    if file_hash(motion.SOURCE/'sensor-seal.json') != motion.HASHES['sensor-seal.json']:
        raise ValueError('old 3D source seal changed')
    old_seal = json.loads((motion.SOURCE/'sensor-seal.json').read_text())
    if file_hash(motion.SOURCE/'sensor-summary.json') != old_seal['sha256']['sensor-summary.json']:
        raise ValueError('old 3D summaries changed')
    old = json.loads((motion.SOURCE/'sensor-summary.json').read_text())
    image = json.loads((source/'image-motion-summary.json').read_text())
    cells = {}
    for condition, count in motion.prior.FRAME_COUNTS.items():
        with (source/f'{condition}-features.jsonl').open() as stream:
            rows = [json.loads(line) for line in stream]
        selected = rows[EXTREMES[condition]*count:(EXTREMES[condition]+1)*count]
        old_file = motion.SOURCE/f'{condition}-tracks.jsonl'
        if file_hash(old_file) != motion.HASHES[old_file.name]:
            raise ValueError('old fixed extreme source changed')
        with old_file.open() as stream:
            old_selected = [r for line in stream if (r := json.loads(line))['seed_id'] == EXTREMES[condition]]
        if len(selected) != count or len(old_selected) != count:
            raise ValueError('complete fixed extreme trajectories required')
        joined = []
        for new, stored in zip(selected, old_selected, strict=True):
            if any(new[k] != stored[k] for k in ('seed_id', 'capture_id', *motion.NATIVE_KEYS)):
                raise ValueError('representations must share original native rows')
            joined.append({'seed_id': new['seed_id'], 'capture_id': new['capture_id'],
                'image_motion': new['image_motion'], 'stored_3D_reference_delta': stored['reference_deltas']['preclose']})
        curves = [{**summary, **{k: rows[i][k] for k in ('phase', 'control', 'source_capture_stream',
            'source_capture_seq', 'capture_read_sim_time_s', 'tcp_read_sim_time_s',
            'cached_geometry_sample_time_s', 'exact_observation_sample_time_s')},
            'own_tcp_image_projection': rows[i]['own_tcp_image_projection'],
            'tcp_image_delta_xy_px': rows[i]['image_motion']['tcp_delta_xy_px']}
            for i, summary in enumerate(image['cells'][condition])]
        cells[condition] = {'image_motion_curves': curves, 'stored_3D_curves': old['cells'][condition],
            'reference_capture_id': count-17, 'fixed_exploratory_seed': EXTREMES[condition],
            'fixed_exploratory_trajectory': joined,
            'checkpoints': {label: {'image': curves[i], 'stored_3D': old['cells'][condition][i]}
                for label, i in (('initial', 0), ('preclose', count-17), ('postclose_or_hold', count-9), ('postlift', count-1))}}
    compact = {'source_path': str(source), 'new_sensor_seal_sha256': file_hash(source/'sensor-seal.json'),
        'old_3D_sensor_seal_sha256': motion.HASHES['sensor-seal.json'],
        'old_3D_summary_sha256': old_seal['sha256']['sensor-summary.json'],
        'post_seal_old_3D_join': True, 'feature_recomputation': False,
        'cells': cells, 'identity_verified': None, 'holding': None, 'all_seeds_retained': True}
    motion.prior.base.write_json(target/'portable-comparison.json', compact)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, 5, figsize=(23, 13), sharey='col')
    labels = ('A: RGB image-down displacement', 'A: RGB displacement norm',
              'B: RGB minus projected TCP, image-down', 'B: RGB minus projected TCP norm')
    for ri, (condition, cell) in enumerate(cells.items()):
        curves, reference = cell['image_motion_curves'], cell['reference_capture_id']
        times = np.array([r['capture_read_sim_time_s'] for r in curves])
        times -= times[reference]
        for key, label, style in (('native_admitted_count', 'Native admitted', '-'),
                ('A_available_count', 'A reference available', '--'), ('B_available_count', 'B reference available', ':')):
            axes[ri, 0].plot(times, [r[key] for r in curves], label=label, linestyle=style)
        axes[ri, 0].set_ylim(-10, 510)
        axes[ri, 0].set_ylabel(condition+'\nCount / 492')
        for ci, key in enumerate(motion.METRICS, start=1):
            stats = [r['metrics'][key] for r in curves[reference:]]
            def values(field):
                return [r[field] if r[field] is not None else np.nan for r in stats]
            axes[ri, ci].fill_between(times[reference:], values('min'), values('max'), color='gray', alpha=.12)
            axes[ri, ci].fill_between(times[reference:], values('q25'), values('q75'), color='C0', alpha=.25)
            axes[ri, ci].plot(times[reference:], values('median'), marker='.', markersize=3)
            axes[ri, ci].set_ylabel('Pixels; median / IQR / full range')
            axes[0, ci].set_title(labels[ci-1], fontsize=10)
        for ax in axes[ri]:
            ax.axvline(0., color='gray', linestyle=':')
            ax.axvline(times[-9], color='gray', linestyle='--')
            ax.set_xlabel('Read time from preclose (s)')
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=7, loc='center left')
    axes[0, 0].set_title('Complete fixed population')
    fig.suptitle('Fixed POINT-anchor 2×2: A uses RGB coordinates; B adds own TCP + calibration\n'
        '492 dependent seeds; no sampled scene depth; shared scale per column; no identity/holding inference')
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(target/'image-motion-curves.png', dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(4, 2, figsize=(12, 12), sharey='col')
    for ri, (condition, cell) in enumerate(cells.items()):
        reference = cell['reference_capture_id']
        times = [r['capture_read_sim_time_s']-cell['image_motion_curves'][reference]['capture_read_sim_time_s']
                 for r in cell['image_motion_curves'][reference:]]
        rows = cell['fixed_exploratory_trajectory'][reference:]
        axes[ri, 0].plot(times, [r['image_motion']['metrics']['rgb_delta_norm_px'] for r in rows], marker='.')
        axes[ri, 1].plot(times, [1000*r['stored_3D_reference_delta']['point_delta_norm_m'] for r in rows], marker='.')
        axes[ri, 0].set_ylabel(f'{condition}; seed {cell["fixed_exploratory_seed"]}\nPixels')
        axes[ri, 1].set_ylabel('Millimetres')
        for ax in axes[ri]:
            ax.axvline(times[8], color='gray', linestyle='--')
            ax.set_xlabel('Read time from preclose (s)')
            ax.grid(alpha=.2)
    axes[0, 0].set_title('Native RGB displacement norm')
    axes[0, 1].set_title('Already stored scene-depth 3D displacement norm')
    fig.suptitle('Four previously fixed post-outcome 3D extrema; no new selection or population filtering\n'
                 'Distinct units: compare temporal behavior, not raw numerical amplitude')
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(target/'fixed-extreme-representation-traces.png', dpi=140)
    plt.close(fig)
    motion.prior.base.write_json(target/'artifacts.json', {p.name: file_hash(p) for p in sorted(target.iterdir()) if p.is_file()})
    print(target)


if __name__ == '__main__':
    main()
