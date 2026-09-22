"""Deterministic evidence for Stage-1 temporal semantics (no simulator/models)."""
from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime import FakeBackend, MultiRateFusion, ObservationEvent, RuleProvider, Runtime
from embodied_runtime.fusion import ConstantVelocityFusion3D, PositionMeasurement, TemporalConfig


def measurement(seq, t, position=None, source="depth"):
    return PositionMeasurement(source, seq, t, np.array([t, 0., 1.] if position is None else position), np.eye(3) * 1e-4)


def event(seq, t, *, episode="ep", covariance=True, position=None, ttl=.75, source="depth"):
    value = {"position_world_m": [t, 0., 1.] if position is None else position,
             "probabilities": {"drawer": .9, "unknown": .1}}
    if covariance:
        value["position_covariance_m2"] = (np.eye(3) * 1e-4).tolist()
    return ObservationEvent(source, episode, seq, t, 1000 + seq, value, track_id="drawer",
                            valid_until_sim=t + ttl)


def runtime(config=None):
    return Runtime("ep", RuleProvider(), FakeBackend(), fusion=MultiRateFusion(config=config or TemporalConfig(process_noise_mps2=.1)))


def test_in_order_and_delayed_capture_orders_have_identical_posterior_and_semantics():
    ordered, delayed = runtime(), runtime()
    for seq in (1, 2, 3):
        assert ordered.ingest(event(seq, (seq - 1) / 10), now_sim=.3)
    for seq in (3, 1, 2):  # including a capture earlier than the initial arrival
        assert delayed.ingest(event(seq, (seq - 1) / 10), now_sim=.3)
    a, b = ordered.fusion.snapshot(reference_time=.3), delayed.fusion.snapshot(reference_time=.3)
    np.testing.assert_allclose(a["geometry"]["drawer"].position_m, b["geometry"]["drawer"].position_m, atol=1e-12)
    np.testing.assert_allclose(a["geometry"]["drawer"].covariance, b["geometry"]["drawer"].covariance, atol=1e-12)
    assert a["semantic"]["drawer"] == pytest.approx(b["semantic"]["drawer"])
    for rt, snapshot in ((ordered, a), (delayed, b)):
        assert snapshot["geometry"]["drawer"].position_m[0] == pytest.approx(.3, abs=.003)
        assert snapshot["geometry"]["drawer"].velocity_mps[0] == pytest.approx(1, abs=.02)
        assert snapshot["validity"]["drawer"]["geometry_age_s"] == pytest.approx(.1)
        assert snapshot["validity"]["drawer"]["geometry_valid"]
        assert snapshot["validity"]["drawer"]["temporal_consistency_ok"]
        assert rt.fusion.geometry["drawer"].stats.replay_count == 3
        assert rt.store.admission.stats.accepted_delayed == 3
    assert delayed.store.admission.stats.accepted_out_of_order == 2


@pytest.mark.parametrize("seq,t,now,reason,counter", [
    (2, .2, .3, "duplicate", "dropped_duplicate"),
    (1, .0, 1.1, "too_late", "dropped_too_late"),
    (1, .3, .3, "sequence_regression", "dropped_out_of_order"),
    (3, .1, .3, "sequence_regression", "dropped_out_of_order"),
])
def test_rejected_events_change_neither_geometry_nor_semantics(seq, t, now, reason, counter):
    rt = runtime()
    assert rt.ingest(event(2, .2), now_sim=.2)
    before = rt.fusion.snapshot(reference_time=now)
    stats = asdict(rt.fusion.geometry["drawer"].stats)
    assert not rt.ingest(event(seq, t), now_sim=now)
    assert rt.store.last_ingest_reason == reason
    assert getattr(rt.store.admission.stats, counter) == 1
    assert rt.store.revision == 1
    after = rt.fusion.snapshot(reference_time=now)
    np.testing.assert_array_equal(before["geometry"]["drawer"].position_m, after["geometry"]["drawer"].position_m)
    np.testing.assert_array_equal(before["geometry"]["drawer"].covariance, after["geometry"]["drawer"].covariance)
    assert before["validity"] == after["validity"]
    assert before["semantic"] == after["semantic"]
    assert asdict(rt.fusion.geometry["drawer"].stats) == stats


