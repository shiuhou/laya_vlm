"""Pure raw-evidence analysis; diagnostic interventions never replace native probes."""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from ..runtime_core import MOVE, _sha256_json
from .records import file_hash, load_records

VERSION = "operating-regime-report-v0.1"
TOKENS = tuple(MOVE) + ("ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP", "RELEASE")
TOLERANCES = {"position_m": .0001, "rotation_deg": .01, "aperture_m": .0001,
              "opening_mm": .1, "duration_s": 1e-9}


def _array(value, shape):
    array = np.asarray(value, dtype=float)
    return array if array.shape == shape and np.isfinite(array).all() else None


def _delta(before, after, key):
    a, b = _array(before.get(key), (3,)), _array(after.get(key), (3,))
    return None if a is None or b is None else (b - a).tolist()


def _difference(a, b):
    return None if a is None or b is None else a - b


def _norm(value):
    return None if value is None else float(np.linalg.norm(value))


def _rotation(a, b):
    a, b = _array(a, (3, 3)), _array(b, (3, 3))
    return None if a is None or b is None else a @ b.T


def _angle(rotation):
    return None if rotation is None else float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1., 1.))))


def _commands(probe):
    execution = probe.get("execution", {})
    return execution.get("low_level_commands", execution.get("commands"))


def _horizon(a, b):
    values = (a["duration_s"], b["duration_s"], a["environment_steps"], b["environment_steps"])
    return None if any(v is None for v in values) else (
        abs(values[0] - values[1]) <= TOLERANCES["duration_s"] and values[2] == values[3])


def probe_metrics(probe):
    before, after = probe.get("before", {}), probe.get("after", {})
    execution = probe.get("execution", {})
    features_before, features_after = probe.get("features_before", {}), probe.get("features_after", {})
    fk, observed = _delta(before, after, "tcp_fk_m"), _delta(before, after, "tcp_observed_m")
    rotation = _rotation(after.get("orientation_fk"), before.get("orientation_fk"))
    token = probe["token"]
    expected = np.asarray(MOVE.get(token, (0., 0., 0.))) * .01
    theta = np.radians({"ROTATE_CW": -10., "ROTATE_CCW": 10.}.get(token, 0.))
    nominal_rotation = np.array([[np.cos(theta), -np.sin(theta), 0.], [np.sin(theta), np.cos(theta), 0.], [0., 0., 1.]])
    traces = probe.get("control_trace", [])
    clips = [row.get("inner", {}).get("clipped_steps_by_joint") for row in traces]
    clips_known = bool(clips) and all(c is not None for c in clips)
    clip_total = np.sum(clips, axis=0).tolist() if clips_known else None
    return {"token": token, "variant": probe["variant"], "repeat": probe["repeat"],
            "traced": probe.get("traced"), "fk_delta_m": fk, "observed_delta_m": observed,
            "fk_displacement_m": _norm(fk), "observed_displacement_m": _norm(observed),
            "fk_vs_observed_delta_error_m": None if fk is None or observed is None else _norm(np.asarray(fk) - observed),
            "fk_nominal_translation_error_m": None if fk is None else _norm(np.asarray(fk) - expected),
            "fk_rotation_deg": _angle(rotation),
            "fk_nominal_rotation_error_deg": _angle(None if rotation is None else rotation @ nominal_rotation.T),
            "execution_reported_delta_m": execution.get("delta_m"),
            "execution_reported_rotation_deg": execution.get("rotation_angle_deg"),
            "closure_mm": _difference(features_before.get("remaining_open_mm"), features_after.get("remaining_open_mm")),
            "opening_after_mm": features_after.get("remaining_open_mm"),
            "contact_after": features_after.get("moving_contact"), "obstacle_after": features_after.get("obstacle_contact"),
            "success_after": features_after.get("success"), "contacts_after": features_after.get("contacts"),
            "aperture_before_m": before.get("gripper_width_joint_m"), "aperture_after_m": after.get("gripper_width_joint_m"),
            "aperture_delta_m": _difference(after.get("gripper_width_joint_m"), before.get("gripper_width_joint_m")),
            "grip_command_before": before.get("gripper_command"), "grip_command_after": after.get("gripper_command"),
            "duration_s": _difference(after.get("sim_time"), before.get("sim_time")),
            "environment_steps": execution.get("environment_step_count"), "low_level_steps": execution.get("low_level_step_count"),
            "contract_violation": execution.get("execution_contract_violation"),
            "contract_reasons": execution.get("execution_contract_reason"),
            "torque_clipped_steps_by_joint": clip_total, "torque_clipped_joint_steps_total": None if clip_total is None else sum(clip_total),
            "traced_physics_steps": sum(r["inner"]["physics_steps"] for r in traces) if traces else None,
            "before_goal_orientation_error_deg": before.get("controller_goal_ori_error_deg"),
            "after_goal_orientation_error_deg": after.get("controller_goal_ori_error_deg"),
            "trace_entry_goal_orientation_error_deg": traces[0].get("before", {}).get("controller_goal_ori_error_deg") if traces else None,
            "max_controller_position_error_m": max((r["inner"]["max_position_tracking_error_m"] for r in traces
                if r.get("inner", {}).get("max_position_tracking_error_m") is not None), default=None),
            "max_controller_orientation_error_deg": max((r["inner"]["max_orientation_tracking_error_deg"] for r in traces
                if r.get("inner", {}).get("max_orientation_tracking_error_deg") is not None), default=None),
            "before_speed_mps": _norm(before.get("velocity_fk_mps")),
            "restore": probe.get("restore"), "endpoint_context_id": probe.get("endpoint_context_id"),
            "command_id": None if _commands(probe) is None else _sha256_json(_commands(probe)),
            "sim_endpoint_id": None if probe.get("sim_state_after") is None else _sha256_json(probe["sim_state_after"])}


