from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.render_measurement_diagnosis import (
    CACHE_FIELDS,CONTEXT_INVARIANTS,array_hash,cache_hashes,check_context_invariants,compare_frames,projected,witness_comparison)


def frame():
    return {'rgb':np.zeros((5,5,3),dtype=np.uint8),'depth_m':np.ones((5,5),dtype=np.float32),
            'intrinsics':np.eye(3),'camera_to_world':np.eye(4)}


def test_exact_frame_gate_detects_dtype_and_single_bit_changes():
    original=frame();other=frame()
    assert all(compare_frames(original,other)['array_exact'].values())
    other['depth_m']=other['depth_m'].astype(np.float64)
    assert not compare_frames(original,other)['array_exact']['depth_m']
    other=frame();other['rgb'][2,2,1]=1
    result=compare_frames(original,other)
    assert result['rgb_different_pixels']==1 and not result['array_exact']['rgb']
    assert array_hash(np.array([0.]))!=array_hash(np.array([-0.]))


def test_cache_integrity_detects_geometry_change_with_unchanged_joint_state():
    data=SimpleNamespace(time=1.,**{key:np.zeros(3) for key in CACHE_FIELDS})
    before=cache_hashes(data);data.geom_xpos[0]=1e-12;after=cache_hashes(data)
    assert before['qpos']==after['qpos'] and before['geom_xpos']!=after['geom_xpos']


def test_all_registered_neighbors_retained_without_best_pixel_selection():
    native=frame();zero=frame();zero['depth_m'][1,2]=.5
    result=witness_comparison(native,zero,[(2,2)])[0]
    assert len(result['all_3x3_pixels'])==9
    assert result['all_3x3_pixels'][4]['pixel_xy']==[2,2]
    assert result['all_3x3_pixels'][4]['zero_minus_native_depth_m']==0
    assert result['all_3x3_pixels'][1]['zero_minus_native_depth_m']==-.5


def test_projected_vertices_use_declared_camera_transform_and_reject_behind_camera():
    t=np.eye(4);t[:3,3]=[1,2,3]
    k=np.array([[4,0,10],[0,4,20],[0,0,1]])
    np.testing.assert_allclose(projected([[3,4,7]],k,t),[[12,22]])
    with pytest.raises(ValueError,match='camera plane'):projected([[1,2,2]],k,t)


def test_sampling_control_rejects_other_context_changes():
    native={key:0 for key in CONTEXT_INVARIANTS};zero=dict(native)
    native['context_actual_offSamples']=4;zero['context_actual_offSamples']=0
    check_context_invariants(native,zero)
    zero['geomgroup']=[1,1,1,0,0,0]
    with pytest.raises(RuntimeError,match='Non-sampling'):check_context_invariants(native,zero)
