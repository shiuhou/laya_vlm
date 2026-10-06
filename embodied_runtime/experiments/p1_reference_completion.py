"""One preregistered reference POINT call; budget-only decoder intervention.

Archive BOX reuse is explicit. Incomplete output is sealed raw and stops BEFORE
any POINT parsing, support geometry or tracker. No simulator or labels imported.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np

from ..contracts import require
from ..perception.semantic_output import parse_semantic_reply
from .p1_semantic_grounding import MODEL_CONTENT_ID, QUERIES, _cuda_allocation, _explicit_gpu_mask, frozen_geometry
from .p1_surface_dev import load_inputs, write
from .point_grounding_probe import SETTINGS, generation_audit, parse_grounding, serialize_model_config
from .records import code_identity, file_hash, jsonable, model_identity, versions

SOURCE = Path('runs/p1/surface-dev-20261006-capture02')
BASELINE = Path('runs/p1/surface-dev-gpu-20261006')
STEM = 'init-025-fixed_cabinet_reference'
BUDGET = 1024
PROTOCOL = Path('docs/research/p1_reference_completion_budget_protocol.md')
GPU_UUID = 'GPU-293fca5f-bdb8-2235-fa2e-18ab6c488b36'


def infer(output):
    import torch
    from PIL import Image
    from ..adapters.locateanything import LocateAnythingWorker

    folder = Path(output)
    require(not folder.exists(), 'fresh independent condition directory required')
    code = code_identity()
    require(not code['dirty_status'], 'clean inference revision required')
    source_registration, _ = load_inputs(SOURCE)
    source_index = json.loads(Path('docs/evidence/p1_grounding/surface_dev_20261006/artifact-index.json').read_text())
    for name, digest in source_index['files_sha256'].items():
        require(file_hash(SOURCE/name) == digest, 'original source changed')
    seal = json.loads((BASELINE/'stopped-seal.json').read_text())
    for name, digest in seal['artifacts_sha256'].items():
        require(file_hash(BASELINE/name) == digest, 'baseline reference evidence changed')
    mask = _explicit_gpu_mask()
    require(mask == GPU_UUID, 'same preregistered physical GPU UUID required')
    allocation = _cuda_allocation(torch, mask)
    config = source_registration['config']
    frozen_geometry(config['geometry_config'])
    identity = model_identity(config['model_path'])
    require(identity['content_id'] == MODEL_CONTENT_ID, 'checkpoint bytes changed')
    require(versions() == json.loads((BASELINE/'loading.json').read_text())['versions'], 'software versions changed')
    settings = {**SETTINGS, 'max_new_tokens': BUDGET}
    folder.mkdir(parents=True, exist_ok=False)
    write(folder/'registration.json', dict(registered_at_utc=datetime.now(timezone.utc).isoformat(), code=code,
        protocol_sha256=file_hash(PROTOCOL), source=str(SOURCE), baseline=str(BASELINE), model=identity,
        execution_allocation=allocation, versions=versions(), frozen_tracker_revision='ab361eb',
        frozen_evidence_revision='065ad2b', baseline_settings=SETTINGS, settings=settings,
        source_files_sha256=source_index['files_sha256'], baseline_files_sha256=seal['artifacts_sha256'],
        old_box_response_sha256=file_hash(BASELINE/f'{STEM}-box-response.json'),
        expected_model_calls=1, archived_box_calls=1, geometry_evaluated=False, point_parsed=False,
        no_annotations_or_simulator=True, no_robot_actions=True))
    torch.set_num_threads(config['torch_threads'])
    worker = LocateAnythingWorker(config['model_path'], device='cuda:0', dtype=config['dtype'],
                                  model_revision=identity['content_id'])
    torch.set_num_threads(config['torch_threads'])
    model_config = serialize_model_config(worker.model.config.to_dict())
    require(model_config == json.loads((BASELINE/'model_config.json').read_text()), 'resolved model config changed')
    write(folder/'model_config.json', model_config)
    request = json.loads((BASELINE/f'{STEM}-point-request.json').read_text())
    frame = request['frame']
    image_path = SOURCE/frame['image']
    require(file_hash(image_path) == frame['image_file_sha256'], 'RGB changed')
    image = Image.open(image_path).convert('RGB')
    require(hashlib.sha256(np.asarray(image).tobytes()).hexdigest() == frame['rgb_sha256'], 'RGB bytes changed')
    question = f"Point to: {QUERIES['fixed_cabinet_reference']}."
    require(request['question'] == question, 'reference query changed')
    messages = [{'role':'user', 'content':[{'type':'image','image':image}, {'type':'text','text':question}]}]
    template = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = worker.processor.process_vision_info(messages)
    tensors = worker.processor(text=[template], images=images, videos=videos, return_tensors='pt').to('cuda:0')
    ids = tensors['input_ids'].detach().cpu().tolist()[0]
    actual_request = dict(frame=frame, entity=request['entity'], mode='point', question=question, prompt=template,
        input_token_ids=ids,
        pixel_values_sha256=hashlib.sha256(tensors['pixel_values'].float().cpu().numpy().tobytes()).hexdigest(),
        pixel_values_hash_encoding='processor float32 contiguous bytes',
        image_grid_hws=jsonable(tensors['image_grid_hws'].detach().cpu().numpy()
            if hasattr(tensors['image_grid_hws'], 'detach') else tensors['image_grid_hws']))
    require(actual_request == request, 'entire model-facing input differs from sealed baseline', 'CONDITION_CHANGED')
    write(folder/f'{STEM}-point-request.json', actual_request)
    require(len(ids)+BUDGET <= worker.tokenizer.model_max_length, 'input/output exceed model context')
    observed, original_decode = [], worker.tokenizer.batch_decode

    def decode_audit(sequences, *args, **kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original_decode(sequences, *args, **kwargs)

    worker.tokenizer.batch_decode = decode_audit
    try:
        torch.cuda.synchronize(0)
        started = time.perf_counter()
        print('Starting one reference POINT, budget1024, identical input', flush=True)
        with torch.no_grad():
            raw = worker.model.generate(pixel_values=tensors['pixel_values'].to(worker.dtype),
                input_ids=tensors['input_ids'], attention_mask=tensors['attention_mask'],
                image_grid_hws=tensors.get('image_grid_hws'), tokenizer=worker.tokenizer, **settings)
        torch.cuda.synchronize(0)
        latency = time.perf_counter()-started
        require(len(observed) == 1 and len(observed[0]) == 1, 'actual generated token audit missing')
        raw = raw[0] if isinstance(raw, tuple) else raw
        require(isinstance(raw, str), 'raw model reply must be text')
        audit = generation_audit(observed[0][0], len(ids), worker.tokenizer.model_max_length,
                                worker.tokenizer.convert_tokens_to_ids('<|im_end|>'), max_new_tokens=BUDGET)
        response = dict(frame=frame, entity=request['entity'], mode='point', raw_output=raw,
                        audit=audit, latency_s=latency)
        # Persist all raw evidence first. Completion must pass before either
        # typed parsing or legacy compatibility projection can run.
        write(folder/f'{STEM}-point-response.json', response)
        completion = audit['complete_generation'] and 0 < len(observed[0][0]) <= audit['effective_limit']
        if not completion:
            write(folder/'outcome.json', dict(status='STOPPED_INCOMPLETE_GENERATION', model_calls=1,
                archived_box_calls=1, point_parsed=False, geometry_evaluated=False, tracker_started=False,
                generated_tokens=audit['actual_generated_token_count'], terminal_eos=audit['terminal_eos_observed'],
                effective_limit=audit['effective_limit'], latency_s=latency, verify_status='UNKNOWN'))
        else:
            typed = parse_semantic_reply(raw, image.width, image.height, mode='point', audit=audit)
            write(folder/'typed-point.json', typed.evidence())
            if not typed.admitted:
                write(folder/'outcome.json', dict(status='STOPPED_TYPED_POINT_REJECTED', model_calls=1,
                    point_parsed=True, geometry_evaluated=False, tracker_started=False, reason=typed.reason,
                    errors=typed.errors, verify_status='UNKNOWN'))
            else:
                response['parsed'] = parse_grounding(raw, image.width, image.height)
                # This pair contains one byte-identical archived BOX plus one
                # fresh POINT; sealing it never implies two fresh calls.
                pair = folder/'admitted-pair'
                pair.mkdir()
                for mode in ('box',):
                    for kind in ('request', 'response'):
                        shutil.copy2(BASELINE/f'{STEM}-{mode}-{kind}.json', pair/f'{STEM}-{mode}-{kind}.json')
                write(pair/f'{STEM}-point-request.json', actual_request)
                write(pair/f'{STEM}-point-response.json', response)
                write(pair/'loading.json', dict(inputs_sha256=file_hash(SOURCE/'inputs.json'),
                    registration_sha256=file_hash(SOURCE/'registration.json'),
                    selected_pair=STEM, fresh_model_calls=1, archived_box_calls=1, settings=settings, code=code))
                write(pair/'complete.json', dict(calls=2, fresh_model_calls=1, archived_box_calls=1,
                    selected_pair=STEM, artifacts_sha256={p.name:file_hash(p) for p in sorted(pair.glob('*.json'))}))
                write(folder/'outcome.json', dict(status='READY_FOR_SEPARATE_ASSOCIATION', model_calls=1,
                    archived_box_calls=1, point_parsed=True, geometry_evaluated=False, tracker_started=False,
                    verify_status='UNKNOWN'))
        write(folder/'sealed.json', dict(artifacts_sha256={str(p.relative_to(folder)):file_hash(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}, model_calls=1))
        print(json.dumps(json.loads((folder/'outcome.json').read_text())), flush=True)
    finally:
        worker.tokenizer.batch_decode = original_decode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    infer(args.output)


if __name__ == '__main__':
    main()
