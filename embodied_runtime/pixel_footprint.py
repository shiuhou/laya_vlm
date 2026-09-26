"""Geometric sample footprints; no depth resolve, scene ownership or clearance.

Image coordinates use top-left *pixel edges*: pixel (x, y) has center
(x + .5, y + .5). Camera K must use that same convention. Triangle coverage
is a two-sided geometric candidate, not an emulation of GPU raster rules.
"""
from __future__ import annotations

import numpy as np


def flipped_sample_locations(pixel_xy, samples_bottom_left):
    """Map GL samples in bottom-left pixels to a vertically flipped image."""
    pixels = np.asarray(pixel_xy)
    samples = np.asarray(samples_bottom_left, dtype=float)
    if pixels.shape[-1:] != (2,) or not np.isfinite(pixels).all():
        raise ValueError("Finite pixel xy pairs required")
    if (pixels < 0).any() or (pixels != np.floor(pixels)).any():
        raise ValueError("Nonnegative integer pixel indices required")
    if samples.ndim != 2 or samples.shape[1] != 2 or not len(samples):
        raise ValueError("Nonempty sample xy pairs required")
    if not np.isfinite(samples).all() or (samples < 0).any() or (samples >= 1).any():
        raise ValueError("GL sample offsets must lie in [0, 1)")
    offsets = np.column_stack((samples[:, 0], 1 - samples[:, 1]))
    return pixels[..., None, :] + offsets


def _intrinsics(intrinsics):
    k = np.asarray(intrinsics, dtype=float)
    if (k.shape != (3, 3) or not np.isfinite(k).all()
            or not np.array_equal(k[2], [0, 0, 1])
            or k[1, 0] != 0 or k[0, 0] <= 0 or k[1, 1] <= 0):
        raise ValueError("Conventional finite optical-camera K required")
    return k


def optical_rays(image_xy, intrinsics):
    """Return unnormalized camera rays whose z=1 makes ray scale optical depth."""
    xy = np.asarray(image_xy, dtype=float)
    if xy.shape[-1:] != (2,) or not np.isfinite(xy).all():
        raise ValueError("Finite image xy pairs required")
    homogeneous = np.concatenate((xy, np.ones((*xy.shape[:-1], 1))), axis=-1)
    return homogeneous @ np.linalg.inv(_intrinsics(intrinsics)).T


def camera_vertices(vertices_world, camera_to_world):
    vertices = np.asarray(vertices_world, dtype=float)
    transform = np.asarray(camera_to_world, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Finite vertex xyz rows required")
    if (transform.shape != (4, 4) or not np.isfinite(transform).all()
            or not np.array_equal(transform[3], [0, 0, 0, 1])
            or not np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3),
                               rtol=0, atol=1e-12)
            or not np.isclose(np.linalg.det(transform[:3, :3]), 1, rtol=0, atol=1e-12)):
        raise ValueError("Rigid optical camera-to-world transform required")
    return (vertices - transform[:3, 3]) @ transform[:3, :3]


