# P1 tracker episode repair — bounded continuation

User authorized correcting the harness episode ID and independently replaying
tracker initialization after the `0d25216` checkpoint. Register this before the
new attempt. The preceding WRONG_EPISODE failure remains preserved.

The only behavioral implementation change is to construct the offline tracker
with `view["episode_id"]`, taken from the immutable recorded sensor view. Do not
rewrite a frame identity, relax the tracker episode guard or fabricate a new
capture. Semantic typed contract, query/checkpoint, raw replies, independent BOX
ROI, selected POINT, reviewed surface, inventory seed and all geometry/tracker
settings remain fixed. Use the existing pinned development RGB/support review.

Run the same sealed init25 wrist drawer-front inputs into a fresh directory,
at a clean identifiable revision; persist the exact command, source/inference/
review hashes and process output. One initialization attempt, no new inference,
no robot actions. Stop on UNKNOWN/AMBIGUOUS association, missing support-contained
rectangle, non-TRACKED initialization or runtime failure. No automatic retry.

If TRACKED, inspect the saved feature/rectangle and actual RGB/depth evidence.
This is static offline initialization using capture-clock timestamps, not
continuous tracking, live freshness, generalization or push-safety acceptance.
Then assess independent fixed cabinet reference observability from existing
sealed reference evidence and original RGB only. The earlier non-EOS reference
reply remains inadmissible; do not extract its point prefix, run geometry on it,
or substitute a visually chosen surface. No reference inference retry, query
change, larger token limit, human-label seed or official success is authorized.
If reference cannot be established, report UNKNOWN and stop before VERIFY/PUSH.

Only the actual sealed-input replay and targeted lint are required for this
one-line harness correction; no broad regression suite or new synthetic tests.
Preserve canonical success/failure inputs and artifacts; do not duplicate full
models or historical datasets in the new evidence bundle.
