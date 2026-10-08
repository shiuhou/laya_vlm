from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_localizer_surface_dev as pipeline
from embodied_runtime.perception.surface_association import sensor_view_identity


def test_recorded_source_is_exact_and_unique(monkeypatch):
    view = dict(rgb=np.zeros((10, 12, 3), np.uint8), depth_m=np.full((10, 12), .7),
                intrinsics_K=np.eye(3), T_base_camera=np.eye(4), frame_id='local',
                canonical_frame_id='episode/camera/1', frame_seq=1, camera_id='camera',
                frame='robot_base', episode_id='episode', calibration_version='v1',
                capture_sim_time_s=1., capture_monotonic_ns=100)
    envelope = SimpleNamespace(payload={'proprio': {'valid': True}})
    frames = [(envelope, [view])]
    monkeypatch.setattr(pipeline, 'replay_frames', lambda _: iter(frames))
    record = dict(recording='unused', source_identity=sensor_view_identity(view))
    assert pipeline.source_frame(record)[0]['frame_id'] == 'episode/camera/1'
    frames.append((envelope, [view]))
    with pytest.raises(ProtocolError, match='exactly one'):
        pipeline.source_frame(record)
    frames[:] = [(envelope, [dict(view, calibration_version='v2')])]
    with pytest.raises(ProtocolError, match='exactly one'):
        pipeline.source_frame(record)
