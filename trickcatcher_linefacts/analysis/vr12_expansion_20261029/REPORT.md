# VR12 expansion feasibility: 11 fresh eligible tasks, two uncovered targets

The existing frozen semantic binder cannot supply 20 fresh eligible tasks. Over
the completed 113-task V85 archive it supports **17 distinct tasks**, six already
used by VR8/VR9. A complete census of the remaining **11 fresh tasks** is prepared
with the original round1 receipt and ten saved reference receipts for each task.
No new model/API request was made. V85/VR9 sources and old outputs are unchanged.

## Source eligibility and public OBS coverage

| Registered family | Supported bindings | Distinct eligible tasks | Fresh tasks |
|---|---:|---:|---:|
| normalization | 14 | 14 | 10 |
| membership | 4 | 4 | 2 |
| ordering | 2 | 2 | 0 |

Rows overlap: task64 has both a normalization and membership binding. Only old
tasks137/148 support ordering, so the fresh expansion cannot be balanced across
the three families without altering the binder or reusing earlier tasks.
Unsupported candidates remain unsupported; no family was added to reach a count.

The public-source census fixed all eleven fresh IDs before native OBS measurement.
Target binding choice prefers no observed true state on valid saved round1 inputs,
with a fixed SHA256 tie break. Task order is SHA256(decimal task ID):
**80, 67, 27, 12, 162, 118, 48, 64, 112, 89, 140**.
SELECTION.json records the exact algorithm and selected binding for every task.

Pinned isolated frozen VR9 native workers reclassified the saved round1 tuples
on public PUT source. Eleven jobs processed 109 unique saved tuples: 102 B5-valid
and seven invalid. All workers completed with zero trace errors. Task67 contains
all seven invalid tuples; only its three valid tuples contribute OBS states.
Task112 has nine unique saved tuples; the other tasks have ten.

| Selected target stratum | Tasks | Evidence |
|---|---:|---|
| Already observed true | 9 | normalization tasks12,27,48,67,80,89,112,140,162 |
| No true, observed false | 1 | task64 membership: ten false, zero unknown |
| No true, mixed false/unreached | 1 | task118 membership: six false, four unknown/unreached |

Task27 additionally has five unreached/unknown inputs, but five valid inputs already
observe its normalization effect, so its target is covered. Task64's alternate
normalization binding is also covered; the deterministic preference selects its
uncovered membership hypothesis instead. False/uncovered OBS is not a confirmed
defect or proof that the membership hypothesis is applicable.

**The proposed gate of at least six fresh uncovered-target tasks is not met.**
There are only two such tasks in the entire eligible fresh census. The parent
must report this limitation and have its reviewer accept an explicit protocol
amendment before a model run; silently treating the gate as passed or adding
unsupported targets would invalidate the intended diagnostic. The remaining
nine tasks primarily exercise already-covered/generic routing behavior.

## Materialized inputs and provenance

- `assets/prepared.json`: eleven public task records, selected target index,
  frozen binding, exact round1 receipt and public OBS summary.
- `assets/refs.json`: 110 inherited reference-program receipts; final scoring
  resources only, with no new reference generation.
- `assets/PROVENANCE.json`: archive SHA256 and 154 original frozen member hashes.
- `PUBLIC_INVENTORY.json`: support-only inventory of all113 tasks and available
  archive member paths, with no final bug labels.
- `obs/<task>/job.json`, `result.json`: public-only native OBS jobs and receipts.
- `OBS_SUMMARY.json`, `SELECTION.json`: raw observability counts and fixed census.

The archive is `handoffs/v85_20261029_resume2/completed/artifacts.tar.gz`, SHA256
`8aa4df9351584038048962a3601b0b632f72f2067a40a6905eef23bcec729475`.
Every selected prepared input, round1 generation file/receipt, saved round1
classification and reference receipt matches its GENERATION_FREEZE digest.
Selection SHA256 is
`a732b9e1cace7647a8d21686d301aa62279dce120b1e7600d9cf319c6c614a3a`.

The pipeline owner can directly copy these prepared/ref assets. If reconstructing
from the archive, select only the 154 exact members listed in PROVENANCE plus
GENERATION_FREEZE.json; no archive Python file needs execution. Grading source
may be copied opaquely from frozen VR9 `assets/grading_references.json` for final
scoring after generation freeze. No canonical source was read for generation or
public OBS measurement.

## Historical label exposure and interpretation

An earlier feasibility request explicitly requested saved round1 bug-ceiling
strata, so those labels were mechanically inspected before the reviewer clarified
public-only selection. This exposure is disclosed in PLAN.md. It did not select
the census IDs or bindings: every fresh source-supported task is included and
binding preference depends solely on public OBS. This is development-informed,
not blinded or held out.

After freezing census/targets, SAVED_LABEL_SECONDARY.json records historical
ceiling context separately: seven selected tasks were already confirmed by old
round1 ref scoring; four were not (27,67,89,118). These labels do not appear in
the prepared generation records or source-only inventory and are not selection
criteria. The task67 B5-validity limitation must remain visible in interpretation.

## Model-budget feasibility

The exact VR8/VR9 strategy pools exist only for the original six-task diagnostic.
The eleven fresh tasks need fresh strategy requests for their new semantic/
applicability prompts; their original V85 round2 strategies represent a different
treatment and cannot be silently replayed as exact matches.

For K=1, three arms permit at most **11*3*3 = 99** new completions, and four arms
at most **11*4*3 = 132**: two strategy requests and one expected-output request per
task/arm. Shared exact-request replay can reduce physical calls. Keep one locked
ledger, no retries/fallback, inherited round1/110refs separate from new tokens,
and the frozen strategy/expected token budgets. No completion was launched here.
The parent owns the final arm choice, preregistration, independent review and
decision about the unmet uncovered-target gate.