def triangle_sample_depths(vertices_camera, faces, intrinsics, image_shape,
                           samples_bottom_left):
    """Nearest positive optical depth at each sample across two-sided triangles.

    Perspective-correct triangle interpolation computes ray/plane intersection
    depth. Edges are included without a fitted geometric tolerance. Degenerate
    projected triangles have no area and are skipped. Camera-plane crossings
    are rejected rather than silently applying an uncalibrated clip rule.
    NaN means no modeled triangle intersection, never observed free space.
    """
    vertices = np.asarray(vertices_camera, dtype=float)
    faces = np.asarray(faces)
    shape = np.asarray(image_shape)
    if shape.shape != (2,) or (shape <= 0).any() or (shape != np.floor(shape)).any():
        raise ValueError("Positive integer image height and width required")
    height, width = map(int, shape)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Finite vertex xyz rows required")
    if (faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer)
            or (faces < 0).any() or (faces >= len(vertices)).any()):
        raise ValueError("Integer triangle vertex indices required")
    if (vertices[:, 2] <= 0).any():
        raise ValueError("All modeled vertices must be in front of the camera plane")
    offsets = flipped_sample_locations([0, 0], samples_bottom_left)
    projected = vertices @ _intrinsics(intrinsics).T
    projected = projected[:, :2] / projected[:, 2, None]
    depth = np.full((height, width, len(offsets)), np.inf)
    edge = np.zeros(depth.shape, dtype=bool)
    degenerate = 0

    def cross(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

    for face in faces:
        triangle = projected[face]
        denominator = cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        if denominator == 0:
            degenerate += 1
            continue
        lower = np.ceil(triangle.min(axis=0) - offsets.max(axis=0)).astype(int)
        upper = np.floor(triangle.max(axis=0) - offsets.min(axis=0)).astype(int)
        x0, y0 = np.maximum(lower, [0, 0])
        x1, y1 = np.minimum(upper, [width - 1, height - 1])
        if x0 > x1 or y0 > y1:
            continue
        y, x = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        locations = np.stack((x, y), axis=-1)[..., None, :] + offsets
        b0 = cross(triangle[1] - locations, triangle[2] - locations) / denominator
        b1 = cross(triangle[2] - locations, triangle[0] - locations) / denominator
        b2 = cross(triangle[0] - locations, triangle[1] - locations) / denominator
        inside = (b0 >= 0) & (b1 >= 0) & (b2 >= 0)
        inverse_z = b0 / vertices[face[0], 2] + b1 / vertices[face[1], 2] + b2 / vertices[face[2], 2]
        candidate = np.full(inside.shape, np.inf)
        np.divide(1., inverse_z, out=candidate, where=inside & (inverse_z > 0))
        region = depth[y0:y1 + 1, x0:x1 + 1]
        edge_region = edge[y0:y1 + 1, x0:x1 + 1]
        triangle_edge = inside & ((b0 == 0) | (b1 == 0) | (b2 == 0))
        nearer = candidate < region
        tied = np.isfinite(candidate) & (candidate == region)
        edge_region[nearer] = triangle_edge[nearer]
        edge_region[tied] |= triangle_edge[tied]
        region[nearer] = candidate[nearer]
    coverage = np.isfinite(depth)
    depth[~coverage] = np.nan
    return {"potential_coverage": coverage, "potential_depth_m": depth,
            "geometric_edge_hit": edge, "degenerate_projected_triangles": degenerate}


def own_gripper_footprint(resolved_depth_m, intrinsics, camera_to_world,
                          own_meshes_world, samples_bottom_left):
    """Keep the observed scalar separate from own-only geometric predictions.

    own_meshes_world is a sequence of (vertices_world, triangle_faces) pairs
    from robot calibration and own joint FK. Scene geometry is not an input.
    Neither all-sample nor zero-sample coverage determines observed ownership.
    """
    resolved = np.asarray(resolved_depth_m)
    if resolved.ndim != 2 or not np.issubdtype(resolved.dtype, np.floating):
        raise ValueError("Floating two-dimensional resolved depth required")
    y, x = np.indices(resolved.shape)
    locations = flipped_sample_locations(np.stack((x, y), axis=-1), samples_bottom_left)
    rays = optical_rays(locations, intrinsics)
    nearest = np.full(rays.shape[:-1], np.inf)
    nearest_geometry = np.full(nearest.shape, -1, dtype=np.int32)
    geometry_tie = np.zeros(nearest.shape, dtype=bool)
    edge = np.zeros(nearest.shape, dtype=bool)
    degenerate = 0
    if not own_meshes_world:
        raise ValueError("At least one own-gripper triangle mesh required")
    for index, (vertices, faces) in enumerate(own_meshes_world):
        result = triangle_sample_depths(camera_vertices(vertices, camera_to_world), faces,
                                       intrinsics, resolved.shape, samples_bottom_left)
        candidate = result["potential_depth_m"]
        nearer = np.isfinite(candidate) & (candidate < nearest)
        tied = np.isfinite(candidate) & (candidate == nearest)
        nearest[nearer] = candidate[nearer]
        nearest_geometry[nearer] = index
        edge[nearer] = result["geometric_edge_hit"][nearer]
        geometry_tie[nearer] = False
        edge[tied] |= result["geometric_edge_hit"][tied]
        geometry_tie[tied] = True
        degenerate += result["degenerate_projected_triangles"]
    coverage = np.isfinite(nearest)
    nearest[~coverage] = np.nan
    return {"resolved_depth_m": resolved.copy(), "sample_rays_camera": rays,
            "potential_own_coverage": coverage, "potential_own_depth_m": nearest,
            "nearest_own_geometry_index": nearest_geometry, "geometric_edge_hit": edge,
            "nearest_own_geometry_tie": geometry_tie,
            "covered_sample_count": coverage.sum(axis=-1),
            "degenerate_projected_triangles": degenerate,
            "observed_ownership": "unknown", "unmodeled_or_occluded_space": "unknown",
            "depth_resolve_rule": "unspecified; no scalar-to-sample assignment",
            "geometry_tie_rule": "first input geometry index retained; exact ties flagged",
            "coverage_semantics": "two-sided geometric potential only; GPU edge/clip/cull rules not emulated"}
