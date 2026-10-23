# Independent clean-context delta re-review — PASS

- Date: 2026-10-23. Reviewer: `v50_delta_review3_claude_subagent`. Read-only, no prepare/Qwen/endpoint calls. No repo file was edited. The simulations ran only in the session scratchpad: a FakeClient, or the real `d1_client.Client` over `httpx.MockTransport`, with real file hashes. Only verify, approval_matches and quota were patched.
- Sources reviewed: `flow_common.digest(revision.sources())` = `fe9a9b2574bfb95883cd1072de9cf4a9f58d9580fe359cc2061cded96628d491` over 64 files. This is HEAD d979262 plus the uncommitted diff to CHANGELOG, PREREG, d1_client, revision, revision_protocol and test_revision. The digest was unchanged after the tests ran, and `out/.../revision8` does not exist.
- EVALUATION.md sha256 observed: `71975d7a79908d8c458a355fc9cb8954de9072519a3408e9c26f6e242c69414c` (matches the pin; the file is unchanged).
- CPU suite: 40 run, 40 pass, 0 fail, 0 error.

## CODE_REVIEW2 items
- **MF1 (launch record before the first quota check): FIXED.**
  - revision.py:213-216 writes `launches/launchN.json` before `quota(root)` at :217. It stores the hash of the bytes read at :171 and their strict UTF-8 text.
  - Test :408 and my own simulation: a stop at the first check, then renewal B, a mid-run stop, then renewal C, completes with 24 unique calls. Checkpoints 0000/0001 stay byte-identical, and launch0..2 hold the exact approval bytes.
- **MF2 (real-hash regressions): FIXED.** Tests at test_revision.py:408, :426 and :458 cover accepted and chained renewal, tampered, removed and forged launch records, artifact drift, a non-window change, an expiry that is not later, deleted or edited status, a non-quota stop and the line-194 case. Each rejection leaves the call count, checkpoint count and status bytes unchanged. My line trace over these 4 tests executes every code line of revision.py:171-217; only the comment lines 170, 188, 189 and 212 are not hit.
- **N1: adopted and correct.** A first launch (none of status, checkpoints or launches present) passes. A legitimate quota resume passes, because the status equals checkpoint['state'] written from the same dict. A completed run is refused. One residual is listed as R1 below.
- **N2: adopted.**
  - :200-204 compares everything except endpoint_window against the archived predecessor and requires a strictly later expiry.
  - The predecessor is safe to read: a launch record is written only after the window has been validated (:164-169).
  - One residual is listed as R2 below.
- **N3: adopted.** Simulated a CRLF plus non-ASCII approval: renewed twice, it completes with 24 calls; previously it failed closed. A non-UTF-8 approval fails before any state is written.
- **N4: correct.**
  - d1_client.py:150-152 raises InputOverCap after the cached or guarded tokenizer call and before the completion `before_request`, `wire_request` and `attempt.json`.
  - revision.py:146-154 records `raw=None` and `protocol.unavailable('input_over_cap')`. `slots()` reports input_over_cap, and the run continues.
  - final_packet (:132) gives both arms `initial_response=None` with the same admission. Only tool_feedback differs: the tool arm gets an empty table.
  - Simulated resume with the real Client: the E3 tool final and E6 initial are over cap, with a quota stop right after E6 initial, then a renewal. Run 2 sends 1 models GET, 20 tokenize calls and 20 completions. The over-cap slots replay from the token cache with no HTTP, no 'already consumed' error and no cap hit. There are 22 attempts in total, raw/tool parity holds, and a rerun is refused as terminal.
  - This is consistent with Amendment 2 and with EVALUATION.md ("Missing calls ... remain failures in denominator8").
- **N5/N6:** registered in PREREG Amendment 2 (documentation only). **N7:** parity and arm alternation (:231) are unchanged.
- **CODE_REVIEW1 (a)-(e): no regression.**
  - The guard runs before every models, tokenize and completion HTTP call and before each reservation.
  - Metadata ledgers and no-retry are unchanged.
  - The unknown-concept compatibility flag is still None.
  - The EVALUATION pin is still at :76, :92 and :104.
  - Checkpoints and launch records are immutable, and quota snapshots are append-only.

## Must-fixes (BLOCKING)
None.

## Non-blocking notes
- **R1. The resume gate keys only on status, checkpoints and launches (revision.py:175).**
  - Simulated: after an endpoint_window_expired stop with 1 received slot, I deleted all three and renewed the approval. The run then sent 21 never-attempted slots.
  - Attempted slots stay protected by `calls/*/attempt.json` and the token/metadata records (d1_client.py:125-126, :146-147).
  - Hardening: also trigger the gate on transport/, artifacts/, requests/, quota_checks/ or slots.json.
- **R2. A mid-run edit of launch_approval.json skips the N2 check.**
  - before_http and verify never re-check the launch approval. A quota-stop checkpoint therefore records the edited hash, and the resume takes the non-renewal path (:187).
  - Simulated: `review_sha256` was swapped mid-run, then accepted on resume and archived as launch1.
  - approval_matches and freeze_sha256 still pin sources, the review file, the rubric and the freeze.
  - Hardening: at resume, require the latest launch record's `approval_sha256` to equal the checkpoint's `launch_approval.json` hash.
- **R3. Validation and archive use different reads.** The approval is validated from the read at :161 and archived from the read at :171, a tiny race window. Add `strict_json(approval_text) == approval`.
- **R4. "Nothing is sent" is inaccurate.** PREREG Amendment 2 says so, and the record writes `http_sent: False` (revision.py:151). But the slot's /tokenize metadata request is sent and recorded (d1_client.py:127-133); only the completion is never sent. Rename the field to `completion_sent` or clarify it in reports. Also, an over-cap final makes the transitions record (:237) list every initial ID as "removed". That is syntactic only and must not be read as a revision loss.
- **R5. Quota-helper failure is terminal (pre-existing, not a regression).** A nonzero exit, timeout or bad JSON from the helper (:110-111) stops the run as controller_failure, not as the resumable `quota_at_or_below15_or_unknown`. It fails closed; consider registering this.
- **R6. Optional regression.** Add a test for resume with over-cap slots under the real Client, mirroring the simulation above.

## Parent disposition (Claude, 2026-10-23, after reading this review; not reviewer text)

PASS accepted at digest fe9a9b25…; source is NOT changed after review, so the
approved digest is the frozen one. R1–R3 need an operator to delete/edit run-root
files; launch procedure: never delete/edit anything under revision8/ except a
whole-file launch_approval.json renewal after a quota stop. R4 reporting rule:
`http_sent: false` means the completion request was never sent; the slot's
/tokenize metadata request was sent and is in metadata_calls/. Over-cap final
transitions listing initial IDs as removed are syntactic, never a revision loss.
R5: helper failure = terminal controller_failure, fail closed, needs user
instruction to continue. R6 covered by the reviewer's simulation, not a suite test.
