"""Read-only integrator-boundary observations of two exactly reproduced native arms."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from ..runtime_core import AtomicExecutor
from . import coarse_native_counterfactual as reference
from .records import RunRecorder, code_identity, file_hash, load_records, versions

RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
REFERENCE = RAW/'coarse-native-counterfactual-run-01'
REFERENCE_SHA256 = '23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa'
PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/native_substep_observability_protocol.md'
ARMS = ('MV_RIGHT', 'MV_DOWN')
FUNCTIONS = ('mj_step', 'mj_step1', 'mj_step2')
VERSION = 'native-substep-observability-v1'
data, one = reference.data, reference.one


def load_reference():
    if file_hash(REFERENCE/'episodes.jsonl') != REFERENCE_SHA256:
        raise ValueError('completed seven-arm reference changed')
    rows, errors = load_records(REFERENCE/'episodes.jsonl')
    if errors or data(rows, 'failure') or one(rows, 'termination')['reason'] != 'seven_arms_complete':
        raise ValueError('complete seven-arm reference required')
    frozen = one(rows, 'frozen_inputs')
    root = Path(__file__).resolve().parents[2]
    if any(file_hash(root/name) != digest for name, digest in frozen['code']['source_sha256'].items()):
        raise ValueError('reference scientific source changed')
    return rows


def stepping_identity():
    import robosuite.environments.base
    import robosuite.utils.binding_utils
    import libero.libero.envs.bddl_base_domain
    import jev_libero.world
    modules = (robosuite.environments.base, robosuite.utils.binding_utils,
               libero.libero.envs.bddl_base_domain, jev_libero.world)
    return {str(Path(inspect.getfile(module)).resolve()): file_hash(inspect.getfile(module)) for module in modules}


def frozen_inputs(source, prior):
    base = reference.frozen_inputs(source)
    return {'version':VERSION, 'source_conditions':base, 'arms':list(ARMS),
            'reference':str(REFERENCE), 'reference_sha256':REFERENCE_SHA256,
            'reference_frozen_inputs':one(prior, 'frozen_inputs'),
            'protocol_sha256':file_hash(PROTOCOL), 'code':code_identity(),
            'stepping_source_sha256':stepping_identity(),
            'native_calls_per_control':25, 'native_controls_per_arm':8,
            'instrumented_entry_points':list(FUNCTIONS), 'model_calls':0, 'retries':0}


def array_hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def integration_fingerprint(world):
    api = world.mujoco
    spec = api.mjtState.mjSTATE_INTEGRATION
    values = np.empty(api.mj_stateSize(world.model, spec), dtype=np.float64)
    api.mj_getState(world.model, world.data, values, spec)
    return array_hash(values)


def snapshot(world, robot_geoms, drawer_geoms, handle_geoms, last_forward):
    """Reads native cached data; never advances/synchronizes physics or observations."""
    initial = integration_fingerprint(world)
    model, simdata = world.model, world.data
    contacts = []
    for i in range(simdata.ncon):
        contact = simdata.contact[i]
        a, b = int(contact.geom1), int(contact.geom2)
        force = np.zeros(6)
        world.mujoco.mj_contactForce(model, simdata, i, force)
        contacts.append({'index':i, 'geom_ids':[a,b],
            'geom_names':[world.env.sim.model.geom_id2name(g) for g in (a,b)],
            'robot_sides':[a in robot_geoms,b in robot_geoms],
            'drawer_sides':[a in drawer_geoms,b in drawer_geoms],
            'handle_sides':[a in handle_geoms,b in handle_geoms],
            'position_world_m':np.asarray(contact.pos).tolist(), 'distance_m':float(contact.dist),
            'force_contact_frame':force.tolist(), 'normal_force_N':float(force[0]),
            'above_original_1N':bool(force[0] > 1.)})
    dof = int(model.jnt_dofadr[world.jid])
    qpos = int(model.jnt_qposadr[world.jid])
    state = {'time_s':float(simdata.time), 'qpos':np.asarray(simdata.qpos).tolist(),
        'qvel':np.asarray(simdata.qvel).tolist(), 'qacc':np.asarray(simdata.qacc).tolist(),
        'ctrl':np.asarray(simdata.ctrl).tolist(),
        'drawer_qpos_address':qpos, 'drawer_dof_address':dof,
        'drawer_qpos_m':float(simdata.qpos[qpos]), 'drawer_qvel_m_s':float(simdata.qvel[dof]),
        'drawer_qacc_m_s2':float(simdata.qacc[dof]),
        'cached_handle_geom_positions_m':{str(g):np.asarray(simdata.geom_xpos[g]).tolist() for g in sorted(handle_geoms)},
        'contacts':contacts, 'last_native_forward':last_forward,
        'integration_fingerprint':initial,
        'cache_semantics':'native derived buffers; no added forward; post-step qpos/time can be newer than contact/force/geometry buffers'}
    state['xfrc_applied'] = np.asarray(simdata.xfrc_applied).tolist()
    for field in ('qfrc_applied','qfrc_constraint','qfrc_passive','qfrc_bias','qfrc_actuator','qfrc_smooth'):
        state[field] = np.asarray(getattr(simdata, field)).tolist()
        state['drawer_'+field] = float(getattr(simdata, field)[dof])
    if integration_fingerprint(world) != initial:
        raise ValueError('read-only snapshot changed native integration state')
    return state


@contextmanager
def observe_integrators(world, recorder, arm, tracking, geometry):
    api = world.mujoco
    originals = {name:getattr(api,name) for name in (*FUNCTIONS, 'mj_forward')}
    calls, forwards = [], []
    last_forward = None
    def active(args, kwargs):
        model = args[0] if args else kwargs.get('m',kwargs.get('model'))
        simdata = args[1] if len(args)>1 else kwargs.get('d',kwargs.get('data'))
        return model is world.model and simdata is world.data
    def observed_forward(*args, **kwargs):
        nonlocal last_forward
        if not active(args, kwargs):
            return originals['mj_forward'](*args, **kwargs)
        row = {'arm':arm,'forward_index':len(forwards),'control':tracking['control'],
               'input_time_s':float(world.data.time),'input_qpos_sha256':array_hash(world.data.qpos)}
        result = originals['mj_forward'](*args, **kwargs)
        row['output_time_s'] = float(world.data.time)
        last_forward = dict(row)
        forwards.append(row)
        recorder.record('native_forward_completed', row)
        return result
    def wrapper(name):
        def observed(*args, **kwargs):
            if not active(args, kwargs):
                return originals[name](*args, **kwargs)
            control = tracking['control']
            if control is None:
                raise ValueError('native integration outside registered control')
            index = sum(row['control']==control for row in calls)
            identifiers = {'arm':arm,'call_index':len(calls),'control':control,
                           'within_control_index':index,'function':name}
            before = snapshot(world,*geometry,last_forward)
            recorder.record('integrator_call_started', {**identifiers,'before':before})
            result = originals[name](*args, **kwargs)
            after = snapshot(world,*geometry,last_forward)
            row = {**identifiers,'before':before,'after':after}
            calls.append(row)
            recorder.record('integrator_call_completed', {**identifiers,'after':after})
            return result
        return observed
    api.mj_forward = observed_forward
    for name in FUNCTIONS:
        setattr(api,name,wrapper(name))
    try:
        yield calls, forwards
    finally:
        for name, original in originals.items():
            setattr(api,name,original)


def require_equal(actual, expected, context):
    if actual != expected:
        raise ValueError(f'exact reference mismatch: {context}')


@contextmanager
def observe_controls(world, measurements, gap, recorder, arm, expected, tracking, calls):
    original, controls = world.env.step, []
    def observed(command):
        i = len(controls)
        intent = {'arm':arm,'control':i,'command':np.asarray(command).tolist(),
                  'state_before':world.env.sim.get_state().flatten().tolist()}
        recorder.record('arm_control_started', intent)
        if i >= 8:
            raise ValueError('extra native control refused')
        require_equal(intent,{k:expected[i][k] for k in intent},f'{arm} control {i} before')
        tracking['control'] = i
        returned = original(command)
        tracking['control'] = None
        row = {**intent,'state_after':world.env.sim.get_state().flatten().tolist(),
            'sim_time_s':float(world.data.time),'contacts':reference.base.contact_rows(measurements),
            'gripper_to_designated_handle_surface_mm':gap.minimum_mm(world.data),
            'drawer_joint_qpos_m':float(world.data.qpos[world.qindex]),
            'returned_robot_tcp_m':np.asarray(returned[0]['robot0_eef_pos']).tolist(),
            'returned_gripper_qpos':np.asarray(returned[0]['robot0_gripper_qpos']).tolist(),
            'robot_observation_exact_sample_time_s':None}
        recorder.record('arm_control_completed',row)
        require_equal(row,expected[i],f'{arm} control {i} after')
        selected = [r for r in calls if r['control']==i]
        if len(selected)!=25 or any(r['function']!='mj_step' for r in selected):
            raise ValueError('registered actual integrator path/count differs')
        controls.append(row)
        return returned
    world.env.step = observed
    try:
        yield controls
    finally:
        world.env.step = original
        tracking['control'] = None


def run(args):
    recorder = RunRecorder(args.output,{'mode':args.mode,'preflight':args.preflight,
        'planned_arms':list(ARMS),'reference':str(REFERENCE),'model_calls':0,'retries':0},
        {'run_id':Path(args.output).name,'code':code_identity(),'versions':versions()})
    completed, current = [], None
    try:
        source, prior = reference.load_source(), load_reference()
        frozen = frozen_inputs(source,prior)
        recorder.record('frozen_inputs',frozen)
        (recorder.output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        if args.mode=='preflight':
            recorder.record('termination',{'reason':'preflight_complete','executed_arms':[]})
            return
        preflight, errors = load_records(Path(args.preflight)/'episodes.jsonl')
        if errors or data(preflight,'failure'):
            raise ValueError('successful preflight required')
        require_equal(one(preflight,'frozen_inputs'),frozen,'preflight')
        require_equal(one(preflight,'termination'),{'reason':'preflight_complete','executed_arms':[]},'preflight termination')
        from .engineering_demo import RecordingBackend, save_trajectory
        from jev_libero.measurements import Measurements
        from jev_libero.geometry import GeometryGap
        initial = one(source,'environment')
        config = one(source,'run_start')['resolved_config']
        for current in ARMS:
            original = next(x for x in data(prior,'arm_completed') if x['arm']==current)
            boundary = next(x for x in data(prior,'preboundary') if x['arm']==current)
            expected = [x for x in data(prior,'arm_control_completed') if x['arm']==current]
            recorder.record('arm_started',{'arm':current,'fresh_reset':True,'diagnostic_prefix_controls':200})
            backend = RecordingBackend.from_task('top_drawer',seed=1,init_state_id=0,render=True,
                libero_root=config['libero_root'],config_dir=config['config_dir'])
            try:
                world = backend.world
                require_equal(world.config,initial['task_config'],'task configuration')
                require_equal(backend.execution_state(),initial['initial_state'],'initial execution state')
                state = reference.exact_state(world,initial['sim_state'],f'{current} initial')
                recorder.record('arm_initial_state',{'arm':current,'state':state,'execution_state':backend.execution_state()})
                reference.replay_prefix(world,data(source,'control_observation')[:200],recorder,current)
                reference.exact_state(world,boundary['state'],f'{current} boundary')
                require_equal(backend.execution_state(),original['result']['execution_before'],'preboundary execution state')
                require_equal(backend.proprioception(),boundary['proprioception'],'preboundary robot observation')
                measurements = Measurements(world)
                handle = measurements.ids(world.config['measurements']['handle_center_mm']['entity'])
                gap = GeometryGap(world.model,world.gripper_geoms,handle)
                require_equal(reference.base.oracle_evaluation(backend,gap,measurements),original['oracle_before'],'preboundary evaluator')
                reference.capture(backend,recorder,current,'before')
                robot, drawer = measurements.ids({'group':'robot'}), measurements.ids({'group':'target'})
                native = {'arm':current,'integrator':int(world.model.opt.integrator),
                    'model_timestep_s':float(world.model.opt.timestep),
                    'control_timestep_s':float(world.env.env.control_timestep),
                    'drawer_joint_id':int(world.jid),'drawer_qpos_address':int(world.model.jnt_qposadr[world.jid]),
                    'drawer_dof_address':int(world.model.jnt_dofadr[world.jid]),
                    'robot_geom_ids':sorted(robot),'drawer_geom_ids':sorted(drawer),'handle_geom_ids':sorted(handle),
                    'state':boundary['state'],'reference_preboundary':boundary}
                recorder.record('preboundary',native)
                tracking = {'control':None}
                with observe_integrators(world,recorder,current,tracking,(robot,drawer,handle)) as (calls,forwards):
                    with observe_controls(world,measurements,gap,recorder,current,expected,tracking,calls) as controls:
                        result = AtomicExecutor(backend).execute(current)
                recorder.record('execution_result',{'arm':current,'result':result})
                require_equal(result,original['result'],f'{current} full executor result')
                reference.exact_state(world,original['state_after'],f'{current} endpoint')
                save_trajectory(backend,recorder.output,original['arm_index'],recorder)
                after = reference.base.oracle_evaluation(backend,gap,measurements)
                require_equal(after,original['oracle_after'],f'{current} evaluator endpoint')
                reference.capture(backend,recorder,current,'after')
                if len(controls)!=8 or len(calls)!=200:
                    raise ValueError('incomplete native arm')
                recorder.record('arm_completed',{'arm':current,'result':result,'oracle_after':after,
                    'exact_full_reference_match':True,'controls':8,'native_integrator_calls':len(calls),
                    'native_forward_calls':len(forwards)})
                completed.append(current)
            finally:
                backend.close()
        recorder.record('termination',{'reason':'two_arms_complete','executed_arms':completed,
            'missing_arms':[],'diagnostic_prefix_controls':400,'native_controls':16,'native_integrator_calls':400,'model_calls':0})
    except BaseException as exc:
        recorder.record('failure',{'arm':current,'reason':repr(exc),'retries':0})
        recorder.record('termination',{'reason':'failure','executed_arms':completed,
            'missing_arms':[a for a in ARMS if a not in completed]})
        raise
    finally:
        recorder.close()


def audit(directory):
    directory = Path(directory)
    source, prior = reference.load_source(), load_reference()
    rows, errors = load_records(directory/'episodes.jsonl')
    if errors or data(rows,'failure') or one(rows,'termination')['reason']!='two_arms_complete':
        raise ValueError('complete failure-free diagnostic required')
    frozen = one(rows,'frozen_inputs')
    require_equal(one(rows,'run_start')['manifest']['code'],frozen['code'],'frozen generation code')
    require_equal(frozen['arms'],list(ARMS),'registered arms')
    preflight, errors = load_records(Path(one(rows,'run_start')['resolved_config']['preflight'])/'episodes.jsonl')
    if errors or one(preflight,'frozen_inputs')!=frozen or code_identity()['source_sha256']!=frozen['code']['source_sha256']:
        raise ValueError('preflight/scientific code changed')
    if file_hash(PROTOCOL)!=frozen['protocol_sha256'] or file_hash(directory/'protocol.md')!=frozen['protocol_sha256']:
        raise ValueError('frozen protocol changed')
    if file_hash(REFERENCE/'episodes.jsonl')!=frozen['reference_sha256']:
        raise ValueError('reference changed')
    for name,digest in frozen['stepping_source_sha256'].items():
        if file_hash(name)!=digest:
            raise ValueError('native stepping source changed')
    require_equal([x['arm'] for x in data(rows,'arm_completed')],list(ARMS),'arm order')
    reports=[]
    for arm in ARMS:
        def own(kind): return [x for x in data(rows,kind) if x['arm']==arm]
        original = next(x for x in data(prior,'arm_completed') if x['arm']==arm)
        require_equal(own('arm_initial_state')[0]['state'],one(source,'environment')['sim_state'],'initial state')
        for kind in ('prefix_control_started','prefix_control_completed'):
            prefix=own(kind)
            require_equal(len(prefix),200,'prefix length')
            for i,(row,old) in enumerate(zip(prefix,data(source,'control_observation')[:200])):
                require_equal(row['ordinal'],i,'prefix ordinal')
                for key in ('command','state_before')+ (('state_after',) if kind.endswith('completed') else ()):
                    require_equal(row[key],old[key],'prefix '+key)
        controls=own('arm_control_completed')
        require_equal(controls,[x for x in data(prior,'arm_control_completed') if x['arm']==arm],'all reference control rows')
        intents=own('arm_control_started')
        require_equal(len(intents),8,'eight control intents')
        for intent,control in zip(intents,controls):
            require_equal(intent,{k:control[k] for k in intent},'intent/completion')
        require_equal(own('execution_result')[0]['result'],original['result'],'full executor result')
        require_equal(own('arm_completed')[0]['result'],original['result'],'completed executor result')
        require_equal(own('arm_completed')[0]['oracle_after'],original['oracle_after'],'evaluator endpoint')
        starts,done=own('integrator_call_started'),own('integrator_call_completed')
        require_equal(len(starts),200,'native integrator starts');require_equal(len(done),200,'native integrator completions')
        boundary=own('preboundary')[0];by_control=[];all_robot=[]
        forwards={x['forward_index']:x for x in own('native_forward_completed')}
        for i,(start,completion) in enumerate(zip(starts,done)):
            for key in ('arm','call_index','control','within_control_index','function'):
                require_equal(start[key],completion[key],'integrator identifiers')
            require_equal((start['call_index'],start['control'],start['within_control_index'],start['function']),
                          (i,i//25,i%25,'mj_step'),'native path')
            before,after=start['before'],completion['after']
            if not np.isclose(after['time_s']-before['time_s'],boundary['model_timestep_s'],rtol=0,atol=1e-14):
                raise ValueError('native integrator time interval changed')
            if i%25==0:
                require_equal([before['time_s']]+before['qpos']+before['qvel'],controls[i//25]['state_before'],'control start integration state')
            if i%25==24:
                require_equal([after['time_s']]+after['qpos']+after['qvel'],controls[i//25]['state_after'],'control end integration state')
            elif i+1<len(starts):
                require_equal(after['qpos'],starts[i+1]['before']['qpos'],'integrator qpos chain')
                require_equal(after['qvel'],starts[i+1]['before']['qvel'],'integrator qvel chain')
            for phase,snap in (('before',before),('after',after)):
                require_equal(snap['drawer_qpos_m'],snap['qpos'][boundary['drawer_qpos_address']],'direct drawer position')
                require_equal(snap['drawer_qvel_m_s'],snap['qvel'][boundary['drawer_dof_address']],'direct drawer velocity')
                forward=snap['last_native_forward']
                require_equal(forward,forwards[forward['forward_index']],'native forward lineage')
                for contact in snap['contacts']:
                    require_equal(contact['robot_sides'],[g in boundary['robot_geom_ids'] for g in contact['geom_ids']],'robot membership')
                    require_equal(contact['drawer_sides'],[g in boundary['drawer_geom_ids'] for g in contact['geom_ids']],'drawer membership')
                    require_equal(contact['handle_sides'],[g in boundary['handle_geom_ids'] for g in contact['geom_ids']],'handle membership')
                    require_equal(contact['normal_force_N'],contact['force_contact_frame'][0],'contact normal')
                    require_equal(contact['above_original_1N'],contact['normal_force_N']>1.,'strict contact threshold')
                    if any(contact['robot_sides']):
                        all_robot.append({'call_index':i,'control':i//25,'within_control_index':i%25,
                            'phase':phase,'buffer_time_s':snap['time_s'],
                            'integration_interval_s':[before['time_s'],after['time_s']],**contact})
        for control in range(8):
            selected=[x for x in all_robot if x['control']==control]
            start=starts[control*25]['before'];after=done[(control+1)*25-1]['after']
            by_control.append({'control':control,'drawer_delta_mm':1000*(after['drawer_qpos_m']-start['drawer_qpos_m']),
                'native_boundary_robot_contact_rows':len(selected),
                'max_robot_normal_force_N':max((x['normal_force_N'] for x in selected),default=0.),
                'after_control_robot_contact_rows':len(controls[control]['contacts'])})
        nonhandle=[x for x in all_robot if not any(x['handle_sides'])]
        reports.append({'arm':arm,'integrator':boundary['integrator'],'model_timestep_s':boundary['model_timestep_s'],
            'native_calls':200,'native_forward_calls':len(forwards),'exact_reference_match':True,
            'native_boundary_robot_contact_rows':len(all_robot),'native_boundary_nonhandle_contact_rows':len(nonhandle),
            'max_robot_normal_force_N':max((x['normal_force_N'] for x in all_robot),default=0.),
            'first_observed_robot_contact':all_robot[0] if all_robot else None,
            'first_observed_nonhandle_contact':nonhandle[0] if nonhandle else None,
            'per_control':by_control,'reference_result':original['result'],
            'drawer_joint_delta_mm':original['drawer_joint_delta_m']*1000,
            'scope':'native integrator-boundary cached contacts; before/after can duplicate one event; not continuous contact onset or causal isolation'})
    for row in data(rows,'capture')+data(rows,'demo_trajectory'):
        require_equal(file_hash(directory/row['artifact']),row['sha256'],'artifact hash')
    require_equal(len(data(rows,'capture')),4,'before/after capture count')
    require_equal(len(data(rows,'demo_trajectory')),2,'native trajectory count')
    for arm,trajectory in zip(ARMS,data(rows,'demo_trajectory')):
        controls=[x for x in data(rows,'arm_control_completed') if x['arm']==arm]
        with np.load(directory/trajectory['artifact'],allow_pickle=False) as arrays:
            require_equal(arrays['commands'].tolist(),[x['command'] for x in controls],'trajectory commands')
            require_equal(arrays['states_before'].tolist(),[x['state_before'] for x in controls],'trajectory before states')
            require_equal(arrays['state_after'].tolist(),controls[-1]['state_after'],'trajectory final state')
            require_equal(len(arrays['frames']),8,'native trajectory frames')
    return {'raw_sha256':file_hash(directory/'episodes.jsonl'),'reference_sha256':REFERENCE_SHA256,
        'prefix_controls':400,'native_controls':16,'integrator_calls':400,'snapshots':800,'model_calls':0,'arms':reports}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','run','audit'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--preflight')
    args=parser.parse_args()
    if args.mode=='audit':
        print(json.dumps(audit(args.output),indent=2))
    else:
        if args.mode=='run' and not args.preflight:
            parser.error('run requires frozen preflight')
        run(args)


if __name__=='__main__':
    main()
