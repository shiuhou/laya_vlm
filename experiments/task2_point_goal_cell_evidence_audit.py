"""Stored-only independent fixed-facet check of the registered nine placements."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(source):
    source = Path(source)
    manifest = json.loads((source / 'manifest.json').read_text())
    assert digest(source / 'request.json') == manifest['request_sha256']
    seal = json.loads((source / 'feature-seal.json').read_text())
    for name, expected in seal.items():
        assert digest(source / name) == expected
    request = json.loads((source / 'request.json').read_text())
    result = json.loads((source / 'features/result.json').read_text())
    points = np.array([p['position_world_m'] for p in request['full_support']])
    with np.load(source / 'features/containment.npz', allow_pickle=False) as data:
        inside = data['inside']
        positions = data['hypothetical_TCP_world_m']
    assert inside.shape == (9, 1340, 5)
    assert np.array_equal(positions[0], request['point_P_world_m'])
    assert result['halfspace_numeric_tolerance'] == 1e-12
    margins = np.empty_like(inside, dtype=float)
    maximum_translation_residual = 0.0
    for proxy, name in enumerate(result['geometry_order']):
        base = np.array(result['placements'][0]['proxy_vertices_world_m'][name])
        planes = ConvexHull(base).equations
        normal_lengths = np.linalg.norm(planes[:, :3], axis=1)
        # One fixed facet system for all nine translations, independent of the
        # producer's separately recomputed hulls / closest-point helper.
        for placement in range(9):
            translation = positions[placement] - positions[0]
            vertices = np.array(result['placements'][placement]['proxy_vertices_world_m'][name])
            error = np.max(np.abs(vertices - (base + translation)))
            maximum_translation_residual = max(maximum_translation_residual, float(error))
            assert error < 1e-14
            plane_values = (points - translation) @ planes[:, :3].T + planes[:, 3]
            actual = (plane_values <= 1e-12).all(axis=1)
            assert np.array_equal(actual, inside[placement, :, proxy])
            assert np.flatnonzero(actual).tolist() == result['placements'][placement]['per_proxy'][name]['full_support_indices']
            margins[placement, :, proxy] = np.min(-plane_values / normal_lengths, axis=1)
    pairs = np.argwhere(inside[1:].all(axis=0))
    saved = [(w['full_support_index'], result['geometry_order'].index(w['proxy']))
             for w in result['same_point_same_proxy_all_eight_corner_witnesses']]
    assert pairs.tolist() == [list(p) for p in saved]
    witnesses = []
    for point, proxy in pairs:
        witnesses.append({
            'full_support_index': int(point), 'proxy': result['geometry_order'][proxy],
            'pixel_xy': request['full_support'][point]['pixel_xy'],
            'minimum_signed_facet_margin_over_eight_corners_m': float(margins[1:, point, proxy].min()),
        })
    common_margins = [w['minimum_signed_facet_margin_over_eight_corners_m'] for w in witnesses]
    return {
        'status': 'PASS', 'source': str(source),
        'producer_commit': manifest['code']['commit'],
        'result_sha256': digest(source / 'features/result.json'),
        'feature_seal_sha256': digest(source / 'feature-seal.json'),
        'all_60300_boolean_entries_recomputed': True,
        'maximum_proxy_translation_residual_m': maximum_translation_residual,
        'contained_point_counts': inside.any(axis=2).sum(axis=1).tolist(),
        'common_same_point_proxy_witness_count': len(witnesses),
        'all_witnesses_strictly_inside_without_tolerance': all(m > 0 for m in common_margins),
        'minimum_common_witness_facet_margin_m': min(common_margins, default=None),
        'maximum_common_witness_facet_margin_m': max(common_margins, default=None),
        'common_witnesses': witnesses,
        'scope': 'Fixed terminal orientation/jaws, frozen partial observed support and calibrated convex proxies only; no physical or global reachability claim.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.source)
    with Path(args.output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'common_witnesses'}))
