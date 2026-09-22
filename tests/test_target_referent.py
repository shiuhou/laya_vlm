import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.target_referent import (
    LEGACY_REFERENT_VERSION, REFERENT_VERSION, audit_referent_run, bbox_mask, evaluate_mask_overlap,
    oracle_rendered_handle, oracle_visible_handle,
    resolve_handle_geom, sensor_bbox_reference, surface_centroid,
)


def test_visible_surface_is_pixel_weighted_world_centroid_not_bbox_median():
    depth = np.array([[1., 3.], [2., 4.]])
    k = np.eye(3)
    transform = np.eye(4)
    transform[:3, 3] = [10., 20., 30.]
    result = surface_centroid(depth, np.ones((2, 2), bool), k, transform)
    assert result["position_definition"] == REFERENT_VERSION
    assert result["position_world_m"] == [13., 22.75, 32.5]
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
    assert result["position_world_m"] == [1., 1., 1.]
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
    result = oracle_rendered_handle(world, frame)
    assert result["privileged"] and result["geom_name"] == "wooden_cabinet_1_g17"
    assert result["mask"].tolist() == [[True, False], [False, False]]
    assert result["position_world_m"][:2] == [0., 0.]
    assert result["valid_pixel_count"] == 1
    assert calls[0]["segmentation"] and calls[0]["depth"]
    with pytest.raises(ValueError, match="physical capture time"):
        oracle_rendered_handle(world, {**frame, "capture_sim_time": 1.})
    sim._render_context_offscreen.vopt.geomgroup[0] = 1
    with pytest.raises(ValueError, match="collision meshes off"):
        oracle_rendered_handle(world, frame)


def test_exact_multiray_oracle_matches_individual_rays_and_ignores_sensor_depth():
    mujoco = pytest.importorskip("mujoco")
    model = mujoco.MjModel.from_xml_string('''<mujoco><asset>
      <mesh name="wooden_cabinet_1_wooden_cabinet_top_handle_vis"
            vertex="-0.5 -0.5 0  0.5 -0.5 0  0 0.5 0  0 0 1"/>
      </asset><worldbody><body name="wooden_cabinet_1_cabinet_top" pos="0 0 3">
      <geom name="wooden_cabinet_1_g17" mesh="wooden_cabinet_1_wooden_cabinet_top_handle_vis"
            type="mesh" group="1" contype="0" conaffinity="0"/>
      </body></worldbody></mujoco>''')
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    groups = np.array([0, 1, 0, 0, 0, 0], dtype=np.uint8)
    sim = SimpleNamespace(get_state=lambda: np.array([data.time]),
                          _render_context_offscreen=SimpleNamespace(vopt=SimpleNamespace(geomgroup=groups)))
    world = SimpleNamespace(model=model, data=data, env=SimpleNamespace(sim=sim),
                            scene=SimpleNamespace(moving=[0], local_vertices=lambda g: np.array([[0, 0, 0], [1, 1, 1]])))
    k = np.array([[10., 0., 2.], [0., 10., 2.], [0., 0., 1.]])
    frame = {"capture_sim_time": 0., "depth_m": np.full((5, 5), np.nan), "intrinsics": k,
             "camera_to_world": np.eye(4), "camera_name": "unused"}
    result = oracle_visible_handle(world, frame)
    assert result["valid_pixel_count"] > 0
    assert result["position_world_m"][2] == pytest.approx(3., abs=1e-6)
    assert result["membership_estimator"] == "exact_first_visual_mesh_ray_hit"
    distances = []
    for row in range(5):
        for col in range(5):
            vec = np.array([(col + .5 - 2) / 10., (row + .5 - 2) / 10., 1.])
            norm = np.linalg.norm(vec)
            geom = np.array([-1], dtype=np.int32)
            distance = mujoco.mj_ray(model, data, np.zeros(3), vec / norm, groups, 1, -1, geom)
            assert result["mask"][row, col] == (geom[0] == 0)
            if geom[0] == 0:
                distances.append(distance / norm)
    assert np.allclose(result["selected_depths_m"], distances)
    # Simulated depth is an independent readout; sensor NaNs do not erase it.
    assert np.isnan(frame["depth_m"]).all()


