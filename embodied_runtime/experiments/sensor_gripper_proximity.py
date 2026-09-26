"""Pure sensor-point to own-gripper-proxy diagnostic, without scene identity.

Inputs are calibrated optical depth/camera pose, static robot geometry and own
scalar joint positions. No simulator, archive, target, contact or policy API.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from .robot_only_geometry import forward

DISTANCE_LEVELS_M = (.001, .002, .005, .01, .02, .05)
NUMERIC_TOLERANCE = 1e-12


def dot(a, b):
    return np.einsum('...i,...i->...', a, b)


def closest_triangle(points, triangle):
    """Closest points on a nondegenerate closed triangle, vectorized over P."""
    a, b, c = np.asarray(triangle, dtype=float)
    ab, ac = b-a, c-a
    normal = np.cross(ab, ac)
    normal /= np.linalg.norm(normal)
    projection = points-dot(points-a, normal)[:, None]*normal
    ap = projection-a
    aa, bb, cc = dot(ab,ab), dot(ab,ac), dot(ac,ac)
    denominator = aa*cc-bb*bb
    u = (cc*dot(ap,ab)-bb*dot(ap,ac))/denominator
    v = (aa*dot(ap,ac)-bb*dot(ap,ab))/denominator
    inside = (u >= 0) & (v >= 0) & (u+v <= 1)
    best = np.full(len(points), np.inf)
    closest = np.empty_like(points)
    for start, end in ((a,b),(b,c),(c,a)):
        edge = end-start
        t = np.clip(dot(points-start,edge)/dot(edge,edge), 0, 1)
        candidate = start+t[:,None]*edge
        squared = dot(points-candidate,points-candidate)
        replace = squared < best
        best[replace], closest[replace] = squared[replace], candidate[replace]
    closest[inside] = projection[inside]
    return closest


def proxy_distance(points, vertices):
    """Euclidean distance to a solid convex hull; interior distance is zero."""
    points, vertices = np.asarray(points, dtype=float), np.asarray(vertices,dtype=float)
    hull = ConvexHull(vertices)
    best = np.full(len(points),np.inf)
    closest = np.zeros_like(points)
    inside = np.ones(len(points), dtype=bool)
    for normal_offset in hull.equations:
        inside &= dot(points,normal_offset[:3])+normal_offset[3] <= NUMERIC_TOLERANCE
    for triangle in vertices[hull.simplices]:
        candidate = closest_triangle(points,triangle)
        squared = dot(points-candidate,points-candidate)
        replace = squared < best
        best[replace], closest[replace] = squared[replace],candidate[replace]
    best[inside] = 0
    closest[inside] = points[inside]
    return np.sqrt(best), closest, inside


def depth_cloud(depth, intrinsics, camera_to_world):
    depth, k, transform = map(lambda a:np.asarray(a,dtype=float), (depth,intrinsics,camera_to_world))
    if depth.ndim != 2 or k.shape != (3,3) or transform.shape != (4,4):
        raise ValueError('Depth image and calibrated 3x3/4x4 matrices required')
    if not np.isfinite(k).all() or not np.isfinite(transform).all():
        raise ValueError('Finite camera calibration required')
    if not np.allclose(k[2],[0,0,1],rtol=0,atol=NUMERIC_TOLERANCE):
        raise ValueError('Conventional optical-depth camera intrinsics required')
    if not np.allclose(transform[3],[0,0,0,1],rtol=0,atol=NUMERIC_TOLERANCE):
        raise ValueError('Homogeneous camera pose required')
    if not np.allclose(transform[:3,:3].T@transform[:3,:3],np.eye(3),rtol=0,atol=1e-10):
        raise ValueError('Rigid calibrated camera orientation required')
    if not np.isclose(np.linalg.det(transform[:3,:3]),1.,rtol=0,atol=1e-10):
        raise ValueError('Proper camera orientation required')
    y,x = np.indices(depth.shape)
    pixels = np.column_stack((x.ravel()+.5,y.ravel()+.5,np.ones(depth.size)))
    rays = pixels@np.linalg.inv(k).T
    valid = np.isfinite(depth.ravel()) & (depth.ravel()>0)
    camera = rays[valid]*depth.ravel()[valid,None]
    return camera@transform[:3,:3].T+transform[:3,3], valid, pixels[:,:2]


def projected_proxy_mask(vertices, intrinsics, camera_to_world, shape):
    """Exclude the entire projected convex silhouette, regardless of depth.

    This conservative image-space exclusion is not a robot-pixel classifier.
    A proxy crossing the camera plane excludes the whole image rather than
    making a claim from an undefined finite projection.
    """
    vertices = np.asarray(vertices,dtype=float)
    transform = np.asarray(camera_to_world,dtype=float)
    camera = (vertices-transform[:3,3])@transform[:3,:3]
    if np.all(camera[:,2] <= 0):
        return np.zeros(shape,dtype=bool), {'status':'behind_camera','polygon_pixel_xy':[]}
    if np.any(camera[:,2] <= 0):
        return np.ones(shape,dtype=bool), {'status':'crosses_camera_plane_exclude_all','polygon_pixel_xy':[]}
    projected = camera@np.asarray(intrinsics).T
    projected = projected[:,:2]/projected[:,2,None]
    hull = ConvexHull(projected)
    y,x = np.indices(shape)
    pixels = np.column_stack((x.ravel()+.5,y.ravel()+.5))
    mask = np.ones(len(pixels),dtype=bool)
    for equation in hull.equations:
        mask &= dot(pixels,equation[:2])+equation[2] <= NUMERIC_TOLERANCE
    return mask.reshape(shape), {'status':'overlaps_pixel_centers' if mask.any() else 'outside_pixel_centers',
                                'polygon_pixel_xy':projected[hull.vertices].tolist()}


def measure(calibration, own_positions, depth, intrinsics, camera_to_world):
    robot = forward(calibration,own_positions)
    geometry_names = list(robot['geometries'])
    points, valid, pixels = depth_cloud(depth,intrinsics,camera_to_world)
    shape = np.shape(depth)
    distance_columns, closest_columns, inside_columns, masks, projections = [],[],[],[],{}
    for name, geometry in robot['geometries'].items():
        vertices = geometry['vertices_world_m']
        distance, closest, inside = proxy_distance(points,vertices)
        mask, projection = projected_proxy_mask(vertices,intrinsics,camera_to_world,shape)
        distance_columns.append(distance);closest_columns.append(closest);inside_columns.append(inside)
        masks.append(mask);projections[name] = projection
    distance = np.column_stack(distance_columns)
    closest = np.stack(closest_columns,axis=1)
    inside = np.column_stack(inside_columns)
    masks = np.stack(masks,axis=-1)
    union_mask = masks.any(axis=-1)
    unmasked = ~union_mask.ravel()[valid]
    best_proxy = np.argmin(distance,axis=1)
    union_distance = np.min(distance,axis=1)
    valid_pixels = pixels[valid]
    depths = np.asarray(depth).ravel()[valid]
    def stats(values, indices, proxy_indices):
        if not len(indices):
            return {'point_count':0,'nearest':None,'quantiles_m':None,
                    'counts_at_or_below_m':{str(level):0 for level in DISTANCE_LEVELS_M}}
        selected = values[indices]
        index = int(indices[np.argmin(selected)])
        proxy = int(proxy_indices[index])
        return {'point_count':len(indices), 'nearest':{
            'distance_m':float(values[index]), 'pixel_xy':np.floor(valid_pixels[index]).astype(int).tolist(),
            'pixel_center_xy':valid_pixels[index].tolist(), 'depth_m':float(depths[index]),
            'point_world_m':points[index].tolist(), 'proxy':geometry_names[proxy],
            'closest_solid_proxy_point_world_m':closest[index,proxy].tolist(),
            'inside_proxy':bool(inside[index,proxy])},
            'quantiles_m':dict(zip(('minimum','p01','p10','median'),np.quantile(selected,[0,.01,.1,.5]).tolist())),
            'counts_at_or_below_m':{str(level):int(np.count_nonzero(selected <= level)) for level in DISTANCE_LEVELS_M}}
    groups = {}
    for label, indices in (('all_valid_depth',np.arange(len(points))),
                           ('outside_partial_gripper_silhouette',np.flatnonzero(unmasked))):
        per_proxy = {name:stats(distance[:,i],indices,np.full(len(points),i)) for i,name in enumerate(geometry_names)}
        union = stats(union_distance,indices,best_proxy)
        union['nearest_proxy_contributions_at_or_below_m'] = {
            str(level):{name:int(np.count_nonzero((union_distance[indices]<=level)&(best_proxy[indices]==i)))
                        for i,name in enumerate(geometry_names)} for level in DISTANCE_LEVELS_M}
        groups[label] = {'union':union,'per_proxy':per_proxy}
    distance_image = np.full((*shape,len(geometry_names)),np.nan)
    distance_image.reshape(-1,len(geometry_names))[valid] = distance
    output = {'geometry_names':geometry_names,'valid_depth_pixels':int(valid.sum()),
              'invalid_depth_pixels':int((~valid).sum()),'partial_mask_pixels':int(union_mask.sum()),
              'partial_mask_valid_depth_pixels':int(union_mask.ravel()[valid].sum()),
              'projection':projections,'groups':groups,
              'residual_point_identity':'unknown; arm/wrist and visual-proxy differences may remain',
              'distance_semantics':'distance to known solid convex robot proxy from recorded finite positive depth points; interior zero',
              'missing_or_occluded_geometry':'unknown; no free-space inference'}
    arrays = {'distance_to_proxy_m':distance_image,'partial_gripper_mask':union_mask,
              'per_proxy_projected_masks':masks,'valid_depth_mask':valid.reshape(shape)}
    return output,arrays


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    source, output = Path(args.input),Path(args.output)
    request = json.loads((source/'request.json').read_text())
    if set(request) != {'calibration','own_joint_packets'}:
        raise ValueError('Only robot calibration and own joint packets admitted')
    if set(request['own_joint_packets']) != {'sample0','sample1'}:
        raise ValueError('Exactly the two frozen opaque sample identifiers required')
    output.mkdir(exist_ok=False)
    results = {}
    for label, packet in request['own_joint_packets'].items():
        if label not in {'sample0','sample1'}:
            raise ValueError('Fixed opaque sample identifiers required')
        with np.load(source/f'{label}.npz',allow_pickle=False) as frame:
            if set(frame.files) != {'depth_m','intrinsics','camera_to_world'}:
                raise ValueError('Only recorded depth and camera calibration admitted')
            result, arrays = measure(request['calibration'],packet,frame['depth_m'],
                                     frame['intrinsics'],frame['camera_to_world'])
        results[label] = result
        np.savez_compressed(output/f'{label}-arrays.npz',**arrays)
    with (output/'measurements.json').open('x') as stream:
        json.dump(results,stream,indent=2,allow_nan=False);stream.write('\n')
