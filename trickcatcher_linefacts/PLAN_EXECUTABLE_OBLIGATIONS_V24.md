# v24: executable obligation + witnessed hypothesis, narrow diagnostic

2026-10-17. User approves implementing the proposed repair. Best parent remains v7;
new folder v24_obligations, original/frozen folders untouched. No paper reproduction.
Libraries: jsonschema, inspect, ast, collections.Counter, existing isolated workers,
httpx/Jinja2 and Hypothesis for a common frozen input pool. Code/clean-context review
before any new diagnostic calls. Existing authorized Qwen endpoint may be used; no
paid fallback or benchmark/held-out expansion.

## Scope and responsibility

Nine seen authored cases from v23: f01/f02/f14/f15 (sorted multiplicity, correct,
returned dedup, unused set, unreachable dedup), f03/f04 (inclusive count), f05/f06
(membership inclusion), f13 (undefined suitability).3 buggy,5 correct,1 ambiguous.
Qwen alone proposes normative semantics, actual behavior and a fault hypothesis.
Tools never pick a fault by property-name/text matching or an AST fault catalog.

First increment: one executable full input/output obligation per function, not a
general arbitrary-spec compiler or a multi-obligation completeness claim. Qwen sees
spec/signature only and returns exact source quote, domain prose, relation prose,
uncertainty, and Python function obligation(arguments, observation). Observation is
{status: ok, value: JSON value} or {status: exception, exception_type: string}.
Ambiguous semantics require unknown with no executable predicate. Domain is enforced
by the fixed original fixture filter, never narrowed by the model's domain prose.

Predicate/trigger code is resource-bounded, pure restricted Python in network-isolated
workers. AST checks restrict calls to supplied pure builtins/Counter and deny imports,
attributes, mutation, arbitrary calls/statement-loops/I/O. Bounded generator/list
comprehensions over bounded JSON containers are allowed for counts/membership, with
no nested function/lambda, dynamic call or mutation. Literal/JSON sizes, ASTs, execution time,
memory, result boolean type and input mutation are checked. Exception/timeout/error
means unknown, never a witnessed violation. Original/traced PUT agreement is required.

## Diagnostic-only semantic calibration

Executable syntax/base agreement is insufficient. BEFORE using a predicate, compare
it against a frozen authored semantic probe bank: valid inputs with spec outputs and
deliberately alternative typed outputs, independently computed from the fixture spec.
This bank tests full output relations, including boolean type, multiplicity, ordering,
boundary, extras and duplicates. It is an explicit qualification use of diagnostic
gold, NOT a deployable reference-free semantic verifier or a blind benchmark.
No probe row, expected output or failed candidate repair enters model context. Only
qualification state is exposed; malformed/wrong predicates remain failures/unknowns.
No model retry or replacement based on calibration. Full9 denominator retained.
Independent model-assisted semantic audit is separate from this finite calibration;
neither is a universal proof or human gold. Real benchmark use needs another protocol.

## Input, evidence and hypothesis

JSON {arguments:{parameter_name: JSON value}} binds via inspect.Signature semantics
derived from source AST; reject unknown/missing/unsupported parameters, bool-as-int
where domain excludes it, oversized/nested/nonfinite values. No repr/tuple strings in
model output. Binding code is generic, not task-ID dispatch.

Freeze a common bounded Hypothesis input pool (24 unique argument objects per case,
fixed seed) BEFORE Qwen. Strategies derive from fixture parameter types only, not bug
labels, spec interpretation, PUT constants or gold witnesses; public base inputs
included separately. Whole pool is replayed once/task, shared across arms. Search
costs/physical PUT and predicate calls recorded, no extra search after seeing failure.

S2 Qwen behavior sees code/syntax only. S3 sees spec/code, S2 behavior claim, proposed
contract and public base evidence; proposes mismatch/consistent/unknown, obligation reference, source
lines, relation/effect claim, alternative and pure trigger(arguments) function for
mismatch. Common pool checks both trigger and obligation plus requested line reach.
A supported hypothesis needs model mismatch, calibrated contract, true trigger,
verified native/traced execution, observed target reach and false obligation result.
This is observed witness support, not universal trigger sufficiency/causal proof.
Consistent hypotheses contradicted by the pool are recorded; no automatic semantic
rewrite. One predeclared model feedback revision may keep/revise/withdraw/unknown.
S4 cannot edit the obligation, quote, domain or contract code. Its revised trigger and
source references are revalidated and reexecuted on the SAME frozen pool. Invalid or
fabricated obligation references fail the stage; no repair or alternate predicate.
All initial hypotheses/counterevidence are preserved. Missing evidence is unverified,
not inferred infeasibility. Reuse frozen pool only; no model predicate as expected
oracle, no oracle-based hypothesis reranking.

