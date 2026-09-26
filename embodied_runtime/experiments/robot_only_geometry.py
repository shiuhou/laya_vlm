"""Pure own-joint forward kinematics over a standalone robot calibration.

No simulator, task, scene, target, contact, dynamics or full-state input exists.
The supported calibration contains fixed bodies, scalar hinges/slides, sites,
and finite vertex sets for known robot collision geometry.
"""
from __future__ import annotations

import numpy as np

VERSION = 'robot-only-static-chain-v1'


def quaternion_matrix(wxyz):
    q = np.asarray(wxyz, dtype=float)
    if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) == 0:
        raise ValueError('Finite nonzero wxyz quaternion required')
    w,x,y,z = q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def axis_rotation(axis, angle):
    axis = vector(axis)
    length = np.linalg.norm(axis)
    if not np.isclose(length, 1., rtol=0, atol=1e-12):
        raise ValueError('Calibrated joint axis must be unit length')
    x,y,z = axis
    cross = np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)*np.cos(angle)+(1-np.cos(angle))*np.outer(axis,axis)+np.sin(angle)*cross


def vector(value):
    result = np.asarray(value,dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError('Finite three-vector required')
    return result


def pose(position, rotation):
    return {'position_world_m':position.tolist(), 'rotation_world':rotation.tolist()}


def forward(calibration, joint_positions):
    """Infer poses/extents from own scalar encoders and static robot-only data."""
    if set(calibration) != {'version','bodies','sites','geometries'} or calibration['version'] != VERSION:
        raise ValueError('Standalone robot calibration schema required')
    names = [j['name'] for body in calibration['bodies'] for j in body['joints']]
    if len(names) != len(set(names)) or set(joint_positions) != set(names):
        raise ValueError('Exactly the calibrated own-joint encoders are required')
    if not all(np.asarray(value).shape == () and np.isfinite(value) for value in joint_positions.values()):
        raise ValueError('Own-joint encoder values must be finite scalars')
    transforms = {}
    result = {'bodies':{},'sites':{},'geometries':{}}
    for body in calibration['bodies']:
        parent = body['parent']
        if body['name'] in transforms:
            raise ValueError('Body names must be unique')
        if parent is None:
            parent_pos,parent_rot = np.zeros(3),np.eye(3)
        elif parent in transforms:
            parent_pos,parent_rot = transforms[parent]
        else:
            raise ValueError('Robot chain must be parent-first and self-contained')
        position = parent_pos+parent_rot@vector(body['position_parent_m'])
        rotation = parent_rot@quaternion_matrix(body['quaternion_parent_wxyz'])
        for joint in body['joints']:
            delta = float(joint_positions[joint['name']])-float(joint['qpos_reference'])
            axis = vector(joint['axis_body'])
            if joint['kind'] == 'hinge':
                anchor = vector(joint['anchor_body_m'])
                anchor_world = position+rotation@anchor
                rotation = rotation@axis_rotation(axis,delta)
                position = anchor_world-rotation@anchor
            elif joint['kind'] == 'slide':
                if not np.isclose(np.linalg.norm(axis),1.,rtol=0,atol=1e-12):
                    raise ValueError('Calibrated joint axis must be unit length')
                position = position+rotation@axis*delta
            else:
                raise ValueError('Only calibrated scalar hinge and slide joints are supported')
        transforms[body['name']] = position,rotation
        result['bodies'][body['name']] = pose(position,rotation)
    for family in ('sites','geometries'):
        for item in calibration[family]:
            if item['body'] not in transforms or item['name'] in result[family]:
                raise ValueError('Unique robot-owned geometry/site required')
            body_pos,body_rot = transforms[item['body']]
            position = body_pos+body_rot@vector(item['position_body_m'])
            rotation = body_rot@quaternion_matrix(item['quaternion_body_wxyz'])
            observation = pose(position,rotation)
            if family == 'geometries':
                local = np.asarray(item['vertices_local_m'],dtype=float)
                if local.ndim != 2 or local.shape[1] != 3 or not len(local) or not np.isfinite(local).all():
                    raise ValueError('Finite robot geometry vertex set required')
                vertices = local@rotation.T+position
                observation.update(vertices_world_m=vertices.tolist(),
                    aabb_world_m=[vertices.min(axis=0).tolist(),vertices.max(axis=0).tolist()],
                    shape_representation=item['shape_representation'])
            result[family][item['name']] = observation
    return result


def extract_own_positions(flattened_archive_state, own_position_flat_indices):
    """Archive boundary adapter: indexes only allowed encoders, never other state.

    This is retrospective extraction from a privileged container, not evidence
    that a physical joint sensor supplied these records. Indices are calibration
    metadata; the pure forward estimator receives only this returned dictionary.
    """
    result = {name:float(flattened_archive_state[index]) for name,index in own_position_flat_indices.items()}
    if not all(np.isfinite(value) for value in result.values()):
        raise ValueError('Extracted own encoder value is nonfinite')
    return result


if __name__ == '__main__':
    # A separate process receives only serialized robot calibration and own joints.
    # No archive path, full state, environment model, or evaluator payload is passed.
    import json
    import sys
    request = json.load(sys.stdin)
    if set(request) != {'calibration','joint_packets'}:
        raise ValueError('Only robot calibration and own encoder packets accepted')
    json.dump({name:forward(request['calibration'],packet) for name,packet in request['joint_packets'].items()},
              sys.stdout,allow_nan=False)
    sys.stdout.write('\n')
