from dataclasses import asdict, replace

import pytest

from embodied_runtime.contracts import ProtocolError, canonical_json
from embodied_runtime.router import MessageRouter
from embodied_runtime.runtime_core import BeliefStore, ObservationEvent
from test_protocol import envelope


def router():
    store = BeliefStore("ep", allow_delayed=True)
    r = MessageRouter("ep", 1, 1, "host/boot")
    def validate(p):
        if set(p) != {"position_m"}:
            raise ProtocolError("INVALID_SCHEMA", "geometry fixture")
    def ingest(e):
        return store.ingest(ObservationEvent(e.producer, "ep", e.producer_seq,
                           e.reference_sim_time_s, 0., dict(e.payload)), now_sim=.3)
    r.register_handler("GeometryObservation", ingest, validator=validate)
    return r, store


def state(store):
    return (store.revision, store.reference_time, canonical_json(asdict(store.admission.stats)),
            repr(store._latest))


def test_ingress_rejections_do_not_mutate_belief():
    r, store = router()
    assert r.receive(envelope(), 100).status == "ACCEPTED"
    before = state(store)
    for bad in [replace(envelope(), episode_generation=2), replace(envelope(), goal_generation=2),
                replace(envelope(), clock_domain="other"), replace(envelope(), payload={"x": 1})]:
        assert r.receive(bad, 200).status == "REJECTED"
        assert state(store) == before
    assert r.receive(envelope(), 200).status == "DUPLICATE"
    assert state(store) == before


def test_oosm_and_independent_producer_sequences():
    r, store = router()
    assert r.receive(envelope(producer_seq=2, message_id="a2", reference_sim_time_s=.2), 100).status == "ACCEPTED"
    assert r.receive(envelope(producer_seq=1, message_id="a1", reference_sim_time_s=.1), 110).status == "ACCEPTED"
    assert r.receive(envelope(producer="other", producer_seq=1, message_id="b1"), 110).status == "ACCEPTED"
    assert store.revision == 3


def test_frame_request_identity_and_expiry():
    r, _ = router()
    seen = []
    r.register_handler("SemanticObservation", lambda m: seen.append(m), validator=lambda p: None)
    r.register_frame("f", camera_id="cam", frame_seq=1, calibration_version="cal1",
                     capture_sim_time_s=0., frame_ref="frames/f.npy")
    expected = dict(camera_id="cam", frame_seq=1, calibration_version="cal1", query_generation=2)
    r.register_request("req", message_type="SemanticObservation", deadline_monotonic_ns=200,
                       expected=expected, source_ids=("f",))
    msg = envelope(message_type="SemanticObservation", payload={**expected, "request_id":"req"}, source_ids=("f",))
    assert r.receive(replace(msg, payload={**msg.payload, "calibration_version":"cal2"}), 110).status == "REJECTED"
    assert not seen
    assert r.receive(msg, 200).rejection.reason_code == "PROPOSAL_EXPIRED"
    assert r.receive(msg, 150).status == "ACCEPTED"
    r.reset("new", 2, 1, "host/boot")
    assert not r.requests and not r.frames
    assert r.receive(msg, 201).rejection.reason_code == "WRONG_EPISODE"


def test_sequence_reuse_and_unregistered_type():
    r, _ = router()
    assert r.receive(envelope(), 100).status == "ACCEPTED"
    assert r.receive(replace(envelope(), message_id="different"), 100).rejection.reason_code == "SEQUENCE_CONFLICT"
    assert r.receive(envelope(message_type="Bogus", producer_seq=2, message_id="b"), 100).status == "REJECTED"


@pytest.mark.parametrize("message", [None, [], {"wrong":1}])
def test_malformed_ingress_is_recorded(message):
    r, _ = router()
    assert r.receive(message, 1).status == "REJECTED"
