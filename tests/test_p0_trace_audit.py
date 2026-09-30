import json

import pytest

from embodied_runtime.contracts import load_config
from embodied_runtime.experiments.p0_contract_probe import probe_virtual
from embodied_runtime.experiments.p0_trace_audit import audit


def test_raw_audit_detects_expired_dispatch_independent_of_summary(tmp_path):
    _,events = probe_virtual(load_config("configs/p0_runtime.json"))
    path = tmp_path/"events.jsonl"
    def write():
        path.write_text("".join(json.dumps(e)+"\n" for e in events))
    write()
    assert audit(path)["expired_dispatches"] == 0
    tick = next(e for e in events if e["kind"] == "servo_tick")
    tick["payload"]["monotonic_ns"] = 999_000_000_000
    write()
    with pytest.raises(AssertionError):
        audit(path)
