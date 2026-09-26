"""Eight fixed finite-gap target-region corners; sufficient common-pair test."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from . import task2_finite_gap_control as gap_source
from . import task2_observed_surface_sweep as geometry
from .records import code_identity, file_hash
from .robot_only_geometry import forward
from .sensor_gripper_proximity import NUMERIC_TOLERANCE, proxy_distance

ROOT, RAW = geometry.ROOT, geometry.RAW
PROTOCOL = ROOT/'docs/research/task2_finite_gap_target_region_protocol.md'
GAP_RUN = RAW/'task2-finite-gap-control-run-01'
GAP_FILES = {'request.json': '49df0c6413a0161ed0900e5962d6844161089775c369e646baad6372f4f3e8a3',
             'features/result.json': 'dc569f9a564c59faa3686254f6fa726ad304fdcdce37b753a10108e05e821a13',
             'sensor-seal.json': 'af9d221f996c1ad5cefab7cb5a92fcba5b71d258bcf58370d4273d05ebe64d6e'}
GAP_HELPER_SHA = '0302f9d1fc4152ba69ee5d6d88122b432f8b1aea1c5b7902e4263e5e40306648'


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def target_region_corners(point, rotation, lower, upper):
    point, rotation, low, high = [np.asarray(value, float) for value in (point, rotation, lower, upper)]
    if (point.shape != (3,) or low.shape != (3,) or high.shape != (3,) or rotation.shape != (3, 3)
            or not all(np.isfinite(value).all() for value in (point, rotation, low, high))
            or not np.allclose(rotation.T@rotation, np.eye(3), rtol=0, atol=1e-10)
            or not np.isclose(np.linalg.det(rotation), 1., rtol=0, atol=1e-10)
            or np.any(low > high)):
        raise ValueError('Finite proper rigid rotation and nonempty calibrated gap required')
    choices = np.asarray(list(product((0, 1), repeat=3)), dtype=int)
    gap_corners = (1-choices)*low+choices*high
    return point-gap_corners@rotation.T, gap_corners, choices


def common_pairs(inside):
    inside = np.asarray(inside)
    if inside.dtype != np.bool_ or inside.ndim != 3 or inside.shape[0] != 8 or inside.shape[2] != 5 or inside.shape[1] == 0:
        raise ValueError('Boolean8xNx5 tensor with every registered corner required')
    return np.argwhere(inside.all(axis=0))


def prepare():
    if file_hash(Path(gap_source.__file__)) != GAP_HELPER_SHA:
        raise ValueError('Reviewed finite-gap source helper changed')
    for name, expected in GAP_FILES.items():
        if file_hash(GAP_RUN/name) != expected:
            raise ValueError('Sealed finite-gap source changed: '+name)
    source, admission = gap_source.prepare()  # Source/schema only; no new geometry outcomes.
    old_request = json.loads((GAP_RUN/'request.json').read_text())
    if source != old_request:
        raise ValueError('Exact frozen terminal finite-gap request differs')
    old_result = json.loads((GAP_RUN/'features/result.json').read_text())
    request = {key: source[key] for key in ('point_P_world_m', 'own_packet', 'calibration', 'full_support')}
    request['sealed_geometry_reference'] = {key: old_result[key] for key in
        ('finite_gap_lower_site_m', 'finite_gap_upper_site_m', 'calibrated_pad_vertices_site_m', 'mount')}
    return request, {**admission, 'finite_gap_source_sha256': GAP_FILES,
        'finite_gap_helper_sha256': GAP_HELPER_SHA, 'new_target_region_outcomes_computed': False,
        'target_corner_count': 8, 'candidate_or_one_step_score_recomputed': False}


def compute(request, output):
    if (set(request) != {'point_P_world_m', 'own_packet', 'calibration', 'full_support', 'sealed_geometry_reference'}
            or set(request['own_packet']) != geometry.OWN_KEYS
            or request['calibration'] != geometry.subtree(request['calibration'])):
        raise ValueError('Sanitized fixed sensor/own/calibration request required')
    calibration, own, full = request['calibration'], request['own_packet'], request['full_support']
    if any(set(row) != {'pixel_xy', 'depth_m', 'position_world_m'} for row in full):
        raise ValueError('Observed support fields only')
    points = np.asarray([row['position_world_m'] for row in full], float)
    if points.shape != (1340, 3) or not np.isfinite(points).all():
        raise ValueError('All1340finite observed full BOX points required')
    proxies, mount = geometry.place(calibration, own)
    if list(proxies) != geometry.GEOMS:
        raise ValueError('All five separate proxies required')
    local = forward(calibration, dict(zip(('gripper0_finger_joint1', 'gripper0_finger_joint2'), own['robot0_gripper_qpos'])))
    site = local['sites']['gripper0_grip_site']
    origin, local_rotation = np.asarray(site['position_world_m']), np.asarray(site['rotation_world'])
    pads = {name: (np.asarray(local['geometries'][name]['vertices_world_m'])-origin)@local_rotation for name in gap_source.PADS}
    low, high = gap_source.finite_gap(pads)
    actual_geometry = {'finite_gap_lower_site_m': low.tolist(), 'finite_gap_upper_site_m': high.tolist(),
                       'calibrated_pad_vertices_site_m': {name: vertices.tolist() for name, vertices in pads.items()}, 'mount': mount}
    if actual_geometry != request['sealed_geometry_reference']:
        raise ValueError('Original finite-gap geometry must reproduce exactly')
    rotation = np.asarray(mount['returned_site_rotation_world'])
    positions, gap_corners, choices = target_region_corners(request['point_P_world_m'], rotation, low, high)
    point = np.asarray(request['point_P_world_m'])
    residual = float(np.max(np.abs((point-positions)@rotation-gap_corners)))
    if residual > NUMERIC_TOLERANCE:
        raise ValueError('Constructed target corner relation differs numerically')
    output = Path(output)
    output.mkdir(exist_ok=False)
    inside, rows = [], []
    for index, position in enumerate(positions):
        translated = {name: vertices+(position-np.asarray(own['robot0_eef_pos'])) for name, vertices in proxies.items()}
        measured = np.column_stack([proxy_distance(points, vertices)[2] for vertices in translated.values()])
        inside.append(measured)
        rows.append({'index': index, 'gap_endpoint_choices': choices[index].tolist(),
            'gap_corner_site_m': gap_corners[index].tolist(), 'hypothetical_TCP_world_m': position.tolist(),
            'proxy_vertices_world_m': {name: vertices.tolist() for name, vertices in translated.items()},
            'contained_point_union_count': int(measured.any(axis=1).sum()), 'any_containment': bool(measured.any()),
            'per_proxy': {name: {'contained_point_count': int(measured[:, column].sum()),
                                'full_support_indices': np.flatnonzero(measured[:, column]).tolist()}
                          for column, name in enumerate(geometry.GEOMS)}})
    inside = np.stack(inside)
    witnesses = [{'full_support_index': int(point_index), 'proxy': geometry.GEOMS[proxy_index], **full[point_index]}
                 for point_index, proxy_index in common_pairs(inside)]
    np.savez_compressed(output/'containment.npz', inside=inside, hypothetical_TCP_world_m=positions,
                        gap_corners_site_m=gap_corners, endpoint_choices=choices)
    write(output/'result.json', {'geometry': actual_geometry, 'point_P_world_m': point.tolist(),
        'own_packet': own, 'geometry_order': geometry.GEOMS, 'corners': rows, 'tensor_shape': list(inside.shape),
        'unique_target_corner_count': int(len(np.unique(positions, axis=0))),
        'maximum_target_relation_residual_m': residual,
        'all_eight_corner_unions_positive': bool(inside.any(axis=(1, 2)).all()),
        'common_same_point_same_proxy_witnesses': witnesses,
        'certificate': 'entire_target_region_excluded' if witnesses else 'no_common_witness_certificate',
        'negative_certificate_is_inconclusive': not bool(witnesses),
        'region_definition': 'T = P - R*G; exact zero finite-gap-distance target translations at fixed orientation/jaws',
        'not_entire_discrete_rule_STOP_set': True, 'corner_order': 'lexicographic0/1lower/upper choices in site XYZ',
        'halfspace_numeric_tolerance': NUMERIC_TOLERANCE, 'physical_margin_m': 0.,
        'containment_artifact_sha256': file_hash(output/'containment.npz'),
        'no_pose_selected': True, 'no_adaptive_refinement': True, 'one_step_scores_recomputed': False,
        'model_physics_render_calls': 0, 'automatic_extension': False,
        'scope': 'Conditional frozen observed support and separate calibrated convex proxies at this terminal orientation/jaw state; no physical/global impossibility, feasible pose or grasp claim.'})


def preflight(output):
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('Clean protocol/source/tests freeze required')
    _, admission = prepare()
    write(output, {'code': identity, 'protocol_sha256': file_hash(PROTOCOL), 'python': sys.executable, **admission})
    print('PASS: sources only; no target corners or outcomes computed.')


def run(output, receipt, review):
    identity = code_identity()
    previous = json.loads(Path(receipt).read_text())
    if identity['dirty_status'] or previous['code'] != identity or previous['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('Exact clean preflight/freeze required')
    if identity['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('Independent prospective PASS naming exact freeze required')
    request, admission = prepare()
    if any(previous[key] != value for key, value in admission.items()):
        raise ValueError('Source admission changed')
    output = Path(output)
    output.mkdir(exist_ok=False)
    write(output/'request.json', request)
    write(output/'manifest.json', {'code': identity, **admission, 'protocol_sha256': file_hash(PROTOCOL),
        'preflight_sha256': file_hash(receipt), 'request_sha256': file_hash(output/'request.json'), 'review_sha256': file_hash(review)})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'review.md').write_bytes(Path(review).read_bytes())
    try:
        subprocess.run([sys.executable, '-m', __package__+'.task2_finite_gap_target_region', 'worker',
                        '--input', str(output/'request.json'), '--output', str(output/'features')], check=True)
        write(output/'feature-seal.json', {str(path.relative_to(output)): file_hash(path) for path in sorted((output/'features').iterdir())})
        print('Single eight-corner target-region calculation sealed; no pose selected or extension.')
    except BaseException as exc:
        write(output/'failure.json', {'error': str(exc), 'no_retry': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'run', 'worker'))
    for name in ('input', 'preflight', 'review'):
        parser.add_argument('--'+name)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.mode == 'preflight':
        preflight(args.output)
    elif args.mode == 'worker':
        compute(json.loads(Path(args.input).read_text()), args.output)
    else:
        if not args.preflight or not args.review:
            parser.error('run requires --preflight and --review')
        run(args.output, args.preflight, args.review)
