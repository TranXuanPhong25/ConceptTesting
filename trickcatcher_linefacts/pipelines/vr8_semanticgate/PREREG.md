# VR8 semantic-gate diagnostic — 2026-10-29

User explicitly authorizes the proposed diagnostic and requires retrieval-version
prefix vr8,vr9,... distinct from LineFacts vNN. This folder is an actual copy of
v85_retrievalhybrid source/templates; PARENT.json preserves original hashes.
Original source/card/retriever/default and completed v85 results stay unchanged.

Prior art: v5 scoped binding did not improve site74/113; v6 site90did not establish
utility; v7 full hints reduced40task detection; v85 ref78vs77 with206/275STMTgates.
This tests measurement alignment, not a new learned ConceptCoder model.

Scope: three measured OBS properties, not bug truth or full contract verification:
(1) a bound normalization operation changes its receiver value;
(2) a bound finite character-class lookup differs from an explicit ASCII-vowel
hypothesis, with public-spec evidence and case-policy provenance recorded;
(3) a bound string comparator disagrees with numeric order or a unique literal
rank-table alternative. Alternate-order applicability remains a hypothesis unless
public-spec evidence supports it. No grading reference enters extraction.
Normative REQ and downstream propagation are not inferred merely from an OBS hit.
Unsupported syntax/runtime types/unreached sites return unknown, never covered.
Line reachability is retained separately and cannot substitute for semantic OBS.

Before inference: native CPU fixtures verify positive/benign contrasts, unknown,
exact AST binding, unchanged output/side-effect evaluation, and denied network.
Selection: among existing v85 retrieved cards with supported bindings, SHA256-sort
task IDs, take two unique tasks per family; allocate ordering,membership,normalization
in that order so overlaps do not consume two slots. No use of scores/win/loss labels.
At most6development tasks, no heldout/generalization claim. Freeze selection/source
before model calls. Excluded unsupported forms remain reported, not silently fixed.

Reuse each selected task's v85 retrieval round1 response/assertions and preparation.
Reuse its10completed spec-only refs.Threearms:old gate,semantic gate,generic input
control. Same card definitions and selected IDs/sites. Semantic target text describes
its measured predicate; this operational binding text is necessarily different.
Round1 stays identical and generation is still two-round with Hypothesis strategies,
B5validity,strict expected-output injection,20assertioncap and original seed scheme.

Diagnostic scheduling amendment, applied symmetrically: two strategy calls per arm
(single attempt per slot,no corrective generation retry), then at most one unchanged
expected-output call if novel eligible inputs exist. Choose uncovered target by each
arm's own gate; when none remain, use generic strategy instruction. Generic control
always targets novel valid inputs. Report realized expected-output calls separately;
fixed strategy budget does not claim equal realized tokens or identical prompts.
This isolates a bounded gate/selection diagnostic,not an untouched v85 rerun.

Qwen3.5-27B-AWQ/context8192,2workers,900second completion timeout,existing context
allocation, no transport retry/fallback/model swap. At most6*3*3=54new completions.
Equal request bodies may share cached receipts; log logical vs physical separately.
Endpoint preflight currently404; CPU work proceeds, model launch waits for liveness.

Freeze all generation before grading; canonical/contracts are final labels only.
Report ref/o0 confirmed tasks,false alarms,input-only reach,semantic realization,
unknown/invalid counts,actual calls/tokens and inherited costs separately. A positive
mechanism signal needs new valid semantic realizations beyond old/generic,without
counting mere line hits as semantic coverage; detection alone is insufficient.
No autoexpansion tofull113,replication orvr9 after results. No paper/vendor edits.
