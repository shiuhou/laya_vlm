"""One-command offline Qwen -> SAM -> frozen geometry development pipeline.

Uses existing isolated workers without changing their algorithms. Optional
tracking replays the same recordings; this is not online control or P1 acceptance.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import time

from ..contracts import require
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import code_identity, file_hash

REPO = Path(__file__).resolve().parents[2]
MODEL = '/home/junhongli/models/huggingface/Qwen3-VL-4B-Instruct-modelscope-302de2ef'


@dataclass(frozen=True)
class Stage:
    name: str
    command: list[str]
    output: str
    dependencies: tuple[str, ...]


def build_stages(args):
    """Only compose existing CLIs; keep interpreter symlinks un-resolved."""
    root = Path(args.output).absolute()
    qwen = str(Path(args.qwen_python).absolute())
    sam = str(Path(args.sam_python).absolute())
    geometry = str(Path(args.geometry_python).absolute())
    recordings = [str(Path(p).resolve()) for p in args.recording]
    grounding, masks, patches = (str(root/name) for name in ('grounding', 'masks', 'geometry'))
    command = [qwen, '-m', 'embodied_runtime.experiments.p1_qwen_coarse_to_fine_dev',
        '--model', str(Path(args.model).resolve()), '--device', 'cuda:0', '--camera', args.camera,
        '--output', grounding, '--max-new-tokens', str(args.max_new_tokens),
        '--request-timeout-s', str(args.request_timeout_s), '--seed', str(args.seed)]
    for recording in recordings:
        command.extend(['--recording', recording])
    if args.image_min_pixels is not None:
        command.extend(['--image-min-pixels', str(args.image_min_pixels)])
    if args.image_max_pixels is not None:
        command.extend(['--image-max-pixels', str(args.image_max_pixels)])
    stages = [Stage('grounding', command, grounding, ()),
        Stage('masks', [sam, '-m', 'embodied_runtime.experiments.p1_localizer_surface_dev',
            'masks', '--input', grounding, '--output', masks], masks, ('grounding',)),
        Stage('geometry', [geometry, '-m', 'embodied_runtime.experiments.p1_localizer_surface_dev',
            'geometry', '--input', masks, '--output', patches], patches, ('masks',))]
    if args.track:
        for i, recording in enumerate(recordings):
            output = str(root/f'tracking-{i:03d}')
            module = ('embodied_runtime.experiments.p1_automatic_patch_tracking' if args.tracking_method == 'template'
                      else 'embodied_runtime.experiments.p1_flow_mask_tracking_dev')
            command = [geometry, '-m', module, '--geometry', patches, '--recording', recording, '--output', output]
            if args.tracking_method == 'template':
                command.extend(['--seed-method', args.seed_method])
            stages.append(Stage(f'tracking-{i:03d}', command, output, ('geometry',)))
    return stages


def execute_stages(stages, *, output, environment, timeout_s, runner=subprocess.run):
    """Persist failed stages and stop; never retry, resume or replace artifacts."""
    output = Path(output)
    statuses = [dict(name=s.name, command=s.command, output=s.output, dependencies=list(s.dependencies),
                     status='NOT_ATTEMPTED') for s in stages]
    for stage, status in zip(stages, statuses):
        log = output/f'{stage.name}.log'
        started = time.perf_counter()
        status.update(started_at_utc=datetime.now(timezone.utc).isoformat(), log_uri=str(log.resolve()))
        try:
            require(not Path(stage.output).exists(), 'stage output already exists; no retry or overwrite')
            with log.open('x') as stream:
                result = runner(stage.command, cwd=str(REPO), env=environment, stdout=stream,
                    stderr=subprocess.STDOUT, timeout=timeout_s, check=False)
            status['exit_code'] = result.returncode
            require(result.returncode == 0, f'{stage.name} process failed; downstream blocked')
            verify_seal(stage.output)
            aggregate = Path(stage.output)/'outputs.json'
            if aggregate.is_file():
                require(not read(aggregate).get('runtime_failure'), 'upstream reported runtime failure')
            require(not any((Path(stage.output)/name).is_file() for name in
                ('failure.json', 'process-failure.json', 'runtime-failure.json')), 'stage failure receipt present')
            status.update(status='COMPLETE', output_seal_sha256=file_hash(Path(stage.output)/'sealed.json'))
        except subprocess.TimeoutExpired as exc:
            status.update(status='FAILED', failure='PROCESS_TIMEOUT', error=str(exc), hidden_retry=False)
        except Exception as exc:
            status.update(status='FAILED', failure='STAGE_FAILURE', error=repr(exc), hidden_retry=False)
        status.update(elapsed_s=time.perf_counter()-started, finished_at_utc=datetime.now(timezone.utc).isoformat())
        if log.exists():
            status['log_sha256'] = file_hash(log)
        write(output/f'{stage.name}-process.json', status)
        print(stage.name, status['status'], flush=True)
        if status['status'] != 'COMPLETE':
            break
    return dict(stages=statuses, completed=all(x['status']=='COMPLETE' for x in statuses),
        first_failure=next((x['name'] for x in statuses if x['status']=='FAILED'), None),
        retries=0, evaluation_labels_used=False, robot_commands=0, for_execution=False,
        independent_heldout=False, perception_acceptance=False, p1_pass_claimed=False,
        continuous_end_to_end_hz_measured=False)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recording', action='append', required=True, help='Original recorded sensor sequence; repeat for multiple sources')
    p.add_argument('--camera', default='frontview', help='Exact recorded camera, no fallback (default: frontview)')
    p.add_argument('--gpu-uuid', required=True, help='Single physical GPU UUID for sequential Qwen and SAM processes')
    p.add_argument('--output', required=True, help='New exclusive evidence directory')
    p.add_argument('--model', default=MODEL)
    p.add_argument('--qwen-python', default=str(REPO/'.venv-p1-qwen3vl/bin/python'))
    p.add_argument('--sam-python', default=str(REPO/'.venv-p1-sam2/bin/python'))
    p.add_argument('--geometry-python', default=str(REPO/'.venv-p1/bin/python'))
    p.add_argument('--image-min-pixels', type=int, default=1572864)
    p.add_argument('--image-max-pixels', type=int, default=1572864)
    p.add_argument('--max-new-tokens', type=int, default=256)
    p.add_argument('--request-timeout-s', type=float, default=120.)
    p.add_argument('--stage-timeout-s', type=float, default=3600.)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--track', action='store_true', help='Replay existing tracker on each same source recording; no new capture/reseed')
    p.add_argument('--tracking-method', choices=['template', 'sparse-flow'], default='template',
                   help='Optional offline tracking worker; historical template tracker remains default')
    p.add_argument('--seed-method', choices=['mask-rectangle', 'depth-supported-rectangle'], default='mask-rectangle',
                   help='Optional tracker seed adapter; historical mask-rectangle remains default')
    p.add_argument('--dry-run', action='store_true', help='Print commands/environment only; no files or workers started')
    return p


def main():
    args = parser().parse_args()
    require(args.gpu_uuid.startswith('GPU-') and ',' not in args.gpu_uuid, 'single GPU UUID required')
    require(args.stage_timeout_s > 0 and args.request_timeout_s > 0 and args.max_new_tokens > 0, 'positive budgets required')
    require(args.image_min_pixels > 0 and args.image_max_pixels >= args.image_min_pixels, 'valid image area bounds required')
    stages = build_stages(args)
    overrides = dict(CUDA_VISIBLE_DEVICES=args.gpu_uuid, CUBLAS_WORKSPACE_CONFIG=':4096:8',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    if args.dry_run:
        import json
        print(json.dumps(dict(stages=[asdict(s) for s in stages], environment=overrides), indent=2))
        return
    for executable in (args.qwen_python, args.sam_python, args.geometry_python):
        require(Path(executable).is_file(), 'worker interpreter not found: '+executable)
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    write(root/'pipeline.json', dict(condition='p1-offline-perception-orchestration/1', code=code_identity(),
        configuration=vars(args), stages=[asdict(s) for s in stages], environment=overrides,
        created_at_utc=datetime.now(timezone.utc).isoformat(), evaluation_labels_used=False,
        for_execution=False, p1_pass_claimed=False, automatic_retry=False))
    result = execute_stages(stages, output=root, environment=dict(os.environ, **overrides), timeout_s=args.stage_timeout_s)
    write(root/'result.json', result)
    seal(root)
    raise SystemExit(0 if result['completed'] else 1)


if __name__ == '__main__':
    main()
