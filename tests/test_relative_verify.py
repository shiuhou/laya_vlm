"""Synthetic VERIFY logic only: these records are not real sensor calibration."""
from dataclasses import replace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, canonical_json
from embodied_runtime.perception.relative_verify import (
    CalibrationEvidence, EvidenceRecord, FlushReferenceEvidence,
    RelativeSurfaceVerifier, SurfaceEvidence, VerifyConfig,
)


def surface(role, step, *, gap=.001, **changes):
    value = SurfaceEvidence(
        "episode", 1, 1, f"{role}/observation/{step}", f"snapshot/{step}", role, 1,
        "visible-plane", 1, f"lineage/{role}", "camera", "cal1", (f"frame/{step}",),
        step*.1, step*100_000_000, "TRACKED", (0., 0., gap if role == "face" else 0.),
        (0., 0., 1.), tuple(map(tuple, (np.eye(3)*4e-6).tolist())),
        tuple(map(tuple, (np.diag([1., 1., 0.])*np.deg2rad(1)**2).tolist())), "synthetic-covariance-v1",
    )
    return replace(value, **changes)


def record(name, kind, *, sources=("recorded-observation", "lineage/reference")):
    return EvidenceRecord(name, kind, sources, f"fixture://{name}.json", "a"*64, "synthetic_test")


def support():
    return FlushReferenceEvidence(
        surface("reference", 0).lineage, "cal1", "coplanar_with_visible_reference",
        "observed_rigid_attachment_to_visible_cabinet_frame",
        record("prior", "declared_flush_category_prior"),
        record("flush", "visible_flush_reference"),
        record("attachment", "visible_fixed_structure_support"),
    )


def calibration():
    return CalibrationEvidence(record("synthetic-uncertainty", "relative_gap_uncertainty_validation"),
                               ("synthetic-covariance-v1",), {"camera": "cal1"}, .010,
                               "synthetic-contract-test-only", 100, .98, .95)


def update(verifier, step, *, face=None, reference=None, flush=None, uncertainty=None, **kwargs):
    return verifier.update(surface("face", step) if face is None else face,
                           surface("reference", step) if reference is None else reference,
                           flush_reference=support() if flush is None else flush,
                           uncertainty=calibration() if uncertainty is None else uncertainty,
                           now_sim_time_s=step*.1, now_monotonic_ns=step*100_000_000, **kwargs)


def test_three_distinct_fresh_updates_required_and_no_frame_count_uncertainty_reduction():
    verifier = RelativeSurfaceVerifier()
    results = [update(verifier, i) for i in range(3)]
    assert [r["result"] for r in results] == ["UNKNOWN", "UNKNOWN", "SATISFIED"]
    assert [r["consecutive_valid_updates"] for r in results] == [1, 2, 3]
    for result in results:
        assert result["g_closed_m"] == 0.
        assert result["metrics"]["gap_m"] == pytest.approx(.001)
        assert result["metrics"]["sigma_g_bound_m"] == pytest.approx(.004)
        assert result["metrics"]["absolute_gap_upper_bound_m"] == pytest.approx(.009)
        assert result["condition"] == "synthetic_test"
        assert result["calibrated_confidence"] is None
        assert not result["fixed_reference_inferred_from_stationarity"]
        assert not result["metrics"]["independent_measurements_assumed"]
        canonical_json(result)
    with pytest.raises(TypeError):
        results[-1]["metrics"]["gap_m"] = 0


def test_uncalibrated_defaults_preserve_raw_gap_but_never_verify():
    verifier = RelativeSurfaceVerifier()
    for i in range(4):
        result = verifier.update(surface("face", i), surface("reference", i),
                                 flush_reference=support(), now_sim_time_s=i*.1, now_monotonic_ns=i*100_000_000)
        assert result["result"] == "UNKNOWN" and result["consecutive_valid_updates"] == 0
        assert result["metrics"]["gap_m"] == pytest.approx(.001)
        assert "UNCERTAINTY_UNCALIBRATED" in result["reason_codes"]


