import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments.p1_sam_video_tracking_dev import checked_rgb, temporal_reason, video_builder_options
from embodied_runtime.perception.surface_association import sensor_view_identity


def view():
    return dict(rgb=np.arange(10*12*3, dtype=np.uint8).reshape(10, 12, 3), depth_m=np.ones((10, 12), np.float32),
        intrinsics_K=np.eye(3), T_base_camera=np.eye(4), frame_id='f0', frame_seq=0,
        camera_id='frontview', frame='robot_base', episode_id='e', calibration_version='c',
        capture_sim_time_s=0., capture_monotonic_ns=0)


def test_lossless_recorded_rgb_binding_rejects_changed_source_bytes():
    source = view()
    identity = sensor_view_identity(source)
    rgb = checked_rgb(source, identity)
    assert rgb is source['rgb']
    assert np.array_equal(rgb, source['rgb'])
    source['rgb'][0, 0, 0] ^= 1
    with pytest.raises(ProtocolError, match='identity changed'):
        checked_rgb(source, identity)


def test_explicit_video_condition_and_gap_admission_before_propagation():
    options = video_builder_options()
    assert options == dict(apply_postprocessing=False, vos_optimized=False,
                          hydra_overrides_extra=['++model.multimask_output_for_tracking=false'])
    options['hydra_overrides_extra'].append('bad')
    assert len(video_builder_options()['hydra_overrides_extra']) == 1
    old = sensor_view_identity(view())
    new = dict(old, frame_id='f1', frame_seq=1, capture_sim_time_s=.3, capture_monotonic_ns=300000000)
    assert temporal_reason(new, old) is None
    assert temporal_reason(dict(new, capture_monotonic_ns=300000001), old) == 'FRAME_GAP_EXCEEDS_300MS'
    assert temporal_reason(dict(new, calibration_version='other'), old) == 'SOURCE_DISCONTINUITY'
    assert temporal_reason(dict(new, frame_seq=0), old) == 'CAPTURE_CLOCK_REGRESSION'
