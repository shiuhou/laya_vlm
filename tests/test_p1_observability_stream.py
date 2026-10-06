import time

from embodied_runtime.experiments.p1_observability_stream import LatestBundleSlot, run_latest_stream


def test_latest_slot_replaces_complete_bundle_and_drains_on_close():
    slot = LatestBundleSlot()
    first, second = {"views": ["a1", "b1"]}, {"views": ["a2", "b2"]}
    assert slot.put(first) is None
    assert slot.put(second) is first
    slot.close()
    assert slot.take() is second
    assert slot.take() is None


def test_live_capture_continues_while_worker_persists_and_preserves_capture_age():
    captures, persisted = [], []

    def capture():
        clock = time.monotonic_ns()
        bundle = dict(bundle_id=f"bundle-{len(captures)}", capture_sim_time_s=7.0,
                      views=[dict(camera_id=c, frame_id=f"{c}/{len(captures)}",
                                  capture_monotonic_ns=clock, capture_sim_time_s=7.0)
                             for c in ("a", "b")])
        captures.append(bundle)
        return bundle

    def process(bundle):
        time.sleep(0.02)
        return {"identity": "UNKNOWN"}

    def persist(bundle, record):
        # Durable I/O must be after snapshot publication, not hidden inside it.
        assert record["published_monotonic_ns"] <= time.monotonic_ns()
        assert record["freshness"][0]["capture_monotonic_ns"] == bundle["views"][0]["capture_monotonic_ns"]
        time.sleep(0.03)
        persisted.append(bundle["bundle_id"])

    records, capture_rows, summary = run_latest_stream(capture, process, persist,
                                                      duration_s=0.16, requested_hz=200)
    assert len(capture_rows) > len(records) >= 2
    assert summary["queue_replacements"] > 0
    assert summary["dropped_views"] == 2*summary["queue_replacements"]
    assert summary["captured_bundles"] == summary["published_snapshots"]+summary["queue_replacements"]
    assert summary["valid_target_hz"] == 0 and summary["semantic_identity"] == "UNKNOWN"
    assert all(r["persistence_finished_monotonic_ns"] > r["published_monotonic_ns"] for r in records)
    assert all(f["sim_age_s"] == 0 and f["wall_age_s"] >= 0.02 for r in records for f in r["freshness"])
    assert len(persisted) == len(records)
