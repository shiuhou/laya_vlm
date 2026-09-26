"""Offline reconstruction of one initial-point control, including its first contact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from .records import load_records
from ..runtime_core import MOVE, _sha256_json
from ..decision_interface import FIELD_NAMES


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def data(rows, kind):
    return [r['data'] for r in rows if r['kind'] == kind]


def one(rows, kind):
    values = data(rows, kind)
    if len(values) != 1:
        raise ValueError(f'Expected one {kind}')
    return values[0]


def audit(run, repository):
    run, repository = Path(run), Path(repository)
    checks = []

    def check(name, value):
        if not bool(value):
            raise AssertionError(name)
        checks.append(name)

    rows, errors = load_records(run/'episodes.jsonl')
    check('complete evidence record chain', not errors)
    start = one(rows,'run_start')
    config, code = start['resolved_config'], start['manifest']['code']
    check('clean frozen source', code['dirty_status'] == '')
    for name, expected in code['source_sha256'].items():
        content = subprocess.check_output(['git','-C',str(repository),'show',code['commit']+':'+name])
        check('frozen source '+name, hashlib.sha256(content).hexdigest() == expected)
    check('frozen protocol', sha(run/'protocol.md') == config['protocol_sha256'])
    parent = Path(config['experiment_profile']['baseline_source'])
    check('archived fresh-query source', sha(parent/'episodes.jsonl') == config['experiment_profile']['baseline_sha256'])
    previous, errors = load_records(parent/'episodes.jsonl')
    check('baseline record chain', not errors)
    check('expected setup/budget', (config['seed'],config['init_state_id'],config['steps'],config['timeout_s']) == (1,0,40,900.))
    check('no runtime failure', not data(rows,'failure'))
    environment = one(rows,'environment')
    check('exact initial state/config/contacts match baseline', environment == one(previous,'environment'))
    check('exact benchmark identity', one(rows,'initial_identity') == one(previous,'initial_identity'))
    threshold = environment['new_contact_force_threshold_N']
    check('unchanged contact threshold', threshold == environment['task_config']['contact']['min_normal_force_N'] == 1.)
    check('initial contacts absent', environment['initial_contacts'] == [])
    initial_call = one(rows,'point_call_started')
    initial_output = one(rows,'point_call_completed')
    check('initial model arguments exactly match baseline', initial_call == data(previous,'point_call_started')[0])
    check('initial output exactly matches excluding wall latency',
        {k:v for k,v in initial_output.items() if k != 'latency_s'} ==
        {k:v for k,v in data(previous,'point_call_completed')[0].items() if k != 'latency_s'})
    model = next(r['model'] for r in data(rows,'manifest_update') if 'model' in r)
    model_path = Path(model['path'])
    hashed = {name:sha(model_path/name) for name in model['files_sha256']}
    check('all checkpoint bytes and content ID', hashed == model['files_sha256'] and _sha256_json(hashed) == model['content_id'])
    actions, boundaries, captures = (data(rows,k) for k in ('action','decision_boundary','vision_capture'))
    controls, starts, pauses = (data(rows,k) for k in ('control_observation','control_started','paused_state_check'))
    trajectories, schedule = (data(rows,k) for k in ('demo_trajectory','target_grounding_schedule'))
    term = one(rows,'termination')
    check('observed count consistency', len(actions) == len(boundaries) == len(captures) == len(trajectories) ==
          len(schedule) == len(pauses) == term['executed_primitives'] and len(controls) == len(starts) == 8*len(actions))
    frozen = one(rows,'initial_target_frozen')
    fixed = np.asarray(frozen['admitted']['position_world_m'])
    check('single initial target source', frozen['source_capture_seq'] == initial_call['capture_seq'] == 1 and frozen['completed_model_calls'] == 1)
    expected_state = environment['sim_state']
    for intent, control in zip(starts,controls,strict=True):
        check('control sequence '+str((control['step'],control['control'])),
              all(intent[k] == control[k] for k in intent) and control['state_before'] == expected_state and
              len(control['command']) == 7 and control['command'][6] == -1. and
              abs(control['state_after'][0]-control['state_before'][0]-.05) < 1e-12)
        expected_state = control['state_after']
    frames, camera_stable, boundary_summary = {}, True, []
    known = {'task.instruction','task.target_identity','robot.tcp_position_m','robot.gripper_width_m','robot.gripper_command',
        'target.position_m','target.position_definition','quality.geometry_valid','quality.geometry_age_s','quality.semantic_age_s',
        'relations.tcp_target_delta_m','relations.distance_m','relations.xy_error_m','relations.height_error_m'}
    initial_time = captures[0]['capture_sim_time']
    for step, (boundary,capture,pause,usage) in enumerate(zip(boundaries,captures,pauses,schedule,strict=True)):
        check('boundary ordering '+str(step), boundary['step'] == pause['step'] == step and
              boundary['capture_seq'] == capture['capture_seq'] == usage['boundary_capture_seq'] == step+1)
        check('paused state and timing '+str(step), pause['unchanged'] and pause['before'] == pause['after'] and
              pause['before'] == (environment['sim_state'] if step == 0 else controls[step*8-1]['state_after']) and
              capture['capture_sim_time'] == pause['before'][0])
        check('capture hash '+str(step), sha(run/capture['artifact']) == capture['artifact_sha256'])
        with np.load(run/capture['artifact'],allow_pickle=False) as artifact:
            frame = {key:artifact[key].copy() for key in artifact.files}
        frames[step] = frame
        camera_stable &= all(np.array_equal(frame[key],frames[0][key]) for key in ('intrinsics','camera_to_world'))
        fields = boundary['canonical']['state']['fields']
        check('unknown fields and privilege '+str(step), set(fields) == set(FIELD_NAMES) and
              all(not value['privileged'] and (name in known or value['value'] is None) for name,value in fields.items()))
        age = capture['capture_sim_time']-initial_time
        check('immutable target and truthful age '+str(step), boundary['admitted'] == frozen['admitted'] and
              fields['target.position_m']['value'] == fixed.tolist() and fields['quality.geometry_age_s']['value'] == age and
              fields['quality.semantic_age_s']['value'] == age == usage['target_age_sim_s'] and
              usage['source_capture_seq'] == 1 and usage['completed_model_calls'] == 1 and
              usage['target_refreshed'] == usage['current_rgbd_consumed_for_target'] == (step == 0))
        tcp = np.asarray(fields['robot.tcp_position_m']['value'])
        check('current returned robot proprioception '+str(step), np.array_equal(tcp,
              environment['initial_state']['tcp_xyz'] if step == 0 else actions[step-1]['result']['after']))
        delta = fixed-tcp
        values = [(float(np.linalg.norm(delta-.01*np.asarray(MOVE[token]))),token) for token in MOVE]
        distance, token = min(values)
        rule = token if distance < float(np.linalg.norm(delta)) else 'STOP'
        check('literal nominal selector '+str(step), boundary['selected'] == boundary['rule_recommendation'] == rule and
              [c['token'] for c in boundary['canonical']['candidates']] == [*MOVE,'STOP'])
        for token in MOVE:
            effect = boundary['canonical']['effects']['effects'][token]
            check('nominal effect '+str(step)+' '+token, effect['source'] == 'geometry' and not effect['privileged'] and
                effect['values']['distance_change_m'] == float(np.linalg.norm(delta-.01*np.asarray(MOVE[token]))-np.linalg.norm(delta)))
        boundary_summary.append({'step':step,'selected':rule,'target_age_sim_s':age,'tcp_world_m':tcp.tolist(),
            'fixed_point_distance_mm':float(np.linalg.norm(delta)*1000),
            'oracle_surface_gap_mm':actions[step]['oracle_before']['gripper_to_designated_handle_surface_mm']})
    # Reconstruct initial processor inputs and full generated-token decode on CPU.
    import torch
    from transformers import AutoProcessor, AutoTokenizer
    torch.set_num_threads(4)
    processor = AutoProcessor.from_pretrained(model_path,local_files_only=True,trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=True)
    messages = [{'role':'user','content':[{'type':'image','image':Image.fromarray(frames[0]['rgb']).convert('RGB')},
        {'type':'text','text':'Point to: '+config['query']+'.'}]}]
    text = processor.py_apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    images,videos = processor.process_vision_info(messages)
    inputs = processor(text=[text],images=images,videos=videos,return_tensors='pt')
    check('CPU processor text/tokens/attention/grid', text == initial_call['formatted_text'] and
          inputs['input_ids'][0].tolist() == initial_call['input_token_ids'] and
          inputs['attention_mask'].tolist() == initial_call['attention_mask'] and
          np.asarray(inputs['image_grid_hws']).tolist() == initial_call['image_grid_hws'])
    check('input tensor hash',sha(run/initial_call['pixel_values_artifact']) == initial_call['pixel_values_sha256'])
    with np.load(run/initial_call['pixel_values_artifact'],allow_pickle=False) as artifact:
        check('actual bfloat16 generate image arguments', np.array_equal(artifact['pixel_values_float32'],
              inputs['pixel_values'].to(torch.bfloat16).float().numpy()))
    generation = initial_output['generation_audit']
    ids = generation['actual_generated_token_ids']
    check('complete raw token decode',tokenizer.batch_decode([ids],skip_special_tokens=False)[0] == initial_output['raw_output'] and
          ids[-1] == generation['eos_token_id'] and generation['terminal_eos_observed'] and not generation['length_limit_reached'])
    boxes = re.findall(r'<box>(.*?)</box>',initial_output['raw_output'],re.S)
    check('one strict POINT',len(boxes) == 1 and re.fullmatch(r'<([0-9]+)><([0-9]+)>',boxes[0]) is not None)
    coords = np.array([int(x) for x in re.findall(r'<([0-9]+)>',boxes[0])])
    x,y = np.floor(coords/1000*384).astype(int)
    f, admitted = frames[0], frozen['admitted']
    z,k = float(f['depth_m'][y,x]),f['intrinsics']
    point = (f['camera_to_world'] @ np.array([(x+.5-k[0,2])*z/k[0,0],(y+.5-k[1,2])*z/k[1,1],z,1.]))[:3]
    check('independent initial depth projection',np.array_equal(point,fixed) and admitted['sample_pixel_xy'] == [x,y])
    for action, trajectory in zip(actions,trajectories,strict=True):
        step = action['step']; result = action['result']; cs = controls[step*8:(step+1)*8]
        check('actual primitive controls '+str(step), result['environment_step_count'] == 8 and
              result['low_level_commands'] == [c['command'] for c in cs] and
              result['token'] == action['token'] == boundaries[step]['selected'] and not result['execution_contract_violation'])
        check('trajectory hash '+str(step),sha(run/trajectory['artifact']) == trajectory['sha256'])
        with np.load(run/trajectory['artifact'],allow_pickle=False) as artifact:
            check('trajectory states/commands/frames '+str(step), artifact['states_before'].tolist() == [c['state_before'] for c in cs] and
                  artifact['state_after'].tolist() == cs[-1]['state_after'] and artifact['commands'].tolist() == result['low_level_commands'] and
                  len(artifact['frames']) == 8)
        pairs = sorted({tuple(c['geom_ids']) for control in cs for c in control['contacts'] if c['normal_force_N'] > threshold})
        check('external contact abort recomputation '+str(step), pairs == [tuple(pair) for pair in action['new_robot_contact_pairs']])
    old_actions, old_boundaries = data(previous,'action'), data(previous,'decision_boundary')
    first_divergence = next((i for i,(a,b) in enumerate(zip(actions,old_actions)) if a['token'] != b['token']),None)
    check('observed comparison has action divergence',first_divergence is not None)
    prefix_controls = first_divergence*8
    check('all physical control prefix records exactly equal', controls[:prefix_controls] == data(previous,'control_observation')[:prefix_controls])
    sensor_distance_keys = {'sensor_fixed_point_distance_before_m','sensor_fixed_point_distance_after_m'}
    check('all physical action prefix fields exactly equal', all(
        {k:v for k,v in new.items() if k not in sensor_distance_keys} ==
        {k:v for k,v in old.items() if k not in sensor_distance_keys}
        for new,old in zip(actions[:first_divergence],old_actions[:first_divergence],strict=True)))
    sensor_distance_differences = [i for i,(new,old) in enumerate(zip(actions[:first_divergence],old_actions[:first_divergence]))
        if any(new[k] != old[k] for k in sensor_distance_keys)]
    check('all prefix RGB-D capture hashes exactly equal',captures[:first_divergence+1] == data(previous,'vision_capture')[:first_divergence+1])
    check('first divergent boundary simulator state exactly equal', pauses[first_divergence] == data(previous,'paused_state_check')[first_divergence])
    new_fields = boundaries[first_divergence]['canonical']['state']['fields']
    old_fields = old_boundaries[first_divergence]['canonical']['state']['fields']
    check('divergent boundary proprioception exactly equal', all(new_fields[k] == old_fields[k] for k in new_fields if k.startswith('robot.')))
    divergent_rules = {}
    for label, fields in [('initial',new_fields),('fresh',old_fields)]:
        delta = np.array(fields['target.position_m']['value'])-fields['robot.tcp_position_m']['value']
        distance,token = min((float(np.linalg.norm(delta-.01*np.asarray(MOVE[t]))),t) for t in MOVE)
        divergent_rules[label] = token if distance < np.linalg.norm(delta) else 'STOP'
    check('first differing action explained by target alone',divergent_rules['initial'] == actions[first_divergence]['token'] and
          divergent_rules['fresh'] == old_actions[first_divergence]['token'])
    contacted = [c for c in controls if c['contacts']]
    crossed = [c for c in contacted if any(r['normal_force_N'] > threshold for r in c['contacts'])]
    check('stopped at first above-threshold contact primitive',bool(crossed) and crossed[0]['step'] == actions[-1]['step'] == term['boundary'] and
          term['reason'] == 'external_oracle_new_robot_contact')
    handle = set(environment['task_config']['measurements']['gripper_handle_contacts']['right']['geoms'])
    nonhandle = set(environment['task_config']['measurements']['gripper_nonhandle_contacts']['right']['geoms'])
    check('all sampled contacts are configured nonhandle geoms',all(any(n in nonhandle for n in c['geom_names']) and
          not any(n in handle for n in c['geom_names']) for row in contacted for c in row['contacts']))
    replay = json.loads((run/'replay-check.json').read_text())
    check('full exact actual-control replay', replay['raw_source_sha256'] == sha(run/'episodes.jsonl') and
          replay['controls'] == len(controls) and replay['passed'] and all(c['max_error'] == 0 for c in replay['checks']))
    ray_path = parent.parent/'coarse-point-boundary-grounding-audit-01.json'
    ray_audit = json.loads(ray_path.read_text())
    initial_ray = ray_audit['rows'][0]
    check('archived initial ray identity with identical state/image/point',
          ray_audit['source_episodes_sha256'] == sha(parent/'episodes.jsonl') and
          initial_ray['frame_sha256'] == captures[0]['artifact_sha256'] and initial_ray['target_member'] is True and
          initial_ray['sensor_point_world_m'] == fixed.tolist())
    result = {'all_checks_passed':True,'checks':len(checks),'check_names':checks,'raw':str(run),'commit':code['commit'],
        'raw_sha256':sha(run/'episodes.jsonl'),'initial_calls':1,'executed_primitives':len(actions),'controls':len(controls),
        'termination':term,'camera_calibration_exactly_stable':bool(camera_stable),'initial_point_world_m':fixed.tolist(),
        'initial_ray_evaluator':{'source':str(ray_path),'sha256':sha(ray_path),'row':initial_ray,
            'basis':'Inherited evaluator evidence only after exact initial state/image/point equality; no new ray or policy input.'},
        'first_divergence':{'boundary':first_divergence,'matching_primitives':first_divergence,'matching_controls':prefix_controls,
            'matching_boundary_RGBD_captures':first_divergence+1,'state_and_proprioception_exactly_equal':True,
            'prefix_sensor_distance_metric_differences':sensor_distance_differences,
            'rules':divergent_rules,'initial_point_world_m':new_fields['target.position_m']['value'],
            'fresh_point_world_m':old_fields['target.position_m']['value']},
        'first_contact':contacted[0],'first_above_threshold_contact':crossed[0],
        'contact_samples':[{'step':r['step'],'control':r['control'],'contacts':r['contacts']} for r in contacted],
        'first_oracle':actions[0]['oracle_before'],'last_oracle':actions[-1]['oracle_after'],
        'target_handle_center_max_change_before_final_primitive_mm':float(max(np.linalg.norm(
            np.array(a['oracle_before']['handle_center_m'])-actions[0]['oracle_before']['handle_center_m']) for a in actions)*1000),
        'boundaries':boundary_summary,'replay':{'controls':replay['controls'],'max_state_error':max(c['max_error'] for c in replay['checks']),
            'checks':len(replay['checks']),'sha256':sha(run/'replay-check.json')},
        'limitations':['One init/seed physical condition; GPU assignment differs from historical baseline.',
            'Processor evidence reconstructs generate arguments, not actual forward hooks or full-vocabulary logits.',
            'Current visibility/identity and target motion are unobserved by the selector after initialization.',
            'Contact abort is privileged and occurs after completing the native atomic action.',
            'Contact is sampled after native controls, not every integration substep.']}
    selected = [0,first_divergence,first_divergence+1,len(actions)-1]
    with np.load(run/trajectories[-1]['artifact'],allow_pickle=False) as artifact:
        last_frames = artifact['frames'].copy()
    sheet = Image.new('RGB',(384*4,424*2),'white')
    for column,step in enumerate(selected):
        sheet.paste(Image.fromarray(frames[step]['rgb']),(column*384,24))
        ImageDraw.Draw(sheet).text((column*384+5,5),f'Boundary {step}: {actions[step]["token"]}; initial point copied',fill='black')
    for column,index in enumerate((0,2,4,7)):
        sheet.paste(Image.fromarray(last_frames[index]),(column*384,448))
        force = next((c['contacts'][0]['normal_force_N'] for c in contacted if c['control'] == index),None)
        ImageDraw.Draw(sheet).text((column*384+5,429),f'Action {len(actions)-1}, control {index}; force {force:.3f} N',fill='black')
    sheet.save(run/'independent-contact-sheet.png')
    with (run/'independent-audit.json').open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--repository',default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    result = audit(args.source,args.repository)
    print(json.dumps({key:result[key] for key in ('all_checks_passed','checks','executed_primitives','controls','first_divergence','replay')},indent=2))
