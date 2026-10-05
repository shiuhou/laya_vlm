"""Durable checksummed FrameBundle storage; replay receives only sensor fields."""
from __future__ import annotations

import hashlib
import io
import json
from itertools import zip_longest
from pathlib import Path

import numpy as np

from ..contracts import BlobRef, Envelope, canonical_json, content_hash, freeze, require, thaw, validate_frame_bundle
from ..sensor_api import Proprioception


def array_bytes(array):
    data = io.BytesIO()
    np.save(data, np.ascontiguousarray(array), allow_pickle=False)
    return data.getvalue()


def _blob(root, array, *, layout, depth_scale=None):
    raw = array_bytes(array)
    digest = hashlib.sha256(raw).hexdigest()
    uri = f"blobs/{digest}.npy"
    path = root/uri
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, "blob hash collision")
    else:
        path.write_bytes(raw)
    return thaw(BlobRef(uri,digest,tuple(array.shape),str(array.dtype),layout,depth_scale))


class FrameRecorder:
    def __init__(self, directory, *, episode_id, episode_generation=1, goal_generation=1,
                 clock_domain, condition):
        self.root = Path(directory)
        self.root.mkdir(parents=True,exist_ok=False)
        self.episode_id,self.episode_generation,self.goal_generation = episode_id,episode_generation,goal_generation
        self.clock_domain,self.condition = clock_domain,condition
        self.seq = 0
        self._previous_identity_hash = None
        self._log = (self.root/"frames.jsonl").open("x",encoding="utf-8")
        self._identities = (self.root/"source-identities.jsonl").open("x",encoding="utf-8")
        self._metadata = dict(condition=condition, clock_domain=clock_domain, provenance="sensor-derived",
                              episode_id=episode_id, episode_generation=episode_generation,
                              goal_generation=goal_generation, format_revision="sensor-frames/2", closed=False)
        (self.root/"recording.json").write_text(json.dumps(self._metadata, indent=2)+"\n")

    def append(self, views, proprio, *, emitted_monotonic_ns):
        """Record arrays first, then append immutable metadata; no dangling slots."""
        require(bool(views), "empty capture")
        if not isinstance(proprio,Proprioception):
            proprio = Proprioception.from_mapping(proprio)
        records, sources = [], []
        for view in views:
            require(view["frame"] == "robot_base", "capture frame")
            require(isinstance(view.get("frame_id"), str) and view["frame_id"], "source frame ID required")
            sources.append(dict(camera_id=view["camera_id"], frame_seq=view["frame_seq"],
                                source_frame_id=view["frame_id"],
                                canonical_frame_id=f"{self.episode_id}/{view['camera_id']}/{view['frame_seq']}"))
            rgb,depth = np.asarray(view["rgb"]),np.asarray(view["depth_m"])
            require(rgb.dtype == np.uint8 and depth.dtype == np.float32, "recording dtype")
            require(rgb.shape == (*depth.shape,3), "RGB/depth exposure dimensions")
            h,w = depth.shape
            records.append(dict(camera_id=view["camera_id"],frame_seq=view["frame_seq"],
                                calibration_version=view["calibration_version"],
                                rgb_blob=_blob(self.root,rgb,layout="HWC"),
                                depth_blob=_blob(self.root,depth,layout="HW",depth_scale=1.),
                                width_px=w,height_px=h,depth_units="m",pixel_origin="top_left",
                                intrinsics_K=np.asarray(view["intrinsics_K"]).tolist(),
                                T_base_camera=np.asarray(view["T_base_camera"]).tolist(),
                                capture_sim_time_s=view["capture_sim_time_s"],
                                capture_monotonic_ns=view["capture_monotonic_ns"]))
        next_seq = self.seq + 1
        captured_sim = max(proprio.capture_sim_time_s, *(v["capture_sim_time_s"] for v in records))
        captured_wall = max(proprio.capture_monotonic_ns, *(v["capture_monotonic_ns"] for v in records))
        require(emitted_monotonic_ns >= captured_wall, "emission precedes capture")
        bundle_id = f"{self.episode_id}/bundle/{next_seq}"
        payload = dict(bundle_id=bundle_id,capture_sim_time_s=captured_sim,capture_monotonic_ns=captured_wall,
                       views=records,proprio=proprio.to_dict())
        validate_frame_bundle(freeze(payload))
        message = Envelope("FrameBundle",bundle_id,"sensor_recorder",next_seq,
                           self.episode_id,self.episode_generation,self.goal_generation,self.clock_domain,
                           captured_sim,emitted_monotonic_ns,(),payload)
        identity = dict(bundle_message_id=bundle_id, envelope_sha256=content_hash(message),
                        previous_sha256=self._previous_identity_hash, sources=sources)
        identity["record_sha256"] = content_hash(identity)
        # A crash between writes is detected as an unmatched pair on replay;
        # source identity is never silently reconstructed after a partial write.
        self._identities.write(canonical_json(identity)+"\n")
        self._identities.flush()
        self._log.write(canonical_json(message)+"\n")
        self._log.flush()
        self.seq, self._previous_identity_hash = next_seq, identity["record_sha256"]
        return message

    def close(self):
        if self._log.closed:
            return
        self._log.close()
        self._identities.close()
        self._metadata.update(closed=True, record_count=self.seq, final_identity_sha256=self._previous_identity_hash)
        (self.root/"recording.json").write_text(json.dumps(self._metadata, indent=2)+"\n")

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()


