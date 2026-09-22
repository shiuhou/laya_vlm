from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
import sys

import numpy as np
import pytest

from embodied_runtime.decision_interface import project_belief, project_oracle, shared_atomic_candidates
from embodied_runtime.experiments.equivalence import make_pair, paired_inputs
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.experiments.reference_quality import local_reference, preview_probes, summarize
from embodied_runtime.runtime_core import BeliefSnapshot, RuleProvider, _sha256_json


def features(*, remaining=100., gap=20., contact=False, success=False, obstacle=False):
    return {"remaining_open_mm": remaining, "distance_to_moving_geometry_mm": gap,
            "moving_contact": contact, "success": success, "obstacle_contact": obstacle,
            "contacts": [{"hand": "finger", "other": "cabinet", "obstacle": True}] if obstacle else []}


def probe(after, *, pairs=(), steps=8):
    return {"after": after, "obstacle_pairs_seen": list(pairs), "peak_obstacle_force_N": 0.,
            "execution": {"environment_step_count": steps, "execution_before": {"sim_time": .5},
                          "execution_after": {"sim_time": .5 + .05 * steps}},
            "sim_state_after": [after["remaining_open_mm"]]}


def test_passive_stop_progress_is_not_credited_to_chosen_action():
    before = features()
    previews = {"STOP": probe(features(remaining=90.)), "GRASP": probe(features(remaining=90.))}
    result = local_reference(before, previews)
    assert result["candidates"]["GRASP"]["closing_mm"] == 10
    assert result["candidates"]["GRASP"]["closing_vs_stop_mm"] == 0
    assert result["candidates"]["GRASP"]["local_support"] == []
    assert result["reference_tokens"] == []
    assert result["tier"] == "no_resolved_one_step_reference"


@pytest.mark.parametrize("stop_remaining, action_remaining", [(100., 101.), (98., 99.)])
def test_approach_or_contact_does_not_override_absolute_or_stop_relative_regression(stop_remaining, action_remaining):
    previews = {"STOP": probe(features(remaining=stop_remaining)),
                "MV_FWD": probe(features(remaining=action_remaining, gap=0., contact=True))}
    result = local_reference(features(), previews)
    assert result["candidates"]["MV_FWD"]["local_support"] == []
    assert result["reference_tokens"] == []


def test_contact_already_produced_by_stop_is_not_incremental_contact():
    result = local_reference(features(), {
        "STOP": probe(features(contact=True, gap=0.)), "GRASP": probe(features(contact=True, gap=0.))})
    assert result["candidates"]["GRASP"]["local_support"] == []


def test_unresolved_preparation_is_not_labeled_incorrect_or_stop_optimal():
    result = local_reference(features(contact=True, gap=0.), {
        "STOP": probe(features(contact=True, gap=0.)), "RELEASE": probe(features(contact=False, gap=1.))})
    assert result["reference_tokens"] == []
    assert result["candidates"]["RELEASE"]["interpretation"] == "no_local_utility_demonstrated"
    assert "incorrect" not in result["candidates"]["RELEASE"]


def test_terminal_success_and_already_terminal_preservation_are_distinct():
    previews = {"STOP": probe(features(remaining=10.)),
                "MV_FWD": probe(features(remaining=0., success=True), steps=3)}
    new = local_reference(features(remaining=10.), previews)
    assert new["tier"] == "terminal" and new["reference_tokens"] == ["MV_FWD"]
    assert "task_completion" in new["candidates"]["MV_FWD"]["local_support"]
    assert new["candidates"]["MV_FWD"]["equal_horizon_to_stop"] is False
    terminal = local_reference(features(remaining=0., success=True), {
        "STOP": probe(features(remaining=0., success=True), steps=1),
        "MV_FWD": probe(features(remaining=-1., success=True), steps=1)})
    assert terminal["tier"] == "terminal"
    assert terminal["candidates"]["STOP"]["local_support"] == ["terminal_preservation"]
    assert terminal["candidates"]["STOP"]["equal_horizon_to_stop"] is True


