# v30 contract diagnostic — 2026-10-19, before new model outputs

User explicitly authorized “chạy đi m”. Run a bounded, paired interface diagnostic, not a new efficacy benchmark or
semantic-gate promotion. Preserve frozen v21/v30 sources. External runner uses the already reviewed v30 implementation;
it does not enable its disabled general experiment CLIs. Live transport is the unchanged v21 Qwen client.

## Frozen treatment and sample

10 previously seen HumanEval pilot cases:0,43,70,77,84,90,105,131 (all8 prior ID-cap failures), plus82 and116 (successful
structural-query repeat controls). This is an intentionally failure-enriched diagnostic; no population/benchmark gain claim.
Freeze original source/spec/base/mined validity, ordered hypotheses/concepts and common witness inputs from the saved
v21 pilot20 artifacts. Verify saved generation/source hashes and exact prepared task hash before reuse. No new S1–S3
calls, hypothesis revisions, manual semantic repairs, known bug locations or canonical outputs in prompts.

Two arms:old_contract (v21 package, dispatcher and feedback projection) versus repaired_contract (v30 package,
dispatcher/schema disclosure, structured errors and retained error summaries). Both receive the same full
concept+input+hypothesis package and original context. The treatment bundles disclosure, validation/error feedback
and history projection; it cannot isolate each part or prove model capability independent of interface.

Same Qwen2.5-Coder-7B pinned16,384-token context, temperature0/top_p1. Same per-case/round seed in both arms.
Two tool-choice calls and one final-test call/arm:60 logical completion slots maximum,3 cumulative transport attempts
per slot (180 completion attempts ceiling), no content/schema retry. Existing v21 transport tokenizes at most3 times
per prompt (separate metadata/tokenization budget); no paid fallback. Agent max output768, final1,024 tokens.
Serial execution with keepalive; stop/quarantine on tokenizer/context/protocol mismatch. Record failures and unknown
attempt usage, never reset ledgers. Endpoint/key must remain in memory/environment only.

## Tool/input budget

2 rounds ×6 actions,12 total/arm; same limits as v21/v30. No mandatory replay, automatic query repair/truncation,
forced branch, extra round or adaptive case selection. Each recognizable invalid replay consumes an execution slot
per the audited legacy precedence. Record actual action, error, cache and physical-process counts separately.

Common discovery at most6 inputs/case (60 replay requests ceiling), shared frozen trace artifacts projected to both
arms. Final at most6 inputs/arm (120 final requests). At most12 in-round replay requests/arm (240 replay requests),
thus420 replay/final/common requests and840 ordinary+traced processes ceiling, plus at most840 mined validity checks
inside those workers. Actual reused witnesses/duplicates/cache hits reported. No canonical/reference execution.

Final tests are input-generation artifacts and observed native outputs only. No new D_IO, TP/FA, gate success or
oracle-accuracy metric is computed. Cached old outcome labels are evaluation-only and excluded from the runner.

## Metrics, success reading and stop rule

Report all10 cases/two arms: attempted/valid reply slots, per-tool counts, action errors and fields/limits, repeated
queries, whether second round changes a rejected query into a valid action, active replay/path use, hypothesis
linkage, final admissible inputs, native agreement, model/token/physical costs. Parse invalid object actions per-slot;
a valid sibling is not erased. Strict action schemas remain out of the outer agent-reply envelope.

Descriptive diagnostic support requires fewer ID-cap errors for repaired_contract. Query correction and active
replay/check_path usage remain separate outcomes; fewer errors alone is not evidence of path-based hypothesis
validation or improved detection. No p-value/promotion from this selected n10,K1. No automatic larger sweep/held-out.

Freeze code/config/prepared packets before first completion and raw generation before report. If endpoint unavailable,
publish preflight status with0 completions; retain prepared run for unchanged resume once the user provides a live
endpoint. No automatic indefinite polling or substitute model. Independently review protocol/runner before launch.

## Review resolutions pinned before runner/model output

Case order is exactly0,43,70,77,84,90,105,131,82,116; alternate old-first/repaired-first by zero-based case index.
Seed =20261019 +100×case_id +round_index (rounds1,2,final3), identical between arms. Pin tokenizer manifest/template
and model/context hashes. Reuse common traces from frozen ledgers (no new common PUT executions) only after verifying
old/new CFG and projection-code equivalence. Packets contain no reference, canonical, score or outcome-label fields.

Any protocol/context/quarantine or terminal transport failure stops the diagnostic; remaining slots are reported as
not-attempted on the full60-slot denominator. A dispatcher/integrity failure records an arm failure and blocks that
arm's remaining slots; do not repair old code or manufacture a tool result. Invalid content consumes a call, receives
typed reply failure feedback and follows the fixed remaining slots, without an extra repair call. Truncated completion
is a content failure for both arms. Successful output ceiling51,200 tokens; retry-inclusive maximum153,600, with timedout
usage separately unknown. Tokenization ceiling180 attempts; metadata/keepalive counted separately.

The new runner is an explicitly authorized external diagnostic adapter over unchanged reviewed CPU libraries, not a
change to v30's general disabled experiment entrypoints. Independent read-only protocol reviews found no scope blocker;
code review is required before launch. Observed error feedback/native outputs are evidence, never an expected oracle.

Final runner review resolutions: stable transport slots `case/arm/stage` detect prompt drift instead of opening extra
slots. Any unexpected dispatcher/integrity exception stops the whole diagnostic (a stricter stop than earlier arm-local
wording). Native sandbox invocations are durably reserved, capped840; metadata/tokenizer counts survive resume.
Raw transport/packet/case records freeze before reporting; partial snapshots do not block unchanged missing-work
resume. Candidate cap correction means a valid round2 query of the same tool reduces an earlier rejected >4-ID query
to a nonempty ≤4-ID subset; report descriptively, not causally.
