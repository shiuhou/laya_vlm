"""Prepared offline two-boundary adapter; no CLI, model, world or executor call.

The caller must supply the separately released, hash-bound sensor packet. This
module supplies only strict return reading and the existing numeric comparison;
it deliberately does not invent a future source-audit schema or launch a run.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import numpy as np

from ..decision_interface import CanonicalDecisionInput, evidence, geometric_effects
from ..runtime_core import _sha256_json
from . import task2_box_point_boundary as base
from . import task2_closed_empty_point_adapter as point_adapter
from . import task2_endpoint_containment_veto as guard
from .coarse_point_probe import admit_point
from .records import file_hash

ORDER = ('present-postevent', 'away-postevent')
QUESTION = 'Point to: the wine bottle.'
HYBRID = {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid',
          'temperature': 0.0, 'do_sample': False, 'verbose': False}
SLOW = {**HYBRID, 'generation_mode': 'slow'}
CACHED_POINT = [-0.11673469557117522, 0.058971097589474636, 0.9883583307522877]
GUARD_SHA = '5782d1905481f14903ea66d10dc91da1fb10382c929fc3da6e4d878b5d57c378'
RETURN_FILES = {'sensor-result.json', 'generation-return.json', 'native-input.json',
                'generation-settings.json', 'resolved_config.yaml'}


def read_slow_return(directory, sha256):
    """Only after source-audit release; verify supplied hashes before parsing."""
    directory = Path(directory)
    if set(sha256) != RETURN_FILES:
        raise ValueError('Exact five-file slow return binding required')
    for name, expected in sha256.items():
        if file_hash(directory / name) != expected:
            raise ValueError('Bound slow source changed: ' + name)
    data = {name: json.loads((directory / name).read_text()) for name in RETURN_FILES}
    config, native = data['resolved_config.yaml'], data['native-input.json']
    if (config['case_id'] not in ORDER or native['condition'] != config['case_id']
            or config['question'] != QUESTION or native['question'] != QUESTION
            or config['settings'] != SLOW or data['generation-settings.json'] != SLOW):
        raise ValueError('Same-question postevent source with explicit slow mode required')
    actual = point_adapter.analyze_rgb_return(data['generation-return.json'],
        len(native['input_token_ids']), 16384, 151645)
    if actual != data['sensor-result.json']:
        raise ValueError('Stored admission differs from unchanged full-return parser')
    return {'case_id': config['case_id'], 'sensor': actual, 'settings': deepcopy(SLOW),
            'image_source': config['image_source'], 'model_RGB_identity': native['rgb'],
            'sha256': deepcopy(sha256)}


def load_same_frame(packet, physical_source_root, own_row):
    """Join a released return to its hash-bound image and saved own sensor row."""
    source = packet['image_source']
    keys = ('capture_id', 'source_capture_stream', 'source_capture_seq', 'artifact',
            'artifact_sha256', 'capture_read_sim_time_s', 'exact_observation_sample_time_s')
    if (source['case_id'] != packet['case_id'] or any(source[k] != own_row[k] for k in keys)
            or own_row['condition'] != 'neck-'+packet['case_id'].split('-')[0]
            or source['directory'] != own_row['condition']):
        raise ValueError('Model image and own sensor row are not the same bound capture')
    root = point_adapter.suffix.relative(physical_source_root, source['directory'])
    path = point_adapter.suffix.relative(root, source['artifact'])
    if file_hash(path) != source['artifact_sha256']:
        raise ValueError('Bound same-frame RGB-D archive changed')
    admitted = packet['sensor']['status'] == 'admitted_rgb_point'
    names = base.FRAME_KEYS if admitted else ('rgb',)
    with np.load(path, allow_pickle=False) as archive:
        frame = {key: archive[key].copy() for key in names}
    rgb = frame['rgb']
    identity = {'shape': list(rgb.shape), 'dtype': str(rgb.dtype),
                'bytes_sha256': hashlib.sha256(rgb.tobytes(order='C')).hexdigest()}
    if rgb.shape != (384, 384, 3) or rgb.dtype != np.uint8 or identity != packet['model_RGB_identity']:
        raise ValueError('RGB-D frame RGB differs from the actual native model input')
    if admitted and (frame['depth_m'].shape != (384, 384) or frame['intrinsics'].shape != (3, 3)
            or frame['camera_to_world'].shape != (4, 4)
            or not np.isfinite(frame['intrinsics']).all() or not np.isfinite(frame['camera_to_world']).all()
            or frame['intrinsics'][0, 0] <= 0 or frame['intrinsics'][1, 1] <= 0):
        raise ValueError('Saved same-frame depth/calibration schema invalid')
    return {'case_id': packet['case_id'], 'source': deepcopy(source), 'settings': deepcopy(packet['settings']),
            'sensor': deepcopy(packet['sensor']), 'own': deepcopy(own_row['own_observations']), 'frame': frame,
            'provenance': {'slow_return_sha256': deepcopy(packet['sha256']),
                           'image_artifact_sha256': source['artifact_sha256']}}


def decision(point, own, read_time, revision, arm, provenance):
    """Retain baseline relation/rule/effect arithmetic; correct stale metadata."""
    joints = np.asarray(own['robot0_gripper_qpos'], float)
    proprio = {'tcp_pos_world_m': own['robot0_eef_pos'],
               'gripper_width_m': float(np.sum(np.abs(joints))), 'gripper_command': None}
    source_read = .5 if arm == 'cached' else read_time
    view = base.decision({'position_world_m': point,
        'definition': 'native_POINT_containing_pixel_center_depth'}, proprio,
        source_read, read_time, revision, ())
    fields = {**view.state.fields,
        'task.instruction': evidence('Approach the reported target point.', 'task', 'offline decision comparison'),
        'target.position_m': evidence(point, 'sensor', 'hash-bound native POINT pixel-center depth projection'),
        'quality.geometry_valid': evidence(True, 'derived', 'finite sampled projection; ownership unverified'),
        'quality.geometry_age_s': evidence(None, 'unknown', 'exact depth sample time unknown'),
        'quality.semantic_age_s': evidence(None, 'unknown', 'exact RGB sample time unknown')}
    state = replace(view.state, fields=fields, meta={
        'revision': revision, 'asof_sim_time': read_time, 'target_source_read_time_s': source_read,
        'target_read_age_s': read_time-source_read, 'exact_target_sample_time_s': None,
        'robot_observation_exact_sample_time_s': None, 'target_refreshed': arm == 'fresh',
        'generation_mode': 'hybrid' if arm == 'cached' else 'slow',
        'goal_provenance': deepcopy(provenance), 'tracking_active': False,
        'guard_support': 'original_cached_full_BOX', 'current_support_verified': False,
        'new_model_calls': 0, 'comparison_changes_observation_and_generation_mode': True})
    return CanonicalDecisionInput(state, view.candidates, geometric_effects(state, view.candidates), ())


def strip_goal_scores(selection):
    """Goal-independent veto evidence can be shared with a nonadmitted row."""
    return {token: {k: deepcopy(v) for k, v in details.items() if k != 'nominal_tcp_to_P_m'}
            for token, details in selection['all_seven_candidates'].items()}


def compare_two(cases, cached, guard_packet):
    """Compute exactly four records from an already admitted sensor binding.

    No source read or feature call occurs merely by importing this module. The
    actual two-boundary run remains gated outside this prepared numeric adapter.
    """
    if ([case['case_id'] for case in cases] != list(ORDER)
            or cached['question'] != QUESTION or cached['settings'] != HYBRID
            or cached['point'] != CACHED_POINT or _sha256_json(guard_packet) != GUARD_SHA):
        raise ValueError('Both fixed postevent cases and same-question cached hybrid POINT required')
    # Validate both sensor packets before any projection or selector computation.
    for case in cases:
        if (case['settings'] != SLOW or case['source']['case_id'] != case['case_id']
                or case['source']['local_suffix_capture_id'] != 0 or case['source']['capture_id'] != 31
                or case['source']['source_capture_stream'] != 'scene' or case['source']['source_capture_seq'] != 2
                or case['source']['exact_observation_sample_time_s'] is not None):
            raise ValueError('Exact paired postevent slow-mode sensor binding required')
        own = case['own']
        if set(own) != set(base.OBS_KEYS):
            raise ValueError('Only the four named returned own observations are allowed')
        for key, size in zip(base.OBS_KEYS, (3, 4, 2, 2), strict=True):
            if np.asarray(own[key]).shape != (size,) or not np.isfinite(own[key]).all():
                raise ValueError('Finite complete saved own packet required')
        sensor = case['sensor']
        if (sensor['status'] not in ('admitted_rgb_point', 'not_admitted')
                or (sensor['status'] == 'admitted_rgb_point') != (sensor['point'] is not None)):
            raise ValueError('Native admission/null-point contract changed')
    rows = []
    for index, case in enumerate(cases):
        own, sensor = case['own'], case['sensor']
        read_time = case['source']['capture_read_sim_time_s']
        projection, depth_sample, nonadmission = None, None, sensor['reason']
        if sensor['status'] == 'admitted_rgb_point':
            x, y = sensor['point']['pixel_index_xy']
            depth = float(case['frame']['depth_m'][y, x])
            depth_sample = {'pixel_index_xy': [x, y], 'pixel_center_xy': [x+.5, y+.5],
                            'value_m': depth if np.isfinite(depth) else None,
                            'nonfinite_value': None if np.isfinite(depth) else repr(depth)}
            try:
                projection = admit_point(sensor['parsed'], sensor['generation_audit'], case['frame'])
            except ValueError as exc:
                if not str(exc).startswith('point_admission:'):
                    raise
                nonadmission = str(exc)
        shared = {'case_id': case['case_id'], 'source': deepcopy(case['source']), 'own': deepcopy(own),
                  'guard_packet_sha256': _sha256_json(guard_packet), 'retained_command': None,
                  'fresh_syntax_status': sensor['status'], 'visual_identity_is_policy_input': False}
        cached_selection = None
        for arm in ('cached', 'fresh'):
            point = cached['point'] if arm == 'cached' else (None if projection is None else projection['position_world_m'])
            row = {**deepcopy(shared), 'arm': arm, 'point_world_m': point,
                   'generation_mode': 'hybrid' if arm == 'cached' else 'slow',
                   'projection': None if arm == 'cached' else projection,
                   'depth_sample': None if arm == 'cached' else depth_sample,
                   'native_image_point': None if arm == 'cached' else deepcopy(sensor['point']),
                   'syntax_status': 'admitted_sensor_point' if arm == 'cached' else sensor['status'],
                   'nonadmission': nonadmission if arm == 'fresh' else None}
            if point is None:
                row.update(canonical=None, eligible_canonical=None, unguarded_token=None, guarded_token=None,
                    selection=None, policy_status='not_evaluated_nonadmitted_goal',
                    guard_reference_record={'case_id': case['case_id'], 'arm': 'cached'},
                    all_seven_candidates={token: {**value, 'nominal_tcp_to_P_m': None}
                        for token, value in strip_goal_scores(cached_selection).items()})
            else:
                provenance = cached['provenance'] if arm == 'cached' else case['provenance']
                view = decision(point, own, read_time, index, arm, provenance)
                token, selection, reason = guard.EndpointSelector(guard_packet)(view, own)
                row.update(canonical=asdict(view), eligible_canonical=selection['eligible_canonical'],
                    unguarded_token=view.rule_token(), guarded_token=token, selection=selection,
                    all_seven_candidates=selection['all_seven_candidates'], terminal_reason=reason,
                    policy_status='evaluated_existing_rule', STOP_means='terminal_without_execution')
                if arm == 'cached':
                    cached_selection = selection
                elif strip_goal_scores(selection) != strip_goal_scores(cached_selection):
                    raise ValueError('Matched own/support unexpectedly changed guard exclusions')
            rows.append(row)
    return {'case_order': list(ORDER), 'arm_order': ['cached', 'fresh'], 'records': rows,
            'record_count': 4, 'candidate_records': 28, 'new_model_physics_render_calls': 0,
            'executed_actions': 0, 'support_refreshed': False,
            'comparison_changes_observation_and_generation_mode': True,
            'current_support_safety_or_clearance_established': False}
