"""Reference-specific contracts; model-free and independent of installed Jev."""
from types import SimpleNamespace
import sys

import numpy as np
import pytest

from embodied_runtime.adapters.libero import LiberoWorldBackend
from embodied_runtime.adapters.physics_preview import PhysicsPreviewCandidateBuilder
from embodied_runtime.runtime import Runtime
from embodied_runtime.runtime_core import BeliefSnapshot, Candidate, FakeBackend, RuleProvider
from embodied_runtime.experiments import privileged_reference as ref


def features(**extra):
    return {"qpos_m": -.15, "remaining_open_mm": 150.,
            "distance_to_moving_geometry_mm": 40., "moving_contact": False,
            "obstacle_contact": False, "finger_gap_mm": 70.,
            "success": False, **extra}


def prediction(**extra):
    return {"after": features(), "closing_mm": 0., "geometry_approach_mm": 2.,
            "peak_obstacle_force_N": 0., "obstacle_pairs_seen": [],
            "steps": 8, "sim_state_after": [0., 1.], **extra}


def belief(candidates=()):
    return BeliefSnapshot("test", 1, 0., {}, {}, {}, candidates)


def test_native_mapping_keeps_union_without_ranking_or_synthetic_fallback(monkeypatch):
    predictions = {"x+40mm": prediction(closing_mm=5.), "y-3mm": prediction(closing_mm=1.),
                   "close": prediction(geometry_approach_mm=0.)}
    def contracts(before, received, collision_aware, task_config):
        assert received is predictions and collision_aware and task_config == {"test": True}
        return {"advance_target": {"y-3mm": received["y-3mm"]},
                "approach_target": {"x+40mm": received["x+40mm"]}}, {"close": "no witnessed goal effect"}
    monkeypatch.setitem(sys.modules, "jev_libero.policy", SimpleNamespace(contracts=contracts))
    world = SimpleNamespace(config={"test": True}, predict_all=lambda grip: (features(), predictions))
    builder = PhysicsPreviewCandidateBuilder(world, action_map={n: n for n in predictions})
    result = builder.build(belief())
    assert [c.token for c in result if c.feasible] == ["x+40mm", "y-3mm"]
    assert result[-1].reason_codes == ("no witnessed goal effect",)
    monkeypatch.setitem(sys.modules, "jev_libero.policy", SimpleNamespace(contracts=lambda *a, **kw: ({}, {})))
    empty = builder.build(belief())
    assert not any(c.feasible for c in empty)
    assert {c.token for c in empty} == set(predictions)


@pytest.mark.parametrize("names,grip", [([], -1), (["x+40mm"], -1),
    (["hold", "open"], -1), (["hold", "close"], 1)])
def test_singletons_and_exact_grip_aliases_are_not_model_choice(names, grip):
    with pytest.raises(RuntimeError, match="two distinct"):
        ref.ensure_real_choice(tuple(Candidate(n, n) for n in names), grip)


def test_real_choice_keeps_all_legal_candidates_in_order():
    cs = (Candidate("close", "", False), Candidate("y-3mm", ""), Candidate("x+40mm", ""))
    assert ref.ensure_real_choice(cs, -1.) == ["y-3mm", "x+40mm"]


def test_presentation_contains_effects_and_real_feedback_not_predicted_feedback():
    ps = {"x+40mm": prediction(closing_mm=10.)}
    last = {"action": "y-3mm", "closure_mm": -2., "gap_reduction_mm": -1.,
            "after": features(), "official_success": False, "controls": 8}
    state, questions = ref.presentation(features(), ps, ["x+40mm"], 1., last)
    assert "effect_source=oracle_sim; privileged=true" in state
    assert "Last actual: y-3mm; closure=-2.000mm" in state
    assert "x+40mm|10.000|2.00" in state
    assert "grip=closed" in state
    assert questions["action"]["criteria"] == {"x+40mm": ""}


def test_view_preserves_live_authorization_identity():
    b = belief((Candidate("x+40mm", ""), Candidate("y-3mm", "")))
    view = ref.ReferenceView(b, "compact", {"action": {}})
    assert view.snapshot_id() == b.snapshot_id()
    assert view.candidate_set_id() == b.candidate_set_id()
    assert view.allowed() == b.allowed()
    assert view.provider_input() == "compact"


