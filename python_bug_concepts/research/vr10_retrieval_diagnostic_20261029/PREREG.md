# vr10: small frozen retrieval diagnostic

Registered 2026-10-29 before new retrieval or scores. Status: engineering preparation;
independent read-only review and an explicit approval receipt are required before run.

Question: does the already implemented dense channel recover useful mechanism/site
hypotheses beyond open BM25 at the same budget? This is a diagnostic on previously
exposed development material, not a new benchmark, utility experiment or paper reproduction.

## Earlier attempts and immutable implementation

V2: 74 family/site hits; V6: 90 first-site hits on the existing 113 cohort, after
development iterations. V3's LLM selector did not beat V2. V7's four-fixture smoke
established infrastructure only. V85's completed primary comparison (78 vs77) did
not establish detection gain; vr8/vr9 concern downstream gating/retention. This
diagnostic tests retrieval only and cannot establish downstream bug-detection gain.

Do not modify V6/V7, cards, model, binder or source views. Freeze imported .py,
corpus data and pinned model manifest as well as this harness before inference.
One local Jina CPU model, existing fixed revision/runtime; no model shopping,
training, API calls, target execution, larger follow-up or parameter rescue.

## Prospective deterministic sample

Use the frozen V2 inputs and V6 iter06 saved outputs, not new model output or gold,
to select12tasks. Four strata: old V2/V6 concept/first-site signature changed or
unchanged × either old selector returned one of the8existing overlay cards or not.
Take3per stratum by ascending SHA256(`vr10-fixed-20261029/`+task_id). If a stratum
has fewer than3, take all then fill remaining slots from the entire unused pool
by the same hash. Save availability and selected membership for every stratum.
All113tasks are historically exposed development material, including the old
`audit` split. Selection does not inspect gold correctness or known wins.

For these12tasks also retrieve each canonical source alone, from the pinned local
HumanEvalPlus cache. Canonical sources are separate control queries; no buggy/fixed
pair, ID, witness, expected output or label is passed to a retriever. Joining pairs
is an analysis operation afterwards. A warning on canonical code is not automatically
a false positive: a conditional concept may be a useful test opportunity on correct code.

Add exactly the4existing V7 smoke fixtures unchanged. These have been inspected
previously; they are exploratory engineering controls, never independent efficacy
evidence. The distinct/occurrence pair changes contract intentionally; it is not
called a meaning-preserving paraphrase. No new synthetic implementation of a paper.

## Arms and budgets

V6 balanced is the unchanged reference, requested at top12; report its first3.
Balanced gating can return fewer12and is part of V6. V7 A/B/C/D use their unchanged
12unique-concept candidate budget and first3bound results. A/C: structural+open
BM25; B/D add dense. C/D enable the existing8record evidence overlay. Same V7
site universe/binder across all4arms; V6 is a different package reference.
V6 top12 is a post-policy shortlist, whereas V7 candidate12 is pre-binding; this
asymmetry must stay visible and must not be described as identical candidate recall.

Compute every query/arm before reading gold. Worker input is code strings only;
the worker is a separate process and does not receive the manifest, task IDs,
references bundle or gold. Save query SHA and packets first, seal their hash, then
perform label joins in a separate scoring command. Label freezes must verify.

## Metrics and semantic review

Primary machine diagnostics: known concept-label hit@12, known first-site hit@3,
known family mapping hit@12, returned count, recognized-tier>=2 versus unknown,
dense outside-structural nominations and paired B-A / D-C candidate+top3changes.
Family mapping is overlay family when known, otherwise concept ID: it does not
invent a complete family ontology. Gold is incomplete: unmatched means unlabelled,
not wrong. No precision, bug truth or applicability accuracy from label matches.
First-site hit matches existing line annotations, not full causal proof.

Create an arm-blinded shuffled semantic review queue for the deduplicated union
of every selected first-site binding across arms. Omit method, rank, tier,
recognizer explanations and known-label fields; use anonymous review keys.
Review public contract, selected source expression, causal relation, preconditions,
guard/domain evidence and a concrete benign explanation. Mark applicable/contradicted/
unknown with source quotes, and record whether it is a useful hypothesis even on
canonical code. Reviewers must not infer support from similarity or tier alone.
No binary benign false-alarm rate without these judgments.
Reviewers see the same canonical card definition for each nominated concept;
method-specific revised overlay text is withheld to preserve blinding. These
judgments assess mechanism/site suitability, not whether the overlay's own
condition wording or citations are better. Overlay effects are measured through
candidate/selection differences; wording quality requires a separate review.

After retrieval freeze an independent reader reviews all dense-only top3bindings
and their A/C counterparts, plus the fixed distinct/occurrence pair. Real query
grading may use gold only after the arm-blinded contract review. Report reviewer
unblinding and remaining unknowns; root author is not the independent reviewer.

GO criterion from P4: >=2 independently supported dense-only recovered bindings
on real buggy tasks, from >=2mechanisms beyond BM25 at the same budget, with no additional definite-wrong
applicability on paired controls. Frozen-gold wins alone cannot satisfy this gate.
Dense-only means correct concept plus source binding appears in B top3 but not A
top3, or D top3 but not C top3. Dense-branch membership alone does not qualify.
Previously inspected engineering fixtures cannot establish GO.
No GO if review is missing. No enlargement or model swap to rescue no signal.

## Review and immutable outputs

Before run, root writes REVIEW_APPROVAL.json: status=approved,
freeze_sha256=SHA256(FREEZE.json), prereg_sha256=SHA256(PREREG.md),
must_fixes_remaining=[] and reviewer identifier after independent read-only review.
Apply required changes as dated append-only amendments; regenerate freeze before
approval if source changes. A run uses a new explicit output directory, never
overwrites or resumes old results. Checks run before and after inference/scoring.

## Prospective amendment after independent engineering review, 2026-10-29

Applied before any vr10 retrieval or score. Previous preparation freeze SHA256:
`8645ed7d97a0ff9934b477228975b18384f56aa38b0ff7cf96df775b6ea1c928`.
The sample MANIFEST is unchanged. Correct the first-site metric to require both
membership in the accepted concept labels and membership in that concept's
annotated site lines; a site-only annotation cannot add a concept label.

Clarify ordering: all retrieval predictions are sealed first. The separate scorer
may then compute machine label joins before manual contract review and generate
the blinded queue in the same pass. This supersedes the earlier requirement to
delay real-task label joins until after manual review. The independent semantic
reviewer receives ONLY SEMANTIC_REVIEW.json and the rubric, with no RESULTS.json,
REVIEW_KEY.json, machine labels, arms or ranks. Their judgments are frozen before
unblinding. Machine label results cannot establish applicability or the GO gate.