def read_blob(root, reference):
    ref = BlobRef(**reference)
    root = Path(root).resolve()
    path = (root/ref.uri).resolve()
    require(path.is_relative_to(root), "blob escapes recording root")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref.sha256, "blob checksum mismatch", "BLOB_CORRUPT")
    array = np.load(io.BytesIO(raw),allow_pickle=False)
    require(tuple(array.shape) == ref.shape and str(array.dtype) == ref.dtype, "blob metadata mismatch")
    array.setflags(write=False)
    return array


def replay_frames(directory):
    root = Path(directory)
    metadata = json.loads((root/"recording.json").read_text())
    require(metadata.get("format_revision") == "sensor-frames/2", "source identity sidecar required", "RECORDING_VERSION")
    require(metadata.get("closed") is True, "recording is incomplete", "RECORDING_INCOMPLETE")
    seen, previous_hash = set(), None
    camera_history = {}
    count = 0
    previous_capture = None
    with (root/"frames.jsonl").open(encoding="utf-8") as frames, \
            (root/"source-identities.jsonl").open(encoding="utf-8") as identities:
        for line, identity_line in zip_longest(frames, identities):
            require(line is not None and identity_line is not None, "unmatched frame/identity records", "RECORDING_INCOMPLETE")
            env = Envelope.from_mapping(json.loads(line))
            identity = json.loads(identity_line)
            require(set(identity) == {"bundle_message_id", "envelope_sha256", "previous_sha256", "sources", "record_sha256"},
                    "source identity schema")
            digest = identity["record_sha256"]
            unhashed = {key: value for key, value in identity.items() if key != "record_sha256"}
            require(content_hash(unhashed) == digest and identity["previous_sha256"] == previous_hash,
                    "source identity chain mismatch", "RECORDING_CORRUPT")
            require(identity["bundle_message_id"] == env.message_id and identity["envelope_sha256"] == content_hash(env),
                    "frame metadata differs from source identity record", "RECORDING_CORRUPT")
            previous_hash = digest
            require(env.message_type == "FrameBundle", "recording message type")
            require(env.message_id not in seen, "recording duplicate ID")
            require(env.episode_id == metadata["episode_id"] and env.clock_domain == metadata["clock_domain"]
                    and env.episode_generation == metadata["episode_generation"]
                    and env.goal_generation == metadata["goal_generation"], "recording episode/clock/generation mismatch")
            require(env.producer == "sensor_recorder" and env.producer_seq == count + 1,
                    "recording producer sequence discontinuity")
            require(env.message_id == env.payload["bundle_id"], "bundle identity mismatch")
            validate_frame_bundle(env.payload)
            require(env.emitted_monotonic_ns >= env.payload["capture_monotonic_ns"], "emission precedes capture")
            require(len(identity["sources"]) == len(env.payload["views"]), "source/view count mismatch")
            current_capture = (env.payload["capture_sim_time_s"], env.payload["capture_monotonic_ns"])
            require(previous_capture is None or all(now >= previous for now, previous in zip(current_capture, previous_capture)),
                    "recording capture clock regressed")
            previous_capture = current_capture
            seen.add(env.message_id)
            views = []
            for v, source in zip(env.payload["views"], identity["sources"]):
                require(set(source) == {"camera_id", "frame_seq", "source_frame_id", "canonical_frame_id"}, "source identity keys")
                require(source["camera_id"] == v["camera_id"] and source["frame_seq"] == v["frame_seq"], "source frame mismatch")
                require(source["canonical_frame_id"] == f"{env.episode_id}/{v['camera_id']}/{v['frame_seq']}",
                        "canonical frame mapping mismatch")
                require(isinstance(source["source_frame_id"], str) and source["source_frame_id"], "source frame ID missing")
                camera = v["camera_id"]
                state = (v["frame_seq"], v["capture_sim_time_s"], v["capture_monotonic_ns"])
                old = camera_history.get(camera)
                require(old is None or (state[0] > old[0] and state[1] >= old[1] and state[2] >= old[2]),
                        "camera frame sequence/clock regressed")
                camera_history[camera] = state
                metadata_view = freeze({key:value for key,value in v.items() if key not in {"rgb_blob","depth_blob"}})
                views.append(dict(metadata_view, rgb=read_blob(root,v["rgb_blob"]),depth_m=read_blob(root,v["depth_blob"]),
                                  frame="robot_base",frame_id=source["source_frame_id"],
                                  canonical_frame_id=source["canonical_frame_id"], episode_id=env.episode_id,
                                  episode_generation=env.episode_generation, goal_generation=env.goal_generation,
                                  clock_domain=env.clock_domain))
            count += 1
            yield env,tuple(views)
    require(count == metadata.get("record_count") and previous_hash == metadata.get("final_identity_sha256"),
            "recording tail differs from closed metadata", "RECORDING_INCOMPLETE")


def project_base_points(points_base_m,K,T_base_camera):
    """Sensor calibration only; useful for rendering overlays and reprojection."""
    points = np.asarray(points_base_m,dtype=float)
    require(points.ndim == 2 and points.shape[1] == 3 and np.isfinite(points).all(), "point shape")
    t = np.asarray(T_base_camera,dtype=float)
    k = np.asarray(K,dtype=float)
    camera = (points-t[:3,3])@t[:3,:3]
    require(np.all(camera[:,2] > 0), "points behind camera")
    projected = camera@k.T
    return projected[:,:2]/projected[:,2,None]
