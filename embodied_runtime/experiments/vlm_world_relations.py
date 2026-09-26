"""Frozen task-independent visible-relation probe with mirror and context controls."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image, ImageOps
from itertools import product

from . import visual_subgoal_probe as parent

from .point_grounding_probe import serialize_model_config
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .visual_target_verification import GENERATION, MODEL_REPO, tensor_fingerprint
from . import visual_target_verification_run as native
from .visual_target_verification_run import REVISION

VERSION = 'vlm-world-relations-v1'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/vlm_world_relations_protocol.md'
MODEL_CONTENT_ID = parent.MODEL_CONTENT_ID
PARENT_INDICES = (0, 2, 4)
FIELD_OPTIONS = (('left', 'right', 'aligned', 'uncertain'),
                 ('separated', 'adjacent', 'uncertain'), ('upright', 'diagonal', 'uncertain'))
LABELS = tuple(','.join(values) for values in product(*FIELD_OPTIONS))
NEUTRAL = (
    'Report only visible image geometry, not an action or hidden physical state. '
    'Give three labels in this order, separated by commas and with no other text. '
    "First: where is the bottle's center horizontally relative to the visible open drawer interior? "
    'left = left of the interior; right = right of it; aligned = within its horizontal extent; '
    'uncertain = cannot determine. '
    "Second: is there a clear visible gap between the bottle and the robot's gripper fingertips? "
    'separated = clear gap; adjacent = visibly next to or overlapping the fingertips; '
    'uncertain = cannot determine. This does not ask whether the robot securely holds the bottle. '
    "Third: is the bottle's long axis upright or diagonal in the image? "
    'upright = approximately vertical; diagonal = clearly tilted; uncertain = cannot determine. '
    'If no image is available or the objects are not visible, use uncertain for each unsupported field. '
    'Format: left/right/aligned/uncertain,separated/adjacent/uncertain,upright/diagonal/uncertain'
)
TASK_PREFIX = ('Task: pick the wine bottle from the tabletop, place it inside the bottom drawer, '
               'release it, then close the drawer.\n')
INSTRUCTIONS = {'neutral': NEUTRAL, 'task': TASK_PREFIX + NEUTRAL}
PLANNED_CALLS = [
    {'call_id': 'neutral-text', 'image_index': None, 'condition': 'neutral'},
    {'call_id': 'neutral-gray', 'image_index': 6, 'condition': 'neutral'},
] + [
    {'call_id': f'neutral-{kind}-{original}', 'image_index': 2*i+j, 'condition': 'neutral'}
    for i, original in enumerate(PARENT_INDICES) for j, kind in enumerate(('original', 'mirror'))
] + [
    {'call_id': 'task-text', 'image_index': None, 'condition': 'task'},
] + [
    {'call_id': f'task-original-{original}', 'image_index': 2*i, 'condition': 'task'}
    for i, original in enumerate(PARENT_INDICES)
]
CALL_KEYS = ('call_id', 'image_index', 'condition')


def parse_label(text):
    values = [part.strip() for part in text.strip().split(',')]
    valid = len(values) == 3 and all(v in allowed for v, allowed in zip(values, FIELD_OPTIONS))
    return {'status': 'valid' if valid else 'invalid', 'label': ','.join(values) if valid else None}


def expected_manifest(source):
    source = Path(source).resolve()
    original = parent.load_inputs(source)
    return {'version': VERSION, 'protocol_sha256': file_hash(PROTOCOL),
        'parent_directory': str(source), 'parent_manifest_sha256': file_hash(source/'manifest.json'),
        'source_type': original['source_type'], 'not_original_control_replay_or_raw_sensor': True,
        'model_repo': MODEL_REPO, 'model_revision': REVISION, 'model_content_id': MODEL_CONTENT_ID,
        'instructions': INSTRUCTIONS, 'field_options': FIELD_OPTIONS,
        'generation_settings': GENERATION, 'planned_calls': PLANNED_CALLS}


def prepare(source, output):
    source, output = Path(source), Path(output)
    manifest = expected_manifest(source)
    output.mkdir(parents=True, exist_ok=False)
    examples = []
    for original in PARENT_INDICES:
        source_path = source/f'rgb-{original}.png'
        with Image.open(source_path) as opened:
            image = opened.copy()
        for variant in ('original', 'mirror'):
            index = len(examples)
            path = output/f'image-{index}.png'
            (image if variant == 'original' else ImageOps.mirror(image)).save(path)
            examples.append({'image_index': index, 'rgb_artifact': path.name,
                'rgb_sha256': file_hash(path), 'width': 600, 'height': 600,
                'parent_image_index': original, 'parent_rgb_sha256': file_hash(source_path),
                'transform': 'identity' if variant == 'original' else 'horizontal_mirror'})
    path = output/'image-6.png'
    Image.new('RGB', (600, 600), (128, 128, 128)).save(path)
    examples.append({'image_index': 6, 'rgb_artifact': path.name, 'rgb_sha256': file_hash(path),
        'width': 600, 'height': 600, 'parent_image_index': None, 'parent_rgb_sha256': None,
        'transform': 'uniform_gray_128'})
    manifest['examples'] = examples
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return load_inputs(output)


def load_inputs(source):
    source = Path(source)
    manifest = json.loads((source/'manifest.json').read_text())
    expected = expected_manifest(manifest['parent_directory'])
    expected = json.loads(json.dumps(expected))
    if set(manifest) != {*expected, 'examples'} or any(manifest[k] != v for k, v in expected.items()):
        raise ValueError('registered twelve-call settings or parent provenance changed')
    examples = manifest['examples']
    if [e['image_index'] for e in examples] != list(range(7)):
        raise ValueError('registered image order changed')
    for i, example in enumerate(examples):
        expected_parent = None if i == 6 else PARENT_INDICES[i//2]
        transform = 'uniform_gray_128' if i == 6 else 'horizontal_mirror' if i % 2 else 'identity'
        if (set(example) != {'image_index', 'rgb_artifact', 'rgb_sha256', 'width', 'height',
                'parent_image_index', 'parent_rgb_sha256', 'transform'}
                or example['parent_image_index'] != expected_parent or example['transform'] != transform
                or example['rgb_artifact'] != f'image-{i}.png'
                or (example['width'], example['height']) != (600, 600)):
            raise ValueError('unexpected image fields or lineage')
        path = source/example['rgb_artifact']
        if path.resolve().parent != source.resolve() or file_hash(path) != example['rgb_sha256']:
            raise ValueError('prepared image changed or escaped source')
        with Image.open(path) as opened:
            if opened.mode != 'RGB' or opened.size != (600, 600):
                raise ValueError('prepared RGB format changed')
            actual = np.asarray(opened)
        if expected_parent is None:
            if example['parent_rgb_sha256'] is not None or not np.all(actual == 128):
                raise ValueError('gray control differs')
        else:
            parent_path = Path(manifest['parent_directory'])/f'rgb-{expected_parent}.png'
            if example['parent_rgb_sha256'] != file_hash(parent_path):
                raise ValueError('parent RGB identity differs')
            with Image.open(parent_path) as opened:
                expected_pixels = np.asarray(opened if transform == 'identity' else ImageOps.mirror(opened))
            if not np.array_equal(actual, expected_pixels):
                raise ValueError('registered image transformation differs')
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
    parsed = parse_label(raw['decoded_text'])
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
    if identity['content_id'] != MODEL_CONTENT_ID:
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
    names = {'vlm_world_relations.py','visual_subgoal_probe.py','visual_target_verification.py','visual_target_verification_run.py',
             'point_grounding_probe.py','records.py'}
    code = code_identity()
    frozen = {'manifest_sha256':file_hash(source/'manifest.json'), 'protocol_sha256':file_hash(PROTOCOL),
        'evaluation_sha256':args.evaluation_sha256, 'safe_input_manifest':manifest,
        'model':identity, 'revision':REVISION, 'model_config':serialize_model_config(config.to_dict()),
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
    if any(p['input_token_count']+GENERATION['max_new_tokens']>config.max_position_embeddings for _,p in prepared):
        raise ValueError('model context would truncate input')
    if args.mode=='generate':
        prior, diagnostics = load_records(Path(args.preflight_source)/'episodes.jsonl')
        if diagnostics or native.unique(prior,'termination')!={'reason':'preflight_complete','planned_calls':12}:
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
        recorder.record('termination',{'reason':'preflight_complete','planned_calls':12})
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
    recorder.record('termination',{'reason':'generation_complete','planned_calls':12})


def run(args):
    recorder = RunRecorder(args.output,{'mode':args.mode,'source':str(Path(args.source).resolve()),
        'preflight_source':args.preflight_source,'evaluation_sha256':args.evaluation_sha256,
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
        raise ValueError('exactly twelve completed calls in registered order required')
    labels = evaluation['calls']
    if [row['call_id'] for row in labels] != [p['call_id'] for p in PLANNED_CALLS]:
        raise ValueError('evaluator call order differs')
    rows = []
    for call, label in zip(calls, labels):
        allowed = label['acceptable_fields']
        if len(allowed) != 3 or any(not values or not set(values) <= set(options)
                for values, options in zip(allowed, FIELD_OPTIONS)):
            raise ValueError('evaluator field vocabulary differs')
        fields = call['label'].split(',') if call['status'] == 'valid' else [None]*3
        agreements = [value in values for value, values in zip(fields, allowed)]
        rows.append({**call, 'fields': fields, 'acceptable_fields': allowed,
            'field_agreements': agreements, 'all_fields_agree': all(agreements),
            'useful_correct_fields': sum(agree and value != 'uncertain' for agree, value in zip(agreements, fields))})
    def group(selected):
        return {'denominator_images': len(selected), 'all_field_agreements': sum(r['all_fields_agree'] for r in selected),
            'field_agreements': [sum(r['field_agreements'][i] for r in selected) for i in range(3)],
            'useful_correct_fields': sum(r['useful_correct_fields'] for r in selected),
            'denominator_fields': 3*len(selected), 'invalid_count': sum(r['status'] != 'valid' for r in selected),
            'uncertain_field_count': sum(r['fields'].count('uncertain') for r in selected)}
    by_id = {r['call_id']: r for r in rows}
    pairs = []
    flip = {'left': 'right', 'right': 'left', 'aligned': 'aligned', 'uncertain': 'uncertain'}
    for i in PARENT_INDICES:
        original, mirror = (by_id[f'neutral-{variant}-{i}'] for variant in ('original', 'mirror'))
        valid = original['status'] == mirror['status'] == 'valid'
        transformed = [flip.get(original['fields'][0]), *original['fields'][1:]]
        pairs.append({'original_image_index': i, 'valid_pair': valid,
            'mirror_consistent': valid and transformed == mirror['fields'],
            'both_correct': original['all_fields_agree'] and mirror['all_fields_agree'],
            'original_fields': original['fields'], 'mirror_fields': mirror['fields']})
    comparison = []
    for i in PARENT_INDICES:
        neutral, task = by_id[f'neutral-original-{i}'], by_id[f'task-original-{i}']
        comparison.append({'original_image_index': i, 'neutral': neutral['fields'], 'task': task['fields'],
            'neutral_correct': neutral['all_fields_agree'], 'task_correct': task['all_fields_agree'],
            'changed': neutral['fields'] != task['fields'] or neutral['status'] != task['status']})
    return {'rows': rows, 'neutral_scenes': group(rows[2:8]),
        'neutral_originals': group([by_id[f'neutral-original-{i}'] for i in PARENT_INDICES]),
        'neutral_mirrors': group([by_id[f'neutral-mirror-{i}'] for i in PARENT_INDICES]),
        'abstention_controls': group([rows[0], rows[1], rows[8]]),
        'task_scenes': group(rows[9:]), 'mirror_pairs': pairs, 'task_prefix_comparison': comparison,
        'scope': 'coarse visible image geometry only; mirror pairs are dependent controls; no physical inference'}


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
    if native.unique(rows,'termination')!={'reason':'generation_complete','planned_calls':12}:
        raise ValueError('twelve-call generation did not complete')
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
    if len(presentations)!=12 or len(raw)!=12 or len(completed)!=12:
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
