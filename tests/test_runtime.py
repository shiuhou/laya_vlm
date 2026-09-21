import pytest

from embodied_runtime.runtime_core import (
    AtomicExecutor,
    BeliefSnapshot,
    BeliefStore,
    Candidate,
    FakeBackend,
    ObservationEvent,
    RuleProvider,
)


def event(source, seq, t, value, track=None, valid=None):
    return ObservationEvent(source, "ep", seq, t, t, value, track_id=track, valid_until_sim=valid)


def test_semantic_belief_expires_and_keeps_unknown():
    store = BeliefStore("ep")
    assert store.ingest(event("semantic", 1, 0.0, {"hypotheses": {"red": .9, "unknown": .1}}, "obj", 0.5), 0.0)
    fresh = store.snapshot(.2)
    assert fresh.semantic["obj"]["red"] > fresh.semantic["obj"]["unknown"]
    stale = store.snapshot(1.0)
    assert stale.flags["semantic_stale:obj"]
    assert stale.semantic["obj"]["unknown"] >= .5


def test_out_of_order_observation_is_rejected():
    store = BeliefStore("ep")
    assert store.ingest(event("geometry", 2, .2, {"obj_x": 1}), .2)
    assert not store.ingest(event("geometry", 1, .1, {"obj_x": 0}), .2)
    assert store.dropped_out_of_order == 1


def test_rule_is_candidate_bounded():
    snap = BeliefSnapshot("ep", 1, 0.0, {"aligned": False}, {}, {"satisfied": False},
                          (Candidate("MV_FWD", "forward"), Candidate("STOP", "stop")), {})
    decision = RuleProvider().decide(snap)
    assert decision.token in snap.allowed()


def test_executor_and_done_gate():
    backend = FakeBackend()
    executor = AtomicExecutor(backend)
    assert executor.execute("MV_FWD")["delta_m"][0] == pytest.approx(.02)
    executor.execute("GRASP")
    assert backend.width == 0.0
    executor.execute("RELEASE")
    assert backend.width == .08
    with pytest.raises(RuntimeError):
        executor.execute("DONE")


def test_laya_provider_uses_system_one_without_loading_weights():
    from embodied_runtime.runtime_core import LayaProvider

    class FakeAgent:
        def system_one(self, state, questions):
            return {"answers": {"action": {
                "choice": "MV_FWD",
                "probabilities": {"MV_FWD": 0.9, "STOP": 0.1},
                "confidence": 0.9,
            }}}

    snap = BeliefSnapshot("ep", 1, 0.0, {}, {}, {},
                          (Candidate("MV_FWD", "forward"), Candidate("STOP", "stop")), {})
    decision = LayaProvider(FakeAgent()).decide(snap)
    assert decision.token == "MV_FWD"
    assert decision.source == "laya"