def test_missing_duration_is_not_asserted_equal_horizon():
    previews = {"STOP": probe(features()), "GRASP": probe(features())}
    for item in previews.values():
        item.pop("execution")
    result = local_reference(features(), previews)
    assert result["candidates"]["GRASP"]["equal_horizon_to_stop"] is None


def test_obstacle_contact_excludes_even_apparent_completion_and_near_best_is_set_valued():
    previews = {"STOP": probe(features()), "MV_FWD": probe(features(remaining=95.)),
                "MV_LEFT": probe(features(remaining=95.2)),
                "GRASP": probe(features(remaining=0., success=True), pairs=[("finger", "cabinet")])}
    result = local_reference(features(), previews)
    assert result["tier"] == "incremental_closure"
    assert set(result["reference_tokens"]) == {"MV_FWD", "MV_LEFT"}
    assert result["candidates"]["GRASP"]["sampled_obstacle_admissible"] is False


@pytest.mark.parametrize("fail", [False, True])
def test_preview_is_separate_from_provider_inputs_and_restores_backend_commands(monkeypatch, fail):
    world = SimpleNamespace(state=np.array([100.]))
    world.env = SimpleNamespace(sim=SimpleNamespace(get_state=lambda: world.state.copy()))
    world.features = lambda: features(remaining=float(world.state[0]))
    backend = SimpleNamespace(world=world, _grip_cmd=-1., last_execution={"previous": "outcome"})
    starts, rows = [], []
    class Snapshot:
        def __init__(self, source):
            self.state = source.state.copy()
        def restore(self):
            world.state = self.state.copy()
    class Executor:
        def __init__(self, current):
            assert current is backend
        def execute(self, token):
            starts.append((token, backend._grip_cmd, world.state.copy()))
            if token == "GRASP":
                backend._grip_cmd = 1.
            world.state[0] -= 1.
            backend.last_execution = {"peak_obstacle_force_N": 0., "obstacle_pairs_seen": []}
            if fail and token == "GRASP":
                raise RuntimeError("injected execution error")
            return probe(features())["execution"]
    monkeypatch.setitem(sys.modules, "jev_libero.world", SimpleNamespace(Snapshot=Snapshot))
    monkeypatch.setattr("embodied_runtime.experiments.reference_quality.AtomicExecutor", Executor)
    recorder = SimpleNamespace(record=lambda kind, data: rows.append((kind, data)))
    candidates = shared_atomic_candidates()
    before_candidates = [c.canonical() for c in candidates]
    if fail:
        with pytest.raises(RuntimeError, match="injected"):
            preview_probes(backend, candidates, recorder, "physical")
    else:
        result = preview_probes(backend, candidates, recorder, "physical")
        assert result["source_restore_max_error"] == 0
        assert result["stop_replay_max_error"] == 0
        assert [token for token, _, _ in starts] == [c.token for c in candidates] + ["STOP"]
    assert all(grip == -1. and np.array_equal(state, [100.]) for _, grip, state in starts)
    assert np.array_equal(world.state, [100.]) and backend._grip_cmd == -1.
    assert backend.last_execution == {"previous": "outcome"}
    assert before_candidates == [c.canonical() for c in candidates]
    assert all(data["not_supplied_to_model"] for _, data in rows)


def paired_record():
    belief = BeliefSnapshot("ep", 1, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "vision:drawer:position_world_m": [.2, 0., 1.]}, {}, {"instruction": "close the drawer"},
        validity={"drawer": {"geometry_valid": True}})
    perceptual = project_belief(belief, "drawer")
    oracle = project_oracle(perceptual, {"source_id": "physical", "target_position_m": [.2, 0., 1.],
        "position_definition": "moving_collision_geometry_world_aabb_center", "remaining_open_mm": 100.})
    return make_pair(oracle, perceptual, shared_atomic_candidates(), physical={"sim_time": .5,
        "physical_state_id": "physical", "task": "top_drawer", "init_state_id": 0, "seed": 1, "environment_step": 0})


