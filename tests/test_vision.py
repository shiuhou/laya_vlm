import numpy as np

from embodied_runtime.vision import (
    LocateAnythingProvider,
    pixel_to_camera,
    robust_depth,
)


def test_depth_projection_and_provider_event():
    depth = np.ones((20, 20), dtype=float)
    assert robust_depth(depth, (5, 5, 15, 15)) == (1.0, 1.0)
    assert np.allclose(pixel_to_camera(5, 5, 1.0, {"fx": 10, "fy": 10, "cx": 5, "cy": 5}), [0, 0, 1])
    provider = LocateAnythingProvider(
        lambda rgb, q: {"boxes_xyxy": [[5, 5, 15, 15]], "score": .9},
        {"fx": 10, "fy": 10, "cx": 5, "cy": 5},
    )
    event = provider.observe(np.zeros((20, 20, 3), dtype=np.uint8), depth, "red_mug",
                             episode_id="ep", source_seq=1, capture_sim_time=1.0)
    assert event is not None
    assert event.track_id == "red_mug"
    assert event.value["position_camera_m"] == [0.0, 0.0, 1.0]
