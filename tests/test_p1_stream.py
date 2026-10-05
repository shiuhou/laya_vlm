import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments.p1_geometry_stream_probe import (
    age_metrics,
    run_stream,
)


def test_wall_age_not_frozen_sim_clock_controls_freshness():
    view = {"capture_monotonic_ns": 100, "capture_sim_time_s": 1.0}
    age = age_metrics(
        view,
        publish_monotonic_ns=400_000_100,
        publish_sim_time_s=1.0,
        free_age_s=0.3,
        contact_age_s=0.2,
    )
    assert age["sim_age_s"] == 0 and age["conservative_age_s"] == 0.4
    assert not age["free_geometry_fresh"] and not age["contact_geometry_fresh"]
    with pytest.raises(ProtocolError):
        age_metrics(
            view,
            publish_monotonic_ns=99,
            publish_sim_time_s=1.0,
            free_age_s=0.3,
            contact_age_s=0.2,
        )


def test_end_to_end_rate_includes_capture_geometry_and_persistence_no_deadline_hiding():
    now = [0]

    def capture():
        now[0] += 50_000_000
        return {"bundle_id": "test"}

    def process(bundle):
        now[0] += 200_000_000
        return {"status": "UNKNOWN"}

    def persist(bundle, record):
        now[0] += 50_000_000

    records, summary = run_stream(
        capture,
        process,
        persist,
        duration_s=0.9,
        requested_hz=10,
        clock_ns=lambda: now[0],
        sleep=lambda seconds: now.__setitem__(0, now[0] + round(seconds * 1e9)),
    )
    assert len(records) == 3
    assert summary["complete_persisted_cycles_hz"] == pytest.approx(1 / 0.3)
    assert summary["missed_cycle_deadlines"] == 3
    assert records[-1]["schedule_lag_ms"] == 400
    assert records[0]["capture_ms"] == 50 and records[0]["geometry_pipeline_ms"] == 200
    assert records[0]["end_to_end_ms"] == 250
    assert records[0]["persistence_finished_monotonic_ns"] == 300_000_000
