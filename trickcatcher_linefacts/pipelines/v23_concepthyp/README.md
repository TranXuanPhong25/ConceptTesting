# v23_concepthyp: concept → hypothesis → discriminating input

Code-first increment, 2026-10-17. Direct copy of best v7, with parent file hashes in
PARENT.json. Original v7 and existing untracked v21_flowtools are untouched. Source,
literal, tokenizer and isolated execution interfaces are explicitly ported from v22;
PORTS.json records their original hashes. No model outputs/caches are imported.

## What the diagnostic tests

16 previously seen authored fixtures: seven buggy, eight correct (including unused
and unreachable suspicious operations), one ambiguous spec. This is a mechanism
diagnostic, not unseen generalization or benchmark D_IO. No paper is reproduced.

1. A spec-only Qwen call extracts one normative concept/relation and domain/uncertainty.
2. A code-only call summarizes actual returned behavior. It receives masked code and
   syntax facts, without spec, base tests, evaluator labels or concept claims.
3. Two separate calls propose one hypothesis: concept-guided and direct. Both see
   original context, identical model behavior and fixed public-base execution evidence;
   only the concept-guided call receives the extracted concept.
4. Each generation arm proposes up to three literal argument tuples with separate
   spec-expected and PUT-predicted outputs. Fixed native/traced replay supplies feedback.
   One revision call may add up to three tuples. Empty proposals are legal abstentions.

| Arm | Hypothesis | Explicit concept during input generation |
| --- | --- | --- |
| concept_chain | Concept-guided | Yes |
| direct_chain | Direct from original spec/code/behavior | No |
| hyp_only | Exact same artifact as concept_chain | No |

concept_chain vs direct_chain measures the complete concept-guidance intervention.
hyp_only vs direct_chain holds input-generation presentation constant and tests the
upstream concept-guided hypothesis. concept_chain vs hyp_only tests additional explicit
concept presentation conditional on the same hypothesis. Hypotheses themselves contain
normative semantics; the last contrast does not remove every semantic concept.

All arms retain original spec/code/base tests. Limits match downstream: one hypothesis
call per independent hypothesis, two input calls per arm, three candidates per round,
six unique tuples maximum. Preparation S1/S2 is shared and reported separately. The
hyp_only arm reuses its hypothesis without a new model call. At most160 logical model
calls/480 physical completion attempts; no content repair/retry. Invalid/blocked tasks
stay in the16-fixture denominator. This is not a total-cost-matched benchmark comparison.

## Execution and truth boundaries

Tools return AST statements/lexical enclosing guards and observed line events; no CFG,
complete path conditions, local-effect proof or static semantic matcher is claimed.
Uses Python ast/json/hashlib/fcntl, jsonschema, httpx, Jinja2 and the parent's existing
network-isolated sandbox. Native and traced status, typed result, exception, argument
mutation and output alias signatures must agree for verified observations. Unsupported,
filtered, capped and mismatching executions are unknown, not verified evidence.

Common discovery inputs are public base calls, not hidden bug witnesses. The evaluator's
known witnesses run only in CPU preflight. New candidate feedback contains no reference
output. No canonical/reference programs or held-out datasets are read. Evaluator-only
fixture oracles are imported by report after source/generation snapshots verify.

Report distinguishes input discrepancies, correct bug assertions, false alarms,
unknowns, blocked cases and detections outside shared seeds. Deduplication is per arm
across both rounds. Model prediction agreement with PUT never establishes spec truth.
Review packets preserve raw invalid model responses and reasoning; schema validity
does not label semantic correctness. Independent semantic adjudication remains needed.
No automatic benchmark expansion, even if every mechanical check passes.

## Commands

Use the existing environment with jsonschema/httpx/jinja2/pytest:

```bash
CoverUp_concept/.venv/bin/python -m pytest -q trickcatcher_linefacts/pipelines/v23_concepthyp/test_diagnostic.py
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v23_concepthyp.diagnostic preflight
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v23_concepthyp.diagnostic freeze
```

Online execution is a later explicit action. Set QWEN_BASE_URL in environment only;
never persist endpoint/key. Then use diagnostic online --online with the same module
prefix. It pins the model/context, counts the official rendered prompt with server
/tokenize, checks completion usage, reserves cumulative attempts before requests,
quarantines protocol failures and locks a single controller. Default commands make
zero model calls. Interrupted source/config cannot be silently changed on resume.
Terminal transport/context failures become failed artifacts without format retries.
Untrusted tokenizer/model-binding failures stop the run and produce an explicit
incomplete status with the full16-fixture denominator; no unfrozen efficacy scoring.
The passing CPU preflight is bound to the exact source/fixtures checked before online.
Long runs should launch detached; a20-minute keepalive is built in.

Inherited v7 experiment CLI entrypoints are disabled. This diagnostic does not silently
reuse v7's historical unmatched round2 schedule, scoring or fair-comparison claim.

## Small-model capability probe

Separate optional gpt-6-luna/low clean-context probe on five seen fixtures compares
an authored normative concept against the same context without that extra concept.
The supplied concept contains no fault hypothesis, trigger or witness. Both agents
must produce a hypothesis and concrete tests. This tests use of supplied concepts;
it does not establish Qwen extraction reliability or an API-stage-isolated chain.
Its own preregistration, packets, raw responses and scores live in analysis/ and
are never mixed with Qwen's diagnostic report.
