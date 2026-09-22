"""Same-provider, same-question, same-candidate paired decision diagnostic CLI."""
import argparse
from pathlib import Path

from ..runtime_core import RuleProvider, load_laya_provider
from .equivalence import replay_pair
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs_jsonl")
    ap.add_argument("--output", required=True)
    ap.add_argument("--provider", choices=["rule", "laya", "both"], default="both")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    args = ap.parse_args()
    rows, diagnostics = load_records(args.pairs_jsonl)
    if diagnostics:
        raise ValueError("incomplete collection log; inspect before replay")
    if not any(r["kind"] == "termination" and r["data"].get("reason") == "collection_smoke_complete" for r in rows):
        raise ValueError("collection has no successful completion; preserve and inspect failed attempt")
    pairs = [r["data"] for r in rows if r["kind"] == "paired_state"]
    if not pairs or len(pairs) > 16 or not 2 <= args.repeats <= 10:
        raise ValueError("bounded smoke only: 1..16 pairs, 2..10 repeats")
    recorder = RunRecorder(args.output, {**vars(args), "source_sha256": file_hash(args.pairs_jsonl),
                                        "oracle": True, "purpose": "diagnostic_state_gap_not_policy_evaluation",
                                        "seed_scope": "once before model load, not before each inference"},
                           {"run_id": Path(args.output).name, "code": code_identity(), "versions": versions()})
    try:
        providers = [RuleProvider()] if args.provider in ("rule", "both") else []
        if args.provider in ("laya", "both"):
            import torch
            torch.manual_seed(args.seed)
            recorder.manifest_update({"models": {"laya": model_identity(args.laya_path)}, "inference": {
                "api": "LayaProvider.agent.system_one", "seed": args.seed, "device": args.device,
                "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                "cuda_version": torch.version.cuda, "gpu": torch.cuda.get_device_name(args.device)}})
            providers.append(load_laya_provider(args.laya_path, subfolder=None, device=args.device))
        for pair in pairs:
            recorder.record("paired_state", pair)
            for provider in providers:
                replay_pair(pair, provider, recorder, repeats=args.repeats)
        recorder.record("termination", {"reason": "equivalence_smoke_complete", "pairs": len(pairs),
                                         "providers": [type(p).__name__ for p in providers], "executed_actions": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "replay_error", "exception": repr(exc)})
        raise
    finally:
        recorder.close()
    print(args.output)


if __name__ == "__main__":
    main()
