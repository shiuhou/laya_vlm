"""Observational paired-surface VERIFY, never an official-success evaluator.

The only supported category prior is coplanarity with a visible fixed reference:
g_closed=0 is derived from that declared relation, not supplied as a scalar. A
fixed-reference support record must describe visible structural attachment;
stationarity alone is not evidence of being fixed. Records are externally
verified, immutable artifact references: this helper does not calibrate sensors
or establish semantic correspondence by geometry.

Default engineering covariances cannot yield SATISFIED. An explicit matching
uncertainty-validation record is necessary, and three distinct, fresh geometry
updates must each satisfy abs(g)+2*sigma_g <= epsilon. Same-frame face/reference
measurements may be correlated; uncertainty components are conservatively added
as standard deviations and are never divided by frame/point/update count.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isfinite, radians, sqrt

import numpy as np

from ..contracts import ProtocolError, content_hash, freeze, thaw


def _require(condition, code):
    if not condition:
        raise ProtocolError(code)


def _name(value):
    return isinstance(value, str) and bool(value)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _array(value, shape, code):
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(code) from exc
    _require(result.shape == shape and np.isfinite(result).all(), code)
    return result


def _cov(value):
    result = _array(value, (3, 3), "INVALID_COVARIANCE")
    _require(np.allclose(result, result.T, rtol=0, atol=1e-12)
             and np.linalg.eigvalsh(result).min() >= -1e-12, "INVALID_COVARIANCE")
    return result


@dataclass(frozen=True)
class EvidenceRecord:
    """Externally validated evidence locator, not a model-generated truth flag."""
    record_id: str
    kind: str
    source_ids: tuple
    artifact_uri: str
    artifact_sha256: str
    condition: str

    def __post_init__(self):
        _require(all(_name(x) for x in (self.record_id, self.kind, self.artifact_uri)), "INVALID_EVIDENCE_RECORD")
        _require(self.condition in ("synthetic_test", "sensor_validation"), "INVALID_EVIDENCE_CONDITION")
        _require(isinstance(self.source_ids, (list, tuple)) and bool(self.source_ids)
                 and all(_name(x) for x in self.source_ids), "EVIDENCE_SOURCES_REQUIRED")
        _require(isinstance(self.artifact_sha256, str) and len(self.artifact_sha256) == 64
                 and all(c in "0123456789abcdef" for c in self.artifact_sha256), "INVALID_EVIDENCE_DIGEST")
        _require(not self.artifact_uri.startswith(("oracle:", "joint:", "success:")), "INFORMATION_BOUNDARY")
        if self.condition == "sensor_validation":
            _require(not self.artifact_uri.startswith("fixture:"), "SYNTHETIC_EVIDENCE_NOT_REAL_VALIDATION")
        object.__setattr__(self, "source_ids", tuple(self.source_ids))


@dataclass(frozen=True)
class SurfaceEvidence:
    episode_id: str
    episode_generation: int
    goal_generation: int
    observation_id: str
    snapshot_id: str
    track_id: str
    track_generation: int
    feature_id: str
    feature_generation: int
    lineage_id: str
    camera_id: str
    calibration_version: str
    source_frame_ids: tuple
    capture_sim_time_s: float
    capture_monotonic_ns: int
    status: str
    position_m: tuple | None
    normal_unit: tuple | None
    position_covariance_m2: tuple | None
    normal_covariance: tuple | None
    covariance_model_id: str
    frame: str = "robot_base"
    provenance: str = "sensor-derived"

    def __post_init__(self):
        for key in ("episode_id", "observation_id", "snapshot_id", "track_id", "feature_id", "lineage_id",
                    "camera_id", "calibration_version", "covariance_model_id"):
            _require(_name(getattr(self, key)), "INVALID_SURFACE_IDENTITY")
        for key in ("episode_generation", "goal_generation", "track_generation", "feature_generation", "capture_monotonic_ns"):
            _require(type(getattr(self, key)) is int and getattr(self, key) >= 0, "INVALID_SURFACE_IDENTITY")
        _require(self.frame == "robot_base" and self.provenance == "sensor-derived", "INFORMATION_BOUNDARY")
        _require(_number(self.capture_sim_time_s) and self.capture_sim_time_s >= 0, "INVALID_CAPTURE_TIME")
        _require(self.status in ("TRACKED", "DEGRADED", "LOST", "AMBIGUOUS", "UNKNOWN"), "INVALID_SURFACE_STATUS")
        _require(isinstance(self.source_frame_ids, (list, tuple)) and bool(self.source_frame_ids)
                 and all(_name(x) for x in self.source_frame_ids)
                 and len(set(self.source_frame_ids)) == len(self.source_frame_ids), "INVALID_SURFACE_SOURCES")
        object.__setattr__(self, "source_frame_ids", tuple(self.source_frame_ids))
        if self.status == "TRACKED":
            position = _array(self.position_m, (3,), "INVALID_SURFACE_POSITION")
            normal = _array(self.normal_unit, (3,), "INVALID_SURFACE_NORMAL")
            _require(abs(np.linalg.norm(normal)-1) <= 1e-6, "INVALID_SURFACE_NORMAL")
            object.__setattr__(self, "position_m", tuple(position.tolist()))
            object.__setattr__(self, "normal_unit", tuple(normal.tolist()))
            object.__setattr__(self, "position_covariance_m2", tuple(map(tuple, _cov(self.position_covariance_m2).tolist())))
            object.__setattr__(self, "normal_covariance", tuple(map(tuple, _cov(self.normal_covariance).tolist())))

    @property
    def context(self):
        return self.episode_id, self.episode_generation, self.goal_generation

    @property
    def lineage(self):
        return self.track_id, self.track_generation, self.feature_id, self.feature_generation, self.lineage_id


@dataclass(frozen=True)
class FlushReferenceEvidence:
    reference_lineage: tuple
    calibration_version: str
    relation: str
    structural_relation: str
    category_prior: EvidenceRecord
    visible_flush_reference: EvidenceRecord
    fixed_structure_support: EvidenceRecord

    def __post_init__(self):
        _require(len(self.reference_lineage) == 5 and _name(self.calibration_version), "INVALID_REFERENCE_LINEAGE")
        _require(self.relation == "coplanar_with_visible_reference", "UNSUPPORTED_CLOSED_OFFSET_RELATION")
        _require(self.structural_relation == "observed_rigid_attachment_to_visible_cabinet_frame",
                 "FIXED_REFERENCE_NEEDS_STRUCTURAL_SUPPORT")
        for evidence, kind in ((self.category_prior, "declared_flush_category_prior"),
                               (self.visible_flush_reference, "visible_flush_reference"),
                               (self.fixed_structure_support, "visible_fixed_structure_support")):
            _require(isinstance(evidence, EvidenceRecord) and evidence.kind == kind, "INVALID_REFERENCE_EVIDENCE")
        _require(len({r.condition for r in (self.category_prior, self.visible_flush_reference,
                                            self.fixed_structure_support)}) == 1, "MIXED_EVIDENCE_CONDITIONS")
        # Reference observations must be cited by both perceptual support records;
        # the lineage record identifies the uninterrupted reference being reused.
        _require(self.reference_lineage[4] in self.visible_flush_reference.source_ids
                 and self.reference_lineage[4] in self.fixed_structure_support.source_ids,
                 "REFERENCE_EVIDENCE_LINEAGE_MISSING")
        _require(all(any(source != self.reference_lineage[4] for source in record.source_ids)
                     for record in (self.visible_flush_reference, self.fixed_structure_support)),
                 "REFERENCE_OBSERVATION_SOURCES_REQUIRED")
        object.__setattr__(self, "reference_lineage", tuple(self.reference_lineage))


@dataclass(frozen=True)
class CalibrationEvidence:
    record: EvidenceRecord
    covariance_model_ids: tuple
    camera_calibration_versions: Mapping
    epsilon_close_m: float
    heldout_split_id: str
    evaluated_samples: int
    measured_coverage: float
    required_coverage: float

    def __post_init__(self):
        _require(isinstance(self.record, EvidenceRecord) and self.record.kind == "relative_gap_uncertainty_validation",
                 "CALIBRATION_RECORD_REQUIRED")
        _require(bool(self.covariance_model_ids) and all(_name(x) for x in self.covariance_model_ids), "INVALID_COVARIANCE_MODEL")
        _require(isinstance(self.camera_calibration_versions, Mapping) and bool(self.camera_calibration_versions)
                 and all(_name(k) and _name(v) for k, v in self.camera_calibration_versions.items()), "INVALID_CALIBRATION")
        _require(_number(self.epsilon_close_m) and self.epsilon_close_m > 0 and _name(self.heldout_split_id)
                 and type(self.evaluated_samples) is int and self.evaluated_samples > 0, "INVALID_CALIBRATION_RECORD")
        _require(_number(self.measured_coverage) and _number(self.required_coverage)
                 and 0 < self.required_coverage <= self.measured_coverage <= 1, "INSUFFICIENT_CALIBRATION_COVERAGE")
        object.__setattr__(self, "covariance_model_ids", tuple(self.covariance_model_ids))
        object.__setattr__(self, "camera_calibration_versions", freeze(self.camera_calibration_versions))


@dataclass(frozen=True)
class VerifyConfig:
    revision: str = "paired-surface-verify-v1"
    epsilon_close_m: float = .010
    max_age_s: float = .2
    max_pair_skew_s: float = .05
    position_sigma_floor_m: float = .002
    normal_sigma_floor_rad: float = radians(1.)

    def __post_init__(self):
        _require(_name(self.revision), "INVALID_VERIFY_CONFIG")
        for key, value in asdict(self).items():
            if key != "revision":
                _require(_number(value) and value > 0, "INVALID_VERIFY_CONFIG")


class RelativeSurfaceVerifier:
    def __init__(self, *, config=VerifyConfig()):
        self.config = config
        self.reset()

    def reset(self):
        self.streak = 0
        self._context = None
        self._lineages = None
        self._calibrations = None
        self._seen = {"face": set(), "reference": set()}
        self._last_captures = None
        self._evidence_hash = None

    def _raw_gap(self, face, reference):
        n = np.asarray(reference.normal_unit)
        delta = np.asarray(face.position_m)-reference.position_m
        terms = []
        effective_positions = []
        for observation in (face, reference):
            cov = _cov(observation.position_covariance_m2)
            cov += np.eye(3)*max(0., self.config.position_sigma_floor_m**2-float(np.linalg.eigvalsh(cov).min()))
            effective_positions.append(cov.tolist())
            terms.append(sqrt(max(0., float(n @ cov @ n))))
        normal_cov = _cov(reference.normal_covariance)
        basis = np.linalg.svd(n[None, :], full_matrices=True)[2][1:].T
        projection = np.eye(3)-np.outer(n, n)
        lift = max(0., self.config.normal_sigma_floor_rad**2-float(np.linalg.eigvalsh(basis.T @ normal_cov @ basis).min()))
        normal_cov = projection @ normal_cov @ projection+lift*projection
        terms.append(sqrt(max(0., float(delta @ normal_cov @ delta))))
        gap = float(n @ delta)
        sigma = sum(terms)
        return dict(gap_m=gap, sigma_g_bound_m=sigma, uncertainty_bound_m=2*sigma,
                    absolute_gap_upper_bound_m=abs(gap)+2*sigma, sigma_components_m=terms,
                    reference_normal_base=n.tolist(), delta_position_base_m=delta.tolist(),
                    effective_position_covariances_m2=effective_positions,
                    effective_reference_normal_covariance=normal_cov.tolist(),
                    correlation_assumption="unknown_correlation_sum_standard_deviations",
                    independent_measurements_assumed=False)

    def update(self, face, reference, *, flush_reference=None, uncertainty=None,
               now_sim_time_s, now_monotonic_ns):
        """Return raw gap plus conditional VERIFY evidence; never route/control.

        The evidence registrar is responsible for validating referenced artifact
        contents/digests before constructing support/calibration records. Merely
        providing uncertainty_calibrated=True in geometry is never sufficient.
        """
        _require(isinstance(face, SurfaceEvidence) and isinstance(reference, SurfaceEvidence), "SURFACE_EVIDENCE_REQUIRED")
        _require(_number(now_sim_time_s) and now_sim_time_s >= 0
                 and type(now_monotonic_ns) is int and now_monotonic_ns >= 0, "INVALID_CLOCK")
        raw = self._raw_gap(face, reference) if face.status == reference.status == "TRACKED" else None
        result = dict(result="UNKNOWN", predicate_id="visible_flush_relative_gap", stage="VERIFY",
                      metrics=raw, g_closed_m=None, consecutive_valid_updates=0, required_updates=3,
                      reason_codes=[], source_snapshot_ids=(face.snapshot_id, reference.snapshot_id),
                      source_observation_ids=(face.observation_id, reference.observation_id),
                      source_frame_ids={"face": face.source_frame_ids, "reference": reference.source_frame_ids},
                      lineages={"face": face.lineage, "reference": reference.lineage},
                      config=asdict(self.config), flush_reference_evidence=thaw(flush_reference),
                      uncertainty_evidence=thaw(uncertainty), condition=None,
                      uncertainty_calibrated=False, calibrated_confidence=None,
                      fixed_reference_inferred_from_stationarity=False)
        reasons = result["reason_codes"]
        if face.track_id == reference.track_id or face.lineage_id == reference.lineage_id:
            reasons.append("DISTINCT_SURFACE_LINEAGES_REQUIRED")
        if face.context != reference.context:
            reasons.append("EPISODE_OR_GOAL_MISMATCH")
        current_context = face.context
        lineages = (face.lineage, reference.lineage)
        calibrations = ((face.camera_id, face.calibration_version), (reference.camera_id, reference.calibration_version))
        if self._context is None:
            self._context, self._lineages, self._calibrations = current_context, lineages, calibrations
        elif (current_context != self._context or lineages != self._lineages or calibrations != self._calibrations):
            reasons.append("CONTEXT_LINEAGE_OR_CALIBRATION_CHANGED_RESET_REQUIRED")
        for name, surface in (("face", face), ("reference", reference)):
            if surface.status != "TRACKED":
                reasons.append(f"{name.upper()}_{surface.status}")
            age, wall_age = now_sim_time_s-surface.capture_sim_time_s, (now_monotonic_ns-surface.capture_monotonic_ns)/1e9
            if age < 0 or wall_age < 0 or age > self.config.max_age_s or wall_age > self.config.max_age_s:
                reasons.append(f"{name.upper()}_GEOMETRY_STALE")
            keys = {f"observation:{surface.observation_id}", f"snapshot:{surface.snapshot_id}",
                    *(f"frame:{f}" for f in surface.source_frame_ids)}
            if keys & self._seen[name]:
                reasons.append(f"{name.upper()}_EVIDENCE_REUSED")
            self._seen[name].update(keys)
        if (abs(face.capture_sim_time_s-reference.capture_sim_time_s) > self.config.max_pair_skew_s
                or abs(face.capture_monotonic_ns-reference.capture_monotonic_ns)/1e9 > self.config.max_pair_skew_s):
            reasons.append("SURFACE_CAPTURE_SKEW")
        captures = ((face.capture_sim_time_s, face.capture_monotonic_ns),
                    (reference.capture_sim_time_s, reference.capture_monotonic_ns))
        if self._last_captures is not None:
            for old, new in zip(self._last_captures, captures):
                if new[0] <= old[0] or new[1] <= old[1]:
                    reasons.append("GEOMETRY_UPDATE_NOT_NEW")
                if new[0]-old[0] > self.config.max_age_s or (new[1]-old[1])/1e9 > self.config.max_age_s:
                    reasons.append("GEOMETRY_CONTINUITY_GAP")
        self._last_captures = captures
        if not isinstance(flush_reference, FlushReferenceEvidence):
            reasons.append("VISIBLE_FLUSH_AND_FIXED_REFERENCE_EVIDENCE_REQUIRED")
        elif (flush_reference.reference_lineage != reference.lineage
              or flush_reference.calibration_version != reference.calibration_version):
            reasons.append("REFERENCE_EVIDENCE_LINEAGE_MISMATCH")
        else:
            result["g_closed_m"] = 0.  # Derived solely from explicit visible coplanarity relation.
            result["condition"] = flush_reference.category_prior.condition
        if not isinstance(uncertainty, CalibrationEvidence):
            reasons.append("UNCERTAINTY_UNCALIBRATED")
        else:
            if (uncertainty.epsilon_close_m != self.config.epsilon_close_m
                    or any(surface.covariance_model_id not in uncertainty.covariance_model_ids
                           or uncertainty.camera_calibration_versions.get(surface.camera_id) != surface.calibration_version
                           for surface in (face, reference))):
                reasons.append("UNCERTAINTY_VALIDATION_SCOPE_MISMATCH")
            elif result["condition"] is not None and result["condition"] != uncertainty.record.condition:
                reasons.append("MIXED_EVIDENCE_CONDITIONS")
            else:
                result["uncertainty_calibrated"] = True
        evidence_hash = content_hash({"flush": thaw(flush_reference), "uncertainty": thaw(uncertainty)})
        if self._evidence_hash is not None and evidence_hash != self._evidence_hash:
            reasons.append("SUPPORT_EVIDENCE_CHANGED")
        self._evidence_hash = evidence_hash
        if reasons:
            self.streak = 0
        elif raw["absolute_gap_upper_bound_m"] <= self.config.epsilon_close_m:
            self.streak += 1
            if self.streak >= 3:
                result["result"] = "SATISFIED"
            else:
                reasons.append("AWAITING_DISTINCT_GEOMETRY_UPDATES")
        else:
            self.streak = 0
            # A confidently outside interval supports NOT_SATISFIED; an interval
            # straddling the tolerance remains UNKNOWN, never false completion.
            if abs(raw["gap_m"])-raw["uncertainty_bound_m"] > self.config.epsilon_close_m:
                result["result"] = "NOT_SATISFIED"
                reasons.append("GAP_OUTSIDE_CLOSED_TOLERANCE")
            else:
                reasons.append("GAP_UNCERTAINTY_OVERLAPS_TOLERANCE")
        result["consecutive_valid_updates"] = self.streak
        return freeze(result)
