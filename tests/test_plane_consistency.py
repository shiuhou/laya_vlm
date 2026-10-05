from copy import deepcopy
from dataclasses import replace
from math import cos, radians, sin

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, canonical_json
from embodied_runtime.perception.plane_consistency import PlaneConsistencyConfig, compare_planes


def patch(source="front/frame1", *, center=(0., 0., .5), normal=(0., 0., -1.), **changes):
    result = dict(geometry_status="VALID", centroid_base_m=center, normal_base=normal,
                  covariance_m2=(np.eye(3)*4e-6).tolist(), normal_covariance=(np.diag([1., 1., 0.])*radians(1)**2).tolist(),
                  source_frame_id=source, calibration_version=f"cal/{source}", track_id="manual-table-roi",
                  feature_id="plane", capture_sim_time_s=1., capture_monotonic_ns=100,
                  config_revision="p1-geometry-v1", provenance="sensor-derived", metrics={})
    result.update(changes)
    return result


def compare(first=None, second=None, **kwargs):
    return compare_planes(patch() if first is None else first,
                          patch("wrist/frame1") if second is None else second,
                          first_camera_id="front", second_camera_id="wrist",
                          same_plane_assumption="manual table positive-control correspondence; unverified", **kwargs)


def test_opposite_camera_facing_normals_same_plane_are_sign_invariant():
    result = compare(second=patch("wrist/frame1", normal=(0., 0., 1.), center=(.2, .1, .5)))
    assert result["status"] == "COMPATIBLE" and result["compatible"] is True
    metrics = result["metrics"]
    assert metrics["angle_deg"] == 0
    assert metrics["second_normal_sign_flipped"]
    assert metrics["perpendicular_residuals_m"] == (0., 0.)
    assert metrics["centroid_distance_m"] > .2  # Tangential ROI displacement is not separation.
    assert result["semantic_identity_verified"] is False
    assert result["calibration_verified"] is False
    assert result["uncertainty_calibrated"] is False
    assert result["calibrated_confidence"] is None
    assert not result["evidence_merged"]
    with pytest.raises(TypeError):
        result["metrics"]["angle_deg"] = 1
    canonical_json(result)


def test_parallel_offset_planes_compare_both_signed_residuals_and_fail_bound():
    result = compare(second=patch("wrist/frame1", center=(.05, .02, .55)))
    assert result["status"] == "INCOMPATIBLE"
    assert result["compatible"] is False
    assert result["metrics"]["first_plane_second_centroid_signed_residual_m"] == pytest.approx(-.05)
    assert result["metrics"]["second_plane_first_centroid_signed_residual_m"] == pytest.approx(.05)


def test_angled_planes_fail_even_when_centroids_coincide():
    angle = radians(15)
    second = patch("wrist/frame1", normal=(sin(angle), 0., -cos(angle)))
    result = compare(second=second)
    assert result["status"] == "INCOMPATIBLE"
    assert result["metrics"]["angle_deg"] == pytest.approx(15.)
    assert result["metrics"]["max_perpendicular_separation_m"] == 0


def test_zero_reported_covariance_cannot_remove_engineering_floor():
    zero = np.zeros((3, 3)).tolist()
    first, second = patch(covariance_m2=zero, normal_covariance=zero), patch("wrist/frame1", covariance_m2=zero, normal_covariance=zero)
    before = deepcopy((first, second))
    result = compare(first, second)
    assert result["status"] == "COMPATIBLE"
    metrics = result["metrics"]
    assert metrics["position_floor_added_m2"] == (4e-6, 4e-6)
    assert metrics["perpendicular_sigma_bounds_m"] == pytest.approx((.004, .004))
    assert metrics["angular_sigma_bound_deg"] == pytest.approx(2.)
    assert (first, second) == before


def test_high_uncertainty_cannot_make_close_estimates_confidently_compatible():
    result = compare(second=patch("wrist/frame1", covariance_m2=np.eye(3).tolist()))
    assert result["status"] == "UNKNOWN" and result["compatible"] is None
    assert result["reason_codes"] == ("UNCERTAINTY_EXCEEDS_ENGINEERING_RESOLUTION",)
    assert result["metrics"]["max_perpendicular_separation_m"] == 0


