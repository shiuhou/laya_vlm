from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.experiments import current_motor_provider_control as control
from embodied_runtime.experiments import current_motor_replication as motor
from embodied_runtime.experiments import provider_comparison as pc
from embodied_runtime.experiments.records import file_hash
from embodied_runtime.runtime_core import _sha256_json


class Tokenizer:
    all_special_ids = [2]

    def decode(self, ids, skip_special_tokens):
        return "x+40mm" if skip_special_tokens else "x+40mm<eos>"


def evidence():
    prepared = {"input_ids": [20, 21, 22], "input_id": "input"}
    raw = {"sequence_ids": [20, 21, 22, 1, 2], "generated_ids": [1, 2],
           "forward_input_ids": [[[20, 21, 22]], [[1]]], "decoded_text": "x+40mm",
           "raw_decoded_text": "x+40mm<eos>", "device": "cpu", "dtype": "torch.float32"}
    logits = np.array([[0., 3., 2.], [0., 1., 2.]], dtype=np.float32)
    loaded = {"config": {"vocab_size": 3}, "generation_config": {"eos_token_id": [2]},
              "device": "cpu", "dtype": "torch.float32"}
    return prepared, raw, logits, loaded


def test_native_option_validated_with_actual_tokens_and_argmax():
    prepared, raw, logits, loaded = evidence()
    assert control.validate_answer(prepared, raw, logits, Tokenizer(), loaded, ["x+40mm", "open"]) == "x+40mm"
    logits[0, 0] = 4.
    with pytest.raises(ValueError, match="argmax"):
        control.validate_answer(prepared, raw, logits, Tokenizer(), loaded, ["x+40mm", "open"])


@pytest.mark.parametrize("mutation,match", [
    (lambda p, r, logits, m: r.update(forward_input_ids=[[[99]], [[1]]]), "consumed"),
    (lambda p, r, logits, m: r.update(device="cuda"), "device"),
    (lambda p, r, logits, m: m["generation_config"].update(eos_token_id=[0]), "EOS"),
])
def test_incomplete_generation_or_execution_evidence_rejected(mutation, match):
    prepared, raw, logits, loaded = evidence()
    mutation(prepared, raw, logits, loaded)
    with pytest.raises(ValueError, match=match):
        control.validate_answer(prepared, raw, logits, Tokenizer(), loaded, ["x+40mm", "open"])


def test_valid_token_generation_of_nonmember_is_not_extracted_or_retried():
    prepared, raw, logits, loaded = evidence()
    with pytest.raises(ValueError, match="malformed"):
        control.validate_answer(prepared, raw, logits, Tokenizer(), loaded, ["open", "close"])


def test_unexpected_internal_special_token_is_rejected():
    prepared, raw, logits, loaded = evidence()
    tokenizer = Tokenizer()
    tokenizer.all_special_ids = [1, 2]
    with pytest.raises(ValueError, match="special"):
        control.validate_answer(prepared, raw, logits, tokenizer, loaded, ["x+40mm", "open"])


def test_logit_artifact_and_invalid_response_remain_in_missing_denominator(tmp_path):
    prepared, raw, logits, loaded = evidence()
    f = {"fixture_id": "fixture", "option_order": ["open", "close"]}
    intent = {"fixture_id": "fixture", "repeat": 0, "ordinal": 0}
    intent["call_id"] = _sha256_json(intent)
    intent["input_id"] = "input"
    path = tmp_path / "logits.npz"
    np.savez_compressed(path, logits=logits)
    response = {"call_id": intent["call_id"], **raw, "logits_artifact": "logits.npz",
                "logits_sha256": file_hash(path), "logits_values_sha256": pc.values_hash(logits)}
    rows = [{"kind": "provider_call_intent", "data": intent}, {"kind": "provider_raw_response", "data": response}]
    calls, invalid, missing = control.recover_calls(tmp_path, rows, [f], {"fixture": prepared}, Tokenizer(), loaded)
    assert not calls and len(invalid) == 1 and not missing
    assert "malformed" in invalid[0]["reason"]
    calls, invalid, missing = control.recover_calls(tmp_path, rows[:1], [f], {"fixture": prepared}, Tokenizer(), loaded)
    assert not calls and not invalid and missing == [intent["call_id"]]


def test_wrong_fixture_traversal_rejected(tmp_path):
    prepared, _, _, loaded = evidence()
    f = {"fixture_id": "fixture", "option_order": ["open", "close"]}
    intent = {"fixture_id": "fixture", "repeat": 0, "ordinal": 1}
    intent["call_id"] = _sha256_json(intent)
    intent["input_id"] = "input"
    with pytest.raises(ValueError, match="traversal"):
        control.recover_calls(tmp_path, [{"kind": "provider_call_intent", "data": intent}],
                              [f], {"fixture": prepared}, Tokenizer(), loaded)


def test_all_current_fields_and_canonical_native_order_preserved_in_existing_wrapper():
    source = Path("runs/privileged-reference/local-objective-task-adapter-episode-01")
    if not source.exists():
        pytest.skip("local frozen current motor archive unavailable")
    fixtures, _, _ = motor.frozen_source(source)
    for fixture in fixtures:
        before = deepcopy(fixture)
        fixture["source"]["evaluator_secret"] = "DO NOT TRANSMIT"
        messages = pc.messages(fixture["state"], fixture["questions"])
        assert messages[0] == {"role": "system", "content": pc.SYSTEM}
        content = messages[1]["content"]
        lines = content.splitlines()
        assert lines[0] == "choice question: " + fixture["questions"]["action"]["instructions"]
        assert lines[1:1+len(fixture["option_order"]) ] == [
            name + ": " + fixture["questions"]["action"]["criteria"][name] for name in fixture["option_order"]]
        assert content.endswith(before["state"])
        assert "DO NOT TRANSMIT" not in str(messages)
        assert before["state"] == fixture["state"] and before["questions"] == fixture["questions"]


def test_native_names_fit_frozen_qwen_tokenizer_when_available():
    path = Path(control.MODEL_PATH)
    source = Path("runs/privileged-reference/local-objective-task-adapter-episode-01")
    if not path.exists() or not source.exists():
        pytest.skip("local model/tokenizer or frozen source unavailable")
    transformers = pytest.importorskip("transformers")
    tokenizer = transformers.AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    fixtures, _, _ = motor.frozen_source(source)
    result = control.option_audit(tokenizer, fixtures)
    assert set(result) == {name for fixture in fixtures for name in fixture["option_order"]}
    assert max(item["tokens_including_eos"] for item in result.values()) <= 16


def test_source_hashes_and_complete_laya_controls_before_qwen_loading():
    import argparse
    args = argparse.Namespace(source="runs/privileged-reference/local-objective-task-adapter-episode-01",
                              laya_source="runs/autonomous-research/current-motor-replication-01",
                              qwen_source="runs/provider-comparison/qwen-v01")
    if not all(Path(path).exists() for path in vars(args).values()):
        pytest.skip("local archived sources unavailable")
    fixtures, laya, old = control.sources(args)
    assert len(fixtures) == 5 and laya["complete"]
    assert old["generation_config"]["max_new_tokens"] == 16
    assert old["generation_config"]["do_sample"] is False
    assert old["system_instruction"] == pc.SYSTEM
