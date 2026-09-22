"""Paired *visible-surface* target referent, not a rigid grasp point.

The estimand is the mean world position of valid camera pixel centers whose
first visible surface belongs to the top-drawer handle visual mesh. It is
pixel-weighted, view/occlusion dependent, and not the handle volume center.

The sensor estimator approximates membership with a query bounding box. It may
include background, other objects, or only part of the handle; those errors are
NOT corrected using the oracle. Oracle segmentation is evaluator-only.
"""
from __future__ import annotations

import numpy as np

REFERENT_VERSION = "top_drawer_handle_visible_pixel_surface_centroid_v0.1"
HANDLE_MESH_SUFFIX = "wooden_cabinet_top_handle_vis"


def surface_centroid(depth, mask, intrinsics, camera_to_world, *, min_support=1):
    """Backproject selected valid depth pixels; no simulator input or access."""
    depth, mask = np.asarray(depth, dtype=float), np.asarray(mask)
    k, transform = np.asarray(intrinsics, dtype=float), np.asarray(camera_to_world, dtype=float)
    if depth.ndim != 2 or mask.shape != depth.shape or mask.dtype != np.bool_:
        raise ValueError("depth and boolean mask must have matching HxW shape")
    if (k.shape != (3, 3) or transform.shape != (4, 4) or not np.isfinite(k).all()
            or not np.isfinite(transform).all() or k[0, 0] <= 0 or k[1, 1] <= 0
            or not np.allclose(k[2], [0, 0, 1]) or not np.allclose(k[0, 1], 0)
            or not np.allclose(k[1, 0], 0) or not np.allclose(transform[3], [0, 0, 0, 1])):
        raise ValueError("finite pinhole intrinsics and homogeneous transform required")
    if not isinstance(min_support, int) or min_support < 1:
        raise ValueError("min_support must be a positive integer")
    valid = mask & np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
    rows, cols = np.nonzero(valid)
    count, selected = len(rows), int(np.count_nonzero(mask))
    result = {"position_definition": REFERENT_VERSION, "position_world_m": None,
              "selected_pixel_count": selected, "valid_pixel_count": count,
              "valid_depth_fraction": count / selected if selected else None,
              "depth_valid_range_m": [.01, 5.], "min_support": min_support,
              "status": "insufficient_visible_depth", "pixel_weighting": "uniform_image_pixel_centers",
              "sample_spread_trace_m2": None, "covariance_calibrated": False}
    if count < min_support:
        return result
    z = depth[rows, cols]
    camera = np.column_stack(((cols - k[0, 2]) * z / k[0, 0],
                              (rows - k[1, 2]) * z / k[1, 1], z))
    points = camera @ transform[:3, :3].T + transform[:3, 3]
    result.update(position_world_m=points.mean(axis=0).tolist(), status="estimated",
                  sample_spread_trace_m2=float(np.var(points, axis=0).sum()))
    # Spatial spread of selected surfaces is NOT measurement covariance.
    return result


def bbox_mask(shape, box_xyxy):
    """Half-open integer support, clipped to the image; invalid boxes fail."""
    box = np.asarray(box_xyxy, dtype=float)
    if len(shape) != 2 or box.shape != (4,) or not np.isfinite(box).all():
        raise ValueError("HxW and four finite box coordinates required")
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("box must have positive extent")
    x1, y1 = np.floor(box[:2]).astype(int)
    x2, y2 = np.ceil(box[2:]).astype(int)
    h, w = shape
    mask = np.zeros(shape, dtype=bool)
    mask[np.clip(y1, 0, h):np.clip(y2, 0, h), np.clip(x1, 0, w):np.clip(x2, 0, w)] = True
    return mask


def sensor_bbox_reference(depth, box_xyxy, intrinsics, camera_to_world, *, query,
                          raw_position_world_m=None, min_support=1):
    """Sensor-only noisy estimator; receives neither oracle mask nor world.

    Query must identify the top handle. That instruction is not a guarantee of
    correct instance localization; evaluator overlap measures this separately.
    Returned ``mask`` is the sensor's box support, never privileged segmentation.
    """
    mask = bbox_mask(np.asarray(depth).shape, box_xyxy)
    estimate = surface_centroid(depth, mask, intrinsics, camera_to_world, min_support=min_support)
    return {**estimate, "source": "sensor", "privileged": False, "query": query,
            "membership_estimator": "query_bbox_all_valid_pixels", "box_xyxy": list(box_xyxy),
            "raw_bbox_proxy_position_world_m": raw_position_world_m, "mask": mask,
            "limitations": ["bbox_membership_is_not_segmentation", "background_or_occluder_contamination",
                            "partial_handle_support", "view_and_occlusion_dependent_not_rigid_grasp_point",
                            "spatial_spread_is_not_estimator_uncertainty"]}


