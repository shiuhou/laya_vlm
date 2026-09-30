"""P0 state-publication/association tests: synthetic evidence, no models/sim."""
from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, canonical_json
from embodied_runtime.fusion import MultiRateFusion, TemporalConfig
from embodied_runtime.state_store import PerceptionStateStore


IDENTITY = dict(track_id="front", track_generation=0, feature_id="patch", feature_generation=0)
TARGET = dict(target_track_id="front", target_track_generation=0,
              feature_id="patch", feature_generation=0)


def store(now=0.):
    state = PerceptionStateStore("ep", fusion=MultiRateFusion(config=TemporalConfig(
        process_noise_mps2=.1, geometry_max_age_s=.3)))
    state.advance_to(now)
    state.register_track(**IDENTITY, calibration_ids={"front_camera": "cal-1"})
    return state


def geometry(state, seq, captured, *, position=None, **updates):
    frame = f"frame-{seq}"
    state.register_frame(frame, "front_camera", seq, "cal-1", captured)
    result = dict(**IDENTITY, source_frame_ids=[frame], camera_calibration_ids={"front_camera": "cal-1"},
                  capture_sim_time_s=captured, frame="robot_base",
                  position_m=[captured, 0., 1.] if position is None else position,
                  position_covariance_m2=(np.eye(3) * 1e-4).tolist(), normal_unit=[0., 0., 1.],
                  normal_covariance=(np.eye(3) * 1e-4).tolist(), visible_patch_ref="blob:patch",
                  edge_margin_m=.03, plane_residual_m=.001, support_ratio=.9,
                  status="TRACKED", reason_codes=[])
    result.update(updates)
    return result


def semantic(seq=0, captured=0., **updates):
    result = dict(request_id=f"request-{seq}", query_generation=0, camera_id="front_camera",
                  frame_seq=seq, calibration_version="cal-1", capture_sim_time_s=captured,
                  boxes_xyxy_px=[[1., 2., 3., 4.]], detection_present=True,
                  calibrated_confidence=None, raw_output_ref="blob:semantic", model_revision="fake",
                  latency_ms=2000.)
    result.update(updates)
    return result


def associate(state, source=0, current=2, **updates):
    state.register_association(f"frame-{source}", f"frame-{current}", **IDENTITY,
                               evidence_id=f"association-{source}-{current}", **updates)


def prepared_late_binding():
    state = store()
    assert state.ingest_geometry(geometry(state, 0, 0., position=[0., 0., 1.]))
    state.advance_to(2.)
    assert state.ingest_geometry(geometry(state, 2, 2., position=[0., 0., 1.]))
    associate(state)
    return state


def test_published_reads_are_immutable_and_do_not_run_fusion():
    state = store()
    input_geometry = geometry(state, 0, 0.)
    assert state.ingest_geometry(input_geometry)
    first = state.publish_snapshot()
    diagnostics = deepcopy(state.fusion.diagnostics())
    frozen = canonical_json(first)
    input_geometry["position_m"][0] = 999
    with pytest.raises(TypeError):
        first["tracks"][0]["position_m"][0] = 4
    with pytest.raises(TypeError):
        first["tracks"][0]["geometry_observation"]["camera_calibration_ids"]["front_camera"] = "other"
    for _ in range(8):
        assert state.read_snapshot() is first
        assert state.publish_snapshot() is first
    assert state.fusion.diagnostics() == diagnostics
    assert canonical_json(first) == frozen
    state.advance_to(.2)
    assert state.read_snapshot() is first
    latest = state.publish_snapshot()
    assert latest["revision"] == first["revision"] + 1
    assert latest["tracks"][0]["geometry_age_s"] == pytest.approx(.2)
    assert first["tracks"][0]["geometry_age_s"] == 0


def test_unpublished_read_and_regressing_advance_fail_explicitly():
    state = store(1.)
    with pytest.raises(ProtocolError, match="SNAPSHOT_UNPUBLISHED"):
        state.read_snapshot()
    for time in (.9, float("nan"), True):
        with pytest.raises(ProtocolError, match="INVALID_REFERENCE_TIME"):
            state.advance_to(time)
    assert state.reference_sim_time_s == 1.


def test_out_of_order_geometry_matches_existing_capture_time_posterior():
    ordered, delayed = store(.3), store(.3)
    for seq in (0, 1, 2):
        assert ordered.ingest_geometry(geometry(ordered, seq, seq / 10))
    for seq in (2, 0, 1):
        assert delayed.ingest_geometry(geometry(delayed, seq, seq / 10))
    a, b = ordered.publish_snapshot()["tracks"][0], delayed.publish_snapshot()["tracks"][0]
    np.testing.assert_allclose(a["position_m"], b["position_m"], atol=1e-12)
    np.testing.assert_allclose(a["position_covariance_m2"], b["position_covariance_m2"], atol=1e-12)
    assert a["geometry_age_s"] == pytest.approx(.1)
    assert a["geometry_observation"]["source_frame_ids"] == ("frame-2",)
    assert b["geometry_observation"]["source_frame_ids"] == ("frame-2",)


