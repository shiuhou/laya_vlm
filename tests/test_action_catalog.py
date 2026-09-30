from dataclasses import replace
from math import pi

import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.control.action_catalog import ACTION_IDS, CATALOG, action_spec
from embodied_runtime.control.local_candidates import (
    ContextIdentity, HardEvidence, build_candidate_set,
)


def identity():
    return ContextIdentity("episode", 1, 2, "intent", 3, "front", 4, "patch", 5, ("camera-v1",))


def candidates(*, effects=None, evidence=None):
    allow = HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), ("fixture",), "synthetic")
    return build_candidate_set(
        candidate_set_id="set", identity=identity(), source_snapshot_id="snapshot-1",
        hard_evidence={action: allow for action in ACTION_IDS} if evidence is None else evidence,
        generated_monotonic_ns=100, proposal_deadline_monotonic_ns=1_200_000_100,
        geometric_effects=effects,
    )


def test_exact_robot_base_catalog_without_aliases():
    assert ACTION_IDS == (
        "X-40", "X-10", "X-03", "X+03", "X+10", "X+40",
        "Y-40", "Y-10", "Y-03", "Y+03", "Y+10", "Y+40",
        "Z-40", "Z-10", "Z-03", "Z+03", "Z+10", "Z+40",
        "RX-10", "RX+10", "RY-10", "RY+10", "RZ-10", "RZ+10",
        "OPEN", "CLOSE", "HOLD",
    )
    assert all(spec.reference_frame == "robot_base" for spec in CATALOG)
    assert action_spec("Y-03").nominal_delta == (0, -.003, 0)
    assert action_spec("RZ+10").nominal_delta == (0, 0, pi / 18)
    with pytest.raises(ValueError):
        action_spec("GRASP")


def test_soft_negative_progress_does_not_filter_or_reorder():
    original = candidates()
    bad = candidates(effects={action: {"progress_m": -100.0} for action in ACTION_IDS})
    assert original.allowed_ids == bad.allowed_ids == ACTION_IDS
    assert bad.presentation_order == ACTION_IDS
    assert len(bad.candidates) == 27
    assert bad.candidate_hash != original.candidate_hash


def test_missing_hard_evidence_is_unknown_and_retained():
    blocked = HardEvidence("BLOCKED", ("OBSERVED_COLLISION",), ("depth-sweep",), "sensor-derived")
    pool = candidates(evidence={"X+40": blocked})
    assert len(pool.candidates) == 27 and not pool.allowed_ids
    assert pool.candidate("X+40").execution_status == "BLOCKED"
    assert pool.candidate("HOLD").execution_status == "UNKNOWN"


def test_hard_reason_cannot_be_utility_or_unsubstantiated_permission():
    with pytest.raises(ProtocolError):
        HardEvidence("BLOCKED", ("NOT_USEFUL",), ("model",), "synthetic")
    with pytest.raises(ProtocolError):
        HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), ("missing",), "unknown")
    with pytest.raises(ProtocolError):
        HardEvidence("ALLOWED", ("GEOMETRY_STALE",), ("fixture",), "synthetic")


def test_hash_excludes_log_time_but_binds_semantics_and_deadline():
    pool = candidates()
    assert replace(pool, generated_monotonic_ns=101).candidate_hash == pool.candidate_hash
    for changed in (
        replace(pool, source_snapshot_id="snapshot-2"),
        replace(pool, identity=replace(pool.identity, feature_generation=6)),
        replace(pool, proposal_deadline_monotonic_ns=2_000_000_000),
        replace(pool, identity=replace(pool.identity, calibration_versions=("camera-v2",))),
    ):
        assert changed.candidate_hash != pool.candidate_hash


def test_canonical_effect_mapping_and_deep_immutability():
    effect = {"nested": {"position": [1.0, 2.0]}, "unknown": None}
    pool = candidates(effects={"HOLD": effect})
    equal = candidates(effects={"HOLD": {"unknown": None, "nested": {"position": [1.0, 2.0]}}})
    assert pool.candidate_hash == equal.candidate_hash
    effect["nested"]["position"][0] = 99
    assert pool.candidate("HOLD").geometric_effect_estimate["nested"]["position"][0] == 1
    with pytest.raises(TypeError):
        pool.candidate("HOLD").geometric_effect_estimate["x"] = 0


def test_no_pruning_reordering_catalog_change_or_nan():
    pool = candidates()
    with pytest.raises(ProtocolError):
        replace(pool, candidates=pool.candidates[:-1])
    with pytest.raises(ProtocolError):
        replace(pool, candidates=tuple(reversed(pool.candidates)))
    altered = replace(pool.candidates[0], spec=replace(pool.candidates[0].spec, nominal_delta=(-.5, 0, 0)))
    with pytest.raises(ProtocolError):
        replace(pool, candidates=(altered, *pool.candidates[1:]))
    with pytest.raises((ProtocolError, ValueError)):
        candidates(effects={"HOLD": {"progress": float("nan")}})


def test_all_status_changes_affect_hash():
    pool = candidates()
    evidence = {c.id: c.hard_evidence for c in pool.candidates}
    evidence["X+03"] = HardEvidence("UNKNOWN", ("SPACE_UNKNOWN",), ("unobserved-space",), "sensor-derived")
    changed = candidates(evidence=evidence)
    assert changed.candidate_hash != pool.candidate_hash
    assert changed.allowed_ids == tuple(action for action in ACTION_IDS if action != "X+03")
