from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.coarse_point_probe import (
    admit_point, decision_input, force_pairs, observe_controls, replay_check, contact_rows, control_endpoints,
)
from embodied_runtime.experiments.point_grounding_probe import parse_grounding, generation_audit
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.runtime_core import MOVE


def frame():
    return {'depth_m':np.ones((4,4)), 'intrinsics':np.eye(3), 'camera_to_world':np.eye(4),
            'capture_seq':1, 'capture_sim_time':.5}


def audit():
    return generation_audit([12,99],100,16384,99)


def test_point_admission_uses_containing_pixel_center_not_continuous_point():
    admitted = admit_point(parse_grounding('<box><275><275></box>',4,4), audit(), frame())
    assert admitted['sample_pixel_xy'] == [1,1]
    assert admitted['position_world_m'] == [1.5,1.5,1.]


@pytest.mark.parametrize('raw', [
    '<box>none</box>', '<box><1000><200></box>',
    '<box><200><200></box><box><100><100><300><300></box>',
    '<box><200><200></box><box><300><300></box>',
])
def test_non_single_point_not_salvaged(raw):
    with pytest.raises(ValueError, match='point_admission'):
        admit_point(parse_grounding(raw,4,4), audit(), frame())


@pytest.mark.parametrize('depth', [np.nan, np.inf, .009, 5.001])
def test_invalid_depth_not_clamped(depth):
    f = frame(); f['depth_m'][1,1] = depth
    with pytest.raises(ValueError, match='invalid_depth'):
        admit_point(parse_grounding('<box><275><275></box>',4,4), audit(), f)


@pytest.mark.parametrize('ids', [[12], [12]*255+[99]])
def test_parseable_point_without_eos_or_at_length_limit_not_admitted(ids):
    with pytest.raises(ValueError, match='incomplete_or_length_limited'):
        admit_point(parse_grounding('<box><275><275></box>',4,4), generation_audit(ids,100,16384,99), frame())


def test_no_fabricated_confidence_or_contact_and_canonical_rule_tie_preserved():
    admitted = {'position_world_m':[.02,.02,0.], 'admission':'explicit_fresh_point_admission'}
    proprio = {'tcp_pos_world_m':[0.,0.,0.], 'gripper_width_m':.08, 'gripper_command':'OPEN'}
    view = decision_input(admitted, proprio, frame())
    assert [c.token for c in view.candidates] == [*MOVE, 'STOP']
    assert view.rule_token() == 'MV_FWD'  # unchanged lexical tie on equal X/Y delta
    for name in ('quality.position_covariance_m2','quality.semantic_confidence','quality.semantic_valid',
                 'quality.temporal_consistency_ok','target.velocity_mps','interaction.target_contact',
                 'interaction.holding','progress.remaining_open_mm','target.visible_now'):
        assert view.state.fields[name].value is None
    assert not view.state.privileged and not view.effects.privileged
    assert view.state.fields['quality.geometry_valid'].basis == admitted['admission']


def test_contact_abort_includes_self_contact_but_uses_existing_force_threshold():
    rows = [{'geom_ids':[1,2], 'normal_force_N':.02, 'robot_sides':[True,True]},
            {'geom_ids':[3,4], 'normal_force_N':0., 'robot_sides':[True,False]}]
    assert force_pairs(rows,.01) == {(1,2)}


def test_contact_observer_retains_arm_gripper_self_zero_force_contacts():
    data = [(1,9,.2),(2,8,.1),(1,2,.3),(7,9,4.),(2,10,0.)]
    contacts = [SimpleNamespace(pos=np.zeros(3), dist=-.001) for _ in data]
    w = SimpleNamespace(data=SimpleNamespace(contact=contacts),
        env=SimpleNamespace(sim=SimpleNamespace(model=SimpleNamespace(geom_id2name=lambda g:f'g{g}'))))
    m = SimpleNamespace(world=w, _reset=lambda:None, ids=lambda selector:{1,2}, contacts=lambda:data)
    rows = contact_rows(m)
    assert [r['geom_ids'] for r in rows] == [[1,9],[2,8],[1,2],[2,10]]
    assert rows[-1]['normal_force_N']==0 and rows[2]['robot_sides']==[True,True]


class FakeWorld:
    def __init__(self):
        self.state = np.zeros(2)
        self.data = SimpleNamespace(time=0.)
        self.env = SimpleNamespace(step=self.step, sim=SimpleNamespace(get_state=lambda:self.state.copy()))
        self.obs = {}
    def step(self, command):
        self.state += command
        self.data.time += .05
        return {},0.,False,{}


class Recorder:
    def __init__(self): self.rows=[]
    def record(self, kind, data): self.rows.append((kind,data))


