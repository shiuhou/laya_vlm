"""Prepared two-move callback and exact replay adapter; no world constructor/CLI.

A separately reviewed runner must bind the qualified support, both goals, saved
frame and source admission before attaching this callback to existing collect().
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from ..decision_interface import CanonicalDecisionInput, evidence, geometric_effects
from . import task2_closed_empty_scene as scene
from .records import file_hash, load_records

prior = scene.prior
base = scene.base
local = prior.local
approach = prior.approach
PHASE = 'retarget'
ORDER = ('cached', 'refreshed')
MAX_MOVES = 2


def restore_passive(recorder, groups):
    """Resume the current fresh episode's original initial force baseline."""
    records, errors = load_records(recorder.output / 'episodes.jsonl')
    gates = [r['data'] for r in records if r['kind'] == 'initial_frame_gate']
    native = [r for r in records if r['kind'] in ('native_before', 'native_after')]
    if errors or len(gates) != 1 or not native or native[-1]['kind'] != 'native_after':
        raise ValueError('Complete own-run initial baseline and final approach native sample required')
    gate = gates[0]
    if {k: sorted(v) for k, v in groups.items()} != gate['groups_evaluator_only']:
        raise ValueError('Fresh episode evaluator contact groups changed')
    passive = base.PassiveContactRecorder(recorder, groups, gate['initial_contact_snapshot_evaluator_only'])
    if [list(pair) for pair in sorted(passive.baseline)] != gate['initial_above_threshold_robot_pairs']:
        raise ValueError('Original initial force baseline mismatch')
    if any(r['kind'] == 'first_new_robot_contact' for r in records):
        raise ValueError('Approach contact abort cannot be cleared for retargeting')
    last = native[-1]
    passive.previous = {'stage': last['kind'], 'raw_record_id': last['record_id'],
        **{key: last['data'][key] for key in ('step', 'control', 'index', 'time_s')}}
    return passive


def retarget_decision(goal, proprio, source_time, current_time, revision, history, arm, provenance):
    """Keep original relation/effect/rule arithmetic; describe the actual source."""
    view = base.decision(goal, proprio, source_time, current_time, revision, history)
    fields = {**view.state.fields,
        'task.instruction': evidence('Approach the reported target point.', 'task', 'bounded retargeting diagnostic'),
        'target.position_m': evidence(goal['position_world_m'], 'sensor',
            'sealed native POINT reused under exact archived-input equivalence'),
        'quality.geometry_age_s': evidence(None, 'unknown', 'exact depth sample time unknown'),
        'quality.semantic_age_s': evidence(None, 'unknown', 'exact RGB sample time unknown')}
    state = replace(view.state, fields=fields, meta={
        'revision': revision, 'asof_sim_time': current_time, 'goal_arm': arm,
        'target_source_read_time_s': source_time, 'target_read_age_s': current_time-source_time,
        'exact_target_sample_time_s': None, 'robot_observation_exact_sample_time_s': None,
        'generation_mode': 'hybrid' if arm == 'cached' else 'slow',
        'goal_provenance': deepcopy(provenance), 'tracking_active': False,
        'guard_support': 'fixed_source_current_full_BOX', 'support_refreshed_during_suffix': False,
        'new_model_calls': 0, 'comparison_changes_observation_and_generation_mode': True})
    return CanonicalDecisionInput(state, view.candidates, geometric_effects(state, view.candidates), view.history)