def raw_fixture(tmp_path, *, mutate=None, duplicate=None, missing_probe=False, corrupt_cache=False, obstacle_probe=False):
    pair = paired_record()
    inp = paired_inputs(pair)[0]
    previews = {c.token: probe(features(remaining=95. if c.token == "MV_FWD" else 100.)) for c in inp.candidates}
    if missing_probe:
        previews.pop("RELEASE")
    if obstacle_probe:
        previews["GRASP"] = probe(features(obstacle=True), pairs=[("finger", "cabinet")])
    evaluator = {"physical_state_id": "physical", "not_supplied_to_model": True, "before": features(),
                 "stop_replay_max_error": 0., "source_restore_max_error": 0., **local_reference(features(), previews)}
    if corrupt_cache:
        evaluator["tier"] = "fabricated"
    collection = RunRecorder(tmp_path / "collection", {}, {"run_id": "collection"})
    collection.record("paired_state", pair)
    if duplicate == "pair":
        collection.record("paired_state", pair)
    for token, preview in previews.items():
        data = {"physical_state_id": "physical", "token": token, "not_supplied_to_model": True, **preview}
        collection.record("evaluator_probe", data)
        if duplicate == "probe" and token == "STOP":
            collection.record("evaluator_probe", data)
    collection.record("reference_evaluator", evaluator)
    collection.record("termination", {"reason": "complete"})
    collection.close()
    decision = {"pair_id": pair["pair_id"], "branch": "oracle", "repeat": 0, "provider": "RuleProvider",
        "decision": asdict(RuleProvider().decide(inp)), "presentation_version": "compact-v0.1",
        "model_input_id": _sha256_json({"state": inp.provider_input(), "question": inp.model_questions()}),
        "latency_ms": 1., "choice_allowed": True}
    if mutate:
        decision.update(deepcopy(mutate))
    replay = RunRecorder(tmp_path / "replay", {}, {"run_id": "replay"})
    replay.record("paired_state", pair)
    replay.record("equivalence_decision", decision)
    replay.record("termination", {"reason": "complete"})
    replay.close()
    return collection.output / "episodes.jsonl", replay.output / "episodes.jsonl"


def test_raw_summary_recomputes_and_preserves_physical_evidence(tmp_path):
    paths = raw_fixture(tmp_path)
    result = summarize(*paths)
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["choice"] == "MV_FWD"
    assert row["reference_tokens"] == ["MV_FWD"]
    assert row["chosen_evidence"]["closing_vs_stop_mm"] == 5
    assert row["stop_evidence"]["after"]["remaining_open_mm"] == 100


def test_cached_reference_cannot_override_raw_probes(tmp_path):
    with pytest.raises(ValueError, match="cached evaluator"):
        summarize(*raw_fixture(tmp_path, corrupt_cache=True))


def test_obstacle_pair_tuples_roundtrip_through_raw_json_without_false_integrity_failure(tmp_path):
    result = summarize(*raw_fixture(tmp_path, obstacle_probe=True))
    assert result["rows"][0]["all_local_utilities"]["GRASP"]["sampled_obstacle_admissible"] is False


@pytest.mark.parametrize("duplicate", ["pair", "probe"])
def test_duplicate_raw_observations_are_rejected(tmp_path, duplicate):
    with pytest.raises(ValueError, match="duplicate"):
        summarize(*raw_fixture(tmp_path, duplicate=duplicate))


def test_reference_requires_all_offered_probe_outcomes(tmp_path):
    with pytest.raises(ValueError, match="probe|candidate|complete"):
        summarize(*raw_fixture(tmp_path, missing_probe=True))


@pytest.mark.parametrize("audit", [None, {"available": False}, {"available": True},
                                  {"available": True, "truncated": True}])
def test_laya_reference_requires_available_untruncated_token_audit(tmp_path, audit):
    with pytest.raises(ValueError, match="audit|encoding"):
        summarize(*raw_fixture(tmp_path, mutate={"provider": "LayaProvider", "input_encoding": audit}))


def test_raw_model_input_identity_is_not_inferred_from_snapshot_id(tmp_path):
    with pytest.raises(ValueError, match="model input identity"):
        summarize(*raw_fixture(tmp_path, mutate={"model_input_id": "wrong"}))
