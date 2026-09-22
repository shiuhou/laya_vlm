"""Read-only, model-free inspection of one recorded State-Gap decision boundary.

Shows state values/provenance, shared versus natural candidates, and raw model
outputs. Optional evaluator evidence is a separate diagnostic panel, never an
effect input. This does not certify a reference policy or attribute disagreement
to perception. No simulator/model loading, report files, or evidence mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .equivalence import paired_inputs
from .records import load_records
from .reference_quality import local_reference
from .summarize_equivalence import analyze_equivalence


def _path(path):
    path = Path(path)
    return path / "episodes.jsonl" if path.is_dir() else path


def _index(pair):
    return {"pair_id": pair["pair_id"], **{k: pair["physical"].get(k) for k in (
        "task", "init_state_id", "seed", "environment_step", "variant", "sim_time", "physical_state_id")}}


def _encoding_complete(data):
    audit = data.get("input_encoding") or {}
    questions = audit.get("questions", {})
    flags = [q.get(k) for q in questions.values()
             for k in ("state_truncated", "heading_truncated", "options_truncated")]
    complete = bool(flags) and all(type(flag) is bool for flag in flags)
    if ((audit.get("truncated") is False and any(flag is True for flag in flags)) or
            (complete and type(audit.get("truncated")) is bool and audit["truncated"] != any(flags))):
        raise ValueError("contradictory aggregate/per-question clipping audit")
    return audit.get("available") is True and complete and audit.get("truncated") is False


def _inference_config(data):
    audit = data.get("input_encoding") or {}
    values = [audit.get(k) for k in ("actual_device", "actual_dtype")]
    return None if any(v in (None, "unknown") for v in values) else tuple(values)


def _evaluator_panel(path, pair):
    rows, diagnostics = load_records(_path(path))
    if not any(r["kind"] == "termination" for r in rows):
        diagnostics.append({"category": "run_incomplete", "detail": "no terminal collection record"})
    matched = [r["data"] for r in rows if r["kind"] == "paired_state" and r["data"]["pair_id"] == pair["pair_id"]]
    if len(matched) != 1 or matched[0] != pair:
        raise ValueError("collection must contain the identical paired record exactly once")
    pid = pair["physical"]["physical_state_id"]
    probes, evaluators = {}, []
    for row in rows:
        data = row["data"]
        if data.get("physical_state_id") != pid or row["kind"] not in ("evaluator_probe", "reference_evaluator"):
            continue
        if data.get("not_supplied_to_model") is not True:
            raise ValueError("evaluator evidence lacks diagnostic-only boundary")
        if row["kind"] == "reference_evaluator":
            evaluators.append(data)
        else:
            if data["token"] in probes:
                raise ValueError("duplicate evaluator probe")
            probes[data["token"]] = data
    if len(evaluators) > 1:
        raise ValueError("duplicate reference evaluator")
    expected = paired_inputs(pair)[0].allowed()
    if set(probes) - expected:
        raise ValueError("evaluator candidate mismatch")
    panel = {"scope": "privileged local diagnostics, NOT model input or expert truth",
             "physical_state_id": pid, "diagnostics": diagnostics,
             "missing_probes": sorted(expected - set(probes)), "raw_probes": probes,
             "status": "incomplete", "local_reference": None,
             "identical_command_and_endpoint_groups": []}
    if not evaluators or set(probes) != expected:
        return panel
    evaluator = evaluators[0]
    source_features = pair["physical"].get("features")
    if source_features is not None and evaluator["before"] != source_features:
        raise ValueError("evaluator before-state differs from paired physical features")
    recomputed = local_reference(evaluator["before"], probes)
    if recomputed != {k: evaluator[k] for k in recomputed}:
        raise ValueError("cached evaluator disagrees with raw probes")
    # Exact equality is deliberately conservative; no general action equivalence
    # is inferred, and missing telemetry must not form an apparent alias group.
    groups = {}
    for token, probe in probes.items():
        execution = probe.get("execution", {})
        commands, endpoint = execution.get("low_level_commands"), probe.get("sim_state_after")
        if commands and endpoint:
            key = json.dumps([commands, endpoint], sort_keys=True, allow_nan=False)
            groups.setdefault(key, []).append(token)
    panel.update(status="complete", before=evaluator["before"], local_reference=recomputed,
                 source_features_match=None if source_features is None else True,
                 source_restore_max_error=evaluator.get("source_restore_max_error"),
                 stop_replay_max_error=evaluator.get("stop_replay_max_error"),
                 identical_command_and_endpoint_groups=[sorted(g) for g in groups.values() if len(g) > 1])
    return panel


def inspect_pair(path, *, pair_id=None, step=None, init_state_id=None, variant=None,
                 list_only=False, collection=None, show_input=False):
    """Validate the entire log, then select exactly one boundary (or list it).

    Prefixes are allowed only when unambiguous. Model payloads are reconstructed
    using the recorded presentation version and validated against recorded hashes;
    actual consumed tokens, when observed, remain in ``input_encoding``.
    """
    rows, diagnostics = load_records(_path(path))
    analysis = analyze_equivalence(rows, diagnostics)
    for row in rows:
        if row["kind"] == "equivalence_decision":
            _encoding_complete(row["data"])
    pairs = [r["data"] for r in rows if r["kind"] == "paired_state"]
    pairs = [p for p in pairs if (
        (pair_id is None or p["pair_id"].startswith(pair_id)) and
        (step is None or p["physical"].get("environment_step") == step) and
        (init_state_id is None or p["physical"].get("init_state_id") == init_state_id) and
        (variant is None or p["physical"].get("variant") == variant))]
    if list_only:
        return {"pairs": [_index(p) for p in pairs], "diagnostics": analysis["diagnostics"]}
    if len(pairs) != 1:
        raise ValueError(f"selection matched {len(pairs)} pairs; use --list and select an unambiguous pair")
    pair = pairs[0]
    inputs = paired_inputs(pair)
    if inputs[0].state.meta.get("oracle_source") != pair["physical"]["physical_state_id"]:
        raise ValueError("oracle source does not match physical state")
    metadata = next(p for p in analysis["pairs"] if p["pair_id"] == pair["pair_id"])
    decisions = [r["data"] for r in rows if r["kind"] == "equivalence_decision" and r["data"]["pair_id"] == pair["pair_id"]]
    comparisons = [r.copy() for r in analysis["comparisons"] if r["pair_id"] == pair["pair_id"]]
    warnings = ["Field comparison status checks presence/referent, not decision sufficiency or equal validity semantics.",
                "Null patterns may identify branches even when source labels are absent from model input."]
    for row in comparisons:
        observations = [d for d in decisions if d["provider"] == row["provider"] and d["repeat"] == row["repeat"]]
        row["presentation_agreement"] = None if row["status"] != "complete" else (
            row["oracle_presentation_version"] == row["perceptual_presentation_version"])
        configs = [_inference_config(d) for d in observations]
        row["recorded_device_dtype_agreement"] = (None if row["provider"] != "LayaProvider" or
            len(configs) != 2 or None in configs else len(set(configs)) == 1)
        row["full_input_comparison_valid"] = (
            row["status"] == "complete" and row["oracle_choice_allowed"] and row["perceptual_choice_allowed"] and
            row["presentation_agreement"] is True and
            all(row[f"{branch}_input_truncation_status"] != "truncated" for branch in ("oracle", "perceptual")) and
            (row["provider"] != "LayaProvider" or all(_encoding_complete(d) for d in observations) and all(
                row[f"{branch}_input_truncation_status"] == "not_truncated" and row[f"{branch}_effective_input_id"] is not None
                for branch in ("oracle", "perceptual"))))
    if any(not r["full_input_comparison_valid"] for r in comparisons):
        warnings.append("Some raw comparisons are incomplete/invalid/unaudited or use different presentations; their metrics do NOT establish full-input fidelity.")
    if not decisions:
        warnings.append("No recorded decisions for this pair; no model output is inferred.")
    laya = [d for d in decisions if d["provider"] == "LayaProvider"]
    configurations = {_inference_config(d) for d in laya}
    if None in configurations:
        warnings.append("Some Laya calls lack recorded actual device/dtype; matched inference configuration is unknown.")
    if len(configurations - {None}) > 1:
        warnings.append("Laya actual device/dtype changed across calls; do not attribute differences only to state.")
    manifest, config = {}, {}
    for row in rows:
        if row["kind"] == "run_start":
            manifest, config = dict(row["data"]["manifest"]), row["data"]["resolved_config"]
        elif row["kind"] == "manifest_update":
            manifest.update(row["data"])
    report = {
        "version": "decision-pair-inspection-v0.1", "scope": "read_only_descriptive_diagnostics",
        "run": {"source": str(_path(path)), "run_id": manifest.get("run_id"),
                "config_hash": manifest.get("config_hash"), "resolved_config": config,
                "code_commit": manifest.get("code", {}).get("commit"), "versions": manifest.get("versions"),
                "model_content_ids": {k: v.get("content_id") for k, v in manifest.get("models", {}).items()},
                "declared_inference": manifest.get("inference"),
                "last_complete_record_id": rows[-1]["record_id"] if rows else None},
        "boundary": _index(pair), "diagnostics": analysis["diagnostics"], "warnings": warnings,
        "identity": {"candidate_set_id": pair["candidate_set_id"], "question_id": pair["question_id"],
                     "oracle_state_id": inputs[0].state.identity(), "perceptual_state_id": inputs[1].state.identity()},
        "state_meta": {branch: pair[f"{branch}_state"]["meta"] for branch in ("oracle", "perceptual")},
        "fields": {key: {**diff, "oracle": pair["oracle_state"]["fields"][key],
                         "perceptual": pair["perceptual_state"]["fields"][key]}
                   for key, diff in metadata["field_differences"].items()},
        "candidates": {"shared": pair["shared_candidates"],
                       "natural_perceptual": pair["natural_perceptual_candidates"],
                       "natural_oracle": pair["natural_oracle_candidates"],
                       "natural_feasible_set_agreement": metadata["natural_candidate_set_agreement"]},
        "shared_history": pair["shared_history"], "shared_effects": pair["shared_effects"],
        "decisions": decisions, "comparisons": comparisons,
        "stability": [r for r in analysis["stability"] if r["pair_id"] == pair["pair_id"]],
        "recorded_laya_device_dtype": sorted(configurations - {None}),
        "evaluator": None,
    }
    if show_input:
        report["validated_model_payloads"] = {}
        for decision in decisions:
            version, branch = decision.get("presentation_version", "audit-json-v0"), decision["branch"]
            inp = inputs[("oracle", "perceptual").index(branch)]
            report["validated_model_payloads"].setdefault(version, {})[branch] = {
                "state": inp.provider_input(presentation_version=version),
                "question": inp.model_questions(presentation_version=version)}
    if collection:
        report["evaluator"] = _evaluator_panel(collection, pair)
    return report


def render_text(report):
    """Compact terminal view; JSON preserves full precision/evidence."""
    def encoded(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if "boundary" not in report:
        return "\n".join([encoded(p) for p in report["pairs"]] + [f"diagnostics: {encoded(report['diagnostics'])}"])
    lines = [f"Boundary: {encoded(report['boundary'])}", f"Identity: {encoded(report['identity'])}",
             f"Run provenance: {encoded(report['run'])}",
             f"Recorded Laya device/dtype: {encoded(report['recorded_laya_device_dtype'])}"]
    lines.extend(f"WARNING: {w}" for w in report["warnings"])
    lines.append(f"Log diagnostics: {encoded(report['diagnostics'])}")
    lines.append("\nState fields (raw values; source/privilege/basis are audit evidence):")
    for key, field in report["fields"].items():
        lines.append(f"  {key}: {field['status']}; equal={field['value_equal']}")
        for branch in ("oracle", "perceptual"):
            lines.append(f"    {branch}: {encoded(field[branch])}")
    lines.append("\nShared candidates (offline probes, NOT execution permission):")
    lines.extend(f"  {c['token']}: {c['description']} [offered={c['feasible']}]" for c in report["candidates"]["shared"])
    for branch in ("oracle", "perceptual"):
        candidates = report["candidates"][f"natural_{branch}"]
        lines.append(f"Natural {branch}: {encoded(candidates)}")
    lines.append(f"Natural feasible-set agreement: {encoded(report['candidates']['natural_feasible_set_agreement'])}")
    lines.append(f"Shared history: {encoded(report['shared_history'])}")
    lines.append(f"Shared effects: {encoded(report['shared_effects'])}")
    lines.append("\nRecorded decisions (raw probabilities; normalized metrics shown separately):")
    for d in report["decisions"]:
        lines.append(f"  {d['provider']} {d['branch']} repeat={d['repeat']} choice={d['decision']['token']} "
                     f"latency_ms={d['latency_ms']:.3f} p={encoded(d['decision']['probabilities'])}")
    for r in report["comparisons"]:
        keys = ("provider", "repeat", "status", "missing_branches", "full_input_comparison_valid", "top1_agreement",
                "top2_set_agreement", "top2_boundary_tie", "js_divergence_nats", "oracle_margin",
                "oracle_input_truncation_status", "perceptual_input_truncation_status", "presentation_agreement",
                "recorded_device_dtype_agreement")
        lines.append(f"  Comparison: {encoded({k: r.get(k) for k in keys})}")
    lines.extend(f"  Repeatability: {encoded(r)}" for r in report["stability"])
    if report["evaluator"] is not None:
        e = report["evaluator"]
        lines.append(f"\nEVALUATOR ONLY: {e['scope']}; status={e['status']}")
        lines.append(f"  Source features match={e.get('source_features_match')}; "
                     f"source restore error={e.get('source_restore_max_error')}; STOP replay error={e.get('stop_replay_max_error')}")
        if e.get("source_restore_max_error") != 0 or e.get("stop_replay_max_error") != 0:
            lines.append("  WARNING: restoration/replay error nonzero or unknown; probe completeness is NOT restoration validation.")
        lines.append(f"  Identical commands + endpoint at THIS boundary only: {encoded(e['identical_command_and_endpoint_groups'])}")
        lines.append(f"  Local evidence: {encoded(e['local_reference'])}")
        for token, p in e["raw_probes"].items():
            execution = p.get("execution", {})
            lines.append(f"  {token}: contract_violation={execution.get('execution_contract_violation')} "
                         f"steps={execution.get('environment_step_count')} delta_m={encoded(execution.get('delta_m'))}")
        lines.append(f"  Evaluator diagnostics: {encoded(e['diagnostics'])}; missing probes={encoded(e['missing_probes'])}")
    if "validated_model_payloads" in report:
        lines.append(f"\nHash-validated model payloads (NOT the evaluator): {encoded(report['validated_model_payloads'])}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", help="episodes.jsonl or run directory")
    parser.add_argument("--list", action="store_true", dest="list_only")
    parser.add_argument("--pair-id", help="exact ID or unambiguous prefix")
    parser.add_argument("--step", type=int, help="environment control boundary, not repeat index")
    parser.add_argument("--init-state-id", type=int)
    parser.add_argument("--variant")
    parser.add_argument("--collection", help="optional raw collection for separate privileged evaluator panel")
    parser.add_argument("--show-input", action="store_true", help="show hash-validated payload; JSON also retains recorded token audits")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = vars(parser.parse_args(argv))
    path, fmt = args.pop("replay"), args.pop("format")
    try:
        report = inspect_pair(path, **args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) if fmt == "json" else render_text(report))


if __name__ == "__main__":
    main()
