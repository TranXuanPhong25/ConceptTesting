# Continuation, 2026-10-27

Original retrieve/judge/client scripts, frozen messages and raw outputs stay unchanged.
113 retrieval and 112 judge responses exist; no completion has unknown usage.
One judge (HumanEval/15) was blocked before reservation by context length. Its
validated witness includes duplicate long value/repr strings. For this one missing
judge only, present long serialized values as length, SHA256, and first/last 160
characters; remove duplicate repr fields. Keep source/reference/cards/bindings
unchanged and explicitly mark omitted witness data. Save both job versions.
Use the original judge seed/token budget; this is not a retry of an inference.
Then run the original frozen 120 utility requests and independent native grading.
No new model or paid fallback. Original cap356 remains; main ledger228 +121=349,
plus four canaries and one review =354 total. No further completion keepalives.

Saved-output engineering analysis is explicitly post hoc. Before scoring any
new ranking, freeze these generic variants: (a) deduplicate catalog IDs, keeping
first complete row, passing all other original parser checks; (b) interleave up
to three unique concept IDs in order Qwen rank1, v2 rank1, Qwen rank2, v2 rank2,
Qwen rank3, v2 rank3. Use v2 fallback on invalid/empty Qwen output. No gold,
reference, witnesses or grader outputs enter ranking. Report original v3 scores
alongside derived variants; previous audit is not a new holdout. Do not promote
on these labels alone. No extra inference for derived variants.

A manual native audit will include specifically selected alleged false bugs and
positive controls, replayed against official contract/reference/PUT. It diagnoses
errors, not an unbiased estimate of overall precision. Native equality on one
example alone cannot prove a card irrelevant; source/spec reasoning accompanies it.
Missing utility must be reported pending, never as a measured zero success rate.

## Cache/lifecycle correction during utility execution

The original content-addressed client keys by messages/seed, not arm name.
When two arms have identical concept hints (including empty hints), their requests
are exactly identical. Concurrent submission reserves one request; the other
rejects the already-reserved request before completion, as intended by no-retry.
The original executor then stops updating STATUS but drains its queued futures.
Do not interrupt that queue or submit another completion. After its PID exits,
fill missing per-arm records ONLY from the exact already-terminal request cache
(body/messages/seed/stage matched); missing cache remains a missing task. No
inference retry or changes to outputs. Preserve original controller terminal.
Report 120 planned arm slots separately from unique completion requests. Identical
prompts/seed share a response; this is paired reuse, not independent arm calls.
Then perform native grading and completion-aware reporting once.
