"""Single-field decomposition of the frozen visible-relation probe; one follow-up."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image

from . import vlm_world_relations as parent

from .point_grounding_probe import serialize_model_config
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .visual_target_verification import GENERATION, MODEL_REPO, tensor_fingerprint
from . import visual_target_verification_run as native
from .visual_target_verification_run import REVISION

VERSION = 'vlm-world-single-relation-v1'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/vlm_world_single_relation_protocol.md'
MODEL_CONTENT_ID = parent.MODEL_CONTENT_ID
FIELDS = ('horizontal', 'gap', 'orientation')
FIELD_OPTIONS = dict(zip(FIELDS, parent.FIELD_OPTIONS))
LABELS = tuple(dict.fromkeys(value for options in FIELD_OPTIONS.values() for value in options))
INTRO = 'Report only visible image geometry, not an action or hidden physical state. '
QUESTIONS = {
    'horizontal': "Where is the bottle's center horizontally relative to the visible open drawer interior? "
        'left = left of the interior; right = right of it; aligned = within its horizontal extent; '
        'uncertain = cannot determine. ',
    'gap': "Is there a clear visible gap between the bottle and the robot's gripper fingertips? "
        'separated = clear gap; adjacent = visibly next to or overlapping the fingertips; '
        'uncertain = cannot determine. This does not ask whether the robot securely holds the bottle. ',
    'orientation': "Is the bottle's long axis upright or diagonal in the image? "
        'upright = approximately vertical; diagonal = clearly tilted; uncertain = cannot determine. ',
}
INSTRUCTIONS = {field: INTRO + QUESTIONS[field] +
    'If no image is available or the objects are not visible, answer uncertain. '
    'Return exactly one word: ' + ', '.join(FIELD_OPTIONS[field]) + '.' for field in FIELDS}
BASE_CALLS = parent.PLANNED_CALLS[:8]
PLANNED_CALLS = [{'call_id': field + base['call_id'].removeprefix('neutral'),
    'image_index': base['image_index'], 'condition': field} for field in FIELDS for base in BASE_CALLS]
CALL_KEYS = parent.CALL_KEYS


def parse_label(text, condition):
    value = text.strip()
    valid = value in FIELD_OPTIONS[condition]
    return {'status': 'valid' if valid else 'invalid', 'label': value if valid else None}


def expected_manifest(source):
    source = Path(source).resolve()
    original = parent.load_inputs(source)
    return {'version': VERSION, 'protocol_sha256': file_hash(PROTOCOL),
        'parent_directory': str(source), 'parent_manifest_sha256': file_hash(source/'manifest.json'),
        'source_type': original['source_type'], 'not_original_control_replay_or_raw_sensor': True,
        'model_repo': MODEL_REPO, 'model_revision': REVISION, 'model_content_id': MODEL_CONTENT_ID,
        'instructions': INSTRUCTIONS, 'field_options': FIELD_OPTIONS,
        'generation_settings': GENERATION, 'planned_calls': PLANNED_CALLS,
        'examples': original['examples']}


def prepare(source, output):
    source, output = Path(source), Path(output)
    manifest = expected_manifest(source)
    output.mkdir(parents=True, exist_ok=False)
    for example in manifest['examples']:
        name = example['rgb_artifact']
        (output/name).write_bytes((source/name).read_bytes())
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return load_inputs(output)


def load_inputs(source):
    source = Path(source)
    manifest = json.loads((source/'manifest.json').read_text())
    expected = json.loads(json.dumps(expected_manifest(manifest['parent_directory'])))
    if manifest != expected:
        raise ValueError('registered single-relation settings or image lineage changed')
    for example in manifest['examples']:
        path = source/example['rgb_artifact']
        if path.resolve().parent != source.resolve() or file_hash(path) != example['rgb_sha256']:
            raise ValueError('prepared image changed or escaped source')
    return manifest


def prepare_call(processor, source, planned, examples):
    import torch
    example = None if planned['image_index'] is None else examples[planned['image_index']]
    content = [] if example is None else [{'type':'image'}]
    messages = [{'role':'user','content':content+[{'type':'text','text':INSTRUCTIONS[planned['condition']]}]}]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images = None
    if example is not None:
        with Image.open(Path(source)/example['rgb_artifact']) as image:
            images = [image.copy()]
    inputs = processor(text=[prompt], images=images, return_tensors='pt', truncation=False)
    ids = inputs['input_ids'].tolist()[0]
    if len(ids)+GENERATION['max_new_tokens'] > processor.tokenizer.model_max_length:
        raise ValueError('input plus output exceeds tokenizer context; no truncation allowed')
    image_tokens = ids.count(processor.tokenizer.convert_tokens_to_ids(processor.image_token))
    presentation = {**planned, 'messages':messages, 'prompt':prompt, 'input_ids':ids,
        'input_token_count':len(ids), 'attention_mask':inputs['attention_mask'].tolist(),
        'image_grid_thw':None, 'processor_pixel_values':None, 'consumed_pixel_values':None,
        'rgb_sha256':None if example is None else example['rgb_sha256'],
        'original_image_size':None if example is None else [600,600], 'processed_image_size_wh':None,
        'image_pad_token_count':image_tokens, 'truncation':False}
    if example is None:
        if image_tokens or 'pixel_values' in inputs or 'image_grid_thw' in inputs:
            raise ValueError('text-only condition unexpectedly contains image input')
    else:
        grid = inputs['image_grid_thw']
        expected = int(grid.prod(dim=1).sum().item()) // processor.image_processor.merge_size**2
        if image_tokens != expected:
            raise ValueError('processor image token count differs from patch grid')
        presentation['processor_pixel_values'] = tensor_fingerprint(inputs['pixel_values'])
        inputs['pixel_values'] = inputs['pixel_values'].to(dtype=torch.bfloat16)
        presentation.update(image_grid_thw=grid.tolist(), consumed_pixel_values=tensor_fingerprint(inputs['pixel_values']),
            processed_image_size_wh=[int(grid[0,2])*processor.image_processor.patch_size,
                                     int(grid[0,1])*processor.image_processor.patch_size])
    return inputs, presentation


def validate_generation(presentation, raw, logits, tokenizer, eos_ids, vocab_size):
    # Reuse native input/forward/logit/decode/EOS validation; parse only our registered fields.
    result = native.validate_generation(presentation, raw, logits, tokenizer, eos_ids, vocab_size)
    parsed = parse_label(raw['decoded_text'], presentation['condition'])
    valid = result['terminal_eos'] and not result['unexpected_special_token'] and parsed['status']=='valid'
    return {**result, 'status':'valid' if valid else 'invalid',
            'label':parsed['label'] if valid else None, 'parsed_label':parsed}


def _run(args, recorder):
    import torch
    from transformers import AutoConfig, AutoProcessor, Qwen2_5_VLForConditionalGeneration
    source, model_path = Path(args.source), Path(args.model_path)
    manifest = load_inputs(source)
    if len(args.evaluation_sha256)!=64 or any(c not in '0123456789abcdef' for c in args.evaluation_sha256):
        raise ValueError('preregistered evaluator-label hash required before preflight/generation')
    identity = model_identity(model_path)
    control = None
    if getattr(args, 'capability_registration', None):
        from .vlm_capability_control import registered_model
        control = registered_model(args, identity)
    if identity['content_id'] != (control['content_id'] if control else MODEL_CONTENT_ID):
        raise ValueError('checkpoint differs from pinned visual-verification model')
    torch.set_num_threads(4)
    random.seed(1)
    np.random.seed(1)
    torch.manual_seed(1)
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=False, use_fast=False)
    config = AutoConfig.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    generation = native.make_generation(model_path)
    expected = deepcopy(config)
    expected.dtype = torch.bfloat16
    for name in expected.sub_configs:
        getattr(expected,name).dtype = torch.bfloat16
    expected._attn_implementation = 'sdpa'
    names = {'vlm_world_single_relation.py','vlm_world_relations.py','visual_subgoal_probe.py','visual_target_verification.py','visual_target_verification_run.py',
             'point_grounding_probe.py','records.py','vlm_capability_control.py'}
    code = code_identity()
    frozen = {'manifest_sha256':file_hash(source/'manifest.json'), 'protocol_sha256':file_hash(PROTOCOL),
        'evaluation_sha256':args.evaluation_sha256, 'safe_input_manifest':manifest,
        'model':identity, 'revision':control['revision'] if control else REVISION,
        **({'capability_control':control} if control else {}), 'model_config':serialize_model_config(config.to_dict()),
        'expected_loaded_config':serialize_model_config(expected.to_dict()),
        'generation_config':serialize_model_config(generation.to_dict()),
        'processor_config':serialize_model_config(processor.image_processor.to_dict()),
        'processor_class':type(processor).__name__, 'image_processor_class':type(processor.image_processor).__name__,
        'processor_use_fast':False, 'relevant_source_sha256':{p:h for p,h in code['source_sha256'].items() if Path(p).name in names},
        'versions':versions(), 'seed':1, 'torch_threads':4, 'dtype':'torch.bfloat16', 'attention':'sdpa'}
    options = {}
    for label in LABELS:
        ids = processor.tokenizer(label,add_special_tokens=False,truncation=False)['input_ids']
        if not ids or len(ids)+1>GENERATION['max_new_tokens'] or processor.tokenizer.decode(ids,skip_special_tokens=True)!=label:
            raise ValueError('label not representable within fixed output budget')
        options[label] = ids
    prepared = [prepare_call(processor,source,call,manifest['examples']) for call in PLANNED_CALLS]
    if control:
        from .vlm_capability_control import compare_to_baseline
        recorder.record('baseline_presentation_comparison', compare_to_baseline(args, [p for _,p in prepared]))
    if any(p['input_token_count']+GENERATION['max_new_tokens']>config.max_position_embeddings for _,p in prepared):
        raise ValueError('model context would truncate input')
    if args.mode=='generate':
        prior, diagnostics = load_records(Path(args.preflight_source)/'episodes.jsonl')
        if diagnostics or native.unique(prior,'termination')!={'reason':'preflight_complete','planned_calls':24}:
            raise ValueError('complete preflight required')
        if native.unique(prior,'frozen_inputs')!=frozen or native.unique(prior,'label_tokens')!=options:
            raise ValueError('frozen inputs/model/code/settings/evaluation changed after preflight')
        if [r['data'] for r in prior if r['kind']=='presentation'] != [p for _,p in prepared]:
            raise ValueError('processor inputs changed after preflight')
    recorder.record('frozen_inputs',frozen)
    recorder.record('label_tokens',options)
    for _, presentation in prepared:
        recorder.record('presentation',presentation)
    if args.mode=='preflight':
        recorder.record('termination',{'reason':'preflight_complete','planned_calls':24})
        return
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_path,local_files_only=True,
        trust_remote_code=False,torch_dtype=torch.bfloat16,attn_implementation='sdpa').to(args.device).eval()
    if (serialize_model_config(model.config.to_dict())!=frozen['expected_loaded_config']
            or model.dtype is not torch.bfloat16 or model.training or model.config._attn_implementation!='sdpa'):
        raise ValueError('loaded model config/dtype/eval/attention differs from preflight')
    recorder.record('model_loaded',{'config':serialize_model_config(model.config.to_dict()),'dtype':str(model.dtype),
        'device':str(model.device),'training':model.training,'attention':model.config._attn_implementation,
        'generation_config':serialize_model_config(generation.to_dict()),
        'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'gpu_name':torch.cuda.get_device_name(args.device),
        'gpu_total_memory':torch.cuda.get_device_properties(args.device).total_memory,
        'torch_threads':torch.get_num_threads(),'deterministic_algorithms':torch.are_deterministic_algorithms_enabled()})
    for original, presentation in prepared:
        call_id = presentation['call_id']
        inputs = {k:v.to(args.device) for k,v in original.items()}
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
        hook = model.register_forward_pre_hook(observe,with_kwargs=True)
        recorder.record('call_started',{k:presentation[k] for k in CALL_KEYS})
        torch.cuda.synchronize(args.device)
        torch.cuda.reset_peak_memory_stats(args.device)
        started = time.perf_counter()
        try:
            with torch.no_grad():
                response = model.generate(**inputs,generation_config=generation)
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
            np.savez_compressed(stream,logits=logits)
            stream.flush()
            os.fsync(stream.fileno())
        raw = {**{k:presentation[k] for k in CALL_KEYS},'sequence_ids':sequence,'generated_ids':generated,
            'raw_decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=False),
            'decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=True),'forward_traces':traces,
            'latency_s':elapsed,'logits_artifact':str(artifact),
            'logits_sha256':file_hash(Path(args.output)/artifact),
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(args.device),
            'peak_reserved_bytes':torch.cuda.max_memory_reserved(args.device)}
        recorder.record('raw_response',raw)
        result = validate_generation(presentation,raw,logits,processor.tokenizer,generation.eos_token_id,config.vocab_size)
        recorder.record('call_completed',{**{k:presentation[k] for k in CALL_KEYS},**result})
    recorder.record('termination',{'reason':'generation_complete','planned_calls':24})


def run(args):
    recorder = RunRecorder(args.output,{'mode':args.mode,'source':str(Path(args.source).resolve()),
        'preflight_source':args.preflight_source,'evaluation_sha256':args.evaluation_sha256,
        **({'capability_registration':args.capability_registration} if getattr(args,'capability_registration',None) else {}),
        'inference_settings':GENERATION,'oracle':False,'privileged':False,'no_execution':True},
        {'run_id':Path(args.output).name,'code':code_identity(),'versions':versions()})
    try:
        _run(args,recorder)
    except Exception as exc:
        recorder.record('failure',{'reason':repr(exc),'retries':0})
        raise
    finally:
        recorder.close()


def score_calls(calls, evaluation):
    if [{k: c[k] for k in CALL_KEYS} for c in calls] != PLANNED_CALLS:
        raise ValueError('exactly twenty-four completed calls in registered order required')
    if [r['call_id'] for r in evaluation['calls']] != [r['call_id'] for r in PLANNED_CALLS]:
        raise ValueError('evaluator call order differs')
    rows = []
    for call, gold in zip(calls, evaluation['calls']):
        allowed = gold['acceptable_labels']
        if not allowed or not set(allowed) <= set(FIELD_OPTIONS[call['condition']]):
            raise ValueError('evaluator label vocabulary differs')
        correct = call['status'] == 'valid' and call['label'] in allowed
        rows.append({**call, 'acceptable_labels': allowed, 'correct': correct,
            'useful_correct': correct and call['label'] != 'uncertain'})
    def group(selected):
        return {'denominator': len(selected), 'correct': sum(r['correct'] for r in selected),
            'useful_correct': sum(r['useful_correct'] for r in selected),
            'invalid': sum(r['status'] != 'valid' for r in selected),
            'uncertain': sum(r['label'] == 'uncertain' for r in selected)}
    scene_rows = [r for r in rows if r['image_index'] is not None and r['image_index'] != 6]
    controls = [r for r in rows if r not in scene_rows]
    by_id = {r['call_id']: r for r in rows}
    flip = {'left': 'right', 'right': 'left', 'aligned': 'aligned', 'uncertain': 'uncertain'}
    pairs = []
    for field in FIELDS:
        for original in parent.PARENT_INDICES:
            first, second = (by_id[f'{field}-{kind}-{original}'] for kind in ('original', 'mirror'))
            valid = first['status'] == second['status'] == 'valid'
            transformed = flip.get(first['label']) if field == 'horizontal' else first['label']
            pairs.append({'field': field, 'original_image_index': original, 'valid_pair': valid,
                'mirror_consistent': valid and transformed == second['label'],
                'both_correct': first['correct'] and second['correct']})
    coherent = []
    for base in BASE_CALLS[2:]:
        bundle = [by_id[field+base['call_id'].removeprefix('neutral')] for field in FIELDS]
        coherent.append({'image_index': base['image_index'], 'all_fields_correct': all(r['correct'] for r in bundle),
            'independent_answers': [r['label'] for r in bundle]})
    return {'rows': rows, 'scene_fields': group(scene_rows), 'abstention_controls': group(controls),
        'fields': {field: {'scenes': group([r for r in scene_rows if r['condition'] == field]),
                          'controls': group([r for r in controls if r['condition'] == field])} for field in FIELDS},
        'mirror_pairs': pairs, 'coherent_scenes_from_independent_questions': coherent,
        'coherent_scene_count': sum(r['all_fields_correct'] for r in coherent),
        'coherent_scene_denominator': len(coherent),
        'scope': 'three independent single-image geometry questions; no physical inference; dependent mirrors'}


def summarize(output, evaluation_path):
    from transformers import AutoProcessor
    output = Path(output)
    rows, diagnostics = load_records(output/'episodes.jsonl')
    if diagnostics or any(r['kind']=='failure' for r in rows):
        raise ValueError('complete failure-free evidence required for primary summary')
    config = native.unique(rows,'run_start')['resolved_config']
    frozen = native.unique(rows,'frozen_inputs')
    if (file_hash(evaluation_path)!=config['evaluation_sha256']
            or frozen['evaluation_sha256']!=config['evaluation_sha256']):
        raise ValueError('preregistered evaluator identity changed')
    evaluation = json.loads(Path(evaluation_path).read_text())
    if evaluation['input_manifest_sha256']!=frozen['manifest_sha256']:
        raise ValueError('evaluator labels do not bind the frozen image manifest')
    if native.unique(rows,'termination')!={'reason':'generation_complete','planned_calls':24}:
        raise ValueError('twenty-four-call generation did not complete')
    if (load_inputs(config['source'])!=frozen['safe_input_manifest']
            or file_hash(Path(config['source'])/'manifest.json')!=frozen['manifest_sha256']):
        raise ValueError('frozen source manifest changed')
    starts = [r['data'] for r in rows if r['kind']=='call_started']
    if starts != PLANNED_CALLS:
        raise ValueError('call intent/order differs')
    processor = AutoProcessor.from_pretrained(frozen['model']['path'],local_files_only=True,trust_remote_code=False,use_fast=False)
    presentations = [r['data'] for r in rows if r['kind']=='presentation']
    raw = [r['data'] for r in rows if r['kind']=='raw_response']
    completed = [r['data'] for r in rows if r['kind']=='call_completed']
    if len(presentations)!=24 or len(raw)!=24 or len(completed)!=24:
        raise ValueError('incomplete/extra call evidence')
    eos = frozen['generation_config']['value']['eos_token_id']
    vocab = frozen['model_config']['value']['vocab_size']
    for planned,presentation,response,completion in zip(PLANNED_CALLS,presentations,raw,completed):
        if any(any(item[k]!=v for k,v in planned.items()) for item in (presentation,response,completion)):
            raise ValueError('call-to-input lineage changed')
        artifact = output/response['logits_artifact']
        if file_hash(artifact)!=response['logits_sha256']:
            raise ValueError('native logits artifact changed')
        with np.load(artifact,allow_pickle=False) as arrays:
            result = validate_generation(presentation,response,arrays['logits'],processor.tokenizer,eos,vocab)
        if completion != {**planned,**result}:
            raise ValueError('stored outcome differs from native audit')
    return {'raw_sha256':file_hash(output/'episodes.jsonl'),'evaluation_sha256':config['evaluation_sha256'],
            **score_calls(completed,evaluation)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'preflight', 'generate', 'summarize'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--source')
    parser.add_argument('--evaluation-sha256')
    parser.add_argument('--evaluation')
    parser.add_argument('--model-path', default=native.MODEL_PATH)
    parser.add_argument('--preflight-source')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    if args.mode == 'prepare':
        if not args.source:
            parser.error('prepare requires --source')
        print(json.dumps(prepare(args.source, args.output), indent=2))
    elif args.mode == 'summarize':
        if not args.evaluation:
            parser.error('summarize requires --evaluation')
        print(json.dumps(summarize(args.output, args.evaluation), indent=2))
    elif not args.source or not args.evaluation_sha256 or args.mode == 'generate' and not args.preflight_source:
        parser.error('preflight/generate require source and evaluator hash; generate also needs preflight')
    else:
        run(args)


if __name__ == '__main__':
    main()
