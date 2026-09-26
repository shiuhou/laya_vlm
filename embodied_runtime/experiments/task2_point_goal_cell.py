"""Offline fixed-orientation P/corner containment and same-witness certificate."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy

from . import task2_observed_surface_sweep as geometry
from .records import code_identity, file_hash
from .sensor_gripper_proximity import NUMERIC_TOLERANCE, proxy_distance

ROOT, RAW = geometry.ROOT, geometry.RAW
PROTOCOL = ROOT/'docs/research/task2_point_goal_cell_protocol.md'
SOURCE = RAW/'task2-endpoint-containment-veto-run-01'
SOURCES = {
    'task2-endpoint-containment-veto-run-01/episodes.jsonl': '17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b',
    'task2-endpoint-containment-veto-replay-01/result.json': '341abd1d43e7a7c114cc764cef8506196b7cc8dc1f664d4fdf2f70b602a42def',
    'interaction-observability-paired-01/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
    'task2-box-support-run-02/sensor-representation.json': 'be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead',
    'robot-geometry-observability-03/robot-calibration.json': '11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa',
}
HELPERS = {**{'embodied_runtime/experiments/'+k: v for k, v in geometry.HELPERS.items()},
    'embodied_runtime/experiments/task2_observed_surface_sweep.py': '5d12ce8cf3389746b8e44e3b08b34f6cc2475ae5ac5e0d134476594c440b3e7d',
    'embodied_runtime/decision_interface.py': '92c87afe4b28e90bc50ec25293bb09ca6a93c8d52b598ae465e36d4d54f4c917',
    'embodied_runtime/runtime_core.py': '04be07b6be4d287d9b93e6376fb837cfa1a914eb0f81d9d2cf90b7c7f16763c7'}
STEP_M = .01


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def axis_stop_cell(point, step_m=STEP_M):
    """A ±h axis move improves squared distance iff |P_i-TCP_i| > h/2."""
    point = np.asarray(point, float)
    if point.shape != (3,) or not np.isfinite(point).all() or not np.isfinite(step_m) or step_m <= 0:
        raise ValueError('Finite point and positive nominal step required')
    half = step_m/2
    signs = np.asarray(list(product((-1, 1), repeat=3)), dtype=int)
    return np.vstack((point, point+signs*half)), signs, half


def common_corner_witnesses(inside):
    """Require a single same point/proxy pair at every corner, not union votes."""
    inside = np.asarray(inside)
    if inside.dtype != np.bool_ or inside.ndim != 3 or inside.shape[0] != 9 or inside.shape[2] != 5 or not inside.shape[1]:
        raise ValueError('Boolean9xNx5 per-placement/per-point/per-proxy containment required')
    return np.argwhere(inside[1:].all(axis=0))


def prepare():
    for path, expected in SOURCES.items():
        if file_hash(RAW/path) != expected:
            raise ValueError('Sealed source changed: '+path)
    for path, expected in HELPERS.items():
        if file_hash(ROOT/path) != expected:
            raise ValueError('Existing geometry/rule helper changed: '+path)
    manifest, endpoints, termination = None, [], None
    for line in (SOURCE/'episodes.jsonl').open():
        row = json.loads(line)
        if row['kind'] == 'run_start':
            manifest = row['data']['manifest']
        elif row['kind'] == 'endpoint':
            endpoints.append({'record_id': row['record_id'], **row['data']})
        elif row['kind'] == 'termination':
            termination = row['data']
    if len(endpoints) != 28 or endpoints[-1]['step'] != 27 or termination['last_step'] != 28 or termination['reason'] != 'rule_no_strict_nominal_improvement':
        raise ValueError('Registered completed terminal STOP source required')
    calibration = geometry.subtree(json.loads((RAW/'robot-geometry-observability-03/robot-calibration.json').read_text()))
    sensor = json.loads((RAW/'task2-box-support-run-02/sensor-representation.json').read_text())
    with np.load(RAW/'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as frame:
        full = geometry.support(*(frame[k] for k in ('depth_m', 'intrinsics', 'camera_to_world')), sensor['box_xyxy'])
    if (len(full) != 1340 or sensor['box_xyxy'] != [208, 156, 228, 223]
            or full != manifest['endpoint_guard']['full_support'] or calibration != manifest['endpoint_guard']['calibration']
            or sensor['point_P']['position_world_m'] != manifest['point']['position_world_m']):
        raise ValueError('Exact source full BOX/calibration/P equality required')
    for name, value in (('numpy_version', np.__version__), ('scipy_version', scipy.__version__)):
        if manifest['endpoint_guard']['compatibility'][name] != value:
            raise ValueError('Original numerical library version differs: '+name)
    request = {'calibration': calibration, 'full_support': full,
               'terminal_own_packet': geometry.own_packet(endpoints[-1]['own_observations']),
               'point_P_world_m': manifest['point']['position_world_m'], 'nominal_step_m': STEP_M}
    admission = {'sources_sha256': SOURCES, 'helpers_sha256': HELPERS,
        'terminal_endpoint_record_id': endpoints[-1]['record_id'], 'terminal_step': 27,
        'terminal_capture_seq': endpoints[-1]['capture_seq'], 'exact_own_sample_time_s': None,
        'fixed_orientation_and_jaws': True, 'world_constructed': False, 'new_model_calls': 0,
        'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
        'source_pose_used_only_for_orientation_and_jaws': True, 'geometry_outcomes_computed': False}
    return request, admission


def compute(request, output):
    expected = {'calibration', 'full_support', 'terminal_own_packet', 'point_P_world_m', 'nominal_step_m'}
    if set(request) != expected or set(request['terminal_own_packet']) != geometry.OWN_KEYS or request['nominal_step_m'] != STEP_M:
        raise ValueError('Sanitized fixed source/own-only request required')
    calibration, full, own = request['calibration'], request['full_support'], request['terminal_own_packet']
    if calibration != geometry.subtree(calibration) or any(set(row) != {'pixel_xy', 'depth_m', 'position_world_m'} for row in full):
        raise ValueError('Only normalized own geometry and observed support admitted')
    points = np.asarray([row['position_world_m'] for row in full], float)
    if points.shape != (1340, 3) or not np.isfinite(points).all():
        raise ValueError('All1340finite full BOX points required')
    positions, signs, half = axis_stop_cell(request['point_P_world_m'], request['nominal_step_m'])
    output = Path(output)
    output.mkdir(exist_ok=False)
    inside, placements = [], []
    for index, position in enumerate(positions):
        packet = {**own, 'robot0_eef_pos': position.tolist()}
        proxies, mount = geometry.place(calibration, packet)
        if list(proxies) != geometry.GEOMS:
            raise ValueError('Five separate proxy order differs')
        columns = [proxy_distance(points, vertices)[2] for vertices in proxies.values()]
        measured = np.column_stack(columns)
        inside.append(measured)
        placements.append({'index': index, 'kind': 'exact_P' if index == 0 else 'cell_corner',
            'corner_signs': None if index == 0 else signs[index-1].tolist(), 'hypothetical_TCP_world_m': position.tolist(),
            'returned_orientation_and_jaws_unchanged': True, 'mount': mount,
            'proxy_vertices_world_m': {name: vertices.tolist() for name, vertices in proxies.items()},
            'any_containment': bool(measured.any()), 'contained_point_union_count': int(measured.any(axis=1).sum()),
            'per_proxy': {name: {'contained_point_count': int(measured[:, column].sum()),
                                  'full_support_indices': np.flatnonzero(measured[:, column]).tolist()}
                          for column, name in enumerate(geometry.GEOMS)}})
    inside = np.stack(inside)
    common = common_corner_witnesses(inside)
    if any(not inside[0, point, proxy] for point, proxy in common):
        raise ValueError('Corner certificate numerically contradicts the exact-P containment check')
    witnesses = [{'full_support_index': int(point), 'proxy': geometry.GEOMS[proxy], **full[point]}
                 for point, proxy in common]
    np.savez_compressed(output/'containment.npz', inside=inside, hypothetical_TCP_world_m=positions)
    write(output/'result.json', {'placements': placements, 'geometry_order': geometry.GEOMS,
        'array_shape': list(inside.shape), 'containment_artifact': 'containment.npz',
        'containment_artifact_sha256': file_hash(output/'containment.npz'),
        'nominal_step_m': STEP_M, 'axis_stop_cell_half_width_m': half,
        'point_P_world_m': request['point_P_world_m'], 'terminal_own_packet': own,
        'halfspace_numeric_tolerance': NUMERIC_TOLERANCE, 'physical_margin_m': 0.,
        'exact_P_any_containment': bool(inside[0].any()),
        'all_eight_corner_unions_positive': bool(inside[1:].any(axis=(1, 2)).all()),
        'same_point_same_proxy_all_eight_corner_witnesses': witnesses,
        'entire_axis_stop_cell_excluded_at_fixed_orientation_jaws': bool(witnesses),
        'convexity_basis': 'For one fixed observed q and one fixed convex proxy C, admissible TCP translations with q in C+TCP form q-C. This set is convex; containing all8cell corners contains their convex hull.',
        'scope': 'conditional sensor/proxy exclusion under the existing1e-12numeric convention at this fixed terminal orientation/jaw state; no all-orientation/all-horizon impossibility claim',
        'no_pose_search': True, 'no_dynamics': True, 'new_model_calls': 0})


def preflight():
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('Clean committed protocol/source/tests required')
    request, admission = prepare()
    return request, {'code': identity, 'protocol_sha256': file_hash(PROTOCOL), **admission}


def run(output, review):
    request, admission = preflight()
    if not review or admission['code']['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('Independent prospective PASS naming exact freeze required')
    output = Path(output)
    output.mkdir(exist_ok=False)
    write(output/'request.json', request)
    write(output/'manifest.json', {**admission, 'request_sha256': file_hash(output/'request.json'),
                                   'review_sha256': file_hash(review)})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'review.txt').write_bytes(Path(review).read_bytes())
    try:
        subprocess.run([sys.executable, '-m', __package__+'.task2_point_goal_cell', '--worker',
                        '--input', str(output/'request.json'), '--output', str(output/'features')], check=True)
        write(output/'feature-seal.json', {str(path.relative_to(output)): file_hash(path) for path in sorted((output/'features').iterdir())})
        print(json.dumps({'status': 'complete', 'placements': 9, 'physics': False}))
    except BaseException as exc:
        write(output/'failure.json', {'error': str(exc), 'no_retry': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--review')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--input')
    args = parser.parse_args()
    if args.worker:
        compute(json.loads(Path(args.input).read_text()), args.output)
    elif args.preflight:
        _, admission = preflight()
        write(args.output, admission)
        print(json.dumps({'preflight': 'passed', 'world_constructed': False, 'geometry_outcomes_computed': False}))
    else:
        run(args.output, args.review)