@pytest.mark.parametrize("arrival", [.2, .6, 1.0])
def test_delayed_event_within_lag_is_accepted_at_capture_time(arrival):
    f = ConstantVelocityFusion3D(process_noise_mps2=.1)
    assert f.ingest(measurement(1, 0), reference_time=arrival)
    state = f.estimate(arrival)
    assert f.last_reason == "accepted_delayed"
    assert state.capture_time == 0
    assert state.age_s == arrival
    assert state.reference_time == arrival
    assert np.trace(state.covariance[:3, :3]) > 0
    assert f.stats.accepted_delayed == 1 and f.stats.replay_count == 1


def test_pruning_matches_unpruned_posterior_including_velocity_and_covariance():
    short = ConstantVelocityFusion3D(lag_s=.25, process_noise_mps2=.1)
    full = ConstantVelocityFusion3D(lag_s=10., process_noise_mps2=.1)
    for i in range(12):
        t = i / 10
        for f in (short, full):
            assert f.ingest(measurement(i, t), reference_time=t)
        a, b = short.estimate(t), full.estimate(t)
        np.testing.assert_allclose(a.position_m, b.position_m, atol=1e-12)
        np.testing.assert_allclose(a.velocity_mps, b.velocity_mps, atol=1e-12)
        np.testing.assert_allclose(a.covariance, b.covariance, atol=1e-12)
        assert a.accepted_measurements == i + 1
    assert short.anchor_time == pytest.approx(.85)
    assert short.pending_count == 3
    a, b = short.estimate(2), full.estimate(2)
    assert short.pending_count == 0
    assert a.capture_time == pytest.approx(1.1) and a.age_s == pytest.approx(.9)
    np.testing.assert_allclose(a.position_m, b.position_m, atol=1e-12)
    np.testing.assert_allclose(a.covariance, b.covariance, atol=1e-12)
    # New evidence after the entire old window is pruned still builds on its posterior.
    for f in (short, full):
        assert f.ingest(measurement(12, 2), reference_time=2)
    np.testing.assert_allclose(short.estimate(2).covariance, full.estimate(2).covariance, atol=1e-12)


def test_delay_after_anchor_advancement_matches_full_history():
    short = ConstantVelocityFusion3D(lag_s=.5, process_noise_mps2=.1)
    full = ConstantVelocityFusion3D(lag_s=10., process_noise_mps2=.1)
    for i in (0, 1, 2, 4, 5, 6):
        for f in (short, full):
            assert f.ingest(measurement(i, i / 5), reference_time=i / 5)
    # Capture 0.8 was already received, but missing capture 1.0 from another source
    # is admissible after pruning earlier information into the anchor.
    for f in (short, full):
        assert f.ingest(measurement(0, 1., source="other"), reference_time=1.2)
    np.testing.assert_allclose(short.estimate(1.2).position_m, full.estimate(1.2).position_m, atol=1e-12)
    np.testing.assert_allclose(short.estimate(1.2).covariance, full.estimate(1.2).covariance, atol=1e-12)


def test_pruned_duplicate_is_still_duplicate_and_no_capacity_eviction_loses_information():
    f = ConstantVelocityFusion3D(lag_s=.5, max_events=2)
    assert f.ingest(measurement(1, 0), reference_time=0)
    assert f.ingest(measurement(2, .1), reference_time=.1)
    before = f.estimate(.2)
    assert not f.ingest(measurement(3, .2), reference_time=.2)
    assert f.last_reason == "capacity" and f.stats.dropped_capacity == 1
    np.testing.assert_array_equal(before.covariance, f.estimate(.2).covariance)
    f.estimate(1.)
    assert not f.ingest(measurement(1, 0), reference_time=1.)
    assert f.last_reason == "duplicate" and f.stats.dropped_duplicate == 1
    assert f.stats.dropped_too_late == 0


