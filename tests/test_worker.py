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


def test_close_waits_for_inflight_model_before_teardown():
    import threading
    started = threading.Event()
    provider = LocateAnythingProvider(lambda *_: {}, {"fx": 10, "fy": 10, "cx": 5, "cy": 5})
    records = []
    def slow(*_):
        started.set()
        time.sleep(2.1)  # Reproduces the old two-second shutdown race.
        return {"boxes": []}
    worker = LatestFrameWorker(provider, slow, query="drawer", episode_id="ep",
                               event_sink=lambda k, d: records.append((k, d)))
    worker.submit({"rgb": np.zeros((10, 10, 3)), "depth_m": np.ones((10, 10)),
                   "capture_seq": 1, "capture_sim_time": 0})
    assert started.wait(2)
    state = worker.close()
    assert state["thread_alive"] is False
    assert state["completed"] == 1
    assert any(kind == "vision_completed" for kind, _ in records)
