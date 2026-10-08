"""Bounded Qwen3-VL RGB-only development localization, without robot control.

Each recording contributes its first requested-camera exposure. This runner has
no annotation argument and never invokes SAM, geometry, a planner or controller.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from ..adapters.qwen3vl_grounding import (
    ADAPTER_REVISION, GREEDY_CALL_OVERRIDES, QUERY, SYSTEM, TEMPLATES, Qwen3VLGroundingWorker, checkpoint_identity,
)
from ..contracts import content_hash, require
from ..perception.grounding_observation import build_grounding_observation
from ..perception.recording import replay_frames
from ..perception.surface_association import sensor_view_identity
from .p1_segmentation_probe import seal, write
from .records import code_identity, file_hash, versions


def input_frames(recordings, camera):
    """Validate recordings end-to-end, select first camera exposure, never a scored frame."""
    rows = []
    for recording in recordings:
        root = Path(recording).resolve()
        selected = None
        for _, views in replay_frames(root):
            for view in views:
                if selected is None and view['camera_id'] == camera:
                    selected = view
        require(selected is not None, "requested camera not recorded")
        rows.append(dict(recording=str(root), camera_id=camera, view=selected,
            source_identity=sensor_view_identity(selected),
            metadata_sha256={name:file_hash(root/name) for name in
                             ('recording.json', 'frames.jsonl', 'source-identities.jsonl')}))
    identities = [content_hash(x['source_identity']) for x in rows]
    require(len(set(identities)) == len(identities), "duplicate requested source frames")
    return rows


@contextmanager
def deadline(seconds):
    """Bound a request on POSIX; external process limits still bound blocked kernels."""
    def expired(signum, frame):
        raise TimeoutError(f"localizer request exceeded {seconds}s; no retry")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def execute_requests(worker, frames, root, *, max_new_tokens, request_timeout_s):
    """Independent fixed BOX/POINT slots; typed refusal does not suppress its pair."""
    root = Path(root)
    records = [dict(input_index=i, recording=row['recording'], camera_id=row['camera_id'],
        source_identity=row['source_identity'], box_observation=None, point_observation=None,
        box_status='NOT_ATTEMPTED', point_status='NOT_ATTEMPTED') for i, row in enumerate(frames)]
    fatal = None
    for i, frame in enumerate(frames):
        for mode in ('BOX', 'POINT'):
            record = records[i]
            receipt_dir = root/f'input-{i:03d}-{mode.lower()}'
            receipt_dir.mkdir(exist_ok=False)
            request_id = f'qwen-dev/{i}/{mode}'
            write(receipt_dir/'request.json', dict(request_id=request_id, mode=mode,
                source_identity=frame['source_identity'], query=QUERY,
                max_new_tokens=max_new_tokens, request_timeout_s=request_timeout_s,
                started_at_utc=datetime.now(timezone.utc).isoformat(), hidden_retry=False))
            try:
                with deadline(request_timeout_s):
                    reply = worker.infer(frame['view']['rgb'], mode=mode, query=QUERY,
                                         max_new_tokens=max_new_tokens)
                raw_path = receipt_dir/'raw-output.txt'
                raw_path.write_text(reply['raw_output'], encoding='utf-8')
                observation = build_grounding_observation(reply['typed'], request_id=request_id,
                    source_identity=frame['source_identity'], query=QUERY, target_key='drawer_front_pushable',
                    frontend_id='Qwen3-VL-4B-Instruct-2D', model_identity=worker.model_identity,
                    processor_identity=worker.processor_identity, environment_identity=worker.environment_identity,
                    audit=reply['audit'], input_evidence=reply['input_evidence'],
                    terminal_special_tokens=reply['terminal_special_tokens'], timing=reply['timing'],
                    raw_output_ref=str(raw_path.resolve()))
                write(receipt_dir/'receipt.json', dict(reply, typed=reply['typed'].evidence()))
                write(receipt_dir/'observation.json', observation)
                record[mode.lower()+'_observation'] = observation
                record[mode.lower()+'_receipt_uri'] = str((receipt_dir/'receipt.json').resolve())
                record[mode.lower()+'_status'] = 'COMPLETE' if reply['typed'].admitted else 'TYPED_REJECTED'
            except Exception as exc:
                fatal = dict(input_index=i, mode=mode, error=repr(exc), hidden_retry=False,
                             stopped_at_utc=datetime.now(timezone.utc).isoformat())
                record[mode.lower()+'_status'] = 'RUNTIME_FAILURE'
                write(receipt_dir/'failure.json', fatal)
            seal(receipt_dir)
            write(root/f'frame-{i:03d}-{mode.lower()}-progress.json', record)
            print(i, mode, record[mode.lower()+'_status'], flush=True)
            if fatal:
                break
        if fatal:
            break
    result = dict(records=records, runtime_failure=fatal, requested_frames=len(frames),
        requested_calls=len(frames)*2, attempted_calls=sum(x[m+'_status']!='NOT_ATTEMPTED' for x in records for m in ('box','point')),
        hidden_retry=False, evaluation_labels_used=False, independent_heldout=False,
        for_execution=False, perception_acceptance=False)
    write(root/'outputs.json', result)
    return result


def run(args):
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        require(args.request_timeout_s > 0 and args.max_new_tokens > 0, "positive development budgets required")
        frames = input_frames(args.input_recording, args.camera)
        require(args.device.startswith('cuda'), "this pinned development condition requires CUDA BF16 SDPA")
        gpu = os.environ.get('CUDA_VISIBLE_DEVICES', '')
        require(gpu.startswith('GPU-') and ',' not in gpu, "single GPU UUID allocation required")
        identity = checkpoint_identity(args.model)
        registration = dict(condition='p1-qwen-localizer-development/1', adapter_revision=ADAPTER_REVISION,
            code=code_identity(), model_identity=identity, camera_id=args.camera,
            inputs=[{k:v for k,v in row.items() if k!='view'} for row in frames],
            prompts=dict(system=SYSTEM, templates=TEMPLATES, query=QUERY),
            generation=dict(max_new_tokens=args.max_new_tokens, do_sample=False, num_beams=1, use_cache=True,
                temperature=None, top_p=None, top_k=None, seed=args.seed),
            generation_call_overrides=dict(GREEDY_CALL_OVERRIDES),
            image_processor_override=dict(min_pixels=args.image_min_pixels, max_pixels=args.image_max_pixels),
            request_timeout_s=args.request_timeout_s, device=args.device, gpu_uuid=gpu,
            executable=sys.executable, versions=versions(),
            source_selection='first requested-camera exposure per recording, complete recording verified',
            model_inputs=['full original RGB', 'fixed system message', 'fixed target request'],
            independent_requests=True, zero_retries=True, evaluation_labels_used=False,
            independent_heldout=False, perception_acceptance=False, for_execution=False,
            created_at_utc=datetime.now(timezone.utc).isoformat())
        registration['registration_sha256'] = content_hash(registration)
        write(root/'registration.json', registration)
        gpu_receipt = subprocess.run(['nvidia-smi', '--query-gpu=uuid,name,memory.used,utilization.gpu',
            '--format=csv,noheader'], capture_output=True, text=True, check=False)
        write(root/'gpu-before-load.json', dict(returncode=gpu_receipt.returncode,
              stdout=gpu_receipt.stdout, stderr=gpu_receipt.stderr, selected_uuid=gpu))
        worker = Qwen3VLGroundingWorker(args.model, device=args.device, seed=args.seed, model_identity=identity,
            image_min_pixels=args.image_min_pixels, image_max_pixels=args.image_max_pixels)
        write(root/'loaded-model.json', dict(model_identity=worker.model_identity,
            processor_identity=worker.processor_identity, environment_identity=worker.environment_identity,
            registration_sha256=file_hash(root/'registration.json'), pid=os.getpid()))
        result = execute_requests(worker, frames, root, max_new_tokens=args.max_new_tokens,
                                  request_timeout_s=args.request_timeout_s)
        write(root/'process.json', dict(pid=os.getpid(), elapsed_s=time.perf_counter()-started,
            runtime_failure=result['runtime_failure'], hidden_retry=False, exit_code=1 if result['runtime_failure'] else 0))
        seal(root)
        return 1 if result['runtime_failure'] else 0
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