def compare_probes(a, b, ma, mb):
    """Pairwise only: near endpoint telemetry is not equivalence or safety."""
    horizon = _horizon(ma, mb)
    commands = None if ma["command_id"] is None or mb["command_id"] is None else ma["command_id"] == mb["command_id"]
    sim = None if ma["sim_endpoint_id"] is None or mb["sim_endpoint_id"] is None else ma["sim_endpoint_id"] == mb["sim_endpoint_id"]
    position = _norm(_delta(a.get("after", {}), b.get("after", {}), "tcp_fk_m"))
    angle = _angle(_rotation(a.get("after", {}).get("orientation_fk"), b.get("after", {}).get("orientation_fk")))
    gaps = {"position_m": position, "rotation_deg": angle,
            "aperture_m": _difference(ma["aperture_after_m"], mb["aperture_after_m"]),
            "opening_mm": _difference(ma["opening_after_mm"], mb["opening_after_mm"])}
    discrete = [ma[key] == mb[key] if ma[key] is not None and mb[key] is not None else None
                for key in ("contact_after", "obstacle_after", "success_after", "grip_command_after")]
    known = horizon is not None and all(v is not None for v in gaps.values()) and None not in discrete
    return {"a": [ma["token"], ma["variant"], ma["repeat"]], "b": [mb["token"], mb["variant"], mb["repeat"]],
            "equal_horizon": horizon, "exact_commands_equal": commands, "exact_sim_endpoint_equal": sim,
            "exact_command_and_sim_alias": None if commands is None or sim is None else commands and sim,
            "endpoint_context_equal": None if ma["endpoint_context_id"] is None or mb["endpoint_context_id"] is None else ma["endpoint_context_id"] == mb["endpoint_context_id"],
            "endpoint_differences": gaps,
            "near_endpoint_telemetry_only": None if not known else horizon and all(discrete) and all(abs(v) <= TOLERANCES[k] for k, v in gaps.items())}


