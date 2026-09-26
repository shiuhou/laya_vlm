"""Audit the sealed rejected neck query from bytes only; no model or geometry calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from task2_box_evidence_audit import canonical, read, require, sha

FREEZE = 'f1cae7c9160e31d2439683a7818c339b6f854dca'
QUESTION = 'Locate a single instance that matches the following description: the neck of the wine bottle.'


def audit(sources, checkpoint):
    run = sources / 'task2-neck-box-support-run-01'
    config, manifest = read(run / 'resolved_config.yaml'), read(run / 'manifest.json')
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean reviewed freeze')
    required_source = {
        'embodied_runtime/experiments/task2_box_support.py': '8a8d7d828b4b2f65593975cb0378e5b4e7828c1e27ae432d6ca3bfdae3f179f1',
        'embodied_runtime/experiments/task2_neck_box_support.py': 'c194386706b69519f1b68b275fde1e011c60f7248c99b1d9a080968ce18e38c4'}
    require(all(manifest['code']['source_sha256'][p] == h for p, h in required_source.items()), 'reviewed wrapper and core')
    require(manifest['environment'] == {'CUDA_VISIBLE_DEVICES': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}, 'actual authorized GPU1 and offline settings')
    require(manifest['dtype'] == 'torch.bfloat16' and manifest['gpu'] == 'NVIDIA GeForce RTX 4090', 'fixed dtype and GPU type')
    require(manifest['model']['content_id'] == canonical(manifest['model']['files_sha256']) == config['expected_model_content_id'] == '4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f', 'recorded checkpoint map')
    require(config['question'] == QUESTION and config['model_call_budget'] == 1 and config['timeout_s'] == 300, 'fixed question and budget')
    require(config['settings'] == {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid', 'temperature': 0., 'do_sample': False, 'verbose': False}, 'unchanged native generation settings')
    require(sha(run / 'protocol.md') == config['protocol_sha256'] == '1f96645a8e951ff509850cbe9cd1550b7b61857835206d4219e843695319497e', 'reviewed protocol')
    rows, previous = [], None
    for index, line in enumerate((run / 'episodes.jsonl').read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete record')
        row = json.loads(line)
        require(row['seq'] == index and row['previous_record_id'] == previous, 'journal order')
        require(canonical({k: v for k, v in row.items() if k != 'record_id'}) == row['record_id'], 'record hash')
        require(row['config_hash'] == canonical(config), 'record config hash')
        require(not rows or row['wall_time'] >= rows[-1]['wall_time'], 'wall-time order')
        rows.append(row)
        previous = row['record_id']
    require([r['kind'] for r in rows] == ['run_start', 'manifest_update', 'rgb_input_sealed', 'manifest_update', 'call_started', 'generation_return_sealed', 'model_output_sealed', 'termination'], 'one call; raw return sealed before parser; no sensor/evaluator')
    reconstructed = dict(rows[0]['data']['manifest'])
    for row in rows:
        if row['kind'] == 'manifest_update':
            reconstructed.update(row['data'])
        if row['kind'].endswith('_sealed'):
            require(sha(run / row['data']['artifact']) == row['data']['sha256'], 'sealed artifact bytes')
    require(reconstructed == manifest, 'final manifest reconstructs from journal')
    require(rows[-1]['data'] == {'reason': 'grounding_not_admitted', 'model_calls': 1, 'physics_calls': 0, 'renders': 0, 'retries': 0}, 'terminal rejection and counts')
    for name in ('sensor-representation.json', 'evaluation'):
        require(not (run / name).exists(), 'no sensor extraction or evaluator after rejection')
    preflight_path = sources / 'task2-neck-box-support-processor-preflight-03.json'
    require(sha(preflight_path) == '548c206d665f131c5bc9df121850b55f7ab03dde12633d82aa3da688e809cbcc', 'exact preflight receipt')
    preflight = read(preflight_path)
    require(preflight['code'] == manifest['code'] and preflight['model_calls'] == preflight['model_constructions'] == 0, 'preflight clean identity and zero model counts')
    call = rows[4]['data']
    require(call['question'] == preflight['question'] == QUESTION and call['input_token_ids'] == preflight['input_token_ids'], 'all actual input IDs match exact-question preflight')
    require(call['image_grid_hws'] == preflight['serialized_image_grid_hws'] == [[28, 28]], 'actual grid')
    require(call['pixel_shape'] == [784, 3, 14, 14] and call['pixel_dtype'] == 'torch.bfloat16', 'actual model image tensor schema')
    baseline_journal = sources / 'task2-box-support-run-02/episodes.jsonl'
    require(sha(baseline_journal) == '51dd621269c6da151c39e9b1bd9b0cdf15a890eb2e4af28a59caaea065201a3b', 'unchanged sealed object-level journal')
    baseline_call = next(row['data'] for row in map(json.loads, baseline_journal.read_text().splitlines()) if row['kind'] == 'call_started')
    require(all(call[key] == baseline_call[key] for key in ('image_grid_hws', 'pixel_shape', 'pixel_dtype', 'pixel_bytes_sha256')), 'identical processed BF16 image fingerprint to object-level condition')
    frame_path = sources / 'interaction-observability-paired-01/close/0000.npz'
    require(sha(frame_path) == config['source_frame_sha256'] == preflight['source_frame_sha256'] == '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969', 'fixed original source')
    with np.load(frame_path, allow_pickle=False) as frame:
        original_rgb = frame['rgb']
    rgb = np.load(run / 'rgb-input.npy', allow_pickle=False)
    require(rgb.dtype == original_rgb.dtype and rgb.shape == original_rgb.shape and rgb.tobytes() == original_rgb.tobytes(), 'original RGB bytes')
    require(hashlib.sha256(rgb.tobytes()).hexdigest() == rows[2]['data']['rgb_bytes_sha256'], 'RGB payload seal')
    model, returned = read(run / 'model-output.json'), read(run / 'generation-return.json')
    raw = returned['raw_response']
    require(returned['raw_response_type'] == 'str' and returned['returned_value_repr'] == repr(raw) and model['raw_output'] == raw, 'complete unmodified response')
    observed = returned['observed_decoded_token_sequences']
    require(len(observed) == len(observed[0]) == 1, 'one actual decoded sequence')
    tokens, generation = observed[0][0], model['generation_audit']
    require(tokens == generation['actual_generated_token_ids'] and len(tokens) == generation['actual_generated_token_count'] == 260, 'all actual generated IDs and native count')
    require(len(call['input_token_ids']) == generation['input_token_count'] == 240, 'actual input count')
    for name in ('vocab.json', 'tokenizer_config.json', 'modeling_locateanything.py'):
        require(sha(checkpoint / name) == manifest['model']['files_sha256'][name], 'pinned tokenizer/native decoder bytes')
    tokenizer_config = read(checkpoint / 'tokenizer_config.json')
    vocabulary = {value: key for key, value in read(checkpoint / 'vocab.json').items()}
    vocabulary.update({int(key): value['content'] for key, value in tokenizer_config['added_tokens_decoder'].items()})
    pieces = [vocabulary[token].replace('Ġ', ' ') for token in tokens]
    require(all(piece.isascii() for piece in pieces), 'this ASCII response needs only byte-level space restoration')
    require(''.join(pieces) == raw, 'independent raw token-vocabulary reconstruction without tokenizer execution')
    require(generation['model_max_length'] == tokenizer_config['model_max_length'] == 16384, 'tokenizer maximum length')
    require(generation['effective_limit'] == min(config['settings']['max_new_tokens'], 16384 - len(call['input_token_ids'])) == 256, 'configured effective limit remains 256')
    require(generation['eos_token_id'] == 151645 and vocabulary[151645] == '<|im_end|>' and 151645 not in tokens, 'no EOS anywhere in actual response')
    require(not generation['terminal_eos_observed'] and not generation['complete_generation'] and generation['length_limit_reached'] and generation['truncation_status'] == 'no_terminal_eos', 'independent completion and length audit')
    matches = re.findall(r'<box><(\d+)><(\d+)><(\d+)><(\d+)></box>', raw)
    prefix = '<ref>the neck of the wine bottle</ref>'
    reconstructed_raw = prefix + ''.join('<box>' + ''.join(f'<{x}>' for x in values) + '</box>' for values in matches)
    require(raw == reconstructed_raw and len(matches) == 42, 'complete raw grammar with 42 BOX records')
    require(model['parsed']['status'] == 'multiple_boxes' and model['parsed']['points'] == [] and model['parsed']['invalid'] == [] and model['parsed']['empty_count'] == 0, 'parser rejects multiple BOX records')
    require([box['normalized'] for box in model['parsed']['boxes']] == [list(map(int, values)) for values in matches], 'all raw normalized BOX records preserved, no selection')
    require(model['admitted_box'] is None, 'unchanged admission rejects no EOS, over-limit, multiple BOX response')
    require(0 <= returned['latency_to_return_s'] <= model['latency_s'] < 300, 'return within fixed timeout')
    return {'status': 'pass', 'scientific_outcome': 'grounding_not_admitted', 'freeze': FREEZE,
            'journal_records': len(rows), 'journal_sha256': sha(run / 'episodes.jsonl'),
            'generation_return_sha256': sha(run / 'generation-return.json'), 'model_output_sha256': sha(run / 'model-output.json'),
            'input_token_count': len(call['input_token_ids']), 'configured_max_new_tokens': 256,
            'actual_generated_token_count': len(tokens), 'terminal_eos_observed': False, 'raw_box_records': len(matches),
            'admitted_box': None, 'sensor_representation_created': False, 'evaluator_opened': False,
            'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0,
            'native_decoder_sha256': sha(checkpoint / 'modeling_locateanything.py'),
            'limits': ['independent stored bytes, token vocabulary and scalar counts only',
                       'recorded checkpoint hash map checked; model weights not reread',
                       'no inference, model construction, processor, projection, FK, physics or rendering',
                       'no individual BOX selected; no point/support or proxy evaluation exists',
                       'one fixture and one fixed condition; no semantic or generalization conclusion']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--checkpoint', type=Path, default=Path('/home/junhongli/models/huggingface/LocateAnything-3B'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.checkpoint)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
