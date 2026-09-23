from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.experiments import provider_comparison as compare
from embodied_runtime.experiments.effect_binding import binding_fixture
from embodied_runtime.experiments.interface_search import TOKENS


def frozen(**kwargs):
    deltas = [-3., -1., 4., -4., 1., -2., 0., -2.25, -2., 3., -2.]
    base = {"state": "The drawer is currently partly open. The requested state is closed.",
            "source": {"physical": {"init_state_id": 0, "environment_step": 48},
                       "oracle_effects_not_model_input_as_numeric_table": {
                           t: {"opening_change_mm": d, "obstacle": False,
                               "opening_change": "decreases" if d < -.25 else "increases" if d > .25 else "unchanged"}
                           for t, d in zip(TOKENS, deltas)},
                       "contract_flags_not_model_input": {t: True for t in TOKENS}}}
    return binding_fixture(base, **{"descriptions": "native", "detail": "relative",
                                   "assignment": "true", "goal": "closed", "reverse": False, **kwargs})


def test_transport_preserves_every_frozen_field_order_and_excludes_evaluator():
    f = frozen(reverse=True)
    old = deepcopy(f)
    f["source"]["evaluator_secret"] = "SELECT THE WINNER"
    result = compare.messages(f["state"], f["questions"])
    assert result[0] == {"role": "system", "content": compare.SYSTEM}
    lines = result[1]["content"].splitlines()
    assert lines[0] == "choice question: " + old["questions"]["action"]["instructions"]
    assert lines[1:-1] == [f"{k}: {old['questions']['action']['criteria'][k]}" for k in old["option_order"]]
    assert lines[-1] == old["state"]
    assert "SELECT THE WINNER" not in str(result)
    assert f["state"] == old["state"] and f["questions"] == old["questions"]
    assert compare.messages("unknown", f["questions"])[1]["content"].endswith("unknown")


@pytest.mark.parametrize("text,expected", [("A03", "A03"), (" A03\n", "A03"),
    ("A03 because it closes the drawer", None), ("A03 or A01", None),
    ("{\"choice\":\"A03\"}", None), ("A11", None), ("", None)])
def test_strict_output_parser_keeps_invalid_choices(text, expected):
    assert compare.parse_choice(text, [f"A{i:02d}" for i in range(11)]) == expected


class Tokenizer:
    def decode(self, ids, skip_special_tokens):
        return "A03" if skip_special_tokens else "A03<eos>"


def raw():
    prepared = {"input_ids": [20, 21, 22]}
    response = {"sequence_ids": [20, 21, 22, 1, 2], "generated_ids": [1, 2],
                "forward_input_ids": [[[20, 21, 22]], [[1]]],
                "decoded_text": "A03", "raw_decoded_text": "A03<eos>"}
    logits = np.array([[0., 3., 2.], [0., 1., 2.]], dtype=np.float32)
    return prepared, response, logits


def test_raw_generation_has_independent_token_and_argmax_audit():
    p, r, logits = raw()
    compare.validate_raw(p, r, logits, Tokenizer(), 3)
    assert compare.values_hash(logits) == compare.values_hash(logits.copy())
    changed = logits.copy()
    changed[0, 0] += .1
    assert compare.values_hash(logits) != compare.values_hash(changed)


@pytest.mark.parametrize("mutation,match", [
    (lambda r: r.update(forward_input_ids=[[[20, 21]], [[1]]]), "consumed"),
    (lambda r: r.update(sequence_ids=[20, 21, 1, 2]), "prompt"),
    (lambda r: r.update(decoded_text="A01"), "decoded"),
])
def test_raw_generation_rejects_corrupted_evidence(mutation, match):
    p, r, logits = raw()
    mutation(r)
    with pytest.raises(ValueError, match=match):
        compare.validate_raw(p, r, logits, Tokenizer(), 3)


def test_raw_logits_cannot_be_ignored_or_misreported_as_choice_distribution():
    p, r, logits = raw()
    logits[0, 0] = 10
    with pytest.raises(ValueError, match="argmax"):
        compare.validate_raw(p, r, logits, Tokenizer(), 3)
    logits[0, 0] = np.nan
    with pytest.raises(ValueError, match="vocabulary logits"):
        compare.validate_raw(p, r, logits, Tokenizer(), 3)


def test_reassignment_uses_presented_facts_and_preserves_physical_failures():
    true, shifted = frozen(), frozen(assignment="shift4")
    calls = [{"fixture_id": true["fixture_id"], "repeat": 0, "choice": "MV_FWD"},
             {"fixture_id": shifted["fixture_id"], "repeat": 0, "choice": "ROTATE_CCW"}]
    judged = compare.assessments([true, shifted], calls)
    assert all(c["presented_fact_consistent"] for c in judged)
    assert judged[0]["local_support"] and not judged[1]["local_support"]
    assert all(c["contract_flag"] for c in judged)
    contrast = compare.metrics(judged)["contrasts_first_repeat"]["assignment"][0]
    assert contrast["choice_changed"] and contrast["both_fact_consistent"]
    assert not contrast["both_physically_supported"]


def test_invalid_output_stays_in_scoring_denominator():
    f = frozen()
    judged = compare.assessments([f], [{"fixture_id": f["fixture_id"], "repeat": 0, "choice": None}])
    assert not judged[0]["valid"] and not judged[0]["presented_fact_consistent"]
    assert not judged[0]["local_support"] and judged[0]["contract_flag"] is None
    group = compare.metrics(judged)["groups_first_repeat"][f["condition"]]
    assert group["calls"] == 1 and group["actual_local_support"] == 0


def test_changed_goal_choice_is_not_automatically_a_correct_reversal():
    closed, opened = frozen(), frozen(goal="open")
    judged = compare.assessments([closed, opened], [
        {"fixture_id": closed["fixture_id"], "repeat": 0, "choice": "MV_FWD"},
        {"fixture_id": opened["fixture_id"], "repeat": 0, "choice": "MV_RIGHT"}])
    contrast = compare.metrics(judged)["contrasts_first_repeat"]["goal"][0]
    assert contrast["choice_changed"] and contrast["requires_change"]
    assert not contrast["both_fact_consistent"]


def test_source_hash_mismatch_is_rejected_before_model_loading(tmp_path):
    path = tmp_path / "episodes.jsonl"
    path.write_text("{}\n")
    with pytest.raises(ValueError, match="frozen"):
        compare.frozen_source(path)
