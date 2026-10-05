import importlib
import json
import subprocess
import sys

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.visualization import (
    INVALID_DEPTH_COLOR, UNKNOWN_COLOR, build_patch_diagnostics,
    project_candidate_dots, write_patch_diagnostics,
)


def fixture():
    rgb = np.full((20, 32, 3), 100, dtype=np.uint8)
    depth = np.full((20, 32), .8, dtype=np.float32)
    k = np.array([[40., 0, 16], [0, 50., 10], [0, 0, 1]])
    transform = np.eye(4)
    transform[:3, 3] = [1, 2, 3]
    patch = dict(source_frame_id="frame:3", calibration_version="camera-v1",
                 geometry_status="VALID", reason_codes=[], centroid_base_m=[1, 2, 3.8],
                 normal_base=[0, 0, -1], source_roi_xyxy=[2, 2, 30, 18],
                 candidates=[dict(point_id="a", position_base_m=[1, 2, 3.8],
                                  usable_status="UNKNOWN", geometry_valid=True),
                             dict(point_id="b", position_base_m=[1.04, 2, 3.8],
                                  usable_status="USABLE", geometry_valid=True)])
    return dict(rgb=rgb, depth_m=depth, K=k, T_base_camera=transform,
                roi_xyxy=(2, 2, 30, 18), patch=patch)


def test_numeric_projection_robot_base_non_square_and_preserves_all_candidates():
    args = fixture()
    candidates = [*args["patch"]["candidates"],
                  dict(point_id="behind", position_base_m=[1, 2, 2]),
                  dict(point_id="off-image", position_base_m=[5, 2, 3.8]),
                  dict(point_id="off-roi", position_base_m=[.7, 2, 3.8])]
    results = project_candidate_dots(candidates, args["K"], args["T_base_camera"],
                                    image_shape=(20, 32), roi_xyxy=args["roi_xyxy"])
    assert [record["point_id"] for record in results] == [c["point_id"] for c in candidates]
    np.testing.assert_allclose(results[0]["pixel_uv"], [16, 10])
    np.testing.assert_allclose(results[0]["crop_pixel_uv"], [14, 8])
    assert [record["not_drawn_reason"] for record in results] == [None, None, "BEHIND_CAMERA", "OUTSIDE_IMAGE", "OUTSIDE_ROI"]
    assert all(record["display_status"] == "UNKNOWN" for record in results)


def test_candidate_rendering_never_turns_reported_usable_into_safety_claim():
    result = build_patch_diagnostics(**fixture())
    meta = result["metadata"]
    assert meta["candidate_count"] == meta["drawn_candidate_count"] == 2
    assert meta["candidate_projections"][1]["reported_usable_status"] == "USABLE"
    assert meta["candidate_display_status"] == "UNKNOWN"
    assert meta["visualization_does_not_certify_execution"]
    assert not meta["semantic_identity_verified"]
    np.testing.assert_array_equal(result["images"]["candidates"][8, 14], UNKNOWN_COLOR)


def test_support_is_reconstructed_plane_compatibility_not_ransac_witness():
    args = fixture()
    args["depth_m"][4:7, 4:7] = 1.1
    result = build_patch_diagnostics(**args)
    meta = result["metadata"]
    assert meta["plane_support_status"] == "RECONSTRUCTED_PLANE_DISTANCE_COMPATIBILITY"
    assert not meta["plane_support_is_original_fit_membership"]
    assert meta["plane_compatible_pixel_count"] == 28*16-9
    np.testing.assert_array_equal(result["images"]["plane_support"][3, 3], [100, 100, 100])
    assert not np.array_equal(result["images"]["plane_support"][10, 10], [100, 100, 100])


def test_unknown_geometry_shows_no_fabricated_support_and_depth_invalid_stays_visible():
    args = fixture()
    args["patch"].update(geometry_status="UNKNOWN", normal_base=None,
                         centroid_base_m=None, candidates=[], reason_codes=["INSUFFICIENT_PLANE_SUPPORT"])
    args["depth_m"][5, 5] = np.nan
    result = build_patch_diagnostics(**args)
    assert result["metadata"]["plane_support_status"] == "NOT_AVAILABLE"
    assert result["metadata"]["plane_compatible_pixel_count"] is None
    np.testing.assert_array_equal(result["images"]["plane_support"], result["images"]["rgb_crop"])
    np.testing.assert_array_equal(result["images"]["metric_depth"][3, 3], INVALID_DEPTH_COLOR)


def test_depth_colors_use_fixed_metric_range_not_per_crop_normalization():
    first = fixture()
    second = fixture()
    second["depth_m"][4, 4] = 2.5
    a, b = build_patch_diagnostics(**first), build_patch_diagnostics(**second)
    np.testing.assert_array_equal(a["images"]["metric_depth"][8, 8], b["images"]["metric_depth"][8, 8])


def test_visualization_has_no_pillow_or_simulator_import_side_effect():
    # New process avoids modules imported by unrelated pytest tests.
    code = ("import sys; import embodied_runtime.perception.visualization; "
            "assert 'PIL' not in sys.modules; assert 'mujoco' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True)


def test_writer_preserves_candidate_metadata_and_refuses_overwrite(tmp_path):
    if importlib.util.find_spec("PIL") is None:
        pytest.skip("Pillow is optional outside the P1 rendering environment")
    output = tmp_path/"view"
    meta = write_patch_diagnostics(output, **fixture())
    persisted = json.loads((output/"metadata.json").read_text())
    assert persisted == meta
    assert set(meta["image_paths"]) == {"rgb_crop", "metric_depth", "plane_support", "candidates"}
    assert all((output/path).exists() for path in meta["image_paths"].values())
    with pytest.raises(FileExistsError):
        write_patch_diagnostics(output, **fixture())


def test_frame_and_roi_mismatch_rejected():
    args = fixture()
    with pytest.raises(ProtocolError, match="FRAME_MISMATCH"):
        build_patch_diagnostics(**args, source_frame_id="another-frame")
    args["roi_xyxy"] = (3, 2, 30, 18)
    with pytest.raises(ProtocolError, match="ROI_MISMATCH"):
        build_patch_diagnostics(**args)


def test_config_mismatch_cannot_silently_redraw_with_different_plane_threshold():
    args = fixture()
    args["patch"]["metrics"] = {"config_sha256": "incorrect"}
    with pytest.raises(ProtocolError, match="CONFIG_MISMATCH"):
        build_patch_diagnostics(**args)
