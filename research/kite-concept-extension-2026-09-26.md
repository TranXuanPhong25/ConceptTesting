# KITE concept extension: implementation and blocked reproduction

Date: 2026-09-26

## Executive summary

This work implements a research-oriented KITE/MutGen framework in `kite_concept/`, including the
concept-record extension, PIT ingestion, leakage controls, KITE validity and promotion gates,
AnyPoC-style independent re-execution, equal-call-budget accounting, durable resumability, RBDR,
paired bootstrap intervals, and exact McNemar comparisons. Nine focused tests pass; the focused
integration selection containing the repository style-reference tests passes 17/17.

The requested Gemini/Defects4J experiment did **not** run. Vertex AI failed before an API request
could be made because the sandbox DNS resolver could not resolve the Vertex endpoint. Therefore this
report does not present paper numbers as reproduced results and does not invent tuning or full-run
measurements. The durable failed connectivity checkpoint is at
`/tmp/kite-concept-cache/run-state.sqlite`.

## Sources and artifact search

The implementation was grounded in the repository notes for KITE, MutGen, and Meta ACH; the full
[KITE paper](https://arxiv.org/abs/2607.11573) and
[MutGen paper](https://arxiv.org/abs/2506.02954); and the branch's existing Gemini adapters in
`testeval_py/llm_runner.py` and `magma/llm_client.py`. Searches by title, author, method name, and
artifact venue across GitHub, Zenodo, and figshare found no official KITE or MutGen implementation or
data artifact. MutGen states that it builds on Mutahunter, but does not publish a MutGen repository.

The task named `testeval_py/mutation_loop.py` as an existing branch file, but commit `2cb52fd` in the
mounted worktree does not contain it. A neighboring checkout contained a Python/TestEval comparison-
mutation pilot, which was read only as local context; this package's Java/PIT implementation is
self-contained.

## Method

### Dataset and reconstruction rule

KITE reports 172 method-level Defects4J tasks: Cli 24, Compress 32, Csv 11,
JacksonDatabind 51, and Jsoup 54. The paper starts from 305 bugs, retains 256 single-class patches,
then keeps patches stably localizable to one focal method. It does not publish the 172 identifiers.

The reconstruction therefore uses a declared, deterministic rule:

1. read Defects4J's `classes.modified` for every active bug in the five projects;
2. keep exactly one modified production class;
3. parse the official `*.src.patch`, map every changed production line to the enclosing Java method,
   and require one common focal method;
4. reject changes outside that method, constructors/initializers that cannot be stably named, and
   unresolved patches;
5. record the Defects4J version, rule version, rejection reason, and task-manifest hash.

This rule exactly reconstructed Cli's published count (24). The interrupted cache log had evaluated
all 39 Cli candidates, all 47 Compress candidates, and 7 Csv candidates; it found 33 rather than 32
eligible Compress bugs before the additional stable-localization review, demonstrating why a full
identifier-level match cannot be claimed without the authors' manifest. The cache contains 94 fixed
checkouts (Cli 32, Compress 43, Csv 15, JacksonDatabind 2), but construction was incomplete.
`validate_manifest` refuses any manifest that does not have the exact published split.

The 40-task tuning subset uses seed `260711573`, proportional project stratification with at least one
task per project, and stable sorting. Selection must occur only after the exact 172-row manifest is
available; no incomplete substitute was selected.

### Knowledge base

Historical records are accepted from Defects4J, Bears, Bugs.jar, GitBug-Java, and GHRB only after
normalization to correct/buggy method pairs. `build_knowledge_base` rejects any record whose normalized
source project is Cli, Compress, Csv, JacksonDatabind, or Jsoup. Every reviewed mechanism stores:

- bug mechanism (`what`): violated semantic constraint and deviation;
- applicability (`where`): local conditions and compatible shapes;
- injection intent (`how`): transferable edit direction;
- expected buggy behavior, failure signal, evidence IDs, and structural units.

The external cache contains partial GHRB, Bears, and GitBug-Java sources. It does not contain a
complete five-source corpus, so the paper's 2,069 input records, 1,686 structures, and 1,325 reviewed
mechanisms were not reproduced.

### Structural representation and retrieval

`structure.py` preserves the published KITE grammar: `control_header`, `expression_center`, and
`statement_center` anchors; `condition_of`, `expr_in_stmt`, `guard_to_body`, `adjacent_stmt`, and
`same_block` relations; abstracted identifiers/literals; a coarse composition key; and the first 16
hex digits of SHA-1 over the canonical tree. Retrieval first filters compatible coarse keys, gives
identical fingerprints high confidence, otherwise uses multiset Jaccard, and fuses this with semantic
what/where/how similarity. The precise unpublished Java parser, embedding model, fusion weights, and
review rubric are reconstructed and recorded as deviations.

### Four experimental arms

- **Direct LLM:** one pass over fixed focal source plus lightweight repository context.
- **MutGen:** comments removed; an LLM summary plus PIT tuples `(id, mutated statement, status,
  operator)` are supplied; only survived/uncovered mutants drive subsequent generation; passing and
  repaired tests are unioned across iterations.
- **KITE:** semantic/structural retrieval produces ranked mechanisms; structured local injection plans
  pass locality, syntax/compilation, repository-compatibility, and behavioral-nontriviality gates;
  candidates are promoted only if fixed tests pass, the current injection is exposed, and prior kills
  are preserved.
- **Concept extension:** each mechanism becomes an explicit violated constraint, applicability
  condition, trigger input relation, and expected oracle. The same record is included in both the input
  construction and assertion construction instructions.

All arms use one common `call_budget` per matched task. A SQLite transaction charges calls and tokens
by `(task_id, arm)` and rejects calls beyond budget. KITE's original paper did not equalize calls;
this is a deliberate causal-control deviation requested for this experiment.

### Validity and statistics

A real bug is detected only when every fresh fixed-version execution passes, every fresh buggy-version
execution fails, and at least two independently launched executions per version have consistent exit,
timeout, and output-digest observations. This is stricter than KITE's published RBDR definition and is
the requested AnyPoC-style check.

RBDR uses every task in the declared population as denominator, including generation failures.
Comparisons use matched task IDs, a seeded paired bootstrap interval for the RBDR difference, and an
exact two-sided McNemar test over discordant outcomes.

## Infrastructure status

Java 21 and Maven 3.9.16 were already installed. A cached Temurin JDK 11.0.32.1 and Defects4J checkout
exist under `~/.local/kite`; after sourcing its environment, the Defects4J CLI starts correctly. An
initial direct invocation without the local Perl library path failed on missing `String::Interpolate`;
the task-specific environment supplies that module. External checkouts and 1.8 GiB of partial work
remain outside the repository.

PIT integration is implemented for Maven XML/CSV reports, but no experiment-level PIT run completed.
The KITE paper evaluated generic mutation with Major, while this protocol deliberately uses PIT to
match MutGen and the user's requirement.

Vertex configuration was loaded via the required untracked script before the only connectivity
attempt. The configured model family matched Gemini 3 Flash preview. The client then failed with a
DNS resolution `ServiceUnavailable` before receiving any model response. Shell downloads likewise
could not resolve GitHub. No credentials are stored in repository files.

## Results

### Implementation validation

`python -m pytest -q tests/test_kite_concept.py` reports **9 passed**. The command including the three
available style-reference modules reports **17 passed**. Tests cover deterministic
unit structures, de-leakage, dual retrieval, explicit concepts, all injection/promotion gates, PIT-
shaped MutGen feedback, stable re-execution, checkpoint budgets/resume, exact project split,
deterministic tuning selection, RBDR, bootstrap, and McNemar statistics. An unscoped repository-wide
`pytest` invocation cannot collect because the pre-existing `magma/test_llm.py` exits at import time
when its default Groq credentials are absent; this is unrelated to the new package. The targeted and
integration selections avoid that credentialed script and pass.

### Tuning subset (40 tasks)

| Arm | Detected / 40 | RBDR | Status |
|---|---:|---:|---|
| Direct LLM | — | — | Not completed: exact manifest incomplete and Vertex DNS blocked |
| MutGen | — | — | Not completed: exact manifest incomplete and Vertex DNS blocked |
| KITE | — | — | Not completed: KB/manifest incomplete and Vertex DNS blocked |
| Concept extension | — | — | Not completed: KB/manifest incomplete and Vertex DNS blocked |

### Full set (172 tasks)

| Arm | Detected / 172 | RBDR | Status |
|---|---:|---:|---|
| Direct LLM | — | — | Not completed: same blockers |
| MutGen | — | — | Not completed: same blockers |
| KITE | — | — | Not completed: same blockers |
| Concept extension | — | — | Not completed: same blockers |

For context only—not reproduction results—the KITE paper reports Direct 40/172 (23.26%), MutGen
90/172 (52.33%), and KITE 125/172 (72.67%). It reports KITE by project as Cli 18/24, Compress 26/32,
Csv 11/11, JacksonDatabind 33/51, and Jsoup 37/54. The paper has no concept-extension arm.

Because there are no matched experimental outcomes, no paired confidence interval or McNemar p-value
is reported. Reporting a statistic over paper aggregate rates would be invalid.

## Cost accounting

There were zero successful/billable LLM calls and zero measured input/output tokens in every arm. One
Vertex connectivity attempt failed during DNS resolution before a response; the checkpoint records it
as a failed setup event rather than an arm call. Active inspection/setup time in this session was
approximately 20 minutes; previously cached Defects4J/JDK downloads and 1.8 GiB of checkouts predated
the measured session, so their wall-clock time is unknown and not fabricated. No PIT compute time was
accrued for evaluated tasks.

## Limitations and next steps

The experiment needs an environment with DNS access to Vertex AI, completion of the 305-bug patch
scan, author confirmation or publication of the exact 172 IDs, complete five-source historical data,
and method-level PIT wiring for each project's build system. Once those are available, resume from the
SQLite state; do not rerun completed `(task, arm)` rows. First freeze the 40-task subset, tune only on
it, freeze all parameters, then run the other 132 tasks and report all outcomes—including null or
negative concept effects.

--- BEGIN ORCHESTRATOR SUMMARY ---

### 1. Files created or modified

- `kite_concept/__init__.py`
- `kite_concept/README.md`
- `kite_concept/checkpoint.py`
- `kite_concept/cli.py`
- `kite_concept/dataset.py`
- `kite_concept/evaluator.py`
- `kite_concept/extraction.py`
- `kite_concept/injection.py`
- `kite_concept/knowledge.py`
- `kite_concept/llm.py`
- `kite_concept/metrics.py`
- `kite_concept/models.py`
- `kite_concept/pit.py`
- `kite_concept/prompts.py`
- `kite_concept/protocol.py`
- `kite_concept/structure.py`
- `kite_concept/arms.py`
- `tests/test_kite_concept.py`
- `research/kite-concept-extension-2026-09-26.md`

### 2. Fidelity notes

- KITE: matches published what/where/how records, AST-unit grammar, SHA-1/16 fingerprints, dual recall,
  four injection gates, iterative feedback, and three-condition promotion gate. Deviations are a
  lexical Java parser, bag-of-words semantics, reconstructed fusion weights/prompts, PIT rather than
  the paper's Major evaluation, and the requested equal-call/independent-rerun controls.
- MutGen: matches summaries over comment-stripped source, PIT status/operator/statement tuples,
  survived/uncovered feedback, repair structure, and iterative union. Exact figure-only prompt wording
  and Mutahunter internals are unavailable; Defects4J projects are substantially harder than MutGen's
  standalone HumanEval/LeetCode subjects.
- Concept extension: faithfully adds all four requested fields and supplies trigger relations to input
  generation and expected oracles to assertion generation. It is new work with no paper ground truth.

### 3. RBDR results

| Population | Direct LLM | MutGen | KITE | Concept extension |
|---|---:|---:|---:|---:|
| Tuning subset (40) | Not completed: Vertex DNS/manifest | Not completed: Vertex DNS/manifest | Not completed: Vertex DNS/KB/manifest | Not completed: Vertex DNS/KB/manifest |
| Full run (172) | Not completed: same reason | Not completed: same reason | Not completed: same reason | Not completed: same reason |

### 4. Costs

- Direct LLM: 0 successful calls, 0 measured tokens, cost $0; one non-billable DNS-failed connectivity attempt.
- MutGen: 0 calls, 0 tokens, cost $0.
- KITE: 0 calls, 0 tokens, cost $0.
- Concept extension: 0 calls, 0 tokens, cost $0.
- Defects4J/PIT setup inspected for about 20 minutes in this session; cached setup/checkouts pre-existed,
  and no evaluated PIT run completed.

### 5. Open issues

- Vertex endpoint DNS resolution is blocked; no LLM arm can execute.
- KITE's exact 172 task IDs and official artifact are unpublished; reconstruction is incomplete.
- Only partial external KB sources/checkouts are cached; the 1,325 reviewed mechanisms are unavailable.
- PIT must be adapted and validated per Defects4J project's build layout.
- Full tuning and 172-task results, paired statistics, and honest effect assessment remain pending.

--- END ORCHESTRATOR SUMMARY ---
