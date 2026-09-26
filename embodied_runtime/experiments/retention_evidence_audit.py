"""Read-only independent checks of the sealed interaction diagnostic, without physics.

This does not import the collector, tracker or report being audited. Evaluator
labels are read only to check reported conclusions, never to correct sensors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def audit(source, replay, repository):
    source, replay, repository = map(Path, (source, replay, repository))
    checks = []

    def check(name, condition, **details):
        checks.append({'name': name, 'passed': bool(condition), **details})

    seal = read(source/'sensor-seal.json')
    hashes = {name: digest(source/name) == expected for name, expected in seal['sha256'].items()}
    check('all_sealed_sensor_artifacts', len(hashes) == 188 and all(hashes.values()),
          checked=len(hashes), failed=[name for name, ok in hashes.items() if not ok])
    manifest = read(source/'manifest.json')
    code_checks = {}
    for label, record in [('collection', manifest), ('replay', read(replay/'manifest.json'))]:
        code = record['code']
        failures = []
        for name, expected in code['source_sha256'].items():
            raw = subprocess.check_output(['git', '-C', str(repository), 'show', code['commit']+':'+name])
            if hashlib.sha256(raw).hexdigest() != expected:
                failures.append(name)
        code_checks[label] = {'commit': code['commit'], 'files': len(code['source_sha256']), 'failed': failures}
    check('manifest_source_hashes_match_frozen_git_objects',
          all(not item['failed'] for item in code_checks.values()), records=code_checks)
    check('frozen_protocol', digest(source/'protocol.md') == manifest['protocol_sha256'])
    archived_source = repository/'docs/evidence/privileged_reference/task2_valid_interaction_gate_failure.jsonl'
    check('archived_primitive_source', digest(archived_source) == manifest['source_sha256'])
    actions = [row['choice'] for row in map(json.loads, archived_source.read_text().splitlines())
               if row['kind'] == 'step'][:17]
    expected_actions = {'close': actions, 'open_hold': [*actions[:13], 'hold', *actions[14:]]}
    check('registered_single_primitive_intervention', manifest['actions'] == expected_actions)

    seed = read(source/'seed.json')
    frozen = read(source/'seed-frozen.json')
    check('frozen_seed_equals_sealed_seed', frozen['seed'] == seed and
          frozen['seed_file_sha256'] == digest(source/'seed.json'))
    check('seed_image_hash_chain', seed['image_sha256'] == digest(source/'seed-required.png') ==
          digest(source/'close/0013.png') == digest(source/'open_hold/0013.png'))
    controls = [json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()]
    lookup = {(r['arm'], r['step'], r['control']): r for r in controls}
    check('complete_unique_control_sequence', list(lookup) ==
          [(arm, step, control) for arm in ('close', 'open_hold') for step in range(17) for control in range(8)])
    first_close = lookup['close', 13, 0]['sensor']
    check('seed_frozen_before_any_close_control',
          frozen['wall_time_unix_s'] < first_close['wall_time_unix_s'] and
          frozen['sim_time_s'] == lookup['close', 13, 0]['before_sim_time_s'],
          frozen_wall_time_s=frozen['wall_time_unix_s'], first_close_wall_time_s=first_close['wall_time_unix_s'])
    analysis_seal = read(source/'sensor-analysis-seal.json')
    check('sensor_analysis_seal', digest(source/'sensor-analysis.json') == analysis_seal['sha256'] and
          analysis_seal['oracle_labels_read'] is False)
    check('seal_order_consistent_with_current_mtimes',
          seal['wall_time_unix_s'] <= (source/'evaluator-only/labels.json').stat().st_mtime <
          analysis_seal['wall_time_unix_s'],
          limitation='Local filesystem timestamps are corroboration, not tamper-evident history.')
    check('all_sensor_records_keep_unknown_holding_and_sample_times', all(
          r['sensor']['holding'] is None and r['sensor']['wrist_sample_sim_time_s'] is None and
          r['sensor']['returned_observation_sample_times_s'] is None for r in controls))
    durations = [r['sensor']['read_sim_time_s']-r['before_sim_time_s'] for r in controls]
    check('all_control_durations_50ms', np.allclose(durations, .05, rtol=0, atol=1e-12),
          minimum_s=min(durations), maximum_s=max(durations))
    check('native_jaw_command_schedule', all(r['sensor']['command'][6] ==
          (1.0 if r['arm'] == 'close' and r['step'] >= 13 else -1.0) for r in controls))
    equal = [
        {k: v for k, v in lookup['close', s, c]['sensor'].items() if k != 'wall_time_unix_s'} ==
        {k: v for k, v in lookup['open_hold', s, c]['sensor'].items() if k != 'wall_time_unix_s'}
        for s in range(13) for c in range(8)]
    check('common_prefix_all_sensor_fields_except_walltime_equal', all(equal), controls=len(equal))
    captures = read(source/'captures.json')
    common_images = [next(c['rgb_sha256'] for c in captures if c['arm'] == 'close' and c['after_step'] == s) ==
                     next(c['rgb_sha256'] for c in captures if c['arm'] == 'open_hold' and c['after_step'] == s)
                     for s in range(-1, 13)]
    check('all_14_common_prefix_rgb_hashes_equal', all(common_images))
    frame_lookup, failures = {}, []
    for c in captures:
        with np.load(source/c['artifact'], allow_pickle=False) as npz:
            f = {key: npz[key].copy() for key in npz.files}
        frame_lookup[c['arm'], c['capture_id']] = f
        if not (digest(source/c['artifact']) == c['artifact_sha256'] and
                digest(source/c['rgb_artifact']) == c['rgb_sha256'] and
                np.array_equal(f['rgb'], np.asarray(Image.open(source/c['rgb_artifact']))) and
                float(f['capture_sim_time']) == c['capture_read_sim_time_s'] and
                (c['after_step'] == -1 or c['capture_read_sim_time_s'] ==
                 lookup[c['arm'], c['after_step'], c['control']]['sensor']['read_sim_time_s'])):
            failures.append([c['arm'], c['capture_id']])
    check('capture_hash_rgb_array_and_read_time_consistency', not failures, captures=len(captures), failed=failures)
    max_encoder_difference = max(float(np.max(np.abs(np.asarray(r['sensor']['direct_gripper_qpos_m'])-
        r['sensor']['returned_observations']['robot0_gripper_qpos']))) for r in controls)

    # Independently recompute native LK from RGB with the published frozen parameters.
    import cv2
    check('opencv_frozen_version', cv2.__version__ == '4.11.0', actual=cv2.__version__)
    analysis = read(source/'sensor-analysis.json')
    flow_failures, projection_errors, membership, landmarks = [], [], [], {}
    for arm in ('close', 'open_hold'):
        landmarks[arm] = {}
        for seed_point in seed['points']:
            role = seed_point['role']
            rows = [r for r in analysis['arms'][arm] if r['role'] == role]
            p = np.asarray(seed_point['pixel_xy'], dtype=np.float32).reshape(1, 1, 2)
            alive = True
            for index, r in enumerate(rows):
                f = frame_lookup[arm, r['capture_id']]
                if index:
                    status = 'unknown_after_native_failure'
                    if alive:
                        previous = cv2.cvtColor(frame_lookup[arm, rows[index-1]['capture_id']]['rgb'], cv2.COLOR_RGB2GRAY)
                        current = cv2.cvtColor(f['rgb'], cv2.COLOR_RGB2GRAY)
                        settings = dict(winSize=(21,21), maxLevel=3, criteria=(3,30,.01), flags=0, minEigThreshold=.0001)
                        nxt, fs, _ = cv2.calcOpticalFlowPyrLK(previous, current, p, None, **settings)
                        back, bs = None, None
                        if nxt is not None and np.isfinite(nxt).all() and int(fs[0,0]) == 1:
                            back, bs, _ = cv2.calcOpticalFlowPyrLK(current, previous, nxt, None, **settings)
                        alive = bool(back is not None and np.isfinite(back).all() and int(bs[0,0]) == 1)
                        status = 'native_status_ok' if alive else 'native_failure'
                        if nxt is not None and np.isfinite(nxt).all() and not np.array_equal(nxt.reshape(2), r['point_pixel_index_xy']):
                            flow_failures.append([arm, role, index, 'point'])
                        if back is not None and int(bs[0,0]) == 1 and float(np.linalg.norm(back-p)) != r['forward_backward_residual_px']:
                            flow_failures.append([arm, role, index, 'residual'])
                        if alive:
                            p = nxt
                    if status != r['status']:
                        flow_failures.append([arm, role, index, 'status'])
                pixel = r['sample_pixel_xy']
                if pixel is not None:
                    x, y = pixel
                    k, t = f['intrinsics'], f['camera_to_world']
                    depth = float(f['depth_m'][y,x])
                    point = (t @ np.array([(x+.5-k[0,2])*depth/k[0,0],
                                         (y+.5-k[1,2])*depth/k[1,1], depth, 1.]))[:3]
                    projection_errors.append(float(np.max(np.abs(point-r['surface_point_world_m']))))
                    mask = np.load(source/f'evaluator-only/{arm}-{r["capture_id"]:04d}-bottle-mask.npy', allow_pickle=False)
                    on_bottle = bool(mask[y,x])
                else:
                    on_bottle = None
                membership.append({'arm': arm, 'role': role, 'capture_id': r['capture_id'], 'on_bottle': on_bottle})
            relevant = [r for r in membership if r['arm'] == arm and r['role'] == role]
            landmarks[arm][role] = {'frames': len(rows), 'on_bottle': sum(r['on_bottle'] is True for r in relevant),
                'first_off_bottle_capture': next((r['capture_id'] for r in relevant if r['on_bottle'] is False), None),
                'endpoint_displacement_mm': None if rows[-1]['surface_point_delta_m'] is None else
                    (1000*np.asarray(rows[-1]['surface_point_delta_m'])).tolist()}
    check('independent_LK_coordinates_status_and_residuals', not flow_failures, failed=flow_failures)
    check('independent_depth_backprojection', max(projection_errors) == 0,
          points=len(projection_errors), max_abs_error_m=max(projection_errors))

    labels = read(source/'evaluator-only/labels.json')
    label_lookup = {(r['arm'], r['after_step'], r['control']): r for r in labels}
    check('evaluator_state_dimensions_and_timestamps', all(len(r['state']) == 51 and
          r['state'][0] == r['sim_time_s'] and
          (r['after_step'] == -1 or r['sim_time_s'] == lookup[r['arm'],r['after_step'],r['control']]['sensor']['read_sim_time_s'])
          for r in labels), states=len(labels))
    summary = read(source/'evaluation-audit/summary.json')
    reported_landmarks_equal = True
    for arm in ('close', 'open_hold'):
        reported = summary['arms'][arm]
        for role, result in landmarks[arm].items():
            claim = reported['landmarks'][role]
            reported_landmarks_equal &= result['on_bottle'] == claim['on_bottle_including_seed']
            claimed_delta = claim['endpoint_surface_point_delta_m']
            reported_landmarks_equal &= (result['endpoint_displacement_mm'] is None if claimed_delta is None else
                np.array_equal(result['endpoint_displacement_mm'], np.asarray(claimed_delta)*1000))
        reported_landmarks_equal &= reported['oracle_bilateral_after_seed_controls'] == sum(
            r['valid_grasp_relation'] for r in labels if r['arm'] == arm and r['after_step'] >= 13)
    check('reported_landmark_and_relation_aggregates', reported_landmarks_equal)
    check('evaluator_and_sensor_summary_hash_chain',
          summary['oracle_labels_sha256'] == digest(source/'evaluator-only/labels.json') and
          summary['sensor_analysis_sha256'] == digest(source/'sensor-analysis.json') and
          summary['sensor_seal_sha256'] == digest(source/'sensor-seal.json') and
          summary['manifest_sha256'] == digest(source/'manifest.json') and
          summary['seed_sha256'] == digest(source/'seed.json'))
    for directory in ('evaluation', 'evaluation-audit'):
        artifact_hashes = read(source/directory/'artifacts.json')
        check(directory+'_artifact_hashes', all(digest(source/directory/p) == h for p,h in artifact_hashes.items()),
              checked=len(artifact_hashes))
    check('both_existing_reports_equal', all(digest(source/'evaluation'/name) == digest(source/'evaluation-audit'/name)
          for name in ('summary.json','membership.json','trajectory-contact-sheet.png','trajectory-sensors.png','first-cap-failure.png')))
    replay_manifest = read(replay/'manifest.json')
    replay_result = read(replay/'result.json')
    portable = read(repository/'docs/evidence/autonomous_research/interaction_observability_summary.json')
    check('portable_artifact_and_replay_anchors', all(digest(source/name) == expected for name,expected
          in portable['artifacts_sha256'].items()) and portable['replay']['result_sha256'] == digest(replay/'result.json'))
    width = portable['archived_width_counterexample']
    width_source = Path(width['source'])
    width_rows = [json.loads(line) for line in width_source.read_text().splitlines()]
    width_equal = digest(width_source) == width['source_sha256']
    for claimed in width['records']:
        actual = width_rows[claimed['source_record_seq']]['data']['actual']
        width_equal &= (actual['action'] == claimed['action'] and actual['controls'] == claimed['controls'] and
            actual['before']['finger_gap_mm'] == claimed['geometric_gap_before_mm'] and
            actual['after']['finger_gap_mm'] == claimed['geometric_gap_after_mm'] and
            actual['after']['contacts'] == claimed['contact_rows_after'] and
            actual['after']['bilateral_target_contact'] == claimed['bilateral_target_contact_after'])
    check('archived_empty_close_counterexample_source_and_rows', width_equal, records=[26,54])
    check('replay_source_hash_chain', replay_manifest['sensor_controls_sha256'] == digest(source/'sensors.jsonl') and
          replay_manifest['original_diagnostic_state_sha256'] == digest(source/'evaluator-only/labels.json'))
    check('recorded_replay_all_controls_exact_and_ordered', replay_result['controls'] == 272 and
          replay_result['all_272_states_exact'] and replay_result['max_state_abs_error'] == 0 and
          [(r['arm'],r['step'],r['control']) for r in replay_result['trace']] == list(lookup) and
          all(r['max_state_abs_error'] == 0 and r['sim_time_s'] ==
              lookup[r['arm'],r['step'],r['control']]['sensor']['read_sim_time_s'] for r in replay_result['trace']),
          limitation='Audits recorded replay evidence; does not rerun physics or recover unrecorded actual replay state arrays.')
    flicker = []
    for control in range(8):
        row = label_lookup['close', 16, control]
        if row['valid_grasp_relation']:
            continue
        contacts = [c for c in row['contacts'] if c['moving_target']]
        flicker.append({'step':16, 'control':control, 'bilateral_pad_relation':False,
            'both_physical_fingers_have_recorded_contact': all(any(f'finger{i}_' in c['hand'] for c in contacts) for i in (1,2)),
            'bottle_center_z_mm':row['bottle_center_mm'][2],
            'contacts':[{'hand':c['hand'], 'normal_force_N':c['normal_force_N']} for c in contacts]})
    return {'scope':'independent offline audit; no new physical execution', 'source':str(source), 'replay':str(replay),
        'all_checks_passed': all(c['passed'] for c in checks), 'checks':checks,
        'landmarks':landmarks, 'max_returned_vs_direct_finger_encoder_difference_mm':1000*max_encoder_difference,
        'bilateral_pad_flicker':flicker,
        'annotation_provenance':{'actor':read(source/'annotation-provenance-erratum.json')['actual_annotator'],
            'exact_model_identifier_recorded':False, 'exact_model_independently_verified':False,
            'note':'Assistant attribution is recorded by append-only erratum. Artifacts contain no model/session/tool-call record.'},
        'integrity_limits':['Hashes verify present bytes against present recorded anchors; no external notarization.',
            'seed-frozen.json is outside the 188-file sensor seal; its seed currently equals the sealed seed.json.',
            'Source review supports oracle separation; local timestamps alone cannot prove absence of out-of-band reads.',
            'Evaluator masks label visual rendered geometry, not complete physical support or collision geometry.',
            'Render/read time is not an asserted exact sample time for cached derived geometry.'],
        'input_sha256':{str(p):digest(p) for p in [source/'manifest.json',source/'sensor-seal.json',source/'seed-frozen.json',
            source/'sensor-analysis-seal.json',source/'annotation-provenance-erratum.json',replay/'manifest.json',replay/'result.json']}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--replay', required=True)
    parser.add_argument('--repository', default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.source, args.replay, args.repository)
    with Path(args.output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_checks_passed':result['all_checks_passed'], 'checks':len(result['checks']),
                      'failed':[r['name'] for r in result['checks'] if not r['passed']]}))
    if not result['all_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
