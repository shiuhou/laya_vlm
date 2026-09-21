from embodied_runtime.runtime_core import BeliefStore, CandidateBuilder, FakeBackend, RuleProvider, ObservationEvent, AtomicExecutor


def main() -> None:
    backend = FakeBackend()
    store = BeliefStore("fake")
    provider = RuleProvider()
    executor = AtomicExecutor(backend)
    for seq in range(5):
        event = ObservationEvent("proprio", "fake", seq, seq * .05, seq * .05,
                                 {"gripper_command": "OPEN", "holding": None, "aligned": False})
        store.ingest(event, now_sim=seq * .05)
        snapshot = store.snapshot(seq * .05)
        snapshot = store.snapshot(seq * .05, CandidateBuilder().build(snapshot))
        decision = provider.decide(snapshot)
        print(seq, decision.token, executor.execute(decision.token))


if __name__ == "__main__":
    main()
