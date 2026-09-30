"""P0 publication boundary over the existing capture-time fusion algorithms.

Only ``advance_to`` advances time. Ingestion occurs at that reference time;
publication and reads never execute the filter. Historical image association is
an explicit upstream input, not an image tracker implemented by this module.
All public geometry is robot_base; the adapter's legacy ``position_world_m``
key is a coordinate-agnostic filter input, never an implicit frame transform.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from hashlib import sha256
from math import isfinite

import numpy as np

from .contracts import ProtocolError, canonical_json, freeze, thaw
from .fusion import MultiRateFusion, TemporalConfig
from .runtime_core import ObservationEvent


def _require(condition, code, detail=""):
    if not condition:
        raise ProtocolError(code, detail)


def _identifier(value):
    return isinstance(value, str) and bool(value)


def _generation(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _matrix(value, *, positive=False):
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("INVALID_COVARIANCE") from exc
    _require(array.shape == (3, 3) and np.isfinite(array).all(), "INVALID_COVARIANCE")
    _require(np.allclose(array, array.T, atol=1e-12, rtol=0), "INVALID_COVARIANCE")
    _require(bool(np.all(np.linalg.eigvalsh(array) > 0 if positive else
                         np.linalg.eigvalsh(array) >= -1e-12)), "INVALID_COVARIANCE")
    return array.tolist()


class PerceptionStateStore:
    """Single-writer store; readers receive stable, deeply immutable mappings.

    ``register_*`` admits upstream identities/evidence. The router must first
    validate message/episode identity. A new episode constructs a new store.
    Calibrated semantic probability fusion is deliberately not invoked here:
    unknown model confidence remains null and a binding remains categorical.
    """

    def __init__(self, episode_id, *, fusion=None, history_s=5.0):
        _require(_identifier(episode_id), "INVALID_EPISODE")
        _require(_finite(history_s) and history_s > 0, "INVALID_HISTORY")
        self.episode_id = episode_id
        self.history_s = float(history_s)
        self.fusion = fusion if fusion is not None else MultiRateFusion(
            config=TemporalConfig(geometry_max_age_s=.3))
        _require(self.fusion.episode_id in (None, episode_id), "EPISODE_MISMATCH")
        _require(not self.fusion.geometry and not self.fusion.semantic.tracks,
                 "FUSION_MUST_START_EMPTY", "legacy world-coordinate state cannot be relabeled robot_base")
        self.reference_sim_time_s = self.fusion.reference_time
        self._frames = {}
        self._frame_keys = {}
        self._tracks = {}
        self._associations = {}
        self._semantic_ids = {}
        self._geometry_ids = {}
        self._geometry_records = {}
        self._fused = self.fusion.snapshot(reference_time=self.reference_sim_time_s)
        self._published = None
        self._snapshots = {}
        self._revision = 0

    def advance_to(self, sim_time):
        _require(_finite(sim_time) and sim_time >= self.reference_sim_time_s,
                 "INVALID_REFERENCE_TIME")
        self.reference_sim_time_s = float(sim_time)
        self._fused = self.fusion.snapshot(reference_time=self.reference_sim_time_s)
        cutoff = sim_time - self.history_s
        for frame_id, frame in list(self._frames.items()):
            if frame["capture_sim_time_s"] < cutoff:
                del self._frame_keys[(frame["camera_id"], frame["frame_seq"])]
                del self._frames[frame_id]
        self._associations = {key: item for key, item in self._associations.items()
                              if item["source_frame_id"] in self._frames
                              and item["current_frame_id"] in self._frames}
        self._snapshots = {key: item for key, item in self._snapshots.items()
                           if item["reference_sim_time_s"] >= cutoff}

    def register_frame(self, frame_id, camera_id, frame_seq, calibration_version,
                       capture_sim_time_s):
        _require(all(_identifier(v) for v in (frame_id, camera_id, calibration_version))
                 and _generation(frame_seq), "INVALID_FRAME_IDENTITY")
        _require(_finite(capture_sim_time_s)
                 and 0 <= capture_sim_time_s <= self.reference_sim_time_s,
                 "INVALID_CAPTURE_TIME")
        _require(capture_sim_time_s >= self.reference_sim_time_s - self.history_s,
                 "HISTORY_MISSING")
        frame = freeze(dict(frame_id=frame_id, camera_id=camera_id, frame_seq=frame_seq,
                            calibration_version=calibration_version,
                            capture_sim_time_s=capture_sim_time_s))
        key = (camera_id, frame_seq)
        _require(frame_id not in self._frames or self._frames[frame_id] == frame,
                 "FRAME_ID_CONFLICT")
        _require(key not in self._frame_keys or self._frame_keys[key] == frame_id,
                 "FRAME_ID_CONFLICT")
        self._frames[frame_id] = frame
        self._frame_keys[key] = frame_id

    def register_track(self, track_id, track_generation, feature_id, feature_generation,
                       calibration_ids, status="TRACKED"):
        _require(_identifier(track_id) and _identifier(feature_id)
                 and _generation(track_generation) and _generation(feature_generation),
                 "INVALID_TRACK_IDENTITY")
        _require(status in ("TRACKED", "DEGRADED", "LOST", "AMBIGUOUS"), "INVALID_STATUS")
        _require(isinstance(calibration_ids, Mapping) and bool(calibration_ids)
                 and all(_identifier(k) and _identifier(v) for k, v in calibration_ids.items()),
                 "INVALID_CALIBRATION")
        old = self._tracks.get(track_id)
        identity = (track_generation, feature_id, feature_generation)
        if old:
            old_identity = (old["track_generation"], old["feature_id"], old["feature_generation"])
            _require(track_generation >= old["track_generation"], "TRACK_GENERATION_REGRESSION")
            if track_generation == old["track_generation"]:
                _require(feature_generation >= old["feature_generation"],
                         "FEATURE_GENERATION_REGRESSION")
                _require(feature_id == old["feature_id"] or feature_generation > old["feature_generation"],
                         "FEATURE_GENERATION_REQUIRED")
            unchanged = identity == old_identity and dict(calibration_ids) == old["calibration_versions"]
        else:
            unchanged = False
        self._tracks[track_id] = {
            "track_id": track_id, "track_generation": track_generation,
            "feature_id": feature_id, "feature_generation": feature_generation,
            "calibration_versions": dict(calibration_ids), "status": status,
            "geometry": old["geometry"] if unchanged else None,
            "semantic_binding": old["semantic_binding"] if unchanged else None,
        }
        if old and not unchanged:
            # A new identity must not inherit the old feature's posterior.
            self.fusion.geometry.pop(track_id, None)
            self.fusion.provenance.pop(track_id, None)
            self._fused = self.fusion.snapshot(reference_time=self.reference_sim_time_s)

    def _track(self, track_id, track_generation, feature_id, feature_generation):
        track = self._tracks.get(track_id)
        _require(track is not None, "TRACK_MISSING")
        _require(track["track_generation"] == track_generation
                 and track["feature_id"] == feature_id
                 and track["feature_generation"] == feature_generation, "LINEAGE_MISMATCH")
        return track

    def ingest_geometry(self, observation):
        """Admit R4 GeometryObservation at the already-advanced reference time."""
        observation = thaw(freeze(observation))
        required = ("track_id", "track_generation", "feature_id", "feature_generation", "source_frame_ids",
                    "camera_calibration_ids", "capture_sim_time_s", "frame", "position_m",
                    "position_covariance_m2", "normal_unit", "normal_covariance",
                    "visible_patch_ref", "edge_margin_m", "plane_residual_m", "support_ratio",
                    "status", "reason_codes")
        _require(all(key in observation for key in required), "INVALID_GEOMETRY")
        track = self._tracks.get(observation["track_id"])
        _require(track is not None, "TRACK_MISSING")
        self._track(observation["track_id"], observation["track_generation"],
                    observation["feature_id"], observation["feature_generation"])
        _require(observation["frame"] == "robot_base", "FRAME_MISMATCH")
        _require(observation["status"] in ("TRACKED", "DEGRADED", "LOST", "AMBIGUOUS"), "INVALID_STATUS")
        sources = observation["source_frame_ids"]
        _require(isinstance(sources, list) and bool(sources)
                 and all(_identifier(item) for item in sources) and len(set(sources)) == len(sources),
                 "INVALID_SOURCE_FRAMES")
        _require(all(frame_id in self._frames for frame_id in sources), "HISTORY_MISSING")
        frames = [self._frames[frame_id] for frame_id in sources]
        calibrations = {frame["camera_id"]: frame["calibration_version"] for frame in frames}
        _require(observation["camera_calibration_ids"] == calibrations
                 and all(track["calibration_versions"].get(frame["camera_id"]) == frame["calibration_version"]
                         for frame in frames),
                 "CALIBRATION_MISMATCH")
        captured = observation["capture_sim_time_s"]
        _require(captured == max(frame["capture_sim_time_s"] for frame in frames), "CAPTURE_MISMATCH")
        fingerprint = canonical_json(observation)
        # Depth from the same frames/feature cannot be reweighted by a slow model.
        key = (track["track_id"], track["track_generation"], track["feature_id"],
               track["feature_generation"], tuple(sorted(sources)))
        if key in self._geometry_ids:
            _require(self._geometry_ids[key] == fingerprint, "GEOMETRY_SOURCE_REUSED")
            return False
        _require(isinstance(observation["reason_codes"], list)
                 and all(_identifier(item) for item in observation["reason_codes"]), "INVALID_GEOMETRY")
        for field in ("edge_margin_m", "plane_residual_m", "support_ratio"):
            value = observation[field]
            _require(value is None or (_finite(value) and value >= 0), "INVALID_GEOMETRY")
        support = observation["support_ratio"]
        _require(support is None or support <= 1, "INVALID_GEOMETRY")
        if observation["normal_unit"] is None:
            _require(observation["normal_covariance"] is None
                     and bool(observation["reason_codes"]), "NORMAL_INVALID_REASON_REQUIRED")
        else:
            normal = np.asarray(observation["normal_unit"], dtype=float)
            _require(normal.shape == (3,) and np.isfinite(normal).all()
                     and abs(np.linalg.norm(normal) - 1) <= 1e-6, "INVALID_NORMAL")
            _require(support is not None and support > 0, "NORMAL_SUPPORT_MISSING")
            _matrix(observation["normal_covariance"])
        if observation["status"] in ("TRACKED", "DEGRADED"):
            position = np.asarray(observation["position_m"], dtype=float)
            _require(position.shape == (3,) and np.isfinite(position).all(), "INVALID_POSITION")
            covariance = _matrix(observation["position_covariance_m2"], positive=True)
            _require(captured >= self.reference_sim_time_s - self.fusion.lag_s, "GEOMETRY_TOO_LATE")
            # The source sequence follows capture order (not arrival order).
            # Frame identities are deduplicated above; each frame source is unique.
            source = "sensor_geometry:" + sha256(canonical_json(key).encode()).hexdigest()
            event = ObservationEvent(source, self.episode_id, 0, captured, 0.,
                                     {"position_world_m": position.tolist(),
                                      "position_covariance_m2": covariance,
                                      "position_covariance_source": "sensor_geometry"},
                                     frame_id="robot_base", track_id=track["track_id"], quality=1.)
            admitted = self.fusion.ingest_event(event, reference_time=self.reference_sim_time_s)
            _require(admitted, "GEOMETRY_REJECTED", self.fusion.last_reason)
            self._geometry_records[(source, 0)] = freeze(observation)
            self._fused = self.fusion.snapshot(reference_time=self.reference_sim_time_s)
            filter_ = self.fusion.geometry[track["track_id"]]
            accepted = (event.source, event.source_seq) in filter_.used_ids
            if filter_.used_ids:
                latest = max((self._geometry_records[identity] for identity in filter_.used_ids),
                             key=lambda item: (item["capture_sim_time_s"], canonical_json(item["source_frame_ids"])))
                if track["geometry"] is None or latest["capture_sim_time_s"] >= track["geometry"]["capture_sim_time_s"]:
                    track["geometry"] = latest
                    track["status"] = latest["status"]
        else:
            accepted = True  # A loss report changes validity, never position.
        self._geometry_ids[key] = fingerprint
        if accepted and (track["geometry"] is None
                         or captured >= track["geometry"]["capture_sim_time_s"]):
            track["geometry"] = freeze(observation)
            track["status"] = observation["status"]
        return accepted

    def register_association(self, source_frame_id, current_frame_id, track_id,
                             track_generation, feature_id, feature_generation,
                             evidence_id, status="TRACKED"):
        track = self._track(track_id, track_generation, feature_id, feature_generation)
        _require(source_frame_id in self._frames and current_frame_id in self._frames, "HISTORY_MISSING")
        _require(_identifier(evidence_id) and status in ("TRACKED", "DEGRADED", "LOST", "AMBIGUOUS"),
                 "INVALID_ASSOCIATION")
        source, current = self._frames[source_frame_id], self._frames[current_frame_id]
        _require(source["capture_sim_time_s"] <= current["capture_sim_time_s"], "INVALID_ASSOCIATION")
        _require(all(track["calibration_versions"].get(frame["camera_id"]) == frame["calibration_version"]
                     for frame in (source, current)), "CALIBRATION_MISMATCH")
        item = freeze(dict(source_frame_id=source_frame_id, current_frame_id=current_frame_id,
                           track_id=track_id, track_generation=track_generation,
                           feature_id=feature_id, feature_generation=feature_generation,
                           evidence_id=evidence_id, status=status))
        self._associations[(source_frame_id, track_id, track_generation, feature_id, feature_generation)] = item

    def bind_semantic(self, observation, *, label, track_id, track_generation, feature_id, feature_generation):
        """Bind a late categorical result; never feed its old depth into fusion."""
        observation = thaw(freeze(observation))
        required = ("request_id", "query_generation", "camera_id", "frame_seq", "calibration_version",
                    "capture_sim_time_s", "boxes_xyxy_px", "detection_present", "calibrated_confidence",
                    "raw_output_ref", "model_revision", "latency_ms")
        _require(all(key in observation for key in required), "INVALID_SEMANTIC")
        track = self._track(track_id, track_generation, feature_id, feature_generation)
        _require(_identifier(observation["request_id"]) and _generation(observation["query_generation"])
                 and isinstance(observation["detection_present"], bool), "INVALID_SEMANTIC")
        _require(observation["calibrated_confidence"] is None, "UNCALIBRATED_BINDING_ONLY")
        _require(_identifier(label), "INVALID_SEMANTIC")
        frame_id = self._frame_keys.get((observation["camera_id"], observation["frame_seq"]))
        _require(frame_id in self._frames, "HISTORY_MISSING")
        frame = self._frames[frame_id]
        _require(frame["calibration_version"] == observation["calibration_version"]
                 == track["calibration_versions"].get(observation["camera_id"]), "CALIBRATION_MISMATCH")
        _require(frame["capture_sim_time_s"] == observation["capture_sim_time_s"], "CAPTURE_MISMATCH")
        association = self._associations.get((frame_id, track_id, track_generation, feature_id, feature_generation))
        _require(association is not None, "ASSOCIATION_MISSING")
        _require(association["status"] == "TRACKED" and track["status"] == "TRACKED", "ASSOCIATION_AMBIGUOUS")
        geometry = track["geometry"]
        _require(geometry is not None and association["current_frame_id"] in geometry["source_frame_ids"],
                 "ASSOCIATION_STALE")
        _require(self._fused["validity"].get(track_id, {}).get("geometry_valid", False), "GEOMETRY_STALE")
        fingerprint = canonical_json(dict(observation=observation, label=label, track_id=track_id,
                                          track_generation=track_generation, feature_id=feature_id,
                                          feature_generation=feature_generation))
        request_id = observation["request_id"]
        if request_id in self._semantic_ids:
            _require(self._semantic_ids[request_id] == fingerprint, "SEMANTIC_ID_CONFLICT")
            return False
        previous = track["semantic_binding"]
        if previous:
            _require(observation["query_generation"] >= previous["query_generation"], "QUERY_GENERATION_STALE")
            _require(observation["capture_sim_time_s"] >= previous["capture_sim_time_s"], "SEMANTIC_CAPTURE_STALE")
        self._semantic_ids[request_id] = fingerprint
        track["semantic_binding"] = freeze(dict(observation, label=label, source_frame_id=frame_id,
                                                 association_evidence_id=association["evidence_id"],
                                                 bound_sim_time_s=self.reference_sim_time_s))
        return True

    def publish_snapshot(self, *, proprio=None, observed_occupancy_ref=None, safety_state=None):
        """Publish cached state; this operation never executes fusion."""
        tracks = []
        for track_id, track in sorted(self._tracks.items()):
            geometry = self._fused["geometry"].get(track_id)
            validity = self._fused["validity"].get(track_id, {})
            source = track["geometry"]
            binding = track["semantic_binding"]
            capture = None if geometry is None else geometry.capture_time
            # Hide coordinate-agnostic legacy field names and internal adapter
            # wall-time placeholders; public evidence retains original frames.
            provenance = []
            used = self.fusion.geometry[track_id].used_ids if track_id in self.fusion.geometry else set()
            for item in validity.get("provenance", []):
                identity = (item["source"], item["source_seq"])
                evidence = self._geometry_records[identity]
                provenance.append(dict(source=item["source"], source_seq=item["source_seq"],
                                       source_kind="sensor-derived", frame="robot_base",
                                       episode_id=item["episode_id"],
                                       capture_sim_time_s=item["capture_sim_time"],
                                       source_frame_ids=evidence["source_frame_ids"],
                                       camera_calibration_ids=evidence["camera_calibration_ids"],
                                       position_m=evidence["position_m"],
                                       position_covariance_m2=evidence["position_covariance_m2"],
                                       accepted=identity in used))
            tracks.append(dict(track_id=track_id, track_generation=track["track_generation"],
                               feature_id=track["feature_id"], feature_generation=track["feature_generation"],
                               frame="robot_base", status=track["status"],
                               position_m=None if geometry is None else geometry.position_m.tolist(),
                               position_covariance_m2=None if geometry is None else geometry.covariance[:3, :3].tolist(),
                               normal_unit=None if source is None else source["normal_unit"],
                               normal_covariance=None if source is None else source["normal_covariance"],
                               last_geometry_capture_sim_time_s=capture,
                               geometry_age_s=None if capture is None else self.reference_sim_time_s - capture,
                               geometry_valid=bool(validity.get("geometry_valid", False)
                                                   and track["status"] == "TRACKED"),
                               geometry_invalid_reasons=list(validity.get("geometry_invalid_reasons", ["geometry_missing"]))
                               + ([] if track["status"] == "TRACKED" else [track["status"]]),
                               normal_valid=bool(validity.get("geometry_valid", False)
                                                 and source and source["normal_unit"] is not None
                                                 and track["status"] == "TRACKED"),
                               last_semantic_binding_sim_time_s=None if binding is None else binding["bound_sim_time_s"],
                               semantic_capture_sim_time_s=None if binding is None else binding["capture_sim_time_s"],
                               semantic_age_s=None if binding is None else self.reference_sim_time_s - binding["capture_sim_time_s"],
                               semantic_binding=binding, geometry_observation=source,
                               calibration_versions=track["calibration_versions"],
                               provenance=provenance))
        calibrations = {}
        for track in tracks:
            for camera, version in track["calibration_versions"].items():
                _require(camera not in calibrations or calibrations[camera] == version, "CALIBRATION_MISMATCH")
                calibrations[camera] = version
        payload = dict(episode_id=self.episode_id, reference_sim_time_s=self.reference_sim_time_s,
                       tracks=tracks, proprio=proprio, observed_occupancy_ref=observed_occupancy_ref,
                       calibration_versions=calibrations,
                       safety_state=safety_state if safety_state is not None else {"valid": False, "reason": "UNKNOWN"},
                       temporal_config=asdict(self.fusion.config))
        frozen = freeze(payload)
        if self._published is not None:
            old = {key: value for key, value in self._published.items() if key not in ("snapshot_id", "revision")}
            if frozen == old:
                return self._published
        self._revision += 1
        payload["revision"] = self._revision
        payload["snapshot_id"] = sha256(canonical_json(payload).encode()).hexdigest()
        self._published = freeze(payload)
        self._snapshots[payload["snapshot_id"]] = self._published
        return self._published

    def read_snapshot(self):
        _require(self._published is not None, "SNAPSHOT_UNPUBLISHED")
        return self._published

    def validate_lineage(self, source_snapshot_id, *, target_track_id, target_track_generation,
                         feature_id, feature_generation):
        """Return current track if old proposal identity still has reliable lineage."""
        source = self._snapshots.get(source_snapshot_id)
        _require(source is not None, "HISTORY_MISSING")
        current = self._track(target_track_id, target_track_generation, feature_id, feature_generation)
        original = next((item for item in source["tracks"] if item["track_id"] == target_track_id), None)
        _require(original is not None, "TRACK_MISSING")
        _require(original["track_generation"] == target_track_generation
                 and original["feature_id"] == feature_id
                 and original["feature_generation"] == feature_generation, "LINEAGE_MISMATCH")
        _require(original["calibration_versions"] == current["calibration_versions"], "CALIBRATION_MISMATCH")
        _require(current["status"] == "TRACKED", "ASSOCIATION_AMBIGUOUS")
        _require(self._fused["validity"].get(target_track_id, {}).get("geometry_valid", False), "GEOMETRY_STALE")
        before, after = original["semantic_binding"], current["semantic_binding"]
        if before and after:
            _require((before["label"], before["detection_present"]) ==
                     (after["label"], after["detection_present"]), "SEMANTIC_CHANGED")
        return freeze(current)
