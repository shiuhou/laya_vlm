"""Synthetic-only evaluator invariants; never consume real heldout observations."""
from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_box_grounding_heldout_scoring as scorer


def candidate(inside):
    return dict(inside_annotated_region=inside,
                evaluation_category='VALID_DRAWER_FRONT_CANDIDATE' if inside else 'SEGMENTATION_IDENTITY_FAILURE')


def test_box_localization_is_independent_of_point_and_needs_same_box_thresholds():
    image = dict(width=20, height=20)
    label = np.zeros((20, 20), dtype=bool)
    label[5:15, 5:15] = True
    exact = scorer.box_score([5, 5, 15, 15], image, label)
    broad = scorer.box_score([0, 0, 20, 20], image, label)
    partial = scorer.box_score([5, 5, 10, 15], image, label)
    assert exact['localization_correct']
    assert broad['annotated_coverage'] == 1 and not broad['localization_correct']
    assert partial['human_support_bbox_iou'] == .5 and not partial['localization_correct']
    assert scorer.box_score([0, 0, 20, 20], image, None)['localization_correct'] is None


def test_clean_pool_checks_all_admitted_masks_and_retains_raw_wrong_points():
    natives = [dict(mask_point_admission=dict(admitted=True), candidates=[candidate(True)]),
               dict(mask_point_admission=dict(admitted=True), candidates=[candidate(False)])]
    pool = scorer.candidate_pool(natives)
    assert pool['admitted']['any_correct'] and not pool['admitted']['clean']
    assert pool['admitted']['outside'] == 1
    natives[1]['mask_point_admission']['admitted'] = False
    pool = scorer.candidate_pool(natives)
    assert pool['admitted']['clean'] and pool['raw']['outside'] == 1
    assert not scorer.candidate_pool([])['admitted']['clean']


def rows_fixture():
    rows = []
    for init in scorer.INITS:
        arm = dict(complete_eos=True, typed_admitted=True, any_box_correct=True,
            all_boxes_correct=True, boxes=[], generated_sam_boxes=0, inference_s=.1, native_mask_count=0,
            pools={key:dict(total=0, correct=0, outside=0, unscored=0, any_correct=False, clean=False)
                   for key in ('raw', 'admitted')}, clean=False, failure_reasons=['INCOMPLETE_GENERATION'])
        rows.append(dict(init_index=init, image_id=f'test/{init}', human_status='VISIBLE',
            point=dict(complete_eos=False, typed_admitted=False, depth_available=False, inside_human_region=None,
                       reason='INCOMPLETE_GENERATION', inference_s=.2),
            arms=dict(A=deepcopy(arm), B=deepcopy(arm))))
    return rows


def test_all23_denominator_keeps_point_failures_and_box_success_separate():
    rows = rows_fixture()
    report = scorer.summarize(rows, labels_available=True)
    assert report['point']['typed']['n'] == 0 and report['point']['typed']['denominator'] == 23
    assert report['arms']['B']['box_localization_all']['n'] == 23
    assert report['arms']['B']['clean_all']['n'] == 0
    assert report['paired']['clean_common_sam']['denominator'] == 0
    assert not report['arms']['B']['spatial_ready_signal']
    assert report['p1_pass_claimed'] is False
    rows[0]['human_status'] = 'UNKNOWN'
    report = scorer.summarize(rows, labels_available=True)
    assert report['arms']['B']['box_localization_visible']['denominator'] == 22
    assert report['arms']['B']['box_localization_all']['denominator'] == 23


def test_operational_report_never_invents_semantic_grades_or_pass():
    rows = rows_fixture()
    for row in rows:
        row['human_status'] = 'ANNOTATION_PENDING'
        for arm in row['arms'].values():
            arm.update(any_box_correct=None, all_boxes_correct=None, clean=None)
            for pool in arm['pools'].values():
                pool.update(correct=None, outside=None, any_correct=None, clean=None)
    report = scorer.summarize(rows, labels_available=False)
    assert report['annotation_status'] == 'AWAITING_INDEPENDENT_HUMAN'
    assert report['arms']['A']['clean_all'] is None
    assert report['arms']['A']['candidate_counts']['admitted']['correct'] is None
    assert report['arms']['A']['spatial_ready_signal'] is None
    assert 'paired' not in report


