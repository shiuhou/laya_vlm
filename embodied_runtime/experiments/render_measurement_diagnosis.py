"""Evaluator-only exact prefix reconstruction and fixed-cache raster diagnosis."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import time

import numpy as np

from .records import code_identity,file_hash,load_records,versions
from .robot_geometry_probe import export_robot_static,write
from .robot_only_geometry import extract_own_positions,forward
from .sensor_gripper_proximity_probe import ARCHIVE_SHA256,CALIBRATION_SHA256,SELECTION
from .gripper_visual_mask_probe import VISUAL_SHA256

PROTOCOL=Path(__file__).resolve().parents[2]/'docs/research/render_measurement_diagnosis_protocol.md'
WITNESSES={24:((216,97),(147,162),(147,163),(165,176),(165,177),(237,102)),
           25:((119,126),(156,165),(236,145),(240,110),(156,155))}
CACHE_FIELDS=('qpos','qvel','act','act_dot','qacc','qacc_warmstart','ctrl','qfrc_applied','xfrc_applied',
              'sensordata','xpos','xquat','xmat','xipos','ximat','geom_xpos','geom_xmat',
              'site_xpos','site_xmat','cam_xpos','cam_xmat','mocap_pos','mocap_quat','userdata')
CONTEXT_INVARIANTS=('geomgroup','render_collision_mesh','render_visual_mesh','offWidth','offHeight',
                    'readDepthMap','scene_flags','model_integrator','model_timestep_s')


def array_hash(value):
    a=np.ascontiguousarray(value);h=hashlib.sha256()
    h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()


def cache_hashes(data):
    return {'time':array_hash([float(data.time)]),**{name:array_hash(getattr(data,name)) for name in CACHE_FIELDS}}


def context_record(world):
    import mujoco
    context=world.env.sim._render_context_offscreen;model=world.model
    record={'model_requested_offsamples':int(model.vis.quality.offsamples),
        'context_actual_offSamples':int(context.con.offSamples),'geomgroup':context.vopt.geomgroup.tolist(),
        'render_collision_mesh':bool(world.env.env.render_collision_mesh),'render_visual_mesh':bool(world.env.env.render_visual_mesh),
        'offWidth':int(context.con.offWidth),'offHeight':int(context.con.offHeight),'readDepthMap':int(context.con.readDepthMap),
        'model_integrator':int(model.opt.integrator),'model_timestep_s':float(model.opt.timestep),
        'scene_flags':context.scn.flags.tolist()}
    try:
        from OpenGL import GL
        context.gl_ctx.make_current();GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,int(context.con.offFBO))
        record['gl']={name:GL.glGetString(flag).decode() for name,flag in
                      (('vendor',GL.GL_VENDOR),('renderer',GL.GL_RENDERER),('version',GL.GL_VERSION))}
        record['gl']['bound_framebuffer_samples']=int(GL.glGetIntegerv(GL.GL_SAMPLES))
        record['gl']['sample_positions_bottom_left_pixel_coordinates']=[
            np.asarray(GL.glGetMultisamplefv(GL.GL_SAMPLE_POSITION,i),dtype=float).tolist()
            for i in range(int(context.con.offSamples))]
    except Exception as exc:
        record['gl_introspection_error']=str(exc)
    finally:
        mujoco.mjr_restoreBuffer(context.con)
    return record


def compare_frames(native,other):
    rgb=np.abs(native['rgb'].astype(int)-other['rgb'].astype(int));depth=other['depth_m'].astype(float)-native['depth_m']
    fields=('rgb','depth_m','intrinsics','camera_to_world')
    return {'array_exact':{key:array_hash(native[key])==array_hash(other[key]) for key in fields},
        'native_array_sha256':{key:array_hash(native[key]) for key in fields},
        'other_array_sha256':{key:array_hash(other[key]) for key in fields},
        'rgb_different_pixels':int(np.count_nonzero(np.any(rgb!=0,axis=-1))),'rgb_max_channel_difference':int(rgb.max()),
        'depth_different_pixels':int(np.count_nonzero(depth)),'depth_max_absolute_difference_m':float(np.max(np.abs(depth))),
        'depth_mean_absolute_difference_m':float(np.mean(np.abs(depth)))}


def check_context_invariants(native,zero):
    changes={key:{'native':native[key],'zero':zero[key]} for key in CONTEXT_INVARIANTS if native[key]!=zero[key]}
    if changes:raise RuntimeError('Non-sampling render configuration changed: '+json.dumps(changes))


def witness_comparison(native,zero,centers):
    rows=[]
    for x,y in centers:
        pixels=[]
        for yy in range(y-1,y+2):
            for xx in range(x-1,x+2):
                pixels.append({'pixel_xy':[xx,yy],'native_rgb':native['rgb'][yy,xx].tolist(),
                    'zero_rgb':zero['rgb'][yy,xx].tolist(),'native_depth_m':float(native['depth_m'][yy,xx]),
                    'zero_depth_m':float(zero['depth_m'][yy,xx]),
                    'zero_minus_native_depth_m':float(zero['depth_m'][yy,xx])-float(native['depth_m'][yy,xx])})
        rows.append({'center_pixel_xy':[x,y],'all_3x3_pixels':pixels})
    return rows


def projected(vertices,k,t):
    camera=(np.asarray(vertices)-t[:3,3])@t[:3,:3]
    if np.any(camera[:,2]<=0):raise ValueError('Registered robot projection crosses camera plane')
    uv=camera@k.T
    return uv[:,:2]/uv[:,2,None]


def compare_robot_cache(world,calibrations,packet,frame):
    """Pure FK receives calibration/own values; evaluator separately reads caches."""
    rows=[]
    for family,calibration in calibrations.items():
        estimate=forward(calibration,packet)
        for geom in calibration['geometries']:
            name=geom['name'];gid=int(world.env.sim.model.geom_name2id(name))
            position=world.data.geom_xpos[gid].copy();rotation=world.data.geom_xmat[gid].reshape(3,3).copy()
            vertices=np.asarray(geom['vertices_local_m'])@rotation.T+position
            inferred=estimate['geometries'][name];fk_vertices=np.asarray(inferred['vertices_world_m'])
            cache_uv=projected(vertices,frame['intrinsics'],frame['camera_to_world'])
            fk_uv=projected(fk_vertices,frame['intrinsics'],frame['camera_to_world'])
            displacement=np.linalg.norm(vertices-fk_vertices,axis=1);pixel_delta=np.linalg.norm(cache_uv-fk_uv,axis=1)
            rows.append({'family':family,'geometry':name,'cached_position_world_m':position.tolist(),
                'cached_rotation_world':rotation.tolist(),'fk_position_world_m':inferred['position_world_m'],
                'fk_rotation_world':inferred['rotation_world'],'position_difference_m':(position-inferred['position_world_m']).tolist(),
                'rotation_element_max_error':float(np.max(np.abs(rotation-inferred['rotation_world']))),
                'vertex_count':len(vertices),'vertex_displacement_max_m':float(displacement.max()),
                'vertex_displacement_median_m':float(np.median(displacement)),
                'projected_vertex_displacement_max_px':float(pixel_delta.max()),
                'projected_vertex_displacement_median_px':float(np.median(pixel_delta))})
    return rows


def run(source,robot_source,visual_source,output):
    import mujoco
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_rgbd import LiberoRgbdSource
    from jev_libero.environment import load_libero
    source,robot_source,visual_source,output=map(Path,(source,robot_source,visual_source,output))
    code=code_identity()
    if code['dirty_status']:raise ValueError('Freeze evaluator code before reconstruction')
    for path,expected in ((source/'episodes.jsonl',ARCHIVE_SHA256),(robot_source/'robot-calibration.json',CALIBRATION_SHA256),
                          (visual_source/'gripper-visual-calibration.json',VISUAL_SHA256)):
        if file_hash(path)!=expected:raise ValueError('Frozen source differs: '+str(path))
    rows,errors=load_records(source/'episodes.jsonl')
    if errors:raise ValueError('Source chain invalid')
    config=next(r['data']['resolved_config'] for r in rows if r['kind']=='run_start')
    initial=next(r['data']['sim_state'] for r in rows if r['kind']=='environment')
    controls=[r['data'] for r in rows if r['kind']=='control_observation' and r['data']['step']<25]
    if len(controls)!=200 or [(r['step'],r['control']) for r in controls]!=[(s,c) for s in range(25) for c in range(8)]:
        raise ValueError('Frozen 200-control prefix differs')
    original_frames={}
    for step,artifact,expected in SELECTION:
        if file_hash(source/artifact)!=expected:raise ValueError('Original frame differs')
        with np.load(source/artifact,allow_pickle=False) as f:original_frames[step]={key:f[key] for key in f.files}
    calibrations={'collision':json.loads((robot_source/'robot-calibration.json').read_text()),
                  'visual':json.loads((visual_source/'gripper-visual-calibration.json').read_text())}
    output.mkdir(parents=True,exist_ok=False)
    write(output/'manifest.json',{'scope':'explicit evaluator only; no mask or estimator changes','code':code,'versions':versions(),
        'source':str(source),'source_sha256':ARCHIVE_SHA256,'protocol_sha256':file_hash(PROTOCOL),
        'robot_calibration_sha256':CALIBRATION_SHA256,'visual_calibration_sha256':VISUAL_SHA256,
        'environment':{key:os.environ.get(key) for key in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')},
        'fixed_witnesses':WITNESSES,'cache_integrity_fields':list(CACHE_FIELDS),'opaque_full_MjData_byte_hash_claimed':False})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    stage='bootstrap';counts={s:{key:0 for key in ('env_controls','mj_step','mj_step1','mj_step2','mj_forward')} for s in ('bootstrap','prefix','diagnostic')}
    originals={key:getattr(mujoco,key) for key in ('mj_step','mj_step1','mj_step2','mj_forward')}
    for key,original in originals.items():
        def wrapper(*args,_key=key,_original=original,**kwargs):
            counts[stage][_key]+=1
            if stage=='diagnostic':raise RuntimeError('No stepping or forward calls after reconstruction')
            return _original(*args,**kwargs)
        setattr(mujoco,key,wrapper)
    _,ControlEnv,_,_=load_libero(config['libero_root'],config['config_dir']);original_env_step=ControlEnv.step
    def env_step(env,action):
        counts[stage]['env_controls']+=1
        if stage=='diagnostic':raise RuntimeError('No environment control after reconstruction')
        return original_env_step(env,action)
    ControlEnv.step=env_step
    world=None;state_checks=[];baseline={};snapshots={};native={};copy_checks=[]
    try:
        random.seed(1);np.random.seed(1)
        world=LiberoWorldBackend.from_task('top_drawer',seed=1,init_state_id=0,render=True,
            libero_root=config['libero_root'],config_dir=config['config_dir']).world
        sensor=LiberoRgbdSource(world)
        def check_state(label,expected):
            actual=world.env.sim.get_state().flatten();expected=np.asarray(expected)
            row={'label':label,'exact':bool(np.array_equal(actual,expected)),'max_absolute_error':float(np.max(np.abs(actual-expected)))}
            state_checks.append(row)
            if not row['exact']:raise RuntimeError('Exact archived state mismatch: '+label)
        check_state('initial',initial)
        static,mapping=export_robot_static(world.env,mujoco)
        if static!=calibrations['collision']:raise ValueError('Robot static calibration differs')
        def capture_baseline(step):
            before=cache_hashes(world.data);frame=sensor.capture();after=cache_hashes(world.data)
            comparison=compare_frames(original_frames[step],frame)
            baseline[step]={'original_comparison':comparison,'cache_unchanged_during_capture':before==after,
                            'context':context_record(world),'sim_time_s':float(world.data.time)}
            np.savez_compressed(output/f'native-before-{step}.npz',**{key:frame[key] for key in ('rgb','depth_m','intrinsics','camera_to_world')})
            write(output/f'baseline-before-{step}.json',baseline[step])
            if not all(comparison['array_exact'].values()) or before!=after:raise RuntimeError('Exact baseline RGB-D/cache gate failed at '+str(step))
            snapshot=mujoco.MjData(world.model);mujoco.mj_copyData(snapshot,world.model,world.data)
            copied=cache_hashes(snapshot)
            copy_checks.append({'stage':'snapshot','boundary':step,'source':after,'copy':copied,'exact':after==copied})
            if after!=copied:raise RuntimeError('Full-copy checked arrays differ')
            snapshots[step]=snapshot;native[step]=frame
        stage='prefix'
        for row in controls:
            check_state(f"{row['step']}/{row['control']}/before",row['state_before'])
            if row['step']==24 and row['control']==0:capture_baseline(24)
            world.obs,_,_,_=world.env.step(row['command'])
            check_state(f"{row['step']}/{row['control']}/after",row['state_after'])
        expected=next(r['data']['state_before'] for r in rows if r['kind']=='control_observation' and r['data']['step']==25 and r['data']['control']==0)
        check_state('25/0/before',expected);capture_baseline(25)
        if set(baseline)!={24,25}:raise RuntimeError('Both exact baseline gates required')
        write(output/'baseline-gate.json',{'passed':True,'state_checks':state_checks,'baseline':baseline,'counts_so_far':counts})
        # No physical continuation or forward refresh is permitted from here.
        stage='diagnostic';context=world.env.sim._render_context_offscreen
        requested=int(world.model.vis.quality.offsamples);world.model.vis.quality.offsamples=0
        context.con.free();del context.con;context._set_mujoco_context_and_buffers()
        zero_context=context_record(world)
        if zero_context['context_actual_offSamples']!=0:raise RuntimeError('Zero-sample control did not obtain zero actual samples')
        for step in (24,25):check_context_invariants(baseline[step]['context'],zero_context)
        results={}
        for step in (24,25):
            mujoco.mj_copyData(world.data,world.model,snapshots[step]);before=cache_hashes(world.data)
            original=cache_hashes(snapshots[step]);copy_checks.append({'stage':'restore','boundary':step,'source':original,'copy':before,'exact':before==original})
            if before!=original:raise RuntimeError('Copied-cache restore mismatch')
            zero=sensor.capture();after=cache_hashes(world.data)
            copy_checks.append({'stage':'zero_render','boundary':step,'source':before,'copy':after,'exact':before==after})
            if before!=after:raise RuntimeError('Render-only intervention changed checked cache/state arrays')
            after_context=context_record(world);check_context_invariants(baseline[step]['context'],after_context)
            if after_context['context_actual_offSamples']!=0:raise RuntimeError('Actual sampling changed during zero-sample capture')
            if not np.array_equal(zero['intrinsics'],native[step]['intrinsics']) or not np.array_equal(zero['camera_to_world'],native[step]['camera_to_world']):
                raise RuntimeError('Camera calibration changed in render intervention')
            np.savez_compressed(output/f'zero-msaa-before-{step}.npz',**{key:zero[key] for key in ('rgb','depth_m','intrinsics','camera_to_world')})
            packet=extract_own_positions(world.env.sim.get_state().flatten(),mapping['own_qpos_flat_indices'])
            results[step]={'native_vs_zero':compare_frames(native[step],zero),
                'witnesses':witness_comparison(native[step],zero,WITNESSES[step]),
                'cache_vs_own_qpos':compare_robot_cache(world,calibrations,packet,native[step]),
                'own_joint_packet':packet,'zero_context_after_capture':after_context,
                'cached_camera_position_world_m':world.data.cam_xpos[world.env.sim.model.camera_name2id('agentview')].tolist()}
        write(output/'copy-cache-checks.json',copy_checks)
        write(output/'measurements.json',{'baseline_gate_passed':True,'baseline':baseline,'zero_context':zero_context,
            'native_requested_samples':requested,'comparison_degenerate':all(b['context']['context_actual_offSamples']==0 for b in baseline.values()),
            'counts':counts,'states':results,'no_masks_or_policy':True,'fresh_FK_rendered':False})
        write(output/'output-seal.json',{'wall_time_unix_s':time.time(),'rgb_witness_inspection_started':False,
            'sha256':{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}})
        write(output/'artifacts.json',{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
        print(json.dumps({'status':'sealed','counts':counts,'baseline_exact':True,'output':str(output)}))
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'message':str(exc),'stage':stage,'counts':counts,
            'state_checks':state_checks,'baseline':baseline,'copy_checks':copy_checks,'no_retry':True})
        raise
    finally:
        ControlEnv.step=original_env_step
        if world is not None:world.env.close()
        for key,original in originals.items():setattr(mujoco,key,original)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
    p.add_argument('--robot-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/robot-geometry-observability-03')
    p.add_argument('--visual-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/gripper-visual-calibration-01')
    p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.robot_source,a.visual_source,a.output)
