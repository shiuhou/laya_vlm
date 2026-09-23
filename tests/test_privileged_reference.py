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
from embodied_runtime.experiments.records import RunRecorder


def features(**extra):
    return {"qpos_m": -.15, "remaining_open_mm": 150.,
            "distance_to_moving_geometry_mm": 40., "moving_contact": False,
            "obstacle_contact": False, "finger_gap_mm": 70.,
            "success": False, **extra}


def prediction(**extra):
    return {"after": features(), "closing_mm": 0., "geometry_approach_mm": 2.,
            "peak_obstacle_force_N": 0., "obstacle_pairs_seen": [],
            "steps": 8, "sim_state_after": [0., 1.], **extra}


def witness(**extra):
    return {"second_input": "y-40mm", "net_progress": 1.547539,
            "net_gap_reduction_mm": 2.652469, "terminal_contact": False,
            "terminal_success": False, "peak_obstacle_force_N": 0.,
            "witnessed_effects": ["advance_target", "approach_target"], **extra}


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


def test_reference_builder_uses_existing_witnesses_only_after_empty_one_step_pool(monkeypatch):
    import jev_libero.policy

    predictions = {
        "x+3mm": prediction(geometry_approach_mm=1.),
        "z-3mm": prediction(closing_mm=-.1, geometry_approach_mm=2.7),
        "hold": prediction(geometry_approach_mm=1.),
    }
    witnesses = {
        "x+3mm": {"second_input": "z-3mm", "net_progress": .1,
            "net_gap_reduction_mm": 2.7, "terminal_contact": True,
            "terminal_success": False, "peak_obstacle_force_N": 0.,
            "witnessed_effects": ["advance_target", "establish_contact"]},
        "z-3mm": {"second_input": "x+3mm", "net_progress": 1.,
            "net_gap_reduction_mm": 2.6, "terminal_contact": False,
            "terminal_success": False, "peak_obstacle_force_N": 0.,
            "witnessed_effects": ["advance_target"]},
    }
    calls = []

    def contracts(_before, received, collision_aware, task_config):
        calls.append({name: "reposition_witness" in value for name, value in received.items()})
        eligible = {name: value for name, value in received.items()
                    if value.get("reposition_witness")}
        rejected = {name: "no witnessed effect" for name in received if name not in eligible}
        return ({"reposition": eligible} if eligible else {}), rejected

    world = SimpleNamespace(config={"test": True},
        predict_all=lambda _grip: (features(), predictions),
        two_step_witnesses=lambda _grip: (witnesses, 729))
    backend = SimpleNamespace(world=world, gripper_command=lambda: -1.)
    logged = []
    monkeypatch.setattr(jev_libero.policy, "contracts", contracts)
    monkeypatch.setattr(ref, "actions", lambda: {name: {} for name in predictions})
    monkeypatch.setattr(ref, "context_id", lambda _backend: "same")
    builder = ref.ReferenceBuilder(backend, lambda kind, data: logged.append((kind, data)))
    result = builder.build(belief())

    assert calls == [
        {"x+3mm": False, "z-3mm": False, "hold": False},
        {"x+3mm": True, "z-3mm": True, "hold": False},
    ]
    assert [candidate.token for candidate in result if candidate.feasible] == ["x+3mm", "z-3mm"]
    assert builder.last_preview["one_step_pools"] == {}
    assert builder.last_preview["pools"] == {"reposition": {
        "x+3mm": predictions["x+3mm"], "z-3mm": predictions["z-3mm"]}}
    assert builder.last_preview["two_step_evaluations"] == 729
    assert result[0].metadata["reposition_witness"] == witnesses["x+3mm"]
    assert logged[0][0] == "reference_preview" and logged[0][1]["restored"]


def test_reference_builder_does_not_run_lookahead_when_one_step_pool_exists(monkeypatch):
    import jev_libero.policy

    predictions = {"x+3mm": prediction(closing_mm=1.),
                   "z-3mm": prediction(closing_mm=2.)}

    def contracts(_before, received, collision_aware, task_config):
        return {"advance_target": dict(received)}, {}

    world = SimpleNamespace(config={"test": True},
        predict_all=lambda _grip: (features(), predictions),
        two_step_witnesses=lambda _grip: pytest.fail("non-empty pool must not trigger lookahead"))
    backend = SimpleNamespace(world=world, gripper_command=lambda: -1.)
    monkeypatch.setattr(jev_libero.policy, "contracts", contracts)
    monkeypatch.setattr(ref, "actions", lambda: {name: {} for name in predictions})
    monkeypatch.setattr(ref, "context_id", lambda _backend: "same")
    builder = ref.ReferenceBuilder(backend, lambda *_: None)
    result = builder.build(belief())
    assert all(candidate.feasible for candidate in result)
    assert not builder.last_preview["lookahead_triggered"]
    assert builder.last_preview["two_step_evaluations"] == 0


