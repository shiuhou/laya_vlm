"""Portable sealed eight-corner evidence; no new geometric outcome calculation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from .records import file_hash

EXPECTED_SEAL = 'df260ad8e38988d3c1e6c9159f3f88956023f1f36dcc27237d4d11eab3b05a47'
EXPECTED_FRAME = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'


def report(source, output, audit=None):
    source, output = Path(source), Path(output)
    if file_hash(source/'feature-seal.json') != EXPECTED_SEAL:
        raise ValueError('Registered feature seal differs')
    seal = json.loads((source/'feature-seal.json').read_text())
    for name, expected in seal.items():
        if file_hash(source/name) != expected:
            raise ValueError('Feature artifact differs: '+name)
    manifest = json.loads((source/'manifest.json').read_text())
    request = json.loads((source/'request.json').read_text())
    result = json.loads((source/'features/result.json').read_text())
    if file_hash(source/'request.json') != manifest['request_sha256']:
        raise ValueError('Sanitized request differs')
    with np.load(source/'features/containment.npz', allow_pickle=False) as arrays:
        inside, positions, corners, choices = [arrays[k] for k in
            ('inside', 'hypothetical_TCP_world_m', 'gap_corners_site_m', 'endpoint_choices')]
    if inside.dtype != np.bool_ or inside.shape != (8, 1340, 5):
        raise ValueError('Complete eight-corner tensor required')
    common = np.argwhere(inside.all(axis=0))
    witnesses = [{'full_support_index': int(point), 'proxy': result['geometry_order'][proxy], **request['full_support'][point]}
                 for point, proxy in common]
    if witnesses != result['common_same_point_same_proxy_witnesses']:
        raise ValueError('Same-pair intersection differs')
    for index, row in enumerate(result['corners']):
        if (row['index'] != index or row['hypothetical_TCP_world_m'] != positions[index].tolist()
                or row['gap_corner_site_m'] != corners[index].tolist()
                or row['gap_endpoint_choices'] != choices[index].tolist()
                or row['contained_point_union_count'] != int(inside[index].any(axis=1).sum())):
            raise ValueError('Corner/tensor aggregation differs')
        for column, name in enumerate(result['geometry_order']):
            if row['per_proxy'][name]['full_support_indices'] != np.flatnonzero(inside[index, :, column]).tolist():
                raise ValueError('Per-point/proxy list differs')
    frame_path = source.parent/'interaction-observability-paired-01/close/0000.npz'
    if file_hash(frame_path) != EXPECTED_FRAME:
        raise ValueError('Original actual source frame differs')
    with np.load(frame_path, allow_pickle=False) as frame:
        rgb = frame['rgb']
    if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
        raise ValueError('Original RGB schema differs')
    independent = None
    if audit is not None:
        audit_path = Path(audit).resolve()
        audit_data = json.loads(audit_path.read_text())
        expected_audit = {'status': 'pass', 'freeze': manifest['code']['commit'],
            'feature_seal_sha256': EXPECTED_SEAL, 'result_sha256': seal['features/result.json'],
            'tensor_sha256': seal['features/containment.npz'], 'tensor_entries_checked': inside.size,
            'common_same_pair_count': len(witnesses), 'certificate': result['certificate']}
        if any(audit_data[key] != value for key, value in expected_audit.items()):
            raise ValueError('Independent audit does not match the complete sealed calculation')
        identity = lambda row: (row['full_support_index'], row['proxy'], tuple(row['pixel_xy']))
        if [identity(row) for row in audit_data['common_pair_slacks']] != [identity(row) for row in witnesses]:
            raise ValueError('Independent audit witness identities differ')
        independent = {'path': str(audit_path), 'sha256': file_hash(audit_path), 'data': audit_data}
    output.mkdir(exist_ok=False, parents=True)
    prefix = 'task2_finite_gap_target_region_'
    Image.fromarray(rgb).save(output/(prefix+'source_rgb.png'))
    overlay = rgb.copy()
    pixels = sorted({tuple(w['pixel_xy']) for w in witnesses})
    for x, y in pixels:
        overlay[y, x] = [255, 0, 190]
    if int(np.any(overlay != rgb, axis=2).sum()) != len(pixels):
        raise ValueError('Overlay differs outside complete common source pixel set')
    Image.fromarray(overlay).save(output/(prefix+'common_pixels.png'))
    if not np.array_equal(np.asarray(Image.open(output/(prefix+'source_rgb.png'))), rgb):
        raise ValueError('Unmarked PNG changed source RGB values')
    shutil.copyfile(source/'features/containment.npz', output/(prefix+'containment.npz'))
    summary = {'producer_commit': manifest['code']['commit'], 'raw_directory': str(source),
        'feature_seal_sha256': EXPECTED_SEAL, 'feature_sha256': seal,
        'request_sha256': manifest['request_sha256'], 'protocol_sha256': manifest['protocol_sha256'],
        'review_sha256': manifest['review_sha256'], 'source_sha256': manifest['source_sha256'],
        'finite_gap_source_sha256': manifest['finite_gap_source_sha256'],
        'source_decision_record_id': manifest['source_decision_record_id'],
        'own_packet': result['own_packet'], 'own_sample_time_s': None,
        'point_P_world_m': result['point_P_world_m'], 'geometry': result['geometry'],
        'geometry_order': result['geometry_order'], 'tensor_shape': list(inside.shape),
        'corners': [{key: value for key, value in row.items() if key != 'proxy_vertices_world_m'} for row in result['corners']],
        'unique_target_corner_count': result['unique_target_corner_count'],
        'maximum_target_relation_residual_m': result['maximum_target_relation_residual_m'],
        'all_eight_corner_unions_positive': result['all_eight_corner_unions_positive'],
        'common_same_point_same_proxy_count': len(witnesses), 'common_same_point_same_proxy_witnesses': witnesses,
        'registered_conditional_certificate': result['certificate'], 'independent_audit': independent,
        'region_definition': result['region_definition'], 'corner_order': result['corner_order'],
        'not_entire_discrete_rule_STOP_set': result['not_entire_discrete_rule_STOP_set'], 'scope': result['scope'],
        'halfspace_numeric_tolerance': result['halfspace_numeric_tolerance'], 'physical_margin_m': 0.,
        'no_pose_selected': True, 'one_step_scores_recomputed': False, 'model_physics_render_calls': 0,
        'source_RGB': {'source_npz': str(frame_path), 'source_npz_sha256': EXPECTED_FRAME,
            'unmarked_rgb_values_exact': True, 'common_overlay_unique_pixels': len(pixels),
            'only_changed_pixels_are_all_common_source_pixels': True,
            'artifact_sha256': {prefix+name: file_hash(output/(prefix+name)) for name in ('source_rgb.png', 'common_pixels.png')}},
        'containment_artifact': prefix+'containment.npz',
        'containment_artifact_sha256': file_hash(output/(prefix+'containment.npz'))}
    with (output/(prefix+'summary.json')).open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'corners': len(result['corners']), 'common_pairs': len(witnesses), 'overlay_pixels': len(pixels),
                      'independent_audit_included': independent is not None}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--audit')
    args = parser.parse_args()
    report(args.source, args.output, args.audit)
