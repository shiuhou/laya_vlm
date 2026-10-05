from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.rgbd_geometry import (
    FeasibilityEvidence, GeometryConfig, estimate_visible_patch, project_depth,
    voxel_downsample,
)


def scene(h=64, w=96, *, slope_x=0., slope_y=0., z=.7):
    k = np.array([[240., 0, (w-1)/2], [0, 250., (h-1)/2], [0, 0, 1.]])
    v, u = np.indices((h, w))
    depth = z/(1-slope_x*(u-k[0, 2])/k[0, 0]-slope_y*(v-k[1, 2])/k[1, 1])
    return depth, k, np.eye(4)


def estimate(depth=None, k=None, t=None, **kwargs):
    if depth is None:
        depth, k, t = scene()
    h, w = depth.shape
    defaults = dict(roi_xyxy=(0, 0, w, h), source_frame_id="camera:7",
                    calibration_version="camera-v1", track_id="visible-front", feature_id="patch",
                    capture_sim_time_s=1., capture_monotonic_ns=1_000_000_000,
                    config=GeometryConfig(), eef_position_base_m=(0, 0, .5))
    defaults.update(kwargs)
    return estimate_visible_patch(depth, k, t, **defaults)


def test_non_square_projection_and_reprojection_no_axis_or_flip_guessing():
    depth, k, t = scene(h=35, w=71)
    t[:3, 3] = [.4, -.2, .1]
    cloud = project_depth(depth, k, t, source_frame_id="image:3", calibration_version="v1")
    camera_points = (cloud.points_base_m-t[:3, 3]) @ t[:3, :3]
    uvh = camera_points @ k.T
    np.testing.assert_allclose(uvh[:, :2]/uvh[:, 2:3], cloud.pixels_uv, atol=1e-12)
    assert cloud.valid_mask.shape == (35, 71)
    assert cloud.points_base_m[0, 1] < cloud.points_base_m[-1, 1]
    assert cloud.source_frame_id == "image:3"
    with pytest.raises(ValueError):
        cloud.points_base_m.setflags(write=True)


