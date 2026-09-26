"""Registered one-checkpoint substitution over the frozen 24+7 offline queries."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from .records import code_identity, file_hash, load_records, model_identity
from .point_grounding_probe import serialize_model_config
from . import visual_target_verification_run as native

REPO = 'Qwen/Qwen2.5-VL-7B-Instruct'
REVISION = 'cc594898137f460bfe9f0759e9844b3ce807cfb5'
MODEL_PATH = '/home/junhongli/projects/research-models/Qwen2.5-VL-7B-Instruct'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/vlm_capability_control_protocol.md'
RAW_ROOT = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
PROBES = {
    'relations': ('vlm-world-single-inputs-01', 'vlm-world-single-labels-01',
                  'vlm-world-single-preflight-01', 'vlm-world-single-run-01'),
    'subgoals': ('visual-subgoal-inputs-02', 'visual-subgoal-labels-01',
                 'visual-subgoal-preflight-01', 'visual-subgoal-run-01'),
}


def probe_for(name):
    if name == 'relations':
        from . import vlm_world_single_relation as probe
    elif name == 'subgoals':
        from . import visual_subgoal_probe as probe
    else:
        raise ValueError('unregistered probe')
    return probe


def acquisition_identity(path):
    path = Path(path)
    acquired = json.loads(path.read_text())
    metadata_path = path.parent/'pinned-provider-metadata.json'
    metadata = json.loads(metadata_path.read_text())
    if acquired['repo'] != REPO or acquired['revision'] != REVISION or metadata['sha'] != REVISION:
        raise ValueError('unregistered checkpoint acquisition')
    expected = {f['rfilename']: f for f in metadata['siblings']
                if Path(f['rfilename']).suffix in {'.json', '.txt', '.safetensors'}}
    receipts = {r['name']: r for r in acquired['files']}
    if set(expected) != set(receipts) or len(receipts) != len(acquired['files']):
        raise ValueError('acquired files differ from provider manifest')
    for name, item in expected.items():
        receipt = receipts[name]
        etag = item.get('lfs', {}).get('sha256', item['blobId'])
        digest = receipt['sha256'] if 'lfs' in item else receipt['git_blob_sha1']
        if (receipt['bytes'] != item['size'] or receipt['provider_etag'] != etag or digest != etag
                or receipt['immutable_url'] != f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}'):
            raise ValueError('provider ETag/content verification differs')
    return {'repo': REPO, 'revision': REVISION, 'content_id': acquired['content_id'],
            'files_sha256': {name: row['sha256'] for name, row in receipts.items()},
            'acquisition_path': str(path.resolve()), 'acquisition_sha256': file_hash(path),
            'metadata_sha256': file_hash(metadata_path)}


def register(output, acquisition):
    code = code_identity()
    if code['dirty_status']:
        raise ValueError('commit the complete protocol/code/tests before registration')
    model = model_identity(MODEL_PATH)
    acquired = acquisition_identity(acquisition)
    if model['content_id'] != acquired['content_id'] or model['files_sha256'] != acquired['files_sha256']:
        raise ValueError('local model differs from verified acquired bytes')
    probes = {}
    for name, (source, labels, preflight, run) in PROBES.items():
        probe = probe_for(name)
        source = RAW_ROOT/source
        manifest = probe.load_inputs(source)
        probes[name] = {'source': str(source), 'manifest_sha256': file_hash(source/'manifest.json'),
            'evaluation_sha256': file_hash(RAW_ROOT/labels/'labels.json'),
            'planned_calls': probe.PLANNED_CALLS, 'generation_settings': probe.GENERATION,
            'source_protocol_sha256': file_hash(probe.PROTOCOL),
            'baseline_preflight': str(RAW_ROOT/preflight),
            'baseline_preflight_sha256': file_hash(RAW_ROOT/preflight/'episodes.jsonl'),
            'baseline_run': str(RAW_ROOT/run),
            'baseline_records_sha256': file_hash(RAW_ROOT/run/'episodes.jsonl'),
            'source_type': manifest['source_type']}
    registration = {'version': 'vlm7b-capability-control-v1', 'protocol_sha256': file_hash(PROTOCOL),
        'model': model, 'acquisition': acquired, 'probes': probes, 'total_unique_calls': 31,
        'frozen_code': code, 'no_retries': True, 'no_execution': True,
        'scope': 'fixed-development-image capability control; no planner/manipulation inference'}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'registration.json').write_text(json.dumps(registration, indent=2)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return registration


def load_registration(path, check_code=True):
    registration = json.loads(Path(path).read_text())
    if (registration['version'] != 'vlm7b-capability-control-v1'
            or registration['protocol_sha256'] != file_hash(PROTOCOL)
            or registration['total_unique_calls'] != 31 or not registration['no_retries']
            or not registration['no_execution'] or set(registration['probes']) != set(PROBES)):
        raise ValueError('control registration changed')
    current_code = code_identity()
    if check_code and current_code != registration['frozen_code']:
        raise ValueError('code/commit changed after control registration')
    if current_code['source_sha256'] != registration['frozen_code']['source_sha256']:
        raise ValueError('scientific source changed after control registration')
    acquired = acquisition_identity(registration['acquisition']['acquisition_path'])
    if acquired != registration['acquisition']:
        raise ValueError('frozen acquisition changed')
    for name, entry in registration['probes'].items():
        probe = probe_for(name)
        source, _, preflight, run = PROBES[name]
        if (entry['source'] != str(RAW_ROOT/source)
                or entry['baseline_preflight'] != str(RAW_ROOT/preflight)
                or entry['baseline_run'] != str(RAW_ROOT/run)
                or entry['planned_calls'] != probe.PLANNED_CALLS
                or entry['generation_settings'] != probe.GENERATION
                or entry['source_protocol_sha256'] != file_hash(probe.PROTOCOL)
                or entry['manifest_sha256'] != file_hash(RAW_ROOT/source/'manifest.json')
                or entry['baseline_preflight_sha256'] != file_hash(RAW_ROOT/preflight/'episodes.jsonl')
                or entry['baseline_records_sha256'] != file_hash(RAW_ROOT/run/'episodes.jsonl')):
            raise ValueError('registered fixed input/baseline/settings changed')
        # The original strict loader validates prompts, image identities, and lineage.
        probe.load_inputs(entry['source'])
    return registration


def registered_model(args, identity):
    registration = load_registration(args.capability_registration)
    matching = [entry for entry in registration['probes'].values()
                if entry['source'] == str(Path(args.source).resolve())]
    if len(matching) != 1 or matching[0]['evaluation_sha256'] != args.evaluation_sha256:
        raise ValueError('unregistered input/evaluator pairing')
    if (identity != registration['model'] or identity['path'] != MODEL_PATH
            or identity['content_id'] != registration['acquisition']['content_id']
            or identity['files_sha256'] != registration['acquisition']['files_sha256']):
        raise ValueError('model differs from registered acquired checkpoint')
    return {'repo': REPO, 'revision': REVISION, 'content_id': identity['content_id'],
            'registration_sha256': file_hash(args.capability_registration),
            'protocol_sha256': registration['protocol_sha256'],
            'acquisition_sha256': registration['acquisition']['acquisition_sha256']}


def compare_presentations(baseline, current):
    if len(baseline) != len(current):
        raise ValueError('presentation count changed')
    fields = ('messages', 'prompt', 'input_ids', 'attention_mask', 'image_grid_thw',
              'processor_pixel_values', 'consumed_pixel_values', 'rgb_sha256',
              'processed_image_size_wh', 'image_pad_token_count')
    rows = []
    for old, new in zip(baseline, current):
        if old['call_id'] != new['call_id'] or old['image_index'] != new['image_index']:
            raise ValueError('presentation condition order changed')
        if old['messages'] != new['messages'] or old['rgb_sha256'] != new['rgb_sha256']:
            raise ValueError('model-visible message/image changed')
        rows.append({'call_id': new['call_id'], 'baseline_token_count': old['input_token_count'],
            'control_token_count': new['input_token_count'],
            'token_count_delta': new['input_token_count']-old['input_token_count'],
            'equal': {key: old[key] == new[key] for key in fields}})
    return rows


def compare_to_baseline(args, presentations):
    # Registration was validated before preprocessing; only read original raw inputs.
    registration = json.loads(Path(args.capability_registration).read_text())
    entry = next(item for item in registration['probes'].values()
                 if item['source'] == str(Path(args.source).resolve()))
    baseline, diagnostics = load_records(Path(entry['baseline_run'])/'episodes.jsonl')
    if diagnostics:
        raise ValueError('incomplete baseline evidence')
    return compare_presentations([r['data'] for r in baseline if r['kind'] == 'presentation'], presentations)


def audit(output, registration_path, name, evaluation):
    import torch
    from transformers import AutoConfig, AutoProcessor
    registration = load_registration(registration_path, check_code=False)
    probe, entry = probe_for(name), registration['probes'][name]
    rows, diagnostics = load_records(Path(output)/'episodes.jsonl')
    if diagnostics or any(r['kind'] == 'failure' for r in rows):
        raise ValueError('incomplete or failed control evidence')
    start = native.unique(rows, 'run_start')
    config, frozen = start['resolved_config'], native.unique(rows, 'frozen_inputs')
    if (start['manifest']['code'] != registration['frozen_code']
            or config['source'] != entry['source'] or config['evaluation_sha256'] != entry['evaluation_sha256']
            or config['capability_registration'] != str(Path(registration_path).resolve())):
        raise ValueError('generation code/registration/source changed')
    identity = model_identity(MODEL_PATH)
    # Recheck all immutable identities while allowing later documentation commits.
    expected_control = {'repo': REPO, 'revision': REVISION, 'content_id': identity['content_id'],
        'registration_sha256': file_hash(registration_path), 'protocol_sha256': registration['protocol_sha256'],
        'acquisition_sha256': registration['acquisition']['acquisition_sha256']}
    if identity != registration['model'] or identity != frozen['model'] or frozen['capability_control'] != expected_control:
        raise ValueError('audited checkpoint/registration differs')
    processor = AutoProcessor.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=False, use_fast=False)
    model_config = AutoConfig.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=False)
    expected = deepcopy(model_config)
    expected.dtype = torch.bfloat16
    for config_name in expected.sub_configs:
        getattr(expected, config_name).dtype = torch.bfloat16
    expected._attn_implementation = 'sdpa'
    expected_config = serialize_model_config(expected.to_dict())
    generation = serialize_model_config(native.make_generation(MODEL_PATH).to_dict())
    loaded = native.unique(rows, 'model_loaded')
    if (frozen['model_config'] != serialize_model_config(model_config.to_dict())
            or frozen['expected_loaded_config'] != expected_config or loaded['config'] != expected_config
            or loaded['dtype'] != 'torch.bfloat16' or loaded['training'] or loaded['attention'] != 'sdpa'
            or frozen['generation_config'] != generation or loaded['generation_config'] != generation
            or loaded['torch_threads'] != 4 or loaded['cuda_visible_devices'] != '2'
            or frozen['processor_config'] != serialize_model_config(processor.image_processor.to_dict())):
        raise ValueError('native config/processor/execution audit failed')
    presentation = [r['data'] for r in rows if r['kind'] == 'presentation']
    manifest = probe.load_inputs(entry['source'])
    regenerated = [probe.prepare_call(processor, entry['source'], call, manifest['examples'])[1]
                   for call in probe.PLANNED_CALLS]
    if presentation != regenerated:
        raise ValueError('recorded presentation differs from fresh preprocessing')
    preflight, preflight_diagnostics = load_records(Path(config['preflight_source'])/'episodes.jsonl')
    if (preflight_diagnostics or native.unique(preflight, 'frozen_inputs') != frozen
            or native.unique(preflight, 'termination') != {'reason': 'preflight_complete', 'planned_calls': len(probe.PLANNED_CALLS)}
            or [r['data'] for r in preflight if r['kind'] == 'presentation'] != presentation
            or native.unique(preflight, 'label_tokens') != native.unique(rows, 'label_tokens')):
        raise ValueError('preflight audit differs')
    baseline, baseline_diagnostics = load_records(Path(entry['baseline_run'])/'episodes.jsonl')
    if baseline_diagnostics:
        raise ValueError('incomplete baseline evidence')
    comparison = compare_presentations([r['data'] for r in baseline if r['kind'] == 'presentation'], presentation)
    if (native.unique(rows, 'baseline_presentation_comparison') != comparison
            or native.unique(preflight, 'baseline_presentation_comparison') != comparison):
        raise ValueError('preregistered processor comparison differs')
    # Original summary reconstructs all native logits/tokens/EOS and reads gold only here.
    summary = probe.summarize(output, evaluation)
    return {**summary, 'control_registration_sha256': file_hash(registration_path),
        'native_and_checkpoint_audit': 'pass', 'baseline_raw_sha256': entry['baseline_records_sha256'],
        'processor_comparison': comparison, 'checkpoint': expected_control,
        'model_loaded': loaded,
        'responses': [{'call_id': r['data']['call_id'], 'decoded_text': r['data']['decoded_text'],
            'latency_s': r['data']['latency_s'], 'peak_allocated_bytes': r['data']['peak_allocated_bytes'],
            'peak_reserved_bytes': r['data']['peak_reserved_bytes']} for r in rows if r['kind'] == 'raw_response']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['register', 'preflight', 'generate', 'audit'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--registration')
    parser.add_argument('--acquisition')
    parser.add_argument('--probe', choices=tuple(PROBES))
    parser.add_argument('--preflight-source')
    parser.add_argument('--evaluation')
    args = parser.parse_args()
    if args.mode == 'register':
        if not args.acquisition:
            parser.error('register needs verified acquisition')
        print(json.dumps(register(args.output, args.acquisition), indent=2))
        return
    if not args.registration or not args.probe:
        parser.error('registered probe required')
    if args.mode == 'audit':
        if not args.evaluation:
            parser.error('audit needs original evaluator')
        print(json.dumps(audit(args.output, args.registration, args.probe, args.evaluation), indent=2))
        return
    if args.mode == 'generate' and not args.preflight_source:
        parser.error('generate requires frozen preflight')
    registration = load_registration(args.registration)
    entry = registration['probes'][args.probe]
    # No evaluator path/content is passed to the generator.
    probe_for(args.probe).run(SimpleNamespace(mode=args.mode, output=args.output, source=entry['source'],
        model_path=MODEL_PATH, device='cuda', preflight_source=args.preflight_source,
        evaluation_sha256=entry['evaluation_sha256'], capability_registration=str(Path(args.registration).resolve())))


if __name__ == '__main__':
    main()
