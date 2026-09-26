"""One exact canonical Task1 control replay, with passive native-stage measurements."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np

from ..runtime_core import _sha256_json
from . import native_substep_observability as native
from .records import RunRecorder, code_identity, file_hash, repository_identity, package_directory, versions

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path('/home/junhongli/projects/laya-embodied-runtime/runs/privileged-reference/local-objective-task-adapter-episode-01')
SOURCE_HASHES={'episodes.jsonl':'9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2',
 'manifest.json':'a19ddc51c95e094be6d4dbac3fbb1271902de30ede8f630d432c8e40f9ec4b2a',
 'reference-evidence.json':'063ad9585ca4bd5c9c5e7dbedff39efe522d51261a5a5e2e8246a94653cba008'}
PROTOCOL=ROOT/'docs/research/task1_native_contact_attribution_protocol.md'
CLASSES=('designated_only','historical_non_designated_only','simultaneous','neither_historical_relation')
INTERVAL_CLASSES=(*CLASSES,'ambiguous_stage_difference')
eq=native.require_equal


def stream_records(path):
    """Bounded-memory strict form of the existing record integrity verification."""
    previous=None
    with Path(path).open('rb') as stream:
        for i,line in enumerate(stream):
            if not line.endswith(b'\n'):
                raise ValueError('incomplete trailing record')
            row=json.loads(line)
            if (row['seq']!=i or row['previous_record_id']!=previous or
                    row['record_id']!=_sha256_json({k:v for k,v in row.items() if k!='record_id'})):
                raise ValueError(f'record integrity failure at {i}')
            previous=row['record_id']
            yield row


def load_source():
    for name,digest in SOURCE_HASHES.items():eq(file_hash(SOURCE/name),digest,'canonical source '+name)
    rows=list(stream_records(SOURCE/'episodes.jsonl'))
    if native.data(rows,'failure'):raise ValueError('source failure')
    evidence=json.loads((SOURCE/'reference-evidence.json').read_text())
    eq(evidence['raw_sha256'],SOURCE_HASHES['episodes.jsonl'],'evidence source')
    eq(evidence['actual_success'],True,'source success')
    trajectories=native.data(rows,'demo_trajectory');outcomes=native.data(rows,'reference_outcome')
    actions=native.data(rows,'action');eq(len(trajectories),122,'122 artifacts');eq(len(evidence['trace']),122,'122 primitives')
    primitives=[];previous=None;total=0
    for i,(artifact,outcome,action,trace) in enumerate(zip(trajectories,outcomes,actions,evidence['trace'])):
        eq(artifact['step'],i,'artifact index');eq(outcome['step'],i,'outcome index');eq(action['step'],i,'action index')
        eq(artifact['artifact'],f'trajectory/action-{i:03d}.npz','canonical artifact path')
        eq(file_hash(SOURCE/artifact['artifact']),artifact['sha256'],'archive artifact hash')
        eq(trace['outcome'],outcome,'evidence outcome')
        with np.load(SOURCE/artifact['artifact'],allow_pickle=False) as saved:
            commands=saved['commands'].tolist();states=saved['states_before'].tolist();after=saved['state_after'].tolist()
        eq(len(commands),2 if i==121 else 8,'native archived control count')
        eq(len(states),len(commands),'state count');eq(commands,action['execution']['low_level_commands'],'original commands')
        eq(len(commands),outcome['controls'],'outcome controls')
        if previous is not None:eq(states[0],previous,'primitive state chain')
        primitives.append({'step':i,'action':outcome['action'],'artifact':artifact,
            'commands':commands,'states_before':states,'state_after':after,'outcome':outcome,'control_offset':total})
        total+=len(commands);previous=after
    eq(total,970,'canonical970controls')
    environment=native.one(rows,'environment');eq(primitives[0]['states_before'][0],environment['sim_state'],'initial archive state')
    return {'rows':rows,'primitives':primitives,'environment':environment,
            'manifest':json.loads((SOURCE/'manifest.json').read_text()),
            'config':native.one(rows,'run_start')['resolved_config']}


def frozen_inputs(source):
    from .collect_pairs import initial_state_inventory
    from jev_libero.config import load_task, task_path
    import jev_libero.world
    code=code_identity()
    if code['dirty_status']:raise ValueError('clean frozen code required')
    eq(versions(),source['manifest']['versions'],'source software versions')
    config=source['config'];inventory=initial_state_inventory('top_drawer',config['libero_root'],config['config_dir'])
    import libero
    identity={'task':'top_drawer','seed':1,'init_state_id':0,'binding':inventory['binding'],'benchmark_state_id':inventory['state_ids'][0]}
    eq(identity,native.one(source['rows'],'reference_initial_identity'),'benchmark/reset identity')
    task=load_task('top_drawer');eq(task['contact']['min_normal_force_N'],1.,'strict original1Nthreshold')
    eq(file_hash(task_path('top_drawer')),'006395162b0ccafb5a8a632d56d6fdedf26590c788fb5ac095766c54f09dfe50','current measurement TaskSpec')
    historical_bytes=subprocess.check_output(['git','-C',str(package_directory(jev_libero.world)),
        'show','d67cb50:src/jev_libero/tasks/top_drawer.json'])
    historical_hash=hashlib.sha256(historical_bytes).hexdigest()
    eq(historical_hash,'fb5cd2c73b27ff6ab244667a215dc0a16528eb9a52e25f72e846910dd2d14497','historical semantic TaskSpec')
    historical=json.loads(historical_bytes)
    for key,value in historical['measurements'].items():eq(task['measurements'][key],value,'historical measurement '+key)
    for key in ('valid_handle_contact','valid_handle_grasp','non_designated_robot_contact'):
        eq(task['features'][key],historical['features'][key],'historical contact boolean '+key)
    env={k:os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')}
    eq(env,{'CUDA_VISIBLE_DEVICES':'6','MUJOCO_GL':'egl','MUJOCO_EGL_DEVICE_ID':'6'},'GPU6 environment')
    stepping=native.stepping_identity()
    import robosuite.controllers.base_controller
    import inspect
    path=inspect.getfile(robosuite.controllers.base_controller);stepping[path]=file_hash(path)
    return {'source':str(SOURCE),'source_hashes':SOURCE_HASHES,'source_manifest':source['manifest'],
        'artifacts':[p['artifact'] for p in source['primitives']],
        'primitive_control_counts':[len(p['commands']) for p in source['primitives']],
        'protocol_sha256':file_hash(PROTOCOL),'code':code,'versions':versions(),
        'repositories':{'jev':repository_identity(package_directory(jev_libero.world)),
                        'libero':repository_identity(package_directory(libero))},
        'initial_identity':identity,'task_config':task,'task_config_sha256':file_hash(task_path('top_drawer')),
        'historical_semantic_provenance':{'jev_commit':'d67cb50','task_config_sha256':historical_hash,
            'all_original_measurements_equal':True,'designated_bilateral_nondesignated_expressions_equal':True},
        'stepping_sources':stepping,'execution_environment':env,
        'attribution_classes':list(CLASSES),'interval_classes':list(INTERVAL_CLASSES),
        'threshold_rule':'strict normal_force_N > 1','model_calls':0,'policy_execution':False,'retries':0}


def geometry_metadata(world):
    from jev_libero.measurements import Measurements
    m=Measurements(world);cfg=world.config['measurements']
    selectors={'robot':{'group':'robot'},'arm':{'group':'arm'},'drawer':cfg['all_robot_drawer_contacts']['right'],
        'gripper':{'group':'gripper'},'left_pad':cfg['left_fingerpad_handle_contacts']['left'],
        'right_pad':cfg['right_fingerpad_handle_contacts']['left'],
        'handle':cfg['left_fingerpad_handle_contacts']['right'],'explicit_nonhandle':cfg['gripper_nonhandle_contacts']['right']}
    return {key:{'ids':sorted(m.ids(selector)),'names':[world.env.sim.model.geom_id2name(i) for i in sorted(m.ids(selector))],
        'selector':selector} for key,selector in selectors.items()}


def sensor_metadata(world):
    sensors=[]
    for key,unit,expected_type in (('force_ee','N',world.mujoco.mjtSensor.mjSENS_FORCE),
                                   ('torque_ee','Nm',world.mujoco.mjtSensor.mjSENS_TORQUE)):
        name=world.env.robots[0].gripper.important_sensors[key]
        index=world.env.sim.model.sensor_name2id(name)
        model=world.model;site=int(model.sensor_objid[index])
        eq(int(model.sensor_objtype[index]),int(world.mujoco.mjtObj.mjOBJ_SITE),'native wrist sensor site')
        eq(int(model.sensor_dim[index]),3,'three-axis wrist sensor')
        eq(int(model.sensor_type[index]),int(expected_type),'native wrist sensor physical type')
        body=int(model.site_bodyid[site])
        sensors.append({'key':key,'name':name,'sensor_id':int(index),'address':int(model.sensor_adr[index]),
            'dimension':int(model.sensor_dim[index]),'type':int(model.sensor_type[index]),
            'object_type':int(model.sensor_objtype[index]),'site_id':site,'site_name':world.env.sim.model.site_id2name(site),
            'body_id':body,'body_name':world.env.sim.model.body_id2name(body),
            'site_position_in_body_m':np.asarray(model.site_pos[site]).tolist(),
            'site_quaternion_in_body_wxyz':np.asarray(model.site_quat[site]).tolist(),
            'needstage':int(model.sensor_needstage[index]),'unit':unit,'frame':'local native sensor site',
            'sample_time_s':None,'interpretation':'uncalibrated simulated hardware-sensor analogue; excluded from contact attribution'})
    return sensors


def wrist_buffers(world,metadata):
    before=native.integration_fingerprint(world)
    result={}
    for sensor in metadata:
        address,dim,site=sensor['address'],sensor['dimension'],sensor['site_id']
        result[sensor['key']]={'values':np.asarray(world.data.sensordata[address:address+dim]).tolist(),
            'cached_site_position_world_m':np.asarray(world.data.site_xpos[site]).tolist(),
            'cached_site_rotation_world':np.asarray(world.data.site_xmat[site]).reshape(3,3).tolist(),
            'buffer_read_sim_time_s':float(world.data.time),'actual_sample_time_s':None}
    eq(native.integration_fingerprint(world),before,'passive wrist snapshot neutrality')
    return result


@contextmanager
def with_wrist_snapshots(metadata):
    original=native.snapshot
    def augmented(world,*args,**kwargs):
        result=original(world,*args,**kwargs)
        result['wrist_sensor_buffers']=wrist_buffers(world,metadata)
        return result
    native.snapshot=augmented
    try:yield
    finally:native.snapshot=original


def relation_class(designated,non_designated):
    if designated and non_designated:return 'simultaneous'
    if designated:return 'designated_only'
    if non_designated:return 'historical_non_designated_only'
    return 'neither_historical_relation'


def classify_contacts(contacts,geometry):
    ids={key:set(value['ids']) for key,value in geometry.items()}
    def pair(contact,left,right):
        a,b=contact['geom_ids'];return (a in ids[left] and b in ids[right]) or (b in ids[left] and a in ids[right])
    strong=[c for c in contacts if c['normal_force_N']>1.]
    left=any(pair(c,'left_pad','handle') for c in strong)
    right=any(pair(c,'right_pad','handle') for c in strong);designated=left or right
    arm=any(pair(c,'arm','drawer') for c in strong)
    nonhandle=any(pair(c,'gripper','explicit_nonhandle') for c in strong)
    gripper_handle=any(pair(c,'gripper','handle') for c in strong)
    historical=arm or nonhandle or (gripper_handle and not designated)
    robot_drawer=[c for c in strong if pair(c,'robot','drawer')]
    complement=[c for c in robot_drawer if not (pair(c,'left_pad','handle') or pair(c,'right_pad','handle'))]
    other=[c for c in strong if sum(g in ids['robot'] for g in c['geom_ids'])==1 and not pair(c,'robot','drawer')]
    self_contact=[c for c in strong if all(g in ids['robot'] for g in c['geom_ids'])]
    return {'class':relation_class(designated,historical),'designated':designated,'bilateral':left and right,
        'historical_non_designated':historical,'raw_pairwise_non_designated_above_1N':len(complement),
        'robot_other_scene_above_1N':len(other),'robot_self_contact_above_1N':len(self_contact),'robot_drawer_above_1N':len(robot_drawer),
        'raw_robot_drawer_rows':sum(pair(c,'robot','drawer') for c in contacts),
        'raw_designated_rows':sum(pair(c,'left_pad','handle') or pair(c,'right_pad','handle') for c in contacts)}


def interval_class(before,after):
    return before if before==after else 'ambiguous_stage_difference'


def table(classes):
    return {c:{'intervals':0,'positive_change_mm':0.,'negative_change_mm':0.,'net_change_mm':0.} for c in classes}


def accumulate(totals,label,delta):
    values=totals[label];values['intervals']+=1;values['positive_change_mm']+=max(delta,0.)
    values['negative_change_mm']+=min(delta,0.);values['net_change_mm']+=delta


def replay_control(world,command,before,after,recorder,step,index,global_index):
    actual=world.env.sim.get_state().flatten().tolist()
    recorder.record('control_started',{'step':step,'control':index,'global_control':global_index,
        'command':command,'state_before':actual})
    eq(actual,before,f'primitive{step}control{index}before')
    world.obs,_,_,_=world.env.step(command)
    actual_after=world.env.sim.get_state().flatten().tolist()
    recorder.record('control_state_observed',{'step':step,'control':index,'global_control':global_index,'state_after':actual_after})
    eq(actual_after,after,f'primitive{step}control{index}after')


def run(args):
    recorder=RunRecorder(args.output,{'mode':args.mode,'preflight':args.preflight,'source':str(SOURCE),
        'one_canonical_replay':True,'model_calls':0,'policy_calls':0,'retries':0},
        {'run_id':Path(args.output).name,'code':code_identity(),'versions':versions()})
    backend=None;completed_controls=0;completed_primitives=0;step=None
    try:
        source=load_source();frozen=frozen_inputs(source)
        recorder.record('frozen_inputs',frozen);(recorder.output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        if args.mode=='preflight':
            recorder.record('termination',{'reason':'preflight_complete','executed_controls':0});return
        prior=list(stream_records(Path(args.preflight)/'episodes.jsonl'))
        eq(native.one(prior,'frozen_inputs'),frozen,'frozen preflight')
        eq(native.one(prior,'termination'),{'reason':'preflight_complete','executed_controls':0},'preflight termination')
        from .privileged_task import TOP_DRAWER_ADAPTER
        cfg=source['config'];backend=TOP_DRAWER_ADAPTER.make_backend(SimpleNamespace(seed=1,init_state_id=0,
            libero_root=cfg['libero_root'],config_dir=cfg['config_dir']),render=False)
        world=backend.world
        eq(world.config,frozen['task_config'],'current measurement TaskSpec')
        eq(world.env.sim.get_state().flatten().tolist(),source['environment']['sim_state'],'exact initial state')
        eq(backend.execution_state(),source['environment']['initial_state'],'initial execution state')
        geometry=geometry_metadata(world);sensors=sensor_metadata(world)
        initial=world.features()
        environment={'state':world.env.sim.get_state().flatten().tolist(),'geometry':geometry,'sensors':sensors,
            'initial_features':initial,'model_timestep_s':float(world.model.opt.timestep),'control_timestep_s':float(world.env.env.control_timestep),
            'integrator':int(world.model.opt.integrator),'drawer_qpos_address':int(world.model.jnt_qposadr[world.jid]),
            'drawer_dof_address':int(world.model.jnt_dofadr[world.jid])}
        eq((environment['model_timestep_s'],environment['control_timestep_s'],environment['integrator']),(.002,.05,0),'native stepping path')
        recorder.record('environment',environment)
        with with_wrist_snapshots(sensors):
            for primitive in source['primitives']:
                step=primitive['step'];tag=f'task1-primitive-{step:03d}';tracking={'control':None}
                before=world.features();eq(before['qpos_m'],primitive['outcome']['before']['qpos_m'],'primitive before qpos')
                eq(bool(world.env.check_success()),primitive['outcome']['before']['success'],'primitive before official success')
                recorder.record('primitive_started',{'step':step,'action':primitive['action'],'controls':len(primitive['commands']),
                    'source_artifact':primitive['artifact'],'state':world.env.sim.get_state().flatten().tolist()})
                with native.observe_integrators(world,recorder,tag,tracking,
                        tuple(set(geometry[k]['ids']) for k in ('robot','drawer','handle'))) as (calls,forwards):
                    for i,command in enumerate(primitive['commands']):
                        before_features=world.features();tracking['control']=i
                        after_state=primitive['states_before'][i+1] if i+1<len(primitive['commands']) else primitive['state_after']
                        replay_control(world,command,primitive['states_before'][i],after_state,recorder,step,i,completed_controls)
                        tracking['control']=None
                        selected=calls[i*25:(i+1)*25]
                        if len(selected)!=25 or any(c['function']!='mj_step' for c in selected):raise ValueError('native path/count mismatch')
                        after_features=world.features()
                        # Historical endpoint semantics are recorded from the native measurement layer.
                        recorder.record('control_completed',{'step':step,'control':i,'global_control':completed_controls,
                            'drawer_before_m':before_features['qpos_m'],'drawer_after_m':after_features['qpos_m'],
                            'closure_mm':1000*(after_features['qpos_m']-before_features['qpos_m']),
                            'valid_handle_contact':after_features['valid_handle_contact'],
                            'valid_handle_grasp':after_features['valid_handle_grasp'],
                            'non_designated_robot_contact':after_features['non_designated_robot_contact'],
                            'contacting_robot_links':after_features['contacting_robot_links'],
                            'official_success':bool(world.env.check_success())})
                        completed_controls+=1
                after=world.features();eq(after['qpos_m'],primitive['outcome']['actual_joint_qpos_m'],'primitive after qpos')
                eq(bool(world.env.check_success()),primitive['outcome']['official_success'],'primitive after official success')
                eq(world.env.sim.get_state().flatten().tolist(),primitive['state_after'],'primitive final state')
                recorder.record('primitive_completed',{'step':step,'action':primitive['action'],'controls':len(primitive['commands']),
                    'state_after':primitive['state_after'],'drawer_after_m':after['qpos_m'],'official_success':bool(world.env.check_success()),
                    'native_integrator_calls':len(calls),'native_forward_calls':len(forwards),'exact_reference_state_match':True})
                completed_primitives+=1
        eq((completed_primitives,completed_controls),(122,970),'complete single canonical trace')
        eq(bool(world.env.check_success()),True,'canonical official success preserved')
        recorder.record('termination',{'reason':'canonical_replay_complete','completed_primitives':completed_primitives,
            'completed_controls':completed_controls,'native_integrations':24250,'native_snapshots':48500,
            'official_success':True,'final_drawer_qpos_m':float(world.data.qpos[world.qindex]),'model_calls':0,'policy_calls':0})
    except BaseException as exc:
        recorder.record('failure',{'step':step,'reason':repr(exc),'retries':0})
        recorder.record('termination',{'reason':'failure','completed_primitives':completed_primitives,'completed_controls':completed_controls,
            'missing_primitives':122-completed_primitives,'missing_controls':970-completed_controls})
        raise
    finally:
        if backend is not None:backend.close()
        recorder.close()


def audit(directory):
    """Stream raw records, retaining at most one native snapshot pair and one primitive."""
    directory=Path(directory);source=load_source();counts=Counter();environment=None;frozen=None;pending=None
    before_totals=table(CLASSES);after_totals=table(CLASSES);interval_totals=table(INTERVAL_CLASSES);control_totals=table(CLASSES)
    primitive_reports=[];current=None;last_after=None;control_start=None;control_end=None;forward=None
    interesting=[];per_stage_counts={'before':Counter(),'after':Counter()};termination=None
    for row in stream_records(directory/'episodes.jsonl'):
        kind,d=row['kind'],row['data'];counts[kind]+=1
        if kind=='failure':raise ValueError('recorded replay failure')
        if kind=='run_start':start=d
        elif kind=='frozen_inputs':
            frozen=d;eq(start['manifest']['code'],d['code'],'generation identity')
            eq(d['source_hashes'],SOURCE_HASHES,'registered source identities')
            eq(d['artifacts'],[p['artifact'] for p in source['primitives']],'registered trajectory identities')
            eq(code_identity()['source_sha256'],d['code']['source_sha256'],'frozen scientific source')
            eq(file_hash(PROTOCOL),d['protocol_sha256'],'protocol');eq(file_hash(directory/'protocol.md'),d['protocol_sha256'],'copied protocol')
            for path,digest in d['stepping_sources'].items():eq(file_hash(path),digest,'installed native source')
            prior=list(stream_records(Path(start['resolved_config']['preflight'])/'episodes.jsonl'));eq(native.one(prior,'frozen_inputs'),d,'preflight')
        elif kind=='environment':
            environment=d;eq(d['state'],source['environment']['sim_state'],'initial archive state')
        elif kind=='primitive_started':
            step=d['step'];eq(step,len(primitive_reports),'primitive order');p=source['primitives'][step]
            eq(d['action'],p['action'],'primitive label');eq(d['state'],p['states_before'][0],'primitive start')
            current={'step':step,'action':p['action'],'controls':len(p['commands']),'integrator_calls':0,
                'before':table(CLASSES),'after':table(CLASSES),'interval':table(INTERVAL_CLASSES)}
            last_after=None;forward=None
        elif kind=='control_started':
            p=source['primitives'][d['step']];eq(d['global_control'],counts['control_started']-1,'global control order')
            eq(d['command'],p['commands'][d['control']],'actual command');eq(d['state_before'],p['states_before'][d['control']],'before state')
            control_start=d
        elif kind=='native_forward_completed':forward=d
        elif kind=='integrator_call_started':
            if pending is not None:raise ValueError('uncompleted native call')
            pending=d
            eq(d['function'],'mj_step','native integrator');eq(d['call_index'],current['integrator_calls'],'native call index')
            eq(d['arm'],f"task1-primitive-{current['step']:03d}",'native primitive lineage')
            eq(d['control'],d['call_index']//25,'native control index');eq(d['within_control_index'],d['call_index']%25,'native substep index')
            eq(d['before']['last_native_forward'],forward,'last native forward')
            if last_after is not None:
                eq(d['before']['qpos'],last_after['qpos'],'qpos integration chain');eq(d['before']['qvel'],last_after['qvel'],'qvel integration chain')
            if d['within_control_index']==0:
                eq([d['before']['time_s']]+d['before']['qpos']+d['before']['qvel'],control_start['state_before'],'native control start')
        elif kind=='integrator_call_completed':
            if pending is None:raise ValueError('native call lacks start')
            for key in ('arm','function','control','call_index','within_control_index'):eq(d[key],pending[key],'native call identity')
            b,a=pending['before'],d['after'];eq(a['last_native_forward'],forward,'post-step forward lineage')
            if abs(a['time_s']-b['time_s']-.002)>1e-13:raise ValueError('native integration time mismatch')
            results={}
            for phase,s in (('before',b),('after',a)):
                eq(s['drawer_qpos_m'],s['qpos'][environment['drawer_qpos_address']],'native drawer qpos')
                eq(s['drawer_qvel_m_s'],s['qvel'][environment['drawer_dof_address']],'native drawer velocity')
                for sensor in environment['sensors']:
                    value=s['wrist_sensor_buffers'][sensor['key']];eq(len(value['values']),sensor['dimension'],'native wrist dimension')
                    eq(value['buffer_read_sim_time_s'],s['time_s'],'wrist read timing');eq(value['actual_sample_time_s'],None,'unknown sensor sample time')
                result=classify_contacts(s['contacts'],environment['geometry']);results[phase]=result
                for k,v in result.items():
                    if k!='class':per_stage_counts[phase][k]+=v
            delta=1000*(a['drawer_qpos_m']-b['drawer_qpos_m']);label=interval_class(results['before']['class'],results['after']['class'])
            accumulate(before_totals,results['before']['class'],delta);accumulate(after_totals,results['after']['class'],delta);accumulate(interval_totals,label,delta)
            for phase in ('before','after'):accumulate(current[phase],results[phase]['class'],delta)
            accumulate(current['interval'],label,delta)
            if any(results[phase]['designated'] or results[phase]['bilateral'] for phase in results):
                interesting.append({'step':current['step'],'control':d['control'],'substep':d['within_control_index'],
                    'interval_s':[b['time_s'],a['time_s']],'drawer_delta_mm':delta,'before':results['before'],'after':results['after']})
            current['integrator_calls']+=1;last_after=a;pending=None
        elif kind=='control_state_observed':
            p=source['primitives'][d['step']];i=d['control'];expected=p['states_before'][i+1] if i+1<len(p['commands']) else p['state_after']
            eq(d['state_after'],expected,'exact after-control archive state')
            eq([last_after['time_s']]+last_after['qpos']+last_after['qvel'],expected,'native last snapshot/control endpoint')
            control_end=d
        elif kind=='control_completed':
            eq(d['global_control'],counts['control_completed']-1,'completed control order')
            eq(d['global_control'],control_start['global_control'],'control intent lineage');eq(d['global_control'],control_end['global_control'],'control endpoint lineage')
            expected=classify_contacts(last_after['contacts'],environment['geometry'])
            eq(d['valid_handle_contact'],expected['designated'],'native/historical endpoint designated relation')
            eq(d['non_designated_robot_contact'],expected['historical_non_designated'],'native/historical endpoint nondesignated relation')
            eq(d['drawer_after_m'],last_after['drawer_qpos_m'],'endpoint drawer position')
            eq(d['drawer_before_m'],control_start['state_before'][1+environment['drawer_qpos_address']],'before-control drawer position')
            eq(d['closure_mm'],1000*(d['drawer_after_m']-d['drawer_before_m']),'endpoint closure arithmetic')
            accumulate(control_totals,relation_class(d['valid_handle_contact'],d['non_designated_robot_contact']),d['closure_mm'])
        elif kind=='primitive_completed':
            p=source['primitives'][d['step']];eq(d['state_after'],p['state_after'],'primitive after state')
            eq(d['official_success'],p['outcome']['official_success'],'primitive success');eq(d['drawer_after_m'],p['outcome']['actual_joint_qpos_m'],'primitive direct position')
            eq(d['native_integrator_calls'],len(p['commands'])*25,'per-primitive native calls')
            eq(current['integrator_calls'],d['native_integrator_calls'],'native call completion count');primitive_reports.append(current);current=None
        elif kind=='termination':termination=d
    eq(termination['reason'],'canonical_replay_complete','successful termination')
    eq(termination['official_success'],True,'official success')
    eq(termination['final_drawer_qpos_m'],source['primitives'][-1]['outcome']['actual_joint_qpos_m'],'final archive position')
    for kind,total in [('primitive_completed',122),('control_started',970),('control_state_observed',970),('control_completed',970),
                       ('integrator_call_started',24250),('integrator_call_completed',24250)]:eq(counts[kind],total,kind+' count')
    if pending is not None or current is not None:raise ValueError('unfinished primitive/integration')
    net=1000*(termination['final_drawer_qpos_m']-environment['initial_features']['qpos_m'])
    for totals in (before_totals,after_totals,interval_totals,control_totals):
        if abs(sum(x['net_change_mm'] for x in totals.values())-net)>1e-9:raise ValueError('drawer partition total differs')
    return {'raw_sha256':file_hash(directory/'episodes.jsonl'),'source_hashes':SOURCE_HASHES,
        'record_counts':dict(counts),'official_success':True,'net_drawer_closure_mm':net,
        'before_class_attribution':before_totals,'after_class_attribution':after_totals,
        'interval_class_attribution':interval_totals,'control_endpoint_attribution':control_totals,
        'stage_relation_counts':{k:dict(v) for k,v in per_stage_counts.items()},'designated_intervals':interesting,
        'per_primitive':primitive_reports,'scope':'descriptive direct drawer change by measured native stage classes; not exact causal attribution'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['preflight','run','audit']);p.add_argument('--output',required=True);p.add_argument('--preflight')
    args=p.parse_args()
    if args.mode=='audit':print(json.dumps(audit(args.output),indent=2))
    else:
        if args.mode=='run' and not args.preflight:p.error('run requires frozen preflight')
        run(args)


if __name__=='__main__':main()
