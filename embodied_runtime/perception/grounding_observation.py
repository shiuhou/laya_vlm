"""Source-bound 2D proposals, independent of semantic correctness and execution.

Qwen coordinates follow the official Qwen3-VL 2D grounding convention: [0,1000]
relative to the original image. The entire reply must be JSON, optionally inside
one complete `````json`` fence. No prefix extraction, coordinate repair or model
imports are permitted here. LocateAnything retains its native typed parser.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
import re

from ..contracts import content_hash, freeze, require, thaw
from .semantic_output import parse_semantic_reply

CONTRACT = "p1-grounding-observation/1"
MAPPED_CONTRACT = "p1-grounding-observation/2-model-crop"
CROP_CONTRACT = "model-box-crop/1"
QWEN_CONTRACT = "qwen3vl-grounding-json/1"
QWEN_FORMATS = ("whole-json", "whole-json-fence")
COORDINATES = "normalized-0-1000-original-image-xy"
LABEL = "drawer_front_pushable"


@dataclass(frozen=True)
class GroundingReply:
    contract: str
    mode: str
    raw_output: str
    width: int
    height: int
    admitted: bool
    reason: str | None
    ordered_boxes_xyxy_px: tuple = ()
    point_xy_px: tuple | None = None
    sample_pixel_xy: tuple | None = None
    native_records: tuple = ()
    response_format: str | None = None
    calibrated_confidence: None = None
    semantic_identity_verified: bool = False
    for_execution: bool = False

    def evidence(self):
        return thaw(self)


def _request(mode, width, height):
    if not isinstance(mode, str) or mode.upper() not in {"BOX", "POINT"}:
        raise ValueError("explicit BOX or POINT mode required")
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("positive original image dimensions required")
    return mode.upper()


def _generation_reason(audit):
    """Check token evidence, not a model-generated claim or an EOS text suffix."""
    ids = audit.get("actual_generated_token_ids")
    eos = audit.get("eos_token_ids", [audit.get("eos_token_id")])
    count, limit = audit.get("actual_generated_token_count"), audit.get("effective_limit")
    inputs, maximum = audit.get("input_token_count"), audit.get("model_max_length")
    if not (isinstance(ids, (list, tuple)) and all(type(x) is int and x >= 0 for x in ids)
            and isinstance(eos, (list, tuple)) and eos and all(type(x) is int and x >= 0 for x in eos)
            and type(count) is int and count == len(ids)
            and type(limit) is int and limit > 0 and count <= limit
            and type(inputs) is int and inputs > 0 and type(maximum) is int
            and limit <= maximum-inputs):
        return "INVALID_GENERATION_AUDIT"
    terminal = bool(ids) and ids[-1] in eos
    if (audit.get("terminal_eos_observed") is not terminal
            or audit.get("complete_generation") is not terminal
            or audit.get("length_limit_reached") is not (count >= limit)
            or any(x in eos for x in ids[:-1])):
        return "INVALID_GENERATION_AUDIT"
    return None if terminal else "INCOMPLETE_GENERATION"


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def parse_qwen_grounding(raw_output, width, height, *, mode, audit, terminal_special_tokens=(), expected_label=LABEL):
    """Parse complete native Qwen JSON after token-verified EOS.

    ``terminal_special_tokens`` are tokenizer-decoded EOS strings from the pinned
    checkpoint. Strip at most one matching suffix, never interior special tokens.
    The preserved raw_output always includes the original unmodified text.
    """
    mode = _request(mode, width, height)
    require(isinstance(expected_label, str) and bool(expected_label), "explicit expected target label required")
    if not isinstance(raw_output, str):
        raise TypeError("raw output must be text")
    require(isinstance(terminal_special_tokens, (tuple, list))
            and all(isinstance(x, str) and bool(x) for x in terminal_special_tokens),
            "explicit terminal special token strings required")
    base = dict(contract=QWEN_CONTRACT, mode=mode, raw_output=raw_output, width=width, height=height)
    reason = _generation_reason(audit)
    if reason:
        return GroundingReply(**base, admitted=False, reason=reason)
    text = raw_output.strip()
    for token in sorted(terminal_special_tokens, key=len, reverse=True):
        if text.endswith(token):
            text = text[:-len(token)].strip()
            break
    response_format = "whole-json"
    if text.startswith("```"):
        wrapper = re.fullmatch(r"```json\s*\n([\s\S]*?)\n```", text)
        if wrapper is None:
            return GroundingReply(**base, admitted=False, reason="INVALID_JSON_WRAPPER")
        text, response_format = wrapper[1], "whole-json-fence"
    base["response_format"] = response_format
    try:
        value = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, RecursionError):
        return GroundingReply(**base, admitted=False, reason="INVALID_JSON")
    if not isinstance(value, list):
        return GroundingReply(**base, admitted=False, reason="INVALID_JSON_SCHEMA")
    if not value:
        return GroundingReply(**base, admitted=False, reason="EXPLICIT_ABSTAIN")
    if len(value) != 1:
        return GroundingReply(**base, admitted=False, reason="GROUNDING_CARDINALITY")
    record, field = value[0], "bbox_2d" if mode == "BOX" else "point_2d"
    if not isinstance(record, dict) or set(record) != {"label", field} or record["label"] != expected_label:
        return GroundingReply(**base, admitted=False, reason="INVALID_JSON_SCHEMA")
    coords = record[field]
    if not isinstance(coords, list) or len(coords) != (4 if mode == "BOX" else 2):
        return GroundingReply(**base, admitted=False, reason="INVALID_COORDINATE_SHAPE")
    if any(type(x) not in (int, float) or not 0 <= x <= 1000 or not math.isfinite(x) for x in coords):
        return GroundingReply(**base, admitted=False, reason="INVALID_COORDINATE_RANGE")
    base["native_records"] = (freeze(record),)
    pixels = tuple(x/1000*(width if i % 2 == 0 else height) for i, x in enumerate(coords))
    if mode == "BOX":
        if coords[2] <= coords[0] or coords[3] <= coords[1]:
            return GroundingReply(**base, admitted=False, reason="DEGENERATE_BOX")
        return GroundingReply(**base, admitted=True, reason=None, ordered_boxes_xyxy_px=(pixels,))
    if pixels[0] >= width or pixels[1] >= height:
        return GroundingReply(**base, admitted=False, reason="POINT_OUT_OF_FRAME")
    return GroundingReply(**base, admitted=True, reason=None, point_xy_px=pixels,
                          sample_pixel_xy=tuple(math.floor(x) for x in pixels))


def parse_locateanything_grounding(raw_output, width, height, *, mode, audit):
    """Translate original native typed output; do not change its admission rules."""
    mode = _request(mode, width, height)
    typed = parse_semantic_reply(raw_output, width, height, mode=mode.lower(), audit=audit)
    # The original prompting wrapper rejects incomplete generation before the
    # typed parser. Preserve that first boundary in the common observation.
    incomplete = not audit.get("complete_generation") or not audit.get("terminal_eos_observed")
    return GroundingReply(contract=typed.contract, mode=mode, raw_output=raw_output, width=width,
        height=height, admitted=typed.admitted, reason="INCOMPLETE_GENERATION" if incomplete else typed.reason,
        ordered_boxes_xyxy_px=tuple(x.pixels for x in typed.selected) if typed.admitted and mode == "BOX" else (),
        point_xy_px=typed.selected[0].pixels if typed.admitted and mode == "POINT" else None,
        sample_pixel_xy=typed.selected[0].sample_pixel_xy if typed.admitted and mode == "POINT" else None,
        native_records=tuple(freeze(x) for x in typed.evidence()["atoms"]), response_format="locateanything-native")


def _build_observation(reply, *, request_id, source_identity, query, target_key,
                       frontend_id, model_identity, processor_identity, environment_identity,
                       audit, input_evidence, terminal_special_tokens=(), timing=None,
                       raw_output_ref=None, expected_label=LABEL, _crop_binding=None, _native_reply=None):
    """Bind a parser result to immutable capture and actual request receipts.

    This record is a local perception boundary, not a controller message. The
    caller must supply actual model/environment identities; no defaults invent
    unavailable provenance. Input evidence contains RGB/text/token receipts only.
    """
    for value in (request_id, query, target_key, frontend_id):
        require(isinstance(value, str) and bool(value), "nonempty request identity required")
    require(isinstance(reply, GroundingReply), "typed grounding reply required")
    require(reply.contract != QWEN_CONTRACT or target_key == expected_label, "Qwen target key differs from native label")
    require(source_identity["rgb_shape"] == [reply.height, reply.width, 3], "original image shape differs", "SOURCE_MISMATCH")
    input_rgb_hash = source_identity["rgb_sha256"] if _crop_binding is None else _crop_binding['crop_rgb_sha256']
    require(input_evidence.get("rgb_sha256") == input_rgb_hash
            and input_evidence.get("query") == query, "model input sensor/query differs", "SOURCE_MISMATCH")
    ids = input_evidence.get("input_token_ids")
    require(isinstance(ids, (list, tuple)) and bool(ids)
            and all(type(x) is int and x >= 0 for x in ids)
            and len(ids) == audit.get("input_token_count"), "actual input token evidence required")
    for identity in (model_identity, processor_identity, environment_identity):
        require(isinstance(identity, dict) and bool(identity), "actual model/processor/environment identity required")
    record = dict(contract=CONTRACT, request_id=request_id, mode=reply.mode, query=query,
        target_query_sha256=hashlib.sha256(query.encode()).hexdigest(), target_key=target_key,
        source_identity=source_identity, source_identity_sha256=content_hash(source_identity),
        frontend_id=frontend_id, adapter_revision=reply.contract, model_identity=model_identity,
        processor_identity=processor_identity, environment_identity=environment_identity,
        raw_output=reply.raw_output, raw_output_ref=raw_output_ref,
        raw_output_sha256=hashlib.sha256(reply.raw_output.encode()).hexdigest(),
        generation_audit=audit, input_evidence=input_evidence,
        complete_generation=audit.get("complete_generation"),
        terminal_eos_observed=audit.get("terminal_eos_observed"), token_budget=audit.get("effective_limit"),
        stop_reason=("EOS" if audit.get("terminal_eos_observed") else
                     "LENGTH_LIMIT" if audit.get("length_limit_reached") else "INCOMPLETE_GENERATION"),
        input_token_ids_sha256=content_hash(input_evidence.get("input_token_ids")),
        output_token_ids_sha256=content_hash(audit.get("actual_generated_token_ids")),
        terminal_special_tokens=list(terminal_special_tokens), native_coordinate_system=COORDINATES,
        typed=reply.evidence(), timing=timing, calibrated_confidence=None,
        evaluation_labels_used=False, semantic_identity_verified=False, for_execution=False)
    if expected_label != LABEL:
        record['expected_label'] = expected_label
    if _crop_binding is not None:
        record.update(contract=MAPPED_CONTRACT, crop_binding=_crop_binding,
            native_typed=_native_reply.evidence(), native_coordinate_system='normalized-0-1000-crop-image-xy')
    record["observation_sha256"] = content_hash(record)
    validate_grounding_observation(record)
    return record


def build_grounding_observation(reply, **kwargs):
    """Build original-image observation; optional expected_label binds its request."""
    return _build_observation(reply, **kwargs)


def _crop_roi(box, width, height):
    # The exact deterministic 15% expansion is condition metadata, not a tuned
    # geometry/tool threshold. It is never selected using downstream success.
    x0, y0, x1, y1 = box
    dx, dy = .15*(x1-x0), .15*(y1-y0)
    return [max(0, math.floor(x0-dx)), max(0, math.floor(y0-dy)),
            min(width, math.ceil(x1+dx)), min(height, math.ceil(y1+dy))]


def make_model_crop(view, coarse_observation):
    """One source-bound model BOX -> deterministic crop bytes and provenance.

    The coarse target is a distinct semantic search region, never drawer-front
    support. No annotations, POINT-conditioned selection, fallback or resizing.
    """
    from .surface_association import sensor_view_identity
    source = sensor_view_identity(view)
    coarse = validate_grounding_observation(coarse_observation, view=view)
    require(coarse_observation['contract'] == CONTRACT and coarse.mode == 'BOX'
            and coarse.admitted and len(coarse.ordered_boxes_xyxy_px) == 1,
            'one complete original-image coarse BOX required')
    require(coarse_observation['target_key'] != LABEL, 'coarse search target must be distinct from drawer-front support')
    box = list(coarse.ordered_boxes_xyxy_px[0])
    roi = _crop_roi(box, coarse.width, coarse.height)
    x0, y0, x1, y1 = roi
    require(x1 > x0 and y1 > y0, 'empty coarse model crop')
    crop = view['rgb'][y0:y1, x0:x1].copy()
    binding = dict(contract=CROP_CONTRACT, source_identity=source, source_identity_sha256=content_hash(source),
        coarse_observation=coarse_observation, coarse_observation_sha256=coarse_observation['observation_sha256'],
        coarse_box_ordinal=0, coarse_box_xyxy_px=box, expansion_fraction=.15, crop_xyxy_px=roi,
        crop_rgb_shape=list(crop.shape), crop_rgb_sha256=hashlib.sha256(crop.tobytes()).hexdigest(),
        resizing_before_processor=False, crop_is_search_region_only=True, evaluation_labels_used=False)
    binding['crop_binding_sha256'] = content_hash(binding)
    return crop, binding


def validate_model_crop(binding, *, view=None):
    """Verify native model origin and mapping; with RGB also check actual crop bytes."""
    require(binding['contract'] == CROP_CONTRACT and binding['crop_binding_sha256'] == content_hash(
        {k:v for k,v in binding.items() if k!='crop_binding_sha256'}), 'crop binding changed', 'SOURCE_MISMATCH')
    parent = binding['coarse_observation']
    require(parent['contract'] == CONTRACT and parent['target_key'] != LABEL,
            'original-image coarse semantic search required')
    coarse = validate_grounding_observation(parent, view=view)
    require(coarse.mode == 'BOX' and coarse.admitted and len(coarse.ordered_boxes_xyxy_px) == 1
            and binding['coarse_box_ordinal'] == 0, 'no multi-BOX crop winner allowed')
    box = list(coarse.ordered_boxes_xyxy_px[0])
    roi = _crop_roi(box, coarse.width, coarse.height)
    x0, y0, x1, y1 = roi
    require(binding['source_identity'] == parent['source_identity']
            and binding['source_identity_sha256'] == content_hash(parent['source_identity'])
            and binding['coarse_observation_sha256'] == parent['observation_sha256']
            and binding['coarse_box_xyxy_px'] == box and binding['crop_xyxy_px'] == roi
            and binding['expansion_fraction'] == .15
            and binding['crop_rgb_shape'] == [y1-y0, x1-x0, 3]
            and binding['resizing_before_processor'] is False
            and binding['crop_is_search_region_only'] is True
            and binding['evaluation_labels_used'] is False, 'crop source/rule differs', 'SOURCE_MISMATCH')
    if view is not None:
        crop = view['rgb'][y0:y1, x0:x1]
        require(hashlib.sha256(crop.tobytes()).hexdigest() == binding['crop_rgb_sha256'],
                'crop bytes differ from original image', 'SOURCE_MISMATCH')
    return roi


def _map_reply(reply, binding):
    x0, y0, x1, y1 = binding['crop_xyxy_px']
    require(reply.width == x1-x0 and reply.height == y1-y0, 'native crop dimensions differ', 'SOURCE_MISMATCH')
    h, w, _ = binding['source_identity']['rgb_shape']
    point = None if reply.point_xy_px is None else (reply.point_xy_px[0]+x0, reply.point_xy_px[1]+y0)
    boxes = tuple((b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0) for b in reply.ordered_boxes_xyxy_px)
    return replace(reply, width=w, height=h, ordered_boxes_xyxy_px=boxes, point_xy_px=point,
                   sample_pixel_xy=None if point is None else tuple(math.floor(x) for x in point))


def build_mapped_grounding_observation(reply, *, crop_binding, **kwargs):
    """Preserve native crop parsing while exposing mapped original-image pixels."""
    validate_model_crop(crop_binding)
    require(reply.contract == QWEN_CONTRACT, 'explicit Qwen crop parser required')
    require(kwargs['source_identity'] == crop_binding['source_identity'], 'crop parent source differs', 'SOURCE_MISMATCH')
    return _build_observation(_map_reply(reply,crop_binding), _crop_binding=crop_binding, _native_reply=reply, **kwargs)


def validate_grounding_observation(record, *, view=None):
    """Reparse raw native evidence; cached coordinates cannot bypass admission."""
    require(record["contract"] in {CONTRACT, MAPPED_CONTRACT} and record["observation_sha256"] == content_hash(
        {k: v for k, v in record.items() if k != "observation_sha256"}), "grounding record changed", "SOURCE_MISMATCH")
    require(record["evaluation_labels_used"] is False and record["for_execution"] is False
            and record["semantic_identity_verified"] is False and record["calibrated_confidence"] is None,
            "grounding evidence cannot assert verified identity or execution", "INFORMATION_BOUNDARY")
    typed, source = record["typed"], record["source_identity"]
    mapped = record['contract'] == MAPPED_CONTRACT
    if mapped:
        validate_model_crop(record['crop_binding'], view=view)
        require(record['crop_binding']['source_identity'] == source
                and record['adapter_revision'] == QWEN_CONTRACT, 'mapped native source differs', 'SOURCE_MISMATCH')
    if view is not None:
        from .surface_association import sensor_view_identity
        require(source == sensor_view_identity(view), 'grounding source image differs', 'SOURCE_MISMATCH')
    input_rgb_hash = record['crop_binding']['crop_rgb_sha256'] if mapped else source['rgb_sha256']
    require(record["raw_output_sha256"] == hashlib.sha256(record["raw_output"].encode()).hexdigest()
            and record["target_query_sha256"] == hashlib.sha256(record["query"].encode()).hexdigest()
            and record["source_identity_sha256"] == content_hash(source)
            and source["rgb_shape"] == [typed["height"], typed["width"], 3]
            and record["input_evidence"].get("rgb_sha256") == input_rgb_hash
            and record["input_evidence"].get("query") == record["query"], "grounding source/query differs", "SOURCE_MISMATCH")
    require(record['input_token_ids_sha256'] == content_hash(record['input_evidence'].get('input_token_ids'))
            and record['output_token_ids_sha256'] == content_hash(record['generation_audit'].get('actual_generated_token_ids'))
            and len(record['input_evidence']['input_token_ids']) == record['generation_audit']['input_token_count'],
            "generation token evidence differs", "SOURCE_MISMATCH")
    args = dict(mode=record["mode"], audit=record["generation_audit"])
    native = record['native_typed'] if mapped else typed
    if record["adapter_revision"] == QWEN_CONTRACT:
        expected_label = record.get('expected_label', LABEL)
        require(record['target_key'] == expected_label, 'Qwen target key differs from request label')
        reply = parse_qwen_grounding(record["raw_output"], native["width"], native["height"],
            **args, terminal_special_tokens=record["terminal_special_tokens"], expected_label=expected_label)
    else:
        from .semantic_output import CONTRACT as LA_CONTRACT
        require(record["adapter_revision"] == LA_CONTRACT, "unknown native parser")
        reply = parse_locateanything_grounding(record["raw_output"], typed["width"], typed["height"], **args)
    if mapped:
        require(content_hash(reply.evidence()) == content_hash(native), 'native crop parse differs', 'SOURCE_MISMATCH')
        reply = _map_reply(reply, record['crop_binding'])
    require(content_hash(reply.evidence()) == content_hash(typed), "typed coordinates differ from native output", "SOURCE_MISMATCH")
    return reply
