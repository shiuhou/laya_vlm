"""Package the sealed matched cell calculation without new geometry outcomes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from .records import file_hash

SEAL_SHA = '2e849dd465a93c6f41a72a3bec31ba1ae5a63b2c3f39345db326daf19fe9c0e5'
FRAME_SHA = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'
PREFIX = 'task2_point_anchor_goal_cells_'


def read(path):
    return json.loads(Path(path).read_text())


def report(source, output, audit=None):
    source, output = Path(source), Path(output)
    if file_hash(source/'feature-seal.json') != SEAL_SHA:
        raise ValueError('Registered matched calculation seal differs')
    seal = read(source/'feature-seal.json')
    for name, digest in seal.items():
        if file_hash(source/name) != digest:
            raise ValueError('Sealed feature differs: '+name)
    manifest, request, result = [read(source/name) for name in ('manifest.json', 'request.json', 'features/result.json')]
    if file_hash(source/'request.json') != manifest['request_sha256']:
        raise ValueError('Sanitized request changed')
    with np.load(source/'features/containment.npz', allow_pickle=False) as arrays:
        inside, positions = arrays['inside'], arrays['hypothetical_TCP_world_m']
    if inside.shape != (2, 9, 1340, 5) or inside.dtype != np.bool_:
        raise ValueError('Both complete matched tensors required')
    if result['condition_order'] != ['whole', 'neck']:
        raise ValueError('Registered condition order changed')
    complete, common_pixels = [], {}
    for index, condition in enumerate(result['condition_order']):
        detail = read(source/'features'/condition/'result.json')
        with np.load(source/'features'/condition/'containment.npz', allow_pickle=False) as arrays:
            if not np.array_equal(inside[index], arrays['inside']) or not np.array_equal(positions[index], arrays['hypothetical_TCP_world_m']):
                raise ValueError('Combined and individual arrays differ')
        witnesses = [{'full_support_index': int(point), 'proxy': result['geometry_order'][proxy], **request['full_support'][point]}
                     for point, proxy in np.argwhere(inside[index, 1:].all(axis=0))]
        if witnesses != detail['same_point_same_proxy_all_eight_corner_witnesses']:
            raise ValueError('Common pair aggregation differs')
        for row_index, row in enumerate(detail['placements']):
            measured = inside[index, row_index]
            if (row['index'] != row_index or row['hypothetical_TCP_world_m'] != positions[index, row_index].tolist()
                    or row['contained_point_union_count'] != int(measured.any(axis=1).sum())):
                raise ValueError('Complete placement aggregation differs')
            for column, name in enumerate(result['geometry_order']):
                indices = np.flatnonzero(measured[:, column]).tolist()
                if row['per_proxy'][name] != {'contained_point_count': len(indices), 'full_support_indices': indices}:
                    raise ValueError('Per-point/proxy list differs')
        complete.append({**{key: value for key, value in detail.items() if key != 'placements'}, 'condition': condition,
            'placements': [{key: value for key, value in row.items() if key != 'proxy_vertices_world_m'} for row in detail['placements']]})
        common_pixels[condition] = sorted({tuple(row['pixel_xy']) for row in witnesses})
    independent = None
    if audit is not None:
        audit_path, audit_data = Path(audit).resolve(), read(audit)
        expected = {'status': 'PASS', 'producer_commit': manifest['code']['commit'],
            'raw_directory': str(source), 'request_sha256': manifest['request_sha256'],
            'feature_seal_sha256': SEAL_SHA, 'tensor_entries_checked': inside.size,
            'source_admission_audit_sha256': manifest['source_admission_audit_sha256'],
            'source_point_request_sha256': manifest['source_point_request_sha256']}
        if any(audit_data[key] != value for key, value in expected.items()):
            raise ValueError('Independent audit does not bind this complete calculation')
        if [{'condition': row['condition'], 'exact_P_any_containment': row['exact_P_any_containment']} for row in audit_data['conditions']] != [
                {'condition': row['condition'], 'exact_P_any_containment': row['exact_P_any_containment']} for row in result['conditions']]:
            raise ValueError('Audited ordered exact-center outcomes differ')
        independent = {'path': str(audit_path), 'sha256': file_hash(audit_path), 'data': audit_data}
    frame_path = source.parent/'interaction-observability-paired-01/close/0000.npz'
    if file_hash(frame_path) != FRAME_SHA:
        raise ValueError('Original source RGB-D identity differs')
    with np.load(frame_path, allow_pickle=False) as frame:
        rgb = frame['rgb']
    if rgb.shape != (384, 384, 3) or rgb.dtype != np.uint8:
        raise ValueError('Original RGB schema differs')
    output.mkdir(parents=True, exist_ok=False)
    Image.fromarray(rgb).save(output/(PREFIX+'source_rgb.png'))
    if not np.array_equal(np.asarray(Image.open(output/(PREFIX+'source_rgb.png'))), rgb):
        raise ValueError('Unmarked PNG changed RGB values')
    images = {'source_rgb.png': file_hash(output/(PREFIX+'source_rgb.png'))}
    for condition, pixels in common_pixels.items():
        overlay = rgb.copy()
        for x, y in pixels:
            overlay[y, x] = [255, 0, 190]
        ys, xs = np.nonzero(np.any(overlay != rgb, axis=2))
        if sorted(zip(xs.tolist(), ys.tolist())) != pixels:
            raise ValueError('Overlay must change exactly all unique common source pixels')
        name = condition+'_common_pixels.png'
        Image.fromarray(overlay).save(output/(PREFIX+name))
        images[name] = file_hash(output/(PREFIX+name))
    shutil.copyfile(source/'features/containment.npz', output/(PREFIX+'containment.npz'))
    old_path = source.parent/'task2-point-goal-cell-run-01/features/result.json'
    if file_hash(old_path) != manifest['original_BOX_cell_secondary_reference_sha256']['features/result.json']:
        raise ValueError('Sealed secondary original BOX result changed')
    old = read(old_path)
    summary = {'producer_commit': manifest['code']['commit'], 'raw_directory': str(source),
        'feature_seal_sha256': SEAL_SHA, 'feature_sha256': seal, 'request_sha256': manifest['request_sha256'],
        'preflight_sha256': manifest['preflight_sha256'], 'protocol_sha256': manifest['protocol_sha256'],
        'prospective_review_sha256': manifest['review_sha256'],
        'source_admission_audit_sha256': manifest['source_admission_audit_sha256'],
        'source_point_request_sha256': manifest['source_point_request_sha256'],
        'anchor_provenance': manifest['anchor_provenance'], 'result': result, 'complete_conditions': complete,
        'independent_audit': independent,
        'original_BOX_secondary_reference': {'recomputed': False, 'raw_result_sha256': file_hash(old_path),
            'point_P_world_m': old['point_P_world_m'], 'exact_center_contained_union': old['placements'][0]['contained_point_union_count'],
            'corner_union_counts': [row['contained_point_union_count'] for row in old['placements'][1:]],
            'common_same_point_same_proxy_count': len(old['same_point_same_proxy_all_eight_corner_witnesses']),
            'prior_independent_result_review_commit': 'b60bf3e'},
        'source_RGB': {'source_npz': str(frame_path), 'source_npz_sha256': FRAME_SHA,
            'unmarked_rgb_values_exact': True, 'all_common_pixels_only': True,
            'common_overlay_unique_pixels': {key: len(value) for key, value in common_pixels.items()},
            'image_sha256': images},
        'containment_artifact': PREFIX+'containment.npz',
        'containment_artifact_sha256': file_hash(output/(PREFIX+'containment.npz'))}
    with (output/(PREFIX+'summary.json')).open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'placements': 18, 'tensor_entries': inside.size,
                      'common_pixels': summary['source_RGB']['common_overlay_unique_pixels'], 'audit_included': independent is not None}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--audit')
    args = parser.parse_args()
    report(args.source, args.output, args.audit)
