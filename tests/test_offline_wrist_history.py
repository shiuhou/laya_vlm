from copy import deepcopy

import pytest

from embodied_runtime.experiments import offline_wrist_history as probe


def sensor_row():
    return {'global_control':0,'step':0,'control':0,'before_time_s':1.,
        'baseline_force_N':[1.,2.,3.],'baseline_torque_Nm':[0.,0.,0.],
        'after':[{'time_s':1.+(i+1)*.002,'force_N':[1.,2.,3.],'torque_Nm':[0.,0.,0.]} for i in range(25)]}


def test_same_baseline_transient_peak_and_endpoint_arithmetic():
    row=sensor_row();row['after'][7]['force_N']=[4.,6.,3.];row['after'][-1]['force_N']=[2.,2.,3.]
    row['after'][4]['torque_Nm']=[0.,0.,2.];row['after'][-1]['torque_Nm']=[0.,0.,1.]
    f=probe.sensor_features(row)
    assert f['endpoint_force_change_N']==1. and f['temporal_force_change_N']==5.
    assert f['endpoint_torque_change_Nm']==1. and f['temporal_torque_change_Nm']==2.
    assert set(f)==probe.FEATURE_KEYS


def test_sensor_only_function_rejects_gold_and_unregistered_cadence():
    row=sensor_row();row['contacts']=[]
    with pytest.raises(ValueError,match='schema'):probe.sensor_features(row)
    row=sensor_row();row['after'][0]['gold']='contact'
    with pytest.raises(ValueError,match='unexpected'):probe.sensor_features(row)
    row=sensor_row();row['after'][0]['time_s']+=.001
    with pytest.raises(ValueError,match='cadence'):probe.sensor_features(row)


def test_pairwise_rank_auc_direction_ties_and_undefined_cohort():
    assert probe.auroc([2.,3.],[0.,1.])==1.
    assert probe.auroc([0.,1.],[2.,3.])==0.
    assert probe.auroc([1.,1.],[1.,1.])==.5
    assert probe.negative_rank(1.,[0.,1.,1.,2.])==.5
    assert probe.auroc([], [1.]) is None and probe.auroc([1.],[]) is None


def test_temporal_monotonicity_does_not_imply_auc_improvement():
    assert probe.auroc([2.],[1.])==1.
    assert probe.auroc([3.],[4.])==0.
    assert 3.>=2. and 4.>=1.


def geometry():return {k:{'ids':v} for k,v in {'robot':[0,1,2],'gripper':[1,2],'arm':[0],'drawer':[10]}.items()}


def contact(a,b,f):return {'geom_ids':[a,b],'normal_force_N':f}


def test_strict_threshold_gripper_arm_external_and_self_separation():
    for force in (0.,1.):
        r=probe.contact_membership([contact(1,10,force)],geometry())
        assert not r['gripper'] and r['raw_external_rows']==1
    r=probe.contact_membership([contact(1,10,1.01),contact(0,20,2.),contact(1,2,2.)],geometry())
    assert r['gripper'] and r['arm'] and r['self'] and r['gripper_drawer']
    assert probe.cohort(r['gripper'],r['arm'],r['self'])=='self_contact_present'
    assert probe.cohort(True,False,False)=='gripper_only'
    assert probe.cohort(False,True,False)=='arm_only'
    assert probe.cohort(True,True,False)=='gripper_and_arm'
    assert probe.cohort(False,False,False)=='no_robot_scene_above_1N'


def test_distribution_and_observed_range_overlap_are_descriptive():
    comparison=probe.compare([.5,3.],[0.,1.,2.])
    assert comparison['positive_values_within_negative_observed_range']==1
    assert comparison['negative_values_within_positive_observed_range']==2
    assert comparison['positive']['median']==1.75
    assert probe.distribution([])['median'] is None
