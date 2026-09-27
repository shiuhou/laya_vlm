"""Matched original-rule goal cells for two sealed native POINT anchors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.spatial import ConvexHull

from . import task2_point_goal_cell as cell
from .coarse_point_probe import admit_point
from .records import code_identity, file_hash

ROOT, RAW = cell.ROOT, cell.RAW
PROTOCOL = ROOT/'docs/research/task2_point_anchor_goal_cells_protocol.md'
SOURCE = RAW/'task2-point-region-control-run-01'
CONDITIONS = ('whole', 'neck')
QUERIES = ('the wine bottle', 'the neck of the wine bottle')
SOURCE_FILES = {
    'request.json': '762de6e4a955882fb987988cf561eba36cc5edb9f7dbd6e873e3dcd965db7b9e',
    'episodes.jsonl': '57d9ddcd1348303254d32cf844b0a29e75b90c4eef585a8add4c72afd30b508d',
    'whole/sensor-result.json': '87fb2c2b9587ae1cd08f85d4bf331288c20b4b50b65aa6f0132b78294eb3cef5',
    'neck/sensor-result.json': 'fd6edea327618a8bb86a52dafe48fe2d857a2e71fa7677bdcadb89d65657fd0d',
    'whole/resolved_config.yaml': '73f82530ddc3d3aa376559a36a7e221c23d75a15fef2a68d3bd54c21d1cdae9e',
    'neck/resolved_config.yaml': '622aeed54a0004fda9b2a4d2a4098ebc9d6f6bfc3d6680fe109614468685fb51',
    'whole/generation-return.json': '84a3ac13640b90d7eca42997e0e1cc8749cdcea68ce27026d44d885bc4e2c5e6',
    'neck/generation-return.json': '769b1f87d82636a1b56fa82581e8d805df58e0d7baf79aa5e841521ebc723553',
}
HELPERS = {
    'embodied_runtime/experiments/task2_point_goal_cell.py': 'e5054a7a859f4b8bdc0f8f5e60a37e748b8b8f1f149ad9a456e72eea79f136ab',
    'embodied_runtime/experiments/coarse_point_probe.py': '1448c7a4f4b3c4de02d0938e9951e352ae28437dab3c43885076eb9683914c70',
    'embodied_runtime/vision.py': 'bf428addd6bf1ebc9e6a896ab97dc630c1c16855b61ef1429ef73fcbf93f2b3b',
}
OLD_CELL = RAW/'task2-point-goal-cell-run-01'
OLD_FILES = {
    'request.json': '485e2428b71bcc8fbfb02f6db4cc615bc9da709c3c7dcf79fb96747109a9f3e4',
    'features/result.json': '4ffa028909dff507fb43173e161fc73eff315fe047b0de477bb9cb5432c7f88b',
    'features/containment.npz': '2fafbc642c12b1f623d51c7cef488e4a16abeea6b120f494b8bb7581f420a78a',
    'feature-seal.json': '190a9423fc1d984d011ba9428c122a87a8ef5419b806c52a3f3dc8a4b3c34bd9',
}
SOURCE_AUDIT_SHA = 'c083504fe4574f01a472c4cf957a61ff016055ebc069b4fcb23f752d8bc467d1'


def read(path):
    return json.loads(Path(path).read_text())


def admitted_anchor(sensor, frame):
    audit = sensor['generation_audit']
    if (sensor['status'] != 'admitted_sensor_point' or sensor['reason'] is not None
            or sensor['source_frame_sha256'] != cell.SOURCES['interaction-observability-paired-01/close/0000.npz']
            or sensor['parsed']['status'] != 'single_point' or not audit['complete_generation']
            or not audit['terminal_eos_observed'] or audit['length_limit_reached']
            or any(sensor[key] is not None for key in ('resolved_depth_ownership', 'semantic_confidence', 'grasp_quality'))
            or sensor['semantic_target_identity_verified'] is not False):
        raise ValueError('Sealed completed native POINT admission with explicit unknowns required')
    if admit_point(sensor['parsed'], audit, frame) != sensor['point']:
        raise ValueError('Exact unchanged containing-pixel-center sensor projection differs')
    return sensor['point']['position_world_m']


def prepare(source_audit):
    if file_hash(source_audit) != SOURCE_AUDIT_SHA:
        raise ValueError('Pinned independent POINT source-admission closure required')
    closure = read(source_audit)
    if (closure['status'] != 'pass' or closure['source_admission'] != 'pass'
            or closure['freeze'] != 'd4045496dc330529eb8f637bd46d556fc9bc0598'
            or closure['raw_directory'] != str(SOURCE)
            or closure['source_frame_sha256'] != cell.SOURCES['interaction-observability-paired-01/close/0000.npz']
            or closure['sensor_sha256'] != {name: SOURCE_FILES[name+'/sensor-result.json'] for name in CONDITIONS}
            or [row['condition'] for row in closure['conditions']] != list(CONDITIONS)):
        raise ValueError('Independent admission receipt does not bind both fixed POINT sources')
    for name, digest in SOURCE_FILES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('Sealed native POINT source changed: '+name)
    for name, digest in HELPERS.items():
        if file_hash(ROOT/name) != digest:
            raise ValueError('Unchanged source/goal-cell helper required: '+name)
    for name, digest in OLD_FILES.items():
        if file_hash(OLD_CELL/name) != digest:
            raise ValueError('Sealed original BOX goal-cell reference changed: '+name)
    original, admission = cell.prepare()  # Sources/projection only; never constructs new placements.
    if original != read(OLD_CELL/'request.json'):
        raise ValueError('Original full support/calibration/terminal own source differs')
    with np.load(RAW/'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as frame:
        anchors, provenance = [], []
        for condition, query, audited in zip(CONDITIONS, QUERIES, closure['conditions']):
            config = read(SOURCE/condition/'resolved_config.yaml')
            if (config['condition'] != condition or config['query'] != query
                    or config['question'] != 'Point to: '+query+'.'):
                raise ValueError('Fixed condition/question/source binding differs')
            sensor = read(SOURCE/condition/'sensor-result.json')
            point = admitted_anchor(sensor, frame)
            if (audited['status'] != sensor['status'] or audited['point'] != sensor['point']
                    or audited['sensor_sha256'] != SOURCE_FILES[condition+'/sensor-result.json']):
                raise ValueError('Audited sensor-admission fields differ')
            anchors.append({'condition': condition, 'point_P_world_m': point})
            provenance.append({'condition': condition, 'question': config['question'],
                'sensor_result_sha256': SOURCE_FILES[condition+'/sensor-result.json'],
                'generation_return_sha256': SOURCE_FILES[condition+'/generation-return.json'],
                'point': sensor['point'], 'exact_rgb_sample_time_s': None, 'exact_depth_sample_time_s': None})
    shared = {key: original[key] for key in ('calibration', 'full_support', 'terminal_own_packet', 'nominal_step_m')}
    return {**shared, 'anchors': anchors}, {**admission, 'anchor_source_sha256': SOURCE_FILES,
        'anchor_helper_sha256': HELPERS, 'source_admission_audit_sha256': SOURCE_AUDIT_SHA,
        'source_point_request_sha256': SOURCE_FILES['request.json'],
        'anchor_provenance': provenance, 'condition_order': list(CONDITIONS), 'new_placements': 18,
        'original_BOX_cell_secondary_reference_sha256': OLD_FILES,
        'original_BOX_reference_recomputed': False, 'source_masks_or_visual_receipts_opened': False,
        'new_goal_cell_outcomes_computed': False}


def fixed_facet_check(points, positions, vertices, inside):
    """Check only the same 18 saved translations, with one facet system per solid."""
    points, positions, inside = np.asarray(points, float), np.asarray(positions, float), np.asarray(inside)
    if (points.ndim != 2 or points.shape[1] != 3 or not len(points)
            or positions.shape != (2, 9, 3) or inside.shape != (2, 9, len(points), 5)
            or inside.dtype != np.bool_ or not np.isfinite(points).all() or not np.isfinite(positions).all()):
        raise ValueError('Both complete fixed nine-placement tensors required')
    reference = positions[0, 0]
    checked = np.zeros_like(inside)
    slack = np.empty(inside.shape)
    facets, max_residual = {}, 0.
    for column, name in enumerate(cell.geometry.GEOMS):
        base_vertices = np.asarray(vertices[0][0][name], float)
        equations = ConvexHull(base_vertices).equations
        facets[name] = equations.tolist()
        for anchor in range(2):
            for index in range(9):
                delta = positions[anchor, index]-reference
                moved = np.asarray(vertices[anchor][index][name], float)
                residual = float(np.max(np.abs(moved-(base_vertices+delta))))
                if not np.isfinite(residual) or residual > cell.NUMERIC_TOLERANCE:
                    raise ValueError('Registered placements do not share fixed translated proxy geometry')
                max_residual = max(max_residual, residual)
                signed = -((points-delta)@equations[:, :3].T+equations[:, 3])
                checked[anchor, index, :, column] = np.all(signed >= -cell.NUMERIC_TOLERANCE, axis=1)
                slack[anchor, index, :, column] = signed.min(axis=1)
    if not np.array_equal(checked, inside):
        raise ValueError('Original containment and one fixed facet system disagree')
    per_anchor = []
    for anchor, condition in enumerate(CONDITIONS):
        witnesses = []
        for point, proxy in cell.common_corner_witnesses(inside[anchor]):
            margins = slack[anchor, 1:, point, proxy]
            witnesses.append({'full_support_index': int(point), 'proxy': cell.geometry.GEOMS[proxy],
                'center_minimum_signed_facet_slack_m': float(slack[anchor, 0, point, proxy]),
                'corner_minimum_signed_facet_slacks_m': margins.tolist(),
                'minimum_signed_corner_facet_slack_m': float(margins.min()),
                'strictly_inside_all_corners': bool(np.all(margins > 0.))})
        per_anchor.append({'condition': condition, 'common_pair_checks': witnesses,
            'all_common_pairs_strictly_inside': bool(witnesses) and all(row['strictly_inside_all_corners'] for row in witnesses),
            'minimum_common_pair_corner_slack_m': min((row['minimum_signed_corner_facet_slack_m'] for row in witnesses), default=None),
            'maximum_common_pair_corner_slack_m': max((row['minimum_signed_corner_facet_slack_m'] for row in witnesses), default=None)})
    return {'reference_condition': CONDITIONS[0], 'reference_placement_index': 0,
        'fixed_facet_equations': facets, 'tensor_entries_checked': int(inside.size),
        'fixed_facet_memberships_match_all_entries': True, 'maximum_proxy_translation_residual_m': max_residual,
        'conditions': per_anchor, 'numerical_slack_is_not_physical_margin_or_uncertainty': True}


def compute(request, output):
    if (set(request) != {'calibration', 'full_support', 'terminal_own_packet', 'nominal_step_m', 'anchors'}
            or [row['condition'] for row in request['anchors']] != list(CONDITIONS)
            or any(set(row) != {'condition', 'point_P_world_m'} for row in request['anchors'])):
        raise ValueError('Both fixed anchors and only shared sensor/own inputs required')
    output = Path(output)
    output.mkdir(exist_ok=False)
    results, arrays, positions, vertices = [], [], [], []
    shared = {key: value for key, value in request.items() if key != 'anchors'}
    for anchor in request['anchors']:
        directory = output/anchor['condition']
        cell.compute({**shared, 'point_P_world_m': anchor['point_P_world_m']}, directory)
        result = read(directory/'result.json')
        results.append(result)
        with np.load(directory/'containment.npz', allow_pickle=False) as data:
            arrays.append(data['inside'].copy())
            positions.append(data['hypothetical_TCP_world_m'].copy())
        vertices.append([row['proxy_vertices_world_m'] for row in result['placements']])
    inside, positions = np.stack(arrays), np.stack(positions)
    numeric = fixed_facet_check([row['position_world_m'] for row in shared['full_support']], positions, vertices, inside)
    np.savez_compressed(output/'containment.npz', inside=inside, hypothetical_TCP_world_m=positions)
    rows = []
    for index, condition in enumerate(CONDITIONS):
        result = results[index]
        witnesses = result['same_point_same_proxy_all_eight_corner_witnesses']
        rows.append({'condition': condition, 'point_P_world_m': request['anchors'][index]['point_P_world_m'],
            'exact_center_status': 'contained' if result['exact_P_any_containment'] else 'no_observed_point_containment',
            'exact_P_any_containment': result['exact_P_any_containment'],
            'corner_union_counts': [row['contained_point_union_count'] for row in result['placements'][1:]],
            'all_eight_corner_unions_positive': result['all_eight_corner_unions_positive'],
            'common_same_point_same_proxy_count': len(witnesses),
            'certificate': 'entire_original_rule_goal_cell_excluded' if witnesses else 'no_common_witness_certificate',
            'absence_of_common_witness_is_inconclusive': not bool(witnesses),
            'exact_center_noncontainment_is_not_clearance_or_feasibility': True,
            'complete_result': condition+'/result.json', 'complete_result_sha256': file_hash(output/condition/'result.json')})
    cell.write(output/'result.json', {'condition_order': list(CONDITIONS), 'conditions': rows,
        'tensor_shape': list(inside.shape), 'geometry_order': cell.geometry.GEOMS,
        'nominal_step_m': cell.STEP_M, 'axis_stop_cell_half_width_m': cell.STEP_M/2,
        'corner_order': 'exactP then lexicographic(-1,+1)^3 world-axis signs',
        'terminal_own_packet': request['terminal_own_packet'], 'fixed_facet_numerical_check': numeric,
        'halfspace_numeric_tolerance': cell.NUMERIC_TOLERANCE, 'physical_margin_m': 0.,
        'containment_artifact_sha256': file_hash(output/'containment.npz'),
        'new_placements': 18, 'original_BOX_reference_recomputed': False,
        'new_model_physics_render_calls': 0, 'no_selected_anchor_or_pose': True, 'automatic_extension': False,
        'scope': 'Fixed observed full BOX support and five separate convex own proxies at the prior terminal orientation/jaws; no physical contact, feasible route, clearance, grasp or global impossibility claim.'})


def preflight(output, source_audit):
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('Clean source/protocol/tests freeze required')
    _, admission = prepare(source_audit)
    cell.write(output, {'code': identity, 'protocol_sha256': file_hash(PROTOCOL), 'python': sys.executable, **admission})
    print('PASS: matched source admission only; no new placements or containment outcomes.')


def run(output, preflight_path, review, source_audit):
    identity, receipt = code_identity(), read(preflight_path)
    if identity['dirty_status'] or receipt['code'] != identity or receipt['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('Exact clean source-only preflight required')
    if identity['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('Independent prospective PASS naming this exact freeze required')
    request, admission = prepare(source_audit)
    if any(receipt[key] != value for key, value in admission.items()):
        raise ValueError('Source admission changed after preflight')
    output = Path(output)
    output.mkdir(exist_ok=False)
    cell.write(output/'request.json', request)
    cell.write(output/'manifest.json', {'code': identity, **admission, 'protocol_sha256': file_hash(PROTOCOL),
        'preflight_sha256': file_hash(preflight_path), 'request_sha256': file_hash(output/'request.json'),
        'review_sha256': file_hash(review)})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'review.md').write_bytes(Path(review).read_bytes())
    (output/'source-admission-audit.json').write_bytes(Path(source_audit).read_bytes())
    try:
        subprocess.run([sys.executable, '-m', __package__+'.task2_point_anchor_goal_cells', 'worker',
                        '--input', str(output/'request.json'), '--output', str(output/'features')], check=True)
        cell.write(output/'feature-seal.json', {str(path.relative_to(output)): file_hash(path)
                   for path in sorted((output/'features').rglob('*')) if path.is_file()})
        print('Single matched18-placement calculation sealed; both anchors retained, no extension.')
    except BaseException as exc:
        cell.write(output/'failure.json', {'error': str(exc), 'no_retry': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'run', 'worker'))
    for name in ('source-audit', 'preflight', 'review', 'input'):
        parser.add_argument('--'+name)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.mode == 'worker':
        compute(read(args.input), args.output)
    elif not args.source_audit:
        parser.error('source-admission audit required before preflight/run')
    elif args.mode == 'preflight':
        preflight(args.output, args.source_audit)
    elif not args.preflight or not args.review:
        parser.error('run requires independent prospective review and source-only preflight')
    else:
        run(args.output, args.preflight, args.review, args.source_audit)
