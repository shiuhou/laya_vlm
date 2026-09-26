# Prospective independent Task2 BOX-support review

**PASS for `277842bff8d21c4fba47f152dadf6120b0118dbf` before inference.** The approved scope is one previously inspected initial RGB fixture, one LocateAnything BOX call on GPU 0 with at most 256 generated tokens and no retries, followed by sealed sensor support and separate archived-mask proxy evaluation. It does not include a new scene, render, simulation, point call, segmentation fallback, grasp geometry or action decision.

The model path is pinned to archived checkpoint content identity `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`; I independently found that identity in the prior coarse source manifest. The producer checks current local bytes before model loading. Model inputs contain only the original full RGB and exact existing BOX prompt. Input pixels/tokens, generation settings, raw response and observed generated token sequences are retained. A reviewed fix seals the returned generation before token-audit or parser rejection, preserving failed-attempt evidence. Admission requires one complete valid BOX, terminal EOS and 1–256 generated tokens.

The pure sensor function rejects extra input fields. P preserves the current provider's integer conversion, clipped one-fifth interior crop, valid-depth range, median depth and original box-center ray. G retains exactly the same valid support, with explicit raster-center `+0.5` backprojection; it does not silently change P. Both median rank contributor sets retain all exact-value ties. No evaluator labels, filtering, clustering or shape prior changes the crop or point.

Only after immutable model/sensor sealing and source recomputation does the evaluator open the archived ID-rendered mask. Its overlap, center membership, median-contributor agreement and fixed one-pixel interior/boundary/exterior strata remain proxy comparisons. They are not exact resolved-depth ownership or calibrated semantic confidence, and never clean the sensor support. The code adds no jaw-span or pre-grasp fit computation.

I independently ran the focused tests under the LocateAnything environment: **8 passed**, covering exact provider parity, clipping, empty support, median ties, coordinate convention, malformed/multiple/truncated BOX rejection, budget/EOS rejection, exhaustive proxy strata and schema exclusion of gold. I also performed an **actual frozen-input import/schema preflight**: verified the pinned NPZ hash; RGB uint8 384×384×3; depth float32 384×384; K/T shapes; exact prompt; and frozen hybrid/greedy/256-token settings. This preflight did not load the model, compute outcome-sensitive support, open masks, render or run physics.

| Reviewed file | SHA-256 |
| --- | --- |
| `embodied_runtime/experiments/task2_box_support.py` | `8a53c9fc20f292e5b871c1d2801a867f96d88ba02dc3c707e6b53e35030f139e` |
| `docs/research/task2_initial_grasp_geometry_proposal.md` | `84e9122340d2645e80c7714756ad630421718be92d85a389b099f99421639014` |
| `tests/test_task2_box_support.py` | `9cd3ffe85d350937376b78228da2476d16afead6f9fd174a3cd5415c5cb8b137` |

Any positive result can support a later bounded geometry test only. Object shape/extent, orientation, jaw fit, holding, approach qualification and generalization remain outside this experiment.

## Pre-inference metadata serialization amendment

**Technical PASS for `af94e309893ec11cc53ee18ab0d39eb0e011e947`.** Setup attempt 01 failed while serializing the processor's NumPy image-grid metadata, before `call_started`. The independent journal check found five valid chained records, SHA-256 `beca3ce339b2764f6c05f6f38ae6db5d6bab42362f2e2ffa3d7d1be5b799db3d`, ending with `model_calls_started=0` and `AttributeError: numpy.ndarray has no attribute detach`. It remains a failed setup attempt; the fixed one-call scientific budget was not spent.

The reviewed one-line correction serializes either native tensor or NumPy metadata. It does not change the image-grid object passed to the model, model inputs/settings, feature rules, masks or inference count. The source SHA-256 is now `79483613405e15bb463e19e3bc190b4bb0855715cfb3c07e681bca8d00179bd4`; protocol and test hashes above are unchanged.

The earlier frame-only preflight missed this processor-output schema. The reviewer now ran the actual local AutoProcessor on the fixed RGB/prompt without loading model weights or calling inference: native grid is NumPy `[[28,28]]`, the prompt has 237 input tokens, and the corrected serialization succeeds. The producer must retain attempt 01 and use the separately authorized numbered continuation; this amendment does not authorize a second inference or any retry after an inference outcome.

## Final processor-preflight freeze

**Final PASS for `ba7ab2e6d58932cef893f4d3549cd550279b2d65`.** The diff from the preceding reviewed amendment factors metadata serialization into the pure `grid_metadata()` helper, adds an actual processor-only preflight mode and a native NumPy schema test, and appends the failed-setup account to the protocol. The processor-only preflight stops before model construction or inference. No prompt, checkpoint, decoding setting, feature, mask, or scientific condition changes. The producer reports nine focused tests passing; the reviewer previously ran the original eight and independently exercised the actual NumPy processor schema above.

The final source, protocol, and test SHA-256 values are respectively `9986c4f79578dd4e2691726f21df7ba0706ac8b9876a255ca078eed2f9bb43a6`, `8476959edc85bd60750b233e76404fdb1b723b679075aa1393559d06ca0a5efd`, and `5ed93df4723ebded1c8efed99d8fd3d0239f96fbac123c404d5536799ac3f5ee`. Attempt 02 may proceed under the parent's existing authorization. The one inference remains unspent at this review; attempt 01 and the reviewer preflight miss remain part of the evidence.
