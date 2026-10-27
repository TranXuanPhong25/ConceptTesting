# Concept quality evaluation and Qwen retrieval

V2's 74/113 coverage did not tell whether its other returned concepts were good.
This variant evaluates the full returned set and tests whether better selection
helps produce executable bug-revealing tests with correct expected outputs.

The registered run uses the user-authorized `qwen3.5-27b-awq` endpoint, a frozen
162-card corpus, the same 113 public PUTs, and a fixed 40-task native utility cohort.
It does not train a model, modify v2 or reproduce a paper implementation.

## Measures

1. Frozen-label precision of each concept, hit@1/@3, MRR, actual family + source
   binding. This is only compatibility with the incomplete v2 label set.
2. Blinded per-card grading: irrelevant/wrong, context-only, actual-bug family,
   or precise mechanism. Separate binary checks for concrete where/how/what.
   Shared cards are deduplicated so both methods receive the same card grade.
3. Native test utility: no concept vs v2-selected vs v3-selected cards, with
   matched test-generation slots, seeds, token caps and at most three tests. Exact identical message/seed requests share a cached response; unique call counts are reported separately.
   Official contracts and reference execution check validity/oracle correctness;
   invalid inputs, false alarms and unresolved workers are reported separately.

Qwen retrieval sees public source/spec plus a complete title catalog and a short
detailed shortlist. References, old labels and saved witness inputs enter only
the grader. Method names/ranks are hidden from the concept judge. The judge uses
the same model in a separate context, so its grades are an auxiliary assessment,
not independent ground truth. V3's extra retrieval inference is counted and is
not hidden by claiming equal total pipeline costs.

## Artifacts and lifecycle

- [PREREG.md](PREREG.md): protocol, budgets and prospective amendments.
- [REVIEW.md](REVIEW.md): read-only reviewer findings and their dispositions.
- `data/INPUTS.json`: frozen source/corpus/baseline hashes.
- `data/utility_cohort.json`: fixed 20-development + 20-audit utility tasks.
- `out/run_20261026/STATUS.json`, `OWNER.json`, `TERMINAL.json`: owned run state.
- `out/run_20261026/QUALITY_SUMMARY.json`, `QUALITY_TASKS.json`: final machine-readable scores.
- `out/run_20261026/utility_grading.json`: generated inputs, oracle predictions,
  validity and actual reference/PUT behavior.
- `out/run_20261026/calls/`: exact cached requests/responses and usage.
- `out/canary_20261026/`: all four original canaries, preserved without replacement.
- `out/engineering_review/`: the separate implementation review response.

The endpoint value is read from `CT_RETRIEVAL_BASE_URL`, stored only in the
session's private environment file outside the repo. No URL/key is in requests,
logs, manifests or this documentation. There is no paid provider fallback and
no automatic retry of an unknown completion.

## Explicit API

Once the authorized endpoint environment is loaded:

```bash
python -m python_bug_concepts.retrieval_v3.engine \
  --code path/to/program.py --out /tmp/my-concept-retrieval-cache
```

This makes a model call unless the identical request is already cached. Each
result includes the source card and concrete where/how/what. It remains an
unverified fault hypothesis until separately validated. The default public
search API remains at v2 until the full quality comparison is reviewed.

## Checks and reports

```bash
python -m unittest python_bug_concepts.retrieval_v3.tests -v
python -m python_bug_concepts.retrieval_v3.continuation_20261027.render
```

The report renderer requires completed saved scores; it does not make model
calls or rerun the experiment. Do not launch a duplicate lifecycle while the
owned controller is active. A resume must preserve completed/unknown request
records and use their content-addressed cache.

## Continuation and current results (2026-10-27)

[RESULTS.md](RESULTS.md) includes strict manual/native review, judge false-positive
diagnostics, frozen-label results and utility completeness. Use the completion-aware
renderer above; pending utility must not be presented as zero confirmed bugs.

The continuation preserves the original failure and frozen scripts. Status for the
finishing/cache-restoration/native-grading stage is
`continuation_20261027/FINALIZED.json`; the old STATUS stopped advancing after an
identical-request reservation conflict, while queued requests continued. Check
OWNER.pid and FINALIZER.pid before resuming. Do not launch a duplicate worker.

[Hybrid v4](../retrieval_v4/README.md) is separate and opt-in. Its post-hoc scores
use saved v3 responses, never gold at runtime. The original v3 utility comparison
does not measure v4 utility.