def test_raster_center_convention_and_explicit_legacy_reproduction():
    # Image-boundary principal point at W/2,H/2 lies halfway between four
    # pixel centers in a 2x2 image. Symmetric points must average to its ray.
    k = np.array([[2., 0., 1.], [0., 2., 1.], [0., 0., 1.]])
    current = surface_centroid(np.ones((2, 2)), np.ones((2, 2), bool), k, np.eye(4))
    old = surface_centroid(np.ones((2, 2)), np.ones((2, 2), bool), k, np.eye(4), pixel_center_offset=0.)
    assert current["position_world_m"] == [0., 0., 1.]
    assert old["position_world_m"] == [-.25, -.25, 1.]
    assert current["position_definition"] == REFERENT_VERSION
    assert old["position_definition"] == LEGACY_REFERENT_VERSION


def test_raw_audit_reproduces_both_readouts_and_rejects_changed_oracle_depths(tmp_path):
    from embodied_runtime.experiments.records import RunRecorder
    from embodied_runtime.runtime_core import _sha256_json

    def fixture(path, corrupt=False):
        depth, k, t = np.ones((2, 2)), np.eye(3), np.eye(4)
        sensor = sensor_bbox_reference(depth, [0, 0, 2, 2], k, t, query="handle")
        mask = np.eye(2, dtype=bool)
        oracle = {**surface_centroid(depth, mask, k, t), "mask": mask,
                  "privileged": True, "oracle_backend_version": "mujoco-multiray-v0.1",
                  "selected_depths_m": [2. if corrupt else 1., 1.]}
        def support(item):
            return {**{key: value for key, value in item.items() if key != "mask"},
                    "mask_shape": list(item["mask"].shape), "mask_flat_indices": np.flatnonzero(item["mask"]).tolist()}
        recorder = RunRecorder(path, {"task": "top_drawer", "init_state_id": 0, "seed": 1}, {"run_id": path.name})
        recorder.capture({"capture_seq": 1, "capture_sim_time": 0., "camera_name": "agentview",
                          "rgb": np.zeros((2, 2, 3), np.uint8), "depth_m": depth, "intrinsics": k, "camera_to_world": t})
        pair = {"physical": {"physical_state_id": "physical"}, "perceptual_state": {"fields": {
            "target.position_m": {"value": [1., 1., 1.]}, "quality.geometry_age_s": {"value": 0.},
            "quality.geometry_valid": {"value": True}}},
            "field_differences": {"target.position_m": {"status": "comparable"}}}
        pair["pair_id"] = _sha256_json(pair)
        recorder.record("paired_state", pair)
        recorder.record("target_referent", {"capture_seq": 1, "environment_step": 0,
                        "physical_state_id": "physical", "sensor": support(sensor), "oracle": support(oracle),
                        "membership_evaluation": evaluate_mask_overlap(sensor["mask"], mask), "not_oracle_corrected": True})
        recorder.record("termination", {"reason": "collection_smoke_complete"})
        recorder.close()
    good, bad = tmp_path / "good", tmp_path / "bad"
    fixture(good)
    report = audit_referent_run(good)
    assert report["sensor_centroid_reproduction_residual_m"]["max"] == 0.
    assert report["oracle_centroid_reproduction_residual_m"]["max"] == 0.
    assert report["rows"][0]["oracle_backend_version"] == "mujoco-multiray-v0.1"
    fixture(bad, corrupt=True)
    with pytest.raises(ValueError, match="oracle centroid cannot be reproduced"):
        audit_referent_run(bad)
    frame = good / "frames/capture-000001.npz"
    frame.write_bytes(frame.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="artifact integrity"):
        audit_referent_run(good)