def test_late_semantics_bind_without_geometry_refresh_or_probability_invention():
    state = prepared_late_binding()
    before = state.publish_snapshot()
    diagnostics = deepcopy(state.fusion.diagnostics())
    assert state.bind_semantic(semantic(), label="drawer front", **IDENTITY)
    after = state.publish_snapshot()
    a, b = before["tracks"][0], after["tracks"][0]
    assert b["semantic_age_s"] == 2.
    assert b["semantic_capture_sim_time_s"] == 0.
    assert b["last_semantic_binding_sim_time_s"] == 2.
    assert b["semantic_binding"]["calibrated_confidence"] is None
    assert state.fusion.semantic.tracks == {}
    for key in ("position_m", "position_covariance_m2", "geometry_age_s", "geometry_observation", "provenance"):
        assert a[key] == b[key]
    assert state.fusion.diagnostics() == diagnostics
    assert not state.bind_semantic(semantic(), label="drawer front", **IDENTITY)
    assert state.publish_snapshot() is after


@pytest.mark.parametrize("change,reason", [
    ({"frame_seq": 100}, "HISTORY_MISSING"),
    ({"calibration_version": "cal-2"}, "CALIBRATION_MISMATCH"),
    ({"capture_sim_time_s": .1}, "CAPTURE_MISMATCH"),
    ({"calibrated_confidence": 1.}, "UNCALIBRATED_BINDING_ONLY"),
])
def test_invalid_delayed_semantic_results_leave_snapshot_and_geometry_unchanged(change, reason):
    state = prepared_late_binding()
    previous = state.publish_snapshot()
    diagnostics = deepcopy(state.fusion.diagnostics())
    with pytest.raises(ProtocolError, match=reason):
        state.bind_semantic(semantic(**change), label="drawer", **IDENTITY)
    assert state.publish_snapshot() is previous
    assert state.fusion.diagnostics() == diagnostics


def test_ambiguous_missing_or_stale_association_does_not_bind():
    state = prepared_late_binding()
    associate(state, status="AMBIGUOUS")
    with pytest.raises(ProtocolError, match="ASSOCIATION_AMBIGUOUS"):
        state.bind_semantic(semantic(), label="drawer", **IDENTITY)
    associate(state)
    state.advance_to(2.1)
    state.ingest_geometry(geometry(state, 3, 2.1, position=[0., 0., 1.]))
    with pytest.raises(ProtocolError, match="ASSOCIATION_STALE"):
        state.bind_semantic(semantic(), label="drawer", **IDENTITY)
    fresh = store()
    fresh.ingest_geometry(geometry(fresh, 0, 0.))
    with pytest.raises(ProtocolError, match="ASSOCIATION_MISSING"):
        fresh.bind_semantic(semantic(), label="drawer", **IDENTITY)


def test_history_eviction_prevents_late_semantic_revival():
    state = prepared_late_binding()
    state.advance_to(5.01)
    with pytest.raises(ProtocolError, match="HISTORY_MISSING"):
        state.bind_semantic(semantic(), label="drawer", **IDENTITY)


def test_old_snapshot_with_same_lineage_is_valid_but_new_feature_or_stale_geometry_is_not():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    old = state.publish_snapshot()
    state.advance_to(.1)
    state.ingest_geometry(geometry(state, 1, .1))
    new = state.publish_snapshot()
    assert new["snapshot_id"] != old["snapshot_id"]
    assert state.validate_lineage(old["snapshot_id"], **TARGET)["track_id"] == "front"
    state.advance_to(.5)
    with pytest.raises(ProtocolError, match="GEOMETRY_STALE"):
        state.validate_lineage(old["snapshot_id"], **TARGET)
    identity = dict(IDENTITY, feature_generation=1)
    state.register_track(**identity, calibration_ids={"front_camera": "cal-1"})
    with pytest.raises(ProtocolError, match="LINEAGE_MISMATCH"):
        state.validate_lineage(old["snapshot_id"], **TARGET)
    current = state.publish_snapshot()["tracks"][0]
    assert current["position_m"] is None
    assert not current["geometry_valid"]


def test_calibration_change_invalidates_old_snapshot_without_reusing_posterior():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    old = state.publish_snapshot()
    state.register_track(**IDENTITY, calibration_ids={"front_camera": "cal-2"})
    with pytest.raises(ProtocolError, match="CALIBRATION_MISMATCH"):
        state.validate_lineage(old["snapshot_id"], **TARGET)
    assert state.publish_snapshot()["tracks"][0]["position_m"] is None


