"""Stored-result figures and portable summary; never runs a tracker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .records import file_hash
from .task2_box_temporal_probe import ARMS, SOURCE, sealed_tracks, write_json

CAPTURES = (0, 13, 21, 29, 37, 45)


def main(output):
    output = Path(output)
    tracks = sealed_tracks(output)
    sensor = json.loads((output/'sensor-summary.json').read_text())
    proxy = json.loads((output/'evaluation/proxy-membership.json').read_text())
    target = output/'report'
    target.mkdir(exist_ok=False)
    lookup = {arm: {(r['seed_id'], r['capture_id']): r for r in rows} for arm, rows in tracks.items()}
    groups = {arm: {i: [r for r in rows if r['capture_id'] == i] for i in range(46)} for arm, rows in tracks.items()}
    for overlay in (False, True):
        sheet = Image.new('RGB', (384*len(CAPTURES), 408*2), 'white')
        draw = ImageDraw.Draw(sheet)
        for ai, arm in enumerate(ARMS):
            for ci, capture in enumerate(CAPTURES):
                tile = Image.open(SOURCE/f'{arm}/{capture:04d}.png').convert('RGB')
                if overlay:
                    tdraw = ImageDraw.Draw(tile)
                    for r in groups[arm][capture]:
                        if r['sample_pixel_xy'] is not None:
                            x, y = r['sample_pixel_xy']
                            tdraw.point((x, y), fill='cyan')
                sheet.paste(tile, (ci*384, ai*408+24))
                draw.text((ci*384+4, ai*408+5), f'{arm} capture {capture}: '+('all sampled locations' if overlay else 'original RGB'), fill='black')
        sheet.save(target/('all-sample-locations.png' if overlay else 'original-rgb.png'))

    # Complete curves use all registered per-capture summaries, not selected tracks.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
    for ai, arm in enumerate(ARMS):
        summary = sensor['arms'][arm]
        membership = proxy['arms'][arm]['counts']
        times = [groups[arm][i][0]['capture_read_sim_time_s'] for i in range(46)]
        axes[ai, 0].plot(times, [r['native_surviving_count'] for r in summary], label='Native surviving', linewidth=3)
        axes[ai, 0].plot(times, [r['valid_surface_count'] for r in summary], label='Valid depth', linestyle='--')
        axes[ai, 0].plot(times, [r['proxy_true'] for r in membership], label='Bottle-proxy True')
        axes[ai, 0].plot(times, [r['proxy_false'] for r in membership], label='Bottle-proxy False')
        axes[ai, 0].plot(times, [r['proxy_unknown'] for r in membership], label='Proxy unknown', linestyle=':')
        axes[ai, 0].set_ylim(-10, 510)
        axes[ai, 0].set_ylabel(f'{arm}: count / 492')
        for col, key in ((1, 'point_delta_z_m'), (2, 'point_minus_tcp_delta_norm_m')):
            rr = [r['references']['preclose']['metrics'][key] for r in summary[13:]]
            axes[ai, col].plot(times[13:], [r['median']*1000 if r['median'] is not None else np.nan for r in rr])
            axes[ai, col].fill_between(times[13:], [r['q25']*1000 if r['q25'] is not None else np.nan for r in rr],
                                      [r['q75']*1000 if r['q75'] is not None else np.nan for r in rr], alpha=.2)
            axes[ai, col].set_ylabel('mm; median and IQR')
        for ax in axes[ai]:
            ax.axvline(times[13], color='gray', linestyle=':')
            ax.set_xlabel('Capture read time (s)')
            ax.grid(alpha=.2)
    axes[0, 0].set_title('All tracks: survival and limited membership')
    axes[0, 1].set_title('Point vertical displacement from preclose')
    axes[0, 2].set_title('Point–TCP displacement residual norm')
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('One paired trace; dense dependent seeds; membership is not depth ownership')
    fig.tight_layout()
    fig.savefig(target/'complete-curves.png', dpi=140)
    plt.close(fig)

    witnesses = {}
    for arm in ARMS:
        failures = [r for r in tracks[arm] if r['status'] == 'native_failure']
        departures = list(proxy['arms'][arm]['first_observed_departure_after_proxy_true'].values())
        native = min(failures, key=lambda r: (r['capture_id'], r['seed_id'])) if failures else None
        departure = min(departures, key=lambda r: (r['capture_id'], r['seed_id'])) if departures else None
        witnesses[arm] = {'first_native_failure': native, 'first_proxy_departure': departure}
        if departure is None:
            continue
        seed, capture = departure['seed_id'], departure['capture_id']
        selected = range(max(0, capture-1), min(46, capture+2))
        xy = lookup[arm][(seed, capture)]['seed_pixel_index_xy']
        x0, y0 = xy[0]-20, xy[1]-20
        sheet = Image.new('RGB', (320*len(selected), 344*2), 'white')
        draw = ImageDraw.Draw(sheet)
        details = []
        for ci, i in enumerate(selected):
            r = lookup[arm][(seed, i)]
            details.append(r)
            rgb = np.asarray(Image.open(SOURCE/f'{arm}/{i:04d}.png').convert('RGB')).copy()
            path = SOURCE/f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy'
            if file_hash(path) != proxy['mask_sha256'][str(path)]:
                raise ValueError('evaluated mask changed')
            mask = np.load(path, allow_pickle=False)
            for row in (0, 1):
                shown = rgb.copy()
                if row:
                    shown[mask] = (.4*shown[mask]+.6*np.array([0, 255, 0])).astype(np.uint8)
                crop = Image.fromarray(shown).crop((x0, y0, x0+40, y0+40)).resize((320, 320), Image.Resampling.NEAREST)
                marker = ImageDraw.Draw(crop)
                x, y = r['sample_pixel_xy']
                marker.rectangle(((x-x0)*8, (y-y0)*8, (x-x0+1)*8-1, (y-y0+1)*8-1), outline='orange', width=2)
                sheet.paste(crop, (ci*320, row*344+24))
                draw.text((ci*320+3, row*344+5), f'capture {i}, sample {x},{y}; '+('RGB' if row == 0 else 'MASK PROXY'), fill='black')
        sheet.save(target/f'{arm}-first-proxy-departure.png')
        witnesses[arm]['first_proxy_departure_context'] = details
    write_json(target/'first-failures.json', witnesses)
    compact = {'source_path': str(output), 'sensor_seal_sha256': file_hash(output/'sensor-seal.json'),
               'journal_sha256': file_hash(output/'episodes.jsonl'), 'all_native_failures_absent': all(v['first_native_failure'] is None for v in witnesses.values()),
               'arms': {arm: {'sensor_curves': sensor['arms'][arm], 'proxy_counts': proxy['arms'][arm]['counts'],
                             'first_native_failure': witnesses[arm]['first_native_failure'],
                             'first_proxy_departure': witnesses[arm]['first_proxy_departure'],
                             'first_proxy_departure_context': witnesses[arm].get('first_proxy_departure_context'),
                             'seeds_with_observed_departure': len(proxy['arms'][arm]['first_observed_departure_after_proxy_true'])} for arm in ARMS}}
    write_json(target/'portable-summary.json', compact)
    write_json(target/'artifacts.json', {p.name: file_hash(p) for p in target.iterdir() if p.is_file()})
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