def test_reference_builder_preserves_one_step_singleton_without_lookahead(monkeypatch):
    import jev_libero.policy

    predictions = {"z-3mm": prediction(closing_mm=.06),
                   "open": prediction(geometry_approach_mm=1.)}

    def contracts(_before, received, collision_aware, task_config):
        return {"advance_target": {"z-3mm": received["z-3mm"]}}, {
            "open": "no witnessed effect"}

    world = SimpleNamespace(config={"test": True},
        predict_all=lambda _grip: (features(), predictions),
        two_step_witnesses=lambda _grip: pytest.fail("singleton is a non-empty one-step pool"))
    backend = SimpleNamespace(world=world, gripper_command=lambda: -1.)
    monkeypatch.setattr(jev_libero.policy, "contracts", contracts)
    monkeypatch.setattr(ref, "actions", lambda: {name: {} for name in predictions})
    monkeypatch.setattr(ref, "context_id", lambda _backend: "same")

    builder = ref.ReferenceBuilder(backend, lambda *_: None)
    result = builder.build(belief())

    assert [candidate.token for candidate in result if candidate.feasible] == ["z-3mm"]
    assert not builder.last_preview["lookahead_triggered"]


def test_reference_provider_forces_singleton_without_model_call():
    class NoModelAgent:
        def system_one(self, *_args, **_kwargs):
            raise AssertionError("singleton must not call Laya")

    builder = SimpleNamespace(
        backend=SimpleNamespace(gripper_command=lambda: -1.),
        last_preview={"lookahead_triggered": False},
    )
    logged = []
    provider = ref.ReferenceProvider(NoModelAgent(), builder,
                                     lambda kind, data: logged.append((kind, data)))
    snapshot = belief((Candidate("z-3mm", ""), Candidate("open", "", False)))

    decision = provider.decide(snapshot)

    assert decision.token == "z-3mm"
    assert decision.source == "forced_singleton" and decision.status == "valid"
    assert decision.probabilities == {} and decision.confidence == 0.0
    assert logged == [("reference_forced_singleton", {
        **ref.PRIVILEGE, "snapshot_id": snapshot.snapshot_id(),
        "belief_id": snapshot.belief_id(), "candidate_set_id": snapshot.candidate_set_id(),
        "option_order": ["z-3mm"], "candidate_count": 1, "pool_source": "one_step",
        "token": "z-3mm", "forced_singleton": True, "model_called": False,
        "previous_outcome_record_id": None,
    })]


def test_presentation_contains_effects_and_real_feedback_not_predicted_feedback():
    ps = {"x+40mm": prediction(closing_mm=10.)}
    last = {"action": "y-3mm", "closure_mm": -2., "gap_reduction_mm": -1.,
            "after": features(), "official_success": False, "controls": 8}
    state, questions = ref.presentation(features(), ps, ["x+40mm"], 1., last)
    assert "effect_source=oracle_sim; privileged=true" in state
    assert "Last actual: y-3mm; closure=-2.000mm" in state
    assert "x+40mm|10.000|2.00" in state
    assert "grip=closed" in state
    assert "verified_transition" not in state
    assert questions["action"]["criteria"] == {"x+40mm": ""}


def test_one_step_presentation_remains_byte_identical_to_v1():
    state, _ = ref.presentation(features(), {"x+40mm": prediction(closing_mm=10.)},
                                ["x+40mm"], -1., None)
    assert state == (
        "Task: close top drawer. effect_source=oracle_sim; privileged=true. "
        "Preview up to 8 controls/0.4s. XYZ world mm; rotations world degrees; "
        "nominal commands, predicted dynamics; grip retained except open/close.\n"
        "Current opening=150.000mm gap=40.00mm target_contact=0 "
        "obstacle_contact=0 grip=open finger_gap=70.00mm.\n"
        "Last actual: none.\n"
        "Effects: action|closure_mm (positive closes)|gap_reduction_mm (positive approaches)"
        "|target_contact|obstacle_peak_N|success|controls\n"
        "x+40mm|10.000|2.00|0|0.0|0|8\n"
    )


