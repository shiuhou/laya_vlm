"""Raw-only temporal evaluation packet; never a tracker seed or policy input.

Reuses the blank annotation UI, but owns a distinct temporal schema rather than
pretending multiple frames are the static 50-view independent dataset. The full
recording remains authoritative; sampled PNGs alone cannot certify continuity.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path
import subprocess

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.recording import replay_frames
from .p1_annotation_packet import HTML


def build_packet(recordings_root, output, *, samples_per_case=8):
    from PIL import Image

    require(type(samples_per_case) is int and samples_per_case >= 3, "at least pre/boundary/post samples")
    root, out = Path(recordings_root), Path(output)
    # The API deliberately accepts only raw recording roots. No model result,
    # candidate, annotation, track or evaluator-truth input is accepted.
    cases = sorted(root.glob("T[0-9][0-9]"))
    require(bool(cases), "no raw temporal cases")
    out.mkdir(parents=True, exist_ok=False)
    (out / "images").mkdir()
    (out / "videos").mkdir()
    rules = (Path(__file__).resolve().parents[2] / "docs/p1-annotation-rules.md").read_bytes()
    (out / "annotation_rules.md").write_bytes(rules)
    images, recordings, videos = [], [], []
    for case in cases:
        frames_root = case / "frames"
        bundles = list(replay_frames(frames_root))
        require(bool(bundles), "empty temporal recording")
        chosen = sorted(set(np.linspace(0, len(bundles) - 1, min(samples_per_case, len(bundles)), dtype=int)))
        recordings.append(dict(case_id=case.name, frames_sha256=hashlib.sha256((frames_root / "frames.jsonl").read_bytes()).hexdigest(),
                               raw_recording_uri=str(frames_root.resolve()), bundles=len(bundles), selected_bundle_indices=chosen))
        for camera in [view["camera_id"] for view in bundles[0][1]]:
            all_views = [next(view for view in bundle if view["camera_id"] == camera) for _, bundle in bundles]
            h, w = all_views[0]["rgb"].shape[:2]
            gaps = np.diff([view["capture_sim_time_s"] for view in all_views])
            positive = gaps[gaps > 0]
            fps = 1 / float(np.median(positive)) if len(positive) else 20.0
            relative = f"videos/{case.name}-{camera}.mp4"
            process = subprocess.Popen(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264",
                "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(out / relative)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for view in all_views:
                    process.stdin.write(np.ascontiguousarray(view["rgb"]).tobytes())
                process.stdin.close()
                error = process.stderr.read().decode(errors="replace")
                require(process.wait() == 0, f"raw-only video export failed: {error}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            videos.append(dict(case_id=case.name, camera_id=camera, path=relative, frames=len(all_views),
                display_fps=fps, display_clock="median_sim_capture_gap_not_walltime",
                source_frame_ids=[view["canonical_frame_id"] for view in all_views],
                capture_sim_time_s=[view["capture_sim_time_s"] for view in all_views],
                sha256=hashlib.sha256((out / relative).read_bytes()).hexdigest(), overlays=False))
        for index in chosen:
            env, views = bundles[index]
            refs = {entry["camera_id"]: entry["rgb_blob"] for entry in env.payload["views"]}
            for view in views:
                path = f"images/{len(images):04d}.png"
                Image.fromarray(view["rgb"]).save(out / path)
                h, w = view["rgb"].shape[:2]
                images.append(dict(image_id=view["canonical_frame_id"], frame_id=view["canonical_frame_id"],
                    source_frame_id=view["frame_id"], episode_id=env.episode_id, case_id=case.name,
                    bundle_index=index, camera_id=view["camera_id"], width=w, height=h,
                    rgb_blob_sha256=refs[view["camera_id"]]["sha256"],
                    rgb_pixel_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest(),
                    png_sha256=hashlib.sha256((out / path).read_bytes()).hexdigest(), image_path=path))
    manifest = dict(schema="p1-temporal-human-packet/1", dataset_id=None, expected_image_count=len(images),
        rules_version="p1-rgb-annotation-rules/3", rules_sha256=hashlib.sha256(rules).hexdigest(),
        selection_rule="uniform_source_bundle_indices_each_camera_raw_rgb_only", samples_per_case=samples_per_case,
        images=images, recordings=recordings, videos=videos, completed_annotations=0,
        lineage_review_status="AWAITING_HUMAN_FULL_RAW_SEQUENCE_REVIEW",
        sampling_does_not_certify_continuous_tracking=True, model_outputs_shown=False,
        evaluator_truth_shown=False, runtime_may_read_annotations=False)
    manifest["dataset_id"] = content_hash({k: v for k, v in manifest.items() if k != "dataset_id"})
    (out / "manifest.json").write_text(canonical_json(manifest) + "\n")
    page = HTML.replace("__PACKET__", canonical_json(manifest).replace("<", "\\u003c"))
    page = page.replace("__RULES_TEXT__", html.escape(rules.decode()))
    page = page.replace("p1-human-annotations/3", "p1-temporal-human-annotations/1")
    links = "<section><h2>Full original RGB sequences (no overlays)</h2>" + "".join(
        f'<p>{html.escape(v["case_id"])} / {html.escape(v["camera_id"])}<br>'
        f'<video controls preload="none" width="384" src="{html.escape(v["path"])}"></video></p>' for v in videos) + "</section>"
    page = page.replace("</body>", links + "</body>")
    (out / "index.html").write_text(page)
    (out / "README.txt").write_text(
        "Open index.html: original RGB only, zero supplied labels. Label drawer-front and fixed reference.\n"
        "This temporal packet has a distinct schema and must not be loaded as the static 50-frame evaluation.\n"
        "Sampled polygons cannot certify continuity. Inspect full raw recordings for event coverage, identity continuity,\n"
        "occlusion/reappearance and lineage breaks; no model ROI or algorithm overlay may be shown for annotation.\n"
        "Raw recording paths and hashes are preserved in manifest.json. No automatic interpolation of labels.\n"
        "Human labels are evaluation-only, never a policy/tracker seed.\n")
    return dict(output=str(out), images=len(images), cases=len(cases), completed_annotations=0,
                human_sequence_review_required=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recordings-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples-per-case", type=int, default=8)
    args = parser.parse_args()
    print(canonical_json(build_packet(args.recordings_root, args.output, samples_per_case=args.samples_per_case)))


if __name__ == "__main__":
    main()
