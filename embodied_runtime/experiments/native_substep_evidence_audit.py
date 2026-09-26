"""Independent file-only audit of the paired native substep diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import digest, items, near, records, require, single


def audit(raw_root):
    raw = raw_root / "native-substep-observability-run-01"
    reference = raw_root / "coarse-native-counterfactual-run-01"
    source = records(raw_root / "coarse-initial-point-02")
    prior, rows = records(reference), records(raw)
    require(digest(reference / "episodes.jsonl") == "23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa", "reference identity")
    frozen = single(rows, "frozen_inputs")
    preflight = records(Path(single(rows, "run_start")["resolved_config"]["preflight"]))
    require(frozen == single(preflight, "frozen_inputs"), "frozen preflight")
    require(frozen["code"] == single(rows, "run_start")["manifest"]["code"]
            and not frozen["code"]["dirty_status"], "clean generation")
    require(frozen["reference_frozen_inputs"] == single(prior, "frozen_inputs"), "prior generation")
    require(digest(raw / "protocol.md") == frozen["protocol_sha256"], "protocol")
    for path, expected in frozen["stepping_source_sha256"].items():
        require(digest(Path(path)) == expected, "native stepping source")
    require(single(rows, "termination") == {"reason": "two_arms_complete", "executed_arms": ["MV_RIGHT", "MV_DOWN"],
        "missing_arms": [], "diagnostic_prefix_controls": 400, "native_controls": 16,
        "native_integrator_calls": 400, "model_calls": 0}, "complete termination")
    reports = []
    for arm in ("MV_RIGHT", "MV_DOWN"):
        before = single(rows, "preboundary", arm)
        outcome = single(prior, "arm_completed", arm)
        require(single(rows, "arm_initial_state", arm)["state"] == single(source, "environment")["sim_state"], "reset")
        prefix, intents = items(rows, "prefix_control_completed", arm), items(rows, "prefix_control_started", arm)
        require(len(prefix) == len(intents) == 200, "prefix count")
        for i, (intent, actual, original) in enumerate(zip(intents, prefix, items(source, "control_observation")[:200])):
            require(actual["ordinal"] == intent["ordinal"] == i
                    and all(actual[k] == intent[k] == original[k] for k in ("command", "state_before"))
                    and actual["state_after"] == original["state_after"], "prefix control")
        controls = items(rows, "arm_control_completed", arm)
        require(controls == items(prior, "arm_control_completed", arm), "all native control rows")
        require(len(controls) == 8 and len(items(rows, "arm_control_started", arm)) == 8, "eight controls")
        for intent, control in zip(items(rows, "arm_control_started", arm), controls):
            require(all(control[k] == v for k, v in intent.items()), "control intent")
        require(single(rows, "execution_result", arm)["result"] == outcome["result"]
                and single(rows, "arm_completed", arm)["result"] == outcome["result"]
                and single(rows, "arm_completed", arm)["oracle_after"] == outcome["oracle_after"], "complete native result")
        starts, ends = items(rows, "integrator_call_started", arm), items(rows, "integrator_call_completed", arm)
        forwards = items(rows, "native_forward_completed", arm)
        require(len(starts) == len(ends) == 200, "integration count")
        require([x["forward_index"] for x in forwards] == list(range(len(forwards))), "forward ordinal")
        all_robot, calls_with_contact, first_motion = [], [], None
        for i, (start, end) in enumerate(zip(starts, ends)):
            require(all(start[k] == end[k] for k in ("arm", "call_index", "control", "within_control_index", "function")), "call identifiers")
            require((start["call_index"], start["control"], start["within_control_index"], start["function"])
                    == (i, i//25, i % 25, "mj_step"), "native call path")
            b, a = start["before"], end["after"]
            near(a["time_s"]-b["time_s"], before["model_timestep_s"], "step duration")
            if i % 25 == 0:
                require([b["time_s"]]+b["qpos"]+b["qvel"] == controls[i//25]["state_before"], "control start")
            else:
                previous = ends[i-1]["after"]
                require(all(b[k] == previous[k] for k in ("time_s", "qpos", "qvel")), "integrator chain")
            if i % 25 == 24:
                require([a["time_s"]]+a["qpos"]+a["qvel"] == controls[i//25]["state_after"], "control end")
            call_contacts = []
            for phase, snap in (("before", b), ("after", a)):
                qi, vi = before["drawer_qpos_address"], before["drawer_dof_address"]
                require(snap["drawer_qpos_address"] == qi and snap["drawer_dof_address"] == vi, "joint addresses")
                require(snap["drawer_qpos_m"] == snap["qpos"][qi]
                        and snap["drawer_qvel_m_s"] == snap["qvel"][vi]
                        and snap["drawer_qacc_m_s2"] == snap["qacc"][vi], "direct drawer fields")
                for field in ("qfrc_applied", "qfrc_constraint", "qfrc_passive", "qfrc_bias", "qfrc_actuator", "qfrc_smooth"):
                    require(snap["drawer_"+field] == snap[field][vi], "direct drawer force")
                forward = snap["last_native_forward"]
                require(forward == forwards[forward["forward_index"]], "forward lineage")
                require(forward["control"] == i//25 and forward["input_time_s"] == b["time_s"], "forward stage time")
                require(forward["input_qpos_sha256"] == hashlib.sha256(np.array(b["qpos"], dtype=np.float64).tobytes()).hexdigest(), "forward qpos")
                for contact in snap["contacts"]:
                    for label, field in (("robot", "robot_geom_ids"), ("drawer", "drawer_geom_ids"), ("handle", "handle_geom_ids")):
                        require(contact[label+"_sides"] == [g in before[field] for g in contact["geom_ids"]], "geometry membership")
                    require(len(contact["force_contact_frame"]) == 6 and contact["normal_force_N"] == contact["force_contact_frame"][0]
                            and contact["above_original_1N"] == (contact["normal_force_N"] > 1), "force semantics")
                    if any(contact["robot_sides"]):
                        value = {"call_index": i, "control": i//25, "within_control_index": i % 25,
                            "phase": phase, "integration_interval_s": [b["time_s"], a["time_s"]], **contact}
                        all_robot.append(value); call_contacts.append(value)
            if call_contacts:
                calls_with_contact.append(i)
            if first_motion is None and a["drawer_qpos_m"] != b["drawer_qpos_m"]:
                first_motion = {"call_index": i, "integration_interval_s": [b["time_s"], a["time_s"]],
                    "drawer_qpos_m": [b["drawer_qpos_m"], a["drawer_qpos_m"]],
                    "drawer_qvel_m_s": [b["drawer_qvel_m_s"], a["drawer_qvel_m_s"]],
                    "drawer_qfrc_constraint": [b["drawer_qfrc_constraint"], a["drawer_qfrc_constraint"]],
                    "robot_contact_present": bool(call_contacts)}
        per_control = [{"control": i, "integrator_contact_calls": sum(x//25 == i for x in calls_with_contact),
            "after_control_contact_rows": len(controls[i]["contacts"]),
            "drawer_delta_mm": 1000*(ends[i*25+24]["after"]["drawer_qpos_m"]-starts[i*25]["before"]["drawer_qpos_m"])} for i in range(8)]
        near(sum(x["drawer_delta_mm"] for x in per_control), outcome["drawer_joint_delta_m"]*1000, "drawer total")
        reports.append({"arm": arm, "integrator_enum": before["integrator"], "timestep_s": before["model_timestep_s"],
            "native_forward_calls": len(forwards), "integrator_calls": len(starts), "snapshots": len(starts)+len(ends),
            "exact_reference_result": True, "contact_call_indices": calls_with_contact,
            "robot_contact_cache_rows": len(all_robot), "nonhandle_contact_cache_rows": sum(not any(c["handle_sides"]) for c in all_robot),
            "maximum_normal_force_N": max((c["normal_force_N"] for c in all_robot), default=0),
            "first_observed_robot_contact": all_robot[0] if all_robot else None, "first_direct_drawer_motion": first_motion,
            "per_control": per_control, "all_recorded_cartesian_applied_forces_zero": all(np.count_nonzero(x[phase]["xfrc_applied"]) == 0
                for phase, seq in (("before", starts), ("after", ends)) for x in seq),
            "execution_contract_reasons": outcome["result"]["execution_contract_reason"]})
    artifacts = items(rows, "capture") + items(rows, "demo_trajectory")
    require(len(artifacts) == 6, "artifact count")
    for artifact in artifacts:
        require(digest(raw/artifact["artifact"]) == artifact["sha256"], "artifact hash")
    for arm, trajectory in zip(("MV_RIGHT", "MV_DOWN"), items(rows, "demo_trajectory")):
        controls = items(rows, "arm_control_completed", arm)
        with np.load(raw/trajectory["artifact"], allow_pickle=False) as arrays:
            require(arrays["commands"].tolist() == [c["command"] for c in controls]
                    and arrays["states_before"].tolist() == [c["state_before"] for c in controls]
                    and arrays["state_after"].tolist() == controls[-1]["state_after"] and len(arrays["frames"]) == 8, "trajectory lineage")
    return {"passed": True, "raw_sha256": digest(raw/"episodes.jsonl"), "producer_commit": frozen["code"]["commit"],
        "record_count": len(rows), "prefix_controls": 400, "native_controls": 16, "integrator_calls": 400,
        "snapshots": 800, "scope": "stored-evidence audit only; no dynamics, FK or model run; cached contact rows are not event counts",
        "arms": reports}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.raw_root)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "raw_sha256": result["raw_sha256"], "record_count": result["record_count"]}))
