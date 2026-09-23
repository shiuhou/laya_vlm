"""Small communication artifact from recorded demo frames; never re-simulates."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import textwrap

import numpy as np

from .records import file_hash, load_records, summarize


def evidence(directory):
    directory = Path(directory)
    rows, errors = load_records(directory / "episodes.jsonl")
    if errors:
        raise ValueError("incomplete raw record; do not present as a clean demo")
    summarize(directory)  # checks snapshot/action/decision and RGB-D artifact identities
    def by(kind, key="step"):
        result = {}
        for row in rows:
            if row["kind"] == kind:
                value = row["data"]
                if value[key] in result:
                    raise ValueError(f"duplicate {kind}")
                result[value[key]] = value
        return result
    actions, decisions, starts = by("action"), by("decision"), by("execution_started")
    inputs, responses = by("demo_model_input", "snapshot_id"), by("demo_model_response", "snapshot_id")
    trajectories = by("demo_trajectory")
    detections = by("vision_completed", "capture_seq")
    captures = [r["data"] for r in rows if r["kind"] == "vision_capture"]
    result = []
    for step, action in sorted(actions.items()):
        sid = action["snapshot_id"]
        model, decision, execution = inputs[sid], decisions[step]["decision"], action["execution"]
        if set(model["questions"]["action"]["criteria"]) != {c["token"] for c in next(
                r["data"]["snapshot"]["candidates"] for r in rows
                if r["kind"] == "snapshot" and r["data"]["snapshot_id"] == sid) if c["feasible"]}:
            raise ValueError("model candidates differ from live allowed set")
        if model["audit"].get("truncated"):
            raise ValueError("clipped demo model input")
        if not model["singleton_forced_not_model"]:
            expected = model["audit"]["questions"]["action"]
            traces = responses[sid]["forward_traces"]
            if len(traces) != 1 or traces[0]["input_ids"] != [expected["effective_input_ids"]] or traces[0]["option_markers"] != [expected["option_markers"]]:
                raise ValueError("raw model consumption does not match audit")
        t = trajectories[step]
        if file_hash(directory / t["artifact"]) != t["sha256"]:
            raise ValueError("trajectory artifact mismatch")
        if starts[step]["decision"]["token"] != execution["token"]:
            raise ValueError("executed action differs from validated intent")
        result.append({"step": step, "snapshot_id": sid, "proposed": decision["token"],
            "executed": execution["token"], "source": decision["source"],
            "probabilities": decision["probabilities"],
            "allowed": [c["token"] for c in model["canonical"]["candidates"]],
            "input_tokens": model["audit"]["questions"]["action"]["effective_token_count"],
            "fallback_reason": starts[step]["fallback_reason"], "delta_mm": (np.asarray(execution["delta_m"])*1000).tolist(),
            "rotation_deg": execution["rotation_angle_deg"],
            "gripper_before_mm": execution["execution_before"]["finger_gap_m"]*1000,
            "gripper_after_mm": execution["execution_after"]["finger_gap_m"]*1000,
            "contract_violation": execution["execution_contract_violation"],
            "contract_reasons": execution["execution_contract_reason"], "success": execution["success"],
            "sim_start": execution["execution_before"]["sim_time"], "sim_end": execution["execution_after"]["sim_time"],
            "control_steps": execution["environment_step_count"], "trajectory": t,
            "capture": captures[step],
            "observed_box_xyxy": (detections[captures[step]["capture_seq"]]["event"] or {}).get("value", {}).get("box_xyxy"),
            "model_input": model, "raw_response": responses.get(sid)})
    return {"source_sha256": file_hash(directory / "episodes.jsonl"), "steps": result,
        "failures": [r["data"] for r in rows if r["kind"] == "failure"],
        "termination": [r["data"] for r in rows if r["kind"] == "termination"],
        "config": next(r["data"]["resolved_config"] for r in rows if r["kind"] == "run_start"),
        "purpose": "engineering connectivity; not task success or research validation"}


def render_report(directory):
    from PIL import Image, ImageDraw, ImageFont
    directory = Path(directory)
    data = evidence(directory)
    if not data["steps"]:
        raise ValueError("no completed actions; raw failure records retained")
    (directory / "demo-evidence.json").write_text(json.dumps(data, indent=2)+"\n")
    small = ImageFont.truetype("DejaVuSans.ttf", 15)
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
            draw.rectangle((16+x1*1.5, 80+y1*1.5, 16+x2*1.5, 80+y2*1.5), outline="#60ffc2", width=3)
            draw.text((20, 636), "Green: sensor detection, not ground truth", font=small, fill="#60ffc2")
        x = 612
        lines = [f"Action {row['step']+1}/{len(data['steps'])}: {row['executed']}", label,
                 f"Simulation time: {sim_time:.2f} s", "", f"Provider source: {row['source']}",
                 f"Allowed choices: {len(row['allowed'])}",
                 f"P(selected): {row['probabilities'].get(row['proposed'], 0):.4f}",
                 "Model probabilities are not calibrated.", f"Input: {row['input_tokens']} tokens, no clipping", "",
                 "Measured action-end evidence:",
                 "TCP delta mm: " + ", ".join(f"{v:+.2f}" for v in row["delta_mm"]),
                 f"Rotation: {row['rotation_deg']:.2f} deg",
                 f"Finger gap: {row['gripper_before_mm']:.1f} -> {row['gripper_after_mm']:.1f} mm",
                 f"Controls: {row['control_steps']} x 0.05 s",
                 f"Contract flag: {row['contract_violation']}", f"Task success: {row['success']}", "",
                 "No oracle state or preview in Laya input.",
                 "Unknown: contact, holding, drawer progress.",
                 "Current RGB-D + robot proprioception."]
        y = 85
        for line in lines:
            for part in textwrap.wrap(line, 48) or [""]:
                draw.text((x, y), part, font=small, fill="#e4ebf5")
                y += 22
        draw.text((16, 674), "Recorded frames; motion at 0.5x. Decision pauses shortened. Side panel shows action-end telemetry.",
                  font=small, fill="#a8c0d5")
        return canvas

    table = ["| Step | Laya / executed | P(choice) | Allowed | TCP delta mm | Finger gap mm | Contract flag |",
             "|---|---|---:|---:|---|---|---|"]
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
        table.append(f"| {row['step']} | {row['proposed']} / {row['executed']} | "
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