def test_presentation_exposes_witness_as_evidence_for_first_action_only():
    ps = {"z-3mm": prediction(closing_mm=-.108773,
        geometry_approach_mm=2.732324, reposition_witness=witness())}
    state, questions = ref.presentation(features(), ps, ["z-3mm"], -1., None)
    assert "Execute a only; replan." in state
    assert "Common: fp=0.0,fs=0,n=8,wp=0.0,ws=0." in state
    assert "z-3mm -0.109 2.73 0 > y-40mm 1.548 2.65 0 AP" in state
    assert questions["action"]["criteria"] == {"z-3mm": ""}


def test_compact_witness_presentation_is_lossless_and_preserves_canonical_order():
    names = ["x+3mm", "rotate_z-10deg", "hold"]
    predictions = {
        "x+3mm": prediction(closing_mm=-.108773, geometry_approach_mm=2.732324,
            reposition_witness=witness()),
        "rotate_z-10deg": prediction(closing_mm=1.2344, geometry_approach_mm=-4.567,
            reposition_witness=witness(second_input="x-10mm", net_progress=7.8912,
                net_gap_reduction_mm=-2.345, terminal_contact=True,
                witnessed_effects=["advance_target", "establish_contact"])),
        "hold": prediction(closing_mm=.01, geometry_approach_mm=-5.59,
            reposition_witness=witness(second_input="z-10mm", net_progress=.514,
                net_gap_reduction_mm=-3.08)),
    }
    last = {"action": "close", "closure_mm": .01, "gap_reduction_mm": -.25,
            "after": features(moving_contact=True, obstacle_contact=True),
            "official_success": False, "controls": 8}

    state, questions = ref.presentation(
        features(), predictions, names, 1., last, "reposition"
    )

    assert ref.presentation_format(predictions, names, "reposition") == ref.COMPACT_WITNESS_VERSION
    assert list(questions["action"]["criteria"]) == names
    assert "Rows follow numbered option order" in state
    assert "1 -0.109 2.73 0 > y-40mm 1.548 2.65 0 AP" in state
    assert "2 1.234 -4.57 0 > x-10mm 7.891 -2.35 1 AE" in state
    assert "3 0.010 -5.59 0 > z-10mm 0.514 -3.08 0 AP" in state
    assert "Common first_force 0.0 first_success 0 controls 8 witness_force 0.0 witness_success 0" in state
    assert "effect_source oracle_sim; privileged true" in state
    assert "Execute first action only; replan" in state


def test_compact_witness_presentation_keeps_varying_invariants_per_row():
    names = ["x+3mm", "hold"]
    predictions = {
        "x+3mm": prediction(peak_obstacle_force_N=1.2, steps=7,
            after=features(success=True), reposition_witness=witness(
                peak_obstacle_force_N=2.3, terminal_success=True)),
        "hold": prediction(peak_obstacle_force_N=3.4, steps=8,
            reposition_witness=witness(peak_obstacle_force_N=4.5)),
    }

    state, _ = ref.presentation(features(), predictions, names, -1., None, "reposition")

    assert ("effects first_force first_success controls witness_force witness_success."
            in state)
    assert "Common ." in state
    assert "1 0.000 2.00 0 > y-40mm 1.548 2.65 0 AP 1.2 1 7 2.3 1" in state
    assert "2 0.000 2.00 0 > y-40mm 1.548 2.65 0 AP 3.4 0 8 4.5 0" in state


def test_reference_provider_records_compact_witness_format(monkeypatch):
    names = ["x+3mm", "hold"]
    predictions = {name: prediction(reposition_witness=witness()) for name in names}
    routing = ref.objective_routing({"reposition": predictions}, names)
    builder = SimpleNamespace(
        backend=SimpleNamespace(gripper_command=lambda: -1.),
        last_preview={"before": features(), "predictions": predictions,
                      "lookahead_triggered": True, "objective_routing": routing},
    )
    logged = []
    agent = SimpleNamespace(system_one=lambda *_: {
        "answers": {"action": {"choice": "x+3mm", "probabilities": {
            "x+3mm": .6, "hold": .4}}}})
    monkeypatch.setattr(ref, "encoding_audit", lambda *a: {
        "available": True, "truncated": False,
        "questions": {"action": {"effective_input_ids": [], "option_markers": []}},
    })
    provider = ref.ReferenceProvider(agent, builder,
                                     lambda kind, data: logged.append((kind, data)))
    provider.provider = SimpleNamespace(decide=lambda view: ref.Decision(
        token="x+3mm", probabilities={"x+3mm": .6, "hold": .4}, confidence=.6,
        source="laya", input_revision=view.revision,
        input_sim_time=view.asof_sim_time, completed_wall_time=0.,
        valid_until_sim=view.asof_sim_time + .5,
    ))

    decision = provider.decide(belief(tuple(Candidate(name, "") for name in names)))

    model_input = next(data for kind, data in logged if kind == "reference_model_input")
    assert decision.token == "x+3mm"
    assert model_input["presentation_format"] == ref.COMPACT_WITNESS_VERSION
    assert model_input["option_order"] == names
    assert list(model_input["questions"]["action"]["criteria"]) == names


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


