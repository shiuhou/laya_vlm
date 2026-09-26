"""Report sealed sweep arrays/summaries without recalculating robot geometry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .records import file_hash


def report(source, output):
    source, output = Path(source), Path(output)
    seal = json.loads((source/'feature-seal.json').read_text())
    for relative, expected in seal.items():
        if file_hash(source/relative) != expected:
            raise ValueError('Sealed numerical artifact changed')
    features = json.loads((source/'features/features.json').read_text())
    request = json.loads((source/'request.json').read_text())
    admission = json.loads((source/'admission.json').read_text())
    manifest = json.loads((source/'manifest.json').read_text())
    if file_hash(source/'request.json') != manifest['request_sha256']:
        raise ValueError('Sanitized inputs changed')
    evaluator = json.loads((source/'evaluator-after-seal.json').read_text())
    table, witnesses, contained = {}, set(), set()
    for label, sample in features['samples'].items():
        table[label] = []
        for token, choice in sample['candidates'].items():
            table[label].append({'token': token,
                **{group: {mode: value['union'] for mode, value in modes.items()}
                   for group, modes in choice['supports'].items()}})
            for modes in choice['supports'].values():
                for parts in modes.values():
                    for part in parts.values():
                        if part['nearest']:
                            witnesses.add(tuple(part['nearest']['pixel_xy']))
            with np.load(source/'features'/choice['artifact'], allow_pickle=False) as archive:
                for mode in ('current', 'endpoint', 'sweep'):
                    for i in np.flatnonzero(archive[mode+'_inside'].any(axis=1)):
                        contained.add(tuple(request['full_support'][i]['pixel_xy']))
    source_frame = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/interaction-observability-paired-01/close/0000.npz')
    if file_hash(source_frame) != admission['source_sha256']['interaction-observability-paired-01/close/0000.npz']:
        raise ValueError('Source RGB/depth changed')
    with np.load(source_frame, allow_pickle=False) as frame:
        rgb, depth = frame['rgb'], frame['depth_m']
    summary = {'raw_directory': str(source), 'producer_commit': manifest['code']['commit'],
        'feature_seal_sha256': file_hash(source/'feature-seal.json'),
        'features_sha256': file_hash(source/'features/features.json'), 'numerical_artifacts': seal,
        'input_sha256': manifest['request_sha256'], 'admission': admission,
        'evaluator': evaluator, 'all_seven_union_results': table,
        'all_distinct_primary_witness_pixels': sorted(witnesses, key=lambda p: (p[1], p[0])),
        'all_distinct_contained_pixels': sorted(contained, key=lambda p: (p[1], p[0])),
        'complete_per_proxy_summaries': features}
    output.mkdir(exist_ok=True, parents=True)
    with (output/'task2_observed_surface_sweep_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(15, 10))
    grid = fig.add_gridspec(2, 4, height_ratios=(1.3, 1.), hspace=.35, wspace=.45)
    ax = fig.add_subplot(grid[0, :2])
    ax.imshow(rgb, extent=(0, rgb.shape[1], rgb.shape[0], 0))
    ax.add_patch(Rectangle((208, 156), 20, 67, fill=False, ec='#00c9ff', lw=1.5))
    ax.set_title('Original initial RGB (0.5 s); full BOX in cyan')
    ax.axis('off')
    for column, values, title in ((2, rgb, 'All distinct primary witnesses on source RGB'),
                                  (3, depth, 'Source depth; white × = contained point')):
        ax = fig.add_subplot(grid[0, column])
        ax.imshow(values, cmap='viridis' if column == 3 else None, interpolation='nearest',
                  extent=(0, values.shape[1], values.shape[0], 0))
        ax.set_xlim(196, 240)
        ax.set_ylim(235, 144)
        ax.add_patch(Rectangle((208, 156), 20, 67, fill=False, ec='#00c9ff', lw=1.7))
        ax.add_patch(Rectangle((212, 169), 12, 41, fill=False, ec='#ffad32', lw=1.7))
        xy = np.asarray(sorted(witnesses))+.5
        ax.scatter(xy[:, 0], xy[:, 1], facecolors='none', edgecolors='magenta', s=22, lw=.8)
        for x, y in sorted(contained):
            ax.scatter(x+.5, y+.5, marker='x', c='white', s=65, linewidth=1.7)
            ax.annotate(f'({x}, {y})', (x+.5, y+.5), xytext=(0, 8), textcoords='offset points',
                        color='white', fontsize=8, ha='center')
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('Pixel x; inner crop in orange')
    for row_index, label in enumerate(('sample0', 'sample1')):
        ax = fig.add_subplot(grid[1, row_index*2:(row_index+1)*2])
        rows = table[label]
        step = admission['selections'][label]['step']
        actual = evaluator[str(step)]['executed']
        x = np.arange(len(rows))
        for offset, group, color in ((-.18, 'inner', '#ed9c31'), (.18, 'full', '#15a6cf')):
            sweep = [r[group]['sweep']['minimum_m']*1000 for r in rows]
            endpoint = [r[group]['endpoint']['minimum_m']*1000 for r in rows]
            ax.bar(x+offset, sweep, width=.34, color=color, label=group+' sweep')
            ax.scatter(x+offset, endpoint, color=color, marker='D', edgecolor='black', linewidth=.5,
                       s=27, label=group+' endpoint')
        labels = [r['token'].removeprefix('MV_')+('\nexecuted' if r['token'] == actual else '') for r in rows]
        ax.set_xticks(x, labels, fontsize=9)
        ax.set_ylim(0, 42)
        ax.set_ylabel('Observed-point to nominal solid minimum (mm)')
        ax.set_title(f'Pre-step {step}: all seven candidates in canonical order')
        ax.grid(axis='y', alpha=.2)
        ax.legend(fontsize=8, ncol=2)
        if label == 'sample1':
            ax.annotate('Full FWD: one contained point', (x[0]+.18, 0), xytext=(.4, 9), fontsize=9,
                        arrowprops={'arrowstyle': '->', 'lw': .8})
    fig.suptitle('Task2 retrospective observed-depth / calibrated-gripper diagnostic\n'
                 'Full BOX adds upper-region support; unexecuted outcomes remain unknown', fontsize=14)
    fig.savefig(output/'task2_observed_surface_sweep_witnesses.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    print(json.dumps({'status': 'reported', 'unique_primary_pixels': len(witnesses),
                      'unique_contained_pixels': len(contained)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report(args.source, args.output)
