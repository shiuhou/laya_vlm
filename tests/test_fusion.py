import numpy as np

from embodied_runtime.fusion import (
    ConstantVelocityFusion3D,
    PositionMeasurement,
    SemanticEvidenceFusion,
)


def test_delayed_measurement_replay_and_age():
    f = ConstantVelocityFusion3D(lag_s=1.0, process_noise_mps2=0.1)
    r = np.eye(3) * 1e-4
    assert f.ingest(PositionMeasurement("depth", 1, 0.0, np.array([0., 0., 1.]), r), reference_time=0.0)
    assert f.ingest(PositionMeasurement("depth", 3, 0.2, np.array([0.2, 0., 1.]), r), reference_time=0.2)
    assert f.ingest(PositionMeasurement("depth", 2, 0.1, np.array([0.1, 0., 1.]), r), reference_time=0.2)
    state = f.estimate(0.3)
    assert state is not None and state.age_s >= 0.0
    assert f.stats.replay_count >= 3

def test_semantic_decay_and_sequence_gate():
    s = SemanticEvidenceFusion(half_life_s=0.5)
    assert s.ingest("drawer", {"drawer": .9, "unknown": .1}, capture_time=0.0, source_seq=1)
    assert not s.ingest("drawer", {"drawer": .1}, capture_time=0.1, source_seq=1)
    fresh = s.distribution("drawer", reference_time=.1)
    stale = s.distribution("drawer", reference_time=2.0)
    assert fresh["drawer"] > fresh["unknown"]
    assert stale["unknown"] > 0
