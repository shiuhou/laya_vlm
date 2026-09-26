"""One fixed local grasp/10mm-lift transfer, no model or sensor-selected policy."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import sys

import numpy as np

from ..runtime_core import AtomicExecutor
from . import interaction_observability as prior
from .native_substep_observability import array_hash, integration_fingerprint
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, versions

ROOT = Path(__file__).resolve().parents[2]
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
SOURCE = RAW / 'interaction-observability-paired-01'
PROTOCOL = ROOT / 'docs/research/local_grasp_interface_protocol.md'
HASHES = {
 'manifest.json':'b68dfcbf65048555069bb1c27639915ec2fda9c520822600f81549547031b02f',
 'sensors.jsonl':'59a38821e165393d607be1b3ec9100f093fcc52718282173fe8b28c556174bbe',
 'captures.json':'e632b67471cf4b3b7bb924201a884d43339e677140a64522b4ef63f349fb2650',
 'endpoints.json':'c28136d9e0e67b359491a3d270b0566e49a7f5939287363a18cdd8192ab7abe5',
 'sensor-seal.json':'77752c151c979e234607942a46674f25f3e6664eb66844e4411cff1def076013',
 'evaluator-only/labels.json':'493c7b1ff32943217351d73b631c385199dfaab4d3ed8427a52de32c768945c5'}


def equal(a, b, name):
    if jsonable(a) != jsonable(b):
        raise ValueError('exact comparison failed: ' + name)


def load_source():
    for name, digest in HASHES.items():
        equal(file_hash(SOURCE / name), digest, name)
    seal = json.loads((SOURCE / 'sensor-seal.json').read_text())
    for name, digest in seal['sha256'].items():
        equal(file_hash(SOURCE / name), digest, 'sealed ' + name)
    result = {name: json.loads((SOURCE / (name + '.json')).read_text())
              for name in ('captures', 'endpoints')}
    result['sensors'] = [json.loads(line) for line in (SOURCE / 'sensors.jsonl').read_text().splitlines()]
    result['labels'] = json.loads((SOURCE / 'evaluator-only/labels.json').read_text())
    return result


def required(rows, **keys):
    matches = [r for r in rows if all(r.get(k) == v for k, v in keys.items())]
    if len(matches) != 1:
        raise ValueError('reference key is not unique: ' + str(keys))
    return matches[0]


def fixed_token(arm, step):
    if arm not in prior.ARMS or step not in (13, 14):
        raise ValueError('outside fixed intervention')
    return ('GRASP' if arm == 'close' else 'STOP') if step == 13 else 'MV_UP'


def require_pass(result):
    if result['execution_contract_violation']:
        raise RuntimeError('unchanged_execution_validator:' + ','.join(result['execution_contract_reason']))
    if result['environment_step_count'] != 8:
        raise RuntimeError('unexpected native control count')


def unexpected_contact(a, b, normal_force, groups):
    robot = a in groups['robot'] or b in groups['robot']
    allowed = ((a in groups['gripper'] and b in groups['bottle']) or
               (b in groups['gripper'] and a in groups['bottle']))
    return bool(robot and not allowed and normal_force > .05)


@contextmanager
def read_only_measurement(w):
    fields = ('geom_xpos','geom_xmat','site_xpos','site_xmat','cam_xpos','cam_xmat',
              'sensordata','qacc')
    before = integration_fingerprint(w)
    caches = {key:array_hash(getattr(w.data,key)) for key in fields}
    try:
        yield
    finally:
        equal(integration_fingerprint(w),before,'measurement integration state')
        equal({key:array_hash(getattr(w.data,key)) for key in fields},caches,'measurement cached geometry/sensors')


def read_sensors_and_label(w, sensors, observations, command):
    with read_only_measurement(w):
        return sensors.read(observations,command), prior.evaluation(w)


def contact_snapshot(w, groups):
    fingerprint = integration_fingerprint(w)
    rows = []
    for i in range(w.data.ncon):
        c = w.data.contact[i]
        a, b = int(c.geom1), int(c.geom2)
        f = np.zeros(6)
        w.mujoco.mj_contactForce(w.model, w.data, i, f)
        rows.append({'geom_ids':[a,b], 'geom_names':[w.env.sim.model.geom_id2name(g) for g in (a,b)],
                     'force_contact_frame':f.tolist(), 'normal_force_N':float(f[0]),
                     'unexpected_robot_contact':unexpected_contact(a,b,f[0],groups)})
    robot = w.env.robots[0]
    row = {'time_s':float(w.data.time), 'contacts':rows,
           'wrist_force_local_N':np.asarray(robot.ee_force).tolist(),
           'wrist_torque_local_Nm':np.asarray(robot.ee_torque).tolist(),
           'wrist_sample_time_s':None, 'qpos':np.asarray(w.data.qpos).tolist(),
           'qvel':np.asarray(w.data.qvel).tolist(), 'integration_fingerprint':fingerprint}
    equal(integration_fingerprint(w), fingerprint, 'nonmutating native snapshot')
    return row


@contextmanager
def native_observer(w, recorder, arm, step, tracking, groups):
    original = w.mujoco.mj_step
    rows = []
    def observed(model, data, *args, **kwargs):
        if model is not w.model or data is not w.data:
            return original(model, data, *args, **kwargs)
        if tracking['control'] is None:
            raise RuntimeError('integration outside registered control')
        ids = {'arm':arm, 'step':step, 'control':tracking['control'], 'index':len(rows)}
        before = contact_snapshot(w, groups)
        recorder.record('native_before', {**ids, **before})
        result = original(model, data, *args, **kwargs)
        after = contact_snapshot(w, groups)
        recorder.record('native_after', {**ids, **after})
        rows.append({'control':tracking['control'], 'before':before, 'after':after})
        return result
    w.mujoco.mj_step = observed
    try:
        yield rows
    finally:
        w.mujoco.mj_step = original


def collect(args):
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    from ..adapters.libero_rgbd import LiberoRgbdSource
    from jev_libero.measurements import Measurements
    from .native_substep_observability import stepping_identity
    from .records import repository_identity, package_directory
    import jev_libero.world

    source = load_source()
    code = code_identity()
    if code['dirty_status']:
        raise ValueError('clean frozen code required')
    if not args.review or not Path(args.review).is_file():
        raise ValueError('independent review receipt required')
    frozen = {'code':code, 'source_sha256':HASHES, 'protocol_sha256':file_hash(PROTOCOL),
              'review_path':str(Path(args.review).resolve()), 'review_sha256':file_hash(args.review),
              'jev':repository_identity(package_directory(jev_libero.world)), 'stepping_sources':stepping_identity(),
              'versions':versions(), 'argv':sys.argv, 'task':'wine_bottle_bottom_drawer', 'seed':1, 'init':0,
              'environment':{k:os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')},
              'model_calls':0, 'control_policy':'fixed_mechanical_diagnostic', 'oracle_abort':True}
    equal(frozen['environment'], {'CUDA_VISIBLE_DEVICES':'4','MUJOCO_GL':'egl','MUJOCO_EGL_DEVICE_ID':'4'}, 'GPU allocation')
    recorder = RunRecorder(args.output, {'mode':'local_grasp_interface', 'seed':1,'init':0},
                           {'run_id':Path(args.output).name, **frozen})
    out = recorder.output
    (out / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (out / 'review.txt').write_bytes(Path(args.review).read_bytes())
    oracle, masks, captures, sensor_rows = [], [], [], []
    current = None
    completed = []
    try:
        recorder.record('frozen_inputs', frozen)
        for arm in prior.ARMS:
            current = {'arm':arm, 'step':-1}
            backend = WineBottleBottomDrawerAdapter().make_backend(args, render=True)
            w = backend.world
            directory = out / arm
            directory.mkdir()
            sensors, camera = prior.RobotSensors(w), LiberoRgbdSource(w)
            m = Measurements(w)
            groups = {'robot':m.ids({'group':'robot'}), 'gripper':set(w.gripper_geoms),
                      'bottle':set(w.scene.geoms)}
            recorder.record('arm_started', {'arm':arm,'groups':{k:sorted(v) for k,v in groups.items()},
                            'geom_names':{str(i):w.env.sim.model.geom_id2name(i) for i in range(w.model.ngeom)},
                            'fresh_reset':True, 'physics_timestep_s':float(w.model.opt.timestep),
                            'integrator':int(w.model.opt.integrator)})
            equal(float(w.model.opt.timestep), .002, 'native2ms')
            equal(int(w.model.opt.integrator), 0, 'nativeEuler')
            capture_id = 0
            def capture(step, control):
                nonlocal capture_id
                with read_only_measurement(w):
                    frame, meta = prior.capture(w, camera, directory, capture_id,
                                    {'arm':arm,'after_step':step,'control':control}, masks)
                captures.append(meta)
                if step <= 12:
                    old = required(source['captures'], arm=arm, after_step=step)
                    with np.load(SOURCE / old['artifact'], allow_pickle=False) as original:
                        for key in ('rgb','depth_m','intrinsics','camera_to_world'):
                            if not np.array_equal(frame[key], original[key]):
                                raise ValueError(f'exact image/calibration mismatch:{arm}/{step}/{key}')
                capture_id += 1
            try:
                with read_only_measurement(w):
                    initial = prior.evaluation(w)
                oracle.append({'arm':arm,'after_step':-1,'control':None, **initial})
                recorder.record('initial_observed', {'arm':arm, **initial})
                equal(initial, {k:v for k,v in required(source['labels'],arm=arm,after_step=-1).items()
                                if k not in ('arm','after_step','control')}, 'initial state/evaluator')
                capture(-1, None)
                for step in range(15):
                    current = {'arm':arm,'step':step}
                    token = prior.prefix(arm)[step] if step < 13 else fixed_token(arm,step)
                    recorder.record('action_intent', {**current, 'token':token})
                    original_step = w.env.step
                    override = w.env.__dict__.get('step')
                    controls = []
                    tracking = {'control':None}
                    def observe_control(command):
                        control = len(controls)
                        if control >= 8:
                            raise RuntimeError('extra control refused')
                        tracking['control'] = control
                        state_before = w.env.sim.get_state().flatten().tolist()
                        recorder.record('control_started', {**current, 'control':control,
                                        'command':np.asarray(command).tolist(), 'state_before':state_before})
                        if step <= 13:
                            old = required(source['sensors'],arm=arm,step=step,control=control)
                            equal(command, old['sensor']['command'], 'reference command')
                        returned = original_step(command)
                        tracking['control'] = None
                        sensed, label = read_sensors_and_label(w,sensors,returned[0],command)
                        row = {**current,'control':control,'sensor':sensed}
                        sensor_rows.append(row)
                        oracle.append({'arm':arm,'after_step':step,'control':control, **label})
                        recorder.record('control_observed', {**row, 'state_after':label['state']})
                        controls.append(row)
                        if step <= 13:
                            equal({k:v for k,v in sensed.items() if k != 'wall_time_unix_s'},
                                  {k:v for k,v in old['sensor'].items() if k != 'wall_time_unix_s'}, 'reference robot sensor')
                            oldlabel = required(source['labels'],arm=arm,after_step=step,control=control)
                            equal(label, {k:v for k,v in oldlabel.items() if k not in ('arm','after_step','control')},
                                  'reference state/evaluator')
                        if step >= 13:
                            capture(step,control)
                        return returned
                    w.env.step = observe_control
                    try:
                        context = native_observer(w,recorder,arm,step,tracking,groups) if step >= 13 else nullcontext([])
                        with context as native:
                            if step < 13:
                                result = w.execute(token,grip=backend._grip_cmd,record=False)
                                backend._grip_cmd = result['grip']
                            else:
                                result = AtomicExecutor(backend).execute(token)
                    finally:
                        if override is None:
                            w.env.__dict__.pop('step',None)
                        else:
                            w.env.step = override
                    recorder.record('action_completed', {**current,'token':token,'result':result})
                    equal(len(controls), 8, 'eight native controls')
                    if step >= 13:
                        require_pass(result)
                        equal(len(native), 200, '200 integrations per primitive')
                        for c in range(8):
                            equal(sum(r['control']==c for r in native),25,'25 integrations per control')
                        if any(c['unexpected_robot_contact'] for r in native for stage in ('before','after')
                               for c in r[stage]['contacts']):
                            raise RuntimeError('unexpected_robot_contact_at_native_stage')
                    else:
                        capture(step,7)
                    print(json.dumps({**current,'token':token,'complete':True}),flush=True)
                completed.append(arm)
                recorder.record('arm_completed', {'arm':arm,'official_success':bool(w.env.check_success())})
            finally:
                backend.close()
        recorder.record('termination', {'reason':'both_local_arms_complete','arms':completed})
    except BaseException as exc:
        recorder.record('failure', {'type':type(exc).__name__,'error':str(exc),'boundary':current,
                                   'completed_arms':completed,'no_retry':True})
        raise
    finally:
        prior.write_json(out/'sensors.json',sensor_rows)
        prior.write_json(out/'captures.json',captures)
        paths = ['sensors.json','captures.json'] + [c[key] for c in captures for key in ('artifact','rgb_artifact')]
        prior.write_json(out/'sensor-seal.json',{'sha256':{p:file_hash(out/p) for p in paths},
                          'policy':'fixed_diagnostic_no_sensor_selection','holding':None})
        (out/'evaluator-only').mkdir()
        prior.write_json(out/'evaluator-only/labels.json',oracle)
        for arm, capture_id, mask in masks:
            np.save(out/'evaluator-only'/f'{arm}-{capture_id:04d}-bottle-mask.npy',mask)
        recorder.close()


def replay(args):
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    source = Path(args.source)
    records, errors = load_records(source/'episodes.jsonl')
    if errors or any(r['kind']=='failure' for r in records):
        raise ValueError('completed source required')
    equal(required([r['data'] for r in records if r['kind']=='termination'])['reason'],
          'both_local_arms_complete','completed experiment')
    frozen = required([r['data'] for r in records if r['kind']=='frozen_inputs'])
    equal(code_identity(),frozen['code'],'replay exact clean scientific source')
    equal(file_hash(PROTOCOL),frozen['protocol_sha256'],'replay protocol')
    from .native_substep_observability import stepping_identity
    from .records import repository_identity, package_directory
    import jev_libero.world
    equal(repository_identity(package_directory(jev_libero.world)),frozen['jev'],'replay jev')
    equal(stepping_identity(),frozen['stepping_sources'],'replay stepping sources')
    equal(versions(),frozen['versions'],'replay package versions')
    equal({k:os.environ.get(k) for k in frozen['environment']},frozen['environment'],'replay environment')
    out = Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    rows = []
    try:
        for arm in prior.ARMS:
            backend = WineBottleBottomDrawerAdapter().make_backend(args,render=False)
            w = backend.world
            try:
                starts = [r['data'] for r in records if r['kind']=='control_started' and r['data']['arm']==arm]
                afters = [r['data'] for r in records if r['kind']=='control_observed' and r['data']['arm']==arm]
                equal(len(starts),120,'120 controls/arm')
                equal(len(afters),120,'120 measured states/arm')
                for before,after in zip(starts,afters):
                    equal(w.env.sim.get_state().flatten(),before['state_before'],'replay before')
                    w.obs,_,_,_=w.env.step(before['command'])
                    actual = w.env.sim.get_state().flatten().tolist()
                    equal(actual,after['state_after'],'replay after')
                    rows.append({'arm':arm,'step':before['step'],'control':before['control'],
                                 'state_after':actual,'max_error':0.})
            finally:
                backend.close()
        prior.write_json(out/'result.json',{'source_sha256':file_hash(source/'episodes.jsonl'),
                         'code':code_identity(),'exact_controls':len(rows),'rows':rows})
    except BaseException as exc:
        prior.write_json(out/'failure.json',{'error':str(exc),'rows':rows,'no_retry':True})
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('collect','replay'),required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--source')
    p.add_argument('--review')
    p.add_argument('--libero-root',default='/home/junhongli/projects/LIBERO')
    p.add_argument('--config-dir',default='/home/junhongli/runs/libero-config')
    args=p.parse_args()
    args.seed,args.init_state_id=1,0
    (collect if args.mode=='collect' else replay)(args)
