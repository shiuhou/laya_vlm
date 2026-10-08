import hashlib
import json
import numpy as np

from embodied_runtime.adapters.qwen3vl_grounding import generation_audit, messages_for
from embodied_runtime.experiments.p1_qwen_coarse_to_fine_dev import execute, COARSE_LABEL, FINE_LABEL
from embodied_runtime.perception.grounding_observation import parse_qwen_grounding, validate_grounding_observation
from embodied_runtime.perception.surface_association import sensor_view_identity


def test_model_crop_pipeline_maps_once_and_abstention_has_no_fallback(tmp_path):
    views = [dict(rgb=np.zeros((20, 30, 3), np.uint8), depth_m=np.full((20, 30), .7),
        intrinsics_K=np.eye(3), T_base_camera=np.eye(4), frame_id=f'frame-{i}', frame_seq=i,
        camera_id='wrist', frame='robot_base', episode_id='e', calibration_version='s',
        capture_sim_time_s=float(i), capture_monotonic_ns=i+1) for i in range(2)]
    frames = [dict(recording=f'/recording-{i}', camera_id='wrist', view=v,
                   source_identity=sensor_view_identity(v)) for i, v in enumerate(views)]

    class Worker:
        model_identity = {'mock': 'model'}
        processor_identity = {'mock': 'processor'}
        environment_identity = {'mock': 'environment'}
        calls = []

        def infer(self, rgb, *, mode, query, target_key, max_new_tokens):
            self.calls.append((target_key, mode, rgb.shape))
            if len(self.calls) == 4:
                raw = '[]'
            else:
                value = [250, 250, 750, 750] if target_key == COARSE_LABEL else [0, 0, 1000, 1000] if mode == 'BOX' else [500, 500]
                raw = json.dumps([{'label': target_key, 'bbox_2d' if mode == 'BOX' else 'point_2d': value}])
            audit = generation_audit([5, 9], input_count=1, max_new_tokens=max_new_tokens,
                                     model_max_length=1024, eos_token_ids=[9])
            typed = parse_qwen_grounding(raw, rgb.shape[1], rgb.shape[0], mode=mode, audit=audit, expected_label=target_key)
            return dict(raw_output=raw, typed=typed, audit=audit, terminal_special_tokens=(),
                input_evidence=dict(rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(), query=query, input_token_ids=[1]), timing={})

    worker = Worker()
    result = execute(worker, frames, tmp_path, max_new_tokens=256, request_timeout_s=5)
    assert result['runtime_failure'] is None
    assert worker.calls == [(COARSE_LABEL, 'BOX', (20, 30, 3)), (FINE_LABEL, 'BOX', (14, 20, 3)),
                            (FINE_LABEL, 'POINT', (14, 20, 3)), (COARSE_LABEL, 'BOX', (20, 30, 3))]
    first, second = result['records']
    assert first['crop_binding']['crop_xyxy_px'] == [5, 3, 25, 17]
    point = validate_grounding_observation(first['point_observation'], view=views[0])
    box = validate_grounding_observation(first['box_observation'], view=views[0])
    assert point.point_xy_px == (15., 10.)
    assert box.ordered_boxes_xyxy_px == ((5., 3., 25., 17.),)
    assert second['box_status'] == second['point_status'] == 'NOT_ATTEMPTED_COARSE_REJECTED'
    assert result['attempted_calls'] == 4
    text = messages_for('BOX', 'cabinet query', COARSE_LABEL)[1]['content'][1]['text']
    assert '"tabletop_cabinet"' in text and 'cabinet query' in text
