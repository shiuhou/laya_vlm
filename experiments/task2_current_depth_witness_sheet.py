"""Small post-seal RGB sheet; no geometry computation or source relabeling."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from task2_current_depth_diagnostic import RAW, read, require, sha


def report(directory, output):
    for name, digest in read(directory / 'feature-seal.json').items():
        require(sha(directory / name) == digest, 'numerical artifact seal')
    features = read(directory / 'features.json')
    panel_height = 420
    sheet = Image.new('RGB', (800, 3 * panel_height + 40), 'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 8), 'Full 384 x 384 panels. Red: FWD; yellow: DOWN; blue: LEFT/UP.', fill='black')
    for column, row in enumerate(features['conditions']):
        source = row['source']
        path = RAW / 'task2-closed-empty-scene-run-01' / source['directory'] / source['artifact']
        require(sha(path) == source['artifact_sha256'], 'original RGB source')
        with np.load(path, allow_pickle=False) as saved:
            rgb = saved['rgb']
        with np.load(directory / (row['case_id'] + '-arrays.npz'), allow_pickle=False) as saved:
            xy, inside = saved['pixel_xy'], saved['endpoint_inside']
            mask = saved['projected_proxy_masks'].any(axis=-1)
        panels = [Image.fromarray(rgb)]
        union = np.zeros((384, 384), bool)
        hits = inside.any(axis=(0, 2))
        union[xy[hits, 1], xy[hits, 0]] = True
        raw_overlay = rgb.copy()
        raw_overlay[union] = (.4 * rgb[union] + .6 * np.array([255, 30, 30])).astype(np.uint8)
        panels.append(Image.fromarray(raw_overlay))
        residual = Image.fromarray(rgb)
        boundary = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0)
                            & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
        marked = np.array(residual)
        marked[boundary] = [0, 255, 255]
        residual = Image.fromarray(marked)
        painter = ImageDraw.Draw(residual)
        candidates = row['groups'][1]['all_seven_candidates']
        for token in ('MV_LEFT', 'MV_UP', 'MV_DOWN', 'MV_FWD'):
            color = {'MV_FWD': 'red', 'MV_DOWN': 'yellow'}.get(token, (80, 100, 255))
            for x, y in candidates[token]['witness_pixel_xy']:
                painter.ellipse((x-3, y-3, x+3, y+3), outline=color, width=1)
        panels.append(residual)
        labels = [row['case_id'] + ': original RGB',
                  'All endpoints/current: raw containment union',
                  'Residual witnesses; cyan = existing silhouette']
        for index, panel in enumerate(panels):
            x, y = 8 + column * 400, 40 + index * panel_height
            draw.text((x, y), labels[index], fill='black')
            sheet.paste(panel, (x, y+22))
    sheet.save(output)
    print(json.dumps({'figure': str(output), 'sha256': sha(output), 'size': list(sheet.size)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report(args.source, args.output)
