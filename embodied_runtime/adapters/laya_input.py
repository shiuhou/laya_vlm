"""Audit the installed Laya tokenizer's effective input, without changing it."""
from ..runtime_core import _sha256_json


def encoding_audit(agent, state, questions):
    if not hasattr(agent, "tok") or not hasattr(agent, "cfg"):
        return {"available": False, "reason": "agent_has_no_tokenizer_config"}
    from laya.common import build_sequence, render_options, serialize_state
    tok = agent.tok
    max_len, head_max_len = agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192)
    result = {"available": True, "max_len": max_len, "head_max_len": head_max_len, "questions": {}}
    truncated = False
    for key, question in questions.items():
        q = {"t": question["type"], "ins": question["instructions"], "crit": question["criteria"]}
        tokens, markers = build_sequence(tok, state, q, max_len, head_max_len)
        empty, _ = build_sequence(tok, "", q, max_len, head_max_len)
        full_state = tok(serialize_state(state).replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
        full_heading = tok(f"{q['t']} question: {q['ins']}".replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
        options = [[tok.mask_token_id] + tok(" " + text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
                   for text in render_options(q)]
        heading_retained = empty[1:markers[0] - 1] if markers else []
        option_retained = [empty[start:markers[i+1] if i+1 < len(markers) else len(empty)-2]
                           for i, start in enumerate(markers)]
        room = max(0, max_len - len(empty))
        row = {"state_tokens": len(full_state), "state_budget": room, "effective_token_count": len(tokens),
               "state_truncated": len(full_state) > room, "heading_truncated": heading_retained != full_heading,
               "options_truncated": option_retained != options, "effective_input_ids": tokens,
               "effective_input_id": _sha256_json(tokens), "option_markers": markers}
        result["questions"][key] = row
        truncated |= any(row[k] for k in ("state_truncated", "heading_truncated", "options_truncated"))
    result["truncated"] = truncated
    return result