class RetargetingCallback:
    """Sensor-selected suffix only; cannot reset, load controls, or call a model."""
    def __init__(self, arm, *, goal, goal_source_read_time_s, goal_provenance,
                 guard_packet, postevent_frame, postevent_frame_sha256,
                 postevent_read_time_s, postevent_own, common_evaluation_point):
        if arm not in ORDER:
            raise ValueError('Only the fixed cached/refreshed pair is allowed')
        for point in (goal['position_world_m'], common_evaluation_point):
            if np.asarray(point).shape != (3,) or not np.isfinite(point).all():
                raise ValueError('Both selected and common evaluation sensor points must be finite')
        if not guard_packet['full_support']:
            raise ValueError('Qualified nonempty current full-BOX support required')
        if file_hash(postevent_frame) != postevent_frame_sha256:
            raise ValueError('Bound archived postevent RGB-D changed')
        self.arm, self.goal = arm, deepcopy(goal)
        self.goal_source_read_time_s = float(goal_source_read_time_s)
        self.goal_provenance = deepcopy(goal_provenance)
        self.guard_packet = deepcopy(guard_packet)
        self.postevent_frame, self.postevent_frame_sha256 = Path(postevent_frame), postevent_frame_sha256
        self.postevent_read_time_s, self.postevent_own = float(postevent_read_time_s), scene.own_packet(postevent_own)
        self.common_evaluation_point = np.asarray(common_evaluation_point, float)
        self.attempted = self.completed = 0
        self.started = False

    def __call__(self, *, backend, executor, camera, recorder, groups, approach):
        if self.started:
            raise RuntimeError('One retarget callback per fresh episode')
        self.started = True
        prefix = prior.verify_prefix(recorder.output, 'neck', approach)
        if (approach['completed_actions'] != scene.EVENT_STEP or backend.step_m != .01
                or backend._grip_cmd != -1):
            raise ValueError('Exact 29-action open-jaw neck prefix required')
        passive = restore_passive(recorder, groups)
        recorder.record('approach_prefix_verified', prefix)
        world = backend.world
        try:
            event = scene.SceneSuffix('neck-away')
            event.before_scene(backend=backend, recorder=recorder, groups=groups, approach=approach)
            after = event.sensors[-1]
            if (after['phase'] != 'scene_after' or after['capture_read_sim_time_s'] != self.postevent_read_time_s
                    or after['own_observations'] != self.postevent_own
                    or file_hash(self.postevent_frame) != self.postevent_frame_sha256):
                raise ValueError('Live postevent own/time/source equivalence failed')
            with np.load(recorder.output / after['artifact'], allow_pickle=False) as frame:
                with np.load(self.postevent_frame, allow_pickle=False) as reference:
                    checks = base.require_exact_frame(frame, reference)
            recorder.record('retarget_input_equivalence', {'array_bytes_exact': checks,
                'source_frame_sha256': self.postevent_frame_sha256,
                'postevent_read_time_s': self.postevent_read_time_s, 'own_packet_exact': True,
                'semantic_reuse': 'archived_output_under_exact_input_equivalence', 'new_model_calls': 0,
                'initial_contact_baseline_unchanged': [list(pair) for pair in sorted(passive.baseline)]})
            selector = prior.approach.guard.EndpointSelector(self.guard_packet)
            history, tokens, reason = (), [], 'retarget_two_move_budget'
            for boundary in range(MAX_MOVES):
                step = scene.EVENT_STEP + boundary
                with local.read_only_measurement(world):
                    proprio = backend.proprioception()
                    own = scene.own_packet(world.obs)
                if proprio['gripper_command'] != 'OPEN' or backend._grip_cmd != -1:
                    raise ValueError('Retargeting must preserve OPEN command')
                view = retarget_decision(self.goal, proprio, self.goal_source_read_time_s,
                    float(world.data.time), step, history, self.arm, self.goal_provenance)
                token, selection, stop_reason = selector(view, own)
                if token not in {*base.MOVE, 'STOP'}:
                    raise ValueError('Only unchanged approach moves or terminal STOP allowed')
                recorder.record('decision', {'step': step, 'native_phase': PHASE, 'boundary': boundary,
                    'canonical': asdict(view), 'selected': token, 'experiment_selection': selection,
                    'fixed_support_read_age_s': float(world.data.time)-self.postevent_read_time_s,
                    'exact_support_sample_time_s': None, 'live_own_observations': own})
                if token == 'STOP':
                    reason = stop_reason
                    break
                self.attempted += 1
                recorder.record('action_started', {'step': step, 'token': token, 'native_phase': PHASE,
                    'selection': 'existing_rule_current_own_fixed_goal_and_current_BOX_support'})
                tracking = {'control': None}
                with base.observe_controls(world, recorder, step, tracking, expected_grip=-1) as controls:
                    with local.native_observer(world, passive, PHASE, step, tracking, groups) as native:
                        result = executor.execute(token)
                self.completed += 1
                tokens.append(token)
                recorder.record('action_completed', {'step': step, 'token': token, 'native_phase': PHASE,
                    'result': result, 'controls': len(controls), 'native_integrations': len(native),
                    'new_contact_observed': passive.first is not None})
                if (len(controls) != 8 or len(native) != 200
                        or any(sum(row['control'] == control for row in native) != 25 for control in range(8))):
                    raise RuntimeError('Unexpected retarget primitive/control/native counts')
                with local.read_only_measurement(world):
                    frame, proprio = camera.capture(), backend.proprioception()
                    own = scene.own_packet(world.obs)
                recorder.capture(frame)
                tcp = np.asarray(proprio['tcp_pos_world_m'])
                recorder.record('endpoint', {'step': step, 'native_phase': PHASE, 'proprioception': proprio,
                    'own_observations': own, 'capture_seq': frame['capture_seq'],
                    'distance_to_own_goal_m': float(np.linalg.norm(tcp-self.goal['position_world_m'])),
                    'distance_to_common_fresh_sensor_point_m': float(np.linalg.norm(tcp-self.common_evaluation_point)),
                    'common_target_is_evaluation_only': True})
                if passive.first is not None or result['execution_contract_violation']:
                    reason = 'new_robot_contact' if passive.first is not None else 'execution_contract_violation'
                    break
                history = ({'action': token, 'tcp_delta_m': result['delta_m'],
                    'elapsed_sim_s': result['execution_after']['sim_time']-result['execution_before']['sim_time'],
                    'gripper_command': proprio['gripper_command'], 'source': 'proprioception'},)
            return {'reason': reason, 'approach': approach, 'retarget_arm': self.arm,
                'attempted_actions': approach['attempted_actions']+self.attempted,
                'completed_actions': approach['completed_actions']+self.completed,
                'retarget_attempted_actions': self.attempted, 'retarget_completed_actions': self.completed,
                'retarget_tokens': tokens, 'max_retarget_moves': MAX_MOVES,
                'first_contact_evaluator_only': passive.first, 'new_model_calls': 0,
                'grasp_attempted': False, 'holding': None, 'task_success_claim': False}
        except BaseException as exc:
            recorder.record('retarget_failure', {'exception': repr(exc), 'no_retry': True,
                'retarget_attempted_actions': self.attempted, 'retarget_completed_actions': self.completed})
            raise


