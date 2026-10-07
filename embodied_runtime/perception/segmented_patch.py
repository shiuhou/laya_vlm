"""Source-bound learned-mask geometry diagnostic, without action authority.

A mask is a learned hypothesis, not verified target identity. Outside-mask
depth is UNKNOWN; native-mask depth availability and BOX coverage are distinct.
Persisted artifact bytes must be authenticated by the caller before admission.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping

import numpy as np

from ..contracts import content_hash, require, thaw
from .rgbd_geometry import GeometryConfig, _roi, estimate_visible_patch
from .surface_association import sensor_view_identity


def _sha256(value, name):
    require(isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value), f"invalid {name}")


def estimate_segmented_patch(view, original_box, mask, *, mask_binding, config,
                             track_id, feature_id, seed=0, eef_position_base_m=None,
                             measurement_contract="native-mask-depth/2"):
    """Evaluate one native mask; never rank masks or select a target winner.

    ``mask_binding`` binds the complete sensor identity, original BOX response
    and ordinal, RGB-only mask input, native ordinal, raw boolean bytes and
    persisted artifact receipt. File-byte verification belongs to the caller;
    this function verifies the raw mask against that receipt. No semantic
    correctness, calibrated confidence, fixedness or executability is implied.
    """
    require(isinstance(mask_binding, Mapping), "mask binding required")
    require(measurement_contract in {"native-mask-depth/2", "original-box-depth/1"},
            "explicit known depth measurement contract required")
    require(isinstance(config, GeometryConfig), "explicit unchanged geometry config required")
    source = sensor_view_identity(view)
    source_hash = content_hash(source)
    require(mask_binding.get("source_identity") == source
            and mask_binding.get("sensor_view_sha256") == source_hash,
            "mask sensor source mismatch", "SOURCE_MISMATCH")
    require(mask_binding.get("evaluation_labels_used") is False
            and mask_binding.get("mask_input_channels") == ["rgb"]
            and mask_binding.get("provenance") == "learned estimate",
            "mask must be an RGB-only learned hypothesis without evaluation labels",
            "INFORMATION_BOUNDARY")
    require(mask_binding.get("coordinate_convention") == "top-left-origin-pixel-xyxy",
            "explicit original pixel coordinate convention required")
    require(isinstance(mask_binding.get("query"), str) and bool(mask_binding["query"]),
            "explicit semantic query required")
    for name in ("box_index", "mask_index"):
        require(type(mask_binding.get(name)) is int and mask_binding[name] >= 0,
                f"nonnegative native {name} required")
    for name in ("box_response_sha256", "raw_mask_sha256", "mask_artifact_sha256"):
        _sha256(mask_binding.get(name), name)
    require(isinstance(mask_binding.get("mask_artifact_uri"), str)
            and bool(mask_binding["mask_artifact_uri"]), "mask artifact URI required")

    depth = np.asarray(view["depth_m"])
    native_mask = np.asarray(mask)
    require(depth.ndim == 2 and depth.dtype.kind == "f", "metric float depth required")
    require(native_mask.dtype == bool and native_mask.shape == depth.shape,
            "native bool mask must preserve full sensor HW shape")
    require(np.asarray(view["rgb"]).shape == (*depth.shape, 3), "RGB/depth dimensions disagree")
    native_sha = hashlib.sha256(native_mask.tobytes(order="C")).hexdigest()
    require(mask_binding["raw_mask_sha256"] == native_sha,
            "native mask differs from artifact receipt", "SOURCE_MISMATCH")
    box = np.asarray(original_box, dtype=float)
    bound_box = np.asarray(mask_binding.get("box_xyxy"), dtype=float)
    require(box.shape == (4,) and bound_box.shape == (4,) and np.array_equal(box, bound_box),
            "original BOX differs from mask request binding", "SOURCE_MISMATCH")
    h, w = depth.shape
    x0, y0, x1, y1 = _roi(box, w, h)
    roi_mask = np.zeros(depth.shape, dtype=bool)
    roi_mask[y0:y1, x0:x1] = True
    inside_count = int(np.count_nonzero(native_mask & roi_mask))
    outside_count = int(np.count_nonzero(native_mask & ~roi_mask))

    # Preserve all native pixels and the original BOX. This is no crop,
    # intersection/morphology operation, depth completion, or retimestamping.
    masked_depth = depth.copy()
    masked_depth[~native_mask] = np.nan
    masked_depth.setflags(write=False)
    patch = estimate_visible_patch(
        masked_depth, view["intrinsics_K"], view["T_base_camera"],
        roi_xyxy=box, source_frame_id=source["frame_id"],
        calibration_version=source["calibration_version"], track_id=track_id,
        feature_id=feature_id, capture_sim_time_s=view["capture_sim_time_s"],
        capture_monotonic_ns=view["capture_monotonic_ns"], config=config, seed=seed,
        eef_position_base_m=eef_position_base_m,
        depth_availability_mask=native_mask if measurement_contract == "native-mask-depth/2" else None,
    )
    return dict(
        condition="p1-segmented-patch/2" if measurement_contract == "native-mask-depth/2" else "p1-segmented-patch/1",
        **({"measurement_contract": measurement_contract} if measurement_contract == "native-mask-depth/2" else {}),
        source_identity=source,
        sensor_view_sha256=source_hash, mask_binding=thaw(mask_binding),
        raw_mask_sha256=native_sha,
        original_depth_sha256=source["depth_sha256"],
        masked_depth_sha256=hashlib.sha256(masked_depth.tobytes()).hexdigest(),
        original_box_xyxy=box.tolist(), original_roi_pixel_count=int(roi_mask.sum()),
        native_mask_pixel_count=inside_count+outside_count,
        mask_pixels_inside_original_roi=inside_count,
        mask_pixels_outside_original_roi=outside_count,
        mask_occupancy_inside_original_roi=inside_count/max(1, int(roi_mask.sum())),
        patch=patch.to_dict(), calibrated_confidence=None,
        evidence_provenance={"depth": "sensor-derived", "mask": "learned estimate"},
        semantic_identity="UNKNOWN", semantic_identity_verified=False,
        mask_is_learned_hypothesis=True, for_execution=False,
    )
