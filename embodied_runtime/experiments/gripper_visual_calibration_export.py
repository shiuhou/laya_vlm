"""Static gripper-only visual calibration export; no recorded pose evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

import numpy as np

from .records import code_identity, file_hash, load_records, versions
from .robot_geometry_probe import descendants, export_robot_static, local_vertices, static_environment, write
from .sensor_gripper_proximity_probe import ARCHIVE_SHA256, CALIBRATION_SHA256


def run(source,robot_source,output):
    import mujoco
    source,robot_source,output = map(Path,(source,robot_source,output))
    code = code_identity()
    if code['dirty_status']:
        raise ValueError('Freeze exporter before static extraction')
    if file_hash(source/'episodes.jsonl') != ARCHIVE_SHA256 or file_hash(robot_source/'robot-calibration.json') != CALIBRATION_SHA256:
        raise ValueError('Frozen static construction sources differ')
    rows,errors=load_records(source/'episodes.jsonl')
    if errors:raise ValueError('Archive chain invalid')
    config=next(r['data']['resolved_config'] for r in rows if r['kind']=='run_start')
    output.mkdir(parents=True,exist_ok=False)
    write(output/'manifest.json',{'code':code,'versions':versions(),'scope':'static gripper visual calibration only',
        'archive_sha256':ARCHIVE_SHA256,'reference_collision_calibration_sha256':CALIBRATION_SHA256,
        'recorded_depth_or_joint_packets_read':False,'projection_or_distance_computed':False})
    originals={name:getattr(mujoco,name) for name in ('mj_step','mj_step1','mj_step2')}
    half_steps=[];blocked=[];env=None
    def forbidden(*args,**kwargs):
        blocked.append('forbidden stepping requested')
        raise RuntimeError('Integration and postconstruction stepping forbidden')
    def setup_half_step(model,data):
        before={'time':float(data.time),'qpos':data.qpos.copy().tolist(),'qvel':data.qvel.copy().tolist()}
        originals['mj_step1'](model,data)
        after={'time':float(data.time),'qpos':data.qpos.copy().tolist(),'qvel':data.qvel.copy().tolist()}
        half_steps.append({'before':before,'after':after,'unchanged':before==after})
        if before!=after:raise RuntimeError('Constructor half-step changed time/qpos/qvel')
    try:
        for name in originals:setattr(mujoco,name,forbidden)
        mujoco.mj_step1=setup_half_step
        random.seed(1);np.random.seed(1)
        env=static_environment(config)
        mujoco.mj_step1=forbidden
        if env.sim.data.time!=0 or blocked:raise RuntimeError('Static construction advanced physics')
        collision,mapping=export_robot_static(env,mujoco)
        reference=json.loads((robot_source/'robot-calibration.json').read_text())
        if collision!=reference:raise ValueError('Static robot body chain or collision geometry changed')
        model=env.sim.model._model;sim_model=env.sim.model;robot=env.robots[0]
        root=int(sim_model.body_name2id(robot.gripper.root_body))
        owned=set(descendants(model,root))
        ids=[i for i in range(model.ngeom) if int(model.geom_bodyid[i]) in owned and int(model.geom_group[i])==1]
        if len(ids)!=3:raise ValueError('Frozen XML expects exactly three gripper visual geometries')
        visual=[];audit=[]
        for i in ids:
            if model.geom_contype[i] or model.geom_conaffinity[i] or int(model.geom_type[i])!=int(mujoco.mjtGeom.mjGEOM_MESH):
                raise ValueError('Visual selection must be noncolliding mesh geometry')
            vertices,representation=local_vertices(model,i,mujoco)
            body=int(model.geom_bodyid[i]);name=sim_model.geom_id2name(i)
            visual.append({'name':name,'body':sim_model.body_id2name(body),
                'position_body_m':model.geom_pos[i].tolist(),'quaternion_body_wxyz':model.geom_quat[i].tolist(),
                'vertices_local_m':vertices.tolist(),'shape_representation':representation})
            mesh=int(model.geom_dataid[i])
            audit.append({'name':name,'robot_body':sim_model.body_id2name(body),'compiled_vertex_count':len(vertices),
                'compiled_mesh_face_count':int(model.mesh_facenum[mesh]),'geom_group':int(model.geom_group[i]),
                'contype':int(model.geom_contype[i]),'conaffinity':int(model.geom_conaffinity[i]),
                'geom_rgba':model.geom_rgba[i].tolist()})
        calibration={**collision,'geometries':visual}
        write(output/'gripper-visual-calibration.json',calibration)
        write(output/'constructor-audit-evaluator-only.json',{'half_steps':half_steps,'passed_to_estimator':False})
        write(output/'selection.json',{'rule':'gripper-root descendant bodies, geom_group=1, require noncolliding meshes',
            'gripper_root':robot.gripper.root_body,'body_chain_and_collision_calibration_exact_match':True,
            'geometries':audit,'visual_geometry_count':len(visual),
            'constructor_mj_step1_calls':len(half_steps),'constructor_time_qpos_qvel_unchanged':all(r['unchanged'] for r in half_steps),
            'sim_time_s':float(env.sim.data.time),'dynamic_controls_or_integration':0,'rendering':False,
            'blocked_step_calls':blocked,'visual_calibration_sha256':file_hash(output/'gripper-visual-calibration.json')})
        write(output/'artifacts.json',{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
        print(json.dumps(json.loads((output/'selection.json').read_text()),indent=2))
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'message':str(exc),'constructor_mj_step1_calls':len(half_steps),'blocked_step_calls':blocked})
        raise
    finally:
        if env is not None:env.close()
        for name,value in originals.items():setattr(mujoco,name,value)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
    p.add_argument('--robot-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/robot-geometry-observability-03')
    p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.robot_source,a.output)
