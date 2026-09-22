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

LEGACY_REFERENT_VERSION = "top_drawer_handle_visible_pixel_surface_centroid_v0.1"
REFERENT_VERSION = "top_drawer_handle_visible_pixel_surface_centroid_v0.2"
HANDLE_MESH_SUFFIX = "wooden_cabinet_top_handle_vis"


def surface_centroid(depth, mask, intrinsics, camera_to_world, *, min_support=1, pixel_center_offset=.5):
    """Backproject selected valid depth pixels; no simulator input or access.

    K uses a principal point measured from image boundaries (W/2,H/2), so
    raster pixel [row,col] is at (col+.5,row+.5). Offset0 is legacy-v0.1 audit
    only, retained so old artifacts are not silently reinterpreted.
    """
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
    if pixel_center_offset not in (0., .5):
        raise ValueError("pixel center offset must be declared legacy0 or raster0.5")
    valid = mask & np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
    rows, cols = np.nonzero(valid)
    count, selected = len(rows), int(np.count_nonzero(mask))
    result = {"position_definition": REFERENT_VERSION if pixel_center_offset == .5 else LEGACY_REFERENT_VERSION,
              "pixel_center_offset": pixel_center_offset, "position_world_m": None,
              "selected_pixel_count": selected, "valid_pixel_count": count,
              "valid_depth_fraction": count / selected if selected else None,
              "depth_valid_range_m": [.01, 5.], "min_support": min_support,
              "status": "insufficient_visible_depth", "pixel_weighting": "uniform_image_pixel_centers",
              "sample_spread_trace_m2": None, "covariance_calibrated": False}
    if count < min_support:
        return result
    z = depth[rows, cols]
    camera = np.column_stack(((cols + pixel_center_offset - k[0, 2]) * z / k[0, 0],
                              (rows + pixel_center_offset - k[1, 2]) * z / k[1, 1], z))
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


def oracle_rendered_handle(world, frame, *, min_support=1):
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
    estimate = surface_centroid(depth, mask, frame["intrinsics"], frame["camera_to_world"],
                               min_support=min_support, pixel_center_offset=0.)
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


def oracle_visible_handle(world, frame, *, min_support=1):
    """Privileged first-surface mesh raycast at every calibrated pixel center.

    Unlike an ID-color render, geometric ray hits cannot invent object IDs from
    antialias blending or reflections. Calibration is still shared with the
    sensor pipeline; this is not an independent camera-calibration validation.
    Pixel coordinates use the same raster centers as ``surface_centroid``.
    """
    import mujoco
    if not np.isclose(float(world.data.time), frame["capture_sim_time"], atol=1e-10, rtol=0):
        raise ValueError("oracle reference must use the frame's physical capture time")
    geom = resolve_handle_geom(world)
    sim = world.env.sim
    h, w = np.asarray(frame["depth_m"]).shape
    # Run shared calibration validation without using any sensor depths/mask.
    surface_centroid(np.ones((1, 1)), np.ones((1, 1), bool), frame["intrinsics"], frame["camera_to_world"])
    groups = np.asarray(sim._render_context_offscreen.vopt.geomgroup, dtype=np.uint8).copy()
    if groups[0] or not groups[1]:
        raise ValueError("oracle referent requires visual meshes on and collision meshes off")
    k, transform = np.asarray(frame["intrinsics"]), np.asarray(frame["camera_to_world"])
    rows, cols = np.indices((h, w))
    camera_rays = np.column_stack(((cols.ravel() + .5 - k[0, 2]) / k[0, 0],
                                  (rows.ravel() + .5 - k[1, 2]) / k[1, 1], np.ones(h * w)))
    norms = np.linalg.norm(camera_rays, axis=1)
    world_rays = np.ascontiguousarray((camera_rays / norms[:, None]) @ transform[:3, :3].T, dtype=np.float64)
    origin = np.ascontiguousarray(transform[:3, 3], dtype=np.float64)
    hit_ids = np.full(h * w, -1, dtype=np.int32)
    distances = np.full(h * w, -1., dtype=np.float64)
    state_before = sim.get_state().flatten().copy()
    mujoco.mj_multiRay(world.model, world.data, origin, world_rays.ravel(), groups,
                      1, -1, hit_ids, distances, None, h * w, 5.)
    if not np.array_equal(sim.get_state().flatten(), state_before):
        raise RuntimeError("simulator state changed during oracle reference raycast")
    depth = (distances / norms).reshape(h, w)
    mask = (hit_ids.reshape(h, w) == geom) & (distances.reshape(h, w) >= 0.)
    estimate = surface_centroid(depth, mask, k, transform, min_support=min_support)
    points = np.concatenate([world.scene.local_vertices(g) @ world.data.geom_xmat[g].reshape(3, 3).T
                             + world.data.geom_xpos[g] for g in world.scene.moving])
    return {**estimate, "source": "oracle_sim", "privileged": True, "mask": mask,
            "capture_sim_time": frame["capture_sim_time"], "geom_id": geom,
            "geom_name": mujoco.mj_id2name(world.model, mujoco.mjtObj.mjOBJ_GEOM, geom),
            "mesh_suffix": HANDLE_MESH_SUFFIX, "membership_estimator": "exact_first_visual_mesh_ray_hit",
            "oracle_backend_version": "mujoco-multiray-v0.1", "ray_cutoff_m": 5.,
            "ray_pixel_convention": "u_plus_0.5_v_plus_0.5_with_boundary_principal_point",
            "ray_geomgroups": groups.tolist(), "selected_depths_m": depth[mask].tolist(),
            "raw_moving_aabb_center_world_m": ((points.min(0) + points.max(0)) / 2).tolist(),
            "raw_moving_aabb_definition": "moving_collision_geometry_world_aabb_center",
            "depth_basis": "exact_first_surface_ray_distance_projected_to_optical_depth",
            "limitations": ["view_and_occlusion_dependent_not_rigid_grasp_point",
                            "shared_camera_calibration_not_independently_verified",
                            "raster_antialias_coverage_differs_from_single_pixel_center_rays",
                            "raycutoff_5m_includes_current_benchmark_target_not_arbitrary_scenes"]}


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


