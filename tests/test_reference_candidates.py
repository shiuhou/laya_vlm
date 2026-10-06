"""Reference enumeration does not confer identity or fixedness on geometry."""
import json

import numpy as np

from embodied_runtime.perception.reference_candidates import enumerate_reference_candidates


def sensor_view():
    h, w = 32, 48
    depth = np.full((h, w), .7)
    depth[:, 24:] = .9
    return dict(rgb=np.zeros((h, w, 3), np.uint8), depth_m=depth,
                intrinsics_K=np.array([[240., 0, 23.5], [0, 240., 15.5], [0, 0, 1]]),
                T_base_camera=np.eye(4), frame_id="frame:1", frame_seq=1, camera_id="test",
                frame="robot_base", episode_id="test", calibration_version="synthetic",
                capture_sim_time_s=0., capture_monotonic_ns=1)


def test_all_planes_retained_canonical_but_no_fixed_reference_or_winner():
    result = enumerate_reference_candidates(sensor_view(), [0, 0, 48, 32])
    json.dumps(result, allow_nan=False)
    faces = [c for c in result["candidates"] if c["feature_kind"] == "observed_face"]
    assert len(faces) == len(result["inventory"]["surfaces"]) == 2
    assert faces[0]["geometry"]["support_row_spans"][0][1] == 0
    assert faces[1]["geometry"]["support_row_spans"][0][1] == 24
    assert all(c["geometry_status"] == "PLANE_VALID" for c in faces)
    assert all(c["reference_status"] == "REFERENCE_UNKNOWN" for c in result["candidates"])
    assert all(c["closed_reference_relation"] == "UNKNOWN" for c in result["candidates"])
    assert all(c["fixedness"] == "UNKNOWN" for c in result["candidates"])
    assert result["selected_candidate_id"] is None
    # Image-neighbor planes separated by 20 cm do not form a supported edge.
    assert result["observed_adjacency"] == []
    again = enumerate_reference_candidates(sensor_view(), [0, 0, 48, 32])
    result.pop("stage_timings_s")
    again.pop("stage_timings_s")
    assert result == again


def test_roi_clipped_boundaries_are_finite_observed_pixels_not_physical_edges():
    result = enumerate_reference_candidates(sensor_view(), [0, 0, 20, 32])
    boundaries = [c for c in result["candidates"] if c["feature_kind"] == "observed_support_boundary"]
    assert len(boundaries) == 1
    boundary = boundaries[0]
    assert boundary["physical_edge_identity"] == "UNKNOWN"
    assert boundary["finite_observed_support_only"]
    # Only original support pixels survive; no box centre/intersection vertex.
    assert all(0 <= row < 32 and 0 <= left < right <= 20
               for row, left, right in boundary["geometry"]["support_row_spans"])
    assert "PHYSICAL_EDGE_UNESTABLISHED" in boundary["rejection_reasons"]
    assert result["source"]["search_roi_xyxy"] == [0, 0, 20, 32]
    assert not result["evaluation_labels_used"]


def test_no_support_is_unknown_not_not_visible_or_an_invented_reference():
    view = sensor_view()
    view["depth_m"][:] = np.nan
    result = enumerate_reference_candidates(view, [0, 0, 48, 32])
    assert result["reference_status"] == "REFERENCE_UNKNOWN"
    assert result["candidates"] == []
    assert result["rejection_reason_counts"] == {"NO_OBSERVED_PLANE_SUPPORT": 1}
    assert result["inventory"]["residual_pixels_uv"] == []
