"""Stored-only frame arithmetic and guarded interface dependency audit."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..decision_interface import (CanonicalDecisionInput, CanonicalDecisionState, Evidence,
    FIELD_NAMES, derive_relations, evidence, geometric_effects, shared_atomic_candidates)
from .records import code_identity, file_hash, load_records

ROOT = Path(__file__).resolve().parents[2]
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
HASHES = {
    'local-grasp-interface-run-02/episodes.jsonl': '9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb',
    'local-grasp-interface-run-02/manifest.json': '42bf3cb122acb8c05bd9320e3d914a678235099f5842b5f693dc258bc29b550a',
    'local-grasp-interface-run-02/sensors.json': 'f3eead6a1556e2bbb64ea095aca6c251c6df7e95797099510d5aeb52fe662b58',
    'local-grasp-interface-run-02/sensor-seal.json': '2ac164126dcd9ca32e851c97da90db29657c0a7f0c6bf4a464cdd68862fd1326',
    'interaction-observability-paired-01/endpoints.json': 'c28136d9e0e67b359491a3d270b0566e49a7f5939287363a18cdd8192ab7abe5',
    'robot-geometry-observability-03/robot-calibration.json': '11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa',
    'task2-box-support-run-02/sensor-representation.json': 'be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead',
    'interaction-observability-paired-01/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
    'local-grasp-interface-run-02/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
}
PROTOCOL = ROOT/'docs/research/proprio_frame_consistency_protocol.md'


def qmatrix(quaternion, order='xyzw'):
    q = np.asarray(quaternion, dtype=float)
    if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) == 0:
        raise ValueError('finite nonzero quaternion required')
    q = q/np.linalg.norm(q)
    if order == 'xyzw':
        x, y, z, w = q
    elif order == 'wxyz':
        w, x, y, z = q
    else:
        raise ValueError('explicit quaternion order required')
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def angle(matrix):
    m = np.asarray(matrix)
    skew = np.array([m[2, 1]-m[1, 2], m[0, 2]-m[2, 0], m[1, 0]-m[0, 1]])*.5
    return float(np.degrees(np.arctan2(np.linalg.norm(skew), (np.trace(m)-1)*.5)))


def static_mount(calibration):
    bodies = {b['name']: b for b in calibration['bodies']}
    site = next(s for s in calibration['sites'] if s['name'] == 'gripper0_grip_site')
    position = np.asarray(site['position_body_m'], float)
    rotation = qmatrix(site['quaternion_body_wxyz'], 'wxyz')
    current, chain = site['body'], []
    while current != 'robot0_right_hand':
        b = bodies[current]
        if b['joints']:
            raise ValueError('body-to-site chain is not fixed')
        r = qmatrix(b['quaternion_parent_wxyz'], 'wxyz')
        position = np.asarray(b['position_parent_m'])+r@position
        rotation = r@rotation
        chain.append(current)
        current = b['parent']
    return position, rotation, chain


class GuardedObservations(dict):
    def __getitem__(self, key):
        if key not in ('robot0_eef_pos', 'robot0_gripper_qpos'):
            raise AssertionError('excluded proprioception access: '+key)
        return super().__getitem__(key)


def model_packet(sensor, point, poison=False):
    obs = dict(sensor['returned_observations'])
    if poison:
        obs['robot0_eef_quat'] = [999., -123., 456., -789.]
    backend = LiberoWorldBackend(SimpleNamespace(obs=GuardedObservations(obs)))
    backend._grip_cmd = sensor['command'][-1]
    proprio = backend.proprioception()
    fields = {name: Evidence() for name in FIELD_NAMES}
    for name, value in [('robot.tcp_position_m', proprio['tcp_pos_world_m']),
                        ('robot.gripper_width_m', proprio['gripper_width_m']),
                        ('robot.gripper_command', proprio['gripper_command'])]:
        fields[name] = evidence(value, 'proprioception', 'saved robot-only packet')
    fields['target.position_m'] = evidence(point, 'sensor', 'unchanged sealed initial BOX point')
    fields['quality.geometry_valid'] = evidence(True, 'derived', 'offline dependency comparison only')
    derive_relations(fields)
    state = CanonicalDecisionState(fields, {'revision': 0, 'asof_sim_time': sensor['read_sim_time_s']})
    candidates = shared_atomic_candidates()
    view = CanonicalDecisionInput(state, candidates, geometric_effects(state, candidates))
    # No rule choice, action, controller or model call is made.
    return {'proprioception': proprio, 'model_input': view.provider_input(),
            'effects': asdict(view.effects), 'state_id': state.identity()}


def row_arithmetic(sensor, mount):
    body = qmatrix(sensor['returned_observations']['robot0_eef_quat'])
    corrected = body@mount
    saved = np.asarray(sensor['tcp_fk_rotation_world'])
    wrist = np.asarray(sensor['wrist_frame_rotation_world_at_read_time'])
    joints = sensor['direct_gripper_qpos_m']
    pad_centers = [np.array([-joints[0]-.0035, 0., -.0036]),
                   np.array([-joints[1]+.0035, 0., -.0036])]
    result = {'uncorrected_vs_saved_site_deg': angle(body@saved.T),
              'corrected_vs_saved_site_deg': angle(corrected@saved.T),
              'corrected_vs_saved_site_max_matrix_error': float(np.max(np.abs(corrected-saved))),
              'saved_wrist_vs_saved_site_deg': angle(wrist@saved.T),
              'saved_wrist_site_max_matrix_error': float(np.max(np.abs(wrist-saved))),
              'returned_vs_saved_fk_site_position_mm': float(np.linalg.norm(
                  np.asarray(sensor['returned_observations']['robot0_eef_pos'])-sensor['tcp_fk_world_m'])*1000),
              'hypothetical_pad_center_errors_mm': [float(np.linalg.norm((body-corrected)@p)*1000) for p in pad_centers],
              'sample_time_known': sensor['returned_observation_sample_times_s'] is not None,
              'body_world_position_available': False}
    return result


def stats(values):
    return {'count': len(values), 'min': min(values), 'median': float(np.median(values)), 'max': max(values)}


def run(output):
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('freeze audit code before numerical analysis')
    for name, sha in HASHES.items():
        if file_hash(RAW/name) != sha:
            raise ValueError('source changed: '+name)
    manifest = json.loads((RAW/'local-grasp-interface-run-02/manifest.json').read_text())
    checked_modules = ['embodied_runtime/adapters/libero.py', 'embodied_runtime/runtime_core.py',
                       'embodied_runtime/decision_interface.py', 'embodied_runtime/experiments/interaction_observability.py']
    for module in checked_modules:
        if file_hash(ROOT/module) != manifest['code']['source_sha256'][module]:
            raise ValueError('archived interface source changed: '+module)
    records, errors = load_records(RAW/'local-grasp-interface-run-02/episodes.jsonl')
    if errors:
        raise ValueError(errors)
    sensors = json.loads((RAW/'local-grasp-interface-run-02/sensors.json').read_text())
    from_journal = [{k: r['data'][k] for k in ('arm', 'step', 'control', 'sensor')}
                    for r in records if r['kind'] == 'control_observed']
    if sensors != from_journal or len(sensors) != 240:
        raise ValueError('complete stored sensor lineage differs')
    calibration = json.loads((RAW/'robot-geometry-observability-03/robot-calibration.json').read_text())
    translation, mount, chain = static_mount(calibration)
    point = json.loads((RAW/'task2-box-support-run-02/sensor-representation.json').read_text())['point_P']['position_world_m']
    endpoints = json.loads((RAW/'interaction-observability-paired-01/endpoints.json').read_text())
    initial = [r['sensor'] for r in endpoints if r['arm'] == 'close' and r['after_step'] == -1]
    if len(initial) != 1:
        raise ValueError('one historical initial sensor packet required')
    initial = initial[0]
    rows, by_key = [], {}
    invariant_count = 0
    for r in sensors:
        key = (r['arm'], r['step'], r['control'])
        if key in by_key:
            raise ValueError('duplicate sensor key')
        by_key[key] = r['sensor']
        row = {k: r[k] for k in ('arm', 'step', 'control')}
        row.update(row_arithmetic(r['sensor'], mount))
        baseline = model_packet(r['sensor'], point)
        poisoned = model_packet(r['sensor'], point, poison=True)
        if baseline != poisoned:
            raise ValueError('quaternion altered model-facing state/effects')
        invariant_count += 1
        if baseline['effects']['effects']['GRASP'] != {'source': 'unknown', 'privileged': False, 'values': {}}:
            raise ValueError('GRASP geometric effect unexpectedly populated')
        rows.append(row)
    cached_rows, interventions = [], []
    for record in records:
        if record['kind'] != 'action_completed':
            continue
        d = record['data']; result = d['result']; after_sensor = by_key[(d['arm'], d['step'], 7)]
        matrix = np.asarray(result['execution_after']['orientation'] if d['step'] >= 13
                            else result['features']['eef_rotation_matrix'])
        body = qmatrix(after_sensor['returned_observations']['robot0_eef_quat'])
        saved = np.asarray(after_sensor['tcp_fk_rotation_world'])
        cached_rows.append({'arm': d['arm'], 'step': d['step'], 'token': d['token'],
            'uncorrected_body_vs_cached_site_deg': angle(body@matrix.T),
            'corrected_body_vs_cached_site_deg': angle((body@mount)@matrix.T),
            'saved_fk_vs_cached_site_deg': angle(saved@matrix.T)})
        if d['step'] >= 13:
            before_sensor = by_key[(d['arm'], d['step']-1, 7)]
            body_before = qmatrix(before_sensor['returned_observations']['robot0_eef_quat'])
            body_delta = body@body_before.T
            corrected_delta = (body@mount)@(body_before@mount).T
            cached_delta = matrix@np.asarray(result['execution_before']['orientation']).T
            recomputed = angle(cached_delta)
            if abs(recomputed-result['rotation_angle_deg']) > 1e-7:
                raise ValueError('stored validator rotation does not reproduce')
            interventions.append({'arm': d['arm'], 'step': d['step'], 'token': d['token'],
                'stored_validator_rotation_deg': result['rotation_angle_deg'],
                'recomputed_cached_site_rotation_deg': recomputed,
                'returned_body_relative_rotation_deg': angle(body_delta),
                'body_relative_vs_cached_relative_deg': angle(body_delta@cached_delta.T),
                'mount_cancellation_max_matrix_error': float(np.max(np.abs(body_delta-corrected_delta))),
                'hold_rotation_limit_deg': result['execution_contract_tolerances']['hold_rotation_deg'],
                'recorded_contract_violation': result['execution_contract_violation'],
                'all_low_level_rotation_commands_zero': all(cmd[3:6] == [0., 0., 0.] for cmd in result['low_level_commands'])})
    if len(cached_rows) != 30 or len(interventions) != 4:
        raise ValueError('complete endpoint/intervention accounting required')
    initial_body = qmatrix(initial['returned_observations']['robot0_eef_quat'])
    initial_delta = np.asarray(point)-initial['returned_observations']['robot0_eef_pos']
    scalar_keys = [k for k, v in rows[0].items() if type(v) is float]
    report = {'status': 'pass', 'code': identity, 'protocol_sha256': file_hash(PROTOCOL),
        'source_sha256': HASHES, 'interface_source_matches_archived_producer': checked_modules,
        'no_physics_inference_render_or_FK': True,
        'static_body_to_site_translation_m': translation.tolist(), 'static_body_to_site_rotation': mount.tolist(),
        'static_chain_site_to_body': chain, 'sensor_rows': rows, 'cached_endpoint_rows': cached_rows,
        'sensor_summary': {k: stats([r[k] for r in rows]) for k in scalar_keys},
        'hypothetical_pad_center_error_mm': stats([v for r in rows for v in r['hypothetical_pad_center_errors_mm']]),
        'cached_endpoint_summary': {k: stats([r[k] for r in cached_rows]) for k in
            ('uncorrected_body_vs_cached_site_deg', 'corrected_body_vs_cached_site_deg', 'saved_fk_vs_cached_site_deg')},
        'atomic_interventions': interventions, 'guarded_model_input_effect_invariance_rows': invariant_count,
        'model_state_orientation_fields': [k for k in FIELD_NAMES if 'orientation' in k or 'quat' in k],
        'GRASP_geometric_effect': 'unknown for all240 offline dependency packets',
        'historical_initial_sensor': {**row_arithmetic(initial, mount),
            'provenance': 'paired-01 endpoint -1; local02 initial robot packet absent',
            'fixed_BOX_P_world_m': point, 'P_in_unadjusted_body_axes_at_site_origin_m': (initial_body.T@initial_delta).tolist(),
            'P_in_corrected_site_axes_at_site_origin_m': ((initial_body@mount).T@initial_delta).tolist(),
            'initial_sensor_packet': initial},
        'unknowns': ['independent_world_body_position_not_saved', 'actual_returned_sample_times_unknown',
                     'exact_same_time_body_to_site_agreement_not_established', 'BOX_surface_ownership_unqualified'],
        'scope': 'stored frame arithmetic and current interface dependency; no action selection or target fit'}
    output = Path(output); output.mkdir(exist_ok=False)
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output/'audit.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: report[k] for k in ('status', 'sensor_summary', 'cached_endpoint_summary',
        'hypothetical_pad_center_error_mm', 'atomic_interventions', 'guarded_model_input_effect_invariance_rows')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
