import numpy as np
from embodied_runtime.experiments import p1_box_role as role


def test_geometry_domain_changes_without_clipping_mask_or_rechecking_prompt(monkeypatch):
    captured={}
    class Patch:
        def to_dict(self):return {'marker':'unchanged-core'}
    def core(depth,k,t,**kwargs):captured.update(depth=depth.copy(),**kwargs);return Patch()
    monkeypatch.setattr(role,'estimate_visible_patch',core)
    native=np.array([[True,True],[False,True]])
    depth=np.ones((2,2));view=dict(depth_m=depth,intrinsics_K=np.eye(3),T_base_camera=np.eye(4),
        calibration_version='v',capture_sim_time_s=1.,capture_monotonic_ns=2)
    src=dict(condition='C2',ordinal=0,source_identity={'frame_id':'frame'},box_xyxy=[0,0,1,1])
    role.evaluate_native(view,{'eef_position_base_m':[0,0,0]},native,src,[1,0,2,2])
    assert captured['roi_xyxy']==[1,0,2,2]
    assert np.array_equal(captured['depth_availability_mask'],native)
    assert captured['depth'][0,0]==1 and np.isnan(captured['depth'][1,0])
    assert np.isfinite(depth).all() and captured['seed']==0


def test_factorial_contributions_and_nonmonotonic_effects():
    t=[dict(init_index=0,HH=True,HO=False,OH=True,OO=False),
       dict(init_index=1,HH=True,HO=True,OH=True,OO=False)]
    a=role.attribution(t)
    assert a['prompt_contribution_frames']==.5 and a['domain_contribution_frames']==1.5
    assert a['interaction_frames']==-1 and a['priority']=='separate semantic BOX from geometry search domain'
    assert role.contrast(t,'HO','OH')['losses']==[0]
