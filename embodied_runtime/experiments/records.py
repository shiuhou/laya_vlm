"""Append-only scientific records and deterministic recovery of derived tables."""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import subprocess
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np

from ..runtime_core import BeliefSnapshot, Candidate, _sha256_json

SCHEMA_VERSION = "stage2-evidence-v1"


def jsonable(value):
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    return value


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_identity():
    root = Path(__file__).resolve().parents[2]
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    return {"commit": git("rev-parse", "HEAD"), "dirty_status": git("status", "--porcelain"),
            "source_sha256": {str(p.relative_to(root)): file_hash(p)
                              for p in sorted((root / "embodied_runtime").rglob("*.py"))}}


def repository_identity(path):
    root = subprocess.check_output(["git", "-C", str(path), "rev-parse", "--show-toplevel"], text=True).strip()
    def git(*args):
        return subprocess.check_output(["git", "-C", root, *args], text=True).strip()
    return {"root": root, "commit": git("rev-parse", "HEAD"), "dirty_status": git("status", "--porcelain")}


def package_directory(module):
    """LIBERO may be installed as a namespace package with __file__=None."""
    return Path(module.__file__).parent if module.__file__ else Path(next(iter(module.__path__)))


def model_identity(path):
    """Fingerprint local bytes; no network or dependence on an undocumented revision."""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"local checkpoint directory not found: {root}")
    files = {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*"))
             if p.is_file() and p.suffix in {".safetensors", ".bin", ".json", ".py", ".model", ".txt"}}
    if not any(name.endswith((".safetensors", ".bin")) for name in files):
        raise ValueError(f"no local weights in {root}")
    return {"path": str(root), "content_id": _sha256_json(files), "files_sha256": files,
            "upstream_revision": None, "revision_basis": "sha256_of_local_model_and_code_files"}


def versions():
    import sys
    result = {"python": sys.version}
    for package in ("numpy", "mujoco", "robosuite", "torch", "transformers", "laya", "pytest", "ruff"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    return result


def restore_snapshot(data):
    return BeliefSnapshot(**{**data, "candidates": tuple(Candidate(**c) for c in data["candidates"])})


class RunRecorder:
    """Flush and fsync each complete line. Completed evidence precedes control.

    A hard kill can leave an unfinished last line/action. Recovery labels these
    explicitly; it never guesses whether an unacknowledged action completed.
    """

    def __init__(self, output, config, manifest):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.config = jsonable(config)
        self.config_hash = _sha256_json(self.config)
        self.manifest = {**jsonable(manifest), "config_hash": self.config_hash,
                         "schema_version": SCHEMA_VERSION}
        # JSON is valid YAML; avoid adding a YAML dependency to the model-free core.
        (self.output / "resolved_config.yaml").write_text(json.dumps(self.config, indent=2) + "\n")
        (self.output / "manifest.json").write_text(json.dumps(self.manifest, indent=2) + "\n")
        self._stream = (self.output / "episodes.jsonl").open("x", encoding="utf-8")
        self._lock = threading.Lock()
        self._seq = 0
        self._previous = None
        self.record("run_start", {"resolved_config": self.config, "manifest": self.manifest})

    def record(self, kind, data):
        with self._lock:
            row = {"schema_version": SCHEMA_VERSION, "run_id": self.manifest["run_id"],
                   "config_hash": self.config_hash, "seq": self._seq, "kind": kind,
                   "wall_time": time.time(), "previous_record_id": self._previous,
                   "data": jsonable(data)}
            row["record_id"] = _sha256_json(row)
            encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
            self._stream.write(encoded)
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._seq += 1
            self._previous = row["record_id"]
            return row["record_id"]

    def capture(self, frame):
        relative = Path("frames") / f"capture-{frame['capture_seq']:06d}.npz"
        path = self.output / relative
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            np.savez_compressed(stream, **{k: frame[k] for k in ("rgb", "depth_m", "intrinsics", "camera_to_world")})
            stream.flush()
            os.fsync(stream.fileno())
        return self.record("vision_capture", {"capture_seq": frame["capture_seq"],
                           "capture_sim_time": frame["capture_sim_time"], "camera_name": frame["camera_name"],
                           "calibration_id": _sha256_json(jsonable({k: frame[k] for k in ("intrinsics", "camera_to_world")})),
                           "artifact": str(relative), "artifact_sha256": file_hash(path)})

    def close(self):
        with self._lock:
            self._stream.close()

    def manifest_update(self, data):
        self.record("manifest_update", data)
        self.manifest.update(jsonable(data))
        (self.output / "manifest.json").write_text(json.dumps(self.manifest, indent=2) + "\n")


def load_records(path):
    rows, diagnostics, previous = [], [], None
    lines = Path(path).read_bytes().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.endswith(b"\n") and index == len(lines) - 1:
            diagnostics.append({"category": "incomplete_record", "detail": "unterminated final JSONL line"})
            break
        try:
            row = json.loads(line)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"corrupt complete record at line {index + 1}") from exc
        expected = _sha256_json({k: v for k, v in row.items() if k != "record_id"})
        if row.get("seq") != index or row.get("record_id") != expected or row.get("previous_record_id") != previous:
            raise ValueError(f"record integrity failure at line {index + 1}")
        previous = row["record_id"]
        rows.append(row)
    return rows, diagnostics


