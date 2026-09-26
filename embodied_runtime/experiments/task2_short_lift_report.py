"""Report sealed short-lift transfer artifacts; no tracking or sensor recomputation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import task2_short_lift_transfer as transfer
from .records import file_hash


def main(output):
    output = Path(output)
    tracks = transfer.sealed_tracks(output)
    sensor = json.loads((output/'sensor-summary.json').read_text())
    proxy = json.loads((output/'evaluation/proxy-membership.json').read_text())
    target = output/'report'
    target.mkdir(exist_ok=False)
    lookup = {a: {(r['seed_id'], r['capture_id']): r for r in tracks[a]} for a in transfer.base.ARMS}
    groups = {a: {i: [r for r in tracks[a] if r['capture_id'] == i] for i in range(30)} for a in transfer.base.ARMS}
    membership = {a: {(r['seed_id'], r['capture_id']): r['proxy_membership'] for r in proxy['arms'][a]['rows']}
                  for a in transfer.base.ARMS}

    def rgb(arm, capture):
        row = groups[arm][capture][0]
        path = transfer.SOURCE/row['artifact']
        if file_hash(path) != row['artifact_sha256']:
            raise ValueError('source frame changed')
        with np.load(path, allow_pickle=False) as data:
            return data['rgb'].copy()

    for name, captures, overlay in [('original-rgb.png', (0, 13, 21, 29), False),
                                     ('all-sample-locations.png', (0, 13, 21, 29), True),
                                     ('all-lift-original-rgb.png', tuple(range(22, 30)), False)]:
        sheet = Image.new('RGB', (384*len(captures), 408*2), 'white')
        draw = ImageDraw.Draw(sheet)
        for ai, arm in enumerate(transfer.base.ARMS):
            for ci, capture in enumerate(captures):
                tile = Image.fromarray(rgb(arm, capture))
                if overlay:
                    markers = ImageDraw.Draw(tile)
                    for r in groups[arm][capture]:
                        if r['sample_pixel_xy'] is not None:
                            markers.point(tuple(r['sample_pixel_xy']), fill='cyan')
                sheet.paste(tile, (ci*384, ai*408+24))
                draw.text((ci*384+3, ai*408+4), f'{arm}, capture {capture}; '+('all sampled locations' if overlay else 'original RGB'), fill='black')
        sheet.save(target/name)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 5, figsize=(22, 8))
    metric_labels = ['Point vertical displacement', 'Point displacement norm',
                     'Point minus TCP vertical displacement', 'Point minus TCP displacement norm']
    for ai, arm in enumerate(transfer.base.ARMS):
        summaries = sensor['arms'][arm]
        counts = proxy['arms'][arm]['counts']
        times = [groups[arm][i][0]['capture_read_sim_time_s'] for i in range(30)]
        for key, label, style in [('native_surviving_count', 'Native surviving', '-'),
                                   ('valid_surface_count', 'Valid depth', '--')]:
            axes[ai, 0].plot(times, [r[key] for r in summaries], label=label, linestyle=style)
        for key, label in [('proxy_true', 'Proxy True'), ('proxy_false', 'Proxy False'), ('proxy_unknown', 'Proxy unknown')]:
            axes[ai, 0].plot(times, [r[key] for r in counts], label=label)
        axes[ai, 0].set_ylim(-10, 510)
        axes[ai, 0].set_ylabel(f'{arm}: count / 492')
        for col, key in enumerate(transfer.base.METRICS, start=1):
            rr = [r['references']['preclose']['metrics'][key] for r in summaries[13:]]
            def values(field):
                return [r[field]*1000 if r[field] is not None else np.nan for r in rr]
            axes[ai, col].plot(times[13:], values('median'))
            axes[ai, col].fill_between(times[13:], values('q25'), values('q75'), alpha=.2)
            axes[ai, col].set_ylabel('mm; median and IQR')
            axes[0, col].set_title(metric_labels[col-1], fontsize=10)
        for ax in axes[ai]:
            ax.axvline(times[13], color='gray', linestyle=':')
            ax.axvline(times[21], color='gray', linestyle='--')
            ax.set_xlabel('Capture read time (s)')
            ax.grid(alpha=.2)
    axes[0, 0].set_title('All30 captures: counts')
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Archived visual executor 10 mm transfer; preclose-only motion; dense dependent seeds')
    fig.tight_layout()
    fig.savefig(target/'complete-curves.png', dpi=140)
    plt.close(fig)

    witnesses = {}
    for arm in transfer.base.ARMS:
        failures = [r for r in tracks[arm] if r['status'] == 'native_failure']
        firsts = list(proxy['arms'][arm]['first_observed_departure_after_proxy_true'].values())
        lift = [r for r in proxy['arms'][arm]['rows'] if r['capture_id'] >= 22
                and r['proxy_membership'] is False and membership[arm][(r['seed_id'], r['capture_id']-1)] is True]
        def earliest(rows):
            return min(rows, key=lambda r: (r['capture_id'], r['seed_id'])) if rows else None
        witnesses[arm] = {'first_native_failure': earliest(failures),
                          'first_proxy_departure': earliest(firsts),
                          'first_adjacent_lift_proxy_departure': earliest(lift)}
        for label in ('first_proxy_departure', 'first_adjacent_lift_proxy_departure'):
            departure = witnesses[arm][label]
            if departure is None:
                witnesses[arm][label+'_context'] = None
                continue
            seed, capture = departure['seed_id'], departure['capture_id']
            selected = range(max(0, capture-1), min(30, capture+2))
            xy = lookup[arm][(seed, capture)]['seed_pixel_index_xy']
            x0, y0 = xy[0]-20, xy[1]-20
            sheet = Image.new('RGB', (320*len(selected), 344*2), 'white')
            draw = ImageDraw.Draw(sheet)
            details = []
            for ci, i in enumerate(selected):
                r = lookup[arm][(seed, i)]
                details.append(r | {'proxy_membership': membership[arm][(seed, i)]})
                raw = rgb(arm, i)
                path = transfer.SOURCE/f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy'
                if file_hash(path) != proxy['mask_sha256'][str(path)]:
                    raise ValueError('evaluated mask changed')
                mask = np.load(path, allow_pickle=False)
                for layer in (0, 1):
                    shown = raw.copy()
                    if layer:
                        shown[mask] = (.4*shown[mask]+.6*np.array([0, 255, 0])).astype(np.uint8)
                    crop = Image.fromarray(shown).crop((x0, y0, x0+40, y0+40)).resize((320, 320), Image.Resampling.NEAREST)
                    if r['sample_pixel_xy'] is not None:
                        x, y = r['sample_pixel_xy']
                        ImageDraw.Draw(crop).rectangle(((x-x0)*8, (y-y0)*8, (x-x0+1)*8-1, (y-y0+1)*8-1), outline='orange', width=2)
                    sheet.paste(crop, (ci*320, layer*344+24))
                    draw.text((ci*320+3, layer*344+4), f'{arm} seed {seed}, capture {i}; '+('RGB' if layer == 0 else 'MASK PROXY'), fill='black')
            sheet.save(target/f'{arm}-{label}.png')
            witnesses[arm][label+'_context'] = details
    transfer.base.write_json(target/'first-failures.json', witnesses)
    compact = {'source_path': str(output), 'source_archive': str(transfer.SOURCE),
        'sensor_seal_sha256': file_hash(output/'sensor-seal.json'), 'journal_sha256': file_hash(output/'episodes.jsonl'),
        'prefix_agreement': json.loads((output/'prefix-agreement.json').read_text()),
        'initial_own_tcp_world_m': None, 'initial_reference_metrics': None,
        'arms': {arm: {'sensor_curves': sensor['arms'][arm], 'proxy_counts': proxy['arms'][arm]['counts'],
                      **witnesses[arm],
                      'seeds_with_observed_departure': len(proxy['arms'][arm]['first_observed_departure_after_proxy_true']),
                      'preclose_tcp_world_m': lookup[arm][(0, 13)]['own_tcp_world_m'],
                      'final_tcp_world_m': lookup[arm][(0, 29)]['own_tcp_world_m'],
                      'final_tcp_delta_from_preclose_m': lookup[arm][(0, 29)]['reference_deltas']['preclose']['tcp_delta_m']}
                 for arm in transfer.base.ARMS}}
    transfer.base.write_json(target/'portable-summary.json', compact)
    transfer.base.write_json(target/'artifacts.json', {p.name: file_hash(p) for p in target.iterdir() if p.is_file()})
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
