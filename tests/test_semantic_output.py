"""Boundary tests for whole-reply admission and independent typed channels."""
import pytest

from embodied_runtime.experiments.p1_surface_dev import semantic_pair
from embodied_runtime.experiments.point_grounding_probe import generation_audit, parse_grounding
from embodied_runtime.perception.semantic_output import parse_semantic_reply

POINT = '<box><671><246></box>'
BOX = '<box><673><350><1000><997></box>'
EOS = '<|im_end|>'


def parse(raw, mode='point', **audit_overrides):
    audit = {**generation_audit([7, 99], 10, 16384, 99), **audit_overrides}
    return parse_semantic_reply(raw, 384, 256, mode=mode, audit=audit)


def test_complete_mixed_reply_preserves_typed_atoms_and_unmodified_raw_spans():
    raw = '<ref>front panel</ref>'+POINT+BOX+EOS
    result = parse(raw)
    assert result.admitted and result.selected_ordinals == (0,) and result.auxiliary_ordinals == (1,)
    assert result.atoms[0].pixels == (257.664, 62.976)
    assert result.atoms[0].sample_pixel_xy == (257, 62)
    assert result.atoms[1].pixels == (258.432, 89.6, 384., 255.232)
    assert result.raw_output == raw and result.calibrated_confidence is None
    assert not result.semantic_identity_verified and not result.for_execution
    for atom in result.atoms:
        assert raw[slice(*atom.raw_span)] == atom.raw_text
    reordered = parse(BOX+POINT+EOS)
    assert reordered.admitted and reordered.selected_ordinals == (1,)
    assert parse_grounding(raw, 384, 256)['status'] == 'mixed'  # legacy unchanged


@pytest.mark.parametrize('raw', [
    POINT+POINT+EOS, BOX+EOS, POINT+'<box>none</box>'+EOS,
    POINT+'<box><1><2><3></box>'+EOS, POINT+'<box><3><2><1><4></box>'+EOS,
    POINT+'<box><1001><2><1002><4></box>'+EOS,
    POINT+'<box><-1><2></box>'+EOS, '<box><1000><250></box>'+EOS,
    'prose'+POINT+EOS, POINT+'prose'+EOS, POINT+EOS+'prose',
    POINT+EOS+EOS, '<ref>a</ref><ref>b</ref>'+POINT+EOS,
    '<ref><box><1><2></box></ref>'+POINT+EOS, POINT+'<box><1><2>'+EOS,
    POINT, POINT+EOS+' ', '',
])
def test_invalid_or_nonunique_reply_never_admitted(raw):
    assert not parse(raw).admitted


@pytest.mark.parametrize('audit', [
    {'complete_generation': False}, {'terminal_eos_observed': False},
    {'actual_generated_token_ids': [7, 8]}, {'actual_generated_token_count': 3},
    {'actual_generated_token_ids': [99, 99]}, {'effective_limit': 1},
    {'length_limit_reached': True}, {'model_max_length': 11},
])
def test_textual_eos_does_not_override_generation_integrity(audit):
    assert not parse(POINT+BOX+EOS, **audit).admitted


def test_box_channel_retains_all_rois_in_order_and_does_not_use_auxiliary_point():
    raw = BOX+POINT+'<box><1><2><3><4></box>'+EOS
    result = parse(raw, mode='box')
    assert result.admitted and result.selected_ordinals == (0, 2)
    assert result.auxiliary_ordinals == (1,)
    assert [a.normalized for a in result.selected] == [(673, 350, 1000, 997), (1, 2, 3, 4)]
    assert parse('<box>none</box>'+EOS).reason == 'EXPLICIT_NONE'
    assert not parse(POINT+EOS, mode='box').admitted


def response(raw, mode):
    return dict(raw_output=raw, mode=mode, frame={}, entity='drawer_front_pushable',
                audit=generation_audit([7, 99], 10, 16384, 99), parsed=parse_grounding(raw, 384, 256))


def test_pair_uses_only_independent_box_call_and_preserves_failed_pair_before_geometry():
    independent = '<box><622><0><998><456></box>'
    box, point = response(independent+EOS, 'box'), response(POINT+BOX+EOS, 'point')
    new = semantic_pair(box, point, {}, 'drawer_front_pushable', semantic_contract='typed-v1')
    assert new['admitted'] and len(new['boxes']) == len(new['xy']) == 1
    assert new['boxes'][0]['normalized'] == [622, 0, 998, 456]
    assert new['typed']['point']['auxiliary_ordinals'] == (1,)
    old = semantic_pair(box, point, {}, 'drawer_front_pushable', semantic_contract='legacy')
    assert not old['admitted'] and not old['xy']
    for bad_box, bad_point in ((response(POINT+EOS, 'box'), point),
                               (box, response(POINT+POINT+EOS, 'point'))):
        failed = semantic_pair(bad_box, bad_point, {}, 'drawer_front_pushable', semantic_contract='typed-v1')
        assert not failed['admitted'] and not failed['boxes'] and not failed['xy']


def test_pair_source_mismatch_rejected():
    from embodied_runtime.contracts import ProtocolError
    with pytest.raises(ProtocolError, match='SOURCE_MISMATCH'):
        semantic_pair(response(BOX+EOS, 'box'), response(POINT+EOS, 'point'), {'frame_id': 'other'},
                      'drawer_front_pushable', semantic_contract='typed-v1')
