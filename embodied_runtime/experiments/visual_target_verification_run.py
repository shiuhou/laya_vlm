"""Native Qwen-VL frozen RGB verification with token/image consumption evidence."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
import random
import time
from pathlib import Path

import numpy as np
from PIL import Image

from .point_grounding_probe import serialize_model_config
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .visual_target_verification import (
    GENERATION, INSTRUCTION, LABELS, MODEL_REPO, PROTOCOL, parse_label, tensor_fingerprint,
)

REVISION = '66285546d2b821cf421d4f5eb2576359d3770cd3'
MODEL_PATH = '/home/junhongli/projects/research-models/Qwen2.5-VL-3B-Instruct'


def protocol_for_manifest(manifest):
    """Two registered offline probes share the identical model execution path."""
    version = manifest.get('version')
    if version=='visual-target-verification-input-v1':
        if len(manifest['examples'])!=14 or len(manifest['excluded'])!=4:
            raise ValueError('registered14/4 selection mismatch')
        return PROTOCOL
    if version=='visual-marker-control-input-v1':
        from .visual_marker_control import PROTOCOL as control_protocol, SOURCE_INDICES
        expected = [(i, variant) for i in SOURCE_INDICES for variant in ('original','table')]
        actual = [(e['parent_source_index'],e['variant']) for e in manifest['examples']]
        if actual!=expected or manifest['excluded']:
            raise ValueError('registered marker-control selection mismatch')
        return control_protocol
    raise ValueError('unregistered visual input manifest version')


def frozen_sources(source, model_path):
    source, model_path = Path(source), Path(model_path)
    manifest = json.loads((source/'manifest.json').read_text())
    if (manifest['model_repo']!=MODEL_REPO or manifest['model_revision']!=REVISION
            or manifest['instruction']!=INSTRUCTION or manifest['labels']!=list(LABELS)
            or manifest['generation_settings']!=GENERATION or manifest['repeats']!=2
            or manifest['protocol_sha256']!=file_hash(protocol_for_manifest(manifest))):
        raise ValueError('frozen protocol/model/input settings mismatch')
    examples = manifest['examples']
    indices = [e['source_index'] for e in examples]
    if len(set(indices))!=len(indices):
        raise ValueError('duplicate input index')
    if manifest['planned_calls'] != [{'source_index': i, 'repeat': repeat} for repeat in (1, 2) for i in indices]:
        raise ValueError('frozen repeated call order mismatch')
    index = json.loads((model_path/'model.safetensors.index.json').read_text())
    for shard in set(index['weight_map'].values()):
        if Path(shard).name != shard or not (model_path/shard).is_file():
            raise ValueError('checkpoint shard missing or invalid')
    for example in examples:
        for key in ('raw', 'marked'):
            path = source/example[f'{key}_artifact']
            if path.resolve().parent!=source.resolve() or file_hash(path)!=example[f'{key}_sha256']:
                raise ValueError('image artifact changed or escaped source')
            with Image.open(path) as image:
                if image.mode!='RGB' or image.size!=(example['width'], example['height']):
                    raise ValueError('image format/size changed')
    return manifest


def make_generation(model_path):
    from transformers import GenerationConfig
    defaults = json.loads((Path(model_path)/'generation_config.json').read_text())
    # A fresh config avoids inherited sampling/repetition settings.
    return GenerationConfig(**GENERATION, bos_token_id=defaults.get('bos_token_id'),
        eos_token_id=defaults['eos_token_id'], pad_token_id=defaults['pad_token_id'],
        return_dict_in_generate=True, output_logits=True)


def prepare_image(processor, source, example):
    import torch
    with Image.open(Path(source)/example['marked_artifact']) as opened:
        image = opened.copy()
    messages = [{'role': 'user', 'content': [{'type': 'image'}, {'type': 'text', 'text': INSTRUCTION}]}]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[prompt], images=[image], return_tensors='pt', truncation=False)
    ids = inputs['input_ids'].tolist()[0]
    max_positions = processor.tokenizer.model_max_length
    if len(ids)+GENERATION['max_new_tokens']>max_positions:
        raise ValueError('input plus output exceeds tokenizer context; no truncation allowed')
    grid = inputs['image_grid_thw']
    merge = processor.image_processor.merge_size
    expected_image_tokens = int(grid.prod(dim=1).sum().item()) // (merge*merge)
    image_tokens = ids.count(processor.tokenizer.convert_tokens_to_ids(processor.image_token))
    if image_tokens != expected_image_tokens:
        raise ValueError('processor image token count differs from patch grid')
    raw_pixel = tensor_fingerprint(inputs['pixel_values'])
    inputs['pixel_values'] = inputs['pixel_values'].to(dtype=torch.bfloat16)
    presentation = {'source_index': example['source_index'], 'messages': messages, 'prompt': prompt,
                    'marked_artifact_sha256': example['marked_sha256'],
                    'input_ids': ids, 'input_token_count': len(ids),
                    'attention_mask': inputs['attention_mask'].tolist(),
                    'image_grid_thw': inputs['image_grid_thw'].tolist(),
                    'processor_pixel_values': raw_pixel,
                    'consumed_pixel_values': tensor_fingerprint(inputs['pixel_values']),
                    'original_image_size': list(image.size),
                    'processed_image_size_wh': [int(inputs['image_grid_thw'][0, 2])*processor.image_processor.patch_size,
                                                int(inputs['image_grid_thw'][0, 1])*processor.image_processor.patch_size],
                    'image_pad_token_count': ids.count(processor.tokenizer.convert_tokens_to_ids(processor.image_token)),
                    'truncation': False}
    return inputs, presentation


def validate_generation(presentation, raw, logits, tokenizer, eos_ids, vocab_size):
    """Integrity failures raise; invalid/uncompleted label remains an outcome."""
    generated = raw['generated_ids']
    n = len(generated)
    if n<1 or n>GENERATION['max_new_tokens']:
        raise ValueError('native generated length invalid')
    if raw['sequence_ids'] != presentation['input_ids']+generated:
        raise ValueError('generated sequence differs from input prefix')
    expected = [presentation['input_ids']]+[[token] for token in generated[:-1]]
    traces = raw['forward_traces']
    if len(traces)!=n or [t['input_ids'][0] for t in traces]!=expected:
        raise ValueError('actual consumed input IDs differ')
    if traces[0]['pixel_values']!=presentation['consumed_pixel_values']:
        raise ValueError('actual consumed image tensor differs')
    if traces[0]['image_grid_thw']!=presentation['image_grid_thw']:
        raise ValueError('actual image grid differs')
    if traces[0]['attention_mask']!=presentation['attention_mask']:
        raise ValueError('actual attention mask differs')
    if any(t['pixel_values'] is not None for t in traces[1:]):
        raise ValueError('unexpected image tensor reinjection')
    if logits.shape!=(n, vocab_size) or not np.isfinite(logits).all():
        raise ValueError('full vocabulary logits invalid')
    if logits.argmax(axis=1).tolist()!=generated:
        raise ValueError('greedy tokens differ from raw logits')
    decoded = tokenizer.decode(generated, skip_special_tokens=False)
    plain = tokenizer.decode(generated, skip_special_tokens=True)
    if decoded!=raw['raw_decoded_text'] or plain!=raw['decoded_text']:
        raise ValueError('raw generated decode differs')
    eos = {eos_ids} if isinstance(eos_ids, int) else set(eos_ids)
    complete = generated[-1] in eos and not any(t in eos for t in generated[:-1])
    unexpected = any(t in tokenizer.all_special_ids for t in generated[:-1])
    parsed = parse_label(plain)
    valid = complete and not unexpected and parsed['status']=='valid'
    return {'status': 'valid' if valid else 'invalid', 'label': parsed['label'] if valid else None,
            'parsed_label': parsed, 'terminal_eos': complete, 'unexpected_special_token': unexpected,
            'length_limit_reached': n==GENERATION['max_new_tokens'],
            'generated_token_count': n, 'no_terminal_eos': not complete}


def unique(records, kind):
    rows = [r['data'] for r in records if r['kind']==kind]
    if len(rows)!=1:
        raise ValueError(f'exactly one {kind} record required')
    return rows[0]


def _run(args, recorder):
    import torch
    from transformers import AutoConfig, AutoProcessor, Qwen2_5_VLForConditionalGeneration
    source, model_path = Path(args.source), Path(args.model_path)
    manifest = frozen_sources(source, model_path)
    recorder.record('planned_inputs', {'safe_input_manifest':manifest})
    torch.set_num_threads(4)
    random.seed(1)
    np.random.seed(1)
    torch.manual_seed(1)
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=False, use_fast=False)
    config = AutoConfig.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    generation = make_generation(model_path)
    # Transformers4.57.3 from_pretrained explicitly propagates requested dtype to
    # all composite subconfigs; freeze that expected load normalization separately.
    expected_loaded_config = deepcopy(config)
    expected_loaded_config.dtype = torch.bfloat16
    for name in expected_loaded_config.sub_configs:
        getattr(expected_loaded_config, name).dtype = torch.bfloat16
    expected_loaded_config._attn_implementation = 'sdpa'
    identity = model_identity(model_path)
    code = code_identity()
    own_sources = {p: h for p, h in code['source_sha256'].items() if p in {
        'embodied_runtime/experiments/visual_target_verification.py',
        'embodied_runtime/experiments/visual_target_verification_run.py',
        'embodied_runtime/experiments/point_grounding_probe.py', 'embodied_runtime/experiments/records.py',
        'embodied_runtime/experiments/visual_marker_control.py'}}
    frozen = {'manifest_sha256': file_hash(source/'manifest.json'), 'protocol_sha256': file_hash(protocol_for_manifest(manifest)),
              'model': identity, 'revision': REVISION, 'model_config': serialize_model_config(config.to_dict()),
              'expected_loaded_config': serialize_model_config(expected_loaded_config.to_dict()),
              'generation_config': serialize_model_config(generation.to_dict()),
              'processor_config': serialize_model_config(processor.image_processor.to_dict()),
              'processor_class': type(processor).__name__, 'image_processor_class': type(processor.image_processor).__name__,
              'processor_use_fast': False, 'relevant_source_sha256': own_sources,
              'versions': versions(), 'seed': 1, 'torch_threads': 4, 'dtype': 'torch.bfloat16', 'attention': 'sdpa'}
    prepared = {}
    options = {}
    for label in LABELS:
        ids = processor.tokenizer(label, add_special_tokens=False, truncation=False)['input_ids']
        if not ids or len(ids)+1>GENERATION['max_new_tokens'] or processor.tokenizer.decode(ids, skip_special_tokens=True)!=label:
            raise ValueError('label not representable within fixed output budget')
        options[label] = ids
    for example in manifest['examples']:
        inputs, presentation = prepare_image(processor, source, example)
        if presentation['input_token_count']+GENERATION['max_new_tokens']>config.max_position_embeddings:
            raise ValueError('model context would truncate input')
        prepared[example['source_index']] = inputs, presentation
    if args.mode=='generate':
        prior, diagnostics = load_records(Path(args.preflight_source)/'episodes.jsonl')
        if diagnostics or unique(prior, 'termination')!={'reason':'preflight_complete','planned_calls':len(manifest['planned_calls'])}:
            raise ValueError('complete preflight required')
        if unique(prior, 'frozen_inputs')!=frozen or unique(prior, 'label_tokens')!=options:
            raise ValueError('frozen model/code/settings changed after preflight')
        if [r['data'] for r in prior if r['kind']=='presentation'] != [p for _, p in prepared.values()]:
            raise ValueError('processor inputs changed after preflight')
    recorder.record('frozen_inputs', frozen)
    recorder.record('label_tokens', options)
    for _, presentation in prepared.values():
        recorder.record('presentation', presentation)
    if args.mode=='preflight':
        recorder.record('termination', {'reason':'preflight_complete','planned_calls':len(manifest['planned_calls'])})
        return
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_path, local_files_only=True,
        trust_remote_code=False, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to(args.device).eval()
    loaded_config = serialize_model_config(model.config.to_dict())
    if loaded_config!=frozen['expected_loaded_config'] or model.dtype is not torch.bfloat16:
        raise ValueError('loaded model config/dtype differs from preflight')
    if model.config._attn_implementation != 'sdpa':
        raise ValueError('loaded attention implementation differs')
    recorder.record('model_loaded', {'config':serialize_model_config(model.config.to_dict()),
        'dtype':str(model.dtype),'device':str(model.device),
        'generation_config':serialize_model_config(generation.to_dict()),
        'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),
        'gpu_name':torch.cuda.get_device_name(args.device),
        'gpu_total_memory':torch.cuda.get_device_properties(args.device).total_memory,
        'torch_threads':torch.get_num_threads(),'deterministic_algorithms':torch.are_deterministic_algorithms_enabled()})
    for planned in manifest['planned_calls']:
        index, repeat = planned['source_index'], planned['repeat']
        call_id = f'{index:02d}-r{repeat}'
        original_inputs, presentation = prepared[index]
        inputs = {k:v.to(args.device) for k,v in original_inputs.items()}
        traces = []
        def observe(_module, positional, kwargs):
            if positional:
                raise ValueError('unexpected positional model inputs')
            trace = {}
            for name in ('input_ids','attention_mask','image_grid_thw','position_ids','cache_position'):
                value = kwargs.get(name)
                trace[name] = None if value is None else value.detach().cpu().tolist()
            value = kwargs.get('pixel_values')
            trace['pixel_values'] = None if value is None else tensor_fingerprint(value)
            traces.append(trace)
        hook = model.register_forward_pre_hook(observe, with_kwargs=True)
        recorder.record('call_started', {'call_id':call_id, **planned})
        torch.cuda.synchronize(args.device)
        torch.cuda.reset_peak_memory_stats(args.device)
        started = time.perf_counter()
        try:
            with torch.no_grad():
                response = model.generate(**inputs, generation_config=generation)
            torch.cuda.synchronize(args.device)
        finally:
            hook.remove()
        elapsed = time.perf_counter()-started
        sequence = response.sequences[0].detach().cpu().tolist()
        generated = sequence[len(presentation['input_ids']):]
        logits = torch.stack(response.logits)[:,0,:].float().cpu().numpy()
        artifact = Path('logits')/f'{call_id}.npz'
        (Path(args.output)/'logits').mkdir(exist_ok=True)
        with (Path(args.output)/artifact).open('xb') as stream:
            np.savez_compressed(stream, logits=logits)
            stream.flush()
            os.fsync(stream.fileno())
        raw = {'call_id':call_id, **planned, 'sequence_ids':sequence,'generated_ids':generated,
               'raw_decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=False),
               'decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=True),
               'forward_traces':traces,'latency_s':elapsed,'logits_artifact':str(artifact),
               'logits_sha256':file_hash(Path(args.output)/artifact),
               'peak_allocated_bytes':torch.cuda.max_memory_allocated(args.device),
               'peak_reserved_bytes':torch.cuda.max_memory_reserved(args.device)}
        recorder.record('raw_response',raw)
        validated = validate_generation(presentation,raw,logits,processor.tokenizer,
                                         generation.eos_token_id,config.vocab_size)
        recorder.record('call_completed',{'call_id':call_id, **planned, **validated})
    recorder.record('termination',{'reason':'generation_complete','planned_calls':len(manifest['planned_calls'])})


def run(args):
    recorder = RunRecorder(args.output, {'mode':args.mode, 'source':str(Path(args.source).resolve()),
        'preflight_source':args.preflight_source, 'inference_settings':GENERATION,
        'oracle':False,'privileged':False},
        {'run_id':Path(args.output).name,'code':code_identity(),'versions':versions()})
    try:
        _run(args, recorder)
    except Exception as exc:
        recorder.record('failure', {'reason':repr(exc),'retries':0})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','generate'])
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--model-path',default=MODEL_PATH)
    parser.add_argument('--preflight-source')
    parser.add_argument('--device',default='cuda')
    args=parser.parse_args()
    if args.mode=='generate' and not args.preflight_source:
        parser.error('generation requires --preflight-source')
    run(args)


if __name__=='__main__':
    main()
