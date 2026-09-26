"""Independent streaming audit of canonical Task1 stored native-stage evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import near, require

LABELS = ("neither_historical_relation", "designated_only", "historical_non_designated_only", "simultaneous")
SOURCE_HASHES = {"episodes.jsonl": "9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2",
    "manifest.json": "a19ddc51c95e094be6d4dbac3fbb1271902de30ede8f630d432c8e40f9ec4b2a",
    "reference-evidence.json": "063ad9585ca4bd5c9c5e7dbedff39efe522d51261a5a5e2e8246a94653cba008"}


def file_digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(part)
    return value.hexdigest()


def stream_records(path, identity):
    previous, digest = None, hashlib.sha256()
    with path.open("rb") as stream:
        for index, line in enumerate(stream):
            digest.update(line)
            require(line.endswith(b"\n"), "complete record")
            row = json.loads(line)
            payload = {k: v for k, v in row.items() if k != "record_id"}
            actual = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            require(row["seq"] == index and row["previous_record_id"] == previous and row["record_id"] == actual, "streamed record integrity")
            previous = row["record_id"]
            yield row
    identity.update(sha256=digest.hexdigest(), records=index+1)


def table(labels=LABELS):
    return {k: {"intervals": 0, "positive_change_mm": 0., "negative_change_mm": 0., "net_change_mm": 0.} for k in labels}


def add(totals, label, delta):
    row = totals[label]
    row["intervals"] += 1
    row["positive_change_mm"] += max(delta, 0.)
    row["negative_change_mm"] += min(delta, 0.)
    row["net_change_mm"] += delta


def classify(contacts, groups):
    # Reconstruct historical measurement counts from raw rows; never use wrist values.
    def match(c, left, right):
        a, b = c["geom_ids"]
        return (a in groups[left] and b in groups[right]) or (b in groups[left] and a in groups[right])
    strong = [c for c in contacts if c["normal_force_N"] > 1.]
    left = any(match(c, "left_pad", "handle") for c in strong)
    right = any(match(c, "right_pad", "handle") for c in strong)
    designated = left or right
    forbidden = any(match(c, "arm", "drawer") or match(c, "gripper", "explicit_nonhandle") for c in strong)
    forbidden |= not designated and any(match(c, "gripper", "handle") for c in strong)
    raw_designated = [c for c in contacts if match(c, "left_pad", "handle") or match(c, "right_pad", "handle")]
    return LABELS[int(designated)+2*int(forbidden)], designated, left and right, forbidden, raw_designated


def audit(raw, source):
    source_identity, artifacts, outcomes = {}, {}, {}
    for row in stream_records(source/"episodes.jsonl", source_identity):
        d = row["data"]
        if row["kind"] == "demo_trajectory": artifacts[d["step"]] = d
        elif row["kind"] == "reference_outcome": outcomes[d["step"]] = d
        elif row["kind"] == "environment": source_environment = d
        elif row["kind"] == "failure": raise ValueError("source failure")
    require(source_identity["sha256"] == SOURCE_HASHES["episodes.jsonl"], "canonical source")
    for name in ("manifest.json", "reference-evidence.json"):
        require(file_digest(source/name) == SOURCE_HASHES[name], "canonical source file")
    require(set(artifacts) == set(outcomes) == set(range(122)), "canonical primitive coverage")
    for artifact in artifacts.values():
        require(file_digest(source/artifact["artifact"]) == artifact["sha256"], "source trajectory bytes")
    counts, identity, stage_counts = Counter(), {}, {"before": Counter(), "after": Counter()}
    totals = {"before": table(), "after": table(), "interval": table((*LABELS, "ambiguous_stage_difference")), "control": table()}
    pending = previous = current = last_forward = None
    designated_samples, raw_designated_samples, first_last_robot = [], 0, {}
    per_primitive, forwards_per_primitive = [], []
    for row in stream_records(raw/"episodes.jsonl", identity):
        kind, d = row["kind"], row["data"]
        counts[kind] += 1
        if kind == "failure": raise ValueError("recorded replay failure")
        if kind == "run_start": start = d
        elif kind == "frozen_inputs":
            frozen = d
            require(d["source_hashes"] == SOURCE_HASHES and d["code"] == start["manifest"]["code"] and not d["code"]["dirty_status"], "clean freeze")
            require(d["artifacts"] == [artifacts[i] for i in range(122)] and d["primitive_control_counts"] == [8]*121+[2], "frozen source artifacts")
            require(file_digest(raw/"protocol.md") == d["protocol_sha256"], "frozen protocol")
            prior_identity, prior_frozen = {}, None
            for prior in stream_records(Path(start["resolved_config"]["preflight"])/"episodes.jsonl", prior_identity):
                if prior["kind"] == "frozen_inputs": prior_frozen = prior["data"]
                require(prior["kind"] != "failure", "successful preflight")
            require(prior_frozen == frozen, "preflight equality")
            for path, expected in d["stepping_sources"].items(): require(file_digest(Path(path)) == expected, "installed stepping source")
        elif kind == "environment":
            environment = d
            require(d["state"] == source_environment["sim_state"] and d["model_timestep_s"] == .002 and d["integrator"] == 0, "initial state and path")
            groups = {name: set(value["ids"]) for name, value in d["geometry"].items()}
            qi, vi = d["drawer_qpos_address"], d["drawer_dof_address"]
            require([(s["key"], s["dimension"], s["type"], s["unit"]) for s in d["sensors"]] ==
                    [("force_ee", 3, 4, "N"), ("torque_ee", 3, 5, "Nm")], "wrist physical metadata")
            for s in d["sensors"]:
                require(len(s["site_position_in_body_m"]) == 3 and len(s["site_quaternion_in_body_wxyz"]) == 4 and s["sample_time_s"] is None, "wrist frame/time")
        elif kind == "primitive_started":
            step = d["step"]
            require(step == len(per_primitive) and d["action"] == outcomes[step]["action"], "primitive order/action")
            with np.load(source/artifacts[step]["artifact"], allow_pickle=False) as arrays:
                commands, states, final = arrays["commands"].tolist(), arrays["states_before"].tolist(), arrays["state_after"].tolist()
            require(len(commands) == (2 if step == 121 else 8) and d["state"] == states[0], "archived primitive")
            current, previous, last_forward, local_calls, local_forwards = step, None, None, 0, 0
            primitive_totals = table((*LABELS, "ambiguous_stage_difference"))
        elif kind == "control_started":
            control = d["control"]
            require(d["step"] == current and d["global_control"] == counts[kind]-1
                    and d["command"] == commands[control] and d["state_before"] == states[control], "control before/command")
            control_intent = d
        elif kind == "native_forward_completed":
            require(d["forward_index"] == local_forwards, "forward ordinal")
            local_forwards += 1; last_forward = d
        elif kind == "integrator_call_started":
            require(pending is None and (d["call_index"], d["control"], d["within_control_index"], d["function"])
                    == (local_calls, local_calls//25, local_calls % 25, "mj_step"), "integration intent")
            pending = d; b = d["before"]
            require(b["last_native_forward"] == last_forward, "forward lineage")
            require(last_forward["input_time_s"] == b["time_s"] and last_forward["input_qpos_sha256"] ==
                    hashlib.sha256(np.array(b["qpos"], dtype=np.float64).tobytes()).hexdigest(), "forward stage")
            if previous is not None: require(all(b[k] == previous[k] for k in ("time_s", "qpos", "qvel")), "native state chain")
            if local_calls % 25 == 0: require([b["time_s"]]+b["qpos"]+b["qvel"] == states[control], "control start snapshot")
        elif kind == "integrator_call_completed":
            require(pending is not None and all(d[k] == pending[k] for k in ("arm", "call_index", "control", "within_control_index", "function")), "integration completion")
            b, a, classes = pending["before"], d["after"], {}
            near(a["time_s"]-b["time_s"], .002, "native timestep")
            require(a["last_native_forward"] == last_forward, "after-step cache lineage")
            for phase, snap in (("before", b), ("after", a)):
                require(snap["drawer_qpos_m"] == snap["qpos"][qi] and snap["drawer_qvel_m_s"] == snap["qvel"][vi], "joint addresses")
                for sensor in environment["sensors"]:
                    value = snap["wrist_sensor_buffers"][sensor["key"]]
                    require(len(value["values"]) == 3 and np.isfinite(value["values"]).all()
                            and value["buffer_read_sim_time_s"] == snap["time_s"] and value["actual_sample_time_s"] is None, "passive sensor record")
                for contact in snap["contacts"]:
                    require(contact["normal_force_N"] == contact["force_contact_frame"][0]
                            and contact["above_original_1N"] == (contact["normal_force_N"] > 1.), "contact threshold")
                    for label in ("robot", "drawer", "handle"):
                        require(contact[label+"_sides"] == [g in groups[label] for g in contact["geom_ids"]], "contact membership")
                label, designated, bilateral, forbidden, raw_d = classify(snap["contacts"], groups)
                classes[phase] = label
                stage_counts[phase][label] += 1
                stage_counts[phase]["bilateral"] += int(bilateral)
                stage_counts[phase]["raw_designated_rows"] += len(raw_d)
                raw_designated_samples += bool(raw_d)
                if designated:
                    designated_samples.append({"step": current, "control": control, "substep": local_calls % 25,
                        "phase": phase, "class": label, "time_s": snap["time_s"], "interval_s": [b["time_s"], a["time_s"]]})
            delta = 1000*(a["drawer_qpos_m"]-b["drawer_qpos_m"])
            label = classes["before"] if classes["before"] == classes["after"] else "ambiguous_stage_difference"
            for phase in ("before", "after"): add(totals[phase], classes[phase], delta)
            add(totals["interval"], label, delta); add(primitive_totals, label, delta)
            previous, pending, local_calls = a, None, local_calls+1
        elif kind == "control_state_observed":
            expected = states[control+1] if control+1 < len(commands) else final
            require(d["global_control"] == control_intent["global_control"] and d["state_after"] == expected
                    and [previous["time_s"]]+previous["qpos"]+previous["qvel"] == expected, "all available control after states")
        elif kind == "control_completed":
            result = classify(previous["contacts"], groups)
            require(d["valid_handle_contact"] == result[1] and d["valid_handle_grasp"] == result[2]
                    and d["non_designated_robot_contact"] == result[3], "native endpoint relations")
            require(d["drawer_before_m"] == states[control][1+qi] and d["drawer_after_m"] == previous["drawer_qpos_m"], "direct control position")
            require(d["closure_mm"] == 1000*(d["drawer_after_m"]-d["drawer_before_m"]), "control closure")
            add(totals["control"], result[0], d["closure_mm"])
        elif kind == "primitive_completed":
            require(d["step"] == current and d["state_after"] == final and d["drawer_after_m"] == outcomes[current]["actual_joint_qpos_m"]
                    and d["official_success"] == outcomes[current]["official_success"]
                    and d["native_integrator_calls"] == local_calls == len(commands)*25 and d["native_forward_calls"] == local_forwards, "primitive exact result")
            per_primitive.append({"step": current, "interval_attribution": primitive_totals})
            forwards_per_primitive.append(local_forwards); current = None
        elif kind == "termination": termination = d
    require(pending is None and current is None and termination["reason"] == "canonical_replay_complete" and termination["official_success"] is True, "successful complete replay")
    for kind, expected in (("primitive_completed", 122), ("control_started", 970), ("control_state_observed", 970),
                           ("control_completed", 970), ("integrator_call_started", 24250), ("integrator_call_completed", 24250)):
        require(counts[kind] == expected, "complete counts")
    net = 1000*(termination["final_drawer_qpos_m"]-source_environment["sim_state"][1+qi])
    for group in totals.values(): near(sum(x["net_change_mm"] for x in group.values()), net, "partition conservation")
    return {"passed": True, "raw_identity": identity, "source_hashes": SOURCE_HASHES, "producer_commit": frozen["code"]["commit"],
        "record_counts": dict(counts), "official_success": True, "net_drawer_closure_mm": net,
        "attribution": totals, "stage_counts": {k: dict(v) for k, v in stage_counts.items()},
        "designated_samples": designated_samples, "raw_designated_sample_count": raw_designated_samples,
        "native_forward_calls": sum(forwards_per_primitive), "per_primitive": per_primitive,
        "scope": "independent streaming stored-evidence audit only; no replay, model, FK or force estimation; contact-class sums are descriptive"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True); parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    result = audit(args.raw, args.source)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({k: result[k] for k in ("passed", "raw_identity", "net_drawer_closure_mm", "attribution", "stage_counts", "raw_designated_sample_count")}))
