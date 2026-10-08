"""Local RGB-only Qwen3-VL 2D grounding, with native token provenance.

This adapter has no controller, history, depth, annotation or world-state input.
Every request constructs a fresh chat and fresh generation cache.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
import hashlib
import importlib.metadata
from pathlib import Path
import time

import numpy as np

from ..contracts import content_hash, require
from ..perception.grounding_observation import parse_qwen_grounding

ADAPTER_REVISION = "qwen3vl-rgb-localizer/2"
QUERY = ("the flat outward-facing front panel of the open top drawer of the small cabinet on the "
         "tabletop, excluding its handle, inner cavity, rim, and tabletop")
SYSTEM = ("You are an image-only 2D localizer. Return only the requested JSON, without markdown or "
          "explanation. Use normalized image coordinates from 0 to 1000, with x increasing rightward "
          "and y downward. If the requested visible part cannot be identified, return []. Do not infer hidden surfaces.")
TEMPLATES = {
    "BOX": ('BOX: Locate one visible region matching: {query}. Return exactly one JSON array item with keys '
            '"label" and "bbox_2d". Set label to "drawer_front_pushable" and bbox_2d to [x1,y1,x2,y2] '
            'in the normalized coordinate system. Return [] if unknown.'),
    "POINT": ('POINT: Point to one visible location on: {query}. Return exactly one JSON array item with keys '
              '"label" and "point_2d". Set label to "drawer_front_pushable" and point_2d to [x,y] '
              'in the normalized coordinate system. Return [] if unknown.'),
}


def json_metadata(value):
    """Represent native HF metadata with JSON keys, refusing lossy collisions.

    Hugging Face id2label dictionaries have integer keys. Their explicit JSON
    representation uses decimal string keys; the evidence contract requires that
    conversion before freezing. This affects metadata only, never model config.
    """
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            require(type(key) in (str, int), "unsupported model metadata key type")
            name = str(key)
            require(name not in result, "model metadata keys collide after JSON conversion")
            result[name] = json_metadata(item)
        return result
    if isinstance(value, (tuple, list)):
        return [json_metadata(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_metadata(value.tolist())
    if isinstance(value, np.generic):
        return json_metadata(value.item())
    if isinstance(value, Enum):
        return json_metadata(value.value)
    require(value is None or type(value) in (str, bool, int, float), "unsupported model metadata value type")
    return value


def messages_for(mode, query=QUERY):
    require(mode in TEMPLATES, "BOX or POINT required")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": [
        {"type": "image"}, {"type": "text", "text": TEMPLATES[mode].format(query=query)}]}]


def generation_audit(ids, *, input_count, max_new_tokens, model_max_length, eos_token_ids):
    """Audit actual returned IDs; reaching budget with EOS is still complete."""
    ids = [int(x) for x in ids]
    eos = [int(x) for x in eos_token_ids]
    limit = min(max_new_tokens, model_max_length-input_count)
    require(limit > 0 and len(ids) <= limit, "output/context budget mismatch")
    terminal = bool(ids) and ids[-1] in eos
    return dict(actual_generated_token_ids=ids, actual_generated_token_count=len(ids),
        eos_token_ids=eos, input_token_count=input_count, model_max_length=model_max_length,
        max_new_tokens=max_new_tokens, effective_limit=limit,
        terminal_eos_observed=terminal, complete_generation=terminal,
        length_limit_reached=len(ids) >= limit,
        stop_reason="EOS" if terminal else "TOKEN_BUDGET" if len(ids) >= limit else "INCOMPLETE_STOP")


GREEDY_CALL_OVERRIDES = dict(use_model_defaults=False, do_sample=False, num_beams=1,
    use_cache=True, temperature=None, top_p=None, top_k=None,
    return_dict_in_generate=True, output_scores=False)


def generate_greedy(model, inputs, config):
    """Explicit call kwargs defeat Transformers' checkpoint-default merging.

    In Transformers 4.57.1, False in a supplied config can be treated as a global
    default and overwritten by checkpoint do_sample=True. Both disabling that
    merge and passing controls at highest-priority kwargs makes the boundary
    explicit. The adapter never forwards user/history generation kwargs.
    """
    return model.generate(**inputs, generation_config=config, **GREEDY_CALL_OVERRIDES)


def checkpoint_identity(path):
    """Fingerprint actual local bytes, including chat templates; no inferred upstream SHA."""
    from ..experiments.records import file_hash
    root = Path(path).expanduser().resolve()
    require(root.is_dir(), "local checkpoint directory missing")
    suffixes = {".safetensors", ".bin", ".json", ".model", ".txt", ".jinja", ".tiktoken"}
    files = {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*"))
             if p.is_file() and p.suffix in suffixes and not any(x.startswith('.') for x in p.relative_to(root).parts)}
    require(any(x.endswith((".safetensors", ".bin")) for x in files), "local weights missing")
    return dict(path=str(root), files_sha256=files, content_sha256=content_hash(files),
                revision_basis="actual local checkpoint bytes; acquisition manifest records upstream")


class Qwen3VLGroundingWorker:
    """Optional heavy dependencies are imported only when explicitly constructed."""

    def __init__(self, model_path, *, device="cuda:0", seed=1, model_identity=None):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.torch, self.device = torch, device
        self.model_identity = model_identity or checkpoint_identity(model_path)
        torch.manual_seed(seed)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        self.processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa").to(device).eval()
        require(self.model.config.model_type == "qwen3_vl", "Qwen3-VL checkpoint required")
        tokenizer = self.processor.tokenizer
        image_processor = self.processor.image_processor
        self.processor_identity = json_metadata(dict(processor_class=type(self.processor).__name__,
            tokenizer_class=type(tokenizer).__name__, image_processor_class=type(image_processor).__name__,
            image_processor_config=image_processor.to_dict(), chat_template_sha256=content_hash(self.processor.chat_template),
            model_config=self.model.config.to_dict(), model_class=type(self.model).__name__,
            checkpoint_generation_config=self.model.generation_config.to_dict(),
            tokenizer_eos_token_id=tokenizer.eos_token_id, tokenizer_pad_token_id=tokenizer.pad_token_id,
            tokenizer_model_max_length=tokenizer.model_max_length,
            weights_dtype=str(next(self.model.parameters()).dtype), attention_implementation="sdpa"))
        self.environment_identity = dict(seed=seed, device=device, torch=torch.__version__,
            transformers=importlib.metadata.version("transformers"),
            dtype="bfloat16", autocast=False, quantization=False, tf32=False,
            generation_history=False, cross_request_KV_cache=False, adapter_revision=ADAPTER_REVISION)

    def _sync(self):
        if str(self.device).startswith("cuda"):
            self.torch.cuda.synchronize(self.device)

    def infer(self, rgb, *, mode, query=QUERY, max_new_tokens=256):
        from PIL import Image
        require(isinstance(rgb, np.ndarray) and rgb.dtype == np.uint8
                and rgb.ndim == 3 and rgb.shape[2] == 3, "full original uint8 RGB required")
        require(type(max_new_tokens) is int and max_new_tokens > 0, "positive explicit token budget required")
        started = time.perf_counter()
        requested_at = datetime.now(timezone.utc).isoformat()
        # Only image and this new two-message chat reach the processor/model.
        messages = messages_for(mode, query)
        prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[prompt], images=[Image.fromarray(rgb)], return_tensors="pt")
        input_ids = inputs["input_ids"][0].tolist()
        tensor_receipts = {}
        for key, value in inputs.items():
            if self.torch.is_tensor(value):
                raw = value.detach().cpu().contiguous().view(self.torch.uint8).numpy().tobytes()
                tensor_receipts[key] = dict(shape=list(value.shape), dtype=str(value.dtype), sha256=hashlib.sha256(raw).hexdigest())
        grid = inputs.get("image_grid_thw")
        grids = grid.tolist() if grid is not None else None
        patch = getattr(self.processor.image_processor, "patch_size", None)
        resized = [[int(g[1]*patch), int(g[2]*patch)] for g in grids] if grids is not None and patch is not None else None
        cfg = deepcopy(self.model.generation_config)
        cfg.do_sample, cfg.num_beams, cfg.use_cache = False, 1, True
        cfg.temperature, cfg.top_p, cfg.top_k = None, None, None
        cfg.return_dict_in_generate, cfg.output_scores = True, False
        model_max = int(self.model.config.text_config.max_position_embeddings)
        effective_limit = min(max_new_tokens, model_max-len(input_ids))
        require(effective_limit > 0, "input exceeds context")
        cfg.max_new_tokens = effective_limit
        eos = cfg.eos_token_id
        eos = list(eos) if isinstance(eos, (list, tuple)) else [eos]
        require(eos and all(type(x) is int for x in eos), "actual generation EOS required")
        inputs = inputs.to(self.device)
        self._sync()
        preprocess_s = time.perf_counter()-started
        generation_start = time.perf_counter()
        with self.torch.inference_mode():
            output = generate_greedy(self.model, inputs, cfg)
        self._sync()
        generate_s = time.perf_counter()-generation_start
        sequence = output.sequences[0].tolist()
        require(sequence[:len(input_ids)] == input_ids, "model output changed input token prefix")
        generated = sequence[len(input_ids):]
        audit = generation_audit(generated, input_count=len(input_ids), max_new_tokens=max_new_tokens,
                                 model_max_length=model_max, eos_token_ids=eos)
        tokenizer = self.processor.tokenizer
        raw = tokenizer.decode(generated, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        terminals = tuple(tokenizer.decode([x], skip_special_tokens=False, clean_up_tokenization_spaces=False) for x in eos)
        typed = parse_qwen_grounding(raw, int(rgb.shape[1]), int(rgb.shape[0]), mode=mode,
                                     audit=audit, terminal_special_tokens=terminals)
        return dict(raw_output=raw, raw_output_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            audit=audit, typed=typed, terminal_special_tokens=terminals,
            input_evidence=dict(rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(), query=query,
                original_rgb_shape=list(rgb.shape), input_token_ids=input_ids,
                messages=messages, rendered_prompt=prompt, rendered_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                tensor_receipts=tensor_receipts, image_grid_thw=grids, processed_image_hw=resized,
                pixel_channels="full original RGB only", history_messages=0),
            timing=dict(requested_at_utc=requested_at, finished_at_utc=datetime.now(timezone.utc).isoformat(),
                preprocess_s=preprocess_s, generate_s=generate_s, total_s=time.perf_counter()-started),
            requested_generation_config=json_metadata(cfg.to_dict()),
            generation_call_overrides=dict(GREEDY_CALL_OVERRIDES),
            effective_generation_config=json_metadata(cfg.to_dict()), calibration_confidence=None,
            evaluation_labels_used=False, for_execution=False)
