"""Offline evidence inspector and media from recorded frames; never re-simulates."""
from __future__ import annotations

import json
import argparse
from math import isfinite
from pathlib import Path
import shutil
import subprocess
import textwrap

import numpy as np

from .records import file_hash, load_records, summarize


def evidence(directory):
    """Derive a decision-by-decision audit, including unfinished attempts.

    Hash/identity corruption is fatal. Missing stages and failed model audits are
    visible issues, never inferred completions or positive connectivity evidence.
    """
    from .engineering_demo import DemoView
    from .records import jsonable, restore_snapshot
    directory = Path(directory)
    rows, errors = load_records(directory / "episodes.jsonl")
    if errors:
        raise ValueError("incomplete raw record; do not present as a clean demo")
    summarize(directory)

    def by(kind, key="step"):
        result = {}
        for row in rows:
            if row["kind"] == kind:
                value = row["data"]
                identity = value[key]
                if identity in result:
                    raise ValueError(f"duplicate {kind}")
                result[identity] = value
        return result

    snapshots = by("snapshot")
    actions, decisions, starts = by("action"), by("decision"), by("execution_started")
    inputs, responses = by("demo_model_input", "snapshot_id"), by("demo_model_response", "snapshot_id")
    trajectories, boundaries = by("demo_trajectory"), by("demo_boundary")
    captures, detections = by("vision_capture", "capture_seq"), by("vision_completed", "capture_seq")
    evaluations = {}
    capture_for_snapshot, observations, pending_observations, last_capture = {}, {}, [], None
    manifest, config = {}, {}
    for row in rows:
        value = row["data"]
        if row["kind"] == "run_start":
            manifest = dict(value.get("manifest", {}))
            config = value["resolved_config"]
        elif row["kind"] == "manifest_update":
            manifest.update(value)
        elif row["kind"] == "evaluation":
            key = (value["step"], value["phase"])
            if key in evaluations:
                raise ValueError("duplicate evaluation")
            evaluations[key] = value
        elif row["kind"] == "vision_capture":
            last_capture = value["capture_seq"]
            pending_observations = []
        elif row["kind"] == "observation":
            pending_observations.append(value)
        elif row["kind"] == "snapshot":
            # Historical v1 had no explicit boundary event. Link by record order,
            # not list index, so an unfinished capture cannot shift later rows.
            capture_for_snapshot[value["step"]] = last_capture
            observations[value["step"]] = list(pending_observations)
    for trajectory in trajectories.values():
        if file_hash(directory / trajectory["artifact"]) != trajectory["sha256"]:
            raise ValueError("trajectory artifact mismatch")
    attempts, completed = [], []
    for step, snapshot in sorted(snapshots.items()):
        sid = snapshot["snapshot_id"]
        model, response = inputs.get(sid), responses.get(sid)
        decision = decisions.get(step, {}).get("decision")
        intent, action = starts.get(step), actions.get(step)
        execution = action["execution"] if action else None
        trajectory = trajectories.get(step)
        capture_seq = boundaries.get(step, {}).get("capture_seq", capture_for_snapshot.get(step))
        capture = captures.get(capture_seq)
        detection = detections.get(capture_seq)
        issues = []
        if capture is None or detection is None:
            issues.append("sensor capture or detection record missing")
        elif capture["capture_sim_time"] != snapshot["snapshot"]["asof_sim_time"]:
            issues.append("capture and decision are not at the same physical boundary")
        if model is None:
            issues.append("model input not recorded")
        else:
            # Reuse the opt-in bridge and shared projection; no second interface.
            view = DemoView(restore_snapshot(snapshot["snapshot"]), config["query"])
            expected = {"state": view.provider_input(), "questions": view.model_questions(),
                "canonical": jsonable(view.canonical), "canonical_input_id": view.canonical.snapshot_id(),
                "belief_id": snapshot["belief_id"], "natural_candidate_set_id": snapshot["candidate_set_id"],
                "singleton_forced_not_model": len(view.allowed()) == 1,
                "oracle": False, "effects": "none", "history": "empty"}
            if any(model.get(k) != v for k, v in expected.items()):
                issues.append("recorded model input differs from the visual demo projection")
            audit = model["audit"]
            if not audit.get("available") or audit.get("truncated"):
                issues.append("model token audit unavailable or clipped")
            if not model["singleton_forced_not_model"]:
                expected_tokens = audit.get("questions", {}).get("action", {})
                traces = (response or {}).get("forward_traces", [])
                if (len(traces) != 1 or not expected_tokens
                    or traces[0]["input_ids"] != [expected_tokens.get("effective_input_ids")]
                    or traces[0]["option_markers"] != [expected_tokens.get("option_markers")]):
                    issues.append("model consumption does not match token audit")
                if decision:
                    answer = (response or {}).get("raw_response", {}).get("answers", {}).get("action", {})
                    if (answer.get("choice") != decision["token"]
                        or answer.get("probabilities", {}) != decision["probabilities"]
                        or decision["source"] != "laya"):
                        issues.append("raw Laya response does not match proposed decision")
            elif response is not None or (decision and decision["source"] != "laya_single_candidate"):
                issues.append("singleton incorrectly attributed to model inference")
        if decision is None:
            issues.append("decision not completed")
        if intent is None:
            issues.append("execution not started")
        elif not intent["fallback_reason"] and intent["decision"] != decision:
            issues.append("validated intent differs from proposed decision without fallback")
        if intent:
            validated = intent["decision"]
            checks = {"input_snapshot_id": sid, "input_belief_id": snapshot["belief_id"],
                "candidate_set_id": snapshot["candidate_set_id"],
                "input_revision": snapshot["snapshot"]["revision"],
                "input_sim_time": snapshot["snapshot"]["asof_sim_time"]}
            allowed = {c["token"] for c in snapshot["snapshot"]["candidates"] if c["feasible"]}
            if (any(validated.get(k) != v for k, v in checks.items())
                or validated["token"] not in allowed
                or not isfinite(validated["valid_until_sim"])
                or validated["valid_until_sim"] < intent["execution_sim_time"]
                or validated["status"] != ("fallback" if intent["fallback_reason"] else "valid")):
                issues.append("executor intent fails identity, membership, expiry or status audit")
            if intent["fallback_reason"] and (validated["source"] != "fallback" or validated["token"] != "STOP"):
                issues.append("fallback intent is not the recorded STOP fallback")
        if execution is None:
            issues.append("execution outcome unknown" if intent else "no execution outcome")
        if trajectory is None:
            issues.append("trajectory not recorded")
        elif execution:
            with np.load(directory / trajectory["artifact"], allow_pickle=False) as archive:
                count = execution["environment_step_count"]
                if (not np.array_equal(archive["commands"], execution["low_level_commands"])
                    or any(len(archive[k]) != count for k in ("commands", "states_before", "frames"))
                    or trajectory["frames"] != count):
                    issues.append("trajectory controls or frame counts differ from executor evidence")
        evaluator = {phase: evaluations.get((step, phase)) for phase in ("before", "after")}
        if any(v is None or v.get("oracle_evaluator") is not True for v in evaluator.values()):
            issues.append("evaluator before/after evidence missing or unlabeled")
        classification = ("validation fallback" if intent and intent["fallback_reason"] else
            "forced singleton; no model inference" if model and model["singleton_forced_not_model"] else
            "Laya inference" if response and decision and decision["source"] == "laya" else
            "incomplete or other provider")
        stages = [r for r in rows if r["data"].get("snapshot_id") == sid
                  and r["kind"] in {"snapshot", "demo_model_input", "demo_model_response",
                                    "decision", "execution_started", "action"}]
        order = {kind: index for index, kind in enumerate(
            ("snapshot", "demo_model_input", "demo_model_response", "decision", "execution_started", "action"))}
        stage_order = [order[r["kind"]] for r in stages]
        if stage_order != sorted(set(stage_order)):
            issues.append("decision stages are duplicated or out of causal order")
        attempt = {"step": step, "snapshot_id": sid, "snapshot": snapshot,
            "model_input": model, "raw_response": response, "decision": decision,
            "intent": intent, "execution": execution, "trajectory": trajectory,
            "capture": capture, "detection": detection, "evaluation": evaluator,
            "observations": observations.get(step, []),
            "option_order": [c["token"] for c in (model or {}).get("canonical", {}).get("candidates", [])],
            "classification": classification, "issues": issues,
            "verified_laya_execution": not issues and classification == "Laya inference"}
        attempt["record_links"] = [{"kind": r["kind"], "seq": r["seq"], "record_id": r["record_id"]}
            for r in rows if r["data"].get("step") == step
            or r["data"].get("snapshot_id") == sid
            or (capture_seq is not None and r["data"].get("capture_seq") == capture_seq)]
        attempts.append(attempt)
        if execution and model and decision and intent and trajectory and capture:
            completed.append({**attempt, "proposed": decision["token"], "executed": execution["token"],
                "source": decision["source"], "probabilities": decision["probabilities"],
                "allowed": attempt["option_order"],
                "input_tokens": model["audit"].get("questions", {}).get("action", {}).get("effective_token_count"),
                "fallback_reason": intent["fallback_reason"], "delta_mm": (np.asarray(execution["delta_m"])*1000).tolist(),
                "rotation_deg": execution["rotation_angle_deg"],
                "gripper_before_mm": execution["execution_before"]["finger_gap_m"]*1000,
                "gripper_after_mm": execution["execution_after"]["finger_gap_m"]*1000,
                "contract_violation": execution["execution_contract_violation"],
                "contract_reasons": execution["execution_contract_reason"], "success": execution["success"],
                "sim_start": execution["execution_before"]["sim_time"], "sim_end": execution["execution_after"]["sim_time"],
                "control_steps": execution["environment_step_count"],
                "observed_box_xyxy": ((detection or {}).get("event") or {}).get("value", {}).get("box_xyxy")})
    source_hash = file_hash(directory / "episodes.jsonl")
    replay = None
    if (directory / "replay-check.json").exists():
        replay = json.loads((directory / "replay-check.json").read_text())
        replay = {"record": replay, "matches_raw_source": replay.get("raw_source_sha256") == source_hash}
    terminations = [r["data"] for r in rows if r["kind"] == "termination"]
    source_root = Path(__file__).resolve().parents[2]
    return {"source_sha256": source_hash, "steps": completed, "attempts": attempts,
        "report_generator": {"version": "demo-inspector-v1", "source_sha256": {
            str(p.relative_to(source_root)): file_hash(p)
            for p in sorted((source_root / "embodied_runtime").rglob("*.py"))}},
        "failures": [r["data"] for r in rows if r["kind"] == "failure"],
        "termination": terminations, "run_incomplete": not terminations,
        "config": config, "manifest": manifest, "replay": replay,
        "invocation": [r["data"] for r in rows if r["kind"] == "demo_invocation"],
        "unassigned_captures": [c for seq, c in captures.items()
                                if seq not in {a["capture"]["capture_seq"] for a in attempts if a["capture"]}],
        "verified_laya_executions": sum(a["verified_laya_execution"] for a in attempts),
        "purpose": "engineering connectivity; not task competence or research validation"}


