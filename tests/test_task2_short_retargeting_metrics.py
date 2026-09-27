from copy import deepcopy

from embodied_runtime.experiments import task2_short_retargeting_metrics as metrics


def stopped_records():
    payloads = [
        ('initial_frame_gate', {'groups_evaluator_only': {'robot': [1]},
            'initial_above_threshold_robot_pairs': [], 'initial_contact_snapshot_evaluator_only': {'contacts': []}}),
        ('scene_boundary', {'scene_boundary': 'after', 'own_observations': {'robot0_eef_pos': [0., 0., 0.]},
            'capture_read_sim_time_s': 12.1}),
        ('retarget_input_equivalence', {'own_packet_exact': True}),
        ('decision', {'step': 29, 'native_phase': 'retarget', 'boundary': 0, 'selected': 'STOP',
            'canonical': {'state': {'fields': {'target.position_m': {'value': [1., 0., 0.]}}}}}),
        ('termination', {'reason': 'rule_no_strict_nominal_improvement',
            'retarget_attempted_actions': 0, 'retarget_completed_actions': 0})]
    return [{'kind': kind, 'data': data, 'record_id': str(i)} for i, (kind, data) in enumerate(payloads)]


def test_stop_preserves_zero_actions_and_common_target_differs_from_own_goal():
    result = metrics.analyze_records(stopped_records(), [], own_goal=[1., 0., 0.], common_goal=[0., 2., 0.])
    assert result['status'] == 'normally_completed'
    assert result['counts']['actions_completed'] == 0
    assert result['initial_and_endpoint_trajectory'][0]['distance_to_own_goal_m'] == 1.
    assert result['initial_and_endpoint_trajectory'][0]['distance_to_common_fresh_sensor_point_m'] == 2.
    pair = metrics.compare_pair({'cached': result, 'refreshed': deepcopy(result)})
    assert pair['both_normal_and_replay_verified'] is False
    assert pair['refreshed_minus_cached_final_common_point_distance_m'] is None


def test_partial_primitive_and_fresh_unrun_cannot_become_comparative_winner():
    rows = stopped_records()[:-1]
    rows[-1]['data']['selected'] = 'MV_DOWN'
    rows += [{'kind': 'action_started', 'record_id': 'partial',
              'data': {'step': 29, 'native_phase': 'retarget', 'token': 'MV_DOWN'}}]
    result = metrics.analyze_records(rows, [{'category': 'incomplete_record'}],
        own_goal=[1., 0., 0.], common_goal=[0., 2., 0.])
    pair = metrics.compare_pair({'cached': result, 'refreshed': None})
    assert result['counts']['actions_started'] == 1 and result['counts']['actions_completed'] == 0
    assert result['completed_tokens'] == [] and result['started_tokens'] == ['MV_DOWN']
    assert pair['arms']['refreshed']['status'] == 'not_run'
    assert pair['winner'] is None and pair['refreshed_minus_cached_final_common_point_distance_m'] is None


def test_original_baseline_threshold_is_strict_and_not_rebased_to_suffix():
    rows = stopped_records()
    rows.insert(-1, {'kind': 'native_after', 'record_id': 'new-contact', 'data': {
        'step': 29, 'control': 0, 'index': 0, 'time_s': 12.102,
        'contacts': [{'geom_ids': [1, 2], 'normal_force_N': .05},
                     {'geom_ids': [1, 3], 'normal_force_N': .050001}]}})
    result = metrics.analyze_records(rows, [], own_goal=[1., 0., 0.], common_goal=[0., 2., 0.])
    assert result['new_robot_pairs_over_0p05N'] == [[1, 3]]
    assert result['status'] == 'incomplete_or_adverse'
    assert result['all_new_pair_native_observations'][0]['record_id'] == 'new-contact'
