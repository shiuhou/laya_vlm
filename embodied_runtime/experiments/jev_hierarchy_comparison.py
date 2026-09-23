"""Fresh same-condition execution of original Jev with frozen original answers.

This is an architecture comparison, not a new model-quality sample.  The original
Jev hierarchy and simulator run from reset; archived controls are never loaded.
Every newly computed model request must equal the archived successful request,
apart from logged one-unit numeric display quantization, before its original Jev
answer can be returned.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import numbers
from pathlib import Path
import subprocess

import numpy as np


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def git_identity(path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()
    return {"root": str(Path(path).resolve()), "commit": git("rev-parse", "HEAD"),
            "dirty_status": git("status", "--porcelain")}


def numeric_only_differences(fresh, archived, path=""):
    """Return numeric leaf differences, or None for any structural/text difference."""
    if isinstance(fresh, dict) and isinstance(archived, dict):
        if fresh.keys() != archived.keys():
            return None
        result = []
        for key in fresh:
            child = numeric_only_differences(fresh[key], archived[key], f"{path}/{key}")
            if child is None:
                return None
            result.extend(child)
        return result
    if isinstance(fresh, list) and isinstance(archived, list):
        if len(fresh) != len(archived):
            return None
        result = []
        for index, (fresh_item, archived_item) in enumerate(zip(fresh, archived, strict=True)):
            child = numeric_only_differences(
                fresh_item, archived_item, f"{path}/{index}"
            )
            if child is None:
                return None
            result.extend(child)
        return result
    if fresh == archived:
        return []
    def numeric(value):
        return isinstance(value, numbers.Real) and not isinstance(value, bool)
    if numeric(fresh) and numeric(archived):
        return [{"path": path, "fresh": fresh, "archived": archived,
                 "absolute_difference": abs(float(fresh) - float(archived))}]
    return None


class FrozenOriginalAnswers:
    """Original responses gated by exact or logged numeric-quantized requests."""

    source_rows = ()
    source_sha256 = None
    instances = []
    displayed_numeric_tolerance = 0.0100001

    def __init__(self, out, *_args, **_kwargs):
        self.out = Path(out)
        self.total = 0.0
        self.calls = 0
        self.index = 0
        self.numeric_equivalences = []
        type(self).instances.append(self)

    def choose(self, step, layer, state, instructions, criteria):
        if self.index >= len(self.source_rows):
            raise RuntimeError("fresh hierarchy requested more decisions than archived Jev")
        original = self.source_rows[self.index]
        request = {"model": original["request"]["model"], "state": state,
                   "questions": {layer: {"type": "choice", "instructions": instructions,
                                          "criteria": criteria}}}
        same_position = (step, layer) == (original["step"], original["layer"])
        exact_request = request == original["request"]
        numeric_differences = (numeric_only_differences(request, original["request"])
                               if same_position and not exact_request else [])
        quantization_equivalent = (numeric_differences is not None
            and all(row["absolute_difference"] <= self.displayed_numeric_tolerance
                    for row in numeric_differences))
        if not same_position or (not exact_request and not quantization_equivalent):
            mismatch = {
                "call_index": self.index,
                "fresh": {"step": step, "layer": layer, "request": request},
                "archived": {"step": original["step"], "layer": original["layer"],
                             "request": original["request"]},
                "numeric_only_differences": numeric_differences,
                "displayed_numeric_tolerance": self.displayed_numeric_tolerance,
            }
            (self.out / "request-mismatch.json").write_text(
                json.dumps(mismatch, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(f"fresh hierarchy request diverged at call {self.index}: {step}/{layer}")
        request_match = "exact"
        if not exact_request:
            request_match = "displayed_numeric_quantization_equivalent"
            equivalence = {"call_index": self.index, "step": step, "layer": layer,
                "differences": numeric_differences,
                "displayed_numeric_tolerance": self.displayed_numeric_tolerance}
            self.numeric_equivalences.append(equivalence)
            with (self.out / "request-numeric-equivalences.jsonl").open(
                    "a", encoding="utf-8") as stream:
                stream.write(json.dumps(equivalence, ensure_ascii=False) + "\n")
        response = original["response"]
        choice = response["answers"][layer]["choice"]
        if choice not in criteria:
            raise RuntimeError("archived Jev answer is not in fresh candidate pool")
        with (self.out / "api.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"step": step, "layer": layer, "request": request,
                "response": response, "response_source": "archived_original_jev",
                "source_sha256": self.source_sha256, "source_call_index": self.index,
                "request_match": request_match},
                ensure_ascii=False) + "\n")
        self.total += float(response["usage"]["cost"])
        self.calls += 1
        self.index += 1
        return choice

    def close(self):
        (self.out / "answer-consumption.json").write_text(
            json.dumps({"consumed": self.index, "available": len(self.source_rows),
                        "complete": self.index == len(self.source_rows),
                        "exact_requests": self.index - len(self.numeric_equivalences),
                        "numeric_quantization_equivalences": len(self.numeric_equivalences)},
                       indent=2) + "\n",
            encoding="utf-8",
        )


def rotation_distance_deg(a, b):
    relative = np.asarray(a) @ np.asarray(b).T
    return float(np.degrees(np.arccos(np.clip((np.trace(relative) - 1) / 2, -1., 1.))))


def run(args):
    from jev_libero import runner
    from jev_libero.actions import ACTIONS
    from jev_libero.config import load_task

    output = Path(args.output)
    archive = Path(args.archive)
    laya_evidence = Path(args.laya_evidence)
    archived_api = archive / "api.jsonl.gz"
    source_rows = read_jsonl(archived_api)
    FrozenOriginalAnswers.source_rows = source_rows
    FrozenOriginalAnswers.source_sha256 = file_hash(archived_api)
    FrozenOriginalAnswers.instances = []

    archived_task = json.loads((archive / "task_config.json").read_text())
    archived_config = json.loads((archive / "config.json").read_text())
    archived_initial = json.loads((archive / "initial_state.json").read_text())
    current_task = load_task("top_drawer")
    task_config_exact = current_task == archived_task
    normalized_current_task = dict(current_task)
    measurement_declaration = normalized_current_task.pop("measurements", None)
    task_config_semantics_exact = (normalized_current_task == archived_task
        and measurement_declaration == {"joint_position": {"kind": "joint_position"}})
    if not task_config_semantics_exact:
        raise RuntimeError("current original Jev task config has a behavioral archive mismatch")
    if ACTIONS != archived_config["candidate_controls"]:
        raise RuntimeError("current original Jev action vocabulary differs from archive")

    if args.analyze_existing:
        if not output.is_dir():
            raise RuntimeError("--analyze-existing requires an existing output directory")
        result = json.loads((output / "summary.json").read_text())
        instance = FrozenOriginalAnswers(output)
        existing_api = read_jsonl(output / "api.jsonl")
        instance.index = len(existing_api)
        equivalence_path = output / "request-numeric-equivalences.jsonl"
        instance.numeric_equivalences = (read_jsonl(equivalence_path)
                                         if equivalence_path.exists() else [])
    else:
        original_decisions = runner.Decisions
        runner.Decisions = FrozenOriginalAnswers
        try:
            result = runner.run("top_drawer", output, seed=1, init_state=0,
                max_decisions=100, budget_usd=.1, lookahead=2, render=True,
                libero_root=args.libero_root, config_dir=args.config_dir,
                provider="openrouter")
        finally:
            runner.Decisions = original_decisions
        instance = FrozenOriginalAnswers.instances[0]
    if result["termination"] == "error":
        raise RuntimeError(f"fresh original Jev run failed: {result['error']}")
    fresh_initial = json.loads((output / "initial_state.json").read_text())
    trace = read_jsonl(output / "trace.jsonl")
    previews = read_jsonl(output / "predictions.jsonl")
    api = read_jsonl(output / "api.jsonl")
    measurement_path = output / "measurements.jsonl"
    measurements = read_jsonl(measurement_path) if measurement_path.exists() else []
    last_measurement = {}
    for row in measurements:
        last_measurement[row["decision"]] = row["features"]
    if len(trace) != len(previews):
        raise RuntimeError("fresh Jev physical evidence is incomplete")

    reference_rows = read_jsonl(Path(args.reference_raw))
    reference_environment = next(r["data"] for r in reference_rows if r["kind"] == "environment")
    initial_archive_differences = numeric_only_differences(fresh_initial, archived_initial)
    initial_archive_numeric_tolerance = 1e-9
    initial_archive_numerically_equal = (initial_archive_differences is not None
        and all(row["absolute_difference"] <= initial_archive_numeric_tolerance
                for row in initial_archive_differences))
    condition = {
        "task_config_exact": task_config_exact,
        "task_config_semantics_exact": task_config_semantics_exact,
        "task_config_mismatch": ({"current_only": {
            "measurements": measurement_declaration},
            "classification": "explicit declaration of the archived legacy joint-position default"}
            if not task_config_exact else None),
        "action_vocabulary_exact": ACTIONS == archived_config["candidate_controls"],
        "task": archived_task["binding"]["task"],
        "init_state": archived_config["initial_state"],
        "seed": archived_config["seed"],
        "horizon_environment_steps": archived_config["horizon_environment_steps"],
        "collision_aware": archived_config["collision_aware"],
        "lookahead": 2,
        "success_predicate": archived_task["binding"]["success"],
        "initial_features_equal_archive": fresh_initial == archived_initial,
        "initial_features_numerically_equal_archive": initial_archive_numerically_equal,
        "initial_archive_numeric_differences": initial_archive_differences,
        "initial_archive_numeric_tolerance": initial_archive_numeric_tolerance,
        "initial_features_equal_flat_laya": fresh_initial == reference_environment["features"],
        "all_policy_requests_exact": (instance.index == len(source_rows) == len(api)
                                      and not instance.numeric_equivalences),
        "all_policy_requests_quantization_equivalent": (
            instance.index == len(source_rows) == len(api)),
        "policy_request_numeric_equivalences": instance.numeric_equivalences,
        "policy_request_displayed_numeric_tolerance": instance.displayed_numeric_tolerance,
        "archived_controls_loaded": False,
        "archived_model_answers_used": True,
        "fresh_simulator_reset": True,
        "geometry_label_archive": archived_config["geometry_distance_backend"],
        "geometry_label_current": json.loads((output / "config.json").read_text())["geometry_distance_backend"],
        "geometry_label_text_equal": (archived_config["geometry_distance_backend"]
                                      == json.loads((output / "config.json").read_text())["geometry_distance_backend"]),
        "geometry_label_note": ("wording changed; fresh initial features match exactly; policy "
                                "requests are separately labeled exact or numeric-quantization-equivalent"),
        "comparison_repository": git_identity(Path(__file__).resolve().parents[2]),
        "comparison_script_sha256": file_hash(__file__),
        "jev_repository": git_identity(Path(__file__).resolve().parents[3] / "jev-libero"),
        "libero_repository": git_identity(args.libero_root),
        "archived_api_sha256": FrozenOriginalAnswers.source_sha256,
    }
    condition["same_physical_condition"] = all(condition[key] for key in (
        "task_config_semantics_exact", "action_vocabulary_exact",
        "initial_features_numerically_equal_archive", "initial_features_equal_flat_laya",
        "all_policy_requests_quantization_equivalent", "fresh_simulator_reset"))
    if not condition["same_physical_condition"]:
        raise RuntimeError("same-condition gate failed")

    boundaries = []
    for t, p in zip(trace, previews, strict=True):
        if t["step"] in last_measurement:
            after = last_measurement[t["step"]]
            after_source = "recorded_execution_measurement"
        else:
            after = p["predictions"][t["choice"]]["after"]
            after_source = "selected_preview_after_with_execution_state_check"
        by_intent = t["eligible_by_intent"]
        union = {name for pool in by_intent.values() for name in pool}
        boundaries.append({"step": t["step"], "intent": t["intent"],
            "intent_reviewed": t["reviewed_intent"], "strategy": t["strategy"],
            "contract_union_count": len(union),
            "intent_pool_count": len(by_intent[t["intent"]]),
            "motor_candidate_pool": t["eligible_motor"],
            "motor_candidate_count": len(t["eligible_motor"]),
            "selected_primitive": t["choice"],
            "pool_source": "lookahead" if p["two_step_evaluations"] else "one_step",
            "before": p["before"], "after": after, "after_source": after_source,
            "actual_closure_mm": t["actual_progress"], "official_success": t["success"],
            "prediction_state_max_error": t["prediction_state_max_error"]})

    laya = json.loads(laya_evidence.read_text())
    laya_trace = laya["trace"]
    jev_initial = previews[0]["before"]
    laya_initial = laya_trace[0]["outcome"]["before"]
    if jev_initial != laya_initial:
        raise RuntimeError("Jev and flat Laya decision boundary zero differ")
    first = {
        "same_initial_physical_state": True,
        "jev": {"intent": boundaries[0]["intent"], "strategy": boundaries[0]["strategy"],
                "motor_pool": boundaries[0]["motor_candidate_pool"],
                "choice": boundaries[0]["selected_primitive"]},
        "laya": {"pool": laya_trace[0]["candidates"],
                 "choice": laya_trace[0]["outcome"]["action"]},
        "first_action_divergence": "Jev x+40mm vs flat Laya x+3mm",
        "both_actions_in_jev_motor_pool": all(x in boundaries[0]["motor_candidate_pool"]
                                               for x in ("x+40mm", "x+3mm")),
        "interpretation": "divergence occurs inside the same hierarchy-selected motor family",
    }
    if len(boundaries) > 1 and len(laya_trace) > 1:
        first["first_cross_axis_divergence"] = {
            "decision": 1, "jev": boundaries[1]["selected_primitive"],
            "flat_laya": laya_trace[1]["outcome"]["action"],
            "jev_opening_before_mm": boundaries[1]["before"]["remaining_open_mm"],
            "laya_opening_before_mm": laya_trace[1]["outcome"]["before"]["remaining_open_mm"],
        }

    laya_terminal = laya_trace[-1]["outcome"]["after"]
    nearest = []
    for b in boundaries:
        a = b["after"]
        nearest.append({"jev_step": b["step"],
            "eef_distance_mm": float(np.linalg.norm(np.asarray(a["eef_mm"])
                                                     - np.asarray(laya_terminal["eef_mm"]))),
            "rotation_distance_deg": rotation_distance_deg(
                a["eef_rotation_matrix"], laya_terminal["eef_rotation_matrix"]),
            "opening_difference_mm": abs(a["remaining_open_mm"]
                                          - laya_terminal["remaining_open_mm"]),
            "jev_contact": a["moving_contact"], "laya_contact": laya_terminal["moving_contact"],
            "jev_opening_mm": a["remaining_open_mm"],
            "jev_gap_mm": a["distance_to_moving_geometry_mm"]})
    nearest_pose = min(nearest, key=lambda x: (x["eef_distance_mm"], x["rotation_distance_deg"]))
    nearest_opening = min(nearest, key=lambda x: x["opening_difference_mm"])
    dead_end = {"laya_terminal": laya_terminal, "visited_exactly": any(
        n["eef_distance_mm"] < 1e-6 and n["rotation_distance_deg"] < 1e-6
        and n["opening_difference_mm"] < 1e-6 for n in nearest),
        "nearest_jev_by_pose": nearest_pose, "nearest_jev_by_opening": nearest_opening}

    alignment = []
    for b in boundaries:
        nearest_laya = min(laya_trace, key=lambda t: abs(
            t["outcome"]["after"]["remaining_open_mm"] - b["after"]["remaining_open_mm"]))
        alignment.append({"jev_step": b["step"], "jev_action": b["selected_primitive"],
            "jev_opening_mm": b["after"]["remaining_open_mm"],
            "nearest_laya_step": nearest_laya["step"],
            "nearest_laya_action": nearest_laya["outcome"]["action"],
            "nearest_laya_opening_mm": nearest_laya["outcome"]["after"]["remaining_open_mm"],
            "opening_difference_mm": abs(nearest_laya["outcome"]["after"]["remaining_open_mm"]
                                         - b["after"]["remaining_open_mm"])})

    evidence = {"version": "jev-hierarchy-same-condition-v1",
        "comparison_type": "fresh_simulation_with_frozen_original_jev_answers",
        "condition": condition, "result": result, "boundaries": boundaries,
        "earliest_divergence": first, "progress_alignment": alignment,
        "laya_dead_end_comparison": dead_end,
        "hierarchy": {"intent_review_steps": [b["step"] for b in boundaries if b["intent_reviewed"]],
            "intent_calls": result["intent_calls"], "strategy_calls": result["strategy_calls"],
            "lookahead_steps": [b["step"] for b in boundaries if b["pool_source"] == "lookahead"],
            "per_step_reductions": [{"step": b["step"],
                "contract_union": b["contract_union_count"],
                "intent_pool": b["intent_pool_count"], "motor_pool": b["motor_candidate_count"]}
                for b in boundaries]},
        "artifact_sha256": {name: file_hash(output / name) for name in
            ("api.jsonl", "predictions.jsonl", "trace.jsonl", "sim_trajectory.npz",
             "summary.json", "task_config.json", "initial_state.json")},
        "execution_measurement_note": ("The original task config does not set record_features, "
            "so boundary contact/gap/opening use the selected preview endpoint. Each endpoint is "
            "backed by trace.prediction_state_max_error against the freshly executed simulator; "
            "actual closure and official success come from the execution trace.")}
    evidence_path = output / "architecture-comparison.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")

    lines = ["# Original Jev same-condition hierarchy comparison", "",
        "Fresh simulator execution with frozen original Jev answers. Archived controls were not loaded.", "",
        f"Same physical condition: **{condition['same_physical_condition']}**. ",
        f"Official success: **{result['success']}** in {result['decisions']} decisions.", "",
        "| Step | Intent | Strategy | Union -> intent -> motor | Motor candidates | Choice | Pool | Opening mm | Gap mm | Target contact | Obstacle contact | Closure mm | Success |",
        "|---:|---|---|---|---|---|---|---:|---:|---|---|---:|---|"]
    for b in boundaries:
        a = b["after"]
        lines.append(f"| {b['step']} | {b['intent']} | {b['strategy']} | "
            f"{b['contract_union_count']} -> {b['intent_pool_count']} -> {b['motor_candidate_count']} | "
            f"{', '.join(b['motor_candidate_pool'])} | `{b['selected_primitive']}` | {b['pool_source']} | "
            f"{a['remaining_open_mm']:.6f} | {a['distance_to_moving_geometry_mm']:.6f} | "
            f"{str(a['moving_contact']).lower()} | {str(a['obstacle_contact']).lower()} | "
            f"{b['actual_closure_mm']:.6f} | {str(b['official_success']).lower()} |")
    lines += ["", "Full conditions, physical-progress alignment, pose distances and artifact hashes: architecture-comparison.json."]
    (output / "architecture-comparison.md").write_text("\n".join(lines) + "\n")
    return evidence


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--archive", default="/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1")
    p.add_argument("--laya-evidence", default=(
        "/home/junhongli/projects/laya-embodied-runtime/runs/privileged-reference/"
        "forced-singleton-episode-01/reference-evidence.json"))
    p.add_argument("--reference-raw", default=(
        "/home/junhongli/projects/laya-embodied-runtime/runs/privileged-reference/"
        "forced-singleton-episode-01/episodes.jsonl"))
    p.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    p.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    p.add_argument("--analyze-existing", action="store_true",
        help="Finalize evidence from an already completed fresh run without rerunning it")
    return p


def main():
    evidence = run(parser().parse_args())
    print(json.dumps({"same_physical_condition": evidence["condition"]["same_physical_condition"],
        "success": evidence["result"]["success"], "decisions": evidence["result"]["decisions"],
        "earliest_divergence": evidence["earliest_divergence"],
        "laya_dead_end_comparison": evidence["laya_dead_end_comparison"]}, indent=2))


if __name__ == "__main__":
    main()