def render_report(directory):
    from PIL import Image, ImageDraw, ImageFont
    directory = Path(directory)
    data = evidence(directory)
    from .demo_inspector import write_inspector
    inspector = write_inspector(directory, data)
    if not data["steps"]:
        return inspector
    if data["run_incomplete"] or any(a["issues"] for a in data["attempts"]):
        # The inspector includes partial evidence; media requires a complete audit.
        return inspector
    small = ImageFont.truetype("DejaVuSans.ttf", 14)
    large = ImageFont.truetype("DejaVuSans.ttf", 23)
    frames, durations, tiles = [], [], []

    def annotated(rgb, row, label, sim_time):
        canvas = Image.new("RGB", (1088, 704), "#101b29")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 10), "Laya -> atomic executor -> LIBERO / MuJoCo", font=large, fill="white")
        draw.text((16, 42), "ENGINEERING CONNECTIVITY DEMO | visual input | not a task-success claim", font=small, fill="#9bd5ed")
        canvas.paste(Image.fromarray(rgb).resize((576, 576)), (16, 80))
        if label.startswith("DECISION") and row["observed_box_xyxy"]:
            x1, y1, x2, y2 = row["observed_box_xyxy"]
            sx, sy = 576/rgb.shape[1], 576/rgb.shape[0]
            draw.rectangle((16+x1*sx, 80+y1*sy, 16+x2*sx, 80+y2*sy), outline="#60ffc2", width=3)
            draw.text((20, 636), "Green: sensor detection, not ground truth", font=small, fill="#60ffc2")
        x = 612
        lines = [f"Action {row['step']+1}/{len(data['steps'])}: {row['executed']}", label,
                 f"Simulation time: {sim_time:.2f} s", "", f"Provider source: {row['source']}",
                 f"Run end: {data['termination'][-1]['reason']}; failures: {len(data['failures'])}",
                 f"Allowed choices: {len(row['allowed'])}",
                 f"Proposed: {row['proposed']} -> executed: {row['executed']}",
                 f"Fallback: {row['fallback_reason']}",
                 f"P(proposed): {row['probabilities'].get(row['proposed'], 'unknown')}",
                 "Model probabilities are not calibrated.", f"Input: {row['input_tokens']} tokens, no clipping", "",
                 "Measured action-end evidence:",
                 "TCP delta mm: " + ", ".join(f"{v:+.2f}" for v in row["delta_mm"]),
                 f"Rotation: {row['rotation_deg']:.2f} deg",
                 f"Finger gap: {row['gripper_before_mm']:.1f} -> {row['gripper_after_mm']:.1f} mm",
                 f"Controls: {row['control_steps']} x 0.05 s",
                 f"Contract flag: {row['contract_violation']}", f"Task success: {row['success']}", "",
                 "Evaluator-only endpoint:",
                 f"Drawer remaining: {row['evaluation']['after']['features'].get('remaining_open_mm', 'unknown')} mm",
                 f"Target contact: {row['evaluation']['after']['features'].get('moving_contact', 'unknown')}", "",
                 "No oracle state or preview in Laya input.",
                 "Unknown: contact, holding, drawer progress.",
                 "Current RGB-D + robot proprioception."]
        y = 85
        for line in lines:
            for part in textwrap.wrap(line, 48) or [""]:
                draw.text((x, y), part, font=small, fill="#e4ebf5")
                y += 19
        draw.text((16, 674), "Recorded frames; motion at 0.5x. Decision pauses shortened. Side panel shows action-end telemetry.",
                  font=small, fill="#a8c0d5")
        return canvas

    table = ["| Step | Source | Proposed / executed | Fallback | P(choice) | Allowed | TCP delta mm | Finger gap mm | Contract flag |",
             "|---|---|---|---|---:|---:|---|---|---|"]
    for row in data["steps"]:
        with np.load(directory / row["trajectory"]["artifact"]) as archive:
            rgbs = archive["frames"]
        capture = row["capture"]
        with np.load(directory / capture["artifact"]) as rgbd:
            frames.append(annotated(rgbd["rgb"], row, "DECISION BOUNDARY (paused)", row["sim_start"]))
        durations.append(1800)
        for i, rgb in enumerate(rgbs):
            sim_time = row["sim_start"]+(i+1)*(row["sim_end"]-row["sim_start"])/len(rgbs)
            frames.append(annotated(rgb, row, "PHYSICAL EXECUTION", sim_time))
            durations.append(100)
        tiles.append(frames[-1])
        table.append(f"| {row['step']} | {row['source']} | {row['proposed']} / {row['executed']} | {row['fallback_reason']} | "
            f"{row['probabilities'].get(row['proposed'],0):.4f} | {len(row['allowed'])} | "
            + ", ".join(f"{v:+.3f}" for v in row["delta_mm"])
            + f" | {row['gripper_before_mm']:.2f} -> {row['gripper_after_mm']:.2f} | {row['contract_violation']} |")
    durations[-1] = 1800
    frames[0].save(directory / "demo.gif", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=False)
    sheet = Image.new("RGB", (1088, 704*len(tiles)), "white")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (0, 704*i))
    sheet.save(directory / "contact-sheet.png")
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(directory/"demo.gif"),
            "-an", "-movflags", "+faststart", "-pix_fmt", "yuv420p", str(directory/"demo.mp4")], check=True)
    text = ("# Visual Laya connectivity demonstration\n\n"
        "This is one short live trajectory, not a successful drawer policy or an E0 result.\n\n"
        "[Open the full evidence inspector](demo.html) — exact inputs, candidate vetoes, validation, physical outcomes and failures.\n\n"
        "[MP4 video](demo.mp4) | [Animated GIF](demo.gif)\n\n"
        "![Recorded demonstration](demo.gif)\n\n" + "\n".join(table) + "\n\n"
        "Pipeline: fresh RGB-D -> LocateAnything + depth -> temporal belief -> CDS v0.1 compact state "
        "+ natural feasible atomic choices -> Laya -> Runtime validation -> AtomicExecutor -> MuJoCo.\n\n"
        "Simulation pauses for perception and decisions. The demo-only bridge changes presentation, "
        "not runtime gates or atomic physics. No effects, rankings, rule fallback policy, oracle target, "
        "contact or progress enter model input. Full natural soft metadata remains audit-only. "
        "Actual raw inputs, probabilities, consumed tokens, commands and simulator states are retained. "
        "A selected command is not evidence that Laya understood the task; no rationale is inferred.\n\n"
        f"Recorded failures: {len(data['failures'])}. Termination: `{data['termination']}`.\n\n"
        "Unknown perceptual contact/progress stay unknown. Tracking inactive; covariance heuristic. "
        "Reset contract flags are not collision/safety guarantees. A singleton is a forced gate result, "
        "not Laya inference. STOP remains an active controller command, not frozen physics.\n\n"
        "[Full decision inputs and outputs](demo-evidence.json) | [Raw records](episodes.jsonl) | "
        "[Action summary](summary.csv) | [Failure records](failures.csv) | "
        "[Trajectory contact sheet](contact-sheet.png)\n")
    (directory / "demo.md").write_text(text)
    return str(directory / "demo.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="existing recorded run directory")
    parser.add_argument("--media", action="store_true", help="also render GIF/MP4 and contact sheet")
    args = parser.parse_args()
    if args.media:
        print(render_report(args.output))
    else:
        from .demo_inspector import write_inspector
        print(write_inspector(args.output, evidence(args.output)))


if __name__ == "__main__":
    main()
