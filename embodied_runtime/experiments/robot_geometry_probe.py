"""Frozen offline robot-only FK correctness and state-dependency probe."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

from .records import code_identity, file_hash, jsonable, load_records, repository_identity, versions
from .robot_only_geometry import VERSION, extract_own_positions

PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/robot_geometry_probe_protocol.md'
SOURCE_SHA256 = 'e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf'
TOLERANCE = 1e-10


def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value),stream,indent=2,allow_nan=False)
        stream.write('\n')


def selected_states(rows):
    def unique(kind,predicate=lambda row:True):
        found = [r for r in rows if r['kind'] == kind and predicate(r['data'])]
        if len(found) != 1:
            raise ValueError('Registered source record missing or ambiguous')
        return found[0]
    initial = unique('environment')
    first = unique('control_observation',lambda r:r['step'] == 25 and r['control'] == 0)
    last = unique('control_observation',lambda r:r['step'] == 25 and r['control'] == 7)
    return [(label,np.asarray(record['data'][key],dtype=float),
             {'record_id':record['record_id'],'seq':record['seq'],'kind':record['kind'],'state_field':key})
        for label,record,key in [('initial',initial,'sim_state'),('pre_action25',first,'state_before'),
                                 ('first_contact_sample',first,'state_after'),('endpoint',last,'state_after')]]


def descendants(model,root):
    def belongs(body):
        while body:
            if body == root:
                return True
            body = int(model.body_parentid[body])
        return False
    return [i for i in range(1,model.nbody) if belongs(i)]


def local_vertices(model,geom,mujoco):
    kind = int(model.geom_type[geom])
    if kind == int(mujoco.mjtGeom.mjGEOM_MESH):
        mesh = int(model.geom_dataid[geom])
        start,count = int(model.mesh_vertadr[mesh]),int(model.mesh_vertnum[mesh])
        return np.asarray(model.mesh_vert[start:start+count],dtype=float).copy(),'compiled_robot_mesh_vertices'
    if kind == int(mujoco.mjtGeom.mjGEOM_BOX):
        return np.asarray(list(product((-1.,1.),repeat=3)))*model.geom_size[geom],'exact_robot_box_corners'
    raise ValueError('Registered gripper probe supports mesh and box collision geometry only')


def export_robot_static(env,mujoco):
    model,robot = env.sim.model._model,env.robots[0]
    sim_model = env.sim.model
    root = int(sim_model.body_name2id(robot.robot_model.root_body))
    if int(model.body_parentid[root]) != 0:
        raise ValueError('This probe requires a calibrated fixed base directly under world')
    body_ids = descendants(model,root)
    joint_names = list(robot.robot_joints)+list(robot.gripper_joints)
    joint_ids = [int(sim_model.joint_name2id(name)) for name in joint_names]
    exported_joint_ids = [j for b in body_ids for j in range(int(model.body_jntadr[b]),int(model.body_jntadr[b]+model.body_jntnum[b]))]
    if sorted(joint_ids) != sorted(exported_joint_ids) or len(joint_ids) != 9:
        raise ValueError('Exactly the registered seven arm and two finger joints must form the robot subtree')
    bodies = []
    for b in body_ids:
        name = sim_model.body_id2name(b)
        joints = []
        for j in range(int(model.body_jntadr[b]),int(model.body_jntadr[b]+model.body_jntnum[b])):
            kind = int(model.jnt_type[j])
            if kind not in (int(mujoco.mjtJoint.mjJNT_HINGE),int(mujoco.mjtJoint.mjJNT_SLIDE)):
                raise ValueError('Unsupported own joint type; no approximation')
            joints.append({'name':sim_model.joint_id2name(j),
                'kind':'hinge' if kind == int(mujoco.mjtJoint.mjJNT_HINGE) else 'slide',
                'anchor_body_m':model.jnt_pos[j].tolist(),'axis_body':model.jnt_axis[j].tolist(),
                'qpos_reference':float(model.qpos0[model.jnt_qposadr[j]])})
        parent = int(model.body_parentid[b])
        bodies.append({'name':name,'parent':None if b == root else sim_model.body_id2name(parent),
            'position_parent_m':model.body_pos[b].tolist(),'quaternion_parent_wxyz':model.body_quat[b].tolist(),
            'joints':joints})
    gripper_root = int(sim_model.body_name2id(robot.gripper.root_body))
    gripper_bodies = set(descendants(model,gripper_root))
    geom_ids = [i for i in range(model.ngeom) if int(model.geom_bodyid[i]) in gripper_bodies and
                (model.geom_contype[i] or model.geom_conaffinity[i])]
    force_sensor = int(sim_model.sensor_name2id(robot.gripper.important_sensors['force_ee']))
    site_ids = [int(robot.eef_site_id),int(model.sensor_objid[force_sensor])]
    site_ids = sorted(set(site_ids))
    def local_pose(i,family):
        b = int(getattr(model,family+'_bodyid')[i])
        if b not in body_ids:
            raise ValueError('Non-robot site or geometry rejected')
        return {'name':getattr(sim_model,family+'_id2name')(i),'body':sim_model.body_id2name(b),
                'position_body_m':getattr(model,family+'_pos')[i].tolist(),
                'quaternion_body_wxyz':getattr(model,family+'_quat')[i].tolist()}
    geometries = []
    for g in geom_ids:
        vertices,representation = local_vertices(model,g,mujoco)
        geometries.append({**local_pose(g,'geom'),'vertices_local_m':vertices.tolist(),
                           'shape_representation':representation})
    calibration = {'version':VERSION,'bodies':bodies,
        'sites':[local_pose(i,'site') for i in site_ids], 'geometries':geometries}
    mapping = {'nq':int(model.nq),'nv':int(model.nv),'na':int(model.na),
        'flattened_state_layout':'time, qpos[nq], qvel[nv]; na=0',
        'own_qpos_flat_indices':{sim_model.joint_id2name(j):1+int(model.jnt_qposadr[j]) for j in joint_ids},
        'own_qvel_flat_indices':{sim_model.joint_id2name(j):1+int(model.nq)+int(model.jnt_dofadr[j]) for j in joint_ids},
        'root_body_name':sim_model.body_id2name(root),'root_position_world_m':model.body_pos[root].tolist(),
        'root_quaternion_world_wxyz':model.body_quat[root].tolist(),
        'base_calibration_source':'static robot root transform from standard task construction; assumed known fixed base',
        'tcp_site_name':sim_model.site_id2name(robot.eef_site_id),
        'body_ids_evaluator_only':body_ids,'site_ids_evaluator_only':site_ids,'geom_ids_evaluator_only':geom_ids,
        'robot_geom_names':[sim_model.geom_id2name(g) for g in geom_ids],
        'important_gripper_geoms':robot.gripper.important_geoms}
    if model.na != 0:
        raise ValueError('Archived state decoder requires na=0')
    return calibration,mapping


def static_environment(config):
    from jev_libero.environment import load_libero
    from jev_libero.config import load_task
    benchmark,ControlEnv,assets,_ = load_libero(config['libero_root'],config['config_dir'])
    task_config = load_task('top_drawer')
    suite = benchmark.get_benchmark_dict()[task_config['binding']['suite']]()
    task = next(suite.get_task(i) for i in range(suite.n_tasks) if suite.get_task(i).name == task_config['binding']['task'])
    return ControlEnv(bddl_file_name=str(assets/'bddl_files'/task.problem_folder/task.bddl_file),
        use_camera_obs=False,has_renderer=False,has_offscreen_renderer=False,camera_heights=384,camera_widths=384)


def run(source,output):
    import mujoco
    source,output = Path(source),Path(output)
    if file_hash(source/'episodes.jsonl') != SOURCE_SHA256:
        raise ValueError('Frozen physical source differs')
    rows,errors = load_records(source/'episodes.jsonl')
    if errors:
        raise ValueError('Source evidence chain invalid')
    start = next(r['data'] for r in rows if r['kind'] == 'run_start')
    states = selected_states(rows)
    output.mkdir(parents=True,exist_ok=False)
    write(output/'manifest.json',{'scope':'offline own-body kinematics; no dynamic simulation or policy',
        'code':code_identity(),'source':str(source),'source_sha256':SOURCE_SHA256,
        'protocol_sha256':file_hash(PROTOCOL),'versions':versions(),'tolerance_m_and_matrix_element':TOLERANCE,
        'selected_state_labels':[name for name,_,_ in states],
        'encoder_provenance':'retrospective own-joint extraction from archived simulator state; not physical sensor measurements'})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    blocked_calls = []
    originals = {}
    def forbidden(*args,**kwargs):
        blocked_calls.append('physics stepping requested')
        raise RuntimeError('No physics stepping permitted in this offline probe')
    for name in ('mj_step','mj_step1','mj_step2'):
        originals[name] = getattr(mujoco,name)
        setattr(mujoco,name,forbidden)
    env = None
    try:
        random.seed(1);np.random.seed(1)
        env = static_environment(start['resolved_config'])
        if env.sim.data.time != 0. or blocked_calls:
            raise RuntimeError('Static construction advanced physics')
        model = env.sim.model._model
        calibration,mapping = export_robot_static(env,mujoco)
        write(output/'robot-calibration.json',calibration)
        write(output/'archive-admission-map.json',mapping)
        import jev_libero.world
        import libero
        from robosuite.utils import binding_utils
        write(output/'static-setup.json',{'sim_time_s':float(env.sim.data.time),'physics_step_calls':blocked_calls,
            'rendering':False,'world_class_used':False,'reset_or_set_init_state_called':False,
            'construction_note':'ControlEnv constructor may initialize/forward caches; no dynamics stepping is allowed.',
            'environment_repositories':{'jev':repository_identity(Path(jev_libero.world.__file__).parent),
                'libero':repository_identity(Path(libero.__file__).parent)},
            'flattened_state_decoder_source_sha256':file_hash(binding_utils.__file__),
            'full_model_dimensions_evaluator_only':{'nbody':int(model.nbody),'ngeom':int(model.ngeom),'nq':int(model.nq),'nv':int(model.nv)},
            'exported_robot_counts':{key:len(calibration[key]) for key in ('bodies','sites','geometries')}})
        original_packets,metadata,poison_packets = {},[],{}
        allowed = set(mapping['own_qpos_flat_indices'].values()) | set(mapping['own_qvel_flat_indices'].values()) | {0}
        for name,state,record in states:
            if len(state) != 1+model.nq+model.nv:
                raise ValueError('Archived state length disagrees with static decoder')
            packet = extract_own_positions(state,mapping['own_qpos_flat_indices'])
            original_packets[name] = packet
            metadata.append({'label':name,'read_sim_time_s':float(state[0]),'archive_record':record,
                             'own_qpos_count':len(packet),'excluded_qpos_count':int(model.nq)-len(packet)})
            for variant in ('nan_nonrobot_state','finite_nonrobot_state'):
                poisoned = state.copy()
                indices = np.array([i for i in range(len(state)) if i not in allowed])
                poisoned[indices] = np.nan if variant.startswith('nan') else 1234.5+np.arange(len(indices))*.25
                poison_packets[name+'/'+variant] = extract_own_positions(poisoned,mapping['own_qpos_flat_indices'])
        hinge = next(j['name'] for b in calibration['bodies'] for j in b['joints'] if j['kind'] == 'hinge')
        slide = next(j['name'] for b in calibration['bodies'] for j in b['joints'] if j['kind'] == 'slide')
        positive = {}
        for name,joint,delta in [('own_hinge_plus_0.01rad',hinge,.01),('own_slide_plus_0.001m',slide,.001)]:
            positive[name] = dict(original_packets['pre_action25'])
            positive[name][joint] += delta
        write(output/'encoder-packets.json',{'provenance':'simulator-state-extracted own encoders only',
              'metadata':metadata,'original':original_packets,'nonrobot_state_poison_extracted':poison_packets,
              'positive_own_joint_controls':positive})
        request = {'calibration':calibration,'joint_packets':{**original_packets,**poison_packets,**positive}}
        write(output/'estimator-input.json',request)
        result = subprocess.run([sys.executable,'-m','embodied_runtime.experiments.robot_only_geometry'],
            input=json.dumps(request,allow_nan=False),text=True,capture_output=True,check=True)
        estimates = json.loads(result.stdout)
        write(output/'sensor-estimates.json',estimates)
        write(output/'sensor-estimates-seal.json',{'sha256':file_hash(output/'sensor-estimates.json'),
            'input_sha256':file_hash(output/'estimator-input.json'),'wall_time_unix_s':time.time(),
            'estimator_process_inputs':'stdin robot calibration plus own joint packets only',
            'evaluator_transforms_computed_yet':False})
        # Evaluator phase begins only after the standalone estimates are sealed.
        evaluator = {}
        for name,state,_ in states:
            data = mujoco.MjData(model)
            data.time = state[0]
            data.qpos[:] = state[1:1+model.nq]
            data.qvel[:] = state[1+model.nq:]
            mujoco.mj_kinematics(model,data)
            geometry = {}
            for g in mapping['geom_ids_evaluator_only']:
                vertices,representation = local_vertices(model,g,mujoco)
                world = vertices@data.geom_xmat[g].reshape(3,3).T+data.geom_xpos[g]
                geometry[env.sim.model.geom_id2name(g)] = {'position_world_m':data.geom_xpos[g].tolist(),
                    'rotation_world':data.geom_xmat[g].reshape(3,3).tolist(),'vertices_world_m':world.tolist(),
                    'aabb_world_m':[world.min(axis=0).tolist(),world.max(axis=0).tolist()],
                    'shape_representation':representation}
            evaluator[name] = {'bodies':{env.sim.model.body_id2name(b):{
                'position_world_m':data.xpos[b].tolist(),'rotation_world':data.xmat[b].reshape(3,3).tolist()}
                for b in mapping['body_ids_evaluator_only']},'sites':{env.sim.model.site_id2name(s):{
                'position_world_m':data.site_xpos[s].tolist(),'rotation_world':data.site_xmat[s].reshape(3,3).tolist()}
                for s in mapping['site_ids_evaluator_only']},'geometries':geometry}
        write(output/'evaluator-recomputed-poses.json',{'privileged':True,'method':'fresh MjData qpos + mj_kinematics only',
            'meaning':'same-qpos recomputed transforms, not original cached contact-time poses','states':evaluator})
        comparisons = []
        for name,truth in evaluator.items():
            for family in ('bodies','sites','geometries'):
                if set(estimates[name][family]) != set(truth[family]):
                    raise ValueError('Estimator/evaluator item sets differ')
                for item in truth[family]:
                    keys = ['position_world_m','rotation_world']+(['vertices_world_m','aabb_world_m'] if family == 'geometries' else [])
                    comparisons.append({'state':name,'family':family,'name':item,
                        'max_abs_error':{key:float(np.max(np.abs(np.asarray(estimates[name][family][item][key])-
                                          truth[family][item][key]))) for key in keys}})
        poison = {name:estimates[name] == estimates[name.split('/')[0]] for name in poison_packets}
        sensitivity = {name:max(float(np.max(np.abs(np.asarray(estimates[name]['geometries'][g]['vertices_world_m'])-
                       estimates['pre_action25']['geometries'][g]['vertices_world_m']))) for g in estimates[name]['geometries'])
                       for name in positive}
        passed = (all(error <= TOLERANCE for row in comparisons for error in row['max_abs_error'].values()) and
                  all(poison.values()) and all(error > 1e-8 for error in sensitivity.values()))
        # Archive robot observations are descriptive timing comparators only.
        environment = next(r['data'] for r in rows if r['kind'] == 'environment')
        actions = [r['data'] for r in rows if r['kind'] == 'action']
        observed = {'initial':environment['initial_state']['tcp_xyz'],
            'pre_action25':actions[25]['result']['before'],'endpoint':actions[25]['result']['after']}
        tcp = mapping['tcp_site_name']
        cached = {name:(np.asarray(estimates[name]['sites'][tcp]['position_world_m'])-value).tolist() for name,value in observed.items()}
        summary = {'passed':passed,'source_sha256':SOURCE_SHA256,'state_count':len(states),
            'own_joint_count':len(mapping['own_qpos_flat_indices']),
            'tolerance':TOLERANCE,'comparison_rows':comparisons,
            'max_position_error_m':max(r['max_abs_error']['position_world_m'] for r in comparisons),
            'max_rotation_matrix_element_error':max(r['max_abs_error']['rotation_world'] for r in comparisons),
            'max_geometry_vertex_error_m':max(r['max_abs_error'].get('vertices_world_m',0) for r in comparisons),
            'max_geometry_aabb_error_m':max(r['max_abs_error'].get('aabb_world_m',0) for r in comparisons),
            'poison_nonrobot_state_output_bitwise_equal':poison,'positive_own_joint_max_geometry_change_m':sensitivity,
            'recomputed_tcp_minus_archived_returned_tcp_m':cached,
            'returned_tcp_sample_times_unknown':True,'base_calibration':{k:v for k,v in mapping.items() if k.startswith('root_') or k.startswith('base_')},
            'physics_controls_executed':0,'physics_step_calls':blocked_calls,
            'no_scene_geometry_in_estimator':True,'no_policy_contact_or_safety_claim':True}
        write(output/'summary.json',summary)
        write(output/'artifacts.json',{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
        print(json.dumps({key:summary[key] for key in ('passed','state_count','own_joint_count','max_position_error_m',
            'max_rotation_matrix_element_error','max_geometry_vertex_error_m','max_geometry_aabb_error_m',
            'poison_nonrobot_state_output_bitwise_equal','positive_own_joint_max_geometry_change_m')},indent=2))
        if not passed:
            raise RuntimeError('Frozen correctness/dependency criteria failed')
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'message':str(exc),
            'physics_step_calls':blocked_calls,'no_physical_retry':True})
        raise
    finally:
        if env is not None:
            env.close()
        for name,original in originals.items():
            setattr(mujoco,name,original)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    run(args.source,args.output)
