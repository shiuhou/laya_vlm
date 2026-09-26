"""Independent stored-only audit of the bounded grasp-interface transfer."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import near, require
from .task1_substep_evidence_audit import stream_records

ARMS = ('close', 'open_hold')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(rows, keys):
    result = {tuple(r[k] for k in keys): r for r in rows}
    require(len(result) == len(rows), 'unique row keys')
    return result


def audit(raw, source, replay):
    identity = {}
    records = list(stream_records(raw/'episodes.jsonl', identity))
    counts = Counter(r['kind'] for r in records)
    require(not counts['failure'] and records[-1]['kind'] == 'termination', 'complete collection')
    require(records[-1]['data'] == {'reason': 'both_local_arms_complete', 'arms': list(ARMS)}, 'both arms complete')
    frozen = next(r['data'] for r in records if r['kind']=='frozen_inputs')
    require(frozen['code']['commit'] == '9b85ad5bb48de68e097b233afef8ecfd84cdb993' and not frozen['code']['dirty_status'], 'reviewed clean freeze')
    require(digest(raw/'protocol.md') == frozen['protocol_sha256'] and digest(raw/'review.txt') == frozen['review_sha256'], 'protocol/review identities')
    for name, value in frozen['source_sha256'].items():
        require(digest(source/name) == value, 'archived source identity')
    seal = json.loads((raw/'sensor-seal.json').read_text())
    for name, value in seal['sha256'].items():
        require(digest(raw/name) == value, 'sealed sensor artifact')
    source_sensors = keyed([json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()], ('arm','step','control'))
    source_labels = keyed(json.loads((source/'evaluator-only/labels.json').read_text()), ('arm','after_step','control'))
    source_captures = keyed(json.loads((source/'captures.json').read_text()), ('arm','after_step','control'))
    sensors = keyed(json.loads((raw/'sensors.json').read_text()), ('arm','step','control'))
    labels = keyed(json.loads((raw/'evaluator-only/labels.json').read_text()), ('arm','after_step','control'))
    captures = json.loads((raw/'captures.json').read_text())
    require(len(sensors)==240 and len(labels)==242 and len(captures)==60, 'complete output artifacts')
    starts = keyed([r['data'] for r in records if r['kind']=='control_started'], ('arm','step','control'))
    observed = keyed([r['data'] for r in records if r['kind']=='control_observed'], ('arm','step','control'))
    actions = keyed([r['data'] for r in records if r['kind']=='action_completed'], ('arm','step'))
    envs = keyed([r['data'] for r in records if r['kind']=='arm_started'], ('arm',))
    native = {stage: keyed([r['data'] for r in records if r['kind']==f'native_{stage}'], ('arm','step','index')) for stage in ('before','after')}
    require(len(starts)==len(observed)==240 and len(actions)==30 and all(len(v)==800 for v in native.values()), 'journal completeness')
    image_checks = 0
    for capture in captures:
        if capture['after_step'] <= 12:
            old = source_captures[(capture['arm'],capture['after_step'],capture['control'])]
            with np.load(raw/capture['artifact'],allow_pickle=False) as actual, np.load(source/old['artifact'],allow_pickle=False) as expected:
                for name in ('rgb','depth_m','intrinsics','camera_to_world'):
                    require(actual[name].dtype==expected[name].dtype and actual[name].shape==expected[name].shape and actual[name].tobytes()==expected[name].tobytes(), 'prefix exact image/calibration')
            image_checks += 1
    result = {}
    for arm in ARMS:
        environment=envs[(arm,)]
        groups={k:set(v) for k,v in environment['groups'].items()}
        require(groups['gripper'] <= groups['robot'] and groups['bottle'].isdisjoint(groups['robot']), 'declared groups')
        pads=[{int(g) for g,name in environment['geom_names'].items() if name==f'gripper0_finger{side}_pad_collision'} for side in (1,2)]
        require(all(len(group)==1 for group in pads), 'bilateral pad identities')
        initial=labels[(arm,-1,None)]
        require(initial==source_labels[(arm,-1,None)], 'fresh initial state/evaluator')
        previous=initial['state']
        checks=[];stage_counts={step:{stage:0 for stage in ('before','after')} for step in (13,14)}
        unexpected_rows=0
        for step in range(15):
            for control in range(8):
                key=(arm,step,control);start,after=starts[key],observed[key]
                sensor=sensors[key];label=labels[key]
                require(start['state_before']==previous and after['state_after']==label['state'], 'full control state chain')
                require(after['sensor']==sensor['sensor'] and start['command']==sensor['sensor']['command'], 'sensor journal/command')
                require(not any(start['command'][3:6]), 'no commanded rotation')
                if step <= 13:
                    old=source_sensors[key]
                    require(start['command']==old['sensor']['command'], 'archived command exact')
                    require({k:v for k,v in sensor['sensor'].items() if k!='wall_time_unix_s'}=={k:v for k,v in old['sensor'].items() if k!='wall_time_unix_s'}, 'archived robot sensor exact')
                    require(label==source_labels[key], 'archived evaluator/state exact')
                contact_pads={c['hand'] for c in label['contacts'] if c['normal_force_N']>.05 and c['moving_target']}
                require(label['valid_grasp_relation']==all(f'gripper0_finger{side}_pad_collision' in contact_pads for side in (1,2)), 'endpoint bilateral predicate')
                if step >= 13:
                    native_previous=start['state_before']
                    for substep in range(25):
                        index=control*25+substep
                        before=native['before'][(arm,step,index)];end=native['after'][(arm,step,index)]
                        require(before['control']==end['control']==control, 'native control index')
                        require([before['time_s']]+before['qpos']+before['qvel']==native_previous, 'native before state')
                        near(end['time_s']-before['time_s'],.002,'native interval')
                        for stage,row in (('before',before),('after',end)):
                            touched=set()
                            for c in row['contacts']:
                                a,b=c['geom_ids'];force=c['normal_force_N']
                                require(force==c['force_contact_frame'][0] and c['geom_names']==[environment['geom_names'][str(g)] for g in (a,b)], 'native pair/force')
                                allowed=(a in groups['gripper'] and b in groups['bottle']) or (b in groups['gripper'] and a in groups['bottle'])
                                unexpected=(a in groups['robot'] or b in groups['robot']) and not allowed and force>.05
                                require(c['unexpected_robot_contact']==unexpected,'symmetric abort arithmetic');unexpected_rows+=unexpected
                                if force>.05:
                                    for side,pad in enumerate(pads):
                                        if (a in pad and b in groups['bottle']) or (b in pad and a in groups['bottle']):touched.add(side)
                            stage_counts[step][stage]+=len(touched)==2
                            require(row['wrist_sample_time_s'] is None and len(row['wrist_force_local_N'])==len(row['wrist_torque_local_Nm'])==3,'native wrist schema')
                        native_previous=[end['time_s']]+end['qpos']+end['qvel']
                    require(native_previous==after['state_after'],'native after control')
                previous=after['state_after']
            if step>=13:
                action=actions[(arm,step)];execution=action['result']
                expected_token='MV_UP' if step==14 else 'GRASP' if arm=='close' else 'STOP'
                require(action['token']==execution['token']==expected_token,'unchanged atomic action')
                require(execution['execution_contract_version']=='atomic-top-drawer-v1' and execution['execution_contract_tolerances']==dict(translation_error_m=.002,hold_translation_m=.0015,hold_rotation_deg=1.,rotation_error_deg=2.),'unchanged tolerance')
                before,after=execution['execution_before'],execution['execution_after']
                delta=np.asarray(after['tcp_xyz'])-before['tcp_xyz'];target=np.array([0.,0.,.01 if step==14 else 0.])
                residual=float(np.linalg.norm(delta-target));rotation=np.asarray(after['orientation'])@np.asarray(before['orientation']).T
                angle=float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2,-1,1))))
                commands=[starts[(arm,step,c)]['command'] for c in range(8)]
                grip=1. if arm=='close' else -1.
                require(execution['low_level_commands']==commands and all(c[-1]==grip for c in commands) and after['gripper_command']==grip,'retained jaw commands')
                require(execution['environment_step_count']==8 and execution['low_level_step_count']==200,'executor counts')
                near(execution['delta_m'],delta,'executor displacement');near(execution['rotation_angle_deg'],angle,'executor rotation')
                require(residual<=(.002 if step==14 else .0015) and angle<=1. and execution['execution_contract_violation'] is False and execution['execution_contract_reason']==[],'independent execution contract pass')
                checks.append({'step':step,'token':expected_token,'tcp_delta_mm':(delta*1000).tolist(),'translation_residual_mm':residual*1000,'rotation_change_deg':angle})
        rise=labels[(arm,14,7)]['bottle_center_mm'][2]-labels[(arm,13,7)]['bottle_center_mm'][2]
        result[arm]={'atomic_checks':checks,'bottle_center_rise_mm':rise,'endpoint_lift_bilateral_samples':sum(labels[(arm,14,c)]['valid_grasp_relation'] for c in range(8)),
                     'native_bilateral_samples':stage_counts,'unexpected_strong_robot_rows':unexpected_rows,'official_success':labels[(arm,14,7)]['official_success']}
        require(unexpected_rows==0,'no oracle contact abort')
    verification=json.loads((replay/'result.json').read_text())
    require(verification['source_sha256']==identity['sha256'] and verification['code']==frozen['code'] and verification['exact_controls']==240,'frozen replay identity')
    replay_rows=keyed(verification['rows'],('arm','step','control'))
    require(set(replay_rows)==set(observed) and all(row['state_after']==observed[k]['state_after'] and row['max_error']==0 for k,row in replay_rows.items()),'all replay states exact')
    witness=result['close']['bottle_center_rise_mm']>max(0,result['open_hold']['bottle_center_rise_mm']) and result['close']['endpoint_lift_bilateral_samples']==8 and result['open_hold']['endpoint_lift_bilateral_samples']==0
    require(witness,'registered sampled-endpoint witness')
    return {'passed':True,'raw_identity':identity,'replay_sha256':digest(replay/'result.json'),'sensor_seal_sha256':digest(raw/'sensor-seal.json'),
            'prefix_frames_exact':image_checks,'archived_controls_exact':224,'total_controls':240,'native_integrations':800,'stage_samples':1600,'replay_states_exact':240,
            'sampled_endpoint_positive_witness':witness,'arms':result,'scope':'independent stored-source/array/contact/validator/replay-record audit; no new physics or FK'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','source','replay','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=audit(args.raw,args.source,args.replay)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result))
