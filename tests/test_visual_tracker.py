"""Synthetic RGB-D association evidence, not object identity or task success."""
from dataclasses import replace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.visual_tracker import TrackerConfig, VisualTracker


ROI = (60., 44., 84., 68.)
TEXTURE = np.random.default_rng(7).integers(20, 240, (24, 24, 3), dtype=np.uint8)


def frame(seq=0, *, dx=0, dy=0, roi=ROI, texture=TEXTURE, depth=.5, scale=1.,
          transform=None, calibration="cal1", camera="camera", occlude=None, duplicate=None):
    rgb = np.full((120, 160, 3), 30, dtype=np.uint8)
    distance = np.full((120, 160), .7, dtype=np.float32)
    center = (np.asarray(roi[:2])+np.asarray(roi[2:]))/2+np.array([dx, dy])
    size = np.rint((np.asarray(roi[2:])-np.asarray(roi[:2]))*scale).astype(int)
    x, y = np.rint(center-size/2).astype(int)
    yy = np.minimum((np.arange(size[1])/size[1]*texture.shape[0]).astype(int), texture.shape[0]-1)
    xx = np.minimum((np.arange(size[0])/size[0]*texture.shape[1]).astype(int), texture.shape[1]-1)
    patch = texture[yy[:, None], xx[None, :]]
    rgb[y:y+size[1], x:x+size[0]] = patch
    distance[y:y+size[1], x:x+size[0]] = depth
    if duplicate is not None:
        other_x, other_y = duplicate
        rgb[other_y:other_y+size[1], other_x:other_x+size[0]] = patch
        distance[other_y:other_y+size[1], other_x:other_x+size[0]] = depth
    if occlude is not None:
        rgb[y:y+size[1], x:x+size[0]] = 120
        distance[y:y+size[1], x:x+size[0]] = occlude
    return dict(rgb=rgb, depth_m=distance, intrinsics_K=np.array([[120., 0., 80.], [0., 120., 60.], [0., 0., 1.]]),
                T_base_camera=np.eye(4) if transform is None else transform, camera_id=camera,
                frame_seq=seq, frame_id=f"frame-{seq}", calibration_version=calibration,
                capture_sim_time_s=seq/10, capture_monotonic_ns=seq*100_000_000,
                frame="robot_base", episode_id="episode")


def initialize(tracker=None, source=None, roi=ROI):
    tracker = tracker or VisualTracker("episode")
    source = source or frame()
    result = tracker.initialize(source, roi, query="visible drawer front", seed_source="manual_seed",
                                now_sim_time_s=source["capture_sim_time_s"],
                                now_monotonic_ns=source["capture_monotonic_ns"])
    assert result.status == "TRACKED"
    return tracker, result


def update(tracker, source):
    return tracker.update(source, now_sim_time_s=source["capture_sim_time_s"],
                          now_monotonic_ns=source["capture_monotonic_ns"])


def semantic(**updates):
    result = dict(request_id="sem1", query_generation=1, camera_id="camera", frame_seq=0,
                  calibration_version="cal1", capture_sim_time_s=0., boxes_xyxy_px=[ROI],
                  detection_present=True, calibrated_confidence=None, raw_output_ref="blob:raw",
                  model_revision="synthetic-semantic", latency_ms=2000.)
    result.update(updates)
    return result


def test_translation_tracks_image_and_metric_position_with_stable_generations():
    tracker, first = initialize()
    for seq, dx, dy in ((1, 4, 2), (2, 8, 4), (3, 10, 6)):
        result = update(tracker, frame(seq, dx=dx, dy=dy))
        assert result.status == "TRACKED", result
        assert result.track_generation == first.track_generation
        assert result.feature_generation == first.feature_generation
        center = (np.array(result.roi_xyxy_px[:2])+np.array(result.roi_xyxy_px[2:]))/2
        np.testing.assert_allclose(center, [72+dx, 56+dy], atol=1.)
        np.testing.assert_allclose(np.array(result.position_base_m)-first.position_base_m,
                                   [dx*.5/120, dy*.5/120, 0.], atol=.005)
        assert result.calibrated_confidence is None
        assert not result.semantic_identity_verified
        assert result.seed_source == "manual_seed"
    with pytest.raises(TypeError):
        result.metrics["appearance_error"] = 0


def test_camera_motion_uses_capture_pose_and_base_association_not_pixel_stasis():
    tracker, first = initialize()
    transform = np.eye(4)
    transform[0, 3] = .025
    result = update(tracker, frame(1, dx=-6, transform=transform))
    assert result.status == "TRACKED", result
    np.testing.assert_allclose(result.position_base_m, first.position_base_m, atol=.005)
    assert result.metrics["projected_center_px"][0] == pytest.approx(66.)