def test_observer_sees_each_control_and_restores_on_exception(monkeypatch):
    import embodied_runtime.experiments.coarse_point_probe as probe
    monkeypatch.setattr(probe,'contact_rows',lambda _:[])
    w, recorder = FakeWorld(), Recorder()
    original = w.env.step
    with pytest.raises(RuntimeError, match='after control'):
        with observe_controls(w,None,recorder,0) as controls:
            w.env.step([1,2]); w.env.step([3,4])
            assert len(controls)==2 and controls[1]['state_after']==[4.,6.]
            raise RuntimeError('after control')
    assert w.env.step == original
    assert [k for k,_ in recorder.rows] == ['control_started','control_observation']*2


def test_replay_checks_partial_atomic_controls_and_rejects_unacknowledged(tmp_path, monkeypatch):
    import embodied_runtime.experiments.coarse_point_probe as probe
    monkeypatch.setattr(probe,'contact_rows',lambda _:[])
    output = tmp_path/'run'
    recorder = RunRecorder(output,{}, {'run_id':'test'})
    w = FakeWorld()
    recorder.record('environment',{'sim_state':w.state.copy()})
    with observe_controls(w,None,recorder,0):
        w.env.step([1,2])
    recorder.close()
    backend_factory = lambda _:SimpleNamespace(world=FakeWorld(),close=lambda:None)
    result = replay_check(output,backend_factory)
    assert result['passed'] and result['controls']==1
    other = tmp_path/'partial'
    recorder = RunRecorder(other,{}, {'run_id':'test2'})
    recorder.record('environment',{'sim_state':[0.,0.]})
    recorder.record('control_started',{'step':0,'control':0,'command':[1,2],'state_before':[0.,0.]})
    recorder.close()
    with pytest.raises(ValueError,match='unacknowledged'):
        replay_check(other,backend_factory)


def test_actual_control_endpoints_do_not_assume_eight_controls():
    def action(step,n,start,end):
        return {'step':step, 'result':{'environment_step_count':n,
            'execution_before':{'sim_time':start}, 'execution_after':{'sim_time':end}}, 'oracle_after':{}}
    actions = [action(0,3,1.,1.15),action(1,5,1.15,1.4)]
    controls = [{'step':0}]*3+[{'step':1}]*5
    result = control_endpoints(actions,controls)
    assert list(result) == [3,8]
    assert result[8]['action_count']==2 and result[8]['cumulative_sim_elapsed_s']==pytest.approx(.4)
    with pytest.raises(ValueError,match='actual control count'):
        control_endpoints(actions,controls[:-1])


def test_expected_checkpoint_is_enforced_before_world_or_model_load():
    import inspect
    from embodied_runtime.experiments.coarse_point_probe import run, EXPECTED_MODEL_CONTENT_ID
    source = inspect.getsource(run)
    assert EXPECTED_MODEL_CONTENT_ID=='4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f'
    assert source.index("identity['content_id'] != EXPECTED_MODEL_CONTENT_ID") < source.index('RecordingBackend.from_task(') < source.index('locator = LocateAnythingWorker(')


def test_comparison_matches_actual_control_endpoints_and_rejects_provenance_change(tmp_path):
    from embodied_runtime.experiments.coarse_point_probe import compare
    def write_arm(name, counts, commit='same'):
        path = tmp_path/name
        recorder = RunRecorder(path,{'condition':name.split('-')[0]},
            {'run_id':name, 'code':{'commit':commit, 'source_sha256':{'probe.py':'same'}}})
        recorder.record('environment', {'sim_state':[0.], 'task_config':{'fixed':1}})
        recorder.record('initial_identity',{'binding':'drawer', 'benchmark_state_id':'same'})
        recorder.manifest_update({'model':{'content_id':'same'}, 'environment_repositories':{'jev':'same'}})
        elapsed = 0.
        for step,n in enumerate(counts):
            for _ in range(n):
                recorder.record('control_observation',{'step':step})
            before = elapsed
            elapsed += n*.05
            recorder.record('action',{'step':step,
                'result':{'environment_step_count':n, 'execution_before':{'sim_time':before},
                          'execution_after':{'sim_time':elapsed}},
                'oracle_after':{'tcp_to_designated_handle_center_m':1.-elapsed,
                                'gripper_to_designated_handle_surface_mm':100.-elapsed}})
        recorder.close()
        return path
    rule, hold = write_arm('rule',[8,8]), write_arm('hold',[16,8])
    result = compare(rule,hold,tmp_path/'comparison.json')
    assert result['common_cumulative_actual_control_counts']==[16]
    matched = result['common_control_endpoints'][0]
    assert matched['sim_elapsed_matched'] and matched['rule']['action_count']==2 and matched['hold']['action_count']==1
    assert matched['tcp_to_handle_distance_rule_minus_hold_m']==0.
    changed = write_arm('hold-changed',[16,8],commit='different')
    with pytest.raises(ValueError,match='provenance mismatch'):
        compare(rule,changed,tmp_path/'bad.json')