def test_gate_rejection_does_not_refresh_geometry_or_inflate_counters_on_reads():
    rt = runtime()
    assert rt.ingest(event(1, 0), now_sim=0)
    assert rt.ingest(event(2, .1, position=[100., 0, 1]), now_sim=.1)
    snapshot = rt.fusion.snapshot(reference_time=.2)
    geom = rt.fusion.geometry["drawer"]
    assert geom.last_reason == "innovation_gate"
    assert snapshot["geometry"]["drawer"].capture_time == 0
    assert snapshot["validity"]["drawer"]["geometry_age_s"] == .2
    assert snapshot["validity"]["drawer"]["semantic_reference_time"] == .1
    assert not snapshot["validity"]["drawer"]["temporal_consistency_ok"]
    assert snapshot["validity"]["drawer"]["temporal_consistency_gap_s"] == .1
    stats = asdict(geom.stats)
    for _ in range(4):
        again = rt.fusion.snapshot(reference_time=.2)
        np.testing.assert_array_equal(snapshot["geometry"]["drawer"].covariance, again["geometry"]["drawer"].covariance)
    assert asdict(geom.stats) == stats
    assert geom.stats.rejected_gate == 1


def test_validity_expires_without_new_observations_and_recovers_on_fresh_evidence():
    config = TemporalConfig(process_noise_mps2=.1, geometry_max_age_s=.25,
                            geometry_max_position_trace_m2=100., semantic_ttl_s=.25)
    rt = runtime(config)
    assert rt.ingest(event(1, 0, ttl=.25), now_sim=0)
    fresh = rt.step(.1)["snapshot"]
    stale = rt.step(.5)["snapshot"]
    assert fresh.validity["drawer"]["geometry_valid"]
    assert fresh.validity["drawer"]["semantic_valid"]
    assert not stale.validity["drawer"]["geometry_valid"]
    assert "geometry_too_old" in stale.validity["drawer"]["geometry_invalid_reasons"]
    assert stale.validity["drawer"]["geometry_age_s"] == .5
    assert stale.validity["drawer"]["semantic_age_s"] == .5
    assert not stale.validity["drawer"]["semantic_valid"]
    assert stale.flags["semantic_stale:drawer"]
    assert sum(stale.semantic["drawer"].values()) == pytest.approx(1.)
    assert stale.semantic["drawer"]["unknown"] >= .5
    assert stale.validity["drawer"]["covariance_summary"]["position_trace_m2"] > fresh.validity["drawer"]["covariance_summary"]["position_trace_m2"]
    assert "vision:drawer:position_world_m" in stale.continuous
    assert rt.ingest(event(2, .5, ttl=.25), now_sim=.5)
    recovered = rt.step(.5)["snapshot"]
    assert recovered.validity["drawer"]["geometry_valid"]
    assert recovered.validity["drawer"]["semantic_valid"]
    assert recovered.validity["drawer"]["geometry_age_s"] == 0
    assert fresh.validity["drawer"]["geometry_age_s"] == .1  # old snapshot remains stable


def test_covariance_threshold_and_missing_covariance_are_explicit():
    rt = runtime(TemporalConfig(geometry_max_position_trace_m2=1e-5))
    assert rt.ingest(event(1, 0), now_sim=0)
    metadata = rt.step(0)["snapshot"].validity["drawer"]
    assert metadata["geometry_age_s"] == 0
    assert metadata["geometry_invalid_reasons"] == ["geometry_uncertain"]
    rt = runtime()
    assert rt.ingest(event(1, 0, covariance=False), now_sim=0)
    metadata = rt.step(0)["snapshot"].validity["drawer"]
    assert "measurement_covariance_unverified" in metadata["geometry_invalid_reasons"]
    assert metadata["provenance"][0]["measurement_covariance_source"] == "configured_fallback"


