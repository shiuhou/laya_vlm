"""Offline model-derived cabinet crop then drawer-front localization.

RGB-only acquisition proposals; no annotations, depth-to-model, policy or action.
The fixed crop is produced only from the same-frame coarse model BOX.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import time

from PIL import Image

from ..adapters.qwen3vl_grounding import (
    ADAPTER_REVISION, GREEDY_CALL_OVERRIDES, SYSTEM, TEMPLATES,
    Qwen3VLGroundingWorker, checkpoint_identity,
)
from ..contracts import content_hash, require
from ..perception.grounding_observation import (
    build_grounding_observation, build_mapped_grounding_observation, make_model_crop,
)
from .p1_qwen_localizer_dev import input_frames, deadline
from .p1_segmentation_probe import seal, write
from .records import code_identity, file_hash, versions

CONDITION = 'p1-qwen-model-crop-development/1'
COARSE_LABEL = 'tabletop_cabinet'
COARSE_QUERY = ('the small cabinet resting on the tabletop, including its drawers and outer housing, '
                'excluding the robot arm, gripper, tabletop, and other objects')
FINE_LABEL = 'drawer_front_pushable'
FINE_QUERY = ('the flat outward-facing front panel of the open top drawer, directly behind and attached '
              'to its protruding handle, excluding the handle itself, drawer interior, neighboring fixed '
              'cabinet panels, tabletop, and robot parts')


def call(worker, rgb, *, root, request_id, source_identity, mode, query, target_key,
         max_new_tokens, request_timeout_s, crop_binding=None):
    """Persist first request and reply, with no repair/retry of model outputs."""
    root.mkdir(exist_ok=False)
    write(root/'request.json', dict(request_id=request_id, source_identity=source_identity,
        input_rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(), input_rgb_shape=list(rgb.shape),
        mode=mode, query=query, target_key=target_key, crop_binding=crop_binding,
        max_new_tokens=max_new_tokens, request_timeout_s=request_timeout_s,
        started_at_utc=datetime.now(timezone.utc).isoformat(), hidden_retry=False))
    try:
        with deadline(request_timeout_s):
            reply = worker.infer(rgb, mode=mode, query=query, target_key=target_key, max_new_tokens=max_new_tokens)
        raw = root/'raw-output.txt'
        raw.write_text(reply['raw_output'], encoding='utf-8')
        kwargs = dict(request_id=request_id, source_identity=source_identity, query=query,
            target_key=target_key, frontend_id='Qwen3-VL-4B-Instruct-model-crop-2D',
            model_identity=worker.model_identity, processor_identity=worker.processor_identity,
            environment_identity=worker.environment_identity, audit=reply['audit'],
            input_evidence=reply['input_evidence'], terminal_special_tokens=reply['terminal_special_tokens'],
            timing=reply['timing'], raw_output_ref=str(raw.resolve()))
        if crop_binding is None:
            observation = build_grounding_observation(reply['typed'], expected_label=target_key, **kwargs)
        else:
            observation = build_mapped_grounding_observation(reply['typed'], crop_binding=crop_binding, **kwargs)
        write(root/'receipt.json', dict(reply, typed=reply['typed'].evidence()))
        write(root/'observation.json', observation)
    except Exception as exc:
        write(root/'failure.json', dict(error=repr(exc), hidden_retry=False,
              failed_at_utc=datetime.now(timezone.utc).isoformat()))
        seal(root)
        raise
    seal(root)
    return observation


def execute(worker, frames, root, *, max_new_tokens, request_timeout_s):
    records = [dict(input_index=i, recording=f['recording'], camera_id=f['camera_id'],
        source_identity=f['source_identity'], query=FINE_QUERY, target_key=FINE_LABEL,
        coarse_observation=None, box_observation=None, point_observation=None,
        coarse_status='NOT_ATTEMPTED', box_status='NOT_ATTEMPTED', point_status='NOT_ATTEMPTED')
        for i, f in enumerate(frames)]
    fatal = None
    for i, frame in enumerate(frames):
        record = records[i]
        frame_root = root/f'frame-{i:03d}'
        frame_root.mkdir(exist_ok=False)
        phase = 'coarse'
        try:
            coarse = call(worker, frame['view']['rgb'], root=frame_root/'coarse-box',
                request_id=f'{CONDITION}/{i}/coarse-BOX', source_identity=frame['source_identity'],
                mode='BOX', query=COARSE_QUERY, target_key=COARSE_LABEL,
                max_new_tokens=max_new_tokens, request_timeout_s=request_timeout_s)
            record['coarse_observation'] = coarse
            record['coarse_status'] = 'COMPLETE' if coarse['typed']['admitted'] else 'TYPED_REJECTED'
            if not coarse['typed']['admitted']:
                record['box_status'] = record['point_status'] = 'NOT_ATTEMPTED_COARSE_REJECTED'
            else:
                phase = 'crop_binding'
                crop, binding = make_model_crop(frame['view'], coarse)
                crop_path = frame_root/'model-crop.png'
                Image.fromarray(crop).save(crop_path)
                write(frame_root/'crop-binding.json', binding)
                record.update(crop_binding=binding, crop_png_uri=str(crop_path.resolve()), crop_png_sha256=file_hash(crop_path))
                # Each crop-local request is a separate chat, with no coarse answer or paired fine answer.
                for mode in ('BOX', 'POINT'):
                    phase = mode.lower()
                    observation = call(worker, crop, root=frame_root/f'fine-{phase}',
                        request_id=f'{CONDITION}/{i}/fine-{mode}', source_identity=frame['source_identity'],
                        mode=mode, query=FINE_QUERY, target_key=FINE_LABEL, crop_binding=binding,
                        max_new_tokens=max_new_tokens, request_timeout_s=request_timeout_s)
                    record[phase+'_observation'] = observation
                    record[phase+'_status'] = 'COMPLETE' if observation['typed']['admitted'] else 'TYPED_REJECTED'
        except Exception as exc:
            fatal = dict(input_index=i, phase=phase, error=repr(exc), hidden_retry=False,
                         failed_at_utc=datetime.now(timezone.utc).isoformat())
            record[phase+'_status'] = 'RUNTIME_FAILURE'
            write(frame_root/'runtime-failure.json', fatal)
        write(frame_root/'result.json', record)
        seal(frame_root)
        print(i, record['coarse_status'], record['box_status'], record['point_status'], flush=True)
        if fatal:
            break
    result = dict(condition=CONDITION, records=records, runtime_failure=fatal,
        max_requested_calls=3*len(frames),
        attempted_calls=sum(r[k+'_status'] in ('COMPLETE', 'TYPED_REJECTED', 'RUNTIME_FAILURE')
                            for r in records for k in ('coarse', 'box', 'point')),
        evaluation_labels_used=False, independent_heldout=False, perception_acceptance=False,
        for_execution=False, hidden_retry=False)
    write(root/'outputs.json', result)
    return result


def run(args):
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        require(args.max_new_tokens > 0 and args.request_timeout_s > 0, 'positive explicit budgets required')
        gpu = os.environ.get('CUDA_VISIBLE_DEVICES', '')
        require(args.device.startswith('cuda') and gpu.startswith('GPU-') and ',' not in gpu,
                'explicit single GPU UUID required')
        frames = input_frames(args.input_recording, args.camera)
        identity = checkpoint_identity(args.model)
        r = dict(condition=CONDITION, code=code_identity(), adapter_revision=ADAPTER_REVISION,
            model_identity=identity, versions=versions(), executable=sys.executable,
            gpu_uuid=gpu, device=args.device, seed=args.seed,
            inputs=[{k:v for k,v in f.items() if k!='view'} for f in frames],
            requests=dict(system=SYSTEM, templates=TEMPLATES, coarse_query=COARSE_QUERY,
                          coarse_label=COARSE_LABEL, fine_query=FINE_QUERY, fine_label=FINE_LABEL),
            crop_rule='sole same-frame typed model BOX; expand 15 percent each side; floor left/top, ceil right/bottom, clip original raster; no fallback',
            generation_call_overrides=dict(GREEDY_CALL_OVERRIDES), max_new_tokens=args.max_new_tokens,
            request_timeout_s=args.request_timeout_s,
            image_processor_override=dict(min_pixels=args.image_min_pixels, max_pixels=args.image_max_pixels),
            model_inputs=['full original RGB for coarse', 'model-derived original RGB crop for fine', 'fixed text'],
            model_depth_input=False, evaluation_labels_used=False, for_execution=False,
            independent_heldout=False, perception_acceptance=False,
            created_at_utc=datetime.now(timezone.utc).isoformat())
        r['registration_sha256'] = content_hash(r)
        write(root/'registration.json', r)
        worker = Qwen3VLGroundingWorker(args.model, device=args.device, seed=args.seed, model_identity=identity,
            image_min_pixels=args.image_min_pixels, image_max_pixels=args.image_max_pixels)
        write(root/'loaded-model.json', dict(model_identity=worker.model_identity,
            processor_identity=worker.processor_identity, environment_identity=worker.environment_identity,
            registration_sha256=file_hash(root/'registration.json'), pid=os.getpid()))
        result = execute(worker, frames, root, max_new_tokens=args.max_new_tokens,
                         request_timeout_s=args.request_timeout_s)
        failed = result['runtime_failure'] is not None
        write(root/'process.json', dict(pid=os.getpid(), elapsed_s=time.perf_counter()-started,
            exit_code=int(failed), hidden_retry=False, runtime_failure=result['runtime_failure']))
        seal(root)
        return int(failed)
    except Exception as exc:
        write(root/'process-failure.json', dict(error=repr(exc), pid=os.getpid(),
            elapsed_s=time.perf_counter()-started, hidden_retry=False))
        seal(root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--input-recording', '--recording', action='append', required=True)
    parser.add_argument('--camera', default='robot0_eye_in_hand')
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-new-tokens', type=int, default=256)
    parser.add_argument('--request-timeout-s', type=float, default=120.)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--image-min-pixels', type=int)
    parser.add_argument('--image-max-pixels', type=int)
    raise SystemExit(run(parser.parse_args()))


if __name__ == '__main__':
    main()
