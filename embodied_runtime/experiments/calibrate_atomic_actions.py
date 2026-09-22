"""Independent atomic probes from a restored simulator AND controller state.

No models or policy are used. Ground truth here is execution calibration only.
NO_ACTION advances no time; SETTLE sends eight zero-delta/open-or-held-command
control steps, isolating natural controller settling from commanded translation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..runtime_core import ATOMIC_ACTIONS, AtomicExecutor


def telemetry(backend):
    world = backend.world
    features = world.features()
    return {
        "sim_time": float(world.data.time),
        "tcp_xyz": backend.tcp_pos().tolist(),
        "orientation": features["eef_rotation_matrix"],
        "finger_gap": features["finger_gap_mm"] / 1000.0,
        "gripper_command": backend._grip_cmd,
        "contacts": features["contacts"],
        "success": features["success"],
    }


def measure(backend, token):
    before = telemetry(backend)
    calls = []
    original = backend.world.execute

    def traced(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(result)
        return result

    backend.world.execute = traced
    result = {}
    commands = []
    try:
        if token == "SETTLE":
            for _ in range(8):
                action = [0.0] * 6 + [backend._grip_cmd]
                backend.world.obs, _, _, _ = backend.world.env.step(action)
                commands.append(action)
        elif token != "NO_ACTION":
            result = AtomicExecutor(backend).execute(token)
    finally:
        backend.world.execute = original
    commands.extend(np.asarray(a).tolist() for call in calls for a in call["commands"])
    after = telemetry(backend)
    row = {f"{key}_{side}": value for side, data in (("before", before), ("after", after)) for key, value in data.items()}
    delta_rotation = np.asarray(after["orientation"]) @ np.asarray(before["orientation"]).T
    row.update({
        "token": token,
        "tcp_delta_xyz": (np.asarray(after["tcp_xyz"]) - before["tcp_xyz"]).tolist(),
        "orientation_delta": delta_rotation.tolist(),
        "rotation_angle_deg": float(np.degrees(np.arccos(np.clip((np.trace(delta_rotation) - 1) / 2, -1, 1)))),
        "finger_gap_delta": after["finger_gap"] - before["finger_gap"],
        "environment_step_count": len(commands),
        "low_level_step_count": int(round((after["sim_time"] - before["sim_time"]) / backend.world.model.opt.timestep)),
        "low_level_commands": commands,
        "execution": result,
    })
    return row


def summarize(output):
    """Calibration-only tables regenerated from the completed raw JSONL."""
    rows = [json.loads(line) for line in (output / "episodes.jsonl").read_text().splitlines()]
    fields = ["task", "seed", "repeat", "initial_gripper", "token", "tcp_delta_xyz",
              "rotation_angle_deg", "finger_gap_delta", "environment_step_count", "low_level_step_count",
              "execution_contract_violation", "execution_contract_reason", "error"]
    summaries = []
    for row in rows:
        data = {**row, **{key: row.get("execution", {}).get(key) for key in ("execution_contract_violation", "execution_contract_reason")}}
        summaries.append({key: data.get(key) for key in fields})
    for name, selected in (("summary.csv", summaries), ("failures.csv", [r for r in summaries if r["error"] or r["execution_contract_violation"]])):
        with (output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="top_drawer")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--initial-gripper", choices=("open", "closed"), default="open")
    parser.add_argument("--libero-root", required=True)
    parser.add_argument("--config-dir", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "kind": "atomic_calibration", "oracle": True,
        "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "command": sys.argv,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], text=True),
        "versions": {name: importlib.metadata.version(name) for name in ("numpy", "mujoco", "robosuite")},
        "source_sha256": {str(path.relative_to(Path(__file__).parents[2])): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(Path(__file__).parents[1].rglob("*.py"))},
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (args.output / "resolved_config.json").write_text(json.dumps(manifest["config"], indent=2) + "\n")
    from jev_libero.world import Snapshot

    tokens = ("NO_ACTION", "SETTLE") + tuple(t for t in ATOMIC_ACTIONS if t != "DONE")
    with (args.output / "episodes.jsonl").open("x") as stream:
        for repeat in range(args.repeats):
            backend = None
            try:
                backend = LiberoWorldBackend.from_task(args.task, seed=args.seed, libero_root=args.libero_root, config_dir=args.config_dir)
                if args.initial_gripper == "closed":
                    for _ in range(3):
                        backend.close_gripper()
                initial_grip = backend._grip_cmd
                snapshot = Snapshot(backend.world)
                for token in tokens:
                    snapshot.restore()
                    backend._grip_cmd = initial_grip
                    initial = backend.world.env.sim.get_state().flatten()
                    row = {"task": args.task, "seed": args.seed, "repeat": repeat,
                           "initial_gripper": args.initial_gripper,
                           "initial_state_sha256": hashlib.sha256(initial.tobytes()).hexdigest(),
                           **measure(backend, token)}
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
                    stream.flush()
                    print(token, "delta_mm", np.round(np.array(row["tcp_delta_xyz"]) * 1000, 4),
                          "rotation_deg", round(row["rotation_angle_deg"], 4),
                          "gap_delta_mm", round(row["finger_gap_delta"] * 1000, 4), flush=True)
            except Exception as exc:
                stream.write(json.dumps({"task": args.task, "seed": args.seed, "repeat": repeat,
                                         "error": repr(exc)}) + "\n")
                stream.flush()
                summarize(args.output)
                raise
            finally:
                if backend is not None:
                    backend.close()
    summarize(args.output)


if __name__ == "__main__":
    main()
