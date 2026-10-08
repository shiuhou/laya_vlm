"""Raw-RGB-only HO23 annotation packet; offline labels, never inference inputs.

Region/status semantics are the frozen rules/2 bytes. A distinct packet schema
states the new 23-frame population and independent-human self-attestations; it
never pretends this is the historical 50-frame packet or rules/3.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path, PurePosixPath

import numpy as np

from ..contracts import ProtocolError, canonical_json, require
from ..perception.evaluation_annotations import (
    ENTITIES, IMAGE_KEYS, _hash, _keys, _text, _validate_record, packet_identity,
)
from ..perception.recording import replay_frames
from .p1_annotation_packet import HTML

PACKET_SCHEMA = "p1-heldout-human-packet/1"
ANNOTATION_SCHEMA = "p1-heldout-human-annotations/1"
RULES_VERSION = "p1-rgb-annotation-rules/2"
RULES_SHA256 = "d595017579fd4acabe16c563b74de8486ca64e5ee9650c294d78b30d7048ecfe"
RULES_SOURCE = Path(__file__).resolve().parents[2] / "runs/p1/human-annotation-packet-v2-20261005/annotation_rules.md"
INIT_INDICES = tuple(range(27, 50))
CAMERA = "robot0_eye_in_hand"
SELECTION = "first_bundle_wrist_init27_through49_raw_rgb_only"
ATTESTATIONS = {"is_human", "independent_of_model_outputs", "independent_of_ai_drafts", "raw_rgb_only"}
SCOPE_NOTICE = (
    "Held-out packet scope: annotate all 23 wrist images, init27–49. The archived rules/2 "
    "below are preserved byte-for-byte for region, visibility and polygon semantics. "
    "Their historical 50-image population and project-primary role do not describe this packet: "
    "this distinct held-out schema requires 23 images and an independent human annotator, "
    "with explicit no-model-output/no-AI-draft attestations. Independence is self-attested, "
    "not verified by software. Do not change region semantics or consult model results. "
    "Fixed-reference labels retain the same rules but are not scored in this BOX experiment."
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_manifest(manifest):
    _keys(manifest, {"schema", "dataset_id", "source_run_manifest_sha256", "selection_rule",
                    "expected_image_count", "images", "rules_version", "rules_sha256", "rules_path",
                    "scope_notice"}, "heldout packet")
    require(manifest["schema"] == PACKET_SCHEMA, "heldout packet schema mismatch", "ANNOTATION_SCHEMA")
    require(manifest["rules_version"] == RULES_VERSION and manifest["rules_sha256"] == RULES_SHA256
            and manifest["rules_path"] == "annotation_rules.md", "frozen rules/2 mismatch", "ANNOTATION_RULES")
    require(manifest["scope_notice"] == SCOPE_NOTICE, "heldout annotation scope changed", "ANNOTATION_RULES")
    _hash(manifest["source_run_manifest_sha256"], "capture manifest hash")
    require(manifest["dataset_id"] == packet_identity(manifest), "packet hash mismatch", "ANNOTATION_BINDING")
    require(manifest["selection_rule"] == SELECTION and type(manifest["expected_image_count"]) is int
            and manifest["expected_image_count"] == 23 and isinstance(manifest["images"], list)
            and len(manifest["images"]) == 23, "exact HO23 population required", "ANNOTATION_COVERAGE")
    images, identities, pixels, paths = {}, set(), set(), set()
    for init, row in zip(INIT_INDICES, manifest["images"]):
        _keys(row, IMAGE_KEYS, "heldout image")
        require(type(row["init_index"]) is int and row["init_index"] == init and row["camera_id"] == CAMERA,
                "canonical init27..49 wrist order required", "ANNOTATION_COVERAGE")
        for key in ("image_id", "frame_id", "source_frame_id", "episode_id", "camera_id"):
            _text(row[key], key)
        for key in ("rgb_blob_sha256", "rgb_pixel_sha256", "png_sha256"):
            _hash(row[key], key)
        require(type(row["width"]) is int and type(row["height"]) is int
                and min(row["width"], row["height"]) > 0, "invalid dimensions", "ANNOTATION_BINDING")
        path = PurePosixPath(row["image_path"])
        require(not path.is_absolute() and len(path.parts) == 2 and path.parts[0] == "images"
                and path.suffix == ".png", "raw local PNG required", "ANNOTATION_BINDING")
        require(row["image_id"] == row["frame_id"] and row["image_id"] not in images
                and row["frame_id"] not in identities and row["rgb_pixel_sha256"] not in pixels
                and row["image_path"] not in paths, "duplicate/mismatched heldout identity", "ANNOTATION_COVERAGE")
        images[row["image_id"]] = row
        identities.add(row["frame_id"])
        pixels.add(row["rgb_pixel_sha256"])
        paths.add(row["image_path"])
    return images


def load_packet(packet_root):
    from PIL import Image

    root = Path(packet_root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    images = validate_manifest(manifest)
    require(_sha((root / "annotation_rules.md").read_bytes()) == RULES_SHA256,
            "frozen rules bytes changed", "ANNOTATION_RULES")
    for entry in images.values():
        path = (root / entry["image_path"]).resolve()
        require(path.is_relative_to(root), "image escapes packet", "ANNOTATION_BINDING")
        require(_sha(path.read_bytes()) == entry["png_sha256"], "PNG hash mismatch", "ANNOTATION_BINDING")
        with Image.open(path) as image:
            require(image.mode == "RGB" and image.size == (entry["width"], entry["height"]),
                    "PNG dimensions/mode mismatch", "ANNOTATION_BINDING")
            require(_sha(np.asarray(image).tobytes()) == entry["rgb_pixel_sha256"],
                    "RGB pixel hash mismatch", "ANNOTATION_BINDING")
    return manifest


def build_packet(recordings_root, output):
    from PIL import Image

    root, out = Path(recordings_root), Path(output)
    capture_bytes = (root / "capture/manifest.json").read_bytes()
    json.loads(capture_bytes)  # Reject corrupt provenance before creating a packet.
    rules = RULES_SOURCE.read_bytes()
    require(_sha(rules) == RULES_SHA256, "frozen rules/2 source mismatch", "ANNOTATION_RULES")
    out.mkdir(parents=True, exist_ok=False)
    (out / "images").mkdir()
    (out / "annotation_rules.md").write_bytes(rules)
    images = []
    for init in INIT_INDICES:
        bundles = list(replay_frames(root / f"init-{init:03d}"))
        require(bool(bundles), "missing heldout raw frame", "ANNOTATION_COVERAGE")
        env, views = bundles[0]
        wrist = [view for view in views if view["camera_id"] == CAMERA]
        require(len(wrist) == 1, "first bundle must contain one wrist view", "ANNOTATION_COVERAGE")
        view = wrist[0]
        refs = {entry["camera_id"]: entry["rgb_blob"] for entry in env.payload["views"]}
        rgb = view["rgb"]
        relative = f"images/{init:03d}.png"
        Image.fromarray(rgb).save(out / relative)
        h, w = rgb.shape[:2]
        images.append(dict(image_id=view["canonical_frame_id"], frame_id=view["canonical_frame_id"],
            source_frame_id=view["frame_id"], episode_id=env.episode_id, init_index=init,
            camera_id=CAMERA, width=w, height=h, rgb_blob_sha256=refs[CAMERA]["sha256"],
            rgb_pixel_sha256=_sha(rgb.tobytes()), png_sha256=_sha((out / relative).read_bytes()),
            image_path=relative))
    manifest = dict(schema=PACKET_SCHEMA, dataset_id=None, source_run_manifest_sha256=_sha(capture_bytes),
        selection_rule=SELECTION, expected_image_count=23, images=images, rules_version=RULES_VERSION,
        rules_sha256=RULES_SHA256, rules_path="annotation_rules.md", scope_notice=SCOPE_NOTICE)
    manifest["dataset_id"] = packet_identity(manifest)
    validate_manifest(manifest)
    (out / "manifest.json").write_text(canonical_json(manifest) + "\n")
    page = HTML.replace("p1-human-annotations/3", ANNOTATION_SCHEMA)
    page = page.replace("__PACKET__", canonical_json(manifest).replace("<", "\\u003c"))
    page = page.replace("__RULES_TEXT__", html.escape(rules.decode()))
    page = page.replace('<section style=', '<p><strong>' + html.escape(SCOPE_NOTICE) + '</strong></p><section style=', 1)
    (out / "index.html").write_text(page)
    empty = dict(schema=ANNOTATION_SCHEMA, dataset_id=manifest["dataset_id"], annotator_id=None,
        annotator_role="independent_human_annotator", rules_version=RULES_VERSION, rules_sha256=RULES_SHA256,
        attestations={key: False for key in sorted(ATTESTATIONS)}, exported_at_utc=None, annotations=[])
    (out / "annotations.empty.json").write_text(canonical_json(empty) + "\n")
    (out / "README.txt").write_text(SCOPE_NOTICE + "\n\nOpen index.html locally. No server or network needed.\n"
        "Only raw RGB is supplied; zero labels or model predictions are supplied.\n"
        "Complete both entities on every image, then export annotations.complete.json.\n"
        "Empty/partial exports cannot enter evaluation. Labels never enter runtime.\n"
        "Validate: python -m embodied_runtime.experiments.p1_heldout_annotation_packet validate "
        "--packet PACKET --annotations annotations.complete.json\n")
    return dict(output=str(out), dataset_id=manifest["dataset_id"], image_count=23, completed_annotations=0,
                label_status="AWAITING_INDEPENDENT_HUMAN_ANNOTATION", rules_version=RULES_VERSION,
                rules_sha256=RULES_SHA256)


def validate_complete(annotation_path, packet_root):
    manifest = load_packet(packet_root)
    images = validate_manifest(manifest)
    annotation_bytes = Path(annotation_path).read_bytes()
    value = json.loads(annotation_bytes)
    _keys(value, {"schema", "dataset_id", "annotator_id", "annotator_role", "rules_version", "rules_sha256",
                  "attestations", "exported_at_utc", "annotations"}, "heldout annotation export")
    require(value["schema"] == ANNOTATION_SCHEMA and value["dataset_id"] == manifest["dataset_id"],
            "annotation dataset/schema mismatch", "ANNOTATION_BINDING")
    require(value["rules_version"] == RULES_VERSION and value["rules_sha256"] == RULES_SHA256,
            "annotation rules/2 mismatch", "ANNOTATION_RULES")
    require(value["annotator_role"] == "independent_human_annotator",
            "independent human role required", "ANNOTATOR_ATTESTATION")
    _text(value["annotator_id"], "human annotator identity")
    require(value["annotator_id"].strip().lower() not in
            {"agent", "assistant", "codex", "astra", "chatgpt", "qwen", "laya", "anonymous"},
            "distinct human identity required", "ANNOTATOR_ATTESTATION")
    _keys(value["attestations"], ATTESTATIONS, "attestations")
    require(all(item is True for item in value["attestations"].values()),
            "explicit human, independence, no-AI-draft and raw-RGB attestations required", "ANNOTATOR_ATTESTATION")
    try:
        stamp = datetime.fromisoformat(value["exported_at_utc"].replace("Z", "+00:00"))
        require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "UTC export required")
    except (ValueError, AttributeError, TypeError) as exc:
        raise ProtocolError("ANNOTATION_SCHEMA", "invalid export timestamp") from exc
    require(isinstance(value["annotations"], list), "annotation records required", "ANNOTATION_SCHEMA")
    seen, counts = set(), {entity: Counter() for entity in ENTITIES}
    for row in value["annotations"]:
        _validate_record(row, images)
        require(row["image_id"] not in seen, "duplicate annotation", "ANNOTATION_COVERAGE")
        seen.add(row["image_id"])
        for entity, label in row["entities"].items():
            counts[entity][label["status"]] += 1
    require(seen == set(images), "all 23 heldout annotations required", "ANNOTATION_COVERAGE")
    return dict(dataset_id=manifest["dataset_id"], annotated_images=23, expected_images=23, complete=True,
        annotation_file_sha256=_sha(annotation_bytes), annotator_id=value["annotator_id"],
        rules_version=RULES_VERSION, rules_sha256=RULES_SHA256,
        visibility_counts={key: dict(count) for key, count in counts.items()}, evaluation_only=True,
        human_identity_and_independence="self_attested_not_independently_verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--recordings-root", required=True)
    build.add_argument("--output", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--packet", required=True)
    validate.add_argument("--annotations", required=True)
    args = parser.parse_args()
    result = (build_packet(args.recordings_root, args.output) if args.command == "build"
              else validate_complete(args.annotations, args.packet))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