def test_separation_and_uncertainty_must_jointly_fit_engineering_bound():
    # Both 19 mm residual and the 8 mm engineering uncertainty alone are under
    # 20 mm, but their sum is not. The measured fits cannot earn COMPATIBLE.
    result = compare(second=patch("wrist/frame1", center=(0., 0., .519)))
    assert result["metrics"]["max_perpendicular_separation_m"] == pytest.approx(.019)
    assert max(result["metrics"]["perpendicular_uncertainty_bounds_m"]) < .020
    assert result["status"] == "UNKNOWN" and result["compatible"] is None


def test_angle_and_uncertainty_must_jointly_fit_engineering_bound():
    angle = radians(8)
    result = compare(second=patch("wrist/frame1", normal=(sin(angle), 0., -cos(angle))))
    assert result["metrics"]["angle_deg"] == pytest.approx(8.)
    assert result["metrics"]["angular_uncertainty_bound_deg"] < 10
    assert result["status"] == "UNKNOWN" and result["compatible"] is None


@pytest.mark.parametrize("status", ["UNKNOWN", "AMBIGUOUS"])
def test_invalid_fit_not_interpreted_as_same_plane(status):
    result = compare(second=patch("wrist/frame1", geometry_status=status, centroid_base_m=None, normal_base=None,
                                  covariance_m2=None, normal_covariance=None))
    assert result["status"] == "UNKNOWN"
    assert result["metrics"] is None
    assert result["reason_codes"] == (f"SECOND_GEOMETRY_{status}",)


def test_temporal_mismatch_refuses_comparison_but_records_both_clocks():
    result = compare(second=patch("wrist/frame1", capture_sim_time_s=1.1, capture_monotonic_ns=300_000_100))
    assert result["status"] == "UNKNOWN"
    assert result["reason_codes"] == ("CAPTURE_TIME_MISMATCH",)
    assert result["capture_wall_skew_s"] == pytest.approx(.3)
    assert result["capture_sim_skew_s"] == pytest.approx(.1)


@pytest.mark.parametrize("first_camera,second_camera,first,second,assumption,reason", [
    ("front", "front", patch(), patch("other"), "table", "DUPLICATE_CAMERA"),
    ("front", "wrist", patch(), patch(), "table", "DUPLICATE_SOURCE"),
    ("front", "wrist", patch(), patch("other"), "", "EXPLICIT_DIAGNOSTIC_ASSUMPTION_REQUIRED"),
    ("front", "wrist", patch(), patch("other", calibration_version=""), "table", "INVALID_PATCH_IDENTITY"),
    ("front", "wrist", patch(), patch("other", provenance="oracle"), "table", "INFORMATION_BOUNDARY"),
    ("front", "wrist", patch(), patch("other", capture_sim_time_s=float("nan")), "table", "INVALID_PATCH_TIMESTAMP"),
    ("front", "wrist", patch(), patch("other", frame="world"), "table", "FRAME_MISMATCH"),
])
def test_sources_assumption_and_frame_must_be_explicit_and_valid(first_camera, second_camera, first, second, assumption, reason):
    with pytest.raises(ProtocolError, match=reason):
        compare_planes(first, second, first_camera_id=first_camera, second_camera_id=second_camera,
                       same_plane_assumption=assumption)


@pytest.mark.parametrize("changes,reason", [
    ({"normal_base": [0., 0., 0.]}, "INVALID_NORMAL"),
    ({"normal_base": [0., 0., 2.]}, "INVALID_NORMAL"),
    ({"centroid_base_m": [0., 0.]}, "INVALID_CENTROID"),
    ({"covariance_m2": -np.eye(3)}, "INVALID_POSITION_COVARIANCE"),
    ({"normal_covariance": [[1, 1, 0], [0, 1, 0], [0, 0, 1]]}, "INVALID_NORMAL_COVARIANCE"),
])
def test_malformed_valid_geometry_is_not_silently_normalized(changes, reason):
    with pytest.raises(ProtocolError, match=reason):
        compare(second=patch("wrist/frame1", **changes))


def test_swap_symmetry_and_explicit_stricter_bound():
    first, second = patch(), patch("wrist/frame1", center=(.1, 0., .505))
    a, b = compare(first, second), compare(second, first)
    assert a["status"] == b["status"] == "COMPATIBLE"
    assert a["metrics"]["angle_deg"] == b["metrics"]["angle_deg"]
    assert a["metrics"]["max_perpendicular_separation_m"] == b["metrics"]["max_perpendicular_separation_m"]
    strict = compare(first, second, config=replace(PlaneConsistencyConfig(), max_perpendicular_separation_m=.004))
    assert strict["status"] == "INCOMPATIBLE"
