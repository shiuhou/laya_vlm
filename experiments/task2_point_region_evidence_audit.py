"""Independent stored POINT audit; no producer imports, model, processor or scene."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from task2_box_evidence_audit import canonical, read, require, sha

FREEZE = 'd4045496dc330529eb8f637bd46d556fc9bc0598'
FRAME = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'
PREFLIGHT = '34bac09d5a1170fe88f339c5896147944533b4b94f989d277762d2781a8aa498'
MODEL = '4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f'
SETTINGS = {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid',
            'temperature': 0., 'do_sample': False, 'verbose': False}
CONDITIONS = [{'condition': name, 'query': query, 'question': f'Point to: {query}.'}
              for name, query in [('whole', 'the wine bottle'), ('neck', 'the neck of the wine bottle')]]


def identity(array):
    return {'shape': list(array.shape), 'dtype': str(array.dtype),
            'bytes_sha256': hashlib.sha256(array.tobytes()).hexdigest()}


def journal(directory, expected_kinds):
    config, manifest = read(directory / 'resolved_config.yaml'), read(directory / 'manifest.json')
    rows, previous = [], None
    for index, line in enumerate((directory / 'episodes.jsonl').read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete journal lines')
        row = json.loads(line)
        require(row['seq'] == index and row['previous_record_id'] == previous, 'journal chain')
        require(canonical({k: v for k, v in row.items() if k != 'record_id'}) == row['record_id'], 'record hash')
        require(row['config_hash'] == canonical(config) == manifest['config_hash'], 'config identity')
        require(not rows or row['wall_time'] >= rows[-1]['wall_time'], 'journal time order')
        if row['kind'].endswith('_sealed'):
            require(sha(directory / row['data']['artifact']) == row['data']['sha256'], 'artifact seal')
        previous = row['record_id']
        rows.append(row)
    require([row['kind'] for row in rows] == expected_kinds, 'exact call/seal accounting')
    require(rows[0]['data']['resolved_config'] == config, 'initial config')
    reconstructed = dict(rows[0]['data']['manifest'])
    for row in rows:
        if row['kind'] == 'manifest_update':
            reconstructed.update(row['data'])
    require(reconstructed == manifest, 'manifest reconstruction')
    return rows, config, manifest


def audit(sources, producer):
    run = sources / 'task2-point-region-control-run-01'
    batch, request, manifest = journal(run, ['run_start', 'condition_intent', 'condition_complete',
                                            'condition_intent', 'condition_complete', 'termination'])
    require(request == read(run / 'request.json'), 'batch request/config')
    require(request['conditions'] == CONDITIONS and request['physical_gpu'] == '1'
            and request['planned_model_calls'] == 2 and request['fresh_process_per_condition']
            and request['seed'] == 1 and request['retries'] == 0, 'registered pair')
    preflight_path = Path(request['preflight'])
    require(sha(preflight_path) == request['preflight_sha256'] == PREFLIGHT, 'reviewed preflight')
    preflight = read(preflight_path)
    require(preflight['code'] == manifest['code'] and manifest['code']['commit'] == FREEZE
            and not manifest['code']['dirty_status'], 'clean reviewed code')
    require(preflight['status'] == 'pass' and preflight['settings'] == SETTINGS
            and preflight['conditions'] == CONDITIONS, 'preflight protocol')
    require(all(preflight[k] == 0 for k in ('model_constructions', 'model_calls', 'physics_calls', 'render_calls')),
            'processor-only preflight accounting')
    for name, expected in manifest['code']['source_sha256'].items():
        data = subprocess.check_output(['git', 'show', f'{FREEZE}:{name}'], cwd=producer)
        require(hashlib.sha256(data).hexdigest() == expected, 'frozen source ' + name)
    require(sha(run / 'protocol.md') == request['protocol_sha256'] == preflight['protocol_sha256']
            == '164e34359f6f83b9b568d484b7e007826d559c6b3a340bbe3c1c58a018a04ab3', 'protocol')
    review_path = sources / 'task2-point-region-control-run-01-review.json'
    review = read(review_path)
    require(review['freeze'] == FREEZE and review['preflight_sha256'] == PREFLIGHT
            and review['review_commit'] == 'e3672e756eeebefb17d7fcc6e1580fb5f077b538'
            and review['model_calls_before_launch'] == 0 and review['physical_gpu'] == '1'
            and review['wall_time_unix_s'] < batch[0]['wall_time'], 'prospective review before run')
    require(sha(sources / 'task2-point-region-control-run-01-review.md') == review['review_sha256'], 'review text')
    frame_path = sources / 'interaction-observability-paired-01/close/0000.npz'
    require(sha(frame_path) == preflight['source_frame_sha256'] == FRAME, 'source frame')
    with np.load(frame_path, allow_pickle=False) as saved:
        frame = {k: saved[k] for k in saved.files}
    require(frame['rgb'].shape == (384, 384, 3) and frame['rgb'].dtype == np.uint8, 'original RGB schema')
    model = preflight['model']
    require(canonical(model['files_sha256']) == model['content_id'] == MODEL, 'recorded checkpoint identity')
    # Static vocabulary lookup validates every emitted ID without constructing a tokenizer.
    vocab = {}
    for name in ('vocab.json', 'added_tokens.json'):
        path = Path(model['path']) / name
        require(sha(path) == model['files_sha256'][name], 'pinned static vocabulary')
        vocab.update({value: key for key, value in read(path).items()})
    for condition, reference in zip(CONDITIONS, preflight['description_provenance']):
        directory = Path(reference['directory'])
        require(sha(directory / 'manifest.json') == reference['manifest_sha256']
                and sha(directory / 'resolved_config.yaml') == reference['resolved_config_sha256'], 'original BOX config seal')
        original, config = read(directory / 'manifest.json'), read(directory / 'resolved_config.yaml')
        require(original['model_config'] == preflight['source_model_config'] and original['dtype'] == 'torch.bfloat16'
                and original['model']['content_id'] == MODEL and config['settings'] == SETTINGS, 'unchanged model/config')
        require(config['question'] == reference['original_question']
                == f"Locate a single instance that matches the following description: {condition['query']}.", 'fixed description')
    conditions, loaded_rows, process_ids, child_rows = [], [], [], []
    for index, condition in enumerate(CONDITIONS):
        name = condition['condition']
        directory = run / name
        rows, config, child = journal(directory, ['run_start', 'rgb_input_sealed', 'manifest_update',
            'native_input_sealed', 'native_input_sealed', 'call_started', 'generation_return_sealed',
            'sensor_result_sealed', 'termination'])
        require(child['code'] == manifest['code'], 'condition code freeze')
        require(config == {**condition, 'settings': SETTINGS, 'model_call_budget': 1, 'seed': 1,
                           'request_sha256': sha(run / 'request.json'), 'source_frame_sha256': FRAME,
                           'protocol_sha256': request['protocol_sha256']}, 'condition configuration')
        require(batch[1 + index * 2]['data'] == {'ordinal': index, **condition}, 'fixed intent')
        require(batch[1 + index * 2]['wall_time'] < rows[0]['wall_time'] < rows[-1]['wall_time']
                < batch[2 + index * 2]['wall_time'], 'fresh condition chronology')
        require(rows[5]['data'] == {'model_call_ordinal': 1, 'timeout_s': 300}, 'one native call')
        require(rows[7]['data']['evaluator_opened'] is False, 'sensor boundary')
        require(rows[-1]['data'] == {'reason': 'fixed_condition_complete', 'status': 'admitted_sensor_point',
                'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0}, 'condition accounting')
        loaded = child['loaded']
        require(child['model'] == model and loaded['model_config'] == preflight['source_model_config'], 'exact loaded config')
        require(loaded['dtype'] == loaded['parameter_dtype'] == 'torch.bfloat16' and not loaded['model_training']
                and loaded['tokenizer_model_max_length'] == 16384 and loaded['eos_token_id'] == 151645
                and loaded['physical_gpu'] == '1', 'BF16/eval/tokenizer/GPU')
        require(loaded['model_config']['value']['text_config']['block_size'] == 6, 'native chunk default')
        rgb = np.load(directory / 'rgb-input.npy', allow_pickle=False)
        require(identity(rgb) == identity(frame['rgb']), 'full original RGB bytes')
        native = read(directory / 'native-input.json')
        require(native == preflight['inputs'][index] and native['rgb'] == identity(rgb), 'all native metadata preflight equality')
        require(all(native[k] == v for k, v in condition.items()), 'native fixed question')
        require(native['image_grid_hws'] == [[28, 28]] and native['pixel_values_original_dtype'] == 'torch.bfloat16', 'native grid/dtype')
        require(len(native['input_token_ids']) == (229, 232)[index]
                and native['attention_mask'] == [[1] * len(native['input_token_ids'])], 'input IDs/mask lengths')
        with np.load(directory / 'native-input.npz', allow_pickle=False) as saved:
            require(saved.files == ['pixel_values_float32'], 'native array schema')
            pixels = saved['pixel_values_float32']
        require(identity(pixels) == native['pixel_values_float32'] == preflight['inputs'][0]['pixel_values_float32'], 'all native pixels')
        require(pixels.dtype == np.float32 and pixels.shape == (784, 3, 14, 14)
                and np.isfinite(pixels).all() and np.all((pixels.view(np.uint32) & 65535) == 0), 'exact BF16 representation')
        raw, sensor = read(directory / 'generation-return.json'), read(directory / 'sensor-result.json')
        tokens = raw['observed_decoded_token_sequences']
        require(len(tokens) == len(tokens[0]) == 1, 'one generated sequence')
        ids = tokens[0][0]
        decoded = ''.join(vocab[i] for i in ids).replace('Ġ', ' ')
        require(decoded == raw['raw_response'] == sensor['raw_output'] and raw['raw_response_type'] == 'str'
                and raw['returned_value_repr'] == repr(decoded), 'raw token/return identity')
        require(raw['latency_to_return_s'] > 0, 'recorded latency')
        limit = min(256, 16384 - len(native['input_token_ids']))
        expected_audit = {'actual_generated_token_ids': ids, 'actual_generated_token_count': len(ids),
            'input_token_count': len(native['input_token_ids']), 'model_max_length': 16384,
            'eos_token_id': 151645, 'effective_limit': limit, 'terminal_eos_observed': ids[-1] == 151645,
            'length_limit_reached': len(ids) >= limit, 'complete_generation': ids[-1] == 151645,
            'truncation_status': 'eos_terminated' if ids[-1] == 151645 else 'no_terminal_eos'}
        require(sensor['generation_audit'] == expected_audit and len(ids) == (10, 13)[index]
                and ids[-1] == 151645 and len(ids) < limit, 'strict EOS and below-limit admission')
        match = re.fullmatch(r'<ref>' + re.escape(condition['query']) + r'</ref><box><(\d+)><(\d+)></box><\|im_end\|>', decoded)
        require(match is not None, 'exact one native POINT')
        normalized = [int(v) for v in match.groups()]
        continuous = [v / 1000 * 384 for v in normalized]
        x, y = [int(np.floor(v)) for v in continuous]
        require(0 <= x < 384 and 0 <= y < 384, 'in-frame without clamp')
        require(sensor['parsed'] == {'status': 'single_point', 'points': [{'normalized': normalized,
            'continuous_xy': continuous, 'sample_pixel_xy': [x, y]}], 'boxes': [], 'empty_count': 0,
            'invalid': [], 'confidence': None}, 'native normalized/floor parsing')
        z = float(frame['depth_m'][y, x])
        require(np.isfinite(z) and .01 <= z <= 5, 'finite source depth')
        k, t = frame['intrinsics'], frame['camera_to_world']
        camera = [(x + .5 - float(k[0, 2])) * z / float(k[0, 0]),
                  (y + .5 - float(k[1, 2])) * z / float(k[1, 1]), z, 1.]
        world = [sum(float(t[i, j]) * camera[j] for j in range(4)) for i in range(3)]
        point = sensor['point']
        residual = float(np.max(np.abs(np.asarray(world) - point['position_world_m'])))
        require(residual <= 2e-15 and np.isfinite(point['position_world_m']).all(), 'independent stored K/T scalar equation')
        require(point['sample_pixel_xy'] == [x, y] and point['sample_pixel_center_xy'] == [x + .5, y + .5]
                and point['depth_m'] == z and point['admission'] == 'fresh_single_POINT_EOS_finite_depth_not_identity_or_safety_verification', 'point fields')
        require(sensor['status'] == 'admitted_sensor_point' and sensor['reason'] is None
                and sensor['semantic_target_identity_verified'] is False
                and all(sensor[k] is None for k in ('resolved_depth_ownership', 'semantic_confidence', 'grasp_quality',
                                                   'cached_rgb_sample_time_s', 'cached_depth_sample_time_s')), 'admission semantic limits')
        require(sensor['source_frame_sha256'] == FRAME and sensor['capture_read_time_s'] == .5
                and sensor['calibration'] == {k: identity(frame[k]) for k in ('intrinsics', 'camera_to_world')}, 'source calibration')
        require(batch[2 + index * 2]['data'] == {'condition': name, 'status': sensor['status'],
                'sensor_sha256': sha(directory / 'sensor-result.json')}, 'batch sensor seal')
        conditions.append({'condition': name, 'status': sensor['status'], 'sensor_sha256': sha(directory / 'sensor-result.json'),
            'raw_return_sha256': sha(directory / 'generation-return.json'), 'journal_sha256': sha(directory / 'episodes.jsonl'),
            'native_input_sha256': sha(directory / 'native-input.json'), 'pid': child['pid'],
            'actual_generated_token_ids': ids, 'actual_generated_token_count': len(ids),
            'input_token_count': len(native['input_token_ids']), 'effective_limit': limit, 'terminal_eos': True,
            'point': point, 'maximum_stored_projection_equation_residual_m': residual})
        loaded_rows.append(loaded)
        process_ids.append(child['pid'])
        child_rows.append(rows)
    require(loaded_rows[0] == loaded_rows[1] and len(set(process_ids)) == 2, 'matched fresh environments/processes')
    require(child_rows[0][-1]['wall_time'] < child_rows[1][0]['wall_time'], 'sequential fresh calls')
    require(batch[-1]['data'] == {'reason': 'fixed_pair_complete', 'conditions': [batch[2]['data'], batch[4]['data']],
        'model_calls': 2, 'retries': 0, 'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False}, 'batch accounting')
    evaluation = run / 'evaluation'
    for name, digest in read(evaluation / 'artifacts.json').items():
        require(sha(evaluation / name) == digest, 'evaluator artifact')
    start = read(evaluation / 'evaluation-start.json')
    sensor_hashes = {c['condition']: c['sensor_sha256'] for c in conditions}
    require(start == {'source_journal_sha256': sha(run / 'episodes.jsonl'), 'sensor_sha256': sensor_hashes,
                      'labels_opened': False}, 'evaluator bound to complete pair before labels')
    proxy = read(evaluation / 'proxy-analysis.json')
    mask_path = sources / 'interaction-observability-paired-01/evaluator-only/close-0000-bottle-mask.npy'
    require(sha(mask_path) == proxy['mask_sha256'] == '2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747', 'whole bottle proxy')
    mask = np.load(mask_path, allow_pickle=False)
    require(mask.shape == (384, 384) and mask.dtype == np.bool_, 'proxy schema')
    for condition, result, point in zip(CONDITIONS, proxy['conditions'], conditions):
        x, y = point['point']['sample_pixel_xy']
        neighbors = [bool(mask[yy, xx]) if 0 <= yy < 384 and 0 <= xx < 384 else False
                     for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)]
        stratum = 'proxy_interior' if all(neighbors) else 'proxy_boundary_band' if any(neighbors) else 'proxy_exterior'
        require(result == {**condition, 'sensor_status': 'admitted_sensor_point', 'sample_pixel_xy': [x, y],
            'whole_bottle_rendered_proxy_membership': bool(mask[y, x]), 'proxy_stratum': stratum,
            'resolved_depth_ownership': None, 'neck_membership': None, 'grasp_quality': None}, 'independent evaluator membership')
        point['whole_bottle_rendered_proxy_membership'] = bool(mask[y, x])
        point['proxy_stratum'] = stratum
    require(proxy['actual_rgb_inspection'].startswith('pending separate'), 'original evaluator not rewritten')
    visual = read(run / 'visual-inspection.json')
    require(visual['figure_sha256'] == sha(evaluation / 'actual-rgb-points.png') and visual['source_frame_sha256'] == FRAME
            and visual['wall_time_unix_s'] > batch[-1]['wall_time'] and visual['input_is_full_uncropped_RGB']
            and visual['admission_changed'] is False and visual['point_selected_for_execution'] is False
            and all(visual[k] is None for k in ('resolved_depth_ownership', 'semantic_neck_truth_label', 'grasp_quality')), 'separate bounded visual receipt')
    require([(v['condition'], v['sample_pixel_xy']) for v in visual['conditions']]
            == [(c['condition'], c['point']['sample_pixel_xy']) for c in conditions], 'visual marker identities')
    docs = producer / 'docs/evidence/autonomous_research'
    portable_path = docs / 'task2_point_region_control_summary.json'
    portable = read(portable_path)
    require(portable['raw_directory'] == str(run) and portable['freeze'] == FREEZE
            and portable['prospective_review'] == review and portable['visual_inspection'] == visual, 'portable provenance/visual receipt')
    require([portable[k] for k in ('model_calls', 'model_processes', 'retries', 'physics_calls', 'render_calls', 'physical_gpu')]
            == [2, 2, 0, 0, 0, '1'], 'portable accounting')
    for name, digest in portable['artifacts_sha256'].items():
        require(sha(run / name) == digest, 'portable raw artifact seal')
    require(set(portable['artifacts_sha256']) == {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()}, 'complete portable artifact inventory')
    for name, digest in portable['sibling_artifacts_sha256'].items():
        require(sha(sources / name) == digest, 'portable sibling seal')
    for condition, row, result in zip(CONDITIONS, portable['conditions'], proxy['conditions']):
        directory = run / condition['condition']
        child = read(directory / 'manifest.json')
        require(row == {'condition': condition['condition'], 'pid': child['pid'],
            'config': read(directory / 'resolved_config.yaml'), 'native_input': read(directory / 'native-input.json'),
            'raw_return': read(directory / 'generation-return.json'), 'sensor': read(directory / 'sensor-result.json'),
            'loaded': child['loaded'], 'evaluation': result}, 'complete portable condition equality')
    require(sha(docs / 'task2_point_region_control_rgb.png') == sha(evaluation / 'actual-rgb-points.png'), 'portable figure byte identity')
    return {'status': 'pass', 'source_admission': 'pass', 'freeze': FREEZE, 'raw_directory': str(run),
        'preflight_sha256': PREFLIGHT, 'source_frame_sha256': FRAME, 'model_content_id': MODEL,
        'journal_sha256': sha(run / 'episodes.jsonl'), 'journal_records_checked': sum(map(len, child_rows)) + len(batch),
        'frozen_source_files_checked': len(manifest['code']['source_sha256']), 'model_calls': 2,
        'fresh_processes': 2, 'physical_gpu': '1', 'conditions': conditions,
        'sensor_sha256': sensor_hashes, 'proxy_sha256': sha(evaluation / 'proxy-analysis.json'),
        'portable_summary_sha256': sha(portable_path), 'figure_sha256': sha(evaluation / 'actual-rgb-points.png'),
        'producer_visual_receipt_sha256': sha(run / 'visual-inspection.json'),
        'limits': ['stored arrays, hashes, static vocabulary and scalar K/T equations only; no model, tokenizer, processor, physics or render rerun',
                   'checkpoint recorded identity map verified; weight bytes not reread',
                   'evaluator start binds both sensor hashes and completed batch journal; its JSON contains no wall-clock timestamp',
                   'POINT uses floor raster containment then pixel center +0.5, not LK nearest-index association',
                   'whole-bottle proxy membership does not establish neck truth, depth ownership, confidence or grasp quality',
                   'visual interpretation is separately reviewed in the accompanying Markdown receipt']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--producer', type=Path, default=Path('/home/junhongli/projects/laya-offline-wrist-history'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.producer)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
