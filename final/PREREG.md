# Final HumanEval pipeline — registered 2026-10-30, before model execution

User request: new, independent `final/` folder; replaceable `CoreModel`; run all
164 HumanEval tasks. The user will supply the model/endpoint. No backend may be
chosen or substituted silently. This is the requested plain pipeline, with no
concept treatment, new paper reproduction, or comparison claim.

Prior work in this repo: v38 sampled 10 spec programs but 182/183 matched the
canonical solution; v39 on VibePass was no-go (C' 12/33, H' 2). This run changes
the target to a fresh, structurally deduplicated base-pass program cohort and
one-shot shared test generation. It does not claim research novelty or assume
structural differences imply algorithmic independence.

## Fixed design

1. Original HumanEval, all 164 task IDs 0..163, local frozen dataset SHA256
   `b2adeeae8b383b6f0c615746a397f25c8abe44da4afb29cd10e6c4bbf0463fd3`.
2. Writer sees only the prompt/spec, and prior retained implementations for
   diversity. No base tests, reference implementation, or extended tests.
3. Target **10 programs per task**, full function source. First request asks for
   10; at most 5 generation invocations total per task replenish invalid/duplicate
   responses. Targeted replenishment uses no test outcomes. No deliberately buggy
   programs, mutation engine, padding statements, or syntax-only renaming.
4. Deduplicate normalized AST after removing comments/docstrings/annotations and
   normalizing binding names. Different source is necessary, not proof of distinct
   algorithms. Shortfall after the cap is a reported incomplete task; do not run a
   smaller cohort as if it had 10 programs.
5. Run the original `check(candidate)` base suite in an isolated interpreter. Keep
   only passes. Assert the canonical solution also passes the base suite.
6. **Exactly one received-model invocation per task with at least one base pass**
   generates up to 30 new tests shared across those programs. No repair calls,
   feedback loops, per-program tester calls, or retries of unknown invocations.
   Tester sees spec, base tests and all passing programs; never canonical source.
7. Tests contain literal Python positional/keyword inputs and restricted boolean
   predicates over `result`, `args`, `kwargs`, safe builtins and public `math`
   attributes. Prompt asks for in-domain novel inputs, specified float tolerances,
   and properties for non-unique outputs.
8. Execute base tests on the reference to trace every actual candidate call.
   Signature-bind/apply defaults to identify input copies despite positional vs
   keyword spelling; reject base copies and duplicate new inputs.
9. Run each proposed test on canonical twice. Reject predicate disagreement,
   exceptions, timeouts and invalid records; never repair the expected outcome
   from canonical output. This reference check does not prove domain validity or
   exclude rejection of another valid output; retain this limitation in reports.
10. Run surviving tests on every base-pass program twice, with a freshly loaded
    implementation per input and a new sandbox per suite repetition. Count a
    program once if at least one same test fails/errors/times out on both repeats.
    Record instability and the complete test/program outcome matrix.

## Model/configuration and execution

- Model/endpoint: **awaiting user**. Same CoreModel instance for writer/tester.
- Default generation/test temperature .9/.6; max output tokens 16000/8000;
  deterministic request seed `20261030 + task_id*100 + round`, tester offset 99.
- Two concurrent task workers. Default 3-second per-load/call/predicate timeout;
  1 GiB worker address-space limit. Linux bubblewrap filesystem and network
  isolation, minimal environment without credentials. Never fall back to host exec.
- Python 3.11.14 from `CoverUp_concept/.venv/bin/python` for the intended run.
- Upper bound: 820 writer + 164 tester invocations; ordinary case 328 total.
  User endpoint/budget constraints may reduce these caps prospectively, never
  after inspecting outcomes.
- Before real model execution, independent read-only Codex review and meaningful
  engineering checks. Append must-fix amendments here before any real outcomes.
- Freeze source hashes, dataset hash, model ID, backend factory, settings,
  interpreter and task IDs in manifest. Source/config changes require a new run
  directory. Save requests/responses/usage separately. No URLs or keys in artifacts.
- Resume only from durable responses; a started invocation without a saved response
  stops and reports unknown usage. Do not silently repeat it. Exclusive directory
  lock prevents duplicate launches. Active requests drain before error exit.

## Report

Primary descriptive counts: 1640 target programs; structurally distinct generated
programs; base passes; programs actually evaluated with valid novel tests;
programs failing new tests in both repeats; tasks with any such failure.
Report detected/base-pass and evaluated/base-pass fractions separately. Neither is
recall of all genuine bugs. Count each program once regardless of tests failing.
Also report shortfalls, tasks with no valid tests, rejected tests by reason,
unstable programs, model calls/known token usage/unknown responses. Preserve raw
artifacts for semantic review. No automatic run enlargement or alternate-model
fallback based on the results.

## Amendment 1 — independent review, 2026-10-30, before real outcomes

Read-only Codex review found three must-fixes, reproduced with engineering fixtures:

1. Preserve the original prompt scaffold/imports/helpers when loading programs.
   Load base tests in a separate original-prompt namespace so generated code cannot
   replace a helper used by the assertions (HumanEval/32, /38, /50).
2. Normalize import aliases; remove unused imports and obvious unused literal
   assignments from structural fingerprints. This closes rename/padding loopholes,
   without claiming complete semantic deduplication.
3. Seed Python `random` consistently per task before base tests and every test
   execution. Collect the union of actual base inputs from reference and candidates;
   use the original prompt's function signature for positional/keyword identity.
   Worker Python uses `-S -B -P` with a minimal environment and explicit read-only
   code path, honoring `PYTHONHASHSEED=0` (unlike `-I`, which ignores it).

Added regression checks for all three issues. No real model call has occurred;
all observed program failures so far are synthetic engineering fixtures only.

## Amendment 2 — scaffold follow-up, 2026-10-30, before model calls

- Follow-up review reproduced a SyntaxError when candidate source starts with
  `from __future__ import ...` after concatenation with a scaffold. Compile/exec
  original prompt and full candidate source as two units in the same candidate
  namespace; retain an independent base-test namespace.
- Canonical-only harness preflight passed 163/164; HumanEval/33's base suite also
  calls the target by its original name. Bind that name to the same wrapped
  candidate as `candidate` in the test namespace, preserving original behavior
  and recording these direct calls too. No base tests or dataset source edited.
- Add future-import and direct-name-call engineering regressions. Recheck all
  164 canonical solutions; save the initial preflight separately. There has been
  no model invocation or generated-program benchmark outcome.
