# Independent unblinding-method review

2026-10-29. Read-only review of `summarize_review.py`, review keys and queue
structure. No GRADES files or semantic judgments were opened; no inference,
target execution or scoring was performed in this review.

## Verified on the frozen run01 structure

- 132 unique source/concept/first-site union keys; every key maps to exactly one
 query SHA256. Thus arm membership comparisons cannot merge different queries.
- 117 unique queued keys, with no duplicates across the two reviewer queues.
 Every queued object equals its source object in SEMANTIC_REVIEW.json.
- All bindings from each of 23 queries with an A/B or C/D top3 binding difference,
 plus all4preinspected fixture queries, are covered. This is exactly117keys:
 no required key missing and no additional key inserted.
- B-A and D-C comparisons use membership of the same deduplicated source/concept/
 first-site key. They are incremental bindings at top3, rather than evidence
 that a concept merely appeared somewhere in the dense branch.
- The 15 omitted union keys belong to queries with identical sparse/dense selections.
 They cannot add incremental wins or losses. Aggregate reviewed-proposal-quality
 counts cover a selected subset, not all28queries or a prevalence estimate.

## Required changes before computing a GO decision

1. The initial summarizer counted contradicted canonical bindings as controls,
   but omitted the4preinspected engineering controls from the no-additional-wrong
   constraint. Include both categories in that veto; fixtures cannot establish
   positive efficacy evidence but can expose definite-wrong applicability.
2. Require a nonempty mechanism-family identifier for every `supported_fault`
   judgment. Without that validation, missing family values could count as a
   mechanism or cause mixed None/string sorting to fail.

The above are method corrections before opening judgments, not retrieval tuning.
Root should record their implementation before running the summarizer. Additional
defensive assertions for one-query keys and exact required queue coverage are
recommended; the present frozen data already passes both invariants.

## Interpretation constraints

The sample was selected prospectively by hash within old V2/V6 disagreement and
overlay-coverage strata. It was not sampled from dense wins. It remains historically
exposed development material. The4engineering fixtures were previously inspected.

V6 top12 is a post-policy shortlist; V7 candidate12 is pre-binding. Top3 source-site
comparisons are interpretable, but their candidate-stage recalls are not calibrated
to identical eligibility policies. All imported source/data/model files were hashed
before predictions; source-only workers received individual code strings and
predictions were sealed before frozen-label scoring.

An8/8plateau on already known labels cannot establish overall concept quality:
the other4sampled real tasks have incomplete labels, unknown nominations are not
false, and a line-label match is not proof of applicability. Manual source reasoning
must evaluate the causal requirement and benign alternatives. These reviewers are
independent agent readers, not human adjudication or native execution ground truth;
disjoint assignments do not support an inter-rater agreement estimate.

Contradicted proposals on canonical code measure confusion in mechanism nomination.
They are not formal bug-report false positives, because a conditional test concept
may be useful even where the implementation is correct. No review outcome here
measures generated-test quality or downstream bug-detection gain.