def summarize(output):
    """Derive both tables only from raw records; also support interrupted runs."""
    output = Path(output)
    rows, failures = load_records(output / "episodes.jsonl")
    snapshots, decisions, intents, actions = {}, {}, {}, {}
    terminated = False
    config = {}
    for row in rows:
        data, kind = row["data"], row["kind"]
        if kind == "run_start":
            config = data["resolved_config"]
        elif kind == "vision_capture":
            if file_hash(output / data["artifact"]) != data["artifact_sha256"]:
                raise ValueError("capture artifact integrity failure")
        elif kind == "snapshot":
            snapshot = restore_snapshot(data["snapshot"])
            if (snapshot.snapshot_id() != data["snapshot_id"] or snapshot.belief_id() != data["belief_id"]
                    or snapshot.candidate_set_id() != data["candidate_set_id"]):
                raise ValueError("snapshot content identity mismatch")
            snapshots[data["snapshot_id"]] = data
        elif kind == "decision":
            decisions[data["step"]] = data
        elif kind == "execution_started":
            intents[data["step"]] = data
        elif kind == "action":
            actions[data["step"]] = data
        elif kind == "failure":
            failures.append({"step": data.get("step"), "category": data["category"], "detail": json.dumps(data, sort_keys=True)})
        elif kind == "termination":
            terminated = True
        elif kind == "vision_worker_closed" and data["thread_alive"]:
            failures.append({"category": "shutdown_incomplete", "detail": "vision thread still alive at cleanup"})
    if not terminated:
        failures.append({"category": "run_incomplete", "detail": "no terminal record"})
    for step in sorted(set(intents) - set(actions)):
        failures.append({"step": step, "category": "execution_outcome_unknown", "detail": "durable intent without completion"})
    summaries = []
    for step, action in sorted(actions.items()):
        intent = intents.get(step)
        if intent is None or action["snapshot_id"] not in snapshots or step not in decisions:
            raise ValueError("action lacks snapshot, decision or execution intent")
        snapshot = snapshots[action["snapshot_id"]]
        if intent["snapshot_id"] != action["snapshot_id"] or decisions[step]["snapshot_id"] != action["snapshot_id"]:
            raise ValueError("decision/action snapshot mismatch")
        execution = action["execution"]
        if execution["token"] != intent["decision"]["token"]:
            raise ValueError("executed token differs from durable intent")
        summaries.append({"task": config.get("task"), "seed": config.get("seed"),
                          "method": config.get("method"), "oracle": config.get("oracle"),
                          "step": step, "belief_id": snapshot["belief_id"],
                          "snapshot_id": action["snapshot_id"], "candidate_set_id": snapshot["candidate_set_id"],
                          "candidate_count": len(snapshot["snapshot"]["candidates"]),
                          "candidate_veto_count": sum(not c["feasible"] for c in snapshot["snapshot"]["candidates"]),
                          "atomic_action": execution["token"], "success": execution["success"],
                          "decision_latency_ms": decisions[step]["decision_latency_ms"],
                          "execution_contract_violation": execution.get("execution_contract_violation")})
    fields = ["task", "seed", "method", "oracle", "step", "belief_id", "snapshot_id", "candidate_set_id",
              "candidate_count", "candidate_veto_count", "atomic_action", "success", "decision_latency_ms", "execution_contract_violation"]
    for name, items, columns in (("summary.csv", summaries, fields),
                                 ("failures.csv", failures, ["step", "category", "detail"])):
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(items)
    return {"completed_actions": len(summaries), "failure_events": len(failures), "terminated": terminated}
