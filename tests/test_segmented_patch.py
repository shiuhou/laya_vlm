import hashlib

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.perception.segmented_patch import estimate_segmented_patch
from embodied_runtime.perception.surface_association import sensor_view_identity


def fixture():
    h, w = 24, 32
    view = dict(rgb=np.zeros((h, w, 3), np.uint8), depth_m=np.full((h, w), .7),
                intrinsics_K=np.array([[240., 0, 15.5], [0, 240., 11.5], [0, 0, 1]]),
                T_base_camera=np.eye(4), frame_id="test/frame1", frame_seq=1,
                camera_id="test", frame="robot_base", episode_id="test",
                calibration_version="synthetic", capture_sim_time_s=0., capture_monotonic_ns=1)
    mask = np.zeros((h, w), bool)
    mask[4:8, 4:8] = True
    mask[20, 30] = True  # Native out-of-BOX pixel must remain in evidence.
    box = [0., 0., 24., 20.]
    source = sensor_view_identity(view)
    binding = dict(source_identity=source, sensor_view_sha256=content_hash(source),
                   query="synthetic target", box_index=0, box_xyxy=box,
                   box_response_sha256="0"*64, mask_index=2,
                   raw_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
                   mask_artifact_uri="fixture/mask.npy", mask_artifact_sha256="1"*64,
                   coordinate_convention="top-left-origin-pixel-xyxy",
                   mask_input_channels=["rgb"], evaluation_labels_used=False,
                   provenance="learned estimate")
    return view, box, mask, binding


def test_native_mask_keeps_original_roi_denominator_and_does_not_mutate_inputs():
    view, box, mask, binding = fixture()
    original_depth, original_mask = view["depth_m"].copy(), mask.copy()
    result = estimate_segmented_patch(view, box, mask, mask_binding=binding,
                                     config=GeometryConfig(), track_id="test", feature_id="mask2",
                                     measurement_contract="original-box-depth/1")
    assert result["patch"]["reason_codes"] == ["INSUFFICIENT_VALID_DEPTH"]
    assert result["patch"]["metrics"]["roi_pixel_count"] == 480
    assert result["patch"]["metrics"]["valid_depth_count"] == 16
    assert result["patch"]["metrics"]["depth_valid_ratio"] == 16/480
    assert result["mask_pixels_outside_original_roi"] == 1
    assert result["native_mask_pixel_count"] == 17
    assert result["mask_binding"]["mask_index"] == 2
    assert result["semantic_identity"] == "UNKNOWN" and result["for_execution"] is False
    assert result["calibrated_confidence"] is None
    np.testing.assert_array_equal(view["depth_m"], original_depth)
    np.testing.assert_array_equal(mask, original_mask)


def test_native_mask_availability_passes_while_absolute_roi_support_still_rejects():
    view, box, mask, binding = fixture()
    result = estimate_segmented_patch(view, box, mask, mask_binding=binding,
        config=GeometryConfig(), track_id="test", feature_id="mask2")
    metrics = result["patch"]["metrics"]
    assert metrics["mask_pixel_count"] == metrics["valid_depth_inside_mask"] == 17
    assert metrics["depth_availability"] == metrics["depth_valid_ratio"] == 1.0
    assert metrics["mask_original_box_coverage"] == 16/480
    assert metrics["mask_pixels_outside_original_roi"] == 1
    assert metrics["valid_depth_count"] == 16
    assert result["patch"]["reason_codes"] == ["INSUFFICIENT_CONNECTED_SUPPORT"]
    assert result["semantic_identity"] == "UNKNOWN" and result["for_execution"] is False


@pytest.mark.parametrize("empty", [False, True])
def test_missing_mask_depth_and_empty_mask_remain_unknown(empty):
    view, box, mask, binding = fixture()
    if empty:
        mask[:] = False
    else:
        view["depth_m"][4:7, 4:8] = np.nan
    binding["raw_mask_sha256"] = hashlib.sha256(mask.tobytes()).hexdigest()
    binding["source_identity"] = sensor_view_identity(view)
    binding["sensor_view_sha256"] = content_hash(binding["source_identity"])
    result = estimate_segmented_patch(view, box, mask, mask_binding=binding,
        config=GeometryConfig(), track_id="test", feature_id="mask2")
    assert result["patch"]["geometry_status"] == "UNKNOWN"
    metrics = result["patch"]["metrics"]
    assert metrics["depth_availability"] == (None if empty else 5/17)
    assert result["patch"]["reason_codes"] == ["EMPTY_DEPTH_AVAILABILITY_MASK" if empty else "INSUFFICIENT_VALID_DEPTH"]


@pytest.mark.parametrize("mutation", ["depth", "rgb", "frame", "camera", "calibration", "box", "mask", "shape", "labels"])
def test_mask_binding_rejects_wrong_source_or_information_boundary(mutation):
    view, box, mask, binding = fixture()
    if mutation == "depth":
        view["depth_m"][0, 0] = .8
    elif mutation == "rgb":
        view["rgb"][0, 0, 0] = 1
    elif mutation == "frame":
        view["frame_id"] = "other/frame"
    elif mutation == "camera":
        view["camera_id"] = "other-camera"
    elif mutation == "calibration":
        view["calibration_version"] = "other-calibration"
    elif mutation == "box":
        box = [0., 0., 20., 20.]
    elif mutation == "mask":
        mask[0, 0] = True
    elif mutation == "shape":
        mask = mask[:, :-1]
    else:
        binding["evaluation_labels_used"] = True
    with pytest.raises(ProtocolError):
        estimate_segmented_patch(view, box, mask, mask_binding=binding,
                                 config=GeometryConfig(), track_id="test", feature_id="mask2")
