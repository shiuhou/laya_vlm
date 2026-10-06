import copy
import hashlib
import json

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.experiments.p1_observability_closure import _score_image, score


def fixture(status):
    image = dict(image_id="i", frame_id="f", rgb_blob_sha256="0" * 64,
                 rgb_pixel_sha256="1" * 64, png_sha256="2" * 64, width=16, height=16,
                 init_index=0, camera_id="camera")
    polygons = [[[0, 0], [8, 0], [8, 8], [0, 8]]] if status == "VISIBLE" else []
    label = {k: v for k, v in image.items() if k not in ("init_index", "camera_id")}
    label["entities"] = dict(drawer_front_pushable=dict(status=status, polygons=polygons, reason="test"))
    surface = dict(surface_id="s", plane_valid=True, support_row_spans=[[y, 0, 8] for y in range(8)])
    candidate = dict(point_id="p", position_base_m=[.5, .5, 1.], usable_status="UNKNOWN", reason_codes=[])
    entity = dict(entity="drawer_front_pushable", parsed_status="single_box", structurally_admitted=True,
                  roi_inventories=[dict(box_index=0, roi_xyxy=[0, 0, 8, 8],
                                       evidence=dict(inventory=dict(surfaces=[surface])))],
                  original_geometry=[dict(box_index=0, structural_reason=None,
                    patch=dict(geometry_status="VALID", metrics={}, reason_codes=[], candidates=[candidate]))])
    record = dict(image=image, entities=[entity], scene_context=dict(
        source=dict(intrinsics_K=np.diag([10., 10., 1.]).tolist(), T_base_camera=np.eye(4).tolist()),
        inventory=dict(surfaces=[surface])))
    return record, label


def test_offline_overlap_does_not_promote_geometry_to_target_identity():
    record, label = fixture("VISIBLE")
    before = copy.deepcopy(record)
    result = _score_image(record, label)["entities"][0]
    assert result["evaluator_only_support_exists"] is True
    assert result["support_metrics"][0]["support_purity"] == 1.
    assert result["original_candidate_metrics"][0]["inside_annotated_region"] is True
    assert result["semantic_identity"] == result["fixedness"] == "UNKNOWN"
    assert result["reference_status"] == "REFERENCE_UNKNOWN"
    assert record == before
    record, label = fixture("UNKNOWN")
    result = _score_image(record, label)["entities"][0]
    assert result["evaluator_only_support_exists"] is None
    assert result["support_metrics"][0]["support_purity"] is None
    assert result["original_candidate_metrics"][0]["inside_annotated_region"] is None


def test_changed_generation_rejected_before_attempt_to_read_annotations(tmp_path):
    files = {}
    for i in range(50):
        path = tmp_path / f"frame-{i:03d}.json"
        path.write_text("{}")
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "generation-sealed.json").write_text(json.dumps(dict(
        frame_count=50, evaluation_labels_consumed=False, files=files, seal_sha256=content_hash(files))))
    (tmp_path / "frame-000.json").write_text('{"tampered":true}')
    with pytest.raises(ProtocolError, match="CONDITION_CHANGED"):
        score(tmp_path, tmp_path / "nonexistent-annotations.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()
