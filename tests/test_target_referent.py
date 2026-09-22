import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.target_referent import (
    REFERENT_VERSION, bbox_mask, evaluate_mask_overlap, oracle_visible_handle,
    resolve_handle_geom, sensor_bbox_reference, surface_centroid,
)


def test_visible_surface_is_pixel_weighted_world_centroid_not_bbox_median():
    depth = np.array([[1., 3.], [2., 4.]])
    k = np.eye(3)
    transform = np.eye(4)
    transform[:3, 3] = [10., 20., 30.]
    result = surface_centroid(depth, np.ones((2, 2), bool), k, transform)
    assert result["position_definition"] == REFERENT_VERSION
    assert result["position_world_m"] == [11.75, 21.5, 32.5]
    assert result["valid_pixel_count"] == 4
    assert "position_covariance" not in result


def test_unknown_for_occluded_empty_or_invalid_depth_support():
    k, t = np.eye(3), np.eye(4)
    missing = surface_centroid(np.ones((2, 2)), np.zeros((2, 2), bool), k, t)
    assert missing["position_world_m"] is None and missing["valid_depth_fraction"] is None
    depth = np.array([[np.nan, 0.], [6., 1.]])
    result = surface_centroid(depth, np.ones((2, 2), bool), k, t, min_support=2)
    assert result["position_world_m"] is None
    assert result["valid_pixel_count"] == 1
    assert result["valid_depth_fraction"] == .25


def test_sensor_bbox_has_no_oracle_access_and_preserves_raw_proxy():
    params = set(inspect.signature(sensor_bbox_reference).parameters)
    assert not params & {"world", "oracle", "oracle_mask", "segmentation", "mask"}
    depth = np.ones((4, 4))
    raw = [9., 8., 7.]
    result = sensor_bbox_reference(depth, [0, 0, 2, 2], np.eye(3), np.eye(4),
                                   query="top drawer handle", raw_position_world_m=raw)
    assert result["raw_bbox_proxy_position_world_m"] == raw
    assert result["position_world_m"] == [.5, .5, 1.]
    assert result["privileged"] is False and result["source"] == "sensor"
    assert "bbox_membership_is_not_segmentation" in result["limitations"]


def test_sensor_contamination_measured_but_never_corrected_by_oracle():
    depth = np.ones((3, 3))
    result = sensor_bbox_reference(depth, [0, 0, 3, 3], np.eye(3), np.eye(4), query="handle")
    sensor_point = list(result["position_world_m"])
    oracle = np.zeros((3, 3), bool)
    oracle[0, 0] = True
    metric = evaluate_mask_overlap(result["mask"], oracle)
    assert metric["iou"] == metric["sensor_pixel_purity"] == pytest.approx(1 / 9)
    assert metric["visible_handle_recall"] == 1
    assert result["position_world_m"] == sensor_point
    assert "mask" not in metric and "position_world_m" not in metric
    missing = evaluate_mask_overlap(result["mask"], np.zeros((3, 3), bool))
    assert not missing["reference_comparable"] and missing["visible_handle_recall"] is None


def test_bounds_and_projection_validation():
    assert bbox_mask((3, 3), [-2, -2, 1, 2]).sum() == 2
    assert not bbox_mask((3, 3), [5, 5, 8, 8]).any()
    with pytest.raises(ValueError, match="positive extent"):
        bbox_mask((3, 3), [2, 1, 1, 2])
    with pytest.raises(ValueError, match="boolean mask"):
        surface_centroid(np.ones((2, 2)), np.ones((2, 2)), np.eye(3), np.eye(4))
    k = np.eye(3)
    k[0, 0] = 0
    with pytest.raises(ValueError, match="intrinsics"):
        surface_centroid(np.ones((2, 2)), np.ones((2, 2), bool), k, np.eye(4))


def test_oracle_visual_binding_render_orientation_and_alignment():
    mujoco = pytest.importorskip("mujoco")
    pytest.importorskip("robosuite")
    model = mujoco.MjModel.from_xml_string('''<mujoco><asset>
      <mesh name="wooden_cabinet_1_wooden_cabinet_top_handle_vis"
            vertex="0 0 0  1 0 0  0 1 0  0 0 1"/>
      </asset><worldbody><body name="wooden_cabinet_1_cabinet_top">
      <geom name="wooden_cabinet_1_g17" mesh="wooden_cabinet_1_wooden_cabinet_top_handle_vis"
            type="mesh" group="1" contype="0" conaffinity="0"/>
      </body></worldbody></mujoco>''')
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    segmentation = np.full((2, 2, 2), -1, dtype=int)
    segmentation[1, 0] = [int(mujoco.mjtObj.mjOBJ_GEOM), 0]  # top-left after vertical flip
    calls = []
    def render(**kwargs):
        calls.append(kwargs)
        return segmentation.copy(), np.full((2, 2), .5)
    sim = SimpleNamespace(model=model, render=render,
                          get_state=lambda: np.array([data.time]),
                          _render_context_offscreen=SimpleNamespace(vopt=SimpleNamespace(geomgroup=[0, 1, 0, 0, 0, 0])))
    world = SimpleNamespace(model=model, data=data, env=SimpleNamespace(sim=sim),
                            scene=SimpleNamespace(moving=[0], local_vertices=lambda g: np.array([[0, 0, 0], [1, 1, 1]])))
    frame = {"capture_sim_time": 0., "depth_m": np.ones((2, 2)), "intrinsics": np.eye(3),
             "camera_to_world": np.eye(4), "camera_name": "agentview"}
    assert resolve_handle_geom(world) == 0
    result = oracle_visible_handle(world, frame)
    assert result["privileged"] and result["geom_name"] == "wooden_cabinet_1_g17"
    assert result["mask"].tolist() == [[True, False], [False, False]]
    assert result["position_world_m"][:2] == [0., 0.]
    assert result["valid_pixel_count"] == 1
    assert calls[0]["segmentation"] and calls[0]["depth"]
    with pytest.raises(ValueError, match="physical capture time"):
        oracle_visible_handle(world, {**frame, "capture_sim_time": 1.})
    sim._render_context_offscreen.vopt.geomgroup[0] = 1
    with pytest.raises(ValueError, match="collision meshes off"):
        oracle_visible_handle(world, frame)
