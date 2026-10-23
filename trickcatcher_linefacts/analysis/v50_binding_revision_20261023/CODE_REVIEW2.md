# Independent clean-context re-review — REQUEST CHANGES

- Date: 2026-10-23. Reviewer: `v50_rereview_claude_subagent`. Read-only, no prepare/Qwen/endpoint calls. No repo file was edited. The scratch simulations ran only in the session scratchpad, importing revision.py with verify, approval_matches, quota and Client patched.
- Sources reviewed: sha256(json.dumps(revision.sources(), sort_keys=True)) = `86bec5d806239e5d7ced6040b16a1df7e90674e1b13b0852e10d5c698420c482` over 64 files. This matches HEAD d979262, has no working-tree diff, and is unchanged after the test run.
- EVALUATION.md sha256 observed: `71975d7a79908d8c458a355fc9cb8954de9072519a3408e9c26f6e242c69414c` (matches the pinned value).
- CPU suite: 36 run, 36 pass, 0 fail, 0 error.

## Approval renewal (revision.py:163-189): verdict
The logic is correct wherever it runs. I simulated it with real file hashes, not the patched `sha`:
- Renewal after a mid-run quota stop: the run completes with 24 unique calls, checkpoint 0000 is byte-identical, and launch0 keeps the old approval bytes.
- A forged extra `launches/launch9.json` is rejected with quota_checkpoint_drift.
- A tampered archived launch0 is rejected with prior_launch_approval_not_archived.
- Renewal combined with artifact drift or a freeze.json change is rejected with quota_checkpoint_drift.
- A non-quota stop (endpoint_window_expired) is rejected with terminal_run_no_automatic_retry.

approval_matches, the freeze_sha256 check and verify(full) still pin sources, dependencies, parents, pools, slots, rubric and freeze. Attempted or unknown completion, tokenizer and preflight attempts are never re-sent (d1_client.py:44-45, 118-119, 139-140).

## Must-fixes (BLOCKING)
1. **Renewal hits a dead end after a quota stop at the first quota check.**
   - Cause: `quota(root)` at revision.py:194 runs before the launch record is written (lines 200-203). A stop there leaves the launch_approval.json then in force unarchived, so every later renewal raises prior_launch_approval_not_archived.
   - Simulated (a): the first run stops at line 194, then the renewal is refused.
   - Simulated (b): run0 stops mid-run, approval renewed to B; run1 stops at line 194; renewing to C is refused, with 1 received slot already on disk.
   - Consequence: recovery would need a code change, which is source drift against the immutable freeze.
   - Fix: compute launch_id and write `launches/launchN.json` with the exact validated approval bytes as the first statement inside `try`, before line 194. Every run that can end in a quota checkpoint then archives its approval.
2. **The renewal regression never exercises the renewal branch.**
   - Cause: test_revision.py:354 patches `app.sha` to return `'x'`, so every fingerprint from files() is `'x'`. The old and current approval hashes compare equal, so lines 176-187 never run (confirmed by line tracing). The checkpoint drift check then compares only file names.
   - Fix: add real-hash regressions that patch only verify, approval_matches, quota and Client. Cover:
     - renewal accepted;
     - no archived predecessor;
     - forged or tampered launch record;
     - renewal plus drift in another file;
     - renewal after a non-quota stop;
     - the line-194 case from must-fix 1.

## CODE_REVIEW1 must-fixes, re-verified
(a) **Guard before every HTTP call, before its attempt is reserved.** The guard runs before the models preflight (d1_client.py:46-47), tokenize (120-121) and the completion after the tokenizer (148-151). It checks verify (sources, dependencies, pools, rubric), quota and window expiry (revision.py:195-199). Tested by test_http_guard_stops_before_completion_reservation. OK.

(b) **Durable metadata attempts, cache and no retry.** The models preflight is cached per launch ID, and an unknown preflight attempt is consumed, never retried (d1_client.py:36-55). Metadata calls have a ledger with a redacted raw body and hash (67-72, 85-92, 105-111). Tested by the cache/resume-preflight, unknown-models and transport no-retry tests. OK. A metadata call left in state 'started' blocks later calls, but that path is untested.

(c) **concept=unknown is not called vocabulary-incompatible.** revision_protocol.py:83-89 sets the compatibility flag to None, and identify_tools maps RELATION_CONCEPTS['unknown'] to all concepts. Tested. OK.

(d) **EVALUATION hash pinned.** It is checked in approval_matches (revision.py:76) and stored and checked in freeze/verify (92, 104). Freeze-side drift is tested. The approval-side check is untested because approval_matches is patched in every lifecycle test. OK.

(e) **Immutable checkpoints, append-only quota snapshots.** Checkpoints are written immutably (revision.py:235) and quota snapshots are append-only (112-113). Tested. OK.

## Non-blocking notes
- **N1. Deleting status.json skips the terminal gate (revision.py:164).** Simulated: after a non-quota stop, deleting status.json lets the run send all remaining never-attempted slots. Resume should key off existing checkpoints/launches and require status to equal the latest checkpoint state.
- **N2. Renewal accepts any byte change.** It does not check that only endpoint_window changed or that expires_utc is later, and review_path/review_sha256 can be swapped. Scientific inputs stay pinned, so this is hardening only.
- **N3. Archive encoding and read race.**
  - The archive stores read_text() output (locale decoding plus newline translation) but is compared against a byte hash (line 183). Approvals with CRLF line endings or non-UTF-8 bytes therefore fail closed.
  - Line 154 validates one read of the approval and line 203 archives a second read. Store the validated bytes once and compare against approval_sha256.
- **N4. Input-token cap can stop the tool arm only.**
  - My estimate on the frozen pools uses a regex word/punctuation count as a stand-in for tokens. A final tool packet is about 3.6-3.8k with a short initial response. The feedback table makes it about 1-1.5k larger than the raw packet.
  - An initial response near 1536 tokens (for example a truncated one) could push the tool final past 6144. That causes an input_token_cap terminal stop, hitting the tool arm only and halting all later episodes.
  - Pre-register how this case is handled, or bound it at preparation.
- **N5. Window expiry mid-run is terminal by design (PREREG:76-77).** Set expires_utc for the worst case: 24 serialized calls with a 3600 s timeout each, plus metadata calls.
- **N6. admit() strips one ```json fence (revision_protocol.py:49-50).** It is symmetric across arms and is not a repair, but it is not declared in PREREG or EVALUATION.
- **N7. PREREG parity holds.**
  - Raw and tool finals differ only in tool_feedback (revision_protocol.py:117-131, and tested).
  - Items are admitted independently, and a truncated response stays unavailable.
  - Transport failures are not retried.
  - Arm order alternates by episode.
