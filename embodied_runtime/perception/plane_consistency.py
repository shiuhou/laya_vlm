"""Cross-view plane comparison under an explicit diagnostic correspondence.

This does not discover or verify that two ROIs are the same object/plane. It
compares independently observed fits in robot_base without merging evidence.
Bounds and covariance floors are engineering assumptions, not calibrated
probabilities, confidence intervals, or proof of camera calibration accuracy.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import acos, degrees, isfinite, radians, sqrt

import numpy as np

from ..contracts import ProtocolError, freeze


def _require(condition, code, detail=""):
    if not condition:
        raise ProtocolError(code, detail)


@dataclass(frozen=True)
class PlaneConsistencyConfig:
    revision: str = "p1-plane-consistency-engineering-v1"
    max_angle_deg: float = 10.
    max_perpendicular_separation_m: float = .020
    position_sigma_floor_m: float = .002
    normal_sigma_floor_deg: float = 1.
    uncertainty_scale: float = 2.
    max_sim_capture_skew_s: float = .05

    def __post_init__(self):
        _require(isinstance(self.revision, str) and self.revision, "INVALID_PLANE_CONFIG")
        for key, value in asdict(self).items():
            if key != "revision":
                _require(isinstance(value, (int, float)) and not isinstance(value, bool)
                         and isfinite(value) and value > 0, "INVALID_PLANE_CONFIG", key)
        _require(self.max_angle_deg <= 90 and self.normal_sigma_floor_deg < 90, "INVALID_PLANE_CONFIG")


def _identity(patch):
    _require(isinstance(patch, Mapping), "INVALID_PATCH")
    names = ("source_frame_id", "calibration_version", "track_id", "feature_id", "config_revision")
    _require(all(isinstance(patch.get(key), str) and patch[key] for key in names), "INVALID_PATCH_IDENTITY")
    sim, wall = patch.get("capture_sim_time_s"), patch.get("capture_monotonic_ns")
    _require(isinstance(sim, (int, float)) and not isinstance(sim, bool) and isfinite(sim) and sim >= 0
             and type(wall) is int and wall >= 0, "INVALID_PATCH_TIMESTAMP")
    _require(patch.get("provenance") == "sensor-derived", "INFORMATION_BOUNDARY")
    _require(patch.get("geometry_status") in ("VALID", "UNKNOWN", "AMBIGUOUS"), "INVALID_GEOMETRY_STATUS")
    # PatchEstimate defines its coordinates as robot_base; an explicitly supplied
    # conflicting frame is rejected rather than silently transformed.
    _require(patch.get("frame", "robot_base") == "robot_base", "FRAME_MISMATCH")
    return {key: patch[key] for key in (*names, "capture_sim_time_s", "capture_monotonic_ns", "geometry_status")}


def _array(value, shape, code):
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(code) from exc
    _require(result.shape == shape and np.isfinite(result).all(), code)
    return result


def _covariance(value, code):
    covariance = _array(value, (3, 3), code)
    _require(np.allclose(covariance, covariance.T, rtol=0, atol=1e-12)
             and np.linalg.eigvalsh(covariance).min() >= -1e-12, code)
    return covariance


def _geometry(patch, config):
    center = _array(patch.get("centroid_base_m"), (3,), "INVALID_CENTROID")
    normal = _array(patch.get("normal_base"), (3,), "INVALID_NORMAL")
    _require(abs(np.linalg.norm(normal)-1) <= 1e-6, "INVALID_NORMAL", "unit normal required")
    position_cov = _covariance(patch.get("covariance_m2"), "INVALID_POSITION_COVARIANCE")
    normal_cov = _covariance(patch.get("normal_covariance"), "INVALID_NORMAL_COVARIANCE")
    # Floor is a PSD lower bound, not N-independent observations to average.
    position_lift = max(0., config.position_sigma_floor_m**2-float(np.linalg.eigvalsh(position_cov).min()))
    effective_position_cov = position_cov+np.eye(3)*position_lift
    tangent = np.eye(3)-np.outer(normal, normal)
    basis = np.linalg.svd(normal[None, :], full_matrices=True)[2][1:].T
    tangent_cov = basis.T @ normal_cov @ basis
    normal_lift = max(0., radians(config.normal_sigma_floor_deg)**2-float(np.linalg.eigvalsh(tangent_cov).min()))
    effective_normal_cov = tangent @ normal_cov @ tangent+normal_lift*tangent
    return center, normal, effective_position_cov, effective_normal_cov, position_lift, normal_lift


def compare_planes(first_patch, second_patch, *, first_camera_id, second_camera_id,
                   same_plane_assumption, config=PlaneConsistencyConfig()):
    """Compare serialized PatchEstimates without target association or fusion.

    Camera IDs and a nonempty diagnostic assumption are mandatory because
    geometry alone cannot supply correspondence. Invalid fits return UNKNOWN;
    malformed identity/geometry and duplicate sources raise ProtocolError.
    """
    _require(all(isinstance(value, str) and value for value in
                 (first_camera_id, second_camera_id, same_plane_assumption)), "EXPLICIT_DIAGNOSTIC_ASSUMPTION_REQUIRED")
    _require(first_camera_id != second_camera_id, "DUPLICATE_CAMERA")
    first, second = _identity(first_patch), _identity(second_patch)
    _require(first["source_frame_id"] != second["source_frame_id"], "DUPLICATE_SOURCE")
    sim_skew = abs(first["capture_sim_time_s"]-second["capture_sim_time_s"])
    wall_skew = abs(first["capture_monotonic_ns"]-second["capture_monotonic_ns"])/1e9
    result = dict(status="UNKNOWN", compatible=None, reason_codes=[], frame="robot_base",
                  first=dict(first, camera_id=first_camera_id), second=dict(second, camera_id=second_camera_id),
                  same_plane_assumption=same_plane_assumption, correspondence_source="explicit_diagnostic_assumption",
                  semantic_identity_verified=False, calibration_verified=False,
                  uncertainty_calibrated=False, calibrated_confidence=None,
                  evidence_merged=False, config=asdict(config),
                  capture_sim_skew_s=sim_skew, capture_wall_skew_s=wall_skew, metrics=None)
    reasons = [f"{name}_GEOMETRY_{identity['geometry_status']}"
               for name, identity in (("FIRST", first), ("SECOND", second)) if identity["geometry_status"] != "VALID"]
    if sim_skew > config.max_sim_capture_skew_s:
        reasons.append("CAPTURE_TIME_MISMATCH")
    if reasons:
        result["reason_codes"] = reasons
        return freeze(result)
    c1, n1, p1, q1, p_lift1, n_lift1 = _geometry(first_patch, config)
    c2, n2, p2, q2, p_lift2, n_lift2 = _geometry(second_patch, config)
    signed_dot = float(np.clip(n1 @ n2, -1., 1.))
    normal_flipped = signed_dot < 0
    aligned_n2 = -n2 if normal_flipped else n2
    angle_deg = degrees(acos(abs(signed_dot)))
    delta = c2-c1
    signed_residuals = (float(n1 @ delta), float(aligned_n2 @ -delta))
    perpendicular = tuple(abs(value) for value in signed_residuals)
    # Unknown cross-camera correlation: triangle bound on standard deviations,
    # not sqrt(sum variances) and not a joint probabilistic confidence interval.
    residual_sigmas = []
    for normal, normal_cov in ((n1, q1), (aligned_n2, q2)):
        components = (normal @ p1 @ normal, normal @ p2 @ normal, delta @ normal_cov @ delta)
        residual_sigmas.append(sum(sqrt(max(0., float(component))) for component in components))
    angular_sigma_deg = degrees(sum(sqrt(max(0., float(np.linalg.eigvalsh(cov).max()))) for cov in (q1, q2)))
    angular_uncertainty_bound = config.uncertainty_scale*angular_sigma_deg
    perpendicular_uncertainty_bounds = tuple(config.uncertainty_scale*value for value in residual_sigmas)
    result["metrics"] = dict(
        normal_signed_dot=signed_dot, second_normal_sign_flipped=normal_flipped,
        first_normal_base=n1.tolist(), second_normal_base=n2.tolist(), aligned_second_normal_base=aligned_n2.tolist(),
        angle_deg=angle_deg, centroid_delta_base_m=delta.tolist(), centroid_distance_m=float(np.linalg.norm(delta)),
        first_plane_second_centroid_signed_residual_m=signed_residuals[0],
        second_plane_first_centroid_signed_residual_m=signed_residuals[1],
        perpendicular_residuals_m=perpendicular, max_perpendicular_separation_m=max(perpendicular),
        effective_position_covariances_m2=(p1.tolist(), p2.tolist()),
        effective_normal_covariances=(q1.tolist(), q2.tolist()),
        position_floor_added_m2=(p_lift1, p_lift2), normal_floor_added_rad2=(n_lift1, n_lift2),
        perpendicular_sigma_bounds_m=tuple(residual_sigmas), angular_sigma_bound_deg=angular_sigma_deg,
        perpendicular_uncertainty_bounds_m=perpendicular_uncertainty_bounds,
        angular_uncertainty_bound_deg=angular_uncertainty_bound,
        uncertainty_combination="sum_of_projected_standard_deviations_unknown_correlation",
    )
    if angle_deg > config.max_angle_deg:
        result["reason_codes"].append("NORMAL_ANGLE_EXCEEDS_ENGINEERING_BOUND")
    if max(perpendicular) > config.max_perpendicular_separation_m:
        result["reason_codes"].append("PERPENDICULAR_SEPARATION_EXCEEDS_ENGINEERING_BOUND")
    if result["reason_codes"]:
        result.update(status="INCOMPATIBLE", compatible=False)
    elif (angle_deg+angular_uncertainty_bound > config.max_angle_deg
          or any(residual+uncertainty > config.max_perpendicular_separation_m
                 for residual, uncertainty in zip(perpendicular, perpendicular_uncertainty_bounds))):
        result["reason_codes"].append("UNCERTAINTY_EXCEEDS_ENGINEERING_RESOLUTION")
    else:
        result.update(status="COMPATIBLE", compatible=True)
    return freeze(result)
