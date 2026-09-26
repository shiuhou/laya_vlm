"""Seven offline task/RGB provisional-subgoal calls; no physical authorization."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image, ImageDraw

from .point_grounding_probe import serialize_model_config
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .visual_target_verification import GENERATION, MODEL_REPO, tensor_fingerprint
from . import visual_target_verification_run as native
from .visual_target_verification_run import REVISION

VERSION = 'visual-subgoal-probe-v1'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/visual_subgoal_probe_protocol.md'
VIDEO_SHA256 = '22abc6df7615bcf058ca5ae1de0bdf7d0b39d862c0654d3c02bc3027a508dda5'
VIDEO = 'runs/privileged-reference/task2-permissive-diagnostic-53mm/media/task2-permissive-diagnostic-53mm-20fps.mp4'
FRAMES = (7, 55, 135, 183, 239, 319)
LABELS = ('approach_object', 'establish_grasp', 'transport_object', 'place_object', 'release_object',
          'approach_drawer', 'establish_drawer_contact', 'advance_drawer', 'uncertain')
INSTRUCTION = (
    'Task: pick the wine bottle from the tabletop, place it inside the bottom drawer, release it, '
    'then close the drawer. Choose the best provisional next local objective using the available '
    'observation. This proposal does not authorize execution; physical preconditions require '
    'independent verification. Do not assume hidden grasp strength or placement fit. If the '
    'observation cannot support a useful choice, return uncertain. Return exactly one allowed '
    'label: approach_object, establish_grasp, transport_object, place_object, release_object, '
    'approach_drawer, establish_drawer_contact, advance_drawer, uncertain.'
)
PLANNED_CALLS = [{'call_id':'text-only', 'image_index':None}] + [
    {'call_id':f'rgb-{i}', 'image_index':i} for i in range(len(FRAMES))]
MODEL_CONTENT_ID = '11fccd61f55d2716ae7f8d4e28790b58b63d4126ade6994cef640a3cf337aa33'


def parse_label(text):
    value = text.strip()
    return {'status':'valid' if value in LABELS else 'invalid', 'label':value if value in LABELS else None}


def prepare(video, output):
    """Sequential decode and camera crop only; no trace/oracle/phase input."""
    import cv2
    video, output = Path(video), Path(output)
    if file_hash(video) != VIDEO_SHA256:
        raise ValueError('frozen source-video identity mismatch')
    if output.exists():
        raise FileExistsError('fresh preparation directory required')
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG)
    try:
        if not capture.isOpened():
            raise ValueError('source video cannot be decoded')
        metadata = {'width':int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height':int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'fps':capture.get(cv2.CAP_PROP_FPS),
                    'frame_count_reported':int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
                    'backend':capture.getBackendName(), 'opencv_version':cv2.__version__}
        if (metadata['width'], metadata['height'], metadata['fps']) != (960,600,20.):
            raise ValueError('source-video dimensions/rate differ')
        selected = {}
        for index in range(max(FRAMES)+1):
            ok, bgr = capture.read()
            if not ok or bgr.shape != (600,960,3) or bgr.dtype != np.uint8:
                raise ValueError(f'source frame {index} unavailable or changed format')
            if index in FRAMES:
                selected[index] = cv2.cvtColor(bgr[:,:600], cv2.COLOR_BGR2RGB)
    finally:
        capture.release()
    output.mkdir(parents=True)
    examples = []
    sheet = Image.new('RGB', (1800,1260), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(FRAMES):
        name = f'rgb-{i}.png'
        image = Image.fromarray(selected[frame])
        image.save(output/name)
        examples.append({'image_index':i, 'rgb_artifact':name, 'rgb_sha256':file_hash(output/name),
                         'width':600, 'height':600})
        x, y = (i%3)*600, (i//3)*630
        sheet.paste(image,(x,y+30))
        draw.text((x+8,y+8),f'REVIEW ONLY: image {i}; source frame {frame}',fill='black')
    manifest = {'version':VERSION, 'protocol_sha256':file_hash(PROTOCOL), 'source_video_sha256':VIDEO_SHA256,
                'source_type':'lossy_resampled_primitive_trace_video_reconstruction',
                'not_original_control_replay_or_raw_sensor':True,
                'model_repo':MODEL_REPO, 'model_revision':REVISION, 'model_content_id':MODEL_CONTENT_ID,
                'instruction':INSTRUCTION, 'labels':list(LABELS), 'generation_settings':GENERATION,
                'repeats':1, 'planned_calls':PLANNED_CALLS, 'examples':examples}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sheet.save(output/'review-contact-sheet.png')
    (output/'extraction.json').write_text(json.dumps({'source_video':str(video.resolve()),
        'source_video_sha256':VIDEO_SHA256, 'decoder':metadata, 'zero_based_frame_indices':list(FRAMES),
        'decode':'sequential from frame0; no seek', 'crop_xyxy':[0,0,600,600],
        'color_conversion':'OpenCV BGR to RGB; no resizing/annotation in model images',
        'manifest_sha256':file_hash(output/'manifest.json')},indent=2)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return manifest


def load_inputs(source):
    source = Path(source)
    manifest = json.loads((source/'manifest.json').read_text())
    expected = {'version':VERSION, 'protocol_sha256':file_hash(PROTOCOL), 'source_video_sha256':VIDEO_SHA256,
        'source_type':'lossy_resampled_primitive_trace_video_reconstruction',
        'not_original_control_replay_or_raw_sensor':True, 'model_repo':MODEL_REPO, 'model_revision':REVISION,
        'model_content_id':MODEL_CONTENT_ID, 'instruction':INSTRUCTION, 'labels':list(LABELS),
        'generation_settings':GENERATION, 'repeats':1, 'planned_calls':PLANNED_CALLS}
    if set(manifest) != {*expected,'examples'} or any(manifest[k] != v for k,v in expected.items()):
        raise ValueError('registered model/prompt/protocol/seven-call settings changed')
    if [e['image_index'] for e in manifest['examples']] != list(range(6)):
        raise ValueError('registered six-image order changed')
    for i, example in enumerate(manifest['examples']):
        if (set(example) != {'image_index','rgb_artifact','rgb_sha256','width','height'}
                or example['rgb_artifact'] != f'rgb-{i}.png' or (example['width'],example['height']) != (600,600)):
            raise ValueError('unexpected image fields or shape')
        path = source/example['rgb_artifact']
        if path.resolve().parent != source.resolve() or file_hash(path) != example['rgb_sha256']:
            raise ValueError('prepared image changed or escaped source')
        with Image.open(path) as image:
            if image.mode != 'RGB' or image.size != (600,600):
                raise ValueError('prepared RGB format changed')
    return manifest


def prepare_call(processor, source, planned, examples):
    import torch
    example = None if planned['image_index'] is None else examples[planned['image_index']]
    content = [] if example is None else [{'type':'image'}]
    messages = [{'role':'user','content':content+[{'type':'text','text':INSTRUCTION}]}]
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
    # Reuse full native input/forward/logit/decode/EOS validation; only label vocabulary differs.
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
    names = {'visual_subgoal_probe.py','visual_target_verification.py','visual_target_verification_run.py',
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
        if diagnostics or native.unique(prior,'termination')!={'reason':'preflight_complete','planned_calls':7}:
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
        recorder.record('termination',{'reason':'preflight_complete','planned_calls':7})
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
        recorder.record('call_started',{'call_id':call_id,'image_index':presentation['image_index']})
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
        raw = {'call_id':call_id,'image_index':presentation['image_index'],'sequence_ids':sequence,'generated_ids':generated,
            'raw_decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=False),
            'decoded_text':processor.tokenizer.decode(generated,skip_special_tokens=True),'forward_traces':traces,
            'latency_s':elapsed,'logits_artifact':str(artifact),
            'logits_sha256':file_hash(Path(args.output)/artifact),
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(args.device),
            'peak_reserved_bytes':torch.cuda.max_memory_reserved(args.device)}
        recorder.record('raw_response',raw)
        result = validate_generation(presentation,raw,logits,processor.tokenizer,generation.eos_token_id,config.vocab_size)
        recorder.record('call_completed',{'call_id':call_id,'image_index':presentation['image_index'],**result})
    recorder.record('termination',{'reason':'generation_complete','planned_calls':7})


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
    if [(c['call_id'],c['image_index']) for c in calls] != [(c['call_id'],c['image_index']) for c in PLANNED_CALLS]:
        raise ValueError('exactly seven completed calls in registered order required')
    examples = evaluation['examples']
    if [e['image_index'] for e in examples] != list(range(6)):
        raise ValueError('six evaluator rows required')
    baseline = calls[0]
    rows = []
    for call, example in zip(calls[1:],examples):
        i = example['image_index']
        primary = i < 3
        allowed = example['acceptable_labels']
        if (example['primary_evaluation'] is not primary
                or primary and (not isinstance(allowed,list) or not allowed or not set(allowed)<=set(LABELS))
                or not primary and allowed is not None):
            raise ValueError('primary/exploratory evaluator scope changed')
        accepted = call['status']=='valid' and call['label'] in allowed if primary else None
        baseline_accepted = baseline['status']=='valid' and baseline['label'] in allowed if primary else None
        rows.append({**call,'primary_evaluation':primary,'acceptable_labels':allowed,
            'annotation_agreement':accepted,'useful_accepted_proposal':accepted and call['label']!='uncertain' if primary else None,
            'task_only_annotation_agreement':baseline_accepted,
            'changed_from_task_only':call['label']!=baseline['label'] or call['status']!=baseline['status']})
    primary_rows = [r for r in rows if r['primary_evaluation']]
    return {'task_only':baseline,'rows':rows,'primary_denominator':3,
        'primary_annotation_agreements':sum(r['annotation_agreement'] for r in primary_rows),
        'primary_useful_accepted_proposals':sum(r['useful_accepted_proposal'] for r in primary_rows),
        'task_only_primary_annotation_agreements':sum(r['task_only_annotation_agreement'] for r in primary_rows),
        'rgb_uncertain_count':sum(r['label']=='uncertain' for r in rows),
        'rgb_invalid_count':sum(r['status']!='valid' for r in rows),
        'scope':'three primary visual-label cases; three descriptive cases; no physical authorization'}


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
    if native.unique(rows,'termination')!={'reason':'generation_complete','planned_calls':7}:
        raise ValueError('seven-call generation did not complete')
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
    if len(presentations)!=7 or len(raw)!=7 or len(completed)!=7:
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
    parser.add_argument('mode',choices=['prepare','preflight','generate','summarize'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--video',default=VIDEO)
    parser.add_argument('--source')
    parser.add_argument('--evaluation-sha256')
    parser.add_argument('--evaluation')
    parser.add_argument('--model-path',default=native.MODEL_PATH)
    parser.add_argument('--preflight-source')
    parser.add_argument('--device',default='cuda')
    args = parser.parse_args()
    if args.mode=='prepare':
        print(json.dumps(prepare(args.video,args.output),indent=2))
    elif args.mode=='summarize':
        if not args.evaluation:
            parser.error('summarize requires --evaluation')
        print(json.dumps(summarize(args.output,args.evaluation),indent=2))
    elif not args.source or not args.evaluation_sha256 or args.mode=='generate' and not args.preflight_source:
        parser.error('preflight/generate require --source and --evaluation-sha256; generate also requires --preflight-source')
    else:
        run(args)


if __name__=='__main__':
    main()
