"""Bounded process worker; slow inference never runs on the servo owner.

P0 uses CPU-only, picklable fake functions. Real GPU/model initialization belongs
inside a future worker factory. Shutdown owns and reaps its process explicitly.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import multiprocessing as mp
import queue

from .contracts import ProtocolError, canonical_json, freeze, thaw, require, integer


def _request_id(request):
    if request.get("protocol") == "embodied.protocol/1":
        return request["payload"]["request_id"]
    return request["request_id"]  # Small generic worker unit fixtures.


def _process_loop(infer, incoming, outgoing, stop):
    while not stop.is_set():
        try:
            request = incoming.get(timeout=.05)
        except queue.Empty:
            continue
        try:
            # Normalize before Queue's feeder thread; a mappingproxy/pickle error
            # must become a visible result, not strand an in-flight request.
            output = thaw(freeze(infer(request)))
            result = {"request_id": _request_id(request), "output": output, "error": None}
        except Exception as exc:
            result = {"request_id": _request_id(request), "output": None, "error": repr(exc)}
        # Full results cannot cause unlimited accumulation or block shutdown.
        while not stop.is_set():
            try:
                outgoing.put(result, timeout=.05)
                break
            except queue.Full:
                continue


class LatestWorker:
    def __init__(self, infer, *, result_capacity=4):
        if type(result_capacity) is not int or result_capacity < 1:
            raise ValueError("positive result capacity required")
        ctx = mp.get_context("spawn")
        self._incoming = ctx.Queue(maxsize=1)
        self._outgoing = ctx.Queue(maxsize=result_capacity)
        self._stop = ctx.Event()
        self._process = ctx.Process(target=_process_loop,
                                    args=(infer, self._incoming, self._outgoing, self._stop),
                                    name="p0-inference", daemon=False)
        self.pending = None
        self.in_flight = None
        self.replaced = 0
        self.completed = 0
        self.closed = False
        self._process.start()

    def submit(self, payload):
        if self.closed:
            raise ProtocolError("WORKER_CLOSED")
        request = freeze(payload)
        try:
            request_id = _request_id(request)
        except (KeyError, TypeError) as exc:
            raise ProtocolError("INVALID_SCHEMA", "worker request_id required") from exc
        if not isinstance(request_id, str):
            raise ProtocolError("INVALID_SCHEMA", "worker request_id required")
        if self.in_flight is None:
            self._dispatch(request)
        else:
            self.replaced += int(self.pending is not None)
            self.pending = request

    def _dispatch(self, request):
        if not self._process.is_alive():
            raise ProtocolError("WORKER_FAILED")
        self._incoming.put_nowait(thaw(request))
        self.in_flight = _request_id(request)

    def discard_pending(self):
        self.pending = None

    def poll(self):
        if self.closed:
            return None
        try:
            result = self._outgoing.get_nowait()
        except queue.Empty:
            if not self._process.is_alive():
                raise ProtocolError("WORKER_FAILED")
            return None
        if result["request_id"] != self.in_flight:
            raise ProtocolError("WORKER_CORRELATION_FAILED")
        self.in_flight = None
        self.completed += 1
        if self.pending is not None:
            pending, self.pending = self.pending, None
            self._dispatch(pending)
        return freeze(result)

    def close(self, timeout_s=1.):
        if self.closed:
            return {"alive": False, "terminated": False}
        self.closed = True
        self.pending = None
        self._stop.set()
        self._process.join(timeout_s)
        terminated = self._process.is_alive()
        if terminated:
            self._process.terminate()
            self._process.join(timeout_s)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout_s)
        if self._process.is_alive():
            raise ProtocolError("WORKER_SHUTDOWN_FAILED")
        for q in (self._incoming, self._outgoing):
            q.cancel_join_thread()
            q.close()
        self._process.close()
        return {"alive": False, "terminated": terminated}


@dataclass(frozen=True)
class ControlEvent:
    event_id: str
    kind: str
    payload: object
    ack_deadline_ns: int

    def __post_init__(self):
        require(isinstance(self.event_id, str) and bool(self.event_id), "control event ID")
        require(self.kind in {"contract", "cancel", "feedback", "intent"}, "control event kind")
        integer(self.ack_deadline_ns, "ACK deadline")
        # Typed frozen contracts retain their interface; arbitrary mappings must
        # not change after the ID/hash was admitted to the reliable queue.
        if isinstance(self.payload, dict):
            object.__setattr__(self, "payload", freeze(self.payload))
        canonical_json(self.payload)


class ReliableEvents:
    """Single-owner bounded unacknowledged events; failure invokes stop first."""
    def __init__(self, *, capacity=32, on_failure):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("positive control capacity required")
        self.capacity, self.on_failure = capacity, on_failure
        self.pending = OrderedDict()
        self.seen = {}

    def send(self, event: ControlEvent):
        content = canonical_json(event)
        if event.event_id in self.seen:
            if self.seen[event.event_id] != content:
                self.on_failure("CONTROL_ID_CONFLICT")
                raise ProtocolError("CONTROL_ID_CONFLICT")
            return False
        if len(self.pending) >= self.capacity:
            self.on_failure("CONTROL_OVERFLOW")
            raise ProtocolError("CONTROL_OVERFLOW")
        self.seen[event.event_id] = content
        self.pending[event.event_id] = event
        return True

    def ack(self, event_id):
        if event_id not in self.seen:
            raise ProtocolError("UNKNOWN_ACK")
        self.pending.pop(event_id, None)

    def check(self, now_ns):
        if any(now_ns >= e.ack_deadline_ns for e in self.pending.values()):
            self.on_failure("CONTROL_ACK_TIMEOUT")
            raise ProtocolError("CONTROL_ACK_TIMEOUT")

    def reset(self):
        self.pending.clear()
        self.seen.clear()
