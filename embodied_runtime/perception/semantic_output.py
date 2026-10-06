"""Versioned native grounding syntax and request-specific typed admission.

Complete reply parsing is independent of geometry. Auxiliary atoms survive as
raw evidence, never as another channel's ROI/anchor. No calibrated confidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import re
from typing import Literal

CONTRACT = "p1-semantic-output/typed-v1"
ATOM = re.compile(r"<box>([^<>]*(?:<\d+>[^<>]*)*)</box>")
REFERENCE = re.compile(r"<ref>([^<>]+)</ref>")
COORDS = re.compile(r"(?:<\d+>){2}(?:(?:<\d+>){2})?")
EOS = "<|im_end|>"


@dataclass(frozen=True)
class GroundingAtom:
    kind: Literal["POINT", "BOX", "NONE", "INVALID"]
    ordinal: int
    raw_span: tuple[int, int]
    raw_text: str
    normalized: tuple[int, ...] | None
    pixels: tuple[float, ...] | None
    sample_pixel_xy: tuple[int, int] | None = None


@dataclass(frozen=True)
class SemanticReply:
    contract: str
    mode: Literal["point", "box"]
    raw_output: str
    raw_utf8_sha256: str
    width: int
    height: int
    reference: str | None
    atoms: tuple[GroundingAtom, ...]
    errors: tuple[str, ...]
    admitted: bool
    reason: str | None
    selected_ordinals: tuple[int, ...]
    auxiliary_ordinals: tuple[int, ...]
    calibrated_confidence: None = None
    provenance: str = "learned estimate"
    semantic_identity_verified: bool = False
    for_execution: bool = False

    def evidence(self):
        return asdict(self)

    @property
    def selected(self):
        return tuple(self.atoms[i] for i in self.selected_ordinals)


def _complete_audit(audit):
    ids = audit.get("actual_generated_token_ids")
    count, limit = audit.get("actual_generated_token_count"), audit.get("effective_limit")
    input_count, model_max = audit.get("input_token_count"), audit.get("model_max_length")
    eos_id = audit.get("eos_token_id")
    return (isinstance(ids, list) and bool(ids) and all(type(x) is int for x in ids)
            and type(count) is int and count == len(ids)
            and type(limit) is int and 0 < count <= limit
            and type(input_count) is int and input_count > 0
            and type(model_max) is int and limit <= model_max-input_count
            and type(eos_id) is int and ids[-1] == eos_id and eos_id not in ids[:-1]
            and audit.get("terminal_eos_observed") is True
            and audit.get("complete_generation") is True
            and audit.get("length_limit_reached") is (count >= limit))


def parse_semantic_reply(raw, width, height, *, mode, audit):
    """Parse the whole sealed reply; no prefix extraction, repair or fallback."""
    if mode not in {"point", "box"} or type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("explicit POINT/BOX mode and positive image dimensions required")
    if not isinstance(raw, str):
        raise TypeError("raw reply must be text")
    atoms, errors, reference = [], [], None
    pos = len(raw)-len(raw.lstrip())
    ref = REFERENCE.match(raw, pos)
    if ref:
        reference = ref[1]
        pos = ref.end()
    while pos < len(raw):
        pos += len(raw[pos:])-len(raw[pos:].lstrip())
        if raw[pos:] == EOS:
            pos = len(raw)
            break
        atom = ATOM.match(raw, pos)
        if atom is None:
            errors.append("UNRECOGNIZED_OR_UNBALANCED_SYNTAX")
            break
        body = atom[1].strip()
        kind, native, pixels, sampled = "INVALID", None, None, None
        if body == "none":
            kind = "NONE"
        elif COORDS.fullmatch(body):
            tokens = [x.lstrip("0") or "0" for x in re.findall(r"<(\d+)>", body)]
            kind = "POINT" if len(tokens) == 2 else "BOX"
            # Reject unbounded numeric text before int/float conversion; retain
            # its raw atom instead of overflowing or accepting a valid prefix.
            if any(len(x) > 4 or (len(x) == 4 and x > "1000") for x in tokens):
                errors.append(f"COORDINATE_OUT_OF_RANGE:{len(atoms)}")
            else:
                native = tuple(int(x) for x in tokens)
                pixels = tuple(x/1000*(width if i % 2 == 0 else height) for i, x in enumerate(native))
                if kind == "POINT":
                    if pixels[0] >= width or pixels[1] >= height:
                        errors.append(f"POINT_OUT_OF_FRAME:{len(atoms)}")
                    else:
                        sampled = (math.floor(pixels[0]), math.floor(pixels[1]))
                elif native[2] <= native[0] or native[3] <= native[1]:
                    errors.append(f"DEGENERATE_BOX:{len(atoms)}")
        else:
            errors.append(f"MALFORMED_ATOM:{len(atoms)}")
        atoms.append(GroundingAtom(kind, len(atoms), atom.span(), atom[0], native, pixels, sampled))
        pos = atom.end()
    if not raw.endswith(EOS):
        errors.append("MISSING_TERMINAL_TEXT_EOS")
    if not _complete_audit(audit):
        errors.append("INCOMPLETE_OR_INCONSISTENT_GENERATION_AUDIT")
    if any(a.kind == "NONE" for a in atoms) and len(atoms) != 1:
        errors.append("CONTRADICTORY_NONE")
    requested = "POINT" if mode == "point" else "BOX"
    selected = tuple(a.ordinal for a in atoms if a.kind == requested)
    auxiliary = tuple(a.ordinal for a in atoms if a.kind not in {requested, "NONE", "INVALID"})
    if errors:
        reason = "INVALID_COMPLETE_REPLY"
    elif len(atoms) == 1 and atoms[0].kind == "NONE":
        reason = "EXPLICIT_NONE"
    elif (mode == "point" and len(selected) != 1) or not selected:
        reason = "POINT_CARDINALITY" if mode == "point" else "NO_BOX"
    else:
        reason = None
    return SemanticReply(CONTRACT, mode, raw, hashlib.sha256(raw.encode()).hexdigest(), width, height,
                         reference, tuple(atoms), tuple(errors), reason is None, reason, selected, auxiliary)