def test_summary_retains_empty_pool_boundary_and_does_not_claim_success(tmp_path):
    out = tmp_path / "failed"
    recorder = RunRecorder(out, {}, {"run_id": "failed"})
    recorder.record("reference_preview", {"belief_id": "boundary", "before": features(),
        "predictions": {"x+40mm": prediction()}, "pools": {},
        "rejected": {"x+40mm": "no witnessed effect"}, "restored": True})
    recorder.record("failure", {"category": "reference_error"})
    recorder.record("termination", {"reason": "reference_error", "success": False})
    recorder.close()
    summary = ref.summarize_reference(out)
    assert not summary["actual_success"] and not summary["qualifies_single_episode"]
    assert len(summary["unexecuted_previews"]) == 1
    assert "Eligible actions: []" in (out / "reference-report.md").read_text()


@pytest.mark.parametrize("condition", ["flat", "local_objective", "tampered_objective"])
def test_summary_counts_forced_singleton_without_model_evidence(tmp_path, condition):
    out = tmp_path / "forced"
    recorder = RunRecorder(out, {"condition": "flat" if condition == "flat" else "local_objective",
                                 "primitive_order": ["z-3mm"]}, {"run_id": "forced"})
    candidate = Candidate("z-3mm", "")
    snapshot = belief((candidate,))
    selected = prediction()
    routing = ref.objective_routing({"advance_target": {"z-3mm": selected}}, ["z-3mm"])
    extra = {"objective_routing": routing} if condition != "flat" else {}
    recorder.record("reference_preview", {"belief_id": snapshot.belief_id(),
        "before": features(), "predictions": {"z-3mm": selected},
        "pools": {"advance_target": {"z-3mm": selected}}, "rejected": {},
        "lookahead_triggered": False, "restored": True, **extra})
    builder = SimpleNamespace(backend=SimpleNamespace(gripper_command=lambda: -1.),
                              last_preview={"lookahead_triggered": False, **extra})
    agent = SimpleNamespace(system_one=lambda *_: pytest.fail("model must not run"))
    provider = ref.ReferenceProvider(agent, builder, recorder.record)
    decision = provider.decide(snapshot)
    recorder.record("decision", {"snapshot_id": snapshot.snapshot_id(), "decision": decision})
    trajectory = out / "trajectory" / "action-000.npz"
    trajectory.parent.mkdir()
    np.savez_compressed(trajectory, commands=np.zeros((8, 7)), states_before=np.zeros((8, 2)),
                        frames=np.empty((0,)), state_after=np.array([0., 1.]))
    recorder.record("demo_trajectory", {"step": 0,
        "artifact": "trajectory/action-000.npz", "sha256": ref.file_hash(trajectory),
        "frames": 0, "frame_timing": "test"})
    recorder.record("reference_outcome", {"step": 0, "snapshot_id": snapshot.snapshot_id(),
        "action": "z-3mm", "before": features(), "after": features(),
        "actual_joint_qpos_m": -.15, "official_success": False,
        "closure_mm": 0., "gap_reduction_mm": 0., "controls": 8,
        "obstacle_peak_N": 0., "comparison": {"state_max_error": 0., "passed": True},
        "candidate_count": 1, "pool_source": "one_step", "lookahead_recovery": False,
        "forced_singleton": True, "genuine_laya_decision": False,
        "decision_source": "forced_singleton", "fallback": None,
        "local_objective": "approach_target" if condition == "tampered_objective" else "advance_target"})
    recorder.record("termination", {"reason": "action_budget", "success": False, "step": 0})
    recorder.close()

    if condition == "tampered_objective":
        with pytest.raises(ValueError, match="objective routing"):
            ref.summarize_reference(out)
        return
    summary = ref.summarize_reference(out)

    assert summary["genuine_laya_decisions"] == 0
    assert summary["forced_singleton_continuations"] == 1
    assert summary["zero_pool_lookahead_recoveries"] == 0
    assert summary["trace"][0]["model_input"] is None
    assert summary["trace"][0]["decision"]["probabilities"] == {}
    assert not summary["actual_success"] and not summary["qualifies_single_episode"]


