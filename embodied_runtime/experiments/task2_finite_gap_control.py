"""One offline P-to-finite-gap decision intervention at a frozen terminal packet."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy

from . import task2_observed_surface_sweep as geometry
from .records import code_identity, file_hash
from .robot_only_geometry import forward

ROOT, RAW = geometry.ROOT, geometry.RAW
SOURCE = RAW/'task2-endpoint-containment-veto-run-01'
PROTOCOL = ROOT/'docs/research/task2_finite_gap_control_protocol.md'
SOURCES = {
    'manifest.json': '5b46de6585fa9940ec8c32cd3a3a61ba704177398d50d7dd4821a135200924ad',
    'episodes.jsonl': '17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b',
}
DECISION_ID = '17565b0bdbef779d6a2b5d3d9d90a9bb70922cf0d28d1080425bd0187360aa08'
HELPERS = {**geometry.HELPERS,
    'task2_observed_surface_sweep.py': '5d12ce8cf3389746b8e44e3b08b34f6cc2475ae5ac5e0d134476594c440b3e7d',
    'task2_endpoint_containment_veto.py': 'a61ce7c1bbf15c317dcfd50b939765d0c121254c95ae9badb3ee70fa08ec35a6'}
PADS = ('gripper0_finger1_pad_collision', 'gripper0_finger2_pad_collision')


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def prepare():
    for name, digest in SOURCES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('sealed source changed: '+name)
    for name, digest in HELPERS.items():
        if file_hash(Path(__file__).with_name(name)) != digest:
            raise ValueError('frozen helper changed: '+name)
    manifest = json.loads((SOURCE/'manifest.json').read_text())
    selected, terminal = [], []
    for line in (SOURCE/'episodes.jsonl').open():
        row = json.loads(line)
        if row['kind'] == 'decision' and row['data']['step'] == 28:
            selected.append(row)
        elif row['kind'] == 'termination':
            terminal.append(row['data'])
    if (len(selected) != 1 or selected[0]['record_id'] != DECISION_ID or len(terminal) != 1
            or terminal[0]['last_step'] != 28 or terminal[0]['reason'] != 'rule_no_strict_nominal_improvement'):
        raise ValueError('exact completed terminal decision required')
    row = selected[0]['data']
    original = row['experiment_selection']
    guard = manifest['endpoint_guard']
    if row['selected'] != 'STOP' or original['STOP_semantics'] != 'termination_before_execute':
        raise ValueError('original decision must be terminal STOP without hold')
    tokens = [c['token'] for c in row['canonical']['candidates']]
    if tokens != list(geometry.MOVES) or list(original['all_seven_candidates']) != tokens:
        # Journal JSON sorts object keys; compare the set, preserve canonical order below.
        if tokens != list(geometry.MOVES) or set(original['all_seven_candidates']) != set(tokens):
            raise ValueError('original seven candidates differ')
    if any(original['all_seven_candidates'][t]['nominal_delta_m'] != geometry.MOVES[t] for t in tokens):
        raise ValueError('original nominal translations differ')
    if any(c['feasible'] is not True for c in row['canonical']['candidates']):
        raise ValueError('original canonical feasibility differs')
    point, own = manifest['point']['position_world_m'], original['own_packet']
    fields = row['canonical']['state']['fields']
    if (set(own) != geometry.OWN_KEYS or point != fields['target.position_m']['value']
            or own['robot0_eef_pos'] != fields['robot.tcp_position_m']['value']
            or manifest['point']['box_xyxy'] != [208, 156, 228, 223]
            or len(guard['full_support']) != 1340):
        raise ValueError('P, full support or terminal own packet differs')
    if guard['calibration'] != geometry.subtree(guard['calibration']):
        raise ValueError('only fixed own gripper subtree admitted')
    for name, value in (('numpy_version', np.__version__), ('scipy_version', scipy.__version__)):
        if guard['compatibility'][name] != value:
            raise ValueError('source numerical library differs: '+name)
    request = {'point_P_world_m': point, 'own_packet': own, 'calibration': guard['calibration'],
        'full_support': guard['full_support'], 'candidate_order': tokens,
        'original_selected': row['selected'], 'original_current_P_distance_m': row['live_tcp_to_fixed_proxy_m'],
        'original_candidates': {t: original['all_seven_candidates'][t] for t in tokens},
        'original_mount': original['mount'],
        'original_proxy_vertices_world_m': original['current_proxy_vertices_world_m']}
    admission = {'source_sha256': SOURCES, 'helper_sha256': HELPERS, 'source_decision_record_id': DECISION_ID,
        'source_decision_step': 28, 'own_sample_time_s': original['own_sample_time_s'],
        'candidate_order': tokens, 'support_count': 1340, 'original_selected': row['selected'],
        'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
        'new_gap_outcomes_computed': False, 'evaluator_read': False, 'world_constructed': False}
    return request, admission


def finite_gap(pad_vertices_site):
    """Use the existing aligned pad-box faces and finite overlap, no task offset."""
    boxes = [np.asarray(pad_vertices_site[name], float) for name in PADS]
    if any(v.shape != (8, 3) or not np.isfinite(v).all() for v in boxes):
        raise ValueError('two finite calibrated eight-corner pad boxes required')
    low = [v.min(axis=0) for v in boxes]
    high = [v.max(axis=0) for v in boxes]
    lower = np.array([high[0][0], max(low[0][1], low[1][1]), max(low[0][2], low[1][2])])
    upper = np.array([low[1][0], min(high[0][1], high[1][1]), min(high[0][2], high[1][2])])
    if np.any(lower > upper):
        raise ValueError('empty finite open-gap prism; no replacement geometry')
    return lower, upper


def distance_to_gap(point_site, lower, upper):
    point, low, high = map(lambda v: np.asarray(v, float), (point_site, lower, upper))
    if any(v.shape != (3,) or not np.isfinite(v).all() for v in (point, low, high)) or np.any(low > high):
        raise ValueError('finite point and nonempty prism required')
    outside = np.maximum(0., np.maximum(low-point, point-high))
    return float(np.linalg.norm(outside))


def rank(current_distance, candidates, order):
    """Same strict-improvement/min(distance, token) rule and unchanged exclusions."""
    choices = [(candidates[t]['gap_distance_m'], t) for t in order if t != 'STOP' and not candidates[t]['excluded']]
    best = min(choices) if choices else None
    return best[1] if best is not None and best[0] < current_distance else 'STOP'


def compute(request, output):
    expected = {'point_P_world_m', 'own_packet', 'calibration', 'full_support', 'candidate_order',
        'original_selected', 'original_current_P_distance_m', 'original_candidates', 'original_mount',
        'original_proxy_vertices_world_m'}
    if set(request) != expected or set(request['own_packet']) != geometry.OWN_KEYS:
        raise ValueError('sanitized sensor-only request required')
    if request['candidate_order'] != list(geometry.MOVES) or len(request['full_support']) != 1340:
        raise ValueError('same seven candidates and all full support required')
    own, calibration = request['own_packet'], request['calibration']
    proxies, mount = geometry.place(calibration, own)
    if mount != request['original_mount'] or any(proxies[n].tolist() != request['original_proxy_vertices_world_m'][n] for n in geometry.GEOMS):
        raise ValueError('original own geometry placement does not reproduce exactly')
    local = forward(calibration, dict(zip(('gripper0_finger_joint1', 'gripper0_finger_joint2'), own['robot0_gripper_qpos'])))
    site = local['sites']['gripper0_grip_site']
    origin, rotation = np.asarray(site['position_world_m']), np.asarray(site['rotation_world'])
    pad_vertices = {name: (np.asarray(local['geometries'][name]['vertices_world_m'])-origin)@rotation for name in PADS}
    low, high = finite_gap(pad_vertices)
    world_rotation = np.asarray(mount['returned_site_rotation_world'])
    point, tcp = np.asarray(request['point_P_world_m']), np.asarray(own['robot0_eef_pos'])
    point_site = world_rotation.T@(point-tcp)
    current = distance_to_gap(point_site, low, high)
    candidates = {}
    for token in request['candidate_order']:
        delta = np.asarray(geometry.MOVES[token])
        original = copy.deepcopy(request['original_candidates'][token])
        baseline_distance = float(np.linalg.norm(point-tcp-delta))
        if baseline_distance != original['nominal_tcp_to_P_m']:
            raise ValueError('original point-distance effect does not reproduce')
        local_point = world_rotation.T@(point-tcp-delta)
        distance = distance_to_gap(local_point, low, high)
        candidates[token] = {'original_guard_and_P_effect': original, 'excluded': original['excluded'],
            'point_in_site_m': local_point.tolist(), 'gap_distance_m': distance,
            'gap_distance_change_m': distance-current, 'strict_improvement': distance < current,
            'point_in_finite_gap': bool(np.all(local_point >= low) and np.all(local_point <= high))}
    original_choices = [(request['original_candidates'][t]['nominal_tcp_to_P_m'], t)
                        for t in request['candidate_order'] if t != 'STOP' and not candidates[t]['excluded']]
    original_best = min(original_choices) if original_choices else None
    original_selected = original_best[1] if original_best and original_best[0] < request['original_current_P_distance_m'] else 'STOP'
    if original_selected != request['original_selected'] or original_selected != 'STOP':
        raise ValueError('frozen original STOP does not reproduce')
    selected = rank(current, candidates, request['candidate_order'])
    passed = selected != 'STOP' and not candidates[selected]['excluded'] and candidates[selected]['strict_improvement']
    result = {'candidate_order': request['candidate_order'], 'current_gap_distance_m': current,
        'current_point_in_site_m': point_site.tolist(), 'finite_gap_lower_site_m': low.tolist(),
        'finite_gap_upper_site_m': high.tolist(), 'calibrated_pad_vertices_site_m': {k: v.tolist() for k, v in pad_vertices.items()},
        'mount': mount, 'candidates': candidates, 'original_selected': original_selected, 'gap_selected': selected,
        'gate_pass': bool(passed), 'gate_result': 'eligible_strict_improving_move' if passed else 'minimal_relation_change_rejected_at_this_boundary',
        'identity_verified': None, 'extent_established': None, 'holding': None, 'qualified_grasp': None,
        'executed_actions': 0, 'model_physics_render_calls': 0, 'evaluator_read': False,
        'guard_recomputed': False, 'guard_basis': 'exact copied frozen sensor-only endpoint exclusions',
        'automatic_extension': False}
    output = Path(output)
    output.mkdir(exist_ok=False)
    write(output/'result.json', result)


def preflight(output):
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('clean freeze required')
    _, admission = prepare()
    write(output, {'code': identity, 'protocol_sha256': file_hash(PROTOCOL), 'python': sys.executable, **admission})
    print('PASS: source/schema only; no finite-gap outcomes computed.')


def run(output, receipt, review):
    identity = code_identity()
    previous = json.loads(Path(receipt).read_text())
    if identity['dirty_status'] or identity != previous['code'] or previous['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('clean matching freeze/preflight required')
    if identity['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('independent exact-commit prospective PASS required')
    request, admission = prepare()
    if any(previous[k] != v for k, v in admission.items()):
        raise ValueError('source admission changed')
    output = Path(output)
    output.mkdir(exist_ok=False)
    write(output/'request.json', request)
    write(output/'manifest.json', {'code': identity, **admission, 'protocol_sha256': file_hash(PROTOCOL),
        'preflight_sha256': file_hash(receipt), 'request_sha256': file_hash(output/'request.json'), 'review_sha256': file_hash(review)})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'review.md').write_bytes(Path(review).read_bytes())
    try:
        subprocess.run([sys.executable, '-m', __package__+'.task2_finite_gap_control', 'worker',
                        '--input', str(output/'request.json'), '--output', str(output/'features')], check=True)
        write(output/'sensor-seal.json', {'sha256': {'features/result.json': file_hash(output/'features/result.json')},
                                       'evaluator_read': False})
        print('Single offline decision intervention sealed; no automatic extension.')
    except BaseException as exc:
        write(output/'failure.json', {'reason': str(exc), 'retries': 0})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'run', 'worker'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--input')
    parser.add_argument('--preflight')
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.mode == 'worker':
        compute(json.loads(Path(args.input).read_text()), args.output)
    elif args.mode == 'preflight':
        preflight(args.output)
    else:
        if not args.preflight or not args.review:
            parser.error('run requires --preflight and --review')
        run(args.output, args.preflight, args.review)