def test_labels_are_never_opened_before_generation_seals(monkeypatch, tmp_path):
    def blocked(_):
        raise ProtocolError('SOURCE_MISMATCH', 'unsealed geometry')
    monkeypatch.setattr(scorer, 'verified_generation', blocked)
    monkeypatch.setattr(scorer, 'validate_complete', lambda *args: pytest.fail('labels opened before seals'))
    with pytest.raises(ProtocolError, match='SOURCE_MISMATCH'):
        scorer.run(tmp_path, packet=tmp_path/'packet', annotations=tmp_path/'does-not-exist.json')


def test_spatial_signal_requires_zero_wrong_and_is_not_p1_pass():
    rows = rows_fixture()
    for row in rows[:19]:
        row['arms']['B']['clean'] = True
        row['arms']['B']['generated_sam_boxes'] = 1
        row['arms']['B']['pools']['admitted'].update(total=1, correct=1)
    report = scorer.summarize(rows, labels_available=True)
    assert report['arms']['B']['spatial_ready_signal']
    assert report['substantial_engineering_gain'] and not report['p1_pass_claimed']
    rows[-1]['arms']['B']['pools']['admitted']['outside'] = 1
    assert not scorer.summarize(rows, labels_available=True)['arms']['B']['spatial_ready_signal']
    pair = scorer.matched([False, True], [True, False])
    assert pair['gains'] == pair['losses'] == 1 and pair['net_gain'] == 0


def test_row_build_scores_boxes_even_when_shared_point_prevents_all_sam(monkeypatch):
    from types import SimpleNamespace
    from embodied_runtime.experiments import p1_mask_support_reanalysis
    monkeypatch.setattr(p1_mask_support_reanalysis, 'config', lambda: SimpleNamespace(min_depth_m=.01, max_depth_m=5.))
    sensors, calls, geometry, truth = {}, {}, [], {}
    for init in scorer.INITS:
        image = dict(image_id=f'test/{init}', width=20, height=20)
        sensors[init] = (dict(image=image), dict(depth_m=np.ones((20, 20))), {})
        truth[image['image_id']] = dict(entities=dict(drawer_front_pushable=dict(
            status='VISIBLE', polygons=[[[5, 5], [15, 5], [15, 15], [5, 15]]])))
        calls[init, 'POINT'] = dict(source_admitted=False, reason='INCOMPLETE_GENERATION', point_xy=None, sample_pixel_xy=None)
        for arm, box in (('A', [0, 0, 20, 20]), ('B', [5, 5, 15, 15])):
            calls[init, arm] = dict(source_admitted=True, reason=None, ordered_boxes=[box])
            geometry.append(dict(init_index=init, arm=arm, box_index=0, box_xyxy=box,
                status='UPSTREAM_UNAVAILABLE', failure_stage='INCOMPLETE_GENERATION',
                prompt_admission=dict(admitted=False, reason='INCOMPLETE_GENERATION'), native_results=[]))
    rows = scorer.build_rows(sensors, calls, geometry, truth)
    report = scorer.summarize(rows, labels_available=True)
    assert len(rows) == 23
    assert report['arms']['A']['box_localization_all']['n'] == 0
    assert report['arms']['B']['box_localization_all']['n'] == 23
    assert report['point']['typed']['n'] == 0
    assert report['arms']['B']['sam_generated_frames'] == 0
    assert report['interpretation'] == 'PARTIAL_BOX_IMPROVEMENT_END_TO_END_BLOCKED'
    operational = scorer.build_rows(sensors, calls, geometry)
    assert operational[0]['arms']['A']['pools']['admitted']['correct'] is None
