"""Explicit offline SAM2 video single-mask development condition.

Each eligible original native support has its own memory state. RGB is read
losslessly from recordings; source timestamps and terminal losses are retained.
This module does not evaluate depth geometry or produce executable actions.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

from ..contracts import content_hash, require
from ..perception.recording import replay_frames
from ..perception.rgbd_geometry import _roi
from ..perception.surface_association import sensor_view_identity
from .p1_automatic_patch_tracking import verified_geometry
from .p1_localizer_surface_dev import ASSETS
from .p1_segmentation_probe import CHECKPOINT_SHA, CONFIG_SHA, read, write, seal
from .records import code_identity, file_hash, versions

CONDITION = 'sam2-video-singlemask/1'
VIDEO_OVERRIDES = ['++model.multimask_output_for_tracking=false']
GAP_S = .3


def video_builder_options():
    return dict(apply_postprocessing=False, vos_optimized=False,
                hydra_overrides_extra=list(VIDEO_OVERRIDES))


def checked_rgb(view, identity):
    require(sensor_view_identity(view) == identity, 'recorded sensor identity changed', 'SOURCE_MISMATCH')
    rgb = view['rgb']
    require(rgb.dtype == np.uint8 and rgb.shape == tuple(identity['rgb_shape']), 'lossless RGB shape/dtype changed')
    require(hashlib.sha256(rgb.tobytes()).hexdigest() == identity['rgb_sha256'], 'RGB bytes changed', 'SOURCE_MISMATCH')
    return rgb


class RecordedRGBFrames:
    """Lazy official image normalization with original RGB, without JPEG encoding."""
    def __init__(self, rows, image_size):
        self.rows, self.image_size = rows, image_size

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        import torch
        row = self.rows[index]
        rgb = checked_rgb(row['view'], row['source_identity'])
        resized = np.array(Image.fromarray(rgb).resize((self.image_size, self.image_size), Image.Resampling.BICUBIC))
        # Match the official JPEG-loader tensor path after decoding: numpy
        # float64 /255 then assignment into float32, followed by normalization.
        tensor = torch.from_numpy(resized/255.).permute(2, 0, 1).float()
        tensor -= torch.tensor((.485, .456, .406), dtype=torch.float32)[:, None, None]
        tensor /= torch.tensor((.229, .224, .225), dtype=torch.float32)[:, None, None]
        return tensor


@contextmanager
def lossless_loader(rows):
    """Scoped input-loader seam; restores pinned module immediately after init."""
    import sam2.sam2_video_predictor as module
    original = module.load_video_frames
    token = 'verified-recorded-rgb://lossless'

    def load(*, video_path, image_size, offload_video_to_cpu, **kwargs):
        require(video_path == token and offload_video_to_cpu, 'unexpected video loader request')
        h, w, _ = rows[0]['source_identity']['rgb_shape']
        require(all(r['source_identity']['rgb_shape'] == [h, w, 3] for r in rows), 'video dimensions changed')
        return RecordedRGBFrames(rows, image_size), h, w

    module.load_video_frames = load
    try:
        yield token
    finally:
        module.load_video_frames = original


def source_sequence(recording, records):
    bundles = list(replay_frames(recording))
    require(bool(bundles), 'recording empty')
    matched = [v for v in bundles[0][1] if any(r['source_identity'] == sensor_view_identity(v) for r in records)]
    require(len(matched) == 1, 'one exact first-frame grounded camera required', 'SOURCE_MISMATCH')
    camera = matched[0]['camera_id']
    rows = []
    for _, views in bundles:
        selected = [v for v in views if v['camera_id'] == camera]
        require(len(selected) == 1, 'recorded camera missing or duplicated')
        view = dict(selected[0], frame_id=selected[0]['canonical_frame_id'])
        rows.append(dict(view=view, source_identity=sensor_view_identity(view)))
    return rows


def seeds(records, first, output):
    decisions, admitted = [], []
    for record in records:
        if record['source_identity'] != first['source_identity']:
            continue
        if record['status'] != 'COMPLETE':
            decisions.append(dict(input_index=record['input_index'], box_index=record['box_index'],
                native_mask_ordinal=None, admitted=False, reason=record.get('failure_stage')))
            continue
        require(file_hash(record['artifact_uri']) == record['artifact_sha256'], 'native masks changed')
        with np.load(record['artifact_uri'], allow_pickle=False) as data:
            for result, native in zip(record['native_results'], data['masks']):
                ordinal = result['ordinal']
                require(hashlib.sha256(native.tobytes()).hexdigest() == record['raw_mask_sha256'][ordinal], 'native bytes changed')
                patch = result['estimate']['patch']
                row = dict(input_index=record['input_index'], box_index=record['box_index'], native_mask_ordinal=ordinal,
                    original_mask_artifact_uri=record['artifact_uri'], original_mask_artifact_sha256=record['artifact_sha256'],
                    original_native_mask_sha256=record['raw_mask_sha256'][ordinal],
                    initial_geometry_status=patch['geometry_status'], initial_candidate_count=len(patch['candidates']),
                    mask_point_admission=result['mask_point_admission'], admitted=False, reason=None)
                if not result['mask_point_admission']['admitted']:
                    row['reason'] = 'POINT_MASK_CONTRADICTION'
                elif patch['geometry_status'] != 'VALID' or not patch['candidates']:
                    row['reason'] = 'NO_INITIAL_GEOMETRY_CANDIDATE'
                else:
                    x0, y0, x1, y1 = _roi(record['box_xyxy'], native.shape[1], native.shape[0])
                    support = np.zeros_like(native)
                    support[y0:y1, x0:x1] = native[y0:y1, x0:x1]
                    require(support.any(), 'geometry-admitted seed support empty')
                    key = f"box-{record['box_index']}-native-{ordinal}"
                    path = output/(key+'.npy')
                    np.save(path, support, allow_pickle=False)
                    row.update(admitted=True, hypothesis_id=key, seed_mask_uri=str(path.resolve()),
                        seed_mask_artifact_sha256=file_hash(path), seed_mask_sha256=hashlib.sha256(support.tobytes()).hexdigest(),
                        seed_support_domain='native_intersection_original_geometry_BOX',
                        original_box_xyxy=record['box_xyxy'], seed_support_pixels=int(support.sum()))
                    admitted.append(dict(row, mask=support))
                decisions.append(row)
    return decisions, admitted


def temporal_reason(current, previous):
    if previous is None:
        return None
    for key in ('camera_id', 'calibration_version', 'episode_id', 'rgb_shape', 'depth_shape', 'intrinsics_K', 'coordinate_frame'):
        if current[key] != previous[key]:
            return 'SOURCE_DISCONTINUITY'
    sim_gap = current['capture_sim_time_s']-previous['capture_sim_time_s']
    wall_gap = (current['capture_monotonic_ns']-previous['capture_monotonic_ns'])/1e9
    if current['frame_id'] == previous['frame_id'] or current['frame_seq'] <= previous['frame_seq'] or min(sim_gap, wall_gap) < 0:
        return 'CAPTURE_CLOCK_REGRESSION'
    return 'FRAME_GAP_EXCEEDS_300MS' if max(sim_gap, wall_gap) > GAP_S else None


def track(model, sequence, hypotheses, out):
    import torch
    rows = []
    for hypothesis in hypotheses:
        key = hypothesis['hypothesis_id']
        directory = out/key
        directory.mkdir()
        torch.cuda.synchronize()
        initialization_start = time.perf_counter()
        with lossless_loader(sequence) as token:
            state = model.init_state(token, offload_video_to_cpu=True, offload_state_to_cpu=False, async_loading_frames=False)
        model.add_new_mask(state, frame_idx=0, obj_id=1, mask=hypothesis['mask'])
        torch.cuda.synchronize()
        write(directory/'initialization.json', dict(initialization_s=time.perf_counter()-initialization_start,
            seed_mask_sha256=hypothesis['seed_mask_sha256'], seed_source_identity=sequence[0]['source_identity']))
        generator = model.propagate_in_video(state, start_frame_idx=0, max_frame_num_to_track=len(sequence)-1, reverse=False)
        terminal, previous = None, None
        for i, source in enumerate(sequence):
            identity = source['source_identity']
            h, w, _ = identity['rgb_shape']
            reason = terminal or temporal_reason(identity, previous)
            row = dict(hypothesis_id=key, source_identity=identity, frame_index=i,
                seed_source_identity_sha256=content_hash(sequence[0]['source_identity']),
                tracker_condition=CONDITION, native_mask_ordinal=hypothesis['native_mask_ordinal'],
                box_index=hypothesis['box_index'], lineage_id=key, generation=1, parent_source_identity=previous,
                status='LOST' if reason else 'TRACKED', reason_codes=[reason] if reason else [],
                mask_sha256=None, current_domain_xyxy_px=[0, 0, w, h], domain_kind='full-frame-masked-depth/1',
                model_input_rgb_sha256=identity['rgb_sha256'], model_evaluation='NOT_EVALUATED',
                evaluation_labels_used=False, oracle_inputs=False, for_execution=False,
                object_score_logits=None, calibrated_confidence=None, automatic_reseed=False)
            if reason is None:
                checked_rgb(source['view'], identity)
                torch.cuda.synchronize()
                started = time.perf_counter()
                index, obj_ids, logits = next(generator)
                torch.cuda.synchronize()
                inference_s = time.perf_counter()-started
                require(index == i and obj_ids == [1], 'video output source order differs')
                storage = 'cond_frame_outputs' if i == 0 else 'non_cond_frame_outputs'
                native = state['output_dict_per_obj'][0][storage][i]
                score = native['object_score_logits'].detach().cpu().float().numpy()
                full = logits.detach().cpu().float().numpy()
                low = native['pred_masks'].detach().cpu().float().numpy()
                require(full.shape == (1, 1, h, w), 'video mask shape differs')
                mask = full[0, 0] > 0
                path = directory/f'frame-{i:04d}.npz'
                np.savez_compressed(path, mask=mask, logits=full, lowres_logits=low, object_score_logits=score)
                finite = np.isfinite(full).all() and np.isfinite(low).all() and np.isfinite(score).all()
                reason = ('NONFINITE_VIDEO_OUTPUT' if not finite else 'OBJECT_NOT_OBSERVED' if np.any(score <= 0)
                          else 'EMPTY_TRACKED_MASK' if not mask.any() else None)
                ys, xs = np.where(mask)
                row.update(model_evaluation='EVALUATED', tracker_s=time.perf_counter()-started, inference_s=inference_s,
                    status='LOST' if reason else 'TRACKED', reason_codes=[reason] if reason else [],
                    artifact_uri=str(path.resolve()), artifact_sha256=file_hash(path),
                    mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(), mask_pixels=int(mask.sum()),
                    current_mask_bbox_diagnostic=[int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1] if mask.any() else None,
                    object_score_logits=np.where(np.isfinite(score), score, None).tolist(), object_score_provenance='seed-mask-presence-derived' if i == 0 else 'learned uncalibrated occlusion score',
                    original_logits_dtype=str(logits.dtype), seed_event=i == 0)
            if reason is not None:
                terminal = reason
            write(directory/f'frame-{i:04d}.json', row)
            rows.append(row)
            previous = identity
            print(key, i, row['status'], row['reason_codes'], flush=True)
        generator.close()
        del state
        seal(directory)
    return rows


def run(geometry, recording, output):
    import torch
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    try:
        records = verified_geometry(geometry)
        sequence = source_sequence(recording, records)
        seed_dir = out/'seeds'
        seed_dir.mkdir()
        decisions, hypotheses = seeds(records, sequence[0], seed_dir)
        write(seed_dir/'decisions.json', decisions)
        seal(seed_dir)
        pinned = read(ASSETS)
        assets = pinned['environment_receipt']
        require(Path(sys.executable).absolute() == Path(assets['python_executable']).absolute(), 'use frozen SAM environment')
        require(torch.__version__ == '2.5.1+cu121' and os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8', 'locked SAM environment required')
        for name, digest in pinned['source_files_sha256'].items():
            if Path(name).resolve().is_relative_to(Path(assets['sam_source']).resolve()):
                require(file_hash(name) == digest, 'pinned SAM source changed')
        require(file_hash(assets['checkpoint_path']) == CHECKPOINT_SHA and
                file_hash(Path(assets['sam_source'])/'sam2/configs/sam2.1/sam2.1_hiera_t.yaml') == CONFIG_SHA,
                'SAM checkpoint/config changed')
        import sam2
        from sam2.build_sam import build_sam2_video_predictor
        from .p1_semantic_grounding import _explicit_gpu_mask, _cuda_allocation
        from .sam2_deterministic_grid import install_and_verify
        require(Path(sam2.__file__).resolve().is_relative_to(Path(assets['sam_source']).resolve()), 'SAM import changed')
        write(out/'condition.json', dict(condition=CONDITION, code=code_identity(), versions=versions(),
            argv=sys.argv, executable=sys.executable, pid=os.getpid(),
            geometry=str(Path(geometry).resolve()), geometry_seal_sha256=file_hash(Path(geometry)/'sealed.json'),
            recording=str(Path(recording).resolve()), recording_frames_sha256=file_hash(Path(recording)/'frames.jsonl'),
            source_identities=[r['source_identity'] for r in sequence], assets=assets,
            builder_options=video_builder_options(), allocation=_cuda_allocation(torch, _explicit_gpu_mask()),
            dtype='float32', memory_feature_storage='native video code casts memory features to bfloat16',
            strict_deterministic_algorithms=True, autocast=False, threshold=0., max_gap_s=GAP_S,
            original_static_SAM_condition_unchanged=True, video_decoder_condition_distinct=True,
            hypotheses=len(hypotheses), no_native_winner=True, no_automatic_reseed=True,
            image_loader='lossless original RGB -> PIL BICUBIC square1024 -> float32 normalize official mean/std',
            video_input_encoding='none; original uint8 RGB bytes verified before processing',
            offload_video_to_cpu=True, offload_state_to_cpu=False, online_freshness_evaluated=False,
            geometry_evaluation='SEPARATE_STAGE_NOT_RUN', evaluation_labels_used=False, oracle_inputs=False, for_execution=False))
        torch.manual_seed(1)
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        rows = []
        if hypotheses:
            model = build_sam2_video_predictor(assets['sam_config'], assets['checkpoint_path'], device='cuda:0', **video_builder_options())
            require(model.multimask_output_for_tracking is False and model.fill_hole_area == 0
                    and model.non_overlap_masks is False and model.sam_mask_decoder.dynamic_multimask_via_stability is False,
                    'implicit video postprocessing or mask winner enabled')
            write(out/'grid-receipt.json', install_and_verify(model))
            rows = track(model, sequence, hypotheses, out)
        write(out/'outputs.json', dict(records=rows, seed_decisions=decisions, frames=len(sequence),
            hypotheses=len(hypotheses), runtime_failure=None, evaluation_labels_used=False, for_execution=False,
            geometry_evaluated=False, continuous_end_to_end_hz_measured=False))
        seal(out)
    except Exception as exc:
        write(out/'runtime-failure.json', dict(error=repr(exc), hidden_retry=False))
        seal(out)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry', required=True)
    p.add_argument('--recording', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    run(a.geometry, a.recording, a.output)


if __name__ == '__main__':
    main()
