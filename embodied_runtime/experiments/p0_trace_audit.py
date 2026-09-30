"""Recompute P0 trace invariants from raw events, independently of summary flags."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ..contracts import content_hash
from ..control.action_catalog import ACTION_IDS


def audit(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path,"rt") as f:
        events = [json.loads(line) for line in f if line.strip()]
    contracts, elapsed, pools, cancelled = {}, {}, {}, set()
    counts = dict(events=len(events), command_ticks=0, candidate_sets=0, model_inputs=0,
                  expired_dispatches=0, post_cancel_dispatches=0, overlong_segments=0,
                  partial_feedback=0, aborted_feedback=0)
    cases = set()
    for event in events:
        case,kind,p = event["case"],event["kind"],event["payload"]
        cases.add(case)
        if kind == "candidate_set":
            assert tuple(c["id"] for c in p["candidates"]) == ACTION_IDS
            assert tuple(p["presentation_order"]) == ACTION_IDS
            pools[(case,p["candidate_set_id"])] = (content_hash(p),p)
            counts["candidate_sets"] += 1
        elif kind == "model_input":
            expected,raw = pools[(case,p["candidate_set_id"])]
            assert p["candidate_hash"] == expected
            assert tuple(c["id"] for c in p["candidates"]) == ACTION_IDS
            assert [(c["id"],c["execution_status"]) for c in p["candidates"]] == [
                (c["id"],c["execution_status"]) for c in raw["candidates"]]
            counts["model_inputs"] += 1
        elif kind == "contract_installed":
            key = (case,p["contract_id"])
            assert key not in contracts, "duplicate installed contract"
            contracts[key] = p
            elapsed[key] = 0.
            cancelled.discard(case)
        elif kind == "cancel":
            cancelled.add(case)
        elif kind == "servo_tick":
            key = (case,p["contract_id"])
            contract = contracts[key]
            counts["command_ticks"] += 1
            counts["expired_dispatches"] += int(p["sim_time_s"] >= contract["valid_until_sim_s"]
                                                or p["monotonic_ns"] >= contract["expires_monotonic_ns"])
            counts["post_cancel_dispatches"] += int(case in cancelled)
            elapsed[key] += p["duration_s"]
            allowed = contract["valid_until_sim_s"]-contract["issued_sim_time_s"]
            counts["overlong_segments"] += int(elapsed[key] > allowed+1e-9)
            assert p["sim_time_s"]+p["duration_s"] <= contract["valid_until_sim_s"]+1e-9
            assert p["monotonic_ns"]+round(p["duration_s"]*1e9) <= contract["expires_monotonic_ns"]+1
        elif kind == "execution_feedback":
            assert p["status"] in {"COMPLETED","PARTIAL","ABORTED","REJECTED"}
            counts["partial_feedback"] += int(p["status"] == "PARTIAL")
            counts["aborted_feedback"] += int(p["status"] == "ABORTED")
    assert counts["expired_dispatches"] == counts["post_cancel_dispatches"] == counts["overlong_segments"] == 0
    counts.update(cases=sorted(cases), condition="synthetic_p0_no_physical_success_claim",
                  trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    args = parser.parse_args()
    print(json.dumps(audit(args.trace),indent=2))


if __name__ == "__main__":
    main()
