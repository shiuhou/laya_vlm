"""Aggregate sealed cell containment and overlay every common source pixel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from .records import file_hash

EXPECTED_SEAL = '190a9423fc1d984d011ba9428c122a87a8ef5419b806c52a3f3dc8a4b3c34bd9'
EXPECTED_FRAME = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'
EXPECTED_AUDIT = 'eaf14227c8afb4954370f82be98176e28dc2c2c01832c08b749857bf983b3c46'


def report(source, output, audit):
    source, output = Path(source), Path(output)
    if file_hash(source/'feature-seal.json') != EXPECTED_SEAL:
        raise ValueError('Sealed feature receipt differs')
    seal = json.loads((source/'feature-seal.json').read_text())
    for name, expected in seal.items():
        if file_hash(source/name) != expected:
            raise ValueError('Feature artifact differs: '+name)
    manifest = json.loads((source/'manifest.json').read_text())
    if file_hash(source/'request.json') != manifest['request_sha256']:
        raise ValueError('Sanitized request differs')
    request = json.loads((source/'request.json').read_text())
    result = json.loads((source/'features/result.json').read_text())
    audit = Path(audit)
    if file_hash(audit) != EXPECTED_AUDIT:
        raise ValueError('Independent numerical audit differs')
    independent = json.loads(audit.read_text())
    if independent['status'] != 'PASS' or independent['feature_seal_sha256'] != EXPECTED_SEAL:
        raise ValueError('Matching independent numerical PASS required')
    with np.load(source/'features/containment.npz', allow_pickle=False) as arrays:
        inside, positions = arrays['inside'], arrays['hypothetical_TCP_world_m']
    if inside.dtype != np.bool_ or inside.shape != (9, 1340, 5) or positions.shape != (9, 3):
        raise ValueError('Complete registered tensor required')
    actual_common = np.argwhere(inside[1:].all(axis=0))
    recorded_common = result['same_point_same_proxy_all_eight_corner_witnesses']
    expected = [{'full_support_index': int(point), 'proxy': result['geometry_order'][proxy], **request['full_support'][point]}
                for point, proxy in actual_common]
    if expected != recorded_common:
        raise ValueError('Common pair aggregation differs from complete tensor')
    for index, placement in enumerate(result['placements']):
        if placement['hypothetical_TCP_world_m'] != positions[index].tolist():
            raise ValueError('Placement position differs')
        for column, name in enumerate(result['geometry_order']):
            if placement['per_proxy'][name]['full_support_indices'] != np.flatnonzero(inside[index, :, column]).tolist():
                raise ValueError('Per-point/proxy aggregation differs')
    frame_path = source.parent/'interaction-observability-paired-01/close/0000.npz'
    if file_hash(frame_path) != EXPECTED_FRAME:
        raise ValueError('Original source frame differs')
    with np.load(frame_path, allow_pickle=False) as frame:
        rgb = frame['rgb']
    if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
        raise ValueError('Actual original RGB schema differs')
    output.mkdir(exist_ok=True, parents=True)
    Image.fromarray(rgb).save(output/'task2_point_goal_cell_source_rgb.png')
    overlay = rgb.copy()
    pixels = sorted({tuple(w['pixel_xy']) for w in recorded_common})
    for x, y in pixels:
        overlay[y, x] = [255, 0, 190]
    if int(np.any(overlay != rgb, axis=2).sum()) != len(pixels):
        raise ValueError('Overlay must change exactly the common source pixels')
    Image.fromarray(overlay).save(output/'task2_point_goal_cell_common_pixels.png')
    if not np.array_equal(np.asarray(Image.open(output/'task2_point_goal_cell_source_rgb.png')), rgb):
        raise ValueError('Unmarked RGB encoding changed source values')
    shutil.copyfile(source/'features/containment.npz', output/'task2_point_goal_cell_containment.npz')
    summary = {'producer_commit': manifest['code']['commit'], 'raw_directory': str(source),
        'feature_seal_sha256': EXPECTED_SEAL, 'feature_sha256': seal,
        'request_sha256': manifest['request_sha256'], 'protocol_sha256': manifest['protocol_sha256'],
        'review_sha256': manifest['review_sha256'], 'sources_sha256': manifest['sources_sha256'],
        'terminal_endpoint_record_id': manifest['terminal_endpoint_record_id'],
        'terminal_own_packet': result['terminal_own_packet'], 'exact_own_sample_time_s': None,
        'point_P_world_m': result['point_P_world_m'], 'nominal_step_m': result['nominal_step_m'],
        'axis_stop_cell_half_width_m': result['axis_stop_cell_half_width_m'],
        'geometry_order': result['geometry_order'], 'tensor_shape': list(inside.shape),
        'exact_P_any_containment': result['exact_P_any_containment'],
        'all_eight_corner_unions_positive': result['all_eight_corner_unions_positive'],
        'same_point_same_proxy_common_count': len(recorded_common),
        'same_point_same_proxy_common_witnesses': recorded_common,
        'registered_conditional_whole_cell_certificate': result['entire_axis_stop_cell_excluded_at_fixed_orientation_jaws'],
        'placements': [{k: value for k, value in placement.items() if k not in ('mount', 'proxy_vertices_world_m')}
                       for placement in result['placements']],
        'source_RGB': {'source_npz': str(frame_path), 'source_npz_sha256': EXPECTED_FRAME,
            'unmarked_rgb_values_exact': True, 'common_overlay_unique_pixels': len(pixels),
            'only_changed_pixels_are_all_common_source_pixels': True,
            'artifacts': {name: file_hash(output/name) for name in ('task2_point_goal_cell_source_rgb.png',
                                                                   'task2_point_goal_cell_common_pixels.png')}},
        'containment_artifact': 'task2_point_goal_cell_containment.npz',
        'containment_artifact_sha256': file_hash(output/'task2_point_goal_cell_containment.npz'),
        'halfspace_numeric_tolerance': result['halfspace_numeric_tolerance'],
        'independent_audit': {'sha256': EXPECTED_AUDIT, 'commit': 'b60bf3e', **independent},
        'physical_margin_m': 0., 'physics_or_model_calls': 0,
        'scope': result['scope'], 'convexity_basis': result['convexity_basis']}
    with (output/'task2_point_goal_cell_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'placements': 9, 'common_pairs': len(recorded_common), 'overlay_pixels': len(pixels),
                      'per_placement_counts': [row['contained_point_union_count'] for row in result['placements']]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--audit', required=True)
    args = parser.parse_args()
    report(args.source, args.output, args.audit)