def test_magic_calibration_or_closed_flags_do_not_substitute_for_evidence_records():
    verifier = RelativeSurfaceVerifier()
    result = verifier.update(surface("face", 0), surface("reference", 0),
                             flush_reference={"g_closed": 0., "fixed": True},
                             uncertainty={"uncertainty_calibrated": True}, now_sim_time_s=0., now_monotonic_ns=0)
    assert result["result"] == "UNKNOWN"
    assert result["g_closed_m"] is None
    assert not result["uncertainty_calibrated"]


def test_stationarity_is_not_fixed_structure_support_and_nonzero_offset_is_not_accepted():
    evidence = support()
    with pytest.raises(ProtocolError, match="FIXED_REFERENCE_NEEDS_STRUCTURAL_SUPPORT"):
        replace(evidence, structural_relation="stationary_for_three_frames")
    with pytest.raises(ProtocolError, match="UNSUPPORTED_CLOSED_OFFSET_RELATION"):
        replace(evidence, relation="hardcoded_joint_offset")
    with pytest.raises(ProtocolError, match="REFERENCE_EVIDENCE_LINEAGE_MISSING"):
        replace(evidence, fixed_structure_support=record("unrelated", "visible_fixed_structure_support", sources=("another",)))
    with pytest.raises(ProtocolError, match="REFERENCE_OBSERVATION_SOURCES_REQUIRED"):
        replace(evidence, fixed_structure_support=record("id-only", "visible_fixed_structure_support", sources=("lineage/reference",)))


@pytest.mark.parametrize("which", ["face", "reference"])
@pytest.mark.parametrize("status", ["LOST", "AMBIGUOUS", "DEGRADED"])
def test_invalid_surface_resets_streak_and_requires_three_new_updates(which, status):
    verifier = RelativeSurfaceVerifier()
    assert update(verifier, 0)["consecutive_valid_updates"] == 1
    assert update(verifier, 1)["consecutive_valid_updates"] == 2
    args = {which: surface(which, 2, status=status, position_m=None, normal_unit=None,
                           position_covariance_m2=None, normal_covariance=None)}
    invalid = update(verifier, 2, **args)
    assert invalid["result"] == "UNKNOWN" and invalid["consecutive_valid_updates"] == 0
    assert invalid["metrics"] is None
    assert [update(verifier, i)["result"] for i in (3, 4, 5)] == ["UNKNOWN", "UNKNOWN", "SATISFIED"]


def test_reusing_one_surface_frame_or_observation_resets_streak():
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    update(verifier, 1)
    result = update(verifier, 2, reference=surface("reference", 2, source_frame_ids=("frame/1",)))
    assert result["result"] == "UNKNOWN" and result["consecutive_valid_updates"] == 0
    assert "REFERENCE_EVIDENCE_REUSED" in result["reason_codes"]
    result = update(verifier, 3, face=surface("face", 3, observation_id="face/observation/0"))
    assert "FACE_EVIDENCE_REUSED" in result["reason_codes"]
    result = update(verifier, 4, face=surface("face", 4, snapshot_id="snapshot/0"))
    assert "FACE_EVIDENCE_REUSED" in result["reason_codes"]


def test_new_frame_ids_at_same_capture_time_cannot_manufacture_three_updates():
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    result = update(verifier, 1, face=surface("face", 1, capture_sim_time_s=0.),
                    reference=surface("reference", 1, capture_sim_time_s=0.))
    assert result["result"] == "UNKNOWN" and "GEOMETRY_UPDATE_NOT_NEW" in result["reason_codes"]


@pytest.mark.parametrize("changes", [
    {"track_generation": 2}, {"feature_generation": 2}, {"lineage_id": "other-lineage"},
    {"calibration_version": "cal2"}, {"episode_id": "other-episode"}, {"goal_generation": 2},
])
def test_lineage_calibration_or_context_change_cannot_extend_old_streak(changes):
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    update(verifier, 1)
    result = update(verifier, 2, face=surface("face", 2, **changes))
    assert result["result"] == "UNKNOWN" and result["consecutive_valid_updates"] == 0
    assert "CONTEXT_LINEAGE_OR_CALIBRATION_CHANGED_RESET_REQUIRED" in result["reason_codes"]


def test_explicit_reset_discards_streak():
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    update(verifier, 1)
    verifier.reset()
    assert update(verifier, 2)["consecutive_valid_updates"] == 1