def test_tilted_plane_normal_in_robot_base_faces_camera():
    depth, k, t = scene(slope_x=.15, slope_y=-.1)
    angle = .35
    t[:3, :3] = [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
    t[:3, 3] = [.3, -.1, .2]
    result = estimate(depth, k, t)
    expected = np.array([.15, -.1, -1.])
    expected = t[:3, :3] @ (expected/np.linalg.norm(expected))
    assert result.geometry_status == "VALID"
    np.testing.assert_allclose(result.normal_base, expected, atol=1e-8)
    assert np.dot(result.normal_base, t[:3, 3]-result.centroid_base_m) > 0
    assert result.metrics["plane_rms_m"] < 1e-10
    assert len(result.candidates) > 5


def test_background_component_removed_without_bbox_center_or_oracle_point():
    depth, k, t = scene()
    depth[:, :12] = 1.4
    result = estimate(depth, k, t)
    assert result.geometry_status == "VALID"
    assert result.metrics["component_sizes"][:2] == (64*84, 64*12)
    assert result.centroid_base_m[2] == pytest.approx(.7)
    assert all(candidate.position_base_m[2] == pytest.approx(.7) for candidate in result.candidates)


def test_two_large_components_abstain_instead_of_selecting_convenient_plane():
    depth, k, t = scene()
    depth[:, :48] = 1.2
    result = estimate(depth, k, t)
    assert result.geometry_status == "AMBIGUOUS"
    assert result.reason_codes == ("AMBIGUOUS_DEPTH_COMPONENTS",)
    assert not result.candidates and result.normal_base is None


def test_hole_and_image_edges_erode_candidates_by_tool_and_uncertainty():
    depth, k, t = scene()
    depth[26:38, 40:56] = np.nan
    result = estimate(depth, k, t)
    assert result.geometry_status == "VALID" and len(result.candidates) > 5
    for candidate in result.candidates:
        assert candidate.edge_margin_m >= candidate.required_edge_margin_m
        point = np.array(candidate.position_base_m)
        uvh = k @ point
        u, v = uvh[:2]/uvh[2]
        assert not (40 <= u < 56 and 26 <= v < 38)
        # A contact disk cannot simply bridge the unobserved hole.
        if 40 <= u < 56:
            assert abs(v-31.5)*.7/250 > candidate.required_edge_margin_m


def test_seeded_ransac_outliers_deterministic_and_raw_metrics_preserved():
    depth, k, t = scene(slope_x=.1)
    rng = np.random.default_rng(7)
    noisy = depth.copy()
    indices = rng.choice(depth.size, 150, replace=False)
    noisy.flat[indices] += .01
    a = estimate(noisy, k, t, seed=17)
    b = estimate(noisy, k, t, seed=17)
    assert a.geometry_status == "VALID" and a.to_dict() == b.to_dict()
    assert a.metrics["plane_support_ratio"] < 1
    assert a.metrics["same_frame_evidence_group"] == "camera:7"
    assert a.capture_sim_time_s == 1.0
    assert a.source_roi_xyxy == (0, 0, 96, 64)


def test_tiny_normal_noise_does_not_exchange_grid_axes_and_reuse_point_ids():
    d1, k, t = scene(slope_x=.000001, slope_y=.000002)
    d2, _, _ = scene(slope_x=.000002, slope_y=.000001)
    a, b = estimate(d1, k, t), estimate(d2, k, t)
    assert a.metrics["grid_chart"] == b.metrics["grid_chart"] == "base_x"
    pa = {point.point_id: point.position_base_m for point in a.candidates}
    pb = {point.point_id: point.position_base_m for point in b.candidates}
    shared = pa.keys() & pb.keys()
    assert len(shared) > 5
    assert max(np.linalg.norm(np.asarray(pa[key])-pb[key]) for key in shared) < 1e-5


def test_covariance_floor_never_averages_away_and_uncalibrated_is_explicit():
    result = estimate()
    floor = np.asarray(GeometryConfig().calibration_covariance_floor_m2)
    covariance = np.asarray(result.covariance_m2)
    assert np.linalg.eigvalsh(covariance-floor).min() >= -1e-12
    for candidate in result.candidates:
        assert np.linalg.eigvalsh(np.asarray(candidate.covariance_m2)-floor).min() >= -1e-12
        assert not candidate.uncertainty_calibrated
        assert candidate.usable_status == "UNKNOWN"
        assert "UNCALIBRATED_UNCERTAINTY" in candidate.reason_codes
        assert candidate.visible_clearance_m is None
    assert np.linalg.eigvalsh(result.normal_covariance).max() >= GeometryConfig().normal_calibration_sigma_rad**2


def test_position_covariance_uses_jacobian_and_camera_rotation():
    depth, k, t = scene(h=7, w=9)
    k[0, 1] = 4.0  # calibrated skew
    cloud = project_depth(depth, k, t, source_frame_id="f", calibration_version="v")
    u, v = cloud.pixels_uv[2]
    z = depth[v, u]
    inv = np.linalg.inv(k)
    jacobian = np.column_stack((z*inv[:, 0], z*inv[:, 1], inv @ [u, v, 1]))
    cfg = GeometryConfig()
    expected = jacobian @ np.diag([cfg.pixel_sigma_px**2]*2+[cfg.depth_sigma_m**2]) @ jacobian.T + np.asarray(cfg.calibration_covariance_floor_m2)
    np.testing.assert_allclose(cloud.covariance_m2[2], expected)


def test_narrow_degenerate_and_invalid_depth_fail_closed():
    depth, k, t = scene()
    empty = estimate(np.full_like(depth, np.nan), k, t)
    assert empty.geometry_status == "UNKNOWN" and not empty.candidates
    line = np.full_like(depth, np.nan)
    line[32] = .7
    result = estimate(line, k, t, config=replace(GeometryConfig(), min_depth_valid_ratio=.001))
    assert result.geometry_status == "UNKNOWN" and not result.candidates
    assert result.reason_codes[0] in {"PLANE_DEGENERATE", "INSUFFICIENT_VOXEL_SUPPORT"}


def test_small_visible_patch_is_not_an_automatic_usable_contact():
    depth, k, t = scene(h=10, w=10)
    result = estimate(depth, k, t)
    assert result.geometry_status in {"VALID", "UNKNOWN"}
    assert not result.candidates


def test_feasibility_and_calibration_are_independent_gates():
    evidence = FeasibilityEvidence(True, True, True, "synthetic-validator", ("synthetic-evidence",))
    uncalibrated = estimate(feasibility=lambda candidate: evidence)
    assert all(c.usable_status == "UNKNOWN" for c in uncalibrated.candidates)
    cfg = replace(GeometryConfig(), uncertainty_calibrated=True, covariance_model_id="synthetic-calibration-fixture")
    passing = estimate(config=cfg, feasibility=lambda candidate: evidence)
    assert all(c.usable_status == "USABLE" for c in passing.candidates)
    blocked = estimate(config=cfg, feasibility=lambda candidate: replace(evidence, swept_clear=False, reason_codes=("OBSERVED_COLLISION",)))
    assert all(c.usable_status == "BLOCKED" for c in blocked.candidates)
    assert len(passing.candidates) == len(blocked.candidates) == len(uncalibrated.candidates)


def test_covariance_too_large_prevents_points_but_keeps_metrics():
    cfg = replace(GeometryConfig(), max_position_sigma_m=.001)
    result = estimate(config=cfg)
    assert result.geometry_status == "UNKNOWN"
    assert result.reason_codes == ("POSITION_UNCERTAINTY_TOO_LARGE",)
    assert result.metrics["position_sigma_m"] > cfg.max_position_sigma_m


def test_robot_mask_is_explicit_and_blocks_masked_region():
    depth, k, t = scene()
    mask = np.zeros(depth.shape, dtype=bool)
    mask[:, :10] = True
    result = estimate(depth, k, t, robot_self_mask=mask,
                      robot_self_mask_source_ids=("declared-robot-model", "capture-proprio"))
    assert result.metrics["robot_self_excluded_count"] == 640
    assert result.metrics["selected_component_count"] == 64*86
    with pytest.raises(ProtocolError, match="robot self mask requires"):
        estimate(depth, k, t, robot_self_mask=mask)


def test_voxel_caps_are_deterministic_and_input_immutable():
    points = np.random.default_rng(1).uniform(-1, 1, (300, 3))
    first = voxel_downsample(points, voxel_m=.01, max_points=17)
    second = voxel_downsample(points[::-1], voxel_m=.01, max_points=17)
    assert len(first) == 17
    np.testing.assert_allclose(first, second)
    assert not first.flags.writeable


def test_strict_prospective_config_and_unknown_fields():
    path = Path(__file__).parents[1]/"configs/p1_geometry.json"
    config = GeometryConfig.load(path)
    assert config == GeometryConfig()
    with pytest.raises(ProtocolError):
        GeometryConfig.from_mapping({**config.to_dict(), "task_name": "drawer"})
    with pytest.raises(ProtocolError):
        replace(config, calibration_covariance_floor_m2=((0, 0, 0),)*3)


@pytest.mark.parametrize("mutation", ["depth_dtype", "negative_fx", "reflection", "bad_roi"])
def test_bad_sensor_geometry_is_rejected_not_guessed(mutation):
    depth, k, t = scene()
    kwargs = {}
    if mutation == "depth_dtype":
        depth = (depth*1000).astype(np.uint16)
    if mutation == "negative_fx":
        k[0, 0] = -240
    if mutation == "reflection":
        t[1, 1] = -1
    if mutation == "bad_roi":
        kwargs["roi_xyxy"] = (-1, 0, 96, 64)
    with pytest.raises(ProtocolError):
        estimate(depth, k, t, **kwargs)
