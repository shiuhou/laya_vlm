"""Minimal generic scheduler: registered intents, bounded proposals, one servo.

This is the new sensor-only migration path. It neither invokes the legacy
privileged Runtime.step nor implements a task-specific phase/action policy.
"""
from __future__ import annotations

from dataclasses import replace

from ..contracts import BrainIntent, Envelope, ProtocolError, Rejection, canonical_json, require, thaw
from ..policy_observation import PolicyObservation, project_candidate
from ..workers import ControlEvent, ReliableEvents
from .action_contracts import ActionProposal, instantiate_contract, validate_identity
from .local_candidates import ContextIdentity
from .servo import Servo


class Scheduler:
    def __init__(self, backend, *, initial_identity, latest_context, config,
                 constraint_templates, completion_templates, operations,
                 policy_config_revision, clock_domain, sink=None, target_context=None, monotonic_clock=None):
        self.backend, self._latest = backend, latest_context
        self._target_context = target_context
        self.identity, self.config = initial_identity, config
        self.constraint_templates = frozenset(constraint_templates)
        self.completion_templates = frozenset(completion_templates)
        self.operations = frozenset(operations)
        self.policy_config_revision = policy_config_revision
        self.clock_domain = clock_domain
        self.monotonic_clock = monotonic_clock
        self.sink = sink
        self.intent = None
        self._intent_history = {}
        self._brain_requests = {}
        self.requests = {}
        self.decisions = {}
        self._request_decisions = {}
        self._cancel_ids = {}
        self.workers = []
        self.rejections = []
        self.halted = False
        self.stop_reason = None
        self.now_sim, self.now_ns = 0., 0
        self._episode_start = None
        self._intent_started_sim = None
        self.servo = Servo(backend, latest_context=self.validation_context, sink=self._emit,
                           monotonic_clock=monotonic_clock)
        self.control = ReliableEvents(capacity=config["control_capacity"], on_failure=self._fail)

    def _emit(self, kind, value):
        if self.sink:
            try:
                self.sink(kind, value)
            except Exception:
                # A logging failure cannot leave an authorized motion running.
                self.halted = True
                self.stop_reason = "LOG_FAILURE"
                self.servo.active = None
                self.backend.hold()
                raise

    def _fail(self, reason):
        self.halted, self.stop_reason = True, reason
        self.servo.cancel(reason, sim_time_s=self.now_sim, monotonic_ns=self.now_ns)

    def _reject(self, message_id, exc):
        rejection = Rejection(message_id, exc.code, detail=exc.detail)
        self.rejections.append(rejection)
        self._emit("rejection", rejection)
        return False

    def validation_context(self, sim_time_s, monotonic_ns):
        latest = (self._target_context(self.identity, sim_time_s, monotonic_ns)
                  if self._target_context else self._latest(sim_time_s, monotonic_ns))
        observed = latest.identity
        require((observed.episode_id, observed.episode_generation) ==
                (self.identity.episode_id, self.identity.episode_generation), "latest episode", "WRONG_EPISODE")
        require(observed.goal_generation == self.identity.goal_generation, "latest goal", "WRONG_GOAL")
        # Installed intent identity belongs to scheduler, never a sensor or model.
        latest = replace(latest, identity=replace(observed, intent_id=self.identity.intent_id,
                                                 intent_generation=self.identity.intent_generation))
        validate_identity(self.identity, latest.identity)
        return latest

    def register_brain_request(self, request_id, *, source_snapshot_id, deadline_monotonic_ns):
        require(deadline_monotonic_ns > self.now_ns, "brain deadline", "PROPOSAL_EXPIRED")
        require(deadline_monotonic_ns <= self.now_ns + int(self.config["brain_request_ttl_s"]*1e9),
                "brain budget exceeds configuration")
        record = (source_snapshot_id, deadline_monotonic_ns, self.identity)
        require(request_id not in self._brain_requests or self._brain_requests[request_id] == record,
                "brain request reused")
        self._brain_requests[request_id] = record

    def install_intent(self, intent: BrainIntent, *, request_id):
        try:
            require(not self.halted, "scheduler halted", "HALTED")
            content = canonical_json(intent)
            if intent.intent_id in self._intent_history:
                require(self._intent_history[intent.intent_id] == content, "intent ID conflict")
                return False
            require(request_id in self._brain_requests, "unregistered brain request")
            source, deadline, identity = self._brain_requests[request_id]
            validate_identity(identity, self.identity)
            require(self.now_ns < deadline and self.now_ns < intent.expires_monotonic_ns <= deadline,
                    "brain response cannot renew its deadline", "PROPOSAL_EXPIRED")
            require(intent.based_on_snapshot_id == source, "intent source")
            require(intent.constraint_template_id in self.constraint_templates
                    and intent.completion_template_id in self.completion_templates
                    and intent.operation in self.operations
                    and intent.policy_config_revision == self.policy_config_revision,
                    "unregistered template/operation/config")
            require(intent.intent_generation > self.identity.intent_generation, "intent generation must advance")
            proposed_identity = replace(self.identity, intent_id=intent.intent_id, intent_generation=intent.intent_generation,
                                        target_track_id=intent.target_track_id, target_track_generation=intent.target_track_generation,
                                        feature_id=intent.feature_id, feature_generation=intent.feature_generation)
            latest = (self._target_context(proposed_identity, self.now_sim, self.now_ns)
                      if self._target_context else self._latest(self.now_sim, self.now_ns))
            require((latest.identity.episode_id, latest.identity.episode_generation, latest.identity.goal_generation) ==
                    (self.identity.episode_id, self.identity.episode_generation, self.identity.goal_generation),
                    "new target context belongs to another goal", "WRONG_GOAL")
            require(source == latest.snapshot_id or source in latest.lineage_source_ids,
                    "intent source lineage", "HISTORY_MISSING")
            require((intent.target_track_id, intent.target_track_generation, intent.feature_id, intent.feature_generation) ==
                    (latest.identity.target_track_id, latest.identity.target_track_generation,
                     latest.identity.feature_id, latest.identity.feature_generation), "intent target lineage", "TARGET_LOST")
            require(latest.geometry_valid and latest.proprio_valid and latest.semantics_unchanged,
                    "intent latest state invalid", "SENSOR_INVALID")
            self.servo.cancel("INTENT_REPLACED", sim_time_s=self.now_sim, monotonic_ns=self.now_ns)
            self.requests.clear()
            for worker in self.workers:
                worker.discard_pending()
            self.intent = intent
            self.identity = replace(proposed_identity, calibration_versions=latest.identity.calibration_versions)
            self._intent_started_sim = self.now_sim
            self._intent_history[intent.intent_id] = content
            self._emit("intent_installed", intent)
            return True
        except ProtocolError as exc:
            return self._reject(intent.intent_id, exc)

    def register_request(self, request):
        require(not self.halted and self.intent is not None and not self.intent.abstain,
                "no actionable intent", "NO_ACTIVE_INTENT")
        validate_identity(self.identity, request.candidate_set.identity)
        require(self.now_ns < request.deadline_monotonic_ns <= self.intent.expires_monotonic_ns,
                "request/intent deadline", "PROPOSAL_EXPIRED")
        require(request.deadline_monotonic_ns <= request.candidate_set.generated_monotonic_ns
                + int(self.config["proposal_ttl_s"]*1e9), "request extends configured budget")
        # Projection is used by the actual model request path, not only in isolated tests.
        payload = dict(thaw(request.structured_context))
        identity = request.candidate_set.identity
        payload.update(request_id=request.request_id, intent_id=identity.intent_id,
                       intent_generation=identity.intent_generation,
                       candidate_set_id=request.candidate_set.candidate_set_id,
                       candidate_hash=request.candidate_set.candidate_hash,
                       source_snapshot_id=request.candidate_set.source_snapshot_id,
                       target_track_id=identity.target_track_id, target_track_generation=identity.target_track_generation,
                       feature_id=identity.feature_id, feature_generation=identity.feature_generation,
                       stage=self.intent.stage, operation=self.intent.operation,
                       deadline_monotonic_ns=request.deadline_monotonic_ns,
                       proprio=self.backend.read_proprioception().to_dict(),
                       candidates=[project_candidate(c, synthetic_condition=self.config["condition"] == "synthetic_p0")
                                   for c in request.candidate_set.candidates])
        observation = PolicyObservation.from_mapping(payload)
        require(request.request_id not in self.requests or canonical_json(self.requests[request.request_id]) == canonical_json(request),
                "request ID conflict")
        self.requests[request.request_id] = request
        self._emit("candidate_set", request.candidate_set.semantic_payload())
        self._emit("model_input", observation.payload)
        return observation

    def accept_proposal(self, proposal):
        try:
            if self.monotonic_clock is not None:
                self.now_ns = max(self.now_ns, self.monotonic_clock())
            require(not self.halted and self.intent is not None and not self.intent.abstain,
                    "no actionable intent", "NO_ACTIVE_INTENT")
            require(proposal.request_id in self.requests, "request gone/cancelled", "REQUEST_CANCELLED")
            require(self.now_ns < self.intent.expires_monotonic_ns, "intent deadline", "INTENT_EXPIRED")
            content = canonical_json(proposal)
            if proposal.decision_id in self.decisions:
                require(self.decisions[proposal.decision_id] == content, "decision ID conflict")
                return False
            require(proposal.request_id not in self._request_decisions, "request already answered", "REQUEST_CONSUMED")
            require(proposal.calibrated_confidence is None,
                    "P0 has no registered action-confidence calibration", "UNCALIBRATED_CONFIDENCE")
            request = self.requests[proposal.request_id]
            contract = instantiate_contract(
                request, proposal, latest=self.validation_context(self.now_sim, self.now_ns),
                contract_id=f"contract/{proposal.decision_id}", now_sim_time_s=self.now_sim,
                now_monotonic_ns=self.now_ns, controller_config_id=self.policy_config_revision,
                contact=self.intent.stage == "INTERACT",
                contact_translation_limit_m=self.config["contact_translation_m"],
                segment_duration_s=self.config["segment_duration_s"],
                segment_translation_limit_m=self.config["segment_translation_m"],
                segment_rotation_limit_rad=self.config["segment_rotation_rad"],
            )
            self.control.send(ControlEvent(contract.contract_id, "contract", contract, contract.expires_monotonic_ns))
            self.decisions[proposal.decision_id] = content
            self._request_decisions[proposal.request_id] = proposal.decision_id
            self._emit("proposal", proposal)
            return True
        except ProtocolError as exc:
            return self._reject(proposal.decision_id, exc)

    def receive_model_result(self, result):
        """Untrusted worker replies re-enter validation; no model may extend time."""
        try:
            canonical_json(result)
        except ProtocolError:
            self._emit("invalid_model_result", {"raw_output_repr":repr(result)})
        else:
            self._emit("raw_model_result", result)
        try:
            require(isinstance(result, dict) or hasattr(result, "get"), "worker result object", "INVALID_OUTPUT")
            require(result.get("error") is None, str(result.get("error")), "MODEL_ERROR")
            output = dict(thaw(result["output"]))
            if output.get("protocol") == "embodied.protocol/1":
                env = Envelope.from_mapping(output)
                require(env.message_type == "ActionProposal", "wrong reply type")
                require(env.clock_domain == self.clock_domain, "model clock domain", "CLOCK_DOMAIN_MISMATCH")
                require(env.emitted_monotonic_ns <= self.now_ns, "future model result", "INVALID_CLOCK")
                require(env.payload.get("request_id") in self.requests, "cancelled request", "REQUEST_CANCELLED")
                request = self.requests[env.payload["request_id"]]
                prior = request.candidate_set.identity
                p = thaw(env.payload)
                # Episode/goal come from the envelope; calibration lineage belongs
                # to the registered request, not model-generated physical facts.
                p["identity"] = dict(episode_id=env.episode_id, episode_generation=env.episode_generation,
                                     goal_generation=env.goal_generation,
                                     intent_id=p.pop("intent_id"), intent_generation=p.pop("intent_generation"),
                                     target_track_id=p.pop("target_track_id"),
                                     target_track_generation=p.pop("target_track_generation"),
                                     feature_id=p.pop("feature_id"), feature_generation=p.pop("feature_generation"),
                                     calibration_versions=prior.calibration_versions)
                output = p
            require(output["request_id"] == result["request_id"], "worker/result identity", "INVALID_OUTPUT")
            output["identity"] = ContextIdentity(**output["identity"])
            proposal = ActionProposal(**output)
        except (ProtocolError, TypeError, KeyError, ValueError) as exc:
            error = exc if isinstance(exc, ProtocolError) else ProtocolError("INVALID_OUTPUT", str(exc))
            return self._reject(result.get("request_id", "unknown") if hasattr(result,"get") else "unknown", error)
        return self.accept_proposal(proposal)

    def cancel(self, reason="CANCELLED", *, event_id=None):
        if event_id is not None and event_id in self._cancel_ids:
            require(self._cancel_ids[event_id] == reason, "cancel ID content changed", "CONTROL_ID_CONFLICT")
            return False
        if event_id is not None:
            self._cancel_ids[event_id] = reason
        # Invalidation is out of band: never wait behind a model or full queue.
        self.servo.cancel(reason, sim_time_s=self.now_sim, monotonic_ns=self.now_ns)
        self.intent = None
        self.requests.clear()
        self._brain_requests.clear()
        self.identity = replace(self.identity, goal_generation=self.identity.goal_generation+1)
        for worker in self.workers:
            worker.discard_pending()
        # Queued motion has already been revoked; acknowledge its cancellation.
        for key in list(self.control.pending):
            self.control.ack(key)
        key = event_id or f"cancel/{self.identity.goal_generation}"
        self.control.send(ControlEvent(key, "cancel", {"reason": reason}, self.now_ns+100_000_000))
        self.control.ack(key)
        self._emit("cancel", {"event_id": key, "reason": reason, "goal_generation": self.identity.goal_generation})
        return True

    def reset(self, identity):
        require((identity.episode_id, identity.episode_generation) !=
                (self.identity.episode_id, self.identity.episode_generation), "reset requires new episode identity")
        self.cancel("RESET")
        self.identity = identity
        self.control.reset()
        self._intent_history.clear()
        self.servo.seen.clear()
        self.servo.decisions.clear()
        self.decisions.clear()
        self._request_decisions.clear()
        self._cancel_ids.clear()
        self.halted, self.stop_reason = False, None
        self._episode_start = None
        self.now_sim = 0.

    def apply_stage_evidence(self, evidence):
        require(self.intent is not None and evidence.intent_id == self.intent.intent_id
                and evidence.stage == self.intent.stage
                and evidence.predicate_id == self.intent.completion_template_id, "stage evidence identity")
        require(bool(evidence.source_snapshot_ids), "stage evidence sources")
        latest = self.validation_context(self.now_sim, self.now_ns)
        require(all(s == latest.snapshot_id or s in latest.lineage_source_ids for s in evidence.source_snapshot_ids),
                "stage evidence lineage", "HISTORY_MISSING")
        self._emit("stage_evidence", evidence)
        if evidence.result == "SATISFIED":
            self.cancel("STAGE_COMPLETED")  # Requests a new intent; no hard-coded next phase.

    def tick(self, *, sim_time_s, monotonic_ns):
        if self.monotonic_clock is not None:
            monotonic_ns = max(monotonic_ns, self.monotonic_clock())
        require(sim_time_s >= self.now_sim and monotonic_ns >= self.now_ns, "regressing scheduler clock")
        self.now_sim, self.now_ns = sim_time_s, monotonic_ns
        if self._episode_start is None:
            self._episode_start = (sim_time_s, monotonic_ns)
        if self.halted:
            self.backend.hold()
            return None
        try:
            if (sim_time_s-self._episode_start[0] >= self.config["episode_sim_s"]
                    or monotonic_ns-self._episode_start[1] >= int(self.config["episode_wall_s"]*1e9)):
                self._fail("EPISODE_BUDGET")
                return None
            if self.intent and (monotonic_ns >= self.intent.expires_monotonic_ns
                                or sim_time_s-self._intent_started_sim >= self.intent.max_duration_sim_s):
                self.cancel("INTENT_EXPIRED")
            self.control.check(monotonic_ns)
            for event in list(self.control.pending.values()):
                try:
                    if event.kind == "contract":
                        require(self.intent is not None, "no active intent", "INTENT_REPLACED")
                        validate_identity(self.identity, event.payload.identity)
                        self.servo.install(event.payload, sim_time_s=sim_time_s, monotonic_ns=monotonic_ns)
                    self.control.ack(event.event_id)
                except ProtocolError as exc:
                    self.control.ack(event.event_id)
                    self._reject(event.event_id, exc)
            result = self.servo.tick(sim_time_s=sim_time_s, monotonic_ns=monotonic_ns,
                                     duration_s=1/self.config["control_hz"])
            if result:
                event = ControlEvent(f"feedback/{result.contract_id}", "feedback", result, monotonic_ns+100_000_000)
                self.control.send(event)
                self.control.ack(event.event_id)  # Local sink delivery is synchronous/reliable.
            return result
        except ProtocolError as exc:
            self._fail(exc.code)
            return self._reject("scheduler/tick", exc)
        except Exception:
            self._fail("RUNTIME_FAILURE")
            raise

    def close(self):
        states, errors = [], []
        try:
            self.cancel("SHUTDOWN")
        except Exception as exc:
            errors.append(exc)
        for worker in self.workers:
            try:
                states.append(worker.close())
            except Exception as exc:
                errors.append(exc)
        try:
            self.backend.close()
        finally:
            self.halted = True
        if errors:
            raise ProtocolError("SHUTDOWN_FAILURE", repr(errors))
        return states