def test_injected_executor_is_used_without_changing_default_runtime():
    class Executor:
        def __init__(self):
            self.tokens = []

        def execute(self, token):
            self.tokens.append(token)
            return {"success": False}
    executor = Executor()
    runtime = Runtime("injected", RuleProvider(), FakeBackend(), executor=executor)
    runtime.step(0.)
    assert len(executor.tokens) == 1
    assert isinstance(Runtime("default", RuleProvider(), FakeBackend()).executor, ref.AtomicExecutor)


def test_model_input_clipping_stops_before_any_inference(monkeypatch):
    agent = SimpleNamespace(system_one=lambda *_: pytest.fail("model must not run"))
    builder = SimpleNamespace(backend=SimpleNamespace(gripper_command=lambda: -1.),
        last_preview={"before": features(), "predictions": {
            "x+40mm": prediction(), "y-3mm": prediction()}})
    logged = []
    provider = ref.ReferenceProvider(agent, builder, lambda kind, data: logged.append((kind, data)))
    monkeypatch.setattr(ref, "encoding_audit", lambda *a: {"available": True, "truncated": True})
    with pytest.raises(RuntimeError, match="truncated"):
        provider.decide(belief((Candidate("x+40mm", ""), Candidate("y-3mm", ""))))
    assert logged[0][1]["option_order"] == ["x+40mm", "y-3mm"]


def test_live_evaluator_does_not_use_predicted_success():
    world = SimpleNamespace(features=lambda: features(),
        data=SimpleNamespace(qpos=np.array([-.15])), qindex=0,
        env=SimpleNamespace(check_success=lambda: False))
    result = ref.measured_outcome(world, features(qpos_m=-.16), "x+40mm",
        {"environment_step_count": 8, "peak_obstacle_force_N": 0.})
    assert not result["official_success"]
    assert result["closure_mm"] == pytest.approx(10.)
    world.env.check_success = lambda: True
    with pytest.raises(RuntimeError, match="evaluator disagrees"):
        ref.measured_outcome(world, features(), "x+40mm", {})


def test_preview_comparison_detects_horizon_and_state_mismatch():
    world = SimpleNamespace(env=SimpleNamespace(sim=SimpleNamespace(
        get_state=lambda: np.array([0., 1.]))))
    outcome = {"closure_mm": 0., "gap_reduction_mm": 2., "controls": 8,
               "official_success": False, "after": features()}
    execution = {"peak_obstacle_force_N": 0., "execution_contract_violation": False,
                 "obstacle_pairs_seen": []}
    assert ref.compare_prediction(world, prediction(), outcome, execution)["passed"]
    assert not ref.compare_prediction(world, prediction(steps=7), outcome, execution)["passed"]
    assert not ref.compare_prediction(world, prediction(sim_state_after=[0., 2.]), outcome, execution)["passed"]
    assert not ref.compare_prediction(world, prediction(after=features(success=True)), outcome, execution)["passed"]


@pytest.mark.parametrize("name", ["x+40mm", "z-3mm", "rotate_x-10deg", "rotate_y+10deg", "open", "close", "hold"])
def test_executor_passes_native_primitive_and_retains_grip(monkeypatch, name):
    specs = {"x+40mm": {"axis": 0, "mm": 40}, "z-3mm": {"axis": 2, "mm": -3},
        "rotate_x-10deg": {"rot_axis": 0, "deg": -10}, "rotate_y+10deg": {"rot_axis": 1, "deg": 10},
        "open": {}, "close": {}, "hold": {}}
    monkeypatch.setattr(ref, "actions", lambda: specs)
    calls = []
    world = SimpleNamespace(obs={"robot0_eef_pos": np.zeros(3)}, data=SimpleNamespace(time=0.),
        env=SimpleNamespace(check_success=lambda: False))
    world.features = lambda: {**features(), "eef_rotation_matrix": np.eye(3).tolist(), "contacts": []}
    def execute(token, grip, record):
        calls.append((token, grip, record))
        g = {"open": -1., "close": 1.}.get(token, grip)
        return {"grip": g, "steps": 8, "commands": [np.r_[np.zeros(6), g]] * 8,
                "peak_obstacle_force_N": 0., "obstacle_pairs_seen": []}
    world.execute = execute
    backend = LiberoWorldBackend(world)
    backend._grip_cmd = 1.
    result = ref.JevAtomicExecutor(backend).execute(name)
    assert calls == [(name, 1., True)]
    assert backend.gripper_command() == (-1. if name == "open" else 1.)
    assert result["token"] == name and not result["execution_contract_violation"]
    assert not result["reset_envelope_validated_for_all_27"]
