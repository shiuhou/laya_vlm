"""Single ingress: reject before dispatch; capture order is not arrival order."""
from __future__ import annotations

from collections.abc import Mapping

from .contracts import (Envelope, ProtocolError, Receipt, Rejection, canonical_json,
                        freeze, integer, require, validate_frame_bundle)


class MessageRouter:
    def __init__(self, episode_id, episode_generation, goal_generation, clock_domain, *, sink=None):
        self.handlers = {}
        self.sink = sink
        self.reset(episode_id, episode_generation, goal_generation, clock_domain)

    def reset(self, episode_id, episode_generation, goal_generation, clock_domain):
        self.episode_id, self.episode_generation = episode_id, episode_generation
        self.goal_generation, self.clock_domain = goal_generation, clock_domain
        self.seen, self.sequences, self.frames, self.requests = {}, {}, {}, {}

    def register_handler(self, message_type, handler, *, validator):
        require(message_type not in self.handlers, "duplicate handler")
        self.handlers[message_type] = (validator, handler)

    def register_frame(self, frame_id, *, camera_id, frame_seq, calibration_version,
                       capture_sim_time_s, frame_ref):
        entry = freeze(dict(camera_id=camera_id, frame_seq=frame_seq,
                            calibration_version=calibration_version,
                            capture_sim_time_s=capture_sim_time_s, frame_ref=frame_ref))
        require(frame_id not in self.frames or self.frames[frame_id] == entry, "frame identity conflict")
        self.frames[frame_id] = entry

    def register_request(self, request_id, *, message_type, deadline_monotonic_ns,
                         expected, source_ids=()):
        integer(deadline_monotonic_ns, "deadline")
        require(isinstance(expected, Mapping), "request expected identities")
        for source in source_ids:
            require(source in self.frames or source in self.seen, "unknown request source", "HISTORY_MISSING")
        entry = freeze(dict(message_type=message_type, deadline_monotonic_ns=deadline_monotonic_ns,
                            expected=expected, source_ids=source_ids))
        require(request_id not in self.requests or self.requests[request_id] == entry,
                "request identity conflict")
        self.requests[request_id] = entry

    def _source_check(self, envelope, now):
        for source in envelope.source_ids:
            require(source in self.frames or source in self.seen or source in self.requests,
                    "unknown source", "HISTORY_MISSING")
        p = envelope.payload
        if envelope.message_type == "FrameBundle":
            validate_frame_bundle(p)
        if envelope.message_type == "GroundingRequest":
            frame = self.frames.get(p.get("frame_ref"))
            require(frame is not None, "unregistered frame", "HISTORY_MISSING")
            for key in ("camera_id", "frame_seq", "calibration_version"):
                require(p.get(key) == frame[key], key, "CALIBRATION_CHANGED" if key == "calibration_version" else "SOURCE_MISMATCH")
        if envelope.message_type in {"SemanticObservation", "ActionProposal", "BrainIntent"}:
            # BrainIntent correlation lives in source_ids; R4 does not put request_id in its payload.
            request_id = p.get("request_id")
            if request_id is None and envelope.message_type == "BrainIntent":
                matches = [s for s in envelope.source_ids if s in self.requests]
                require(len(matches) == 1, "brain request correlation")
                request_id = matches[0]
            request = self.requests.get(request_id)
            require(request is not None, "unregistered request", "SOURCE_MISMATCH")
            require(request["message_type"] == envelope.message_type, "reply type mismatch")
            require(now < request["deadline_monotonic_ns"], "reply deadline", "PROPOSAL_EXPIRED")
            for key, expected in request["expected"].items():
                require(p.get(key) == expected, key, "CALIBRATION_CHANGED" if key == "calibration_version" else "SOURCE_MISMATCH")

    def receive(self, message, received_monotonic_ns):
        identifier = message.message_id if isinstance(message, Envelope) else message.get("message_id", "unknown") if isinstance(message, Mapping) else "unknown"
        try:
            integer(received_monotonic_ns, "received_monotonic_ns")
            env = message if isinstance(message, Envelope) else Envelope.from_mapping(message)
            require((env.episode_id, env.episode_generation) == (self.episode_id, self.episode_generation),
                    "episode identity", "WRONG_EPISODE")
            require(env.goal_generation == self.goal_generation, "goal identity", "WRONG_GOAL")
            require(env.clock_domain == self.clock_domain, "clock domain", "CLOCK_DOMAIN_MISMATCH")
            require(env.emitted_monotonic_ns <= received_monotonic_ns, "future emission")
            content = canonical_json(env)
            if env.message_id in self.seen:
                require(self.seen[env.message_id] == content, "same ID with changed content", "ID_CONFLICT")
                receipt = Receipt(env.message_id, received_monotonic_ns, "DUPLICATE")
            else:
                key = (env.producer, env.producer_seq)
                require(key not in self.sequences, "producer sequence reused", "SEQUENCE_CONFLICT")
                require(env.message_type in self.handlers, "unregistered message type")
                self._source_check(env, received_monotonic_ns)
                validator, handler = self.handlers[env.message_type]
                validator(env.payload)
                # Handlers must validate before mutation and must not partially apply on rejection.
                accepted = handler(env)
                require(accepted is not False, "consumer rejected", "CONSUMER_REJECTED")
                self.seen[env.message_id] = content
                self.sequences[key] = env.message_id
                receipt = Receipt(env.message_id, received_monotonic_ns, "ACCEPTED")
        except (ProtocolError, TypeError, KeyError, AttributeError) as exc:
            code = exc.code if isinstance(exc, ProtocolError) else "INVALID_SCHEMA"
            receipt = Receipt(identifier, received_monotonic_ns, "REJECTED",
                              Rejection(identifier, code, detail=str(exc)))
        if self.sink:
            self.sink(message, receipt)
        return receipt