def test_modest_perspective_scale_change_remains_observation_supported():
    # A spatially smooth texture avoids inventing invariance to arbitrary random
    # per-pixel texture under nearest-neighbor resize/aliasing.
    texture = np.rint(sum(np.roll(np.roll(TEXTURE.astype(float), x, 0), y, 1)
                         for x in (-1, 0, 1) for y in (-1, 0, 1))/9).astype(np.uint8)
    tracker, _ = initialize(source=frame(texture=texture))
    result = update(tracker, frame(1, texture=texture, depth=.48, scale=1.05))
    assert result.status == "TRACKED", result
    assert result.position_base_m[2] == pytest.approx(.48, abs=1e-6)
    assert result.metrics["depth_support_ratio"] >= .75


def test_large_aliasing_error_is_rejected_instead_of_relaxing_appearance_gate():
    tracker, _ = initialize()
    result = update(tracker, frame(1, depth=.48, scale=1.05))
    assert result.status == "LOST"
    assert result.reason_codes == ("APPEARANCE_MISMATCH",)


@pytest.mark.parametrize("occlusion", [float("nan"), 0., .2])
def test_occlusion_fails_closed_and_reappearance_requires_new_seed(occlusion):
    tracker, first = initialize()
    result = update(tracker, frame(1, occlude=occlusion))
    assert result.status in ("LOST", "AMBIGUOUS")
    assert result.position_base_m is None
    recovered_image = frame(2)
    not_reacquired = update(tracker, recovered_image)
    assert not_reacquired.status == "LOST"
    assert not_reacquired.reason_codes == ("RESEED_REQUIRED",)
    _, seeded = initialize(tracker, recovered_image)
    assert seeded.track_generation > first.track_generation


def test_two_equally_plausible_similar_features_are_ambiguous_not_nearest_winner():
    roi = (66., 50., 78., 62.)
    texture = np.random.default_rng(2).integers(20, 240, (12, 12, 3), dtype=np.uint8)
    tracker, _ = initialize(source=frame(roi=roi, texture=texture), roi=roi)
    # Both are inside depth/base-motion gates around the previous projected point.
    result = update(tracker, frame(1, roi=roi, texture=texture, dx=-10, duplicate=(76, 50)))
    assert result.status == "AMBIGUOUS", result
    assert result.reason_codes == ("COMPETING_APPEARANCE_MATCHES",)
    assert result.position_base_m is None


@pytest.mark.parametrize("updates,reason", [
    ({"calibration": "cal2"}, "CALIBRATION_CHANGED_RESEED_REQUIRED"),
    ({"camera": "wrist"}, "CAMERA_CHANGED_RESEED_REQUIRED"),
])
def test_camera_or_calibration_change_breaks_lineage(updates, reason):
    tracker, _ = initialize()
    result = update(tracker, frame(1, **updates))
    assert result.status == "LOST" and result.reason_codes == (reason,)


def test_age_and_unobserved_gap_do_not_extrapolate_geometry():
    tracker, _ = initialize()
    result = tracker.update(frame(1), now_sim_time_s=.5, now_monotonic_ns=500_000_000)
    assert result.status == "LOST" and result.reason_codes == ("FRAME_STALE",)
    tracker, _ = initialize()
    result = update(tracker, frame(4))
    assert result.status == "LOST" and result.reason_codes == ("TRACKING_GAP",)
    assert result.position_base_m is None


def test_duplicate_frame_is_idempotent_but_changed_bytes_or_old_arrival_rejected():
    tracker, first = initialize()
    assert update(tracker, frame()) is first
    changed = frame()
    changed["rgb"][0, 0] = 0
    with pytest.raises(ProtocolError, match="FRAME_ID_CONFLICT"):
        update(tracker, changed)
    update(tracker, frame(1))
    old = frame()
    with pytest.raises(ProtocolError, match="FRAME_STALE"):
        tracker.update(old, now_sim_time_s=.1, now_monotonic_ns=100_000_000)


def test_late_semantics_bind_original_frame_to_current_track_without_geometry_refresh():
    tracker, first = initialize()
    tracker.register_semantic_request("sem1", source_frame_id=first.frame_id, query="drawer front",
                                      query_generation=1, deadline_monotonic_ns=3_000_000_000)
    for i in range(1, 21):
        last = update(tracker, frame(i))
        assert last.status == "TRACKED"
    before = tracker.current
    binding = tracker.bind_semantic(semantic(), now_monotonic_ns=2_000_000_000)
    assert binding["source_capture_sim_time_s"] == 0
    assert binding["current_frame_id"] == "frame-20"
    assert binding["calibrated_confidence"] is None
    assert not binding["semantic_identity_verified"]
    assert tracker.current is before  # No depth refit, new geometry or refreshed timestamp.
    assert tracker.bind_semantic(semantic(), now_monotonic_ns=2_000_000_000) is binding
    fresh = update(tracker, frame(21))
    assert fresh.semantic_binding == binding


