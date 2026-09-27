"""Stored-only current BOX integrity audit; no producer/model/processor imports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import numpy as np

import task2_point_region_evidence_audit as old

read, sha, require, identity = old.read, old.sha, old.require, old.identity
FREEZE = '428d78e7a9bd473ffac95d480d165c0f7288a905'
PREFLIGHT = '7671ec4ce265d0d41898d91de15a3ca520bb5c6c1e6265d581c7eb22c4b20dac'
REVIEW = 'cbad04d2b5fb136773f5457053b88d5e7c6cc75595a33e8cd8d33c06de7ed95b'
PROTOCOL = '469457a38792aeaaa28bc835cb681c7b91c86da346297432fda8c2aa0d65dfcd'
POINT_PREFLIGHT = '35ff93678d77b147bf1f5e0f4767de9ea2e62d915e2f2db3526eeeece2ce1903'
POINT_AUDIT = 'e034ead7baad4f3dd24bb992aa556897563e08d5fb9cae034fd93485d575c251'
ORDER = ('present-postevent', 'away-postevent')
SETTINGS = old.SETTINGS
QUESTION = 'Locate a single instance that matches the following description: the wine bottle.'


def observed_box(text):
    match = re.fullmatch(r'<ref>the wine bottle</ref><box><(\d+)><(\d+)><(\d+)><(\d+)></box><\|im_end\|>', text)
    require(match is not None, 'observed complete single native BOX shape')
    values = list(map(int, match.groups()))
    require(all(0 <= n <= 1000 for n in values) and values[0] < values[2] and values[1] < values[3], 'valid observed normalized box')
    box = [n / 1000 * 384 for n in values]
    return box, {'status': 'single_box', 'points': [], 'boxes': [{'normalized': values, 'continuous_xyxy': box}],
                 'empty_count': 0, 'invalid': [], 'confidence': None}


def audit(run):
    batch, request, manifest = old.journal(run, ['run_start', 'condition_intent', 'condition_complete',
        'condition_intent', 'condition_complete', 'termination'])
    require(request == read(run / 'request.json') and request['conditions'] == list(ORDER)
            and request['planned_model_calls'] == 2 and request['fresh_process_per_condition']
            and request['seed'] == 1 and request['retries'] == 0 and request['physical_gpu'] == '2'
            and request['settings'] == SETTINGS, 'fixed two cold hybrid BOX calls')
    preflight_path = Path(request['preflight'])
    require(sha(preflight_path) == request['preflight_sha256'] == PREFLIGHT
            and sha(run / 'review.json') == request['review_sha256'] == REVIEW
            and sha(run / 'protocol.md') == request['protocol_sha256'] == PROTOCOL, 'reviewed freeze/config inputs')
    preflight = read(preflight_path)
    require(manifest['code'] == preflight['code'] and manifest['code']['commit'] == FREEZE
            and not manifest['code']['dirty_status'] and manifest['versions'] == preflight['versions']
            and preflight['question'] == QUESTION and preflight['settings'] == SETTINGS, 'clean executed freeze and archived environment')
    require(preflight['source']['original_matrix_status'] == 'interrupted_incomplete'
            and preflight['source']['source_admission_sha256'] == request['source_admission_sha256']
            == '57fa52a1ba5ffff73e7e197bbe352fe5f83209397c8cb972736cea389f0d7e42', 'composite source qualification')
    point_preflight_path = run.parent / 'task2-closed-empty-slow-point-preflight-01.json'
    point_audit_path = Path(__file__).resolve().parents[1] / 'docs/evidence/autonomous_research/task2_closed_empty_slow_point_independent_audit.json'
    require(sha(point_preflight_path) == request['point_preflight_sha256'] == POINT_PREFLIGHT
            and sha(point_audit_path) == request['point_audit_sha256'] == POINT_AUDIT, 'independently audited current POINT linkage')
    point_preflight, point_audit = read(point_preflight_path), read(point_audit_path)
    point_run = Path(preflight['point_reference']['directory'])
    require(sha(point_run / 'episodes.jsonl') == point_audit['journal_sha256']
            == preflight['point_reference']['journal_sha256'], 'current POINT journal unchanged')
    model, vocab = preflight['model'], {}
    require(old.canonical(model['files_sha256']) == model['content_id'] == old.MODEL, 'checkpoint content identity')
    for name in ('vocab.json', 'added_tokens.json'):
        path = Path(model['path']) / name
        require(sha(path) == model['files_sha256'][name], 'static token vocabulary')
        vocab.update({value: key for key, value in read(path).items()})
    conditions, pids, loaded_states = [], [], []
    for index, name in enumerate(ORDER):
        directory = run / name
        rows, config, child = old.journal(directory, ['run_start', 'rgb_input_sealed', 'manifest_update',
            'native_input_sealed', 'native_input_sealed', 'generation_settings_sealed', 'call_started',
            'generation_return_sealed', 'model_output_sealed', 'termination'])
        source = preflight['source']['images'][index]
        require(config == {'case_id': name, 'question': QUESTION, 'image_source': source, 'settings': SETTINGS,
            'seed': 1, 'model_call_budget': 1, 'request_sha256': sha(run / 'request.json')}, 'exact input question/config')
        require(batch[1+2*index]['data'] == {'ordinal': index, 'case_id': name}
                and batch[1+2*index]['wall_time'] < rows[0]['wall_time'] < rows[-1]['wall_time']
                < batch[2+2*index]['wall_time'], 'ordered cold case chronology')
        require(rows[6]['data'] == {'model_call_ordinal': 1, 'timeout_s': 300}
                and rows[8]['data']['evaluator_opened'] is False
                and read(directory / 'generation-settings.json') == SETTINGS, 'one generation and pre-call hybrid settings seal')
        loaded = child['loaded']
        require(child['code'] == manifest['code'] and child['versions'] == preflight['versions']
                and child['model'] == model and loaded == preflight['point_reference']['cases'][index]['loaded']
                and loaded['model_config'] == preflight['source_model_config']
                and loaded['dtype'] == loaded['parameter_dtype'] == 'torch.bfloat16' and loaded['model_training'] is False
                and loaded['tokenizer_model_max_length'] == 16384 and loaded['eos_token_id'] == 151645
                and loaded['physical_gpu'] == '2', 'exact loaded model/GPU/BF16/eval configuration')
        source_path = Path(preflight['source']['source_root']) / source['directory'] / source['artifact']
        require(sha(source_path) == source['artifact_sha256'], 'same full-RGB source')
        with np.load(source_path, allow_pickle=False) as archive:
            rgb = archive['rgb']
        require(identity(np.load(directory / 'rgb-input.npy', allow_pickle=False)) == identity(rgb)
                and rgb.shape == (384, 384, 3) and rgb.dtype == np.uint8, 'all RGB bytes')
        metadata = read(directory / 'native-input.json')
        require(metadata == preflight['inputs'][index] and metadata['question'] == QUESTION
                and metadata['condition'] == name and metadata['query'] == 'the wine bottle'
                and metadata['rgb'] == identity(rgb) and len(metadata['input_token_ids']) == 237
                and metadata['attention_mask'] == [[1]*237] and metadata['image_grid_hws'] == [[28, 28]]
                and metadata['pixel_values_original_dtype'] == 'torch.bfloat16', 'all actual input tokens/template/grid/mask')
        for key in ('rgb', 'image_grid_hws', 'pixel_values_original_dtype', 'pixel_values_float32'):
            require(metadata[key] == point_preflight['inputs'][index][key], 'visual input identical to current POINT')
        with np.load(directory / 'native-input.npz', allow_pickle=False) as archive:
            require(archive.files == ['pixel_values_float32'], 'native tensor whitelist')
            pixels = archive['pixel_values_float32']
        require(identity(pixels) == metadata['pixel_values_float32'] and pixels.shape == (784, 3, 14, 14)
                and pixels.dtype == np.float32 and np.isfinite(pixels).all()
                and np.all((pixels.view(np.uint32) & 65535) == 0), 'all actual BF16 tensor bytes')
        raw, result = read(directory / 'generation-return.json'), read(directory / 'model-output.json')
        sequences = raw['observed_decoded_token_sequences']
        require(len(sequences) == len(sequences[0]) == 1, 'one decoded return')
        ids = sequences[0][0]
        decoded = ''.join(vocab[token] for token in ids).replace('Ġ', ' ')
        require(decoded == raw['raw_response'] == result['raw_output'] and raw['raw_response_type'] == 'str'
                and raw['returned_value_repr'] == repr(decoded) and 0 < raw['latency_to_return_s'] < 300
                and ids[-1] == 151645 and 0 < len(ids) < 256, 'all output IDs and complete under-cap return')
        audit_value = {'actual_generated_token_ids': ids, 'actual_generated_token_count': len(ids), 'input_token_count': 237,
            'model_max_length': 16384, 'eos_token_id': 151645, 'effective_limit': 256, 'terminal_eos_observed': True,
            'length_limit_reached': False, 'complete_generation': True, 'truncation_status': 'eos_terminated'}
        box, parsed = observed_box(decoded)
        require(result == {'raw_output': decoded, 'generation_audit': audit_value, 'parsed': parsed,
            'status': 'admitted_rgb_box', 'admitted_box': box, 'depth_read': False, 'holding': None,
            'semantic_target_identity_verified': False, 'support_extracted': False, 'box_median_goal_created': False},
            'independent strict full-return BOX admission and no depth/support extraction')
        require(rows[-1]['data'] == {'reason': 'fixed_rgb_box_condition_complete', 'status': result['status'],
            'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0}, 'case call accounting')
        require(batch[2+2*index]['data'] == {'case_id': name, 'status': result['status'],
            'model_output_sha256': sha(directory / 'model-output.json')}, 'batch output linkage')
        artifacts = {file: sha(directory / file) for file in ('episodes.jsonl', 'manifest.json', 'resolved_config.yaml',
            'rgb-input.npy', 'native-input.json', 'native-input.npz', 'generation-settings.json', 'generation-return.json', 'model-output.json')}
        conditions.append({'case_id': name, 'pid': child['pid'], 'pgid': child['pgid'], 'status': result['status'],
            'raw_output': decoded, 'admitted_box': box, 'parsed': parsed, 'token_count': len(ids),
            'actual_generated_token_ids': ids, 'generation_settings': SETTINGS, 'sha256': artifacts,
            'input_tensor_and_RGB_exact': True, 'all_emitted_ids_checked_against_static_vocabulary': True})
        pids.append(child['pid'])
        loaded_states.append(loaded)
    require(len(set(pids)) == 2 and loaded_states[0] == loaded_states[1], 'distinct cold processes, equal configurations')
    require(batch[-1]['data'] == {'reason': 'two_fixed_cold_current_boxes_complete',
        'conditions': [batch[i]['data'] for i in (2, 4)], 'model_calls': 2, 'retries': 0,
        'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False}, 'complete two-call batch seal')
    exit_path = run.parent / (run.name + '-exit.json')
    exit_receipt = read(exit_path)
    require(exit_receipt['tool_exit_code'] == 0 and exit_receipt['freeze_commit'] == FREEZE
            and exit_receipt['batch_journal_sha256'] == sha(run / 'episodes.jsonl'), 'successful exit binding')
    return {'status': 'PASS', 'freeze': FREEZE, 'raw_directory': str(run), 'preflight_sha256': PREFLIGHT,
        'prospective_review_sha256': REVIEW, 'protocol_sha256': PROTOCOL, 'request_sha256': sha(run / 'request.json'),
        'journal_sha256': sha(run / 'episodes.jsonl'), 'exit_receipt_sha256': sha(exit_path),
        'question': QUESTION, 'generation_settings': SETTINGS, 'model_calls': 2, 'fresh_processes': 2,
        'physical_gpu': '2', 'retries': 0, 'conditions': conditions,
        'new_model_processor_tokenizer_physics_render_FK_calls_during_audit': 0,
        'limits': ['Integrity PASS does not establish target segmentation, depth ownership, extent completeness or safety.',
            'No depth/calibration array was accessed and no support/projection/policy was computed.',
            'RGB semantics are owned by root; output admission here is exact syntax and coordinates.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'audit_sha256': sha(args.output),
        'conditions': [{key: row[key] for key in ('case_id', 'status', 'admitted_box', 'token_count')}
                       for row in result['conditions']]}, indent=2))