## Generation controls and scoring

After preparation freeze,3 arms receive same original context and the SAME up to6
shared pool inputs/native traces. Selection ALGORITHM freezes before model outputs:
prefer final supported trigger+violation rows, then calibrated contract violations,
then original pool order; never independent-oracle score. Selected values are fixed
after preparation; every arm receives identical concrete rows including any witness
used to support a hypothesis. No private witness/native trace from other pool rows
is exposed to one arm alone. Novel detection subtracts the entire24+public-base pool,
not merely the6 shown rows. verified_hyp adds the calibrated
contract, hypothesis and explicit supported/contradicted/unknown evidence. text_hyp
receives same raw textual concept/hypothesis and same inputs/traces without executable
verification presentation. toolinput receives same inputs/traces, no semantic package.
The comparison tests the whole executable-verification intervention, not just wording.
Two generation calls/arm, up to3 named-JSON inputs per call, fixed native replay feedback.
verified_hyp feedback may include predicate/trigger checks; other feedback native only.
Final generation caps equal; actual calls/tokens/executions and preparation reported.
Unqualified/missing predicates supply no executable guidance to verified_hyp; retain
raw model claims for audit and report coverage/fallback explicitly. Text/control arms
continue on original context. Ambiguous f13 has no normative oracle: even a raw model
predicate/mismatch remains unqualified, never auto-corrected into model success.

No expected-output synthesis in this first mechanism diagnostic: all arms scored
after generation freeze by SAME independent authored fixture oracle. It measures
input-generation yield, not improvements in model-authored exact-output assertions.
Property assertions are a separate future oracle track. witness_only executes the
common pool with the same oracle; do not credit its detections again as LLM discovery.
Report new inputs and new detected tasks beyond shared witnesses separately. Report
full9 case counts, false contract flags on correct code, ambiguity, missing predicate/
hypothesis coverage, runtime unknowns, duplicates/invalids and selected-input costs.
Evidence uses immutable pre-call arguments and strict JSON types; True is not integer1.
One primary target_line must be an executable statement in the entry function; support
requires that line observed in completed trace. It proves reach only, not propagation.
Full relation means returned JSON-value semantics, not copy identity or all side effects.

Frozen discovery types come from public base arguments: integer range[-2,3], list
size0..4, no nested lists;24 distinct records retained from at most128 Hypothesis
generated examples, explicit seed20261017+fixture number, database disabled. Failure
to obtain24 unique rows is preparation failure. Hypothesis/dependency/interpreter
versions recorded in protocol. Model inputs use transport caps (64 items,256 nodes,
depth8, integer128bits), independent of original normative-domain filtering.
Calibration inputs exhaust lists over[-1,0,1] of size0..2, limits[-1,0,1] and Cartesian
argument products where needed; typed candidate observations include correct values,
wrong values/types, exceptions and empty cases. No failed calibration example is sent
to Qwen. Calibration explicitly rejects always-true/false or wrong-type predicates.

## Budget, failure and freeze

Per case: S1 contract, S2 behavior, S3 hypothesis, S4 hypothesis revision, then6
generation calls across3 arms =10 logical slots; max90 logical/270 physical attempts.
One output per request, no syntax/semantic repair; transport retries only cumulative3.
Token caps: contract1536, behavior768, hypothesis1536, revision1536, generation768.
Pinned Qwen/context16384, temperature0, fixed seed20261017. Stop globally on protocol/
tokenizer mismatch; slot-local transport/context failures are explicit failed records.
Prepared pools/calibration banks/source/request lineage freeze before model calls;
preparation/hypotheses freeze before generation; all model outputs freeze before scoring.
Reuse v23's reviewed cumulative per-slot transport ledger, persistent tokenizer/protocol
quarantine, context caps and raw-response storage as explicit ports. Resume requires
identical source/config/fixtures/pools/probes and request hash. Controller exclusive
lock; native/predicate caches bind exact source, input, interpreter and resource policy.
No reset of attempts or unknown executions; incomplete status retains all9 cases.
No benchmark promotion or automatic extra adaptation, even with a positive diagnostic.
