# v69 typed writer: implementation and frozen CPU replay — 2026-10-25

Implementation complete;114authored regression tests pass. Frozen CPU replay
of the SIX v67 responses completed normally and passes owner artifact audit.
Case124now produces22native-realized candidates instead of0, with no unsupported
string-order issue. **Sensitive witnesses0; overall gate0/6.** No new model,
endpoint, oracle or private-label calls. New writer adherence is unmeasured.

## What changed

- Prospective writer uses a short restricted Python condition over arg0,arg1,...
  and structured operator/literal/expression edit. The tool compiles conditions
  and source-preserving simple edits, records provenance, then applies the same
  purity, spec binding, public checks and native verification. Free prose is not
  interpreted into repairs; no arbitrary expression evaluation is used.
- Typed checks reject invalid operations before search, including string vs int
  comparisons. They do not infer an omitted len() from the model's intent.
- String comparisons implement Python lexicographic Unicode order, including
  empty/prefix/equal strings. Tagged strings/tuples retain type distinctions.
- Legacy replay records only equivalent gt/ge/ne normalization. None strings,
  assignments and weak/no-mismatch claims are preserved and can remain rejected.
  Old responses are not rewritten to pretend they used the new writer schema.

## Fixed six-case CPU replay

| Case | Proposals | Admitted | Public-consistent alternatives | Candidates / realized | Sensitive | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
|61|3|1|0|0 /0|0|FAIL|
|66|3|0|0|0 /0|0|FAIL|
|124|3|3|2|22 /22|0|FAIL|
|58|0|0|0|0 /0|0|FAIL|
|131|3|0|0|0 /0|0|FAIL|
|85|3|2|0|0 /0|0|FAIL|
|Total|15|6|2|22 /22|0|0/6|

Case61: after equivalent gt normalization the trigger compares a string to an
integer and is rejected by the new type checker; no inferred length repair.
The admitted range replacement still fails a public example. Case66still emits
three expression None alternatives. Case131still contains an assignment/None;
ne normalization fixes syntax vocabulary but does not fix its hypothesis.
Case58still abstains. Case85still has one assignment and two null alternatives.

Case124two alternatives pass all four public examples under two seeds and two
repetitions of each program. String-trigger construction now works; exact site,
predicate, event, repeatability and normal execution hold on6+16candidate runs.
**All22have word1=""**, and none changes the final output relative to its
alternative. The supplied public spec explicitly requires
`1 <= word2.length < word1.length <= 3 * 10^5`: all22violate this constraint.
They therefore cannot establish valid-domain evidence or meaningful failure
hypotheses. This conclusion uses the visible spec/arguments only, not a private
reference or scoring outcome.

The unchanged shape-first enumeration spends the native budget on early empty
word1shapes before reaching larger shapes. Repairing string ordering exposes
that next limitation. No post-hoc reordering, inferred domain filter, budget
increase or second CPU run was performed to rescue the result. Absence of
sensitivity on these inputs does not establish program equivalence or that the
hypotheses would fail on the valid domain.

## Validation, provenance and limits

114tests passed in16.52s: real Python vs symbolic differential checks on Unicode,
empty/prefix/equal strings; solver materialization; Boolean/type constraints;
unsafe condition syntax; alias semantics; edit/source preservation; stable native
re-admission; original proposal receipt indices; prospective writer integration;
and inherited public consistency/gate/replay/accounting regressions.

Runtime is /tmp/concepttester-v57-venv/bin/python. Exact run root, requests,
PID and prelaunch source commit4650f38are recorded in CURRENT_RUN.json.
Source/config/runtime/Z3/author artifact/protocol/review and exact original writer
hashes were frozen before replay. Artifact audit PASS52freeze entries and all6
case receipts, execution sums, display parity and gate results. The pinned v67
parent is unchanged. Replay reused6already completed responses and makes0new
model calls; original35,419v67tokens are historical, not newly consumed here.

Actual native executions252:76public checks+176construction executions.
Case124uses250and case61uses2; each case remains within256.22candidate limit
checks stay under64; case124finishes in about11seconds, under120. No private
labels read, detection score produced or generator arm dispatched. Case124
prepared contexts include nonsensitive inputs; no selected sensitive evidence.
The sensitive-first selection behavior remains validated by authored regressions.

Review is owner source/protocol audit and owner read-only artifact audit;
independent agent review was not performed or claimed. CPU replay is engineering
on already observed responses, not an independent replication or evidence of
new writer improvement. The new writer surface has only been exercised through
authored prepare_case integration fixtures; fresh model responses are needed
before claiming better contract adherence or hypotheses.

## Next unresolved work

The compiler/string backend repair is complete. Before full generation, domain
conditions must enter construction so early invalid shapes do not exhaust the
budget, and a fresh bounded writer diagnostic must test the simpler interface.
The all-case evidence gate and oracle/ref10 remain unchanged. Source-path v66/v68
is a separate branch and has not been modified or merged by this work.

Artifacts: replay_artifacts/ contains the complete checksummed CPU replay;
terminal_audit.json records a read-only verification with zero new native/model
execution. No active owned replay process or automatic model continuation remains.
