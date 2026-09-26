"""Independent stored finite-gap audit using explicit pad bounds and projection."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from ..runtime_core import MOVE, _sha256_json
from .records import file_hash

RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
RUN = RAW/'task2-finite-gap-control-run-01'
SOURCE = RAW/'task2-endpoint-containment-veto-run-01'
RESULT_SHA = 'dc569f9a564c59faa3686254f6fa726ad304fdcdce37b753a10108e05e821a13'
SEAL_SHA = 'af9d221f996c1ad5cefab7cb5a92fcba5b71d258bcf58370d4273d05ebe64d6e'
SOURCE_SHA = '17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b'


def audit(output):
    if (file_hash(RUN/'features/result.json') != RESULT_SHA or file_hash(RUN/'sensor-seal.json') != SEAL_SHA
            or file_hash(SOURCE/'episodes.jsonl') != SOURCE_SHA):
        raise ValueError('Sealed source/result differs')
    read = lambda path: json.loads(path.read_text())
    manifest, request, result = [read(RUN/name) for name in ('manifest.json', 'request.json', 'features/result.json')]
    if file_hash(RUN/'request.json') != manifest['request_sha256'] or manifest['code']['commit'] != '1fd6324fd35c5e42fe05923b4986ccf6f69e8a7c':
        raise ValueError('Registered producer/request differs')
    previous, selected, count = None, None, 0
    for index, line in enumerate((SOURCE/'episodes.jsonl').open('rb')):
        row = json.loads(line)
        if (not line.endswith(b'\n') or row['seq'] != index or row['previous_record_id'] != previous
                or row['record_id'] != _sha256_json({k: v for k, v in row.items() if k != 'record_id'})):
            raise ValueError('Source chain mismatch')
        previous, count = row['record_id'], count+1
        if row['kind'] == 'decision' and row['data']['step'] == 28:
            if selected is not None or row['record_id'] != manifest['source_decision_record_id']:
                raise ValueError('Ambiguous terminal decision')
            selected = row['data']
        if row['kind'] == 'run_start':
            source_manifest = row['data']['manifest']
    original = selected['experiment_selection']
    own = request['own_packet']
    if (own != original['own_packet'] or request['calibration'] != source_manifest['endpoint_guard']['calibration']
            or request['full_support'] != source_manifest['endpoint_guard']['full_support']
            or request['point_P_world_m'] != source_manifest['point']['position_world_m']
            or request['original_candidates'] != original['all_seven_candidates']
            or request['original_mount'] != original['mount']
            or request['original_proxy_vertices_world_m'] != original['current_proxy_vertices_world_m']
            or request['original_selected'] != selected['selected'] or selected['selected'] != 'STOP'):
        raise ValueError('Frozen sensor fields/candidates differ')
    order = [*MOVE, 'STOP']
    if request['candidate_order'] != order or result['candidate_order'] != order:
        raise ValueError('Seven-option ordering differs')
    # Independent ideal static mount and previously audited finite pad formula.
    # Do not invoke producer finite_gap(), distance_to_gap(), rank(), or compute().
    rotation = Rotation.from_quat(own['robot0_eef_quat']).as_matrix()@np.array([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]])
    q1, q2 = own['robot0_gripper_qpos']
    low, high = np.array([-q1+.0005, -.008, -.0116]), np.array([-q2-.0005, .008, .0044])
    pad_error = max(float(np.max(np.abs(low-result['finite_gap_lower_site_m']))),
                    float(np.max(np.abs(high-result['finite_gap_upper_site_m']))))
    rotation_error = float(np.max(np.abs(rotation-result['mount']['returned_site_rotation_world'])))
    if pad_error > 1e-14 or rotation_error > 1e-14:
        raise ValueError('Independent pad/mount reconstruction differs')
    if result['mount'] != request['original_mount']:
        raise ValueError('Saved original mount changed')
    for name, center in (('gripper0_finger1_pad_collision', [-q1-.0035, 0., -.0036]),
                         ('gripper0_finger2_pad_collision', [-q2+.0035, 0., -.0036])):
        expected_vertices = np.asarray(list(product((-.004, .004), (-.008, .008), (-.008, .008))))+center
        vertices = np.asarray(result['calibrated_pad_vertices_site_m'][name])
        if vertices.shape != (8, 3) or any(np.min(np.linalg.norm(expected_vertices-v, axis=1)) > 1e-14 for v in vertices):
            raise ValueError('Stored calibrated pad vertices differ')
    delta = np.asarray(request['point_P_world_m'])-np.asarray(own['robot0_eef_pos'])
    distances, rows, errors = {}, [], []
    for token in order:
        movement = np.asarray(MOVE.get(token, (0., 0., 0.)))*.01
        local = rotation.T@(delta-movement)
        nearest = np.clip(local, low, high)
        distance = float(np.linalg.norm(local-nearest))
        distances[token] = distance
        saved = result['candidates'][token]
        if (saved['original_guard_and_P_effect'] != original['all_seven_candidates'][token]
                or saved['excluded'] != original['all_seven_candidates'][token]['excluded']
                or saved['original_guard_and_P_effect']['nominal_tcp_to_P_m'] != float(np.linalg.norm(delta-movement))):
            raise ValueError('Original guard/P effect changed: '+token)
        error = abs(distance-saved['gap_distance_m'])
        if error > 1e-14 or np.max(np.abs(local-saved['point_in_site_m'])) > 1e-14:
            raise ValueError('Independent Euclidean projection differs: '+token)
        if saved['point_in_finite_gap'] != bool(np.all(local >= low) and np.all(local <= high)):
            raise ValueError('Finite-gap membership differs')
        errors.append(error)
        rows.append({'token': token, 'independent_gap_distance_m': distance, 'saved_gap_distance_m': saved['gap_distance_m'],
                     'distance_error_m': error, 'excluded': saved['excluded'], 'closest_point_in_site_m': nearest.tolist()})
    current = distances['STOP']
    if abs(current-result['current_gap_distance_m']) > 1e-14 or np.max(np.abs(rotation.T@delta-result['current_point_in_site_m'])) > 1e-14:
        raise ValueError('Saved current relation differs')
    for row in rows:
        saved = result['candidates'][row['token']]
        improvement = row['independent_gap_distance_m'] < current
        if saved['strict_improvement'] != improvement or abs(saved['gap_distance_change_m']-(row['independent_gap_distance_m']-current)) > 2e-14:
            raise ValueError('Strict improvement/change differs')
    choices = [(distances[t], t) for t in MOVE if not result['candidates'][t]['excluded']]
    best = min(choices) if choices else None
    selected_gap = best[1] if best and best[0] < current else 'STOP'
    old_choices = [(original['all_seven_candidates'][t]['nominal_tcp_to_P_m'], t)
                   for t in MOVE if not original['all_seven_candidates'][t]['excluded']]
    old_best = min(old_choices) if old_choices else None
    old_selected = old_best[1] if old_best and old_best[0] < selected['live_tcp_to_fixed_proxy_m'] else 'STOP'
    if selected_gap != result['gap_selected'] or old_selected != result['original_selected'] or old_selected != 'STOP':
        raise ValueError('Independent tuple selection differs')
    if (result['gate_pass'] != (selected_gap != 'STOP') or result['executed_actions'] != 0
            or result['model_physics_render_calls'] != 0 or result['automatic_extension'] is not False
            or result['evaluator_read'] is not False or result['guard_recomputed'] is not False
            or any(result[k] is not None for k in ('identity_verified', 'extent_established', 'holding', 'qualified_grasp'))):
        raise ValueError('Registered terminal gate/status differs')
    old_local = rotation.T@delta
    new_local = rotation.T@(delta-.01*np.asarray(MOVE[selected_gap]))
    old_excess, new_excess = old_local-np.clip(old_local, low, high), new_local-np.clip(new_local, low, high)
    contributions = (new_excess**2-old_excess**2)/(current+distances[selected_gap])
    value = {'status': 'PASS', 'producer_commit': manifest['code']['commit'], 'source': str(RUN),
        'result_sha256': RESULT_SHA, 'seal_sha256': SEAL_SHA, 'source_journal_sha256': SOURCE_SHA,
        'source_chained_records_checked': count, 'all_frozen_sensor_fields_guards_P_effects_exact': True,
        'independent_formula': 'SciPy quaternion rotation × ideal audited Rz(-90); explicit calibrated finite pad bounds; Euclidean point minus coordinatewise projection',
        'maximum_pad_bound_error_m': pad_error, 'maximum_mount_matrix_error': rotation_error,
        'maximum_gap_distance_error_m': max(errors), 'current_gap_distance_m': current,
        'original_selected': old_selected, 'gap_selected': selected_gap, 'gate_pass': result['gate_pass'],
        'independent_selected_reduction_m': current-distances[selected_gap],
        'saved_selected_reduction_m': -result['candidates'][selected_gap]['gap_distance_change_m'],
        'selected_point_site_coordinate_delta_m': (new_local-old_local).tolist(),
        'selected_distance_change_axis_contributions_m': contributions.tolist(),
        'candidates': rows, 'new_experiment_or_physics_run': False,
        'interpretation': 'Formal registered strict-improvement gate passes by approximately1.96micrometres; no new threshold, physical qualification or automatic extension is inferred.'}
    with Path(output).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: value[k] for k in ('status', 'original_selected', 'gap_selected', 'maximum_gap_distance_error_m', 'independent_selected_reduction_m')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    audit(parser.parse_args().output)