def summarize(source):
    path = Path(source)
    if path.is_dir():
        path /= "episodes.jsonl"
    records, tail = load_records(path)
    boundaries, probes, starts, failures, terminations = {}, {}, set(), list(tail), []
    for row in records:
        kind, data = row["kind"], row["data"]
        if kind == "regime_boundary":
            if data["context_id"] in boundaries:
                raise ValueError("duplicate regime boundary identity")
            boundaries[data["context_id"]] = data
        elif kind in ("regime_probe", "regime_probe_started"):
            key = (data["context_id"], data["token"], data["variant"], data["repeat"])
            if key[0] not in boundaries:
                raise ValueError("probe lacks preceding boundary")
            if kind == "regime_probe_started":
                if key in starts:
                    raise ValueError("duplicate regime probe intent")
                starts.add(key)
            else:
                if key in probes:
                    raise ValueError("duplicate completed regime probe identity")
                if key not in starts:
                    raise ValueError("probe lacks preceding execution intent")
                if data.get("not_supplied_to_model") is not True:
                    raise ValueError("regime probes must be marked evaluator-only")
                probes[key] = (data, row["record_id"])
        elif kind == "failure":
            failures.append(data)
        elif kind == "termination":
            terminations.append(data)
    if not terminations:
        failures.append({"category": "run_incomplete", "detail": "no termination record"})
    for key in sorted(starts - probes.keys()):
        failures.append({"category": "probe_outcome_unknown", "probe_identity": key})
    result = []
    for context, boundary in boundaries.items():
        local = {key[1:]: item for key, item in probes.items() if key[0] == context}
        measured = {key: {**probe_metrics(item[0]), "raw_record_id": item[1]} for key, item in local.items()}
        stop_key = ("STOP", "native", 0)
        for key, metric in measured.items():
            stop = measured.get(stop_key)
            equal = None if stop is None else _horizon(metric, stop)
            metric.update(equal_horizon_to_native_stop=equal, closure_vs_native_stop_mm=None,
                          fk_delta_vs_native_stop_m=None, fk_endpoint_rotation_vs_native_stop_deg=None)
            if equal is True:
                metric["closure_vs_native_stop_mm"] = _difference(metric["closure_mm"], stop["closure_mm"])
                if metric["fk_delta_m"] is not None and stop["fk_delta_m"] is not None:
                    metric["fk_delta_vs_native_stop_m"] = (np.asarray(metric["fk_delta_m"]) - stop["fk_delta_m"]).tolist()
                metric["fk_endpoint_rotation_vs_native_stop_deg"] = _angle(_rotation(local[key][0]["after"].get("orientation_fk"), local[stop_key][0]["after"].get("orientation_fk")))
            if metric["restore"] is None or metric["restore"].get("context_matches") is not True or metric["restore"].get("sim_max_error") != 0.:
                failures.append({"category": "restore_not_verified", "context_id": context, "probe_identity": key, "restore": metric["restore"]})
        native = [key for key in local if key[1:] == ("native", 0)]
        pairs = [compare_probes(local[a][0], local[b][0], measured[a], measured[b]) for a, b in combinations(native, 2)]
        diagnostics = [compare_probes(local[stop_key][0], local[k][0], measured[stop_key], measured[k])
                       for k in local if k != stop_key and k[0] == "STOP"] if stop_key in local else []
        expected = [(token, "native", 0) for token in TOKENS] + [("STOP", "native", 1)]
        expected += [("STOP", variant, 0) for variant in ("reanchor_orientation", "fk_feedback", "both")]
        result.append({**boundary, "probes": list(measured.values()), "missing_expected_probes": [key for key in expected if key not in local],
                       "native_pairwise_comparisons": pairs, "stop_diagnostic_comparisons": diagnostics})
    orphans = [key for key in probes if key[0] not in boundaries]
    return {"version": VERSION, "source": str(path), "source_sha256": file_hash(path), "terminations": terminations,
            "near_alias_tolerances": TOLERANCES, "nominal": {"translation_m": .01, "rotation_world_z_deg": 10.},
            "near_alias_scope": "pairwise endpoint telemetry only; not transitive, not full-controller equivalence, not safety",
            "failures": failures, "orphan_probe_identities": orphans, "boundaries": result,
            "completed_probe_count": len(probes), "native_probe_count": sum(k[2:] == ("native", 0) for k in probes),
            "contract_violation_count": sum(m["contract_violation"] is True for b in result for m in b["probes"]),
            "evidence_complete": bool(terminations) and bool(result) and not failures and not orphans
            and not any(b["missing_expected_probes"] for b in result)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--output", help="new derived directory; omit for JSON stdout")
    args = parser.parse_args()
    report = summarize(args.source)
    if not args.output:
        print(json.dumps(report, indent=2, allow_nan=False))
        return
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "operating_regime_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    rows = [{"context_id": b["context_id"], "init_state_id": b["physical"].get("init_state_id"),
             "boundary_step": b["physical"].get("environment_step"), **m} for b in report["boundaries"] for m in b["probes"]]
    with (output / "operating_regime_probes.csv").open("w", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)
    print(output)


if __name__ == "__main__":
    main()
