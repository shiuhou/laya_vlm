from functools import partial
import time

from embodied_runtime.contracts import freeze, load_config
from embodied_runtime.experiments.p0_contract_probe import probe_virtual
from embodied_runtime.workers import LatestWorker


def echo(request, delay_s=.05):
    time.sleep(delay_s)
    return freeze({"id":request["request_id"]})


def wait_result(worker, timeout=4.):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        result = worker.poll()
        if result:
            return result
        time.sleep(.01)
    raise AssertionError("worker did not return")


def test_virtual_two_second_response_valid_vs_default_expired():
    summaries, events = probe_virtual(load_config("configs/p0_runtime.json"))
    valid, expired = summaries
    assert valid["accepted"] and valid["commands"] == 2
    assert not expired["accepted"] and expired["commands"] == 0
    assert "PROPOSAL_EXPIRED" in expired["rejections"]
    assert sum(e["kind"] == "proprioception" for e in events) >= 80


def test_process_latest_pending_bounded_and_immutable_output_roundtrip():
    worker = LatestWorker(echo)
    try:
        worker.submit({"request_id":"first"})
        worker.submit({"request_id":"replaced"})
        worker.submit({"request_id":"latest"})
        assert worker.replaced == 1
        assert wait_result(worker)["output"]["id"] == "first"
        assert wait_result(worker)["output"]["id"] == "latest"
        assert worker.completed == 2
    finally:
        assert worker.close()["alive"] is False


def test_hung_worker_shutdown_is_owned_and_bounded():
    worker = LatestWorker(partial(echo,delay_s=30.))
    worker.submit({"request_id":"hung"})
    started = time.monotonic()
    assert worker.close(timeout_s=.1)["alive"] is False
    assert time.monotonic()-started < 2.


def test_real_slow_worker_does_not_block_control_and_cancel_discards_pending():
    worker = LatestWorker(partial(echo,delay_s=2.))
    try:
        worker.submit({"request_id":"old-goal"})
        worker.submit({"request_id":"cancelled-pending"})
        worker.discard_pending()
        started = time.monotonic()
        ticks = 0
        result = None
        while result is None and time.monotonic()-started < 6.:
            # Owner can keep control at each tick while process performs inference.
            ticks += 1
            result = worker.poll()
            time.sleep(.05)
        assert result["request_id"] == "old-goal"
        assert ticks >= 30
        assert worker.pending is None and worker.in_flight is None
    finally:
        assert worker.close()["alive"] is False
