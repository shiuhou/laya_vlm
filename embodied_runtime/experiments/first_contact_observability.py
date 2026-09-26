"""Evaluator-only visibility of a retrospective, motion-corrected contact query."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .records import (RunRecorder, code_identity, file_hash, jsonable, load_records,
                      package_directory, repository_identity, versions)

VERSION = 'first-contact-observability-v0.1'
SOURCE_SHA256 = 'e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf'
PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/first_contact_observability_protocol.md'


def project_world(point, k, t):
    camera = np.linalg.solve(np.asarray(t), np.r_[point, 1.])[:3]
    if camera[2] <= 0 or not np.isfinite(camera).all():
        raise ValueError('query must be finite and in front of the calibrated camera')
    homogeneous = np.asarray(k)@camera
    return homogeneous[:2]/homogeneous[2], float(camera[2])


def backproject(uv, depth, k, t):
    camera = np.linalg.solve(np.asarray(k), np.r_[uv, 1.])*depth
    return (np.asarray(t)@np.r_[camera, 1.])[:3]


def local_point(point, pose):
    return np.asarray(pose['rotation']).T@(np.asarray(point)-pose['position'])


def world_point(point, pose):
    return np.asarray(pose['rotation'])@np.asarray(point)+pose['position']


def nearest_box_surface(point, halfsize):
    """Closest point on an axis-aligned box boundary, including interior queries."""
    p, size = np.asarray(point, dtype=float), np.asarray(halfsize, dtype=float)
    if p.shape != (3,) or size.shape != (3,) or not np.isfinite(p).all() or np.any(size <= 0):
        raise ValueError('finite three-vector and positive box halfsize required')
    nearest = np.clip(p, -size, size)
    if np.all(np.abs(p) <= size):
        axis = int(np.argmin(size-np.abs(p)))
        nearest[axis] = size[axis] if p[axis] >= 0 else -size[axis]
    return nearest


def pose_of(world, gid):
    return {'position': world.data.geom_xpos[gid].copy(),
            'rotation': world.data.geom_xmat[gid].reshape(3,3).copy()}


def one(rows, kind):
    values = [r['data'] for r in rows if r['kind'] == kind]
    if len(values) != 1:
        raise ValueError(f'exactly one {kind} required')
    return values[0]


def values(rows, kind, key):
    out = {}
    for r in rows:
        if r['kind'] == kind:
            if r['data'][key] in out:
                raise ValueError(f'duplicate {kind}')
            out[r['data'][key]] = r['data']
    return out


def restore(world, state):
    sim = world.env.sim
    sim.set_state_from_flattened(np.asarray(state))
    sim.forward()
    if not np.array_equal(sim.get_state().flatten(), state):
        raise ValueError('restored flattened state differs')


def geom_identity(world, gid, robot_root):
    import mujoco
    if gid < 0:
        return {'geom_id': gid, 'geom_name': None, 'body_name': None, 'mesh_name': None, 'category': 'no_hit'}
    model = world.model
    body = int(model.geom_bodyid[gid])
    ancestor = body
    while ancestor not in (0, robot_root):
        ancestor = int(model.body_parentid[ancestor])
    mesh = int(model.geom_dataid[gid]) if model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_MESH else -1
    return {'geom_id': gid,
            'geom_name': mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid),
            'body_id': body, 'body_name': mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body),
            'mesh_name': mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh) if mesh >= 0 else None,
            'geom_type': int(model.geom_type[gid]), 'geom_group': int(model.geom_group[gid]),
            'category': 'robot' if ancestor == robot_root else 'scene',
            'robot_membership_basis': 'body ancestry under recorded instantiated robot model root'}


def ray(world, uv, k, t, groups, robot_root):
    import mujoco
    local = np.linalg.solve(k, np.r_[uv, 1.])
    norm = float(np.linalg.norm(local))
    direction = np.ascontiguousarray(t[:3,:3]@(local/norm), dtype=np.float64)
    origin = np.ascontiguousarray(t[:3,3], dtype=np.float64)
    hit = np.full(1, -1, np.int32)
    distance = float(mujoco.mj_ray(world.model, world.data, origin, direction, groups, 1, -1, hit))
    return {'query_pixel_coordinates': np.asarray(uv).tolist(),
            'ray_origin_world_m': origin.tolist(), 'ray_direction_world_unit': direction.tolist(),
            'range_m': distance, 'optical_depth_m': distance/norm if distance >= 0 else None,
            'surface_world_m': (origin+direction*distance).tolist() if distance >= 0 else None,
            **geom_identity(world, int(hit[0]), robot_root)}


def image_difference(recorded, restored):
    rgb_diff = np.abs(recorded['rgb'].astype(float)-restored['rgb'].astype(float))
    depth_diff = np.abs(recorded['depth_m'].astype(float)-restored['depth_m'].astype(float))
    return {'rgb_exact': bool(np.array_equal(recorded['rgb'], restored['rgb'])),
            'rgb_different_pixels': int(np.count_nonzero(np.any(rgb_diff != 0, axis=-1))),
            'rgb_mean_absolute_channel_difference': float(rgb_diff.mean()),
            'rgb_max_absolute_channel_difference': float(rgb_diff.max()),
            'depth_exact': bool(np.array_equal(recorded['depth_m'], restored['depth_m'])),
            'depth_different_pixels': int(np.count_nonzero(depth_diff)),
            'depth_mean_absolute_difference_mm': float(depth_diff.mean()*1000),
            'depth_max_absolute_difference_mm': float(depth_diff.max()*1000)}


def pixel_measurement(world, frame, rendered, pixel, query, box_pose, size, groups, robot_root):
    x, y = pixel
    k, t = frame['intrinsics'], frame['camera_to_world']
    depth = float(frame['depth_m'][y,x])
    if not np.isfinite(depth) or depth <= 0:
        return {'pixel_xy': [x,y], 'status': 'invalid_recorded_depth'}
    uv = np.array([x+.5, y+.5])
    point = backproject(uv, depth, k, t)
    projected, recovered_depth = project_world(point, k, t)
    _, query_depth = project_world(query, k, t)
    r = ray(world, uv, k, t, groups, robot_root)
    point_local = local_point(point, box_pose)
    nearest = nearest_box_surface(point_local, size)
    return {'pixel_xy': [x,y], 'pixel_center_xy': uv.tolist(), 'status': 'measured',
            'sensor_optical_depth_m': depth, 'sensor_point_world_m': point.tolist(),
            'sensor_minus_query_optical_depth_mm': (depth-query_depth)*1000,
            'sensor_to_query_euclidean_mm': float(np.linalg.norm(point-query)*1000),
            'sensor_to_oracle_box_surface_mm': float(np.linalg.norm(point_local-nearest)*1000),
            'roundtrip_pixel_error': float(np.linalg.norm(projected-uv)),
            'roundtrip_depth_error_m': float(abs(recovered_depth-depth)),
            'restored_render_depth_m': float(rendered['depth_m'][y,x]),
            'recorded_minus_restored_depth_mm': float((depth-rendered['depth_m'][y,x])*1000),
            'rgb_exact_under_fresh_fk': bool(np.array_equal(frame['rgb'][y,x], rendered['rgb'][y,x])),
            'evaluator_visual_ray': r,
            'sensor_minus_ray_optical_depth_mm': None if r['optical_depth_m'] is None else (depth-r['optical_depth_m'])*1000}


def neighborhood(world, frame, rendered, center, radius, query, box_pose, size, groups, robot_root):
    h, w = frame['depth_m'].shape
    x0,y0 = center
    rows = [pixel_measurement(world, frame, rendered, (x,y), query, box_pose, size, groups, robot_root)
            for y in range(max(0,y0-radius), min(h,y0+radius+1))
            for x in range(max(0,x0-radius), min(w,x0+radius+1))]
    valid = [r for r in rows if r['status'] == 'measured']
    nearest = min(valid, key=lambda r:r['sensor_to_query_euclidean_mm']) if valid else None
    ray_counts = Counter(r['evaluator_visual_ray']['category'] for r in valid)
    geom_counts = Counter(str(r['evaluator_visual_ray']['geom_name']) for r in valid)
    return {'radius_pixels': radius, 'all_samples': rows, 'valid_samples': len(valid),
            'ray_category_counts': dict(ray_counts), 'ray_geom_counts': dict(geom_counts),
            'minimum_sensor_to_query_euclidean_mm': nearest['sensor_to_query_euclidean_mm'] if nearest else None,
            'nearest_recorded_support_pixel_xy': nearest['pixel_xy'] if nearest else None,
            'minimum_sensor_to_oracle_box_surface_mm': min((r['sensor_to_oracle_box_surface_mm'] for r in valid), default=None),
            'maximum_recorded_restored_depth_difference_mm': max((abs(r['recorded_minus_restored_depth_mm']) for r in valid), default=None),
            'maximum_absolute_sensor_ray_depth_residual_mm': max((abs(r['sensor_minus_ray_optical_depth_mm']) for r in valid if r['sensor_minus_ray_optical_depth_mm'] is not None), default=None)}


def make_figures(output, frames, measurements, after, initial_point):
    canvas = Image.new('RGB', (768, 830), 'white')
    draw = ImageDraw.Draw(canvas)
    for col, step in enumerate((24,25)):
        im = Image.fromarray(frames[step]['rgb'])
        mark = ImageDraw.Draw(im)
        p = measurements[step]['primary_projection']['pixel_coordinates']
        x,y = p
        mark.ellipse((x-5,y-5,x+5,y+5), outline='orange', width=2)
        uv,_ = project_world(initial_point, frames[step]['intrinsics'], frames[step]['camera_to_world'])
        tx,ty = uv
        mark.line((tx-4,ty,tx+4,ty), fill='cyan', width=2)
        mark.line((tx,ty-4,tx,ty+4), fill='cyan', width=2)
        canvas.paste(im,(col*384,30)); draw.text((col*384+5,5),f'Before action {step}: recorded RGB',fill='black')
        canvas.paste(Image.fromarray(after[col]),(col*384,440))
        draw.text((col*384+5,419),f'Action 25 after control {0 if col==0 else 7}: recorded RGB',fill='black')
    draw.text((4,814),'Orange: oracle carried box-surface query. Cyan: initial observed point, not refreshed.',fill='black')
    canvas.save(output/'recorded-rgb-oracle-query.png')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(12,8))
    for row,step in enumerate((24,25)):
        f=frames[step]; x,y=measurements[step]['primary_projection']['containing_pixel_xy']
        xlo,xhi=max(0,x-32),min(384,x+33); ylo,yhi=max(0,y-32),min(384,y+33)
        axes[row,0].imshow(f['rgb'][ylo:yhi,xlo:xhi],extent=(xlo,xhi,yhi,ylo))
        axes[row,0].plot(x+.5,y+.5,'+',color='orange',ms=12)
        axes[row,0].set_title(f'Before {step}: raw RGB crop / oracle query')
        bounds=(max(0,x-5),min(384,x+6),max(0,y-5),min(384,y+6))
        a,b,c,d=bounds
        im=axes[row,1].imshow(f['depth_m'][c:d,a:b]*1000,extent=(a,b,d,c),interpolation='nearest')
        axes[row,1].plot(x+.5,y+.5,'+',color='orange',ms=12);axes[row,1].set_title('Recorded optical depth (mm)')
        fig.colorbar(im,ax=axes[row,1])
        samples=measurements[step]['neighborhoods'][-1]['all_samples']
        labels=np.full((d-c,b-a),np.nan)
        for item in samples:
            px,py=item['pixel_xy']
            if item['status']=='measured': labels[py-c,px-a]={'scene':0,'robot':1,'no_hit':2}[item['evaluator_visual_ray']['category']]
        axes[row,2].imshow(labels,extent=(a,b,d,c),vmin=0,vmax=2,cmap='viridis',interpolation='nearest')
        axes[row,2].plot(x+.5,y+.5,'+',color='orange',ms=12)
        axes[row,2].set_title('Evaluator ray identity: purple scene / green robot')
        for ax in axes[row]:ax.set_xlabel('pixel x');ax.set_ylabel('pixel y')
    fig.tight_layout();fig.savefig(output/'depth-and-occlusion-audit.png',dpi=160);plt.close(fig)


def evaluate(source, output):
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_rgbd import LiberoRgbdSource
    import mujoco
    import robosuite.utils.camera_utils as camera_utils
    source,output=Path(source),Path(output)
    if file_hash(source/'episodes.jsonl') != SOURCE_SHA256:
        raise ValueError('frozen first-contact source required')
    records,diagnostics=load_records(source/'episodes.jsonl')
    if diagnostics:raise ValueError('complete evidence chain required')
    code=code_identity()
    if code['dirty_status']:raise ValueError('commit analytic code before evaluator run')
    start=one(records,'run_start');config=start['resolved_config'];environment=one(records,'environment')
    current_versions=versions()
    for package in ('numpy','mujoco','robosuite'):
        if current_versions[package]!=start['manifest']['versions'][package]:
            raise ValueError('geometry/render package version changed')
    capture_module='embodied_runtime/adapters/libero_rgbd.py'
    if code['source_sha256'][capture_module]!=start['manifest']['code']['source_sha256'][capture_module]:
        raise ValueError('recorded capture adapter changed')
    recorder=RunRecorder(output,{'version':VERSION,'source':str(source),'source_sha256':SOURCE_SHA256,
        'protocol_sha256':file_hash(PROTOCOL),'evaluator_only':True,'no_model_calls':True,
        'no_task_actions_after_model_bootstrap':True}, {'run_id':output.name,'code':code,'versions':versions()})
    backend=None
    try:
        controls=[r['data'] for r in records if r['kind']=='control_observation']
        threshold=environment['new_contact_force_threshold_N']
        first=next((c,contact) for c in controls for contact in c['contacts'] if contact['normal_force_N']>threshold)
        control,contact=first
        if (control['step'],control['control'])!=(25,0):raise ValueError('registered first sampled contact changed')
        captures=values(records,'vision_capture','capture_seq');paused=values(records,'paused_state_check','step')
        boundaries=values(records,'decision_boundary','step');trajectories=values(records,'demo_trajectory','step')
        if paused[25]['before']!=control['state_before']:raise ValueError('capture/control state mismatch')
        frames={};artifact_hashes={}
        for step in (24,25):
            p=paused[step];cap=captures[boundaries[step]['capture_seq']]
            if not p['unchanged'] or p['before']!=p['after'] or cap['capture_sim_time']!=p['before'][0]:raise ValueError('capture identity changed')
            path=source/cap['artifact'];digest=file_hash(path)
            if digest!=cap['artifact_sha256']:raise ValueError('capture hash changed')
            artifact_hashes[str(path)]=digest
            with np.load(path) as data:frames[step]={k:data[k].copy() for k in data.files}
        trajectory=trajectories[25];path=source/trajectory['artifact']
        if file_hash(path)!=trajectory['sha256']:raise ValueError('trajectory artifact changed')
        artifact_hashes[str(path)]=file_hash(path)
        with np.load(path) as data:
            if data['states_before'][0].tolist()!=control['state_before'] or data['states_before'][1].tolist()!=control['state_after']:raise ValueError('control/trajectory mismatch')
            after=data['frames'][[0,7]].copy()
        recorder.record('source_and_query',{'first_sampled_contact':contact,'step':25,'control':0,
            'artifact_sha256':artifact_hashes,'original_termination':one(records,'termination'),
            'contact_and_all_geometry_queries_are_oracle_evaluation_only':True,
            'post_contact_depth_available':False})
        backend=LiberoWorldBackend.from_task('top_drawer',seed=1,init_state_id=0,render=True,
            libero_root=config['libero_root'],config_dir=config['config_dir'])
        w=backend.world;sim=w.env.sim
        # The constructor's standard reset/ten settling controls instantiate the model.
        # Every subsequent physical action API is disabled for this analytic audit.
        def forbidden(*args,**kwargs):raise RuntimeError('physical controls forbidden in visibility evaluator')
        w.env.step=forbidden;w.execute=forbidden
        import jev_libero.world
        import libero
        repos={'jev':repository_identity(package_directory(jev_libero.world)),
               'libero':repository_identity(package_directory(libero))}
        expected=next(r['data']['environment_repositories'] for r in records if r['kind']=='manifest_update' and 'environment_repositories' in r['data'])
        if repos!=expected or w.config!=environment['task_config']:raise ValueError('environment/task identity changed')
        groups=np.asarray(mujoco.MjvOption().geomgroup,dtype=np.uint8).copy()
        flags={'render_collision_mesh':bool(w.env.env.render_collision_mesh),'render_visual_mesh':bool(w.env.env.render_visual_mesh)}
        groups[0],groups[1]=int(flags['render_collision_mesh']),int(flags['render_visual_mesh'])
        if groups[0] or not groups[1]:raise ValueError('registered visual-only ray groups required')
        gid=sim.model.geom_name2id('wooden_cabinet_1_g11');robot_gid=sim.model.geom_name2id('gripper0_finger1_collision')
        if set(contact['geom_ids'])!={gid,robot_gid} or w.model.geom_type[gid]!=mujoco.mjtGeom.mjGEOM_BOX:raise ValueError('registered contact box/pair changed')
        robot_root_name=w.env.robots[0].robot_model.root_body;robot_root=sim.model.body_name2id(robot_root_name)
        size=w.model.geom_size[gid].copy()
        recorder.record('evaluator_environment',{'repositories':repos,'render_flags':flags,'ray_groups':groups,
            'robot_root_body':robot_root_name,'contact_box':geom_identity(w,gid,robot_root),'box_halfsize_m':size,
            'robot_contact_geom':geom_identity(w,robot_gid,robot_root),
            'camera_utils_sha256':file_hash(camera_utils.__file__),
            'environment_variables':{k:os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')},
            'bootstrap':'standard world reset and ten open-jaw settling controls only; then no physical action APIs',
            'restore_method':'recorded flattened state plus sim.forward; original render agreement measured explicitly'})
        restore(w,control['state_after']);post=pose_of(w,gid)
        raw_point=np.asarray(contact['position_world_m']);local=local_point(raw_point,post)
        surface=nearest_box_surface(local,size)
        matches=[]
        for c in w.data.contact:
            if {int(c.geom1),int(c.geom2)}=={gid,robot_gid}:
                matches.append({'position_world_m':np.asarray(c.pos).tolist(),'distance_m':float(c.dist),
                    'recorded_midpoint_difference_mm':float(np.linalg.norm(c.pos-raw_point)*1000)})
        recorder.record('motion_correspondence',{'recorded_contact_point_world_m':raw_point,'post_geom_pose':post,
            'post_endpoint_local_contact_coordinate_m':local,'nearest_box_surface_local_m':surface,
            'midpoint_to_post_endpoint_box_surface_mm':float(np.linalg.norm(local-surface)*1000),
            'fresh_fk_contact_geometry_same_pair':matches,
            'not_exact_first_touch_material_point':True,'no_unstored_substep_reconstruction':True})
        measurements={};rendered_frames={};clouds={}
        initial_point=np.asarray(one(records,'initial_target_frozen')['admitted']['position_world_m'])
        for step in (24,25):
            restore(w,paused[step]['before']);before=sim.get_state().flatten().copy();pose=pose_of(w,gid)
            query=world_point(surface,pose);midpoint=world_point(local,pose)
            frame=frames[step];k,t=frame['intrinsics'],frame['camera_to_world']
            restored_k=camera_utils.get_camera_intrinsic_matrix(sim,'agentview',384,384)
            restored_t=camera_utils.get_camera_extrinsic_matrix(sim,'agentview')
            if not np.allclose(k,restored_k,rtol=0,atol=1e-12) or not np.allclose(t,restored_t,rtol=0,atol=1e-12):raise ValueError('restored camera differs from recorded calibration')
            rendered=LiberoRgbdSource(w).capture();rendered_frames[step]=rendered
            np.savez_compressed(output/f'evaluator-restored-before-{step}.npz',**{key:rendered[key] for key in ('rgb','depth_m','intrinsics','camera_to_world')})
            uv,z=project_world(query,k,t);center=np.floor(uv).astype(int)
            if not (0<=center[0]<384 and 0<=center[1]<384):raise ValueError('registered query outside source image')
            points={}
            for name,p in (('carried_surface',query),('carried_midpoint',midpoint),('uncorrected_post_contact',raw_point),('initial_sensor_point',initial_point)):
                u,d=project_world(p,k,t);points[name]={'world_m':p.tolist(),'pixel_coordinates':u.tolist(),'optical_depth_m':d}
            row={'step':step,'capture_seq':boundaries[step]['capture_seq'],'geom_pose':pose,
                 'oracle_queries':points,'primary_projection':{**points['carried_surface'],'containing_pixel_xy':center.tolist()},
                 'contact_geom_endpoint_translation_mm':((np.asarray(post['position'])-pose['position'])*1000).tolist(),
                 'raw_contact_to_carried_midpoint_mm':float(np.linalg.norm(raw_point-midpoint)*1000),
                 'contact_geom_endpoint_rotation_difference_frobenius':float(np.linalg.norm(np.asarray(post['rotation'])-pose['rotation'])),
                 'initial_sensor_point_to_query_mm':float(np.linalg.norm(initial_point-query)*1000),
                 'recorded_versus_restored_render':image_difference(frame,rendered),
                 'continuous_query_visual_ray':ray(w,uv,k,t,groups,robot_root),
                 'neighborhoods':[neighborhood(w,frame,rendered,tuple(center),r,query,pose,size,groups,robot_root) for r in (0,2,5)]}
            if not np.array_equal(before,sim.get_state().flatten()):raise ValueError('evaluator render/ray mutated flattened state')
            ys,xs=np.indices(frame['depth_m'].shape)
            camera=np.stack(((xs+.5-k[0,2])*frame['depth_m']/k[0,0],(ys+.5-k[1,2])*frame['depth_m']/k[1,1],frame['depth_m']),axis=-1)
            clouds[f'before_{step}_recorded_depth_pointcloud_world_m']=camera@t[:3,:3].T+t[:3,3]
            measurements[step]=row;recorder.record('visibility_measurement',row)
        np.savez_compressed(output/'recorded-depth-pointclouds.npz',**clouds)
        make_figures(output,frames,measurements,after,initial_point)
        recorder.record('artifact_manifest',{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.suffix in ('.npz','.png')})
        recorder.record('termination',{'reason':'bounded_visibility_audit_complete','boundary_measurements':2,
            'new_model_calls':0,'physical_task_actions_after_bootstrap':0})
    except BaseException as exc:
        recorder.record('failure',{'exception':repr(exc)});raise
    finally:
        if backend is not None:backend.close()
        recorder.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
    parser.add_argument('--output',required=True)
    args=parser.parse_args();evaluate(args.source,args.output)


if __name__=='__main__':main()
