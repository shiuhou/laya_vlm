import json

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, canonical_json
from embodied_runtime.experiments.p1_rgbd_probe import (
    process_recording,
    stable_records,
    verify_replay,
)
from embodied_runtime.perception.recording import FrameRecorder
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.sensor_api import Proprioception


def test_tracker_gates_geometry_and_diagnostic_retains_all_candidates(tmp_path):
    directory = tmp_path / "capture"
    depth = np.ones((48, 64), dtype=np.float32)
    # Empty/flat appearance has no verified semantic identity. Narrow depth
    # spread is valid initially, but uniform local matches are ambiguous later.
    rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    k = np.array([[100.0, 0, 32.0], [0, 100.0, 24.0], [0, 0, 1.0]])
    proprio = Proprioception(
        1.0,
        10,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
        (0.0,),
        None,
        True,
        ("enc/1",),
        reason_codes=("WIDTH_UNCALIBRATED",),
    )
    with FrameRecorder(
        directory, episode_id="ep", clock_domain="host", condition="test"
    ) as recorder:
        for seq in (1, 2):
            recorder.append(
                [
                    dict(
                        rgb=rgb,
                        depth_m=depth,
                        intrinsics_K=k,
                        T_base_camera=np.eye(4),
                        camera_id="front",
                        frame_id=f"raw:{seq}",
                        frame_seq=seq,
                        calibration_version="cal",
                        capture_sim_time_s=1.0,
                        capture_monotonic_ns=seq * 10,
                        frame="robot_base",
                    )
                ],
                proprio,
                emitted_monotonic_ns=seq * 10 + 1,
            )
    config = {
        "rois": {"front": {"plane": [10, 10, 50, 38]}},
        "roi_source": "diagnostic-not-a-label",
    }
    records = process_recording(directory, config, GeometryConfig(), init_index=0)
    assert len(records) == 2
    assert records[0]["source_capture_frame_id"] == "raw:1"
    assert records[0]["frame_id"] == "ep/front/1"
    assert records[0]["tracker"]["track_id"] == "front/plane"
    assert records[0]["tracker"]["semantic_identity_verified"] is False
    assert records[0]["diagnostic_patch"]["geometry_status"] == "VALID"
    assert len(records[0]["diagnostic_patch"]["candidates"]) > 1
    assert all(
        c["usable_status"] == "UNKNOWN"
        for c in records[0]["diagnostic_patch"]["candidates"]
    )
    assert records[1]["tracker"]["status"] == "AMBIGUOUS"
    assert records[1]["patch"]["geometry_status"] == "UNKNOWN"
    assert records[1]["patch"]["candidates"] == []
    assert records[1]["diagnostic_patch"]["candidates"]
    assert canonical_json(stable_records(records)) == canonical_json(
        stable_records(
            process_recording(directory, config, GeometryConfig(), init_index=0)
        )
    )


def test_replay_compares_every_field_except_actual_compute_timings(tmp_path):
    record = {
        "frame_id": "f",
        "candidates": [{"id": "a", "xyz": [1, 2, 3]}, {"id": "b", "xyz": [2, 3, 4]}],
        "geometry_ms": 1.0,
        "tracker_ms": 2.0,
    }
    (tmp_path / "geometry.jsonl").write_text(json.dumps(record) + "\n")
    changed = {**record, "geometry_ms": 999.0}
    assert verify_replay(tmp_path, [changed])["records_compared"] == 1
    changed["candidates"] = list(reversed(record["candidates"]))
    with pytest.raises(ProtocolError, match="REPLAY_DIVERGENCE"):
        verify_replay(tmp_path, [changed])
