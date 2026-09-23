"""Audit the existing embodied loop across decisions; never selects an action."""
from __future__ import annotations

import numpy as np


def feedback_audit(rows, attempts, *, expect_final=False):
    """Link completed execution to fresh sensors and, when present, the next input.

    Checks establish recorded feedback delivery. Choice changes do not establish
    causal model sensitivity, especially when gates remove the previous choice.
    All progress measurements here are simulator evaluation, never model input.
    """
    captures, observations, detections, boundaries, sensing = {}, {}, {}, {}, {}
    active_capture = None
    for row in rows:
        kind, data = row['kind'], row['data']
        if kind == 'vision_capture':
            active_capture = data['capture_seq']
            captures[active_capture] = data
            observations[active_capture] = []
        elif kind == 'vision_completed':
            detections[data['capture_seq']] = data
        elif kind == 'observation' and active_capture is not None:
            observations[active_capture].append(data)
        elif kind == 'demo_boundary':
            boundaries[data['step']] = data
        elif kind == 'demo_sensing_complete':
            sensing[data['step']] = data
    by_step = {a['step']: a for a in attempts}
    transitions = []
    for attempt in attempts:
        execution = attempt['execution']
        if execution is None:
            continue
        step = attempt['step']
        following = by_step.get(step + 1)
        boundary = boundaries.get(step + 1)
        post_capture = captures.get(boundary['capture_seq']) if boundary else (following or {}).get('capture')
        complete = sensing.get(step + 1)
        terminal = bool(complete and complete['terminal_observation'])
        issues = []
        post_proprio, post_visual = None, None
        visual_used_by_next_belief = None
        if post_capture is not None:
            obs = observations[post_capture['capture_seq']]
            proprio = [o for o in obs if o['event']['source'] == 'proprio']
            visual = [o for o in obs if o['event']['source'] == 'locateanything+depth'
                      and o['event']['source_seq'] == post_capture['capture_seq']]
            post_proprio = proprio[-1] if proprio else None
            post_visual = visual[-1] if visual else None
            if post_capture['capture_sim_time'] != execution['execution_after']['sim_time']:
                issues.append('post-action capture is not at the execution endpoint')
            if attempt['capture'] and post_capture['capture_seq'] <= attempt['capture']['capture_seq']:
                issues.append('post-action capture is not fresh')
            if post_proprio is None or not post_proprio['accepted']:
                issues.append('post-action proprioception not admitted')
            else:
                p = post_proprio['event']
                if p['capture_sim_time'] != post_capture['capture_sim_time']:
                    issues.append('proprioception and RGB-D boundary differ')
                if not np.array_equal(p['value']['tcp_pos_world_m'], execution['execution_after'].get('tcp_xyz')):
                    issues.append('post-action robot observation differs from executed TCP endpoint')
                expected_command = 'CLOSED' if execution['execution_after'].get('gripper_command', 0) > 0 else 'OPEN'
                if p['value']['gripper_command'] != expected_command:
                    issues.append('post-action retained gripper command differs from executor')
            if post_visual is None or not post_visual['accepted']:
                issues.append('fresh post-action visual event not admitted')
            elif post_visual['event']['capture_sim_time'] != post_capture['capture_sim_time']:
                issues.append('visual event and RGB-D boundary differ')
            if complete and (complete['after_action_step'] != step
                             or complete['capture_seq'] != post_capture['capture_seq']
                             or not post_proprio
                             or complete['proprio_source_seq'] != post_proprio['event']['source_seq']):
                issues.append('sensing completion does not link this action and its observations')
        elif following or expect_final:
            issues.append('post-action observation missing')
        if following:
            if following['issues']:
                issues.append('next decision evidence has audit issues')
            if post_proprio:
                continuous = following['snapshot']['snapshot']['continuous']
                for key in ('tcp_pos_world_m', 'gripper_width_m', 'gripper_command'):
                    if continuous.get(key) != post_proprio['event']['value'].get(key):
                        issues.append(f'next belief does not contain observed {key}')
            if post_visual:
                event = post_visual['event']
                validity = following['snapshot']['snapshot'].get('validity', {}).get(event.get('track_id'), {})
                evidence_id = [event['source'], event['source_seq']]
                visual_used_by_next_belief = all(evidence_id in validity.get(key, []) for key in
                    ('geometry_evidence_ids', 'semantic_evidence_ids'))
                if not visual_used_by_next_belief:
                    issues.append('fresh visual evidence not used by next fused belief')
        elif expect_final and not terminal:
            issues.append('terminal sensing did not complete')
        model_before = (attempt['model_input'] or {}).get('state', {}).get('state', {})
        model_after = ((following or {}).get('model_input') or {}).get('state', {}).get('state', {})
        changed = {k: {'before': model_before.get(k), 'after': v} for k, v in model_after.items()
                   if v != model_before.get(k)}
        allowed_before = attempt['option_order']
        allowed_after = following['option_order'] if following else []
        proposed_before = (attempt['decision'] or {}).get('token')
        proposed_after = ((following or {}).get('decision') or {}).get('token')
        selected_removed = bool(following and proposed_before not in allowed_after)
        before_eval = (attempt['evaluation']['before'] or {}).get('features', {})
        after_eval = (attempt['evaluation']['after'] or {}).get('features', {})
        remaining_before = before_eval.get('remaining_open_mm')
        remaining_after = after_eval.get('remaining_open_mm')
        closure = None if remaining_before is None or remaining_after is None else remaining_before - remaining_after
        delivery = bool(following and post_capture and not issues and following['verified_laya_execution'])
        transitions.append({'from_step': step, 'to_step': following['step'] if following else None,
            'post_capture': post_capture, 'post_proprioception': post_proprio, 'post_visual_observation': post_visual,
            'post_detection': detections.get(post_capture['capture_seq']) if post_capture else None,
            'terminal_observation': terminal, 'issues': issues, 'feedback_delivery_verified': delivery,
            'visual_used_by_next_belief': visual_used_by_next_belief,
            'proposed_before': proposed_before, 'executed': execution['token'], 'proposed_after': proposed_after,
            'choice_changed': proposed_before != proposed_after if proposed_after is not None else None,
            'previous_choice_removed_by_gate': selected_removed,
            'newly_allowed': [t for t in allowed_after if t not in allowed_before] if following else [],
            'newly_vetoed': [{'token': c['token'], 'reasons': c['reason_codes']}
                            for c in following['snapshot']['snapshot']['candidates']
                            if not c['feasible'] and c['token'] in allowed_before] if following else [],
            'changed_model_state': changed,
            'model_target_distance_before_m': model_before.get('relations.distance_m'),
            'model_target_distance_after_m': model_after.get('relations.distance_m'),
            'allowed_translations': [t for t in allowed_before if t.startswith('MV_')],
            'drawer_closure_mm_evaluator_only': closure,
            'target_contact_evaluator_only': after_eval.get('moving_contact'),
            'interpretation': ('previous choice was removed by the gate; alternation does not isolate model sensitivity'
                if selected_removed else 'feedback delivery is not proof of causal model sensitivity or useful task-directed choice')})
    closures = [t['drawer_closure_mm_evaluator_only'] for t in transitions]
    return {'transitions': transitions,
            'verified_feedback_deliveries': sum(t['feedback_delivery_verified'] for t in transitions),
            'terminal_observations': sum(t['terminal_observation'] and not t['issues'] for t in transitions),
            'net_drawer_closure_mm_evaluator_only': sum(closures) if closures and all(c is not None for c in closures) else None,
            'translation_actions': sum(t['executed'].startswith('MV_') for t in transitions),
            'claim': 'recorded feedback delivery and observed outcomes; no causal sensitivity or competence claim'}