class RetargetReplay(scene.SceneReplay):
    """Explicit event replay for the new phase, including zero-action STOP."""
    def __init__(self, source, output):
        super().__init__(source, output)
        records, errors = load_records(Path(source) / 'episodes.jsonl')
        actions = [r['data'] for r in records if r['kind'] == 'action_completed'
                   and r['data']['step'] >= scene.EVENT_STEP]
        if (errors or len(actions) > MAX_MOVES
                or any(row.get('native_phase') != PHASE or row['token'] not in base.MOVE for row in actions)
                or [row['step'] for row in actions] != list(range(scene.EVENT_STEP, scene.EVENT_STEP+len(actions)))):
            raise ValueError('At most two ordered existing retarget moves required for replay')
        self.suffix_actions, self.backend = len(actions), None

    def __call__(self, backend, action):
        self.backend = backend
        if action['step'] >= scene.EVENT_STEP and action.get('native_phase') != PHASE:
            raise ValueError('Retarget replay phase mismatch')
        # The existing event dispatcher validates the old phase only as a trigger.
        # Bind our new phase above, then adapt only that trigger metadata. No token,
        # control, capture, scene record or native phase passed to replay is changed.
        trigger = ({**action, 'native_phase': scene.SCHEDULE[0][0]}
                   if action['step'] >= scene.EVENT_STEP else action)
        super().__call__(backend, trigger)

    def finish(self):
        if self.invocations == 0:
            if self.suffix_actions != 0 or self.backend is None:
                raise ValueError('Only a replayed complete zero-move prefix may dispatch the terminal event')
            super().__call__(self.backend, {'step': scene.EVENT_STEP, 'native_phase': scene.SCHEDULE[0][0]})
        super().finish()