def test_late_old_semantics_does_not_renew_newer_capture_ttl():
    rt = runtime()
    assert rt.ingest(event(2, .2, ttl=.1), now_sim=.2)
    assert rt.ingest(event(1, .1, ttl=10.), now_sim=.25)
    snapshot = rt.step(.4)["snapshot"]
    m = snapshot.validity["drawer"]
    assert m["semantic_reference_time"] == .2
    assert m["semantic_valid_until_sim"] == pytest.approx(.3)
    assert not m["semantic_valid"]
    assert m["temporal_consistency_ok"]


@pytest.mark.parametrize("bad", [
    replace(event(1, 0), capture_sim_time=float("nan")),
    replace(event(1, 0), valid_until_sim=float("nan")),
    replace(event(1, 0), value={"position_world_m": [float("nan"), 0, 0]}),
    replace(event(1, 0), value={"position_world_m": [0, 0, 0], "position_covariance_m2": np.zeros((3, 3)).tolist()}),
    replace(event(1, 0), value={"position_world_m": [0, 0, 0], "probabilities": {"x": -1}}),
])
def test_invalid_observation_does_not_partially_mutate_store_or_filter(bad):
    rt = runtime()
    with pytest.raises(ValueError):
        rt.ingest(bad, now_sim=0)
    assert rt.store.revision == 0
    assert rt.fusion.geometry == {} and rt.fusion.semantic.tracks == {}


def test_wrong_episode_future_capture_and_zero_quality_cannot_refresh_belief():
    rt = runtime()
    assert not rt.ingest(event(1, 0, episode="other"), now_sim=0)
    assert rt.store.last_ingest_reason == "episode_mismatch"
    with pytest.raises(ValueError, match="reference time"):
        rt.ingest(event(1, .1), now_sim=0)
    assert not rt.ingest(replace(event(1, 0), quality=0), now_sim=0)
    assert rt.store.last_ingest_reason == "zero_quality"
    assert rt.fusion.geometry == {}
    assert rt.store.revision == 0


def test_resolved_config_matches_versioned_file_and_provenance_survives_runtime():
    config = json.loads((Path(__file__).parents[1] / "configs/temporal_stage1.json").read_text())
    assert asdict(TemporalConfig()) == config
    rt = runtime(TemporalConfig(**config))
    observation = event(1, 0)
    assert rt.ingest(observation, now_sim=.1)
    snapshot = rt.step(.1)["snapshot"]
    assert json.loads(snapshot.canonical_json())["temporal_config"] == config
    provenance = snapshot.validity["drawer"]["provenance"][0]
    assert provenance["capture_sim_time"] == 0
    assert provenance["received_wall_time"] == observation.received_wall_time
    assert provenance["quality"] == observation.quality
    assert provenance["source_seq"] == observation.source_seq
    assert provenance["position_covariance_m2"] == observation.value["position_covariance_m2"]


def test_candidate_builder_sees_decision_time_geometry_validity_without_policy_change():
    rt = runtime(TemporalConfig(geometry_max_age_s=.1))
    assert rt.ingest(event(1, 0), now_sim=0)
    observed = []
    original = rt.candidate_builder.build

    def inspect(snapshot):
        observed.append(snapshot.validity["drawer"])
        return original(snapshot)

    rt.candidate_builder.build = inspect
    rt.step(.2)
    assert observed[0]["geometry_reference_time"] == .2
    assert observed[0]["geometry_age_s"] == .2
    assert not observed[0]["geometry_valid"]


def test_equal_capture_time_metadata_is_arrival_order_independent():
    a, b = runtime(), runtime()
    for rt, order in ((a, (1, 2)), (b, (2, 1))):
        for seq in order:
            assert rt.ingest(event(seq, .1, ttl=seq / 10), now_sim=.1)
    sa, sb = a.step(.25)["snapshot"], b.step(.25)["snapshot"]
    assert sa.semantic == sb.semantic
    assert sa.validity["drawer"]["semantic_valid_until_sim"] == pytest.approx(.3)
    assert sb.validity["drawer"]["semantic_valid_until_sim"] == pytest.approx(.3)
    np.testing.assert_array_equal(sa.continuous["vision:drawer:covariance"], sb.continuous["vision:drawer:covariance"])


