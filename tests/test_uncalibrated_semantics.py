import numpy as np
import pytest

from embodied_runtime.adapters.locateanything import parse_locateanything
from embodied_runtime.fusion import MultiRateFusion
from embodied_runtime.runtime_core import BeliefStore
from embodied_runtime.vision import LocateAnythingProvider


def observe(result, *, source="locateanything+depth"):
    provider = LocateAnythingProvider(lambda rgb, query: result,
                                     {"fx": 10, "fy": 10, "cx": 10, "cy": 10}, source=source)
    return provider.observe(np.zeros((20, 20, 3), dtype=np.uint8), np.ones((20, 20)), "drawer_front",
                            episode_id="ep", source_seq=1, capture_sim_time=1,
                            camera_to_world_matrix=np.eye(4))


def test_parser_detection_is_not_confidence_even_for_perfect_syntax():
    parsed = parse_locateanything("<box><100><100><900><900></box>", 20, 20)
    assert parsed["detection_present"] is True
    assert parsed["calibrated_confidence"] is None
    assert "score" not in parsed
    empty = parse_locateanything("no detection", 20, 20)
    assert empty["detection_present"] is False
    assert empty["calibrated_confidence"] is None


@pytest.mark.parametrize("raw", [{}, {"score": 1.0}, {"confidence": .9}, {"score": None}])
def test_box_with_uncalibrated_score_has_geometry_without_fabricated_probability(raw):
    event = observe({"boxes_xyxy": [[2, 2, 18, 18]], **raw})
    assert event is not None and event.quality == 1.0
    assert event.value["calibrated_confidence"] is None
    assert event.value["detection_present"] is True
    assert event.value["semantic_evidence_kind"] == "categorical_binding"
    assert "probabilities" not in event.value
    fusion = MultiRateFusion()
    assert fusion.ingest_event(event, reference_time=1)
    assert "drawer_front" in fusion.geometry
    assert not fusion.semantic.tracks


def test_categorical_label_never_triggers_legacy_certainty_fallback():
    event = observe({"boxes_xyxy": [[2, 2, 18, 18]]}, source="semantic")
    store = BeliefStore("ep", allow_delayed=False)
    assert store.ingest(event, now_sim=1)
    assert not store._semantic


def test_calibrated_probability_requires_matching_recorded_evidence():
    calibrated = {"boxes_xyxy": [[2, 2, 18, 18]], "calibrated_confidence": .8,
                  "model_revision": "model-rev-1",
                  "calibration_provenance": {"calibration_id": "cal-1",
                      "evidence_ref": "calibration-report-sha256-fixture", "model_revision": "model-rev-1"}}
    event = observe(calibrated)
    assert event.quality == 1
    assert event.value["probabilities"]["drawer_front"] == .8
    assert event.value["semantic_evidence_kind"] == "calibrated_probability"
    for change in ({"calibration_provenance": None}, {"calibrated_confidence": float("nan")},
                   {"model_revision": "different"}, {"calibrated_confidence": 2}):
        with pytest.raises(ValueError):
            observe({**calibrated, **change})


def test_no_detection_and_no_depth_do_not_invent_geometry():
    assert observe({"boxes_xyxy": []}) is None
    provider = LocateAnythingProvider(lambda rgb, query: {"boxes_xyxy": [[2, 2, 18, 18]]},
                                     {"fx": 10, "fy": 10, "cx": 10, "cy": 10})
    assert provider.observe(np.zeros((20, 20, 3), dtype=np.uint8), np.full((20, 20), np.nan),
                            "drawer", episode_id="ep", source_seq=1, capture_sim_time=1) is None
