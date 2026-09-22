"""Strict LocateAnything output parsing and optional local model worker."""
from __future__ import annotations

import queue
import re
import threading
import time
from pathlib import Path
from typing import Any

_BOX_RE = re.compile(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>")
_REF_RE = re.compile(r"<ref>(.*?)</ref>")


def parse_locateanything(text: str, width: int, height: int) -> dict[str, Any]:
    boxes = []
    seen = set()
    for match in _BOX_RE.finditer(str(text)):
        coords = tuple(int(x) for x in match.groups())
        if any(x < 0 or x > 1000 for x in coords):
            continue
        x1, y1, x2, y2 = coords
        if x2 <= x1 or y2 <= y1 or coords in seen:
            continue
        seen.add(coords)
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


class LatestFrameWorker:
    """Capacity-one worker: stale pending frames are replaced before inference."""

    def __init__(self, provider, infer, *, query: str, episode_id: str, track_id: str | None = None,
                 event_sink=None):
        self.provider = provider
        self.infer = infer
        self.query = query
        self.episode_id = episode_id
        self.track_id = track_id or query
        self._pending: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._results: queue.Queue[Any] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"vision-{self.query}", daemon=True)
        self.submitted = self.replaced = self.completed = self.dropped = 0
        self.last_latency_ms: float | None = None
        self.last_error: str | None = None
        self.event_sink = event_sink
        self._sink_lock = threading.Lock()
        self._thread.start()

    def _emit(self, kind, data):
        with self._sink_lock:
            if self.event_sink:
                self.event_sink(kind, data)

    def submit(self, frame: dict[str, Any]) -> bool:
        self.submitted += 1
        item = dict(frame)
        item.setdefault("query", self.query)
        item.setdefault("episode_id", self.episode_id)
        item.setdefault("track_id", self.track_id)
        try:
            self._pending.put_nowait(item)
            return True
        except queue.Full:
            try:
                replaced = self._pending.get_nowait()
                self._emit("vision_queue_replaced", {"capture_seq": replaced["capture_seq"],
                                                    "replacement_seq": item["capture_seq"]})
            except queue.Empty:
                pass
            self.replaced += 1
            self._pending.put_nowait(item)
            return True

    def poll(self):
        try:
            return self._results.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self._stop.set()
        # CUDA kernels must finish before interpreter/model teardown. A daemon
        # still executing torch at process exit can abort the whole process.
        self._thread.join(timeout=30.0)
        state = {"thread_alive": self._thread.is_alive(), "pending": self._pending.qsize(),
                 "unconsumed_results": self._results.qsize(), "submitted": self.submitted,
                 "replaced": self.replaced, "completed": self.completed, "dropped": self.dropped}
        self._emit("vision_worker_closed", state)
        if state["thread_alive"]:
            self._emit("failure", {"category": "timeout", "phase": "vision_shutdown", **state})
        with self._sink_lock:
            self.event_sink = None
        return state

    def _run(self):
        while not self._stop.is_set():
            try:
                item = self._pending.get(timeout=0.05)
            except queue.Empty:
                continue
            started = time.perf_counter()
            try:
                self._emit("vision_started", {"capture_seq": item["capture_seq"],
                                              "capture_sim_time": item["capture_sim_time"]})
                result = self.infer(item["rgb"], item.get("query", self.query))
                completion = time.time()
                event = self.provider.observe(
                    item["rgb"], item["depth_m"], item.get("query", self.query),
                    episode_id=item.get("episode_id", self.episode_id),
                    source_seq=int(item["capture_seq"]),
                    capture_sim_time=float(item["capture_sim_time"]),
                    track_id=item.get("track_id", self.track_id),
                    camera_to_world_matrix=item.get("camera_to_world"),
                    inference_result=result,
                )
                self._emit("vision_completed", {"capture_seq": item["capture_seq"],
                                                "capture_sim_time": item["capture_sim_time"],
                                                "model_completed_wall_time": completion,
                                                "worker_latency_ms": (time.perf_counter() - started) * 1000,
                                                "result": result, "event": event})
                if event is not None:
                    self._results.put(event)
                else:
                    self._emit("failure", {"category": "vision_missing", "capture_seq": item["capture_seq"]})
                self.completed += 1
            except Exception as exc:  # noqa: BLE001 - worker must survive one bad frame
                self.last_error = repr(exc)
                self.dropped += 1
                self._emit("failure", {"category": "model_error", "phase": "vision",
                                       "capture_seq": item["capture_seq"], "exception": repr(exc)})
            finally:
                self.last_latency_ms = (time.perf_counter() - started) * 1000.0
