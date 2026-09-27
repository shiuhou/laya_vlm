"""Audit the four saved cold POINT observations without models or processors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import numpy as np

import task2_point_region_evidence_audit as old

read, sha, require, identity = old.read, old.sha, old.require, old.identity
FREEZE = '8cc19ebff9cec07eba4f416d35a157445b60f554'
PREFLIGHT = '366b576db8398de8c51425f0e45a3cb1e5eda732e1eeefc677e53aeb8586308a'
REVIEW = '0538793b32fb7bfaff626fa143e932d2a0b745a6262f8402b968a29c8fa49c7e'
PROTOCOL = '856014997b0b0ffd23dcb1c7b0a641d2b669358cd5310c76cd3208361ab0852e'
ORDER = ('present-postevent', 'away-postevent', 'away-prelift', 'present-prelift')


def parse_observed(text):
    """Independent syntax/arithmetic check for the actually observed return forms."""
    require(text.startswith('<ref>the wine bottle</ref>') and text.endswith('<|im_end|>'), 'native reference and terminal text')
    bodies = re.findall(r'<box>([^/]+)</box>', text)
    require(len(bodies) == text.count('<box>') == text.count('</box>'), 'balanced observed grounding bodies')
    points, boxes, invalid = [], [], []
    for body in bodies:
        require(re.fullmatch(r'(?:<\d+>){2}|(?:<\d+>){4}', body) is not None, 'observed numeric point/box syntax')
        values = list(map(int, re.findall(r'\d+', body)))
        require(all(0 <= n <= 1000 for n in values), 'observed normalized range')
        coordinates = [n / 1000 * 384 for n in values]
        if len(values) == 2:
            require(all(0 <= n < 384 for n in coordinates), 'observed point in frame')
            points.append({'normalized': values, 'continuous_xy': coordinates,
                           'sample_pixel_xy': [int(np.floor(n)) for n in coordinates]})
        elif values[0] < values[2] and values[1] < values[3]:
            boxes.append({'normalized': values, 'continuous_xyxy': coordinates})
        else:
            invalid.append(body)
    require(len(points) == 1 and (not boxes and not invalid or len(boxes) == len(invalid) == 1), 'retained actual return shapes')
    status = 'malformed' if invalid else 'single_point'
    return {'status': status, 'points': points, 'boxes': boxes, 'empty_count': 0, 'invalid': invalid, 'confidence': None}


def audit(run):
    batch, request, manifest = old.journal(run, ['run_start', *[k for _ in ORDER for k in ('condition_intent', 'condition_complete')], 'termination'])
    require(request == read(run / 'request.json') and request['conditions'] == list(ORDER)
            and request['planned_model_calls'] == 4 and request['fresh_process_per_condition']
            and request['seed'] == 1 and request['retries'] == 0 and request['physical_gpu'] == '2', 'fixed four cold calls')
    preflight_path = Path(request['preflight'])
    require(sha(preflight_path) == request['preflight_sha256'] == PREFLIGHT
            and sha(run / 'review.json') == request['review_sha256'] == REVIEW
            and sha(run / 'protocol.md') == request['protocol_sha256'] == PROTOCOL, 'exact prospective inputs')
    preflight = read(preflight_path)
    require(manifest['code'] == preflight['code'] and manifest['code']['commit'] == FREEZE
            and manifest['code']['dirty_status'] == '' and manifest['versions'] == preflight['versions'], 'executed clean freeze and archived model environment')
    require(preflight['source']['original_matrix_status'] == 'interrupted_incomplete'
            and preflight['source']['source_admission_sha256'] == request['source_admission_sha256']
            == '57fa52a1ba5ffff73e7e197bbe352fe5f83209397c8cb972736cea389f0d7e42', 'composite source boundary retained')
    model = preflight['model']
    require(old.canonical(model['files_sha256']) == model['content_id'] == old.MODEL, 'recorded checkpoint content identity')
    vocab = {}
    for name in ('vocab.json', 'added_tokens.json'):
        path = Path(model['path']) / name
        require(sha(path) == model['files_sha256'][name], 'static vocabulary bytes')
        vocab.update({v: k for k, v in read(path).items()})
    conditions, processes, loaded_states, intervals = [], [], [], []
    for index, name in enumerate(ORDER):
        directory = run / name
        rows, config, child = old.journal(directory, ['run_start', 'rgb_input_sealed', 'manifest_update',
            'native_input_sealed', 'native_input_sealed', 'call_started', 'generation_return_sealed', 'sensor_result_sealed', 'termination'])
        source = preflight['source']['images'][index]
        require(child['code'] == manifest['code'] and child['versions'] == preflight['versions'], 'cold worker code/environment')
        require(config == {'case_id': name, 'question': 'Point to: the wine bottle.', 'image_source': source,
            'settings': old.SETTINGS, 'seed': 1, 'model_call_budget': 1, 'request_sha256': sha(run / 'request.json')}, 'case input/configuration')
        require(batch[1 + 2 * index]['data'] == {'ordinal': index, 'case_id': name}
                and batch[1 + 2 * index]['wall_time'] < rows[0]['wall_time'] < rows[-1]['wall_time'] < batch[2 + 2 * index]['wall_time'], 'ordered cold condition chronology')
        require(rows[5]['data'] == {'model_call_ordinal': 1, 'timeout_s': 300}
                and rows[7]['data']['evaluator_opened'] is False, 'one generation and raw-before-sensor seal')
        loaded = child['loaded']
        require(child['model'] == model and loaded['model_config'] == preflight['source_model_config']
                and loaded['dtype'] == loaded['parameter_dtype'] == 'torch.bfloat16' and loaded['model_training'] is False
                and loaded['tokenizer_model_max_length'] == 16384 and loaded['eos_token_id'] == 151645
                and loaded['physical_gpu'] == '2', 'unchanged checkpoint/BF16/eval/tokenizer/GPU')
        path = Path(preflight['source']['source_root']) / source['directory'] / source['artifact']
        require(sha(path) == source['artifact_sha256'], 'actual selected sensor image hash')
        with np.load(path, allow_pickle=False) as archive:
            rgb = archive['rgb']
        saved_rgb = np.load(directory / 'rgb-input.npy', allow_pickle=False)
        require(identity(saved_rgb) == identity(rgb) and saved_rgb.shape == (384, 384, 3) and saved_rgb.dtype == np.uint8, 'all original full RGB bytes')
        native = read(directory / 'native-input.json')
        require(native == preflight['inputs'][index] and native['rgb'] == identity(rgb)
                and native['condition'] == name and native['question'] == 'Point to: the wine bottle.', 'exact actual processor metadata')
        require(len(native['input_token_ids']) == 229 and native['attention_mask'] == [[1] * 229]
                and native['image_grid_hws'] == [[28, 28]] and native['pixel_values_original_dtype'] == 'torch.bfloat16', 'actual native input token/grid schema')
        with np.load(directory / 'native-input.npz', allow_pickle=False) as archive:
            require(archive.files == ['pixel_values_float32'], 'saved native tensor whitelist')
            pixels = archive['pixel_values_float32']
        require(identity(pixels) == native['pixel_values_float32'] and pixels.shape == (784, 3, 14, 14)
                and pixels.dtype == np.float32 and np.isfinite(pixels).all()
                and np.all((pixels.view(np.uint32) & 65535) == 0), 'exact saved BF16-as-float32 input tensor')
        raw, sensor = read(directory / 'generation-return.json'), read(directory / 'sensor-result.json')
        sequences = raw['observed_decoded_token_sequences']
        require(len(sequences) == len(sequences[0]) == 1, 'one raw decoded token sequence')
        ids = sequences[0][0]
        decoded = ''.join(vocab[token] for token in ids).replace('Ġ', ' ')
        require(decoded == raw['raw_response'] == sensor['raw_output'] and raw['raw_response_type'] == 'str'
                and raw['returned_value_repr'] == repr(decoded) and 0 < raw['latency_to_return_s'] < 300, 'every emitted token and raw return')
        expected_audit = {'actual_generated_token_ids': ids, 'actual_generated_token_count': len(ids),
            'input_token_count': 229, 'model_max_length': 16384, 'eos_token_id': 151645, 'effective_limit': 256,
            'terminal_eos_observed': True, 'length_limit_reached': False, 'complete_generation': True, 'truncation_status': 'eos_terminated'}
        require(ids[-1] == 151645 and len(ids) == (10, 22, 22, 10)[index]
                and sensor['generation_audit'] == expected_audit, 'actual complete below-limit generations')
        parsed = parse_observed(decoded)
        admitted = parsed['status'] == 'single_point'
        p = parsed['points'][0]
        expected_point = {'normalized': p['normalized'], 'continuous_xy': p['continuous_xy'], 'pixel_index_xy': p['sample_pixel_xy']} if admitted else None
        expected_sensor = {'raw_output': decoded, 'generation_audit': expected_audit, 'parsed': parsed,
            'status': 'admitted_rgb_point' if admitted else 'not_admitted', 'reason': None if admitted else 'malformed',
            'point': expected_point, 'semantic_target_identity_verified': False, 'semantic_confidence': None, 'holding': None, 'depth_read': False}
        require(sensor == expected_sensor, 'strict full-return parsing and no first-point salvage')
        require(rows[-1]['data'] == {'reason': 'fixed_rgb_point_condition_complete', 'status': sensor['status'],
            'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0}, 'case termination and no retry')
        require(batch[2 + 2 * index]['data'] == {'case_id': name, 'status': sensor['status'],
            'sensor_sha256': sha(directory / 'sensor-result.json')}, 'batch sensor linkage')
        conditions.append({'case_id': name, 'pid': child['pid'], 'pgid': child['pgid'],
            'journal_sha256': sha(directory / 'episodes.jsonl'), 'sensor_sha256': sha(directory / 'sensor-result.json'),
            'raw_return_sha256': sha(directory / 'generation-return.json'), 'native_input_sha256': sha(directory / 'native-input.json'),
            'raw_output': decoded, 'token_count': len(ids), 'status': sensor['status'], 'reason': sensor['reason'],
            'point': sensor['point'], 'parsed_candidates_not_admitted_separately': parsed,
            'all_RGB_and_processor_tensor_bytes_exact': True, 'all_emitted_ids_checked_against_static_vocabulary': True})
        processes.append(child['pid'])
        loaded_states.append(loaded)
        intervals.append((rows[0]['wall_time'], rows[-1]['wall_time']))
    require(len(set(processes)) == 4 and all(loaded == loaded_states[0] for loaded in loaded_states), 'four distinct cold processes and equal loaded environments')
    require(all(a[1] < b[0] for a, b in zip(intervals, intervals[1:])), 'sequential fresh process executions')
    require(batch[-1]['data'] == {'reason': 'four_fixed_cold_rgb_points_complete',
        'conditions': [batch[i]['data'] for i in (2, 4, 6, 8)], 'model_calls': 4, 'retries': 0,
        'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False}, 'complete four-case seal before interpretation')
    return {'status': 'PASS', 'freeze': FREEZE, 'raw_directory': str(run), 'preflight_sha256': PREFLIGHT,
        'prospective_review_sha256': REVIEW, 'journal_sha256': sha(run / 'episodes.jsonl'),
        'model_calls': 4, 'fresh_processes': 4, 'physical_gpu': '2', 'retries': 0,
        'conditions': conditions, 'new_model_processor_tokenizer_physics_render_LK_calls_during_audit': 0,
        'limits': ['Both away raw strings contain a point, a valid box and a degenerate box. Strict full-return status remains malformed; the first point is not salvaged.',
            'Admitted points are RGB-coordinate syntax observations, not independently verified semantic identity, holding or execution targets.',
            'Static vocabulary and recorded checkpoint identity were checked; no model or tokenizer was constructed and weight bytes were not reread.',
            'Actual image/point semantic interpretation is separately owned by root; no depth/calibration/labels used in this audit.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'conditions'}, indent=2))