def test_explicit_measurement_ttl_invalidates_geometry_before_max_age():
    rt = runtime(TemporalConfig(geometry_max_age_s=1., geometry_max_position_trace_m2=10.))
    assert rt.ingest(event(1, 0, ttl=.1), now_sim=0)
    metadata = rt.step(.2)["snapshot"].validity["drawer"]
    assert metadata["geometry_invalid_reasons"] == ["geometry_ttl_expired"]
    assert metadata["semantic_invalid_reasons"] == ["semantic_ttl_expired"]


def test_standalone_filter_rejection_counters_and_late_first_measurement():
    f = ConstantVelocityFusion3D(lag_s=1.)
    assert not f.ingest(measurement(0, 0), reference_time=1.01)
    assert f.last_reason == "too_late" and f.stats.dropped_too_late == 1
    assert f.estimate(1.01) is None  # rejection cannot create an anchor
    assert f.ingest(measurement(2, 1.1), reference_time=1.1)
    state = f.estimate(1.2)
    assert not f.ingest(measurement(2, 1.1), reference_time=1.2)
    assert f.last_reason == "duplicate" and f.stats.dropped_duplicate == 1
    assert not f.ingest(measurement(1, 1.2), reference_time=1.2)
    assert f.last_reason == "sequence_regression" and f.stats.dropped_out_of_order == 1
    np.testing.assert_array_equal(state.covariance, f.estimate(1.2).covariance)
    assert f.stats.replay_count == 1


def test_new_snapshot_is_not_mutated_by_caller_owned_event_arrays():
    rt = runtime()
    observation = event(1, 0)
    assert rt.ingest(observation, now_sim=0)
    snapshot = rt.step(0)["snapshot"]
    observation.value["position_world_m"][0] = 100
    np.testing.assert_array_equal(snapshot.continuous["vision:drawer:position_world_m"], [0, 0, 1])


def test_laya_receives_the_same_published_validity_metadata_as_other_providers():
    from embodied_runtime import LayaProvider

    captured = {}

    class Agent:
        def system_one(self, state, questions):
            captured.update(state)
            return {"answers": {"action": {"choice": "STOP"}}}

    rt = runtime()
    rt.provider = LayaProvider(Agent())
    assert rt.ingest(event(1, 0), now_sim=0)
    snapshot = rt.step(.8)["snapshot"]
    assert captured["validity"] == snapshot.validity
    assert captured["temporal_config"] == snapshot.temporal_config
    assert captured["ages"] == snapshot.ages
    assert not captured["validity"]["drawer"]["geometry_valid"]


def test_episode_and_reference_time_cannot_be_silently_reused():
    rt = runtime()
    assert rt.ingest(event(1, .1), now_sim=.1)
    with pytest.raises(ValueError, match="different episode"):
        Runtime("other", RuleProvider(), FakeBackend(), fusion=rt.fusion)
    assert not rt.fusion.ingest_event(event(2, .1, episode="other"), reference_time=.1)
    assert rt.fusion.last_reason == "episode_mismatch"
    rt.step(.5)
    with pytest.raises(ValueError, match="reference time"):
        rt.ingest(event(2, .2), now_sim=.2)
    assert rt.store.revision == 1


def test_semantic_only_and_geometry_only_provenance_mismatch_is_visible():
    rt = runtime()
    sem = replace(event(1, .1), value={"probabilities": {"drawer": 1.}})
    assert rt.ingest(sem, now_sim=.1)
    metadata = rt.step(.1)["snapshot"].validity["drawer"]
    assert metadata["geometry_invalid_reasons"] == ["geometry_missing"]
    assert not metadata["temporal_consistency_ok"]
    geom = event(2, .2)
    geom.value.pop("probabilities")
    assert rt.ingest(geom, now_sim=.2)
    metadata = rt.step(.2)["snapshot"].validity["drawer"]
    assert metadata["geometry_valid"]
    assert not metadata["temporal_consistency_ok"]
    assert metadata["temporal_consistency_gap_s"] == .1
