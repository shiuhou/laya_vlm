"""Independent raw-record audit of seven fresh-prefix continuations; no physics."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from task2_box_evidence_audit import canonical, read, require, sha

FREEZE = '69d649111e3272c17b7ffd1f6db4a7908927ee78'
MOVES = {'MV_FWD': [1, 0, 0], 'MV_BACK': [-1, 0, 0], 'MV_LEFT': [0, 1, 0], 'MV_RIGHT': [0, -1, 0], 'MV_UP': [0, 0, 1], 'MV_DOWN': [0, 0, -1], 'STOP': [0, 0, 0]}


def classify(pair, groups):
    a, b = pair
    if a in groups['robot'] and b in groups['robot']:
        return 'self'
    for key, label in (('pads', 'pad/bottle'), ('gripper', 'other_gripper/bottle')):
        if (a in groups[key] and b in groups['bottle']) or (b in groups[key] and a in groups['bottle']):
            return label
    return 'gripper/other_scene' if a in groups['gripper'] or b in groups['gripper'] else 'arm/scene'


def audit(sources, run_name):
    run, original = sources / run_name, sources / 'task2-box-point-boundary-run-01'
    source_path = original / 'episodes.jsonl'
    require(sha(source_path) == 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771', 'sealed original journal')
    source_rows = [json.loads(line) for line in source_path.read_text().splitlines()]
    source_data = defaultdict(list)
    for row in source_rows:
        source_data[row['kind']].append(row['data'])
    expected = {}
    for row in source_rows:
        d, k = row['data'], row['kind']
        if k in ('native_before', 'native_after', 'control_started', 'control_completed'):
            expected[(k, d['step'], d['control'], d.get('index'))] = d
    groups = {k: set(v) for k, v in source_data['initial_frame_gate'][0]['groups_evaluator_only'].items()}
    config, manifest = read(run / 'resolved_config.yaml'), read(run / 'manifest.json')
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean reviewed freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_pre22_counterfactual.py'] == '4ede195169750f476d1d3364563952ecab72942c8d51c53c14b630c7b365a97b', 'reviewed adapter')
    require(sha(run / 'protocol.md') == manifest['protocol_sha256'] == '9c191b5b73e430432bbef63469591be80247113d1f032a7a1de3606b94af7e91', 'reviewed protocol')
    require(sha(run / 'review.md') == manifest['review_sha256'] and FREEZE in (run / 'review.md').read_text(), 'prospective receipt identity')
    preflight_path = sources / 'task2-pre22-counterfactual-preflight-01.json'
    require(sha(preflight_path) == '0eccbeb023faf2ebe8baa14d6044850e802165c50f6ddfdb55abd66bec8324ad', 'actual no-world preflight')
    preflight = read(preflight_path)
    require(all(manifest[key] == value for key, value in preflight.items()), 'complete manifest preflight identity')
    require(config == {'mode': 'declared_pre22_counterfactual', 'branches': list(MOVES), 'seed': 1, 'init_state_id': 0, 'prefix_actions_per_branch': 22, 'retries': 0}, 'registered batch configuration')
    _, utilization, memory = manifest['GPU4_before_batch'].split(',')
    require(int(utilization) == 0 and int(memory) <= 100 and manifest['environment'] == {'CUDA_VISIBLE_DEVICES': '4', 'MUJOCO_GL': 'egl', 'MUJOCO_EGL_DEVICE_ID': '4'}, 'recorded resource admission')
    for relative, digest in manifest['frozen_surface_comparison_sha256'].items():
        require(sha(sources / relative) == digest, 'preexisting geometric outputs unchanged')
    by_branch = {name: defaultdict(list) for name in MOVES}
    counts, previous, completed, active = Counter(), None, [], None
    source_checks = Counter()
    for seq, line in enumerate((run / 'episodes.jsonl').open('rb')):
        require(line.endswith(b'\n'), 'complete journal line')
        row = json.loads(line)
        require(row['seq'] == seq and row['previous_record_id'] == previous and row['config_hash'] == canonical(config), 'journal sequence/chain/config')
        require(row['record_id'] == canonical({k: v for k, v in row.items() if k != 'record_id'}), 'record hash')
        previous = row['record_id']
        k, d = row['kind'], row['data']
        counts[k] += 1
        require(k not in ('failure', 'first_mismatch'), 'no ignored qualification failure')
        if k == 'run_start':
            require(d['manifest'] == manifest and d['resolved_config'] == config, 'manifest/config journal identity')
        if k == 'branch_started':
            require(active is None and d['branch'] == list(MOVES)[len(completed)], 'one fresh branch at a time in canonical order')
            active = d['branch']
            require(d['fresh_reset'] and not d['archived_state_restored'] and d['standard_settling_controls'] == 10 and d['prefix_controls'] == 176, 'declared reset/settling/prefix semantics')
        branch = d.get('branch')
        if branch is not None:
            require(branch == active, 'all branch records belong to active continuation')
            if k in ('native_before', 'native_after', 'control_started', 'control_completed'):
                clean = {key: value for key, value in d.items() if key != 'branch'}
                key = (k, d['step'], d['control'], d.get('index'))
                if d['step'] < 22 or branch == 'MV_FWD':
                    require(clean == expected[key], 'entire original prefix/FWD control or native snapshot exact')
                    source_checks[branch] += 1
            by_branch[branch][k].append(d)
        if k == 'probe_started':
            branch_rows = by_branch[branch]
            require(len(branch_rows['prefix_qualified']) == 1 and len(branch_rows['capture']) == 23 and len(branch_rows['control_completed']) == 176 and len(branch_rows['native_before']) == len(branch_rows['native_after']) == 4400, 'all exact prefix evidence precedes probe')
        if k == 'branch_completed':
            require(d['completed_primitive'] and d['no_subsequent_action'], 'one complete probe and no continuation')
            require(d['source_FWD_qualification_exact'] is (True if branch == 'MV_FWD' else None), 'only FWD source qualification asserted')
            completed.append(active)
            active = None
        if k == 'termination':
            termination = d
    require(active is None and completed == list(MOVES), 'all seven branches completed')
    require(counts == Counter({'run_start': 1, 'branch_started': 7, 'initial_gates': 7, 'capture': 168, 'control_started': 1288, 'control_completed': 1288, 'native_before': 32200, 'native_after': 32200, 'prefix_qualified': 7, 'probe_started': 7, 'probe_result': 7, 'branch_completed': 7, 'termination': 1}), 'exact complete journal counts')
    require(termination == {'reason': 'seven_branches_complete', 'completed': list(MOVES), 'prefix_controls_total': 1232, 'probe_controls_total': 56, 'native_integrations_total': 32200, 'original_loop_STOP_semantics': 'no further primitive; represented analytically, no eighth world', 'policy_or_safety_filter_changed': False, 'new_model_calls': 0}, 'complete bounded termination')
    base_model, report = None, {}
    fixed_point = np.asarray(manifest['point']['position_world_m'])
    for branch, records in by_branch.items():
        initial = records['initial_gates'][0]
        require(initial['initial_state'] == source_data['control_started'][0]['state_before'] and initial['own_observations'] == source_data['initial_frame_gate'][0]['initial_own_observations'] and initial['backend_gripper_command'] == -1 and initial['source_state_own_groups_native_exact'], 'recorded fresh initial values')
        model = initial['current_model_identity']
        if base_model is None:
            base_model = model
            require(sha(run / 'current-model.xml') == model['xml_sha256'], 'retained current assembled XML hash')
        require(model == base_model and not model['historical_model_byte_identity_claimed'], 'identical recorded current compiled-model fingerprints across fresh branches')
        nq, nv = model['dimensions']['nq'], model['dimensions']['nv']
        prefix = records['prefix_qualified'][0]
        original_action = source_data['action_completed'][22]['result']
        require(prefix['controls'] == 176 and prefix['native_stage_samples'] == 8800 and prefix['captures'] == 23 and prefix['execution_before'] == original_action['execution_before'], 'exact qualified pre22 boundary')
        begins, ends = records['control_started'], records['control_completed']
        before_native, after_native = records['native_before'], records['native_after']
        require(len(begins) == len(ends) == 184 and len(before_native) == len(after_native) == 4600, 'per-branch complete controls/stages')
        for i, (begin, end) in enumerate(zip(begins, ends)):
            step, control = divmod(i, 8)
            require(begin['step'] == end['step'] == step and begin['control'] == end['control'] == control and begin['command'] == end['command'], 'control lineage')
            if i:
                require(begin['state_before'] == ends[i-1]['state_after'] and begin['previous_returned_own_observations'] == ends[i-1]['returned_own_observations'], 'control-to-control state and own packet handoff')
            for j in range(25):
                b, a = before_native[i*25+j], after_native[i*25+j]
                require(b['step'] == a['step'] == step and b['control'] == a['control'] == control and b['index'] == a['index'] == control*25+j, 'all native stage indices')
                require(np.isclose(a['time_s'] - b['time_s'], .002, rtol=0, atol=1e-12), 'native2ms integration')
                if j:
                    prev = after_native[i*25+j-1]
                    require(b['time_s'] == prev['time_s'] and b['qpos'] == prev['qpos'] and b['qvel'] == prev['qvel'], 'native state handoff')
            for state, native in ((begin['state_before'], before_native[i*25]), (end['state_after'], after_native[i*25+24])):
                require(state[0] == native['time_s'] and state[1:1+nq] == native['qpos'] and state[1+nq:1+nq+nv] == native['qvel'], 'control and native state boundary equality')
        captures = records['capture']
        require([c['capture_seq'] for c in captures] == [c['capture_seq'] for c in source_data['vision_capture'][:24]], 'all initial/prefix/probe captures use the source camera sequence')
        for i, capture in enumerate(captures):
            path = run / capture['artifact']
            require(sha(path) == capture['sha256'], 'captured artifact seal')
            with np.load(path, allow_pickle=False) as actual:
                require(set(actual.files) == {'rgb', 'depth_m', 'intrinsics', 'camera_to_world'}, 'raw sensor-only capture fields')
                if i < 23 or branch == 'MV_FWD':
                    reference = source_data['vision_capture'][i]
                    require(capture['capture_sim_time'] == reference['capture_sim_time'] and all(capture['array_bytes_exact'].values()), 'recorded source capture gate')
                    with np.load(original / reference['artifact'], allow_pickle=False) as expected_frame:
                        require(all(actual[k].dtype == expected_frame[k].dtype and actual[k].shape == expected_frame[k].shape and actual[k].tobytes() == expected_frame[k].tobytes() for k in actual.files), 'independent exact saved prefix/FWD RGB-D bytes')
        probe, outcome = records['probe_started'][0], records['probe_result'][0]
        result = outcome['result']
        delta = np.asarray(MOVES[branch]) * .01
        target = np.asarray(prefix['execution_before']['tcp_xyz']) + delta
        require(probe['nominal_delta_m'] == delta.tolist() and probe['hold_or_translation_target_world_m'] == target.tolist() and probe['token'] == branch, 'actual hold/translation target semantics')
        for begin in begins[176:]:
            command = np.r_[np.clip((target - begin['previous_returned_own_observations']['robot0_eef_pos']) / .05, -1, 1), np.zeros(3), -1.].tolist()
            require(begin['command'] == command, 'all56 actual native feedback commands from retained target and previous own observation')
        require(result['low_level_commands'] == [d['command'] for d in begins[176:]] and result['environment_step_count'] == outcome['controls'] == 8 and result['low_level_step_count'] == outcome['native_integrations'] == 200, 'complete executor/control result')
        require(outcome['endpoint_own_observations'] == ends[-1]['returned_own_observations'] and result['before'] == begins[176]['previous_returned_own_observations']['robot0_eef_pos'] and result['after'] == ends[-1]['returned_own_observations']['robot0_eef_pos'], 'recorded endpoint own correspondence')
        before, after = result['execution_before'], result['execution_after']
        measured_delta = np.asarray(after['tcp_xyz']) - before['tcp_xyz']
        rotation = np.asarray(after['orientation']) @ np.asarray(before['orientation']).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2, -1, 1))))
        require(result['delta_m'] == measured_delta.tolist() and np.allclose(result['rotation_delta'], rotation, rtol=0, atol=1e-15) and abs(result['rotation_angle_deg'] - angle) < 1e-12, 'stored translation/rotation arithmetic')
        require(result['execution_contract_tolerances'] == {'translation_error_m': .002, 'hold_translation_m': .0015, 'hold_rotation_deg': 1., 'rotation_error_deg': 2.}, 'unchanged validator tolerances')
        reasons = []
        if after['gripper_command'] != before['gripper_command'] or any(command[-1] != before['gripper_command'] for command in result['low_level_commands']):
            reasons.append('gripper_command_changed_unexpectedly')
        error = np.linalg.norm(measured_delta - delta)
        if error > (.0015 if branch == 'STOP' else .002):
            reasons.append('unintended_translation' if branch == 'STOP' else 'translation_error')
        if angle > 1.:
            reasons.append('unintended_rotation')
        require(result['execution_contract_reason'] == reasons and result['execution_contract_violation'] == bool(reasons), 'independent unchanged execution validator')
        summaries = {}
        for stage, native in (('before', before_native[-200:]), ('after', after_native[-200:])):
            contacts = [{'control': row['control'], 'index': row['index'], 'time_s': row['time_s'], **contact, 'class': classify(contact['geom_ids'], groups)} for row in native for contact in row['contacts'] if groups['robot'].intersection(contact['geom_ids'])]
            strong = [row for row in contacts if row['normal_force_N'] > .05]
            summaries[stage] = {'raw_robot_rows': len(contacts), 'strict_above_005N_rows': len(strong), 'first_raw': contacts[0] if contacts else None, 'first_strong': strong[0] if strong else None, 'max_normal_force_N': max((r['normal_force_N'] for r in contacts), default=0.), 'all_raw_robot_pairs': [list(pair) for pair in sorted({tuple(sorted(r['geom_names'])) for r in contacts})], 'all_strong_robot_pairs': [list(pair) for pair in sorted({tuple(sorted(r['geom_names'])) for r in strong})]}
        require(outcome['contact_summary'] == summaries, 'every raw/strict contact summary independently recomputed stage separately')
        if branch == 'MV_FWD':
            require(result == original_action, 'full FWD executor continuation exactly reproduces source')
        report[branch] = {'translation_delta_m': measured_delta.tolist(), 'nominal_translation_error_mm': float(error*1000), 'rotation_deg': angle, 'validator_violation': bool(reasons), 'tcp_to_cached_P_gain_mm': float((np.linalg.norm(np.asarray(before['tcp_xyz'])-fixed_point)-np.linalg.norm(np.asarray(after['tcp_xyz'])-fixed_point))*1000), 'contact_summary': summaries, 'source_exact_control_and_native_records': source_checks[branch], 'STOP_is_executed_hold_not_original_loop_termination': branch == 'STOP'}
    return {'status': 'pass', 'freeze': FREEZE, 'journal_sha256': sha(run / 'episodes.jsonl'), 'journal_records': sum(counts.values()), 'record_counts': dict(counts), 'prefix_controls': 1232, 'probe_controls': 56, 'native_integrations': 32200, 'native_stage_samples': 64400, 'captures': 168, 'separate_standard_settling_controls': 70, 'current_model_xml_sha256': base_model['xml_sha256'], 'outcomes': report, 'limits': ['stored hashes, exact source records, arrays and scalar arithmetic only; no dynamics/render/FK/replay rerun', 'current compiled model identity compared through recorded fingerprints, not independent recompilation', 'raw and strict threshold samples remain stage-separated; cached times are not continuous onset', 'one preselected boundary and one0.4s primitive per branch, no learned threshold or future-clearance claim', 'executed STOP is a hold diagnostic; original loop STOP terminates with no additional world']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--run', default='task2-pre22-counterfactual-run-01')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'outcomes'}, indent=2))