def test_summary_rejects_duplicate_preview_identity(tmp_path):
    out = tmp_path / "duplicate"
    recorder = RunRecorder(out, {}, {"run_id": "duplicate"})
    for _ in range(2):
        recorder.record("reference_preview", {"belief_id": "same"})
    recorder.close()
    with pytest.raises(ValueError, match="duplicate reference_preview"):
        ref.summarize_reference(out)


@pytest.mark.parametrize("objective", ref.OBJECTIVE_PRIORITY)
def test_objective_pool_keeps_all_actions_and_original_order(objective):
    pool = {"x+40mm": prediction(closing_mm=100.), "rotate_x+10deg": prediction(),
            "x+3mm": prediction(closing_mm=-100.)}
    order = ["close", "x+3mm", "rotate_x+10deg", "x+40mm"]
    routing = ref.objective_routing({objective: pool}, order)
    assert routing["objective"] == objective
    assert routing["motor_pool"] == order[1:]
    assert routing["objective_excluded"] == {}


def test_objective_priority_is_pool_presence_not_maximum_utility():
    pools = {"approach_target": {"x+40mm": prediction(closing_mm=100.)},
             "advance_target": {"hold": prediction(closing_mm=.01)}}
    routing = ref.objective_routing(pools, ["x+40mm", "hold"])
    assert routing["objective"] == "advance_target"
    assert routing["motor_pool"] == ["hold"]
    assert routing["objective_excluded"] == {"x+40mm": "outside_selected_objective"}
    assert not ref.objective_routing({}, ["hold"])["motor_pool"]
    with pytest.raises(ValueError, match="unknown"):
        ref.objective_routing({"invented_phase": {"hold": {}}}, ["hold"])


def test_baseline_check_allows_only_execution_budget_to_differ():
    baseline = {"seed": 1, "init_state_id": 0, "device": "cuda",
                "timeout_s": 1800., "steps": 100}
    args = SimpleNamespace(**{**baseline, "steps": 200})
    assert ref.validate_baseline_settings(args, baseline) == {
        "baseline_steps": 100, "requested_steps": 200,
        "only_execution_budget_may_differ": True,
    }
    args.seed = 2
    with pytest.raises(RuntimeError, match="seed"):
        ref.validate_baseline_settings(args, baseline)


def test_objective_presentation_preserves_effect_table_and_question_options():
    predictions = {"x+3mm": prediction(), "rotate_x+10deg": prediction()}
    state, question = ref.presentation(features(), predictions, list(predictions), -1., None)
    local, local_question = ref.presentation(features(), predictions, list(predictions), -1., None,
                                            "approach_target")
    assert local == "Current local objective: approach_target.\n" + state
    assert local_question["action"]["criteria"] == question["action"]["criteria"]
    assert "substantial predicted surface-gap reduction" in local_question["action"]["instructions"]


def test_objective_builder_preserves_contract_rejections_and_forces_true_singleton(monkeypatch):
    import jev_libero.policy
    predictions = {"x+3mm": prediction(closing_mm=.01), "rotate_x+10deg": prediction(),
                   "close": prediction()}
    pools = {"advance_target": {"x+3mm": predictions["x+3mm"]},
             "approach_target": {"rotate_x+10deg": predictions["rotate_x+10deg"]}}
    monkeypatch.setattr(jev_libero.policy, "contracts", lambda *a, **kw: (pools, {"close": "obstacle"}))
    monkeypatch.setattr(ref, "actions", lambda: {name: {} for name in predictions})
    monkeypatch.setattr(ref, "context_id", lambda _: "same")
    backend = SimpleNamespace(world=SimpleNamespace(config={}, predict_all=lambda _: (features(), predictions),
        two_step_witnesses=lambda _: pytest.fail("nonempty union")), gripper_command=lambda: -1.)
    builder = ref.ReferenceBuilder(backend, lambda *_: None, "local_objective")
    candidates = builder.build(belief())
    assert [c.token for c in candidates if c.feasible] == ["x+3mm"]
    assert candidates[1].reason_codes == ("outside_selected_objective",)
    assert candidates[2].reason_codes == ("obstacle",)
    assert builder.last_preview["pools"] is pools
    provider = ref.ReferenceProvider(SimpleNamespace(system_one=lambda *_: pytest.fail("singleton")),
                                     builder, lambda *_: None)
    assert provider.decide(belief(candidates)).source == "forced_singleton"
