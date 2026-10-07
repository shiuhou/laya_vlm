"""Synthetic evaluator tests; these never open Formal-50 human labels."""
import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_formal50_scoring as scoring


IMAGE = dict(width=8, height=8)
VISIBLE = dict(status="VISIBLE", polygons=[[[1, 1], [5, 1], [5, 5], [1, 5]]])


def estimate(reason=None, points=()):
    return dict(source_identity=dict(intrinsics_K=np.eye(3).tolist(), T_base_camera=np.eye(4).tolist()),
        patch=dict(geometry_status="UNKNOWN" if reason else "VALID", reason_codes=[reason] if reason else [],
            metrics={}, candidates=[dict(position_base_m=[x,y,1], point_id=str(i), usable_status="UNKNOWN",
                reason_codes=["FEASIBILITY_NOT_EVALUATED", "UNCALIBRATED_UNCERTAINTY"])
                for i,(x,y) in enumerate(points)]))


def evaluate(truth=VISIBLE, patch=None, box=(0,0,8,8), mask=None):
    return scoring.score_mask(IMAGE,truth,np.ones((8,8),dtype=bool) if mask is None else mask,
        estimate() if patch is None else patch, ordinal=0, box=box)


def test_unknown_and_not_visible_preserve_geometry_boundary():
    for visibility in ("UNKNOWN", "NOT_VISIBLE"):
        row=evaluate(dict(status=visibility,polygons=[]),estimate("AMBIGUOUS_DEPTH_COMPONENTS"))
        assert row["human_status"] == row["evaluation_category"] == visibility
        assert row["geometry_category"] == "AMBIGUOUS_DEPTH_COMPONENTS"
        assert row["mask_overlap"]["annotated_overlap_pixels"] is None


def test_candidate_outside_is_identity_failure_not_geometry_success():
    row=evaluate(patch=estimate(points=[(2,2),(6,6)]))
    assert row["geometry_category"] == "GEOMETRIC_CANDIDATE"
    assert row["evaluation_category"] == "SEGMENTATION_IDENTITY_FAILURE"
    assert row["task_valid_candidate_count"] == 1
    assert row["outside_region_candidate_count"] == 1
    assert all(p["executable_acceptance"] is False for p in row["candidates"])


def test_zero_overlap_mask_and_partial_box_are_separate():
    mask=np.zeros((8,8),dtype=bool)
    mask[6:,6:]=True
    row=evaluate(mask=mask,box=(0,0,3,8),patch=estimate("AMBIGUOUS_DEPTH_COMPONENTS"))
    assert row["evaluation_category"] == "SEGMENTATION_IDENTITY_FAILURE"
    assert row["geometry_category"] == "AMBIGUOUS_DEPTH_COMPONENTS"
    assert row["box_overlap"]["intersects_annotated_region"] is True
    assert row["box_overlap"]["fully_covers_annotated_region"] is False
    assert row["box_overlap"]["annotated_coverage"] == .5


def test_valid_plane_without_tool_candidate_is_rejected():
    row=evaluate()
    assert row["geometry_status"] == "VALID"
    assert row["evaluation_category"] == "EDGE_UNCERTAINTY_TOOL_REJECTED"
    row=evaluate(patch=estimate(points=[(2,2)]))
    assert row["evaluation_category"] == "VALID_DRAWER_FRONT_CANDIDATE"
    assert row["candidates"][0]["usable_status"] == "UNKNOWN"


def test_missing_generation_seal_precedes_annotation_access(tmp_path, monkeypatch):
    opened=[]
    original=scoring.read
    def audited(path):
        opened.append(str(path))
        return original(path)
    monkeypatch.setattr(scoring,"read",audited)
    with pytest.raises(FileNotFoundError):
        scoring.score(tmp_path)
    assert not any("annotations" in p for p in opened)


def test_unsealed_output_is_rejected_before_annotation_access(tmp_path):
    for stage in ("masks", "geometry"):
        directory=tmp_path/stage
        directory.mkdir()
        scoring.write(directory/"decoy.json",{})
        scoring.seal(directory)
    with pytest.raises(ProtocolError):
        scoring.score(tmp_path)
