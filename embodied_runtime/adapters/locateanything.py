"""Strict LocateAnything output parsing and optional local model worker."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

_BOX_RE = re.compile(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>")
_REF_RE = re.compile(r"<ref>(.*?)</ref>")


def parse_locateanything(text: str, width: int, height: int) -> dict[str, Any]:
    boxes = []
    for match in _BOX_RE.finditer(str(text)):
        coords = tuple(int(x) for x in match.groups())
        if any(x < 0 or x > 1000 for x in coords):
            continue
        x1, y1, x2, y2 = coords
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append([x1 * width / 1000.0, y1 * height / 1000.0, x2 * width / 1000.0, y2 * height / 1000.0])
    refs = [m.group(1).strip() for m in _REF_RE.finditer(str(text)) if m.group(1).strip()]
    return {"boxes_xyxy": boxes, "references": refs, "raw_response": str(text)}


class LocateAnythingWorker:
    """Lazy local worker; imports heavy Transformers only when constructed."""
    def __init__(self, model_path: str, *, device: str = "cuda", dtype: str = "bfloat16"):
        import torch
        from transformers import AutoModel, AutoProcessor, AutoTokenizer
        self.device, self.model_path = device, str(Path(model_path).expanduser())
        self.torch = torch
        self.dtype = getattr(torch, dtype) if isinstance(dtype, str) else dtype
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True, local_files_only=True)
        self.processor = AutoProcessor.from_pretrained(self.model_path, trust_remote_code=True, local_files_only=True)
        self.model = AutoModel.from_pretrained(self.model_path, torch_dtype=self.dtype, trust_remote_code=True, local_files_only=True).to(device).eval()

    def infer(self, rgb, query: str) -> dict[str, Any]:
        from PIL import Image
        image = Image.fromarray(rgb).convert("RGB")
        question = f"Locate a single instance that matches the following description: {query}."
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": question}]}]
        text = self.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images, videos = self.processor.process_vision_info(messages)
        inputs = self.processor(text=[text], images=images, videos=videos, return_tensors="pt").to(self.device)
        pixel_values = inputs["pixel_values"].to(self.dtype)
        started = time.perf_counter()
        with self.torch.no_grad():
            response = self.model.generate(pixel_values=pixel_values, input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], image_grid_hws=inputs.get("image_grid_hws"), tokenizer=self.tokenizer, max_new_tokens=256, use_cache=True, generation_mode="hybrid", temperature=0.0, do_sample=False, verbose=False)
        latency_ms = (time.perf_counter() - started) * 1000.0
        answer = response[0] if isinstance(response, tuple) else response
        result = parse_locateanything(answer, image.width, image.height)
        result["score"] = 1.0 if result["boxes_xyxy"] else 0.0
        result["model_latency_ms"] = latency_ms
        return result
