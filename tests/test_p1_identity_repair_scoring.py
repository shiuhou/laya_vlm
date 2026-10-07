"""Three synthetic checks; no frozen human annotations or inference inputs."""
import pytest
import hashlib

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_identity_repair_scoring as scoring


def test_unknown_point_label_relation_never_becomes_false_or_true():
    polygons = [[[0,0],[4,0],[4,4],[0,4]]]
    assert scoring.point_label_relation([2,2],dict(status="UNKNOWN",polygons=polygons)) is None
    assert scoring.point_label_relation([2,2],dict(status="NOT_VISIBLE",polygons=[])) is None
    assert scoring.point_label_relation(None,dict(status="VISIBLE",polygons=polygons)) is None
    assert scoring.point_label_relation([2,2],dict(status="VISIBLE",polygons=polygons)) is True
    assert scoring.point_label_relation([7,7],dict(status="VISIBLE",polygons=polygons)) is False
    raw="<point><500><500></point>"
    incomplete=dict(raw_output=raw,response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                    audit=dict(complete_generation=False,terminal_eos_observed=False),
                    typed=None,source_admitted=False,point_xy=None,sample_pixel_xy=None,
                    reason="INCOMPLETE_GENERATION")
    scoring.verify_complete_point(incomplete,dict(width=8,height=8))
    with pytest.raises(ProtocolError):
        scoring.verify_complete_point({**incomplete,"point_xy":[4,4]},dict(width=8,height=8))


def test_raw_prompt_effect_and_admission_filter_are_reported_separately():
    def mask(n, admitted=True):
        return dict(candidates=[{}]*n,task_valid_candidate_count=0,outside_region_candidate_count=n,
                    point_admission=dict(admitted=admitted),mask_overlap=dict(contamination=1.0))
    baseline = [dict(image_id="a",boxes=[dict(masks=[mask(10)])]),
                dict(image_id="b",boxes=[dict(masks=[mask(20)])])]
    rows = [dict(image_id="a",camera_id="agentview",human_status="VISIBLE",
                 point_inside_annotated_region=False,frame_categories=["SEGMENTATION_IDENTITY_FAILURE"],
                 boxes=[dict(masks=[mask(4,False)])]),
            dict(image_id="b",camera_id="agentview",human_status="VISIBLE",
                 point_inside_annotated_region=None,frame_categories=["POINT_NOT_ADMITTED"],boxes=[])]
    paired,summary=scoring.paired_metrics(rows,baseline)
    total=summary["total"]
    assert total["frame_denominator"] == 2
    assert total["planned_mask_slots"] == 6
    assert total["candidate_counts"]["baseline_candidate_count"] == 30
    assert total["candidate_counts"]["raw_candidate_count"] == 4
    assert total["candidate_counts"]["admitted_candidate_count"] == 0
    assert total["matched_generated_subgroup"]["candidate_counts"]["baseline_candidate_count"] == 10
    assert total["matched_generated_subgroup"]["frame_denominator"] == 1
    assert paired[1]["raw_mask_generation_completed"] is False


def test_missing_point_seal_stops_before_annotation_access(tmp_path,monkeypatch):
    paths=[]
    original=scoring.read
    def tracked(path):
        paths.append(str(path))
        return original(path)
    monkeypatch.setattr(scoring,"read",tracked)
    with pytest.raises(FileNotFoundError):
        scoring.score(tmp_path)
    assert not any("annotation" in path for path in paths)
