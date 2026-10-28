# V85: v11 hybrid with v2 concept retrieval — 2026-10-28

User requests replacing v11's concept mechanism with the existing retrieval
pipeline, in a new version, and a direct comparison. Copy v11_fair; do not change
the parents, paper/vendor sources or Kaggle notebook. Earlier v77 combines v11
with v31 fault types and has no completed matched result; this treatment instead
uses the frozen v2 card corpus/selector that reached45/113 in a standalone run.

Compare original v11 concept-hybrid against retrieval-hybrid on all113 existing
public PUTs, K=1 per arm, exact qwen3.5-27b-awq/context8192, same seeds and original
v11 generation settings. This is a new matched K1 run, not historical K3 output.
Shared fresh Qwen27B B5 validity/domain preparation and original v11 code facts,
shared public base tests; no missing-cache task exclusions. All historical model
responses are excluded. Baseline selection/ranking and prompts are unchanged.

Treatment: v2 top3 cards on buggy source only. For each card's first evidence span,
bind the first unused v11 reached/ranked fact at that span. Keep its executable
gate and witness metadata; replace hint text with the unchanged compact card plus
the explicit mechanical target. If none binds, use source-line reachability only
and label it as such. No evidence means omit that card with a recorded reason;
do not fill from baseline. Hypotheses are unverified; no gate proves bug truth.
Selection/representation/gate binding is one package, not a pure wording ablation.

Both arms retain v11 round1, missing-target detection, Hypothesis round2, up to2
strategy attempts/target,100 draws, up to2 selected inputs/target, strict novel
input selection and exact expected-value request. Max8logical calls and20assertions
per sample. Same caps, not necessarily equal realized calls: report realized costs.
Use unchanged arm seed indices; run task pairs in deterministic order with
alternating arm order. Keep the round1 result as a diagnostic, not another run.

Primary oracle: shared10 fresh spec-only DPP implementations/task, original v11
base-test filtering, >=3survivors and unanimous successful outputs, otherwise
abstain. Generated from spec only before target canonical grading; no PUT/card
information in these oracle requests. Also report model-written own expected
values (o0). No judge/full oracle, new paper loop, paid fallback or treatment tuning.

Maximum completion attempts =113*(5shared preparation +2*8generation +10oracle)
=3503. Algorithmic strategy correction is retained; transport retries are disabled.
No extra keepalive completions; active task calls provide keepalive. Freeze source
and public inputs before inference, freeze both arms and oracle responses before
loading target references/contracts for final grading. No reference feedback.
Do not silently reduce output caps or truncate inputs to fit8192; context failures
are terminal and reported. Checkpoint every task/stage, exclusive detached launch.

Primary result: per-task confirmed detection under ref, paired wins/losses and
two-sided exact sign test. Report false-alarm tasks, assertion precision, oracle
abstentions, D_I/D_IO, real calls/tokens and stage failures. All113 in denominator;
an incomplete run is partial, not a win. No independent holdout or broad superiority
claim. Matched plain/placebo/toolinput controls are outside this requested two-arm
comparison; no isolated conceptual-content claim follows from the pair alone.

Mac runtime adaptation applies equally: sandbox-exec denies network, clean worker
environment, wall limits and sampled3GiB RSS cap in place of Linux RLIMIT_AS.
Pinned original tool versions in a separate venv. No target reference data used
in CPU fixtures. Verify parent/source/input hashes and request identities at end.

Version-number correction before any completion: remote main already contains
`v84_reka_completion`, discovered during push. This retrieval package is renamed
to v85; algorithm, cohort, seeds and budgets are unchanged. Initial v84-named
source snapshot is preserved in commit7bf6d3c and PREFLIGHT_FREEZE_V84.json;
its zero-completion HTTP404 receipt is retained. The existing dedicated venv
keeps its original temporary path; no environment/tool versions changed.
