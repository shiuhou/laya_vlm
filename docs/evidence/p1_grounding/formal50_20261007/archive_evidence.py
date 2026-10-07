"""Package completed evidence without altering any sealed generation stage.

Run from repository root. No inference, labels-to-policy, or geometry execution.
Weights/venv/wheels remain external dependencies identified by registration.
"""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path("runs/p1/formal50-native-masks-20261007")
EXPORT = Path("docs/evidence/p1_grounding/formal50_20261007")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")


def archive(path, files, *, verify_existing=False):
    files = sorted(set(Path(p) for p in files))
    # tarfile strips a leading slash even for an explicit arcname. Keep the
    # verifier/index in that same safe member-name convention, including the
    # recorded absolute preparation-receipt aliases. Original bytes unchanged.
    manifest = {str(p).lstrip("/"): sha(p) for p in files}
    # Exclusive archive output and deterministic gzip header, original contents.
    if not verify_existing:
        with Path(path).open("xb") as stream:
            with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0, compresslevel=6) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as tar:
                    for p in files:
                        tar.add(p, arcname=str(p).lstrip("/"), recursive=False)
    with tarfile.open(path, "r:gz") as tar:
        names = [m.name for m in tar.getmembers()]
        assert names == list(manifest)
        for member in tar.getmembers():
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == manifest[member.name]
    return dict(path=str(path), sha256=sha(path), size_bytes=Path(path).stat().st_size,
                member_count=len(files), member_sha256=manifest, every_member_verified=True)


def main():
    registration = json.loads((ROOT/"registration.json").read_text())
    entry = registration["entry"]
    local = [p for p in ROOT.rglob("*") if p.is_file()]
    # Compact Git export contains complete JSON metrics/points/seals and all
    # review images, but authentic raw native arrays are in the full companion.
    compact = [p for p in local if p.suffix != ".npz"]
    verify_existing = sys.argv[1:] == ["--verify-existing"]
    assert sys.argv[1:] in ([], ["--verify-existing"])
    metadata = archive(EXPORT/"metadata-evidence.tar.gz", compact, verify_existing=verify_existing)
    source_root = Path(entry["source_manifest_path"]).parent
    packet_root = Path(entry["annotation_packet_manifest_path"]).parent
    box_root = Path(entry["sealed100_BOX_path"])
    sources = [p for root in (source_root, packet_root) for p in root.rglob("*") if p.is_file()]
    sources += [box_root/f"call-{i:03d}/prediction.json" for i in range(100)]
    sources += [box_root/"preregistration.json", box_root/"predictions-sealed.json"]
    sources += [Path(entry["annotation_path"]), Path(entry["annotation_seal_path"])]
    # Include source snapshots referenced by the prospective registration;
    # code remains additionally reproducible from its exact execution commit.
    sources += [Path(p).relative_to(Path.cwd()) for p in registration["source_files_sha256"]]
    assets = registration["environment_receipt"]
    prep = Path(assets["preparation_seal_path"]).parent
    sources += [p for p in prep.rglob("*") if p.is_file() and p.suffix in {".json", ".txt", ".lock"}]
    full = archive(ROOT.with_name(ROOT.name+"-full-evidence.tar.gz"), local+sources,
                   verify_existing=verify_existing)
    write(EXPORT/"artifact-index.json", dict(schema="p1-formal50-artifacts/1",
        execution_commit=registration["code"]["commit"], native_corpus_root=str(ROOT),
        metadata_archive=metadata, full_raw_companion_archive=full,
        raw_native_masks_in_git_archive=False, raw_native_masks_in_companion_archive=True,
        stage_seals={stage:sha(ROOT/stage/"sealed.json") for stage in ("masks", "geometry", "scoring", "review", "diagnostics")},
        external_model_dependencies=dict(SAM_source_revision=entry["SAM_source_revision"],
            SAM_checkpoint_sha256=entry["SAM_checkpoint_sha256"], dependency_lock_sha256=assets["dependency_lock_sha256"]),
        weights_venv_and_wheels_archived=False, original_evidence_overwritten=False,
        packaging_verification_continuation=verify_existing))
    print(json.dumps({"metadata_bytes":metadata["size_bytes"],"full_bytes":full["size_bytes"],
                      "metadata_members":metadata["member_count"],"full_members":full["member_count"]}))


if __name__ == "__main__":
    main()