def test_semantic_identity_change_invalidates_existing_target_proposal():
    state = prepared_late_binding()
    state.bind_semantic(semantic(), label="drawer", **IDENTITY)
    old = state.publish_snapshot()
    state.bind_semantic(semantic(request_id="request-new", query_generation=1), label="door", **IDENTITY)
    with pytest.raises(ProtocolError, match="SEMANTIC_CHANGED"):
        state.validate_lineage(old["snapshot_id"], **TARGET)


def test_repeated_geometry_does_not_count_twice_and_source_reuse_is_rejected():
    state = store()
    observation = geometry(state, 0, 0.)
    assert state.ingest_geometry(observation)
    previous = state.publish_snapshot()
    diagnostics = deepcopy(state.fusion.diagnostics())
    assert not state.ingest_geometry(observation)
    with pytest.raises(ProtocolError, match="GEOMETRY_SOURCE_REUSED"):
        state.ingest_geometry(dict(observation, position_m=[.1, 0., 1.]))
    assert state.publish_snapshot() is previous
    assert state.fusion.diagnostics() == diagnostics


@pytest.mark.parametrize("change,reason", [
    ({"frame": "world"}, "FRAME_MISMATCH"),
    ({"position_m": [1, 2]}, "INVALID_POSITION"),
    ({"normal_unit": [0, 0, 0]}, "INVALID_NORMAL"),
    ({"support_ratio": 0.}, "NORMAL_SUPPORT_MISSING"),
    ({"normal_unit": None, "normal_covariance": None}, "NORMAL_INVALID_REASON_REQUIRED"),
    ({"position_covariance_m2": [[0., 0., 0.]] * 3}, "INVALID_COVARIANCE"),
    ({"camera_calibration_ids": {"front_camera": "cal-2"}}, "CALIBRATION_MISMATCH"),
    ({"feature_generation": 1}, "LINEAGE_MISMATCH"),
])
def test_invalid_geometry_is_rejected_before_fusion(change, reason):
    state = store()
    observation = geometry(state, 0, 0.)
    previous = state.publish_snapshot()
    diagnostics = deepcopy(state.fusion.diagnostics())
    with pytest.raises(ProtocolError, match=reason):
        state.ingest_geometry(dict(observation, **change))
    assert state.publish_snapshot() is previous
    assert state.fusion.diagnostics() == diagnostics


def test_missing_normal_is_explicitly_invalid_without_losing_valid_position():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0., normal_unit=None, normal_covariance=None,
                                  reason_codes=["NORMAL_SUPPORT_MISSING"]))
    current = state.publish_snapshot()["tracks"][0]
    assert current["geometry_valid"]
    assert current["normal_unit"] is None and not current["normal_valid"]


def test_lost_report_retains_last_position_but_invalidates_geometry_and_lineage():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    previous = state.publish_snapshot()
    state.advance_to(.1)
    state.ingest_geometry(geometry(state, 1, .1, status="LOST", position_m=None,
                                  position_covariance_m2=None, normal_unit=None, normal_covariance=None,
                                  reason_codes=["OCCLUDED"]))
    current = state.publish_snapshot()["tracks"][0]
    assert current["position_m"] is not None
    assert current["geometry_age_s"] == pytest.approx(.1)
    assert not current["geometry_valid"] and not current["normal_valid"]
    with pytest.raises(ProtocolError, match="ASSOCIATION_AMBIGUOUS"):
        state.validate_lineage(previous["snapshot_id"], **TARGET)


def test_outlier_does_not_refresh_source_capture_or_normal():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    state.advance_to(.1)
    assert not state.ingest_geometry(geometry(state, 1, .1, position=[100., 0., 1.], normal_unit=[1., 0., 0.]))
    current = state.publish_snapshot()["tracks"][0]
    assert current["last_geometry_capture_sim_time_s"] == 0.
    assert current["geometry_age_s"] == .1
    assert current["normal_unit"] == (0., 0., 1.)


def test_public_provenance_has_explicit_frame_and_no_fabricated_received_time():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    provenance = state.publish_snapshot()["tracks"][0]["provenance"][0]
    assert provenance["frame"] == "robot_base"
    assert provenance["source_kind"] == "sensor-derived"
    assert provenance["source_frame_ids"] == ("frame-0",)
    assert provenance["capture_sim_time_s"] == 0.
    assert "received_wall_time" not in provenance
    assert "position_world_m" not in provenance


def test_legacy_prepopulated_fusion_cannot_be_relabelled_robot_base():
    state = store()
    state.ingest_geometry(geometry(state, 0, 0.))
    with pytest.raises(ProtocolError, match="FUSION_MUST_START_EMPTY"):
        PerceptionStateStore("ep", fusion=state.fusion)
