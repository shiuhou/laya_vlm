from dataclasses import replace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.surface_association import (
    associate_point, inventory_surfaces, tracker_seed_rectangle,
)
from embodied_runtime.perception.visual_tracker import TrackerConfig, VisualTracker


def view():
    h, w = 32, 48
    depth = np.full((h, w), .7)
    depth[:, 24:] = .9
    depth[12:16, 10:14] = np.nan
    return dict(rgb=np.zeros((h, w, 3), np.uint8), depth_m=depth,
                intrinsics_K=np.array([[240., 0, 23.5], [0, 240., 15.5], [0, 0, 1]]),
                T_base_camera=np.eye(4), frame_id="frame:1", frame_seq=1, camera_id="test",
                frame="robot_base", episode_id="test", calibration_version="synthetic", capture_sim_time_s=0., capture_monotonic_ns=1)


def anchor(inventory, point):
    return {**inventory.source, "query": "synthetic mechanics fixture, not semantic evidence",
            "response_sha256": "0"*64, "evaluation_labels_used": False,
            "generation_complete": True, "parsed_status": "single_point", "points_xy": [point]}


def test_two_comparable_surfaces_retained_and_exact_pixel_selects_without_largest_fallback():
    frame = view()
    inventory = inventory_surfaces(frame, [0, 0, 48, 32])
    assert len(inventory.surfaces) == 2
    left = associate_point(inventory, anchor(inventory, [5., 8.]))
    right = associate_point(inventory, anchor(inventory, [35., 8.]))
    assert left["status"] == right["status"] == "BOUND_HYPOTHESIS"
    assert left["surface_id"] != right["surface_id"]
    assert left["semantic_identity_verified"] is False
    hole = associate_point(inventory, anchor(inventory, [11., 13.]))
    assert hole["status"] == "UNKNOWN" and hole["surface_id"] is None
    assert inventory.source["coordinate_frame"] == "robot_base"


def test_overlapping_support_and_source_mismatch_cannot_silently_pick_a_winner():
    inventory = inventory_surfaces(view(), [0, 0, 48, 32])
    doubled = replace(inventory, surfaces=(*inventory.surfaces, replace(inventory.surfaces[0], surface_id="overlapping")))
    point = anchor(doubled, [5., 8.])
    assert associate_point(doubled, point)["status"] == "AMBIGUOUS"
    for field in ("frame_id", "rgb_sha256", "camera_id", "calibration_version", "sensor_view_sha256"):
        with pytest.raises(ProtocolError, match="SOURCE_MISMATCH"):
            associate_point(inventory, {**point, field: "changed"})
    with pytest.raises(ProtocolError, match="INFORMATION_BOUNDARY"):
        associate_point(inventory, {**point, "evaluation_labels_used": True})
    assert associate_point(inventory, {**point, "points_xy": [[1, 1], [2, 2]]})["status"] == "UNKNOWN"
    assert associate_point(inventory, {**point, "parsed_status": "mixed"})["status"] == "UNKNOWN"
    different_roi = inventory_surfaces(view(), [0, 0, 24, 32])
    assert different_roi.surfaces[0].surface_id != inventory.surfaces[0].surface_id


def test_sensor_supported_rectangle_stays_in_plane_and_passes_unchanged_tracker_gate():
    frame = view()
    inventory = inventory_surfaces(frame, [0, 0, 48, 32])
    binding = associate_point(inventory, anchor(inventory, [7., 7.]))
    surface = next(s for s in inventory.surfaces if s.surface_id == binding["surface_id"])
    roi = tracker_seed_rectangle(surface, [7., 7.], tracker_config=TrackerConfig())
    assert roi is not None and roi[2] < 24
    tracker = VisualTracker("test")
    tracked = tracker.initialize(frame, roi, query="synthetic geometry fixture", seed_source="semantic_query",
                                 now_sim_time_s=0., now_monotonic_ns=1)
    assert tracked.status == "TRACKED"
    assert tracker_seed_rectangle(surface, [11., 13.], tracker_config=TrackerConfig()) is None


def test_residual_and_undersized_support_survive_inventory():
    frame = view()
    frame["depth_m"][:] = np.nan
    frame["depth_m"][0:2, 0:2] = .5
    inventory = inventory_surfaces(frame, [0, 0, 48, 32])
    assert len(inventory.surfaces) == 0
    assert inventory.residual_mask.sum() == 4
    assert inventory.components[0]["insufficient_support"]
    assert associate_point(inventory, anchor(inventory, [0., 0.]))["status"] == "UNKNOWN"