def resolve_handle_geom(world):
    """Privileged binding via visual mesh and target body, not collision AABB."""
    import mujoco
    model = world.model
    candidates = []
    for geom in range(model.ngeom):
        if model.geom_type[geom] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        mesh = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, int(model.geom_dataid[geom])) or ""
        body = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(model.geom_bodyid[geom])) or ""
        if mesh.endswith(HANDLE_MESH_SUFFIX) and body == "wooden_cabinet_1_cabinet_top":
            candidates.append(geom)
    if len(candidates) != 1:
        raise ValueError(f"expected one top-drawer handle visual geom; found {candidates}")
    geom = candidates[0]
    if model.geom_group[geom] != 1 or model.geom_contype[geom] or model.geom_conaffinity[geom]:
        raise ValueError("handle binding must be visual-only mesh, not collision approximation")
    return geom


def oracle_visible_handle(world, frame, *, min_support=1):
    """Evaluator-only independent render, aligned with an existing RGB-D frame.

    Uses privileged geom identity plus ideal rendered depth, not a sensor bbox.
    This is a segmentation/membership oracle in the same synthetic depth sensor
    domain; it does NOT independently validate metric depth calibration.
    """
    import mujoco
    from robosuite.utils.camera_utils import get_real_depth_map
    if not np.isclose(float(world.data.time), frame["capture_sim_time"], atol=1e-10, rtol=0):
        raise ValueError("oracle reference must use the frame's physical capture time")
    geom = resolve_handle_geom(world)
    sim = world.env.sim
    h, w = np.asarray(frame["depth_m"]).shape
    context = sim._render_context_offscreen
    if context.vopt.geomgroup[0] or not context.vopt.geomgroup[1]:
        raise ValueError("oracle referent requires visual meshes on and collision meshes off")
    state_before = sim.get_state().flatten().copy()
    segmentation, raw_depth = sim.render(width=w, height=h, camera_name=frame["camera_name"],
                                         depth=True, segmentation=True)
    segmentation = np.asarray(segmentation)[::-1].copy()
    depth = np.asarray(get_real_depth_map(sim, np.asarray(raw_depth)[::-1]), dtype=float)
    mask = (segmentation[..., 0] == int(mujoco.mjtObj.mjOBJ_GEOM)) & (segmentation[..., 1] == geom)
    if not np.array_equal(sim.get_state().flatten(), state_before):
        raise RuntimeError("simulator state changed during oracle reference render")
    estimate = surface_centroid(depth, mask, frame["intrinsics"], frame["camera_to_world"], min_support=min_support)
    points = np.concatenate([world.scene.local_vertices(g) @ world.data.geom_xmat[g].reshape(3, 3).T
                             + world.data.geom_xpos[g] for g in world.scene.moving])
    return {**estimate, "source": "oracle_sim", "privileged": True, "mask": mask,
            "capture_sim_time": frame["capture_sim_time"], "geom_id": geom,
            "geom_name": mujoco.mj_id2name(world.model, mujoco.mjtObj.mjOBJ_GEOM, geom),
            "mesh_suffix": HANDLE_MESH_SUFFIX, "membership_estimator": "ideal_visible_visual_geom_segmentation",
            "raw_moving_aabb_center_world_m": ((points.min(0) + points.max(0)) / 2).tolist(),
            "raw_moving_aabb_definition": "moving_collision_geometry_world_aabb_center",
            "depth_basis": "independently_rendered_ideal_depth_same_sensor_domain",
            "limitations": ["view_and_occlusion_dependent_not_rigid_grasp_point",
                            "does_not_independently_validate_depth_or_camera_calibration"]}


def evaluate_mask_overlap(sensor_mask, oracle_mask):
    """Evaluator-only; never return a corrected sensor mask or position."""
    sensor, oracle = np.asarray(sensor_mask), np.asarray(oracle_mask)
    if sensor.dtype != np.bool_ or oracle.dtype != np.bool_ or sensor.shape != oracle.shape or sensor.ndim != 2:
        raise ValueError("same-sized boolean masks required")
    intersection = int(np.count_nonzero(sensor & oracle))
    union = int(np.count_nonzero(sensor | oracle))
    s, o = int(np.count_nonzero(sensor)), int(np.count_nonzero(oracle))
    return {"source": "oracle_sim_evaluator", "privileged": True,
            "sensor_support_pixels": s, "oracle_visible_pixels": o, "intersection_pixels": intersection,
            "iou": intersection / union if union else None,
            "sensor_pixel_purity": intersection / s if s else None,
            "visible_handle_recall": intersection / o if o else None,
            "reference_comparable": o > 0,
            "oracle_visible": o > 0}