@pytest.mark.parametrize("updates,reason", [
    ({"calibration_version": "bad"}, "CALIBRATION_CHANGED"),
    ({"frame_seq": 7}, "SOURCE_MISMATCH"),
    ({"query_generation": 2}, "QUERY_GENERATION_MISMATCH"),
    ({"calibrated_confidence": 1.}, "UNCALIBRATED_BINDING_ONLY"),
    ({"boxes_xyxy_px": [(0., 0., 10., 10.)]}, "SEMANTIC_ROI_MISMATCH"),
    ({"boxes_xyxy_px": [ROI, ROI]}, "SEMANTIC_ASSOCIATION_AMBIGUOUS"),
    ({"boxes_xyxy_px": [(0., 0., 500., 500.)]}, "INVALID_SEMANTIC_BOX"),
    ({"detection_present": False}, "DETECTION_ABSENT"),
])
def test_semantic_mismatch_does_not_change_geometry_or_binding(updates, reason):
    tracker, first = initialize()
    tracker.register_semantic_request("sem1", source_frame_id=first.frame_id, query="drawer front",
                                      query_generation=1, deadline_monotonic_ns=1_000_000_000)
    with pytest.raises(ProtocolError, match=reason):
        tracker.bind_semantic(semantic(**updates), now_monotonic_ns=0)
    assert tracker.current is first
    assert update(tracker, frame(1)).semantic_binding is None


def test_semantic_deadline_history_gap_and_reset_cannot_revive_old_identity():
    tracker, first = initialize()
    tracker.register_semantic_request("sem1", source_frame_id=first.frame_id, query="drawer front",
                                      query_generation=1, deadline_monotonic_ns=100_000_000)
    with pytest.raises(ProtocolError, match="PROPOSAL_EXPIRED"):
        tracker.bind_semantic(semantic(), now_monotonic_ns=100_000_000)
    tracker, first = initialize(VisualTracker("episode", config=replace(TrackerConfig(), max_history_frames=2)))
    tracker.register_semantic_request("sem1", source_frame_id=first.frame_id, query="drawer front",
                                      query_generation=1, deadline_monotonic_ns=1_000_000_000)
    update(tracker, frame(1))
    update(tracker, frame(2))
    with pytest.raises(ProtocolError, match="HISTORY_MISSING"):
        tracker.bind_semantic(semantic(), now_monotonic_ns=200_000_000)
    tracker.reset("new-episode")
    with pytest.raises(ProtocolError, match="REQUEST_CANCELLED"):
        tracker.bind_semantic(semantic(), now_monotonic_ns=0)
    with pytest.raises(ProtocolError, match="WRONG_EPISODE"):
        update(tracker, frame(3))


def test_reseed_generation_rejects_semantics_from_broken_chain():
    tracker, first = initialize()
    tracker.register_semantic_request("sem1", source_frame_id=first.frame_id, query="drawer front",
                                      query_generation=1, deadline_monotonic_ns=1_000_000_000)
    update(tracker, frame(1, occlude=0.))
    initialize(tracker, frame(2))
    with pytest.raises(ProtocolError, match="LINEAGE_BROKEN"):
        tracker.bind_semantic(semantic(), now_monotonic_ns=200_000_000)


def test_new_query_prevents_late_old_query_from_overwriting_current_binding():
    tracker, first = initialize()
    for request_id, generation in (("sem1", 1), ("sem2", 2)):
        tracker.register_semantic_request(request_id, source_frame_id=first.frame_id, query="drawer front",
                                          query_generation=generation, deadline_monotonic_ns=1_000_000_000)
    with pytest.raises(ProtocolError, match="QUERY_GENERATION_STALE"):
        tracker.bind_semantic(semantic(), now_monotonic_ns=0)


def test_wall_gap_alone_breaks_continuity_even_when_simulator_clock_pauses():
    tracker, _ = initialize()
    source = frame(1)
    source["capture_sim_time_s"] = 0.
    source["capture_monotonic_ns"] = 1_000_000_000
    result = update(tracker, source)
    assert result.status == "LOST" and result.reason_codes == ("TRACKING_GAP",)


def test_bad_normal_or_camera_matrices_are_not_silently_used():
    source = frame()
    source["T_base_camera"][0, 0] = -1
    tracker = VisualTracker("episode")
    with pytest.raises(ProtocolError, match="INVALID_CALIBRATION"):
        initialize(tracker, source)
    assert tracker.current is None
