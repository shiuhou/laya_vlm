"""Versioned, immutable wire contracts for the sensor-driven runtime.

The legacy runtime deliberately keeps its own API. No simulator or model imports
belong here. All clocks and units are explicit in the wire representation.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
import math
from numbers import Real
from types import MappingProxyType
from typing import Any

PROTOCOL = "embodied.protocol/1"


class ProtocolError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)


def thaw(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: thaw(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw(v) for v in value]
    return value


def freeze(value):
    if is_dataclass(value) and not isinstance(value, type):
        value = thaw(value)
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise ProtocolError("INVALID_SCHEMA", "mapping keys must be strings")
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Real):
        if not math.isfinite(value):
            raise ProtocolError("INVALID_SCHEMA", "nonfinite number")
        return int(value) if isinstance(value, int) else float(value)
    raise ProtocolError("INVALID_SCHEMA", f"unsupported wire type {type(value).__name__}")


def canonical_json(value) -> str:
    return json.dumps(thaw(freeze(value)), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def content_hash(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require(condition, detail, code="INVALID_SCHEMA"):
    if not condition:
        raise ProtocolError(code, detail)


def number(value, name, *, minimum=None):
    require(isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value), f"{name} must be finite")
    require(minimum is None or value >= minimum, f"{name} below minimum")


def integer(value, name, *, minimum=0):
    require(type(value) is int and value >= minimum, f"invalid {name}")


def nonempty(value, name):
    require(isinstance(value, str) and bool(value), f"missing {name}")


def vector(value, n, name):
    require(isinstance(value, (tuple, list)) and len(value) == n, f"{name} shape")
    for v in value:
        number(v, name)


@dataclass(frozen=True)
class Envelope:
    message_type: str
    message_id: str
    producer: str
    producer_seq: int
    episode_id: str
    episode_generation: int
    goal_generation: int
    clock_domain: str
    reference_sim_time_s: float
    emitted_monotonic_ns: int
    source_ids: tuple[str, ...]
    payload: Mapping[str, Any]
    protocol: str = PROTOCOL

    def __post_init__(self):
        require(self.protocol == PROTOCOL, "unsupported protocol")
        for key in ("message_type", "message_id", "producer", "episode_id", "clock_domain"):
            nonempty(getattr(self, key), key)
        for key in ("producer_seq", "episode_generation", "goal_generation", "emitted_monotonic_ns"):
            integer(getattr(self, key), key)
        number(self.reference_sim_time_s, "reference_sim_time_s", minimum=0)
        require(isinstance(self.source_ids, (list, tuple)), "source_ids must be a sequence")
        for source in self.source_ids:
            nonempty(source, "source_id")
        require(isinstance(self.payload, Mapping), "payload must be an object")
        object.__setattr__(self, "source_ids", tuple(self.source_ids))
        object.__setattr__(self, "payload", freeze(self.payload))

    @classmethod
    def from_mapping(cls, data):
        try:
            return cls(**data)
        except (TypeError, KeyError) as exc:
            raise ProtocolError("INVALID_SCHEMA", str(exc)) from exc


@dataclass(frozen=True)
class Rejection:
    rejected_message_id: str
    reason_code: str
    checked_snapshot_id: str | None = None
    retryable: bool = False
    detail: str = ""


@dataclass(frozen=True)
class Receipt:
    message_id: str
    received_monotonic_ns: int
    status: str
    rejection: Rejection | None = None


@dataclass(frozen=True)
class BrainIntent:
    intent_id: str
    intent_generation: int
    based_on_snapshot_id: str
    target_track_id: str
    target_track_generation: int
    feature_id: str
    feature_generation: int
    stage: str
    operation: str
    constraint_template_id: str
    completion_template_id: str
    policy_config_revision: str
    expires_monotonic_ns: int
    max_duration_sim_s: float
    abstain: bool = False

    def __post_init__(self):
        for key in ("intent_id", "based_on_snapshot_id", "target_track_id", "feature_id",
                    "operation", "constraint_template_id", "completion_template_id", "policy_config_revision"):
            nonempty(getattr(self, key), key)
        for key in ("intent_generation", "target_track_generation", "feature_generation", "expires_monotonic_ns"):
            integer(getattr(self, key), key)
        require(self.stage in {"OBSERVE", "APPROACH", "ALIGN", "INTERACT", "RETREAT", "VERIFY"}, "unknown stage")
        number(self.max_duration_sim_s, "max_duration_sim_s", minimum=0)
        require(self.max_duration_sim_s > 0 and type(self.abstain) is bool, "intent duration/abstain")


@dataclass(frozen=True)
class StageEvidence:
    intent_id: str
    stage: str
    source_snapshot_ids: tuple[str, ...]
    predicate_id: str
    result: str
    metrics: Mapping[str, Any]
    thresholds_revision: str

    def __post_init__(self):
        require(self.result in {"SATISFIED", "NOT_SATISFIED", "UNKNOWN"}, "stage result")
        from .policy_observation import assert_sensor_only
        assert_sensor_only(self.metrics)
        object.__setattr__(self, "source_snapshot_ids", tuple(self.source_snapshot_ids))
        object.__setattr__(self, "metrics", freeze(self.metrics))


@dataclass(frozen=True)
class BlobRef:
    uri: str
    sha256: str
    shape: tuple[int, ...]
    dtype: str
    layout: str
    depth_scale: float | None = None

    def __post_init__(self):
        nonempty(self.uri, "uri")
        require(not self.uri.startswith(("ring:", "shm:")), "durable blob URI required")
        require(isinstance(self.sha256, str) and len(self.sha256) == 64
                and all(c in "0123456789abcdef" for c in self.sha256), "sha256")
        require(bool(self.shape), "shape required")
        for size in self.shape:
            integer(size, "shape", minimum=1)
        nonempty(self.dtype, "dtype")
        nonempty(self.layout, "layout")
        if self.depth_scale is not None:
            number(self.depth_scale, "depth_scale", minimum=0)
            require(self.depth_scale > 0, "depth_scale must be positive")
        object.__setattr__(self, "shape", tuple(self.shape))


def validate_frame_bundle(p):
    """Validate same-exposure per-view metadata, including non-square cameras."""
    require(set(p) == {"bundle_id", "capture_sim_time_s", "capture_monotonic_ns", "views", "proprio"},
            "FrameBundle keys")
    nonempty(p["bundle_id"], "bundle_id")
    number(p["capture_sim_time_s"], "capture_sim_time_s", minimum=0)
    integer(p["capture_monotonic_ns"], "capture_monotonic_ns")
    require(bool(p["views"]), "views required")
    cameras = set()
    keys = {"camera_id", "frame_seq", "calibration_version", "rgb_blob", "depth_blob",
            "width_px", "height_px", "depth_units", "pixel_origin", "intrinsics_K", "T_base_camera",
            "capture_sim_time_s", "capture_monotonic_ns"}
    for view in p["views"]:
        require(set(view) == keys, "view keys; each view requires capture times")
        for key in ("camera_id", "calibration_version"):
            nonempty(view[key], key)
        require(view["camera_id"] not in cameras, "duplicate camera")
        cameras.add(view["camera_id"])
        for key in ("frame_seq", "capture_monotonic_ns"):
            integer(view[key], key)
        number(view["capture_sim_time_s"], "view capture", minimum=0)
        require(view["capture_sim_time_s"] <= p["capture_sim_time_s"], "view captured after bundle")
        require(view["capture_monotonic_ns"] <= p["capture_monotonic_ns"], "view captured after bundle")
        for key in ("width_px", "height_px"):
            integer(view[key], key, minimum=1)
        require(view["depth_units"] == "m" and view["pixel_origin"] == "top_left", "image units/origin")
        h, w = view["height_px"], view["width_px"]
        rgb, depth = BlobRef(**view["rgb_blob"]), BlobRef(**view["depth_blob"])
        require(rgb.shape == (h, w, 3) and rgb.dtype == "uint8" and rgb.layout == "HWC", "RGB shape/dtype/layout")
        require(depth.shape == (h, w) and depth.dtype in {"float32", "float64"}
                and depth.layout == "HW" and depth.depth_scale == 1.0, "metric depth metadata")
        k, t = view["intrinsics_K"], view["T_base_camera"]
        require(len(k) == 3 and len(t) == 4, "matrix shapes")
        for row in k:
            vector(row, 3, "K")
        for row in t:
            vector(row, 4, "T_base_camera")
        require(k[0][0] > 0 and k[1][1] > 0 and tuple(k[2]) == (0, 0, 1), "invalid K")
        require(tuple(t[3]) == (0, 0, 0, 1), "invalid homogeneous transform")
        for i in range(3):
            for j in range(3):
                require(abs(sum(t[r][i] * t[r][j] for r in range(3)) - int(i == j)) < 1e-6,
                        "rotation not orthonormal")
        det = (t[0][0]*(t[1][1]*t[2][2]-t[1][2]*t[2][1])
               - t[0][1]*(t[1][0]*t[2][2]-t[1][2]*t[2][0])
               + t[0][2]*(t[1][0]*t[2][1]-t[1][1]*t[2][0]))
        require(abs(det-1) < 1e-6, "rotation must be proper")
    # Import locally: sensor types own their whitelist, not a duplicate here.
    from .sensor_api import Proprioception
    proprio = Proprioception.from_mapping(p["proprio"])
    require(proprio.capture_sim_time_s <= p["capture_sim_time_s"], "proprio captured after bundle")
    require(proprio.capture_monotonic_ns <= p["capture_monotonic_ns"], "proprio captured after bundle")


def load_config(path):
    from pathlib import Path
    config = json.loads(Path(path).read_text())
    expected = {"protocol", "condition", "clock_mode", "control_hz", "proposal_ttl_s",
                "brain_request_ttl_s", "free_geometry_age_s", "contact_geometry_age_s",
                "geometry_lag_s", "image_history_s", "result_capacity", "control_capacity",
                "segment_duration_s", "segment_translation_m", "segment_rotation_rad",
                "contact_translation_m", "episode_sim_s", "episode_wall_s"}
    require(set(config) == expected, "unknown/missing config keys")
    require(config["protocol"] == PROTOCOL and config["condition"] == "synthetic_p0"
            and config["clock_mode"] == "single_machine", "P0 configuration boundary")
    for key in expected - {"protocol", "condition", "clock_mode"}:
        number(config[key], key, minimum=0)
        require(config[key] > 0, f"{key} must be positive")
    for key in ("result_capacity", "control_capacity"):
        integer(config[key], key, minimum=1)
    require(config["segment_duration_s"] <= .1 and config["segment_translation_m"] <= .005
            and config["segment_rotation_rad"] <= math.pi/90
            and config["contact_translation_m"] <= .002, "segment exceeds protocol cap")
    return freeze(config)
