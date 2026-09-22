import time

import numpy as np

from embodied_runtime.adapters.locateanything import LatestFrameWorker
from embodied_runtime.vision import LocateAnythingProvider, camera_to_world


def test_camera_to_world_and_latest_worker():
    assert np.allclose(camera_to_world([1, 2, 3], np.eye(4)), [1, 2, 3])
    provider = LocateAnythingProvider(lambda rgb, q: {"boxes_xyxy": [[2, 2, 8, 8]], "score": 1.0}, {"fx": 10, "fy": 10, "cx": 5, "cy": 5})
    worker = LatestFrameWorker(provider, provider.infer, query="mug", episode_id="ep")
    try:
        frame = {"rgb": np.zeros((10, 10, 3), dtype=np.uint8), "depth_m": np.ones((10, 10)), "capture_seq": 1, "capture_sim_time": 0.0, "camera_to_world": np.eye(4)}
        assert worker.submit(frame)
        deadline = time.time() + 2
        event = None
        while event is None and time.time() < deadline:
            event = worker.poll()
            time.sleep(0.01)
        assert event is not None
        assert event.value["position_world_m"] == event.value["position_camera_m"]
        assert worker.completed == 1
    finally:
        worker.close()
