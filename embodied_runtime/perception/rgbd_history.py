"""Bounded raw sensor history for delayed semantic seeds.

Historical replay preserves capture clocks. It does not establish present-time
validity until a caller-supplied current clock passes the final freshness check.
No semantic result, mask, synthetic frame, or inferred pose fills history gaps.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

import numpy as np

from ..contracts import content_hash, require
from .surface_association import sensor_view_identity
from .visual_tracker import TrackerConfig, VisualTracker


@dataclass(frozen=True)
class CatchUpResult:
    tracker: VisualTracker
    transitions: tuple
    source_identity_sha256: str
    retained_frame_ids: tuple
    current_eligible: bool
    reason: str
    checked_sim_time_s: float | None
    checked_monotonic_ns: int | None


class RGBDHistory:
    """Single episode/camera, FIFO raw images; all capacity limits are explicit.

    The caller serializes append/catch_up. Returned source identity hashes bind
    exact pixels, calibration, pose, and original capture clocks. Arrays are
    owned immutable byte copies, so mutating capture buffers cannot alter them.
    """

    def __init__(self, episode_id, camera_id, *, max_frames, max_bytes, max_age_s):
        require(isinstance(episode_id, str) and episode_id and isinstance(camera_id, str)
                and camera_id, 'episode and camera required')
        require(type(max_frames) is int and max_frames > 0 and type(max_bytes) is int
                and max_bytes > 0 and isinstance(max_age_s, (int, float))
                and not isinstance(max_age_s, bool) and isfinite(max_age_s)
                and max_age_s > 0, 'finite positive history bounds required')
        self.episode_id, self.camera_id = episode_id, camera_id
        self.max_frames, self.max_bytes, self.max_age_s = max_frames, max_bytes, max_age_s
        self._frames = deque()
        self._bytes = 0
        self._validator = VisualTracker(episode_id)

    @property
    def retained_bytes(self):
        return self._bytes

    def __len__(self):
        return len(self._frames)

    def append(self, view):
        require(view.get('episode_id') == self.episode_id and view.get('camera_id') == self.camera_id,
                'history is bound to one episode/camera', 'SOURCE_MISMATCH')
        # Reuse the unchanged tracker input contract, without initializing it.
        self._validator._frame(view, view['capture_sim_time_s'], view['capture_monotonic_ns'])
        if self._frames:
            previous = self._frames[-1][1]
            require(view['frame_seq'] > previous['frame_seq']
                    and view.get('canonical_frame_id', view['frame_id']) != previous['frame_id']
                    and view['capture_sim_time_s'] >= previous['capture_sim_time_s']
                    and view['capture_monotonic_ns'] >= previous['capture_monotonic_ns'],
                    'history capture order must increase', 'FRAME_OUT_OF_ORDER')
        keys = ('episode_id', 'camera_id', 'frame_id', 'frame_seq', 'calibration_version',
                'capture_sim_time_s', 'capture_monotonic_ns', 'frame')
        owned = {k: view[k] for k in keys}
        if 'canonical_frame_id' in view:
            owned['canonical_frame_id'] = view['canonical_frame_id']
            # Recorded observations expose a canonical ID; use the same ID for
            # tracker lineage as the source identity / semantic request binding.
            owned['frame_id'] = view['canonical_frame_id']
        size = 0
        for key in ('rgb', 'depth_m', 'intrinsics_K', 'T_base_camera'):
            array = np.asarray(view[key])
            owned[key] = np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)
            size += array.nbytes
        require(size <= self.max_bytes, 'single frame exceeds byte capacity', 'HISTORY_CAPACITY')
        identity = content_hash(sensor_view_identity(owned))
        self._frames.append((identity, MappingProxyType(owned), size))
        self._bytes += size
        while (len(self._frames) > self.max_frames or self._bytes > self.max_bytes
               or owned['capture_sim_time_s']-self._frames[0][1]['capture_sim_time_s'] > self.max_age_s
               or (owned['capture_monotonic_ns']-self._frames[0][1]['capture_monotonic_ns'])/1e9 > self.max_age_s):
            self._bytes -= self._frames.popleft()[2]
        return identity

    def catch_up(self, source_identity_sha256, roi_xyxy_px, *, query, clock,
                 tracker_config=TrackerConfig(), track_id='delayed-semantic-target'):
        """Seed exact retained source, replay all intervening captures, fail closed.

        ``clock()`` is invoked AFTER replay and returns (sim_time_s, monotonic_ns).
        It must read the actual current clocks for live use. No source timestamp
        is refreshed. Eligibility is only valid at the returned check time;
        downstream consumers must still enforce their normal freshness gates.
        """
        retained = tuple(self._frames)
        start = next((i for i, row in enumerate(retained) if row[0] == source_identity_sha256), None)
        require(start is not None, 'exact seed source evicted or never retained', 'HISTORY_MISSING')
        frames = [row[1] for row in retained[start:]]
        tracker = VisualTracker(self.episode_id, config=tracker_config, track_id=track_id)
        transitions = []
        for i, frame in enumerate(frames):
            clocks = dict(now_sim_time_s=frame['capture_sim_time_s'],
                          now_monotonic_ns=frame['capture_monotonic_ns'])
            result = (tracker.initialize(frame, roi_xyxy_px, query=query,
                      seed_source='semantic_query', **clocks) if i == 0
                      else tracker.update(frame, **clocks))
            transitions.append(result)
            if result.status != 'TRACKED':
                return CatchUpResult(tracker, tuple(transitions), source_identity_sha256,
                    tuple(f['frame_id'] for f in frames), False, result.reason_codes[0], None, None)
        now_sim, now_ns = clock()
        last = frames[-1]
        require(isinstance(now_sim, (int, float)) and not isinstance(now_sim, bool)
                and isfinite(now_sim) and now_sim >= last['capture_sim_time_s']
                and type(now_ns) is int and now_ns >= last['capture_monotonic_ns'],
                'current clock cannot precede latest capture', 'INVALID_CAPTURE_TIME')
        fresh = (now_sim-last['capture_sim_time_s'] <= tracker_config.max_frame_age_s
                 and (now_ns-last['capture_monotonic_ns'])/1e9 <= tracker_config.max_frame_age_s)
        return CatchUpResult(tracker, tuple(transitions), source_identity_sha256,
            tuple(f['frame_id'] for f in frames), fresh,
            'CURRENT_AT_CHECK' if fresh else 'LATEST_FRAME_STALE', now_sim, now_ns)
