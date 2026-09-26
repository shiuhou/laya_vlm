"""Mask-only control over unchanged observed-point / collision distance maps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .robot_only_geometry import forward
from .sensor_gripper_proximity import DISTANCE_LEVELS_M, depth_cloud, projected_proxy_mask


def summarize(distance,eligible,names,depth,k,t):
    """Read previously sealed distances; never construct a collision distance."""
    flat=np.flatnonzero(eligible.ravel());selected=distance.reshape(-1,len(names))[flat]
    y,x=np.unravel_index(flat,eligible.shape)
    def stats(values,proxy_indices):
        if not len(values):return {'point_count':0,'nearest':None,'quantiles_m':None,
            'counts_at_or_below_m':{str(level):0 for level in DISTANCE_LEVELS_M}}
        i=int(np.argmin(values));point=t[:3,:3]@(np.linalg.solve(k,[x[i]+.5,y[i]+.5,1])*depth[y[i],x[i]])+t[:3,3]
        return {'point_count':len(values),'nearest':{'distance_m':float(values[i]),
            'pixel_xy':[int(x[i]),int(y[i])],'pixel_center_xy':[float(x[i]+.5),float(y[i]+.5)],
            'point_world_m':point.tolist(),'depth_m':float(depth[y[i],x[i]]),'proxy':names[int(proxy_indices[i])]},
            'quantiles_m':dict(zip(('minimum','p01','p10','median'),np.quantile(values,[0,.01,.1,.5]).tolist())),
            'counts_at_or_below_m':{str(level):int(np.count_nonzero(values<=level)) for level in DISTANCE_LEVELS_M}}
    minimum=np.min(selected,axis=1);best=np.argmin(selected,axis=1)
    union=stats(minimum,best)
    union['nearest_proxy_contributions_at_or_below_m']={str(level):{name:int(np.count_nonzero((minimum<=level)&(best==i)))
        for i,name in enumerate(names)} for level in DISTANCE_LEVELS_M}
    return {'union':union,'per_proxy':{name:stats(selected[:,i],np.full(len(flat),i)) for i,name in enumerate(names)}}


def measure(visual_calibration,packet,names,frame,reference):
    depth,k,t=[frame[key] for key in ('depth_m','intrinsics','camera_to_world')]
    _,valid,_=depth_cloud(depth,k,t);valid=valid.reshape(depth.shape)
    distance=reference['distance_to_proxy_m'];old=reference['partial_gripper_mask']
    if distance.shape!=(*depth.shape,len(names)) or not np.array_equal(valid,reference['valid_depth_mask']):
        raise ValueError('Frozen map shape/validity differs from unchanged depth')
    if not np.isfinite(distance[valid]).all() or (distance[valid]<0).any():raise ValueError('Invalid sealed distance map')
    geometries=forward(visual_calibration,packet)['geometries'];masks=[];projections={}
    for name,geometry in geometries.items():
        mask,projection=projected_proxy_mask(geometry['vertices_world_m'],k,t,depth.shape)
        masks.append(mask);projections[name]=projection
    individual=np.stack(masks,axis=-1);visual=individual.any(axis=-1)
    groups={'collision_mask_residual':summarize(distance,valid&~old,names,depth,k,t),
            'visual_mask_residual':summarize(distance,valid&~visual,names,depth,k,t)}
    old_stats=groups['collision_mask_residual']
    excluded={}
    for name,stats in [('union',old_stats['union']),*old_stats['per_proxy'].items()]:
        witness=stats['nearest']
        excluded[name]=None if witness is None else {'old_nearest_pixel_xy':witness['pixel_xy'],
            'old_distance_m':witness['distance_m'],'excluded_by_visual_mask':bool(visual[witness['pixel_xy'][1],witness['pixel_xy'][0]])}
    result={'geometry_names':names,'visual_geometry_names':list(geometries),'visual_projection':projections,
        'valid_depth_pixels':int(valid.sum()),'mask_counts':{'old_collision':int(old.sum()),'new_visual':int(visual.sum()),
            'newly_excluded':int((visual&~old).sum()),'newly_admitted':int((old&~visual).sum()),
            'intersection':int((visual&old).sum())},'groups':groups,'old_nearest_witness_exclusion':excluded,
        'distance_maps_recomputed':False,'residual_identities':'unknown','occluded_or_missing_space':'unknown'}
    return result,{'visual_mask':visual,'individual_visual_masks':individual}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source,output=Path(a.input),Path(a.output);request=json.loads((source/'request.json').read_text())
    if set(request)!={'visual_calibration','own_joint_packets','distance_proxy_names'} or set(request['own_joint_packets'])!={'sample0','sample1'}:
        raise ValueError('Strict robot/depth/distance-map boundary required')
    if len(request['visual_calibration']['geometries'])!=3 or len(request['distance_proxy_names'])!=5:
        raise ValueError('Frozen three visual meshes and five collision distance maps required')
    output.mkdir(exist_ok=False);results={}
    for label,packet in request['own_joint_packets'].items():
        with np.load(source/f'{label}.npz',allow_pickle=False) as f,np.load(source/f'{label}-arrays.npz',allow_pickle=False) as r:
            if set(f.files)!={'depth_m','intrinsics','camera_to_world'} or set(r.files)!={'distance_to_proxy_m','partial_gripper_mask','per_proxy_projected_masks','valid_depth_mask'}:
                raise ValueError('Unexpected sanitized sensor/reference-map schema')
            result,arrays=measure(request['visual_calibration'],packet,request['distance_proxy_names'],f,r)
        results[label]=result;np.savez_compressed(output/f'{label}-visual-mask.npz',**arrays)
    with (output/'measurements.json').open('x') as stream:json.dump(results,stream,indent=2,allow_nan=False);stream.write('\n')