def test_distinct_track_and_independent_lineage_are_both_required():
    for changes in ({"track_id": "reference"}, {"lineage_id": "lineage/reference"}):
        result = update(RelativeSurfaceVerifier(), 0, face=surface("face", 0, **changes))
        assert result["result"] == "UNKNOWN"
        assert "DISTINCT_SURFACE_LINEAGES_REQUIRED" in result["reason_codes"]


def test_stale_pair_or_long_observation_gap_resets_streak():
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    result = verifier.update(surface("face", 1), surface("reference", 1), flush_reference=support(),
                             uncertainty=calibration(), now_sim_time_s=.5, now_monotonic_ns=500_000_000)
    assert "FACE_GEOMETRY_STALE" in result["reason_codes"]
    assert "REFERENCE_GEOMETRY_STALE" in result["reason_codes"]
    assert result["metrics"] is not None
    verifier = RelativeSurfaceVerifier()
    update(verifier, 0)
    assert "GEOMETRY_CONTINUITY_GAP" in update(verifier, 4)["reason_codes"]


def test_uncertainty_of_reference_normal_includes_tangential_lever_arm():
    verifier = RelativeSurfaceVerifier()
    result = update(verifier, 0, face=surface("face", 0, position_m=(.5, 0., .001)))
    assert result["metrics"]["sigma_components_m"][2] == pytest.approx(.5*np.deg2rad(1))
    assert result["result"] == "UNKNOWN"
    assert "GAP_UNCERTAINTY_OVERLAPS_TOLERANCE" in result["reason_codes"]


def test_error_plus_uncertainty_not_each_alone_must_fit_epsilon():
    result = update(RelativeSurfaceVerifier(), 0, face=surface("face", 0, gap=.009))
    assert result["metrics"]["gap_m"] < .010
    assert result["metrics"]["uncertainty_bound_m"] < .010
    assert result["metrics"]["absolute_gap_upper_bound_m"] > .010
    assert result["result"] == "UNKNOWN"


def test_stationary_but_far_from_flush_is_not_satisfied():
    verifier = RelativeSurfaceVerifier()
    results = [update(verifier, i, face=surface("face", i, gap=.05)) for i in range(3)]
    assert all(result["result"] == "NOT_SATISFIED" for result in results)
    assert all(result["consecutive_valid_updates"] == 0 for result in results)


@pytest.mark.parametrize("changes", [
    {"epsilon_close_m": .02}, {"camera_calibration_versions": {"camera": "another"}},
    {"covariance_model_ids": ("another",)},
])
def test_calibration_record_must_cover_current_threshold_model_and_camera(changes):
    result = update(RelativeSurfaceVerifier(), 0, uncertainty=replace(calibration(), **changes))
    assert result["result"] == "UNKNOWN"
    assert "UNCERTAINTY_VALIDATION_SCOPE_MISMATCH" in result["reason_codes"]


def test_no_provenance_oracle_artifact_or_coverage_shortcut():
    with pytest.raises(ProtocolError, match="INFORMATION_BOUNDARY"):
        surface("face", 0, provenance="oracle_sim")
    with pytest.raises(ProtocolError, match="INFORMATION_BOUNDARY"):
        replace(record("x", "visible_flush_reference"), artifact_uri="joint://drawer-position")
    with pytest.raises(ProtocolError, match="INSUFFICIENT_CALIBRATION_COVERAGE"):
        replace(calibration(), measured_coverage=.8)
    with pytest.raises(ProtocolError, match="SYNTHETIC_EVIDENCE_NOT_REAL_VALIDATION"):
        replace(record("x", "visible_flush_reference"), condition="sensor_validation")


def test_geometry_floors_are_retained_with_zero_reported_covariance():
    zero = tuple(map(tuple, np.zeros((3, 3))))
    result = update(RelativeSurfaceVerifier(config=VerifyConfig()), 0,
                    face=surface("face", 0, position_covariance_m2=zero),
                    reference=surface("reference", 0, position_covariance_m2=zero, normal_covariance=zero))
    assert result["metrics"]["sigma_g_bound_m"] == pytest.approx(.004)
