"""Clause truth, fixed interventions, leakage and incomplete judgments."""
from copy import deepcopy
from pathlib import Path

import pytest

from embodied_runtime.experiments import predicate_decomposition as d
from embodied_runtime.experiments.records import load_records


def source_fixture(*, goal="closed", delta=-.5, stop=-.5, opening="decreases", relative="same"):
    criterion = ("Choose an intervention with opening decreases, vs STOP lower, and obstacle no."
                 if goal == "closed" else "Choose an intervention with opening increases, vs STOP higher, and obstacle no.")
    return {"state": "The drawer is partly open; requested " + goal, "questions": {"action": {
        "instructions": d.PREFIX + criterion + "\nCandidate: hold pose and grip; opening "
                        + opening + "; vs STOP " + relative + "; obstacle no"}},
        "source": {"goal": goal, "oracle_effects_not_model_input_as_numeric_table": {
            "A": {"opening_change_mm": delta, "obstacle": False}, "STOP": {"opening_change_mm": stop, "obstacle": False}},
            "effect_assignment": {"T": "A"}}, "verification": {"tested_token": "T"}}


def group():
    f = source_fixture()
    labels, criterion, candidate = d.clause_labels(f)
    return {"group_id": "group", "state": f["state"], "goal": "closed", "criterion": criterion,
            "candidate": candidate, "truths_not_model_input": labels, "lineage": [{"secret": "evaluator only"}]}


def test_decreased_opening_does_not_imply_stop_relative_progress():
    labels, _, _ = d.clause_labels(source_fixture())
    assert labels == {"opening_only": True, "stop_only": False, "full_control": False, "full_spaced": False}


def test_stop_progress_without_absolute_progress():
    labels, _, _ = d.clause_labels(source_fixture(goal="open", delta=.1, stop=-.5, opening="unchanged", relative="higher"))
    assert labels["stop_only"] and not labels["opening_only"] and not labels["full_control"]


def test_exact_threshold_is_not_strict_progress():
    labels, _, _ = d.clause_labels(source_fixture(delta=-.25, stop=0, opening="unchanged", relative="same"))
    assert not any(labels.values())


def test_reassignment_uses_presented_effect_not_action_identity():
    f = source_fixture()
    f["source"]["oracle_effects_not_model_input_as_numeric_table"]["T"] = {"opening_change_mm": 9., "obstacle": False}
    labels, _, _ = d.clause_labels(f)
    assert labels["opening_only"]


@pytest.mark.parametrize("bad", ["text", "numeric", "obstacle", "criterion"])
def test_corrupt_evidence_is_rejected(bad):
    f = source_fixture()
    if bad == "text":
        f["questions"]["action"]["instructions"] = f["questions"]["action"]["instructions"].replace("vs STOP same", "vs STOP lower")
    elif bad == "numeric":
        f["source"]["oracle_effects_not_model_input_as_numeric_table"]["A"]["opening_change_mm"] = float("nan")
    elif bad == "obstacle":
        f["source"]["oracle_effects_not_model_input_as_numeric_table"]["A"]["obstacle"] = True
    else:
        f["questions"]["action"]["instructions"] = f["questions"]["action"]["instructions"].replace("Criterion:", "Correct answer:")
    with pytest.raises(ValueError):
        d.clause_labels(f)


def test_full_spaced_changes_only_negative_display_text():
    g = group()
    control, spaced = (d.make_fixture(g, c, False) for c in ("full_control", "full_spaced"))
    assert control["state"] == spaced["state"]
    assert control["questions"]["action"]["instructions"] == spaced["questions"]["action"]["instructions"]
    assert control["option_to_canonical"] == spaced["option_to_canonical"]
    expected = deepcopy(control["questions"])
    expected["action"]["criteria"]["V1"] = "does not satisfy"
    assert spaced["questions"] == expected


def test_clause_labels_and_evidence_never_enter_model_payload():
    g = group()
    for condition in d.CONDITIONS:
        f = d.make_fixture(g, condition, False)
        assert f["state"] == g["state"]
        assert f["questions"]["action"]["instructions"].endswith("\nCandidate: " + g["candidate"])
        assert "evaluator only" not in str((f["state"], f["questions"]))
        assert "truths_not_model_input" not in str((f["state"], f["questions"]))
    opening = d.make_fixture(g, "opening_only", False)
    assert opening["questions"]["action"]["instructions"].startswith(d.PREFIX + "Judge only whether the stated opening decreases.")
    assert opening["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["satisfies"]


def test_reverse_order_preserves_identity_and_label():
    a, b = (d.make_fixture(group(), "stop_only", rev) for rev in (False, True))
    assert a["option_to_canonical"] == b["option_to_canonical"]
    assert a["option_order"] == list(reversed(b["option_order"]))
    assert a["questions"] == b["questions"]
    assert a["payload_id"] != b["payload_id"]
    assert a["diagnostic_reference_not_model_input"] == b["diagnostic_reference_not_model_input"]


def test_missing_judgments_cannot_improve_balanced_accuracy():
    fs = [d.make_fixture(group(), c, False) for c in ("opening_only", "stop_only")]
    report = d.confusion(fs, [])
    assert report["missing_positive"] == report["missing_negative"] == 1
    assert report["balanced_accuracy"] == 0


def test_archived_dedup_retains_lineage_and_byte_identical_controls():
    path = Path("runs/autonomous-research/predicate-verification-run-01/episodes.jsonl")
    if not path.exists():
        pytest.skip("local frozen model evidence absent from source clones")
    rows, errors = load_records(path)
    assert not errors
    fs = [r["data"] for r in rows if r["kind"] == "search_fixture"]
    groups = d.unique_groups(fs)
    assert len(groups) == 74 and sum(len(g["lineage"]) for g in groups) == 176
    by_id = {f["fixture_id"]: f for f in fs}
    all_links = []
    for g in groups:
        for rev in (False, True):
            control = d.make_fixture(g, "full_control", rev)
            for lineage in g["lineage"]:
                original = by_id[lineage["source_fixture_ids"]["reversed" if rev else "forward"]]
                all_links.append(original["fixture_id"])
                assert control["payload_id"] == original["payload_id"]
                assert control["state"] == original["state"] and control["questions"] == original["questions"]
    assert len(all_links) == len(set(all_links)) == 352
    removed = next(f["verification"] for f in fs if "verification" in f)
    incomplete = [f for f in fs if not (f.get("verification", {}).get("parent_fixture_id") == removed["parent_fixture_id"]
                  and f.get("verification", {}).get("tested_token") == removed["tested_token"])]
    with pytest.raises(ValueError, match="176-to-74"):
        d.unique_groups(incomplete)
