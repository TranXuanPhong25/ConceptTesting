# Concept quality and Qwen retrieval v3 — 2026-10-26

Registered before any task-level v3 output. The user rejects coverage alone and
requests (1) evaluation of returned concept quality, and (2) better retrieval,
providing a live OpenAI-compatible Qwen endpoint. Authorized model:
`qwen3.5-27b-awq`, advertised context 8192. Endpoint stays only in a private
environment file outside the repository; no URL or secret is logged here.

## Earlier evidence and scope

V2 reports 74/113 correct family + first manually labeled site, but its corpus
and labels saw public source and broad-family matches do not measure whether all
retrieved concepts are useful. Earlier v17/v31–v35/v44/v47/v74–v78 selection or
concept/template experiments did not establish robust test-generation benefit.
This run evaluates quality explicitly and uses Qwen for code/spec reasoning over
the corpus. Do not equate retrieval hits with useful tests or causal benefit.

Preserve v2 code, labels, audit and 162-card corpus unchanged. Build v3 in this
folder. No paid third-party fallback, training or original paper reimplementation.

## Cohort and freeze

Use the same public 113 PUT sources in v2 `evaluation/inputs.json`; retain the
73 development / 40 audit designation. Both sets have previously been inspected,
so no fresh held-out claim. Snapshot all input/label/baseline/corpus hashes before
task inference. The primary comparison uses the same 113 tasks, missing or
malformed outputs count as failures; no dropping difficult or unlabeled tasks.

## Retrieval treatment

Qwen sees only public PUT/spec, a task-independent 162-card title catalog, and
at most 8 detailed structural-v2 candidates. It selects up to 3 catalog concepts,
binds one source line each, and explains **where / how / what** for the concrete
source. It may abstain. It never sees task IDs, references, old gold labels,
old witness inputs or grading outcomes. The global catalog allows recovery of
concepts filtered out by the structural v2 candidate gate. No new concept IDs.

Calls use the authorized served model only, thinking disabled, low temperature,
fixed recorded seeds, tokenization/context preflight, no tools and no target
execution in the retrieval prompt. Candidate explanations are hypotheses,
not established bugs. Keep every request/response, token usage, parsing status
and error record with safe metadata. No automatic retry of unknown completions.

## Quality evaluation: measure all returned concepts

1. **Frozen-label metrics:** family precision@3, hit@1/@3, MRR and correct-family
   plus first source-line hit@3 against unchanged v2 labels. This measures
   compatibility with the old single-author labels, whose incompleteness is
   disclosed. Unlabeled task outputs are not independently certified negatives.
2. **Blinded concept grading:** combine/deduplicate v2 and v3 selected concepts,
   shuffle with a fixed seed, remove system/rank labels. A separate Qwen context
   receives public source, reference implementation and one validated historical
   witness where available. Grade each **card selection**: 0 irrelevant/wrong,
   1 contextually applicable but no actual-bug link, 2 a correct actual bug family,
   3 direct mechanism with a concrete witness and meaningful test consequence.
   Separately grade source binding / instantiated where/how/what. Reference and
   witnesses enter the grader only. Do not expose which method selected a card.
   Report precision of grade>=2, mean grade, graded nDCG@3 and abstention/coverage.
   Same-model judging is an auxiliary view, not an independent ground truth.
3. **Executable utility:** fixed hash-selected 40 tasks (20 development, 20 audit),
   three matched one-call arms: no concept, v2 top-3, v3 top-3. Qwen proposes up to
   3 JSON argument lists and expected outputs from public code/spec plus the arm
   hints. No references or saved witness inputs. Same model, seed, completion cap
   and test count. Grade official contract validity, reference-correct oracle and
   actual PUT/reference mismatch in separate bounded native workers. Report valid
   inputs, oracle correctness, confirmed bug tasks, false alarms and paired wins /
   losses. A v3-v2 win with no gain over no-concept does not establish concept gain.

Known grade conflicts and examples must be reviewed from saved evidence, not
resolved by making the same model repeat until it agrees. Report actual wrong
concepts and remaining misses with explanations. Preserve all scores and source
artifacts. A single aggregate hit count is not the deliverable.

## Budgets and lifecycle

- Up to 113 retrieval calls + 113 blinded grader calls + 120 utility calls.
- At most 4 engineering canary calls, reused if valid. Transport-only preflight
  is separate. Maximum 350 task completion attempts including canaries.
- 2 concurrent requests at most, no paid provider, 0 automatic unknown retries.
- Retrieval max 1200 completion tokens, judge max 1000, utility max 800; context
  preflight against the advertised 8192 before each call. Exact request budget and
  actual usage are recorded. Keep a 20-minute liveness loop during inactive gaps.
- Long work runs detached with own PID/status/checkpoint files; resume reuses
  completed content-addressed requests and never duplicates an unknown attempt.

Before wider inference, run engineering/schema/leakage/score checks. Any changes
based on task outputs must be dated amendments; do not silently relabel or repair
model outputs. Freeze messages/config before scoring full comparisons.

## Amendment A — before task inference

Read-only Qwen review completed; its raw output and point-by-point dispositions
are in REVIEW.md and out/engineering_review. It incorrectly called grader-only
reference evidence leakage and SHA256 shuffling unstable; those objections are
rejected with explicit input separation/hash checks. Actual grading noise,
style-based imperfect blinding and the independent cost of v3 retrieval remain
limitations. Utility matches test-generation calls, not total pipeline inference.
The review consumed 1 completion (2743 input, 718 output tokens), outside the
346 planned task calls but within the overall 350-attempt registration.

## Amendment B — after four engineering canaries, before wider inference

All four canary completions arrived. Three parsed; one used a decimal-string
line number and was rejected by the strict parser. The latter also proposed a
causal story for which its own bad-input class would return the correct result.
Preserve all four original raw requests/responses in a separate canary folder.

Prospective generic fixes: explicitly normalize only all-digit JSON line strings
to integers (record the normalization; no semantic repair/no re-prompt), and ask
the retriever to mentally check a distinguishing valid example and reject a
hypothesis whose alleged bad case actually matches the specification. No new
catalog entries, IDs, task-specific rules or labels are introduced. The revised
prompt will run on all 113 tasks with no further task-driven prompt tuning.

Because the canary prompt changes, its four responses are **not reused in the
final comparison**. Maximum total attempts increases prospectively to 356:
346 main task completions + 4 preserved canaries + 1 engineering review + at most
3 one-token keepalives = 354 planned maximum, with no automatic completion retry.
This revises an agent-set engineering cap, not a user-paid API budget. The only
inference service remains the explicitly authorized Qwen endpoint.