def _restore_support(record, shape):
    if record["mask_shape"] != list(shape):
        raise ValueError("referent mask shape differs from frame")
    indices = np.asarray(record["mask_flat_indices"])
    if indices.ndim != 1 or (len(indices) and (indices.dtype.kind not in "iu"
            or indices.min() < 0 or indices.max() >= np.prod(shape)
            or len(set(indices.tolist())) != len(indices))):
        raise ValueError("invalid referent mask pixel indices")
    mask = np.zeros(shape, dtype=bool)
    if len(indices):
        mask.flat[indices] = True
    return mask


def _components(mask):
    """8-connected support sizes, diagnostic only; never changes the mask."""
    remaining = set(zip(*np.nonzero(mask)))
    sizes = []
    while remaining:
        pending = [remaining.pop()]
        count = 0
        while pending:
            row, col = pending.pop()
            count += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    point = row + dy, col + dx
                    if point in remaining:
                        remaining.remove(point)
                        pending.append(point)
        sizes.append(count)
    return sorted(sizes, reverse=True)


def _position_distance(a, b):
    return None if a is None or b is None else float(np.linalg.norm(np.asarray(a) - b))


def audit_referent_run(directory):
    """Recompute diagnostic tables from immutable raw records and frame bytes.

    Sensor centroids must reproduce exactly from recorded RGB-D and box support.
    Oracle-mask readout from *sensor* depth is deliberately a separate evaluator
    residual: the independently rendered segmentation/depth pass can differ at
    edges, and may include ID-render artifacts. No pixel is removed or corrected.
    """
    from pathlib import Path
    from ..runtime_core import _sha256_json
    from .records import file_hash, load_records
    directory = Path(directory)
    rows, diagnostics = load_records(directory / "episodes.jsonl")
    config = next(r["data"]["resolved_config"] for r in rows if r["kind"] == "run_start")
    captures, pairs, metrics = {}, {}, []
    for row in rows:
        data = row["data"]
        if row["kind"] == "vision_capture":
            artifact = (directory / data["artifact"]).resolve()
            if directory.resolve() not in artifact.parents or file_hash(artifact) != data["artifact_sha256"]:
                raise ValueError("capture artifact integrity failure")
            captures[data["capture_seq"]] = artifact
        elif row["kind"] == "paired_state":
            if data["pair_id"] != _sha256_json({k: v for k, v in data.items() if k != "pair_id"}):
                raise ValueError("paired-state integrity failure")
            pairs[data["physical"]["physical_state_id"]] = data
    for row in rows:
        if row["kind"] != "target_referent":
            continue
        data = row["data"]
        with np.load(captures[data["capture_seq"]]) as frame:
            depth, k, t = frame["depth_m"], frame["intrinsics"], frame["camera_to_world"]
            oracle = data["oracle"]
            oracle_mask = _restore_support(oracle, depth.shape)
            if oracle["position_definition"] not in {REFERENT_VERSION, LEGACY_REFERENT_VERSION} or not oracle["privileged"]:
                raise ValueError("oracle referent provenance mismatch")
            offset = .5 if oracle["position_definition"] == REFERENT_VERSION else 0.
            backend = oracle.get("oracle_backend_version", "legacy_ID_color_render_v0.1")
            oracle_in_sensor_depth = surface_centroid(depth, oracle_mask, k, t,
                                                       min_support=oracle["min_support"], pixel_center_offset=offset)
            if oracle["selected_pixel_count"] != int(oracle_mask.sum()):
                raise ValueError("oracle support count mismatch")
            oracle_reproduction = None
            if backend == "mujoco-multiray-v0.1":
                selected_depths = np.asarray(oracle["selected_depths_m"], dtype=float)
                if (selected_depths.shape != (int(oracle_mask.sum()),) or not np.isfinite(selected_depths).all()
                        or np.any(selected_depths <= 0)):
                    raise ValueError("invalid oracle selected-depth readout")
                exact_depth = np.full(depth.shape, np.nan)
                exact_depth[oracle_mask] = selected_depths
                exact = surface_centroid(exact_depth, oracle_mask, k, t, min_support=oracle["min_support"],
                                         pixel_center_offset=offset)
                if ((exact["position_world_m"] is None) != (oracle["position_world_m"] is None)
                        or exact["valid_pixel_count"] != oracle["valid_pixel_count"]):
                    raise ValueError("oracle readout missingness/count cannot be reproduced")
                oracle_reproduction = _position_distance(exact["position_world_m"], oracle["position_world_m"])
                if oracle_reproduction is not None and oracle_reproduction > 1e-12:
                    raise ValueError("oracle centroid cannot be reproduced from selected ray depths")
            component_sizes = _components(oracle_mask)
            sensor, overlap, sensor_residual = data["sensor"], None, None
            if sensor is not None:
                sensor_mask = _restore_support(sensor, depth.shape)
                if sensor["privileged"] or sensor["position_definition"] != oracle["position_definition"]:
                    raise ValueError("sensor referent provenance mismatch")
                if not np.array_equal(sensor_mask, bbox_mask(depth.shape, sensor["box_xyxy"])):
                    raise ValueError("sensor support differs from its recorded box")
                recomputed = surface_centroid(depth, sensor_mask, k, t, min_support=sensor["min_support"],
                                              pixel_center_offset=offset)
                if (recomputed["position_world_m"] is None) != (sensor["position_world_m"] is None):
                    raise ValueError("sensor missingness cannot be reproduced")
                sensor_residual = _position_distance(recomputed["position_world_m"], sensor["position_world_m"])
                if sensor_residual is not None and sensor_residual > 1e-12:
                    raise ValueError("sensor centroid cannot be reproduced from raw support")
                for field in ("selected_pixel_count", "valid_pixel_count", "status"):
                    if recomputed[field] != sensor[field]:
                        raise ValueError(f"sensor {field} cannot be reproduced")
                overlap = evaluate_mask_overlap(sensor_mask, oracle_mask)
                if overlap != data["membership_evaluation"]:
                    raise ValueError("membership evaluation cannot be reproduced")
            elif data["membership_evaluation"] is not None:
                raise ValueError("membership evaluation exists without sensor support")
            pair = pairs.get(data["physical_state_id"])
            fields = pair["perceptual_state"]["fields"] if pair else {}
            oracle_point = oracle["position_world_m"]
            sensor_point = sensor["position_world_m"] if sensor else None
            fused_point = fields.get("target.position_m", {}).get("value")
            comparable = bool(oracle_point is not None and pair and
                              pair["field_differences"]["target.position_m"]["status"] == "comparable")
            metrics.append({"task": config["task"], "init_state_id": config["init_state_id"], "seed": config["seed"],
                            "capture_seq": data["capture_seq"], "environment_step": data["environment_step"],
                            "physical_state_id": data["physical_state_id"], "pair_id": pair["pair_id"] if pair else None,
                            "position_definition": oracle["position_definition"], "reference_comparable": comparable,
                            "oracle_backend_version": backend, "pixel_center_offset": offset,
                            "oracle_visible_pixels": int(oracle_mask.sum()),
                            "oracle_mask_component_sizes": component_sizes,
                            "oracle_pixels_outside_largest_component": int(oracle_mask.sum()) - (component_sizes[0] if component_sizes else 0),
                            "sensor_pixel_purity": overlap["sensor_pixel_purity"] if overlap else None,
                            "iou": overlap["iou"] if overlap else None,
                            "visible_handle_recall": overlap["visible_handle_recall"] if overlap else None,
                            "sensor_centroid_reproduction_residual_m": sensor_residual,
                            "oracle_centroid_reproduction_residual_m": oracle_reproduction,
                            "oracle_vs_recorded_depth_readout_residual_m": _position_distance(
                                oracle_point, oracle_in_sensor_depth["position_world_m"]),
                            "raw_sensor_centroid_error_m": _position_distance(sensor_point, oracle_point),
                            "fused_state_position_error_m": _position_distance(fused_point, oracle_point) if comparable else None,
                            "geometry_age_s": fields.get("quality.geometry_age_s", {}).get("value"),
                            "geometry_valid": fields.get("quality.geometry_valid", {}).get("value"),
                            "no_oracle_correction": data["not_oracle_corrected"]})
    summary = {"version": "target-referent-raw-audit-v0.1", "source": str(directory),
               "source_jsonl_sha256": file_hash(directory / "episodes.jsonl"),
               "complete_collection": any(r["kind"] == "termination" and r["data"].get("reason") == "collection_smoke_complete" for r in rows),
               "raw_log_diagnostics": diagnostics, "rows": metrics,
               "limitations": ["oracle_geometry_uses_shared_camera_calibration_not_an_independent_calibration_check",
                               "legacy_ID_render_can_have_blended_or_reflected_ghost_pixels",
                               "ray_backend_excludes_ID_artifacts_but_single_ray_surface_differs_from_antialiased_RGBD_edges",
                               "disconnected_oracle_mask_support_is_reported_not_removed",
                               "bbox_surface_membership_is_approximate_not_an_oracle_corrected_mask",
                               "fresh_capture_does_not_mean_fused_state_equals_measurement"]}
    for field in ("sensor_centroid_reproduction_residual_m", "oracle_centroid_reproduction_residual_m",
                  "oracle_vs_recorded_depth_readout_residual_m",
                  "raw_sensor_centroid_error_m", "fused_state_position_error_m", "sensor_pixel_purity", "iou"):
        values = [m[field] for m in metrics if m[field] is not None]
        summary[field] = {"n": len(values), "min": min(values) if values else None,
                          "max": max(values) if values else None, "mean": float(np.mean(values)) if values else None}
    return summary


def main():
    """Read-only input audit; writes a new, separate derived artifact directory."""
    import argparse
    import csv
    import json
    from pathlib import Path
    from .records import RunRecorder, code_identity, versions
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    summaries = [audit_referent_run(path) for path in args.runs]
    recorder = RunRecorder(args.output, {"input_runs": args.runs, "purpose": "raw_referent_audit_no_correction",
                                         "oracle": True},
                           {"run_id": Path(args.output).name, "code": code_identity(), "versions": versions()})
    try:
        for summary in summaries:
            recorder.record("referent_raw_audit", summary)
        recorder.record("termination", {"reason": "raw_referent_audit_complete", "runs": len(summaries)})
        output = Path(args.output)
        (output / "referent_audit.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n")
        items = [row for summary in summaries for row in summary["rows"]]
        with (output / "referent_audit.csv").open("w", newline="") as stream:
            if items:
                writer = csv.DictWriter(stream, fieldnames=list(items[0]))
                writer.writeheader()
                writer.writerows(items)
    finally:
        recorder.close()
    print(args.output)


if __name__ == "__main__":
    main()
