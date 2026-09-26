"""Read sealed evidence only; no producer helpers, FK, simulator or model imports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SOURCE_HASH = "e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf"
ARMS = ("MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN", "STOP")
DIRECTIONS = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0],
                       [0, 0, 1], [0, 0, -1], [0, 0, 0]])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text())


def records(directory):
    raw = (directory / "episodes.jsonl").read_bytes()
    require(raw.endswith(b"\n"), "unterminated evidence")
    rows, previous = [], None
    for i, line in enumerate(raw.splitlines()):
        row = json.loads(line)
        payload = {k: v for k, v in row.items() if k != "record_id"}
        computed = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        require(row["seq"] == i and row["previous_record_id"] == previous
                and row["record_id"] == computed, f"record chain {directory.name}:{i}")
        previous = row["record_id"]
        rows.append(row)
    require(not [r for r in rows if r["kind"] == "failure"], "failed run")
    return rows


def items(rows, kind, arm=None):
    return [r["data"] for r in rows if r["kind"] == kind
            and (arm is None or r["data"].get("arm") == arm)]


def single(rows, kind, arm=None):
    values = items(rows, kind, arm)
    require(len(values) == 1, f"expected one {kind}/{arm}")
    return values[0]


def near(actual, expected, label):
    require(np.allclose(actual, expected, rtol=0, atol=1e-11), label)


def candidate_audit(root):
    source_dir = root / "coarse-initial-point-02"
    run_dir = root / "coarse-native-counterfactual-run-01"
    require(digest(source_dir / "episodes.jsonl") == SOURCE_HASH, "source hash")
    source, rows = records(source_dir), records(run_dir)
    start = single(rows, "run_start")
    prior = records(Path(start["resolved_config"]["preflight"]))
    frozen = single(rows, "frozen_inputs")
    require(frozen == single(prior, "frozen_inputs"), "preflight/final identity")
    require(frozen["code"] == start["manifest"]["code"] and not frozen["code"]["dirty_status"], "clean freeze")
    require(digest(run_dir / "protocol.md") == frozen["protocol_sha256"], "protocol bytes")
    require(frozen["source_sha256"] == SOURCE_HASH and frozen["arms"] == list(ARMS), "source/arms")
    require(single(rows, "termination") == {"reason": "seven_arms_complete", "executed_arms": list(ARMS),
        "missing_arms": [], "diagnostic_prefix_controls": 1400, "counterfactual_primitives": 7,
        "counterfactual_controls": 56, "model_calls": 0}, "complete termination")
    source_start = single(source, "run_start")
    for name, fingerprint in frozen["native_source_sha256"].items():
        require(source_start["manifest"]["code"]["source_sha256"][name] == fingerprint, "native code unchanged")
    native_files = ("runtime_core.py", "decision_interface.py", "adapters/libero.py",
                    "adapters/libero_rgbd.py", "experiments/coarse_point_probe.py", "experiments/engineering_demo.py")
    for name in native_files:
        key = "embodied_runtime/" + name
        require(source_start["manifest"]["code"]["source_sha256"][key] == frozen["code"]["source_sha256"][key], "controller-facing code")
    env, original_controls = single(source, "environment"), items(source, "control_observation")
    original_boundary = items(source, "decision_boundary")[25]
    original_action = items(source, "action")[25]
    require(len(original_controls) == 208, "source controls")
    require(frozen["source_boundary_record"] == original_boundary, "boundary identity")
    require(frozen["source_task_config"] == env["task_config"], "task config")
    require(frozen["initial_identity"] == single(source, "initial_identity"), "reset identity")
    require(frozen["versions"] == source_start["manifest"]["versions"], "versions")
    repos = next(x["environment_repositories"] for x in items(source, "manifest_update")
                 if "environment_repositories" in x)
    require(frozen["environment_repositories"] == repos, "simulator repositories")
    point = np.array(single(source, "initial_target_frozen")["admitted"]["position_world_m"])
    handles = env["task_config"]["measurements"]["gripper_handle_contacts"]["right"]["geoms"]
    before_state = original_controls[200]["state_before"]
    require([x["arm"] for x in items(rows, "arm_completed")] == list(ARMS), "arm order")
    artifact_hashes, outcomes = {}, []
    for index, arm in enumerate(ARMS):
        initial, boundary, result = (single(rows, kind, arm) for kind in
                                    ("arm_initial_state", "preboundary", "arm_completed"))
        require(initial["state"] == env["sim_state"] and initial["execution_state"] == env["initial_state"], "fresh reset")
        require(boundary["state"] == before_state and boundary["fixed_point_world_m"] == point.tolist(), "preboundary")
        require(boundary["original_candidate"] == original_boundary["canonical"]["candidates"][index]
                and boundary["original_effect"] == original_boundary["canonical"]["effects"]["effects"][arm], "candidate/effect")
        require(boundary["oracle_before"] == original_action["oracle_before"], "preboundary evaluator")
        starts, completed = items(rows, "prefix_control_started", arm), items(rows, "prefix_control_completed", arm)
        require(len(starts) == len(completed) == 200, "prefix length")
        for i, (intent, actual, old) in enumerate(zip(starts, completed, original_controls[:200])):
            require(intent["ordinal"] == actual["ordinal"] == i
                    and all(intent[k] == actual[k] == old[k] for k in ("command", "state_before"))
                    and actual["state_after"] == old["state_after"], "prefix lineage")
        controls, intents = items(rows, "arm_control_completed", arm), items(rows, "arm_control_started", arm)
        require(len(controls) == len(intents) == 8, "native count")
        expected = before_state
        for i, (intent, control) in enumerate(zip(intents, controls)):
            require(control["control"] == i and all(control[k] == v for k, v in intent.items())
                    and control["state_before"] == expected and control["command"][-1] == -1., "arm lineage")
            expected = control["state_after"]
        execution = result["result"]
        require(result["state_before"] == before_state and result["state_after"] == expected
                and execution["environment_step_count"] == 8
                and execution["low_level_commands"] == [c["command"] for c in controls], "completed execution")
        require(execution["execution_before"] == original_action["result"]["execution_before"], "execution before")
        contacts = [contact for c in controls for contact in c["contacts"]]
        nonhandle = [c for c in contacts if not any(g in handles for g in c["geom_names"])]
        gain = result["oracle_before"]["gripper_to_designated_handle_surface_mm"] - result["oracle_after"]["gripper_to_designated_handle_surface_mm"]
        near(gain, result["measured_handle_surface_gap_gain_mm"], "gap gain")
        for name, value in {"observed_robot_contact_rows": len(contacts), "observed_nonhandle_contact_rows": len(nonhandle),
            "robot_contact_above_1N": any(c["normal_force_N"] > 1 for c in contacts),
            "nonhandle_contact_above_1N": any(c["normal_force_N"] > 1 for c in nonhandle),
            "no_observed_robot_contact_and_positive_approach": not contacts and gain > 0,
            "no_observed_nonhandle_contact_and_positive_approach": not nonhandle and gain > 0,
            "no_robot_contact_above_1N_and_positive_approach": not any(c["normal_force_N"] > 1 for c in contacts) and gain > 0}.items():
            require(result[name] == value, f"raw classification {name}")
        before, after = np.array(execution["before"]), np.array(execution["after"])
        near(1000 * (np.linalg.norm(before-point)-np.linalg.norm(after-point)), result["actual_fixed_point_gain_mm"], "point gain")
        near(1000 * (np.linalg.norm(before-point)-np.linalg.norm(before+.01*DIRECTIONS[index]-point)), result["nominal_fixed_point_gain_mm"], "nominal gain")
        delta = after-before
        error = np.linalg.norm(delta-.01*DIRECTIONS[index])
        near(delta, execution["delta_m"], "TCP displacement")
        rotation = np.array(execution["execution_after"]["orientation"]) @ np.array(execution["execution_before"]["orientation"]).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2, -1, 1))))
        near(angle, execution["rotation_angle_deg"], "rotation")
        reasons = []
        tolerance = execution["execution_contract_tolerances"]
        require(tolerance == {"translation_error_m": .002, "hold_translation_m": .0015,
            "hold_rotation_deg": 1., "rotation_error_deg": 2.}, "unchanged contract tolerances")
        if arm == "STOP":
            if error > tolerance["hold_translation_m"]:
                reasons.append("unintended_translation")
        elif error > tolerance["translation_error_m"]:
            reasons.append("translation_error")
        if angle > tolerance["hold_rotation_deg"]:
            reasons.append("unintended_rotation")
        require(reasons == execution["execution_contract_reason"] and bool(reasons) == execution["execution_contract_violation"], "contract arithmetic")
        qi = boundary["drawer_joint_qpos_index"]
        drawer_delta = expected[1+qi]-before_state[1+qi]
        near(drawer_delta, result["drawer_joint_delta_m"], "drawer displacement")
        for c in controls:
            require(c["drawer_joint_qpos_m"] == c["state_after"][1+qi], "control drawer qpos")
        if arm == "MV_RIGHT":
            require(execution == original_action["result"] and result["oracle_after"] == original_action["oracle_after"]
                    and result["original_selected_continuation_exact"] is True, "original continuation")
            for c, old in zip(controls, original_controls[200:]):
                require(all(c[k] == old[k] for k in ("command", "state_before", "state_after", "contacts")), "MV_RIGHT control")
        outcomes.append({"arm": arm, "sampled_robot_contacts": len(contacts), "sampled_nonhandle_contacts": len(nonhandle),
            "maximum_force_N": max((c["normal_force_N"] for c in contacts), default=0.),
            "handle_gap_gain_mm": gain, "point_gain_mm": result["actual_fixed_point_gain_mm"],
            "translation_error_mm": float(error*1000), "contract_reasons": reasons,
            "drawer_joint_delta_mm": float(drawer_delta*1000),
            "sampled_contact_free_progress": not contacts and gain > 0,
            "contract_valid_sampled_contact_free_progress": not contacts and gain > 0 and not reasons})
        trajectory = items(rows, "demo_trajectory")[index]
        with np.load(run_dir/trajectory["artifact"], allow_pickle=False) as arrays:
            require(arrays["commands"].tolist() == [c["command"] for c in controls]
                    and arrays["states_before"].tolist() == [c["state_before"] for c in controls]
                    and arrays["state_after"].tolist() == expected and len(arrays["frames"]) == 8, "trajectory")
    artifacts = items(rows, "capture") + items(rows, "demo_trajectory")
    require(len(items(rows, "capture")) == 14 and len(items(rows, "demo_trajectory")) == 7, "artifact counts")
    for artifact in artifacts:
        artifact_hashes[artifact["artifact"]] = digest(run_dir/artifact["artifact"])
        require(artifact_hashes[artifact["artifact"]] == artifact["sha256"], "artifact bytes")
    return {"raw_sha256": digest(run_dir/"episodes.jsonl"), "producer_commit": frozen["code"]["commit"],
        "record_count": len(rows), "prefix_controls_verified": 1400, "native_controls_verified": 56,
        "original_MV_RIGHT_exact": True, "artifact_hashes": artifact_hashes, "arms": outcomes,
        "contract_valid_sampled_contact_free_progress_arms": [x["arm"] for x in outcomes if x["contract_valid_sampled_contact_free_progress"]]}


def robot_audit(root):
    raw = root/"robot-geometry-observability-03"
    manifest = read_json(raw/"artifacts.json")
    require(len(manifest) == 12, "robot artifact count")
    for name, expected in manifest.items():
        require(digest(raw/name) == expected, "robot artifact hash")
    request = read_json(raw/"estimator-input.json")
    calibration = read_json(raw/"robot-calibration.json")
    packets = read_json(raw/"encoder-packets.json")
    estimates = read_json(raw/"sensor-estimates.json")
    evaluator = read_json(raw/"evaluator-recomputed-poses.json")["states"]
    seal = read_json(raw/"sensor-estimates-seal.json")
    require(seal["sha256"] == digest(raw/"sensor-estimates.json")
            and seal["input_sha256"] == digest(raw/"estimator-input.json")
            and seal["evaluator_transforms_computed_yet"] is False, "seal")
    require(set(request) == {"calibration", "joint_packets"} and request["calibration"] == calibration, "estimator request")
    require(set(calibration) == {"version", "bodies", "sites", "geometries"}, "calibration schema")
    joint_names = {f"robot0_joint{i}" for i in range(1, 8)} | {"gripper0_finger_joint1", "gripper0_finger_joint2"}
    require(len(request["joint_packets"]) == 14 and all(set(p) == joint_names for p in request["joint_packets"].values()), "own packets")
    maximum = {}
    comparisons = 0
    for label, state in evaluator.items():
        for group, values in state.items():
            for name, fields in values.items():
                for field, reference in fields.items():
                    if field in {"position_world_m", "rotation_world", "vertices_world_m", "aabb_world_m"}:
                        difference = float(np.max(np.abs(np.array(estimates[label][group][name][field])-reference)))
                        maximum[field] = max(maximum.get(field, 0.), difference)
                        require(difference <= 1e-10, "FK stored array agreement")
                        comparisons += 1
    poison_count = 0
    for label in estimates:
        if "/" not in label:
            continue
        original = label.split("/")[0]
        require(request["joint_packets"][label] == request["joint_packets"][original], "poison inputs")
        require(estimates[label] == estimates[original], "poison outputs")
        # Numeric JSON leaves parsed to float64; this also distinguishes signed zero.
        def bits(value):
            if isinstance(value, dict):
                return b"".join(bits(value[k]) for k in sorted(value))
            if isinstance(value, list):
                return b"".join(bits(v) for v in value)
            if isinstance(value, str):
                return value.encode()
            return np.float64(value).tobytes()
        require(bits(estimates[label]) == bits(estimates[original]), "poison numeric bits")
        poison_count += 1
    require(poison_count == 8 and len(packets["original"]) == 4, "robot scenario count")
    return {"artifacts_manifest_sha256": digest(raw/"artifacts.json"), "artifact_hashes": manifest,
        "array_fields_compared": comparisons, "max_errors": maximum, "poison_variants_bit_equal": poison_count,
        "export_counts": {k: len(calibration[k]) for k in ("bodies", "sites", "geometries")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"audit_scope": "independent post-result source review and stored-evidence arithmetic; no new experiment",
        "source_sha256": SOURCE_HASH, "candidate_witness": candidate_audit(args.raw_root),
        "robot_geometry": robot_audit(args.raw_root), "passed": True}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": True, "output": str(args.output), "contract_valid_witnesses":
                      result["candidate_witness"]["contract_valid_sampled_contact_free_progress_arms"]}))


if __name__ == "__main__":
    main()
