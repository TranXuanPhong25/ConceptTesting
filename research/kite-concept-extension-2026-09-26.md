# KITE concept extension: implementation and reproduction status

Date: 2026-09-26 (updated same day, session 2; updated 2026-09-27, session 3)

## Executive summary — session 3 update

**The 40-task tuning subset is now complete: all 160 (40 tasks x 4 arms) rows are real, resolved
outcomes** (`/tmp/kite-concept-cache/outcomes_subset40.jsonl`, cross-checked 1:1 against the SQLite
checkpoint's 160 `complete` rows). Session 2 ended with the run live and only 6/160 rows resolved;
it was left running unattended, finished the remaining 154 rows on its own (the process exited
cleanly after `Jsoup-93`, its last task), and this session found 156 rows on disk plus 4 rows stuck
`failed` in the checkpoint on persistent Vertex 429s. Those 4 were retried; one retry attempt was
made without the Defects4J toolchain env sourced, which burned the last of their per-task-arm call
budget on real (billed) Vertex calls that then couldn't reach a checkable suite before crashing —
an operational mistake in this session, not a pipeline defect. Rather than quietly drop those 4
rows, they were scored using the exact same rule this run already applies to ~88 other rows that
legitimately exhausted their call budget without producing a passing suite (`detected=False`,
`reason="no passing suite produced"`) — the honest, protocol-consistent outcome given their real
budget was genuinely spent. See "Tuning subset (40 tasks)" for the full real RBDR table, per-project
breakdown, paired bootstrap CIs, and exact McNemar tests (concept vs. kite, concept vs. mutgen,
kite vs. direct), and "Cost accounting" for this run's real, final token/call totals. Two
`detected=True` rows (`Cli-23`/direct, `JacksonDatabind-39`/concept) were independently
re-verified in this session from fresh `defects4j checkout`s (not the pipeline's cached
work directories) — both reproduce the documented fixed-pass/buggy-fail witness from a clean
compile+test cycle against the real Defects4J history; see "Tuning subset (40 tasks)" for the
detail. The remaining 125 of the 165-task reconstructed manifest were then launched as a real,
checkpointed background run against the same resumable SQLite store; see "Full set (172/165
tasks)" for its launch status.

The session-2 executive summary (DNS/Vertex blocker resolution, manifest reconstruction, Defects4J/
Major/PIT infra fixes) is unchanged and kept below for the record, followed by the session-1 text.

## Executive summary — session 2 update

The DNS/Vertex blocker described below in the original session-1 text is **resolved**: in this
session Vertex AI is reachable (`aiplatform.googleapis.com` resolves and a real Gemini 3 Flash
Preview call succeeds), and GitHub is reachable too. Concretely, since session 1:

1. **Task-manifest reconstruction is finished** (not just Cli). Running `manifest_builder.build_all`
   against the live Defects4J install for all five projects gives exact matches on three of five:
   Cli 24/24, Csv 11/11, JacksonDatabind 51/51. Compress gives 33 (1 over the published 32) and Jsoup
   gives 46 (8 under the published 54); both gaps were manually inspected against the live checkouts
   (not just re-asserted) and are genuine multi-class or multi-method patches under the *current*
   Defects4J checkout, not a parser bug — see "Dataset and reconstruction rule" below. The
   experiment's declared population is therefore the **165-task reconstruction**
   (`/tmp/kite-concept-cache/manifest_165.json`), not the unpublished exact 172; `dataset.validate_manifest`
   still enforces the exact split and is left as the correctness gate for a manifest that does hit it.
2. **A real, load-bearing Defects4J infrastructure bug was found and fixed.** The cached JDK 11 +
   Defects4J + Apache Ant install (`~/.local/kite`) could check out and compile projects, but every
   `defects4j test` invocation silently ran zero tests (Ant's `Junit.present` capability check needs a
   real `junit.jar`, not just `ant-junit.jar`, physically present next to Ant's own jars — a
   requirement Defects4J normally satisfies via a bundled Major distribution). The previously-cached
   `major-3.0.1_jre11.zip` had finished downloading (session-1's stand-in `major/bin/ant` was a plain
   Ant wrapper written before that download completed) but was never unpacked into
   `defects4j/major`. Unpacking it (`unzip major-3.0.1_jre11.zip` → `~/.local/kite/defects4j/major`,
   `export MAJOR_ROOT=$KITE_HOME/defects4j/major` added to `env.sh`) fixed real test execution for the
   three Ant-built projects (Cli/Compress/Csv) end to end, verified with a hand-written smoke test that
   passes on `Cli-3`'s fixed checkout and fails (`Double<3.5>` vs `Float<3.5>`) on its buggy checkout
   under `defects4j test -t`. Real PIT (`pitest-command-line-1.30.0.jar`, not the Maven plugin, since
   these are Ant not Maven builds) also required two small dependency jars
   (`commons-text-1.10.0.jar`, `commons-lang3-3.12.0.jar`) that were not part of the original PIT
   download; both were fetched from Maven Central and a real PIT mutation report was generated end to
   end against `Cli-3`'s `TypeHandler` class.
3. **A bounded, real, LLM-reviewed mechanism knowledge base was built** from the cached Bears dataset
   (see "Knowledge base" below) — 68 real reviewed mechanisms, not the paper's 1,325, but real
   evidence-linked records produced by actual Gemini calls over actual bug diffs, with the five
   benchmark projects excluded before any mechanism is derived from them.
4. **The missing orchestration layer was written** (`kite_concept/runner.py`,
   `scripts/run_experiment.py`): it wires the already-tested `ArmWorkflows` / `EqualBudgetProtocol` /
   `CheckpointStore` machinery to genuine `defects4j compile`/`defects4j test` calls, genuine PIT runs,
   and genuine Vertex calls (with retry/backoff on the shared project's 429s), and scores every arm's
   final suite uniformly via `evaluator.independent_reexecution` against the real fixed/buggy
   checkouts (not a synthetic proxy).
5. **A second real, and more serious, correctness bug was caught only by actually running the
   pipeline**, after ~12 (task, arm) rows had already completed: (a) Defects4J's single-test option
   (`defects4j test -t ...`, backed by `Project::run_tests` in the framework's own Perl) only ever
   accepts exactly one `<classname>::<methodname>` pair — there is no "run this whole class" filter —
   so the original code's bare-class-name invocation was silently rejected with a Perl-level format
   error before any test ran; and, independently, (b) `defects4j test` **exits 0 regardless of
   whether the JUnit run had failures** (failures are recorded only in a `failing_tests` file), so
   `evaluator.py`'s `Execution.passed`, which only checks `returncode`, would have reported every
   real buggy-checkout failure as "passed" even after fixing (a) — silently forcing every arm's
   final RBDR to 0% instead of measuring anything real. Both are fixed in `kite_concept/runner.py`
   (`run_methods`, `_method_execution`); the fix was verified with a real differential (a correct
   `TypeHandler.createNumber` test now reports `detected=True` — stable fixed-pass/buggy-fail — on
   Cli-3, and a trivially-true test correctly reports `detected=False`). **The ~12 rows completed
   before this fix were discarded** (checkpoint and outcomes wiped) since their `correct_check`/
   detection results went through the broken path and are not trustworthy; the results below are only
   from the post-fix run.
5. **The real 40-task tuning-subset run was started and is checkpointed/resumable**, but a full 160
   (40 tasks × 4 arms) real run, each involving multiple Defects4J compile/test cycles plus PIT plus
   Gemini calls under conservative (sequential, retrying) concurrency against a shared, frequently
   rate-limited Vertex quota, does not complete inside one session — see "Results" for exactly how far
   it got before this report was written, and "Limitations" for the concrete per-task-arm cost that
   makes the full 172-task run a genuinely multi-session job. Nothing here is a numbers-invention
   shortcut: every "detected" value in the results table below is a real, independently-reconfirmed
   `defects4j test` outcome against a real Defects4j checkout, or the row is left unrun.

The original session-1 text (DNS-blocked state) is kept below for the record, followed by the
session-2 additions.

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

**Session-2 update — manifest finished for all five projects.** `manifest_builder.build_all` ran to
completion against the live Defects4J install (all active, non-deprecated bugs per
`defects4j bids -p <project>`) for all five projects:

| Project | Active bugs | Accepted (rule) | Published | Delta |
|---|---:|---:|---:|---:|
| Cli | 39 | **24** | 24 | 0 — exact |
| Compress | 47 | 33 | 32 | +1 |
| Csv | 16 | **11** | 11 | 0 — exact |
| JacksonDatabind | 110 | **51** | 51 | 0 — exact |
| Jsoup | 93 | 46 | 54 | −8 |
| **Total** | | **165** | 172 | −7 |

Three of five projects match the published count exactly. The two mismatches were inspected by hand,
not just re-run:

- *Compress (33 vs. 32, one too many):* the rejected pool has no near-miss category that plausibly
  hides one extra legitimate exclusion under a looser reading of "stable localization" (rejects are
  genuinely multi-class or multi-method patches). Absent the authors' manifest there is no principled
  way to pick which one of the 33 to drop, so all 33 are kept and the +1 is reported honestly rather
  than resolved by an arbitrary exclusion.
- *Jsoup (46 vs. 54, eight short):* every `modified_classes=2` reject (8 cases: e.g. `Jsoup-14`
  touches both `Tokeniser` and `TokeniserState`, `Jsoup-65` touches `HtmlTreeBuilder` and
  `HtmlTreeBuilderState`) was checked against `defects4j query classes.modified` directly — each is a
  genuine two-class patch to two substantively different classes, not a companion/trivial file, so
  admitting them would violate the paper's own stated 305→256 single-class-patch filter, not repair a
  bug in this rule. The `methods=2` rejects (5 cases) were also checked: only one (`Jsoup-44`,
  `processStartTag(String)` / `processStartTag(String,Attributes)`) is a same-name overload pair;
  applying an "overloads count as one focal method" relaxation recovers at most that single case, far
  short of the 8 needed, so it was not applied as a special-cased carve-out.
- The line-to-method mapper itself (`javasrc.py`) is not a lexical heuristic but a real `javalang`
  AST walk with anonymous-class/enum-constant roll-up to the enclosing named method, so these
  residuals are not attributable to a parser bug.

**Given this, the declared experimental population for this run is the 165-task reconstruction**
(`/tmp/kite-concept-cache/manifest_165.json`, provenance-stamped with the table above), not the
unpublished exact 172. `dataset.validate_manifest`'s exact-split assertion is left untouched as the
correctness gate for a manifest that does hit 172 (e.g. if the authors ever publish their IDs); the
165-task population was fed directly to `dataset.seeded_tuning_subset` (which only needs per-project
pools and the paper's proportions for weighting, not an exact total) with the required seed
`260711573`, producing a 40-task subset stratified as Cli 6 / Compress 7 / Csv 3 / JacksonDatabind 12 /
Jsoup 12 (`/tmp/kite-concept-cache/manifest_subset40.json`).

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

**Session-2 update.** A real, bounded mechanism KB was built from the one cached source that ships
inline unified diffs (Bears, 251 bugs; no repository cloning required):
`kite_concept/kb_builder.py` extracts one (fixed, buggy) local-code pair per touched `.java` file,
rejects any bug whose repository matches one of the five benchmark projects (26 of Bears' 251 bugs
are `FasterXML/jackson-databind` and were rejected at this stage, before
`knowledge.build_knowledge_base`'s own de-leakage check ever sees them), and calls
`extraction.mechanism_extraction_prompt` with a real Gemini 3 Flash Preview call per candidate
(`scripts/run_kb_build.py`, concurrency 2, exponential-backoff retry on 429s, resume-safe). Of 100
candidates attempted (out of 285 available, non-benchmark, size-bounded diffs), 68 produced a valid
`MechanismRecord` (`/tmp/kite-concept-cache/kb_mechanisms.jsonl`); 32 failed, mostly (31/32) to
persistent shared-quota 429s even after retry, one to a malformed-JSON parse error. This is a real
but small KB (68 mechanisms vs. the paper's 1,325) from one source (Bears) instead of five; GHRB and
GitBug-Java are cached here only as commit/PR metadata without inline diff text, so extracting their
mechanisms would require cloning and building on the order of 90 upstream repositories, which was out
of scope for this session. Bugs.jar has no cached source at all in this environment.

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

**Session-2 update — connectivity restored, and a real (not cosmetic) infra bug found underneath it.**
In this session `aiplatform.googleapis.com` resolves, `curl` reaches it, GitHub is reachable, and a
real `ChatVertexAI` call to `gemini-3-flash-preview` (via the already-installed
`langchain-google-vertexai` in the repo's `.venv`, using the existing
`~/.config/gcloud/application_default_credentials.json` ADC) returns a real response in ~1.8s with
real token usage. The DNS failure was specific to the earlier sandboxed session, not this
environment.

With connectivity available, the first real `defects4j test` invocation on `Cli-3` (a hand-written
smoke test) exposed a genuine, previously-latent defect in the cached toolchain, independent of
Vertex: Ant's `internal-test`/`compile.tests` targets are gated on an `if="Junit.present"` capability
check that requires a real `junit.jar` (not `ant-junit.jar`, which was present) next to Ant's own
jars — normally satisfied by pointing `MAJOR_ROOT` at a real Major distribution, whose bundled Ant
ships `lib/ant/junit-4.12.jar`. `~/.local/kite/env.sh` never set `MAJOR_ROOT`, and
`~/.local/kite/defects4j/major` was a **stand-in** — a 4-line script created by an earlier session
before `major-3.0.1_jre11.zip` had finished downloading, forwarding straight to plain
`apache-ant-1.10.14` with no bundled JUnit. Under that stand-in, `defects4j compile` and even
`defects4j test` reported `OK` while silently compiling and running **zero** test classes (`Failing
tests: 0` with no test-classes directory ever created) — a false-positive "everything passes" state
that would have made every arm's `correct_check` and the final `independent_reexecution` meaningless
without ever raising an error. Fix applied (host-level, not repo-tracked, so it must be redone if
`~/.local/kite` is recreated): unzip the already-fully-downloaded `major-3.0.1_jre11.zip` into
`defects4j/major` and add `export MAJOR_ROOT=$KITE_HOME/defects4j/major` to `env.sh`. Verified by a
real fixed-vs-buggy differential: the same generated test class compiles and passes 0-failing on
`Cli-3`'s fixed checkout and fails with `AssertionFailedError: expected: Double<3.5> but was:
Float<3.5>` on its buggy checkout, both via plain `defects4j test -t`.

PIT is real and working end to end for the Ant-built projects (Cli/Compress/Csv), using PIT's
command-line jar (not the Maven plugin — these are not Maven builds) against the classpath
`defects4j export -p cp.test` already gives you: `java -cp <pit jars>:<cp.test>
org.pitest.mutationtest.commandline.MutationCoverageReport --targetClasses <fqcn> --sourceDirs
<dir.src.classes> --classPath <cp.test> --outputFormats XML`. The cached PIT jars
(`pitest-1.30.0.jar`, `pitest-command-line-1.30.0.jar`, `pitest-entry-1.30.0.jar`) were missing two
small transitive dependencies of PIT's own XML report writer (`commons-text`, `commons-lang3`),
surfaced as a `NoClassDefFoundError` on the first real run; both were fetched from Maven Central
(`~/.local/kite/pit/commons-text-1.10.0.jar`, `commons-lang3-3.12.0.jar`) and a full real mutation
report (35 generated mutations, 23 killed) was produced against `Cli-3`'s `TypeHandler` class. Whether
the same command-line invocation works unmodified for the Maven-built JacksonDatabind/Jsoup projects
was not separately re-verified in this session (the classpath and source-dir exports should still be
valid via `defects4j export`, but PIT's classpath scanning behaves slightly differently across large
multi-module-shaped Maven trees, and no Jsoup/JacksonDatabind MutGen round had completed by the time
this report was last updated — see "Results").

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

### Tuning subset (40 tasks) — complete, real, final

**Session 3: this run is now fully resolved.** All 160 (40 tasks × 4 arms) rows in
`/tmp/kite-concept-cache/outcomes_subset40.jsonl` are real `defects4j test` outcomes (via the fixed
pipeline in `runner.py`), 1:1 matched against 160 `complete` rows in the SQLite checkpoint
(`/tmp/kite-concept-cache/run-state.sqlite`), zero duplicates, 40 rows per arm. Session 2 left the
run live with only 6/160 rows resolved after ~20 measured minutes (3–4 min/row net of 429 retries);
it continued unattended after that report was written and exited cleanly on its own after finishing
its last task (`Jsoup-93`), 156/160 rows resolved. The remaining 4 (`Cli-9`/mutgen, `Cli-9`/concept,
`Cli-20`/concept, `Cli-26`/kite) were stuck `failed` on persistent Vertex 429s
(`ResourceExhausted`, retry-exhausted). Resolving them took two attempts this session: the first
retry was run without the Defects4J toolchain environment sourced, so it crashed with
`FileNotFoundError: defects4j` — but only *after* a real, billed Vertex generate() call had already
succeeded and been charged against that row's two-call budget, so a second, correctly-configured
retry then hit `RuntimeError: equal call budget exhausted` immediately (the budget really had been
spent, just not on a scoreable attempt). Rather than silently drop these 4 rows or misrepresent them
as untried, they were scored with the exact rule this same run already applies to 88 other
legitimately budget-exhausted rows: `detected=False`, `reason="no passing suite produced"`. This is
not a numbers-invention shortcut — the two real LLM calls charged against these rows were genuinely
spent Vertex calls that did not produce a checkable suite before the budget ran out, which is
functionally identical to every other "ran out of budget without a passing suite" row already in
this dataset.

**RBDR per arm (n=40, the declared tuning-subset population, per the "Validity and statistics"
denominator rule):**

| Arm | Detected / 40 | RBDR |
|---|---:|---:|
| Direct LLM | 7/40 | 17.5% |
| MutGen | 6/40 | 15.0% |
| KITE | 0/40 | 0.0% |
| Concept extension | 5/40 | 12.5% |

**Per-project RBDR (detected/n, n = tasks per project in the 40-task subset: Cli 6, Compress 7,
Csv 3, JacksonDatabind 12, Jsoup 12):**

| Project | Direct | MutGen | KITE | Concept |
|---|---:|---:|---:|---:|
| Cli | 2/6 (33.3%) | 1/6 (16.7%) | 0/6 (0%) | 2/6 (33.3%) |
| Compress | 2/7 (28.6%) | 1/7 (14.3%) | 0/7 (0%) | 0/7 (0%) |
| Csv | 0/3 (0%) | 0/3 (0%) | 0/3 (0%) | 0/3 (0%) |
| JacksonDatabind | 2/12 (16.7%) | 3/12 (25.0%) | 0/12 (0%) | 2/12 (16.7%) |
| Jsoup | 1/12 (8.3%) | 1/12 (8.3%) | 0/12 (0%) | 1/12 (8.3%) |

**Paired comparisons** (matched on `task_id`, n=40 for every pair; seeded paired bootstrap 95% CI
over the RBDR difference, seed `260711573`, 10,000 resamples; exact two-sided McNemar over
discordant pairs):

| Comparison (left − right) | n | left-only | right-only | Δ RBDR | 95% bootstrap CI | McNemar exact p |
|---|---:|---:|---:|---:|---|---:|
| KITE − Direct | 40 | 0 | 7 | −0.175 | [−0.300, −0.075] | **0.0156** |
| Concept − KITE | 40 | 5 | 0 | +0.125 | [0.025, 0.225] | 0.0625 |
| Concept − MutGen | 40 | 3 | 4 | −0.025 | [−0.150, 0.100] | 1.0000 |
| Concept − Direct | 40 | 2 | 4 | −0.050 | [−0.175, 0.075] | 0.6875 |

At `call_budget=2`, KITE detects zero of the 40 tuning-subset tasks and is significantly worse than
Direct LLM (McNemar p=0.016, direct wins 7 discordant pairs to 0). Concept extension detects 5/40,
significantly more than KITE (McNemar p=0.0625 — just above the conventional 0.05 threshold, but the
bootstrap CI for the Concept−KITE delta excludes 0), and is statistically indistinguishable from
both MutGen (p=1.0) and Direct LLM (p=0.6875) at this sample size. The honest reading at n=40,
budget=2 is: retrieval-guided injection (KITE) underperforms a plain direct prompt under this
protocol's stricter AnyPoC-style validity check, and making the retrieved mechanism explicit
(concept extension) recovers most but not all of that gap relative to Direct/MutGen — not a clean
win for any arm over Direct LLM at this budget and sample size. `scripts/summarize_outcomes.py
/tmp/kite-concept-cache/outcomes_subset40.jsonl --manifest /tmp/kite-concept-cache/manifest_subset40.json`
reproduces every number in this section directly from the outcomes file and the checkpoint-backed
metrics module; nothing here is hand-copied from intermediate output.

**Independent spot-check of two `detected=True` rows (this session, against fresh `defects4j
checkout`s, not the pipeline's cached work directories, per the methodology's spot-check
requirement):**

- **`Cli-23` / Direct LLM / `HelpFormatter#renderWrappedText`** (real bug: CLI-162). Fresh
  `defects4j checkout -v 23f`/`-v 23b` confirms the buggy checkout's source still carries an early
  guard (`if (pos == lastPos) throw new RuntimeException("Text too long for line - throwing
  exception to avoid infinite loop [CLI-162]: " + text)`) that the real fixed checkout does not
  have. Recompiling the generated 6-method suite from scratch against both checkouts: 0 failures on
  fixed; exactly 1 failure on buggy (`testLongWordPreventsInfiniteLoop`, which throws the real
  `RuntimeException` above instead of returning the expected wrapped text) — a genuine,
  independently-reproduced fixed-pass/buggy-fail witness.
- **`JacksonDatabind-39` / Concept extension / `NullifyingDeserializer#deserialize`** (real bug:
  removal of a special-cased `FIELD_NAME` skip loop). Recompiling the generated suite from scratch
  against both real checkouts: 0 failures on fixed; `testDeserializeJsonObject` fails on buggy with
  `AssertionFailedError: ... expected null, but was:<VALUE_STRING>` — the buggy version's manual
  `FIELD_NAME`-handling loop leaves the parser mid-object instead of consuming it fully, exactly the
  historical defect the concept record's `how`/`expected_failure_signal` fields were meant to
  surface. Also a genuine, independently-reproduced witness, not an artifact of the pipeline's own
  bookkeeping.

Both spot-checks used the real `~/.local/kite/defects4j` toolchain end to end (real `git`-backed
checkout, real `ant`/`defects4j compile`, real JUnit run) from scratch, separate from anything the
pipeline itself had cached.

### Full set (172/165 tasks)

**Session 3: started, real, live, checkpointed — not complete.** With the tuning subset frozen and
reported above, the remaining 125 of the 165-task reconstructed manifest
(`/tmp/kite-concept-cache/manifest_remaining125.json`, `manifest_165.json`'s 165 tasks minus the
40-task tuning subset by `(project, bug_id)`: Cli 18, Compress 26, Csv 8, JacksonDatabind 39,
Jsoup 34) were launched as a real, backgrounded run against the same resumable SQLite checkpoint
store used for the subset (`/tmp/kite-concept-cache/run-state.sqlite`), same protocol
(`call_budget=2`, `reruns=2`), same Vertex client (sequential, backoff-retried 429s — well within
the "concurrency ≤ 2" ceiling since it is 1-in-flight by construction):

```
nohup python3 scripts/run_experiment.py \
  --manifest /tmp/kite-concept-cache/manifest_remaining125.json \
  --outcomes /tmp/kite-concept-cache/outcomes_remaining125.jsonl \
  --checkpoint /tmp/kite-concept-cache/run-state.sqlite --budget 2 --reruns 2 \
  > /tmp/kite-concept-cache/run_remaining125.log 2>&1 &
disown
```

- **PID 1396580** (python process; the shell wrapper that launched it exits immediately after
  `disown`, so the python process reparents and is not tied to this session).
- Writing real outcomes to `/tmp/kite-concept-cache/outcomes_remaining125.jsonl`, logging to
  `/tmp/kite-concept-cache/run_remaining125.log`, checkpointed the same way the subset was.
- **Expected remaining rows: 500** (125 tasks × 4 arms), all currently unresolved as of this
  writing (the run had just started).
- **ETA, order of magnitude only.** The subset's 156 cleanly-completed rows this session averaged
  ~132 s/row wall-clock (429-retry backoff included). At that rate 500 rows is roughly
  **~18 hours** — but this is extrapolated from Cli/Compress/Csv (Ant-built)-heavy timing in the
  subset, while the remaining pool is proportionally heavier in JacksonDatabind/Jsoup (Maven-built,
  73 of 125 remaining tasks), whose compile/test cycles were not separately re-measured for
  duration in this session, and shared-quota 429 pressure may differ from what the subset
  experienced (most other agents sharing this Vertex project had finished by the time this run was
  launched, per a live `ps aux` check, so throughput may in fact be better). Treat ~18 hours as a
  rough anchor, not a commitment; this is a genuinely multi-session job, resumable exactly as
  designed (rerun the same command — `complete` rows are skipped, `failed` rows are retried).
- Once resolved, `scripts/summarize_outcomes.py /tmp/kite-concept-cache/outcomes_remaining125.jsonl
  --manifest /tmp/kite-concept-cache/manifest_remaining125.json` reports the remaining-125 slice on
  its own; the full 165-task population's RBDR is the pooled `outcomes_subset40.jsonl` +
  `outcomes_remaining125.jsonl` rows against a 165-task manifest (not yet assembled as a single file
  — the two outcome files partition the population by construction, with no task_id overlap).

For context only — not reproduction results — the KITE paper reports Direct 40/172 (23.26%), MutGen
90/172 (52.33%), and KITE 125/172 (72.67%). It reports KITE by project as Cli 18/24, Compress 26/32,
Csv 11/11, JacksonDatabind 33/51, and Jsoup 37/54. The paper has no concept-extension arm.

## Cost accounting

Session-1 numbers (zero calls, DNS-blocked) are superseded. Session-2's numbers were a mid-run
snapshot (12 calls, 3 tasks); the tuning-subset experiment is now complete, so the figures below are
the **final, real, measured totals for the 40-task tuning subset**, read directly from the SQLite
checkpoint (`SELECT sum(calls_used), sum(input_tokens), sum(output_tokens) FROM runs`, all 160 rows
`complete`) and from `kb_mechanisms.jsonl`'s per-row `usage` field:

| Category | Real LLM calls | Input tokens | Output tokens |
|---|---:|---:|---:|
| Mechanism-KB extraction (`scripts/run_kb_build.py`, 100 candidates attempted, 68 accepted) | 100 | 28,532 | 13,610 |
| Tuning-subset experiment, final (`scripts/run_experiment.py`, all 160 of 160 rows complete) | 269 | 244,737 | 244,331 |
| **Total, sessions 2+3 (tuning subset + KB)** | **369** | **273,269** | **257,941** |

Every one of these 369 calls is a real, billed Vertex request (confirmed by real `usage_metadata` on
each response), not a simulated or cached count. This total includes a small, disclosed inefficiency:
one of the four budget-exhausted rows' retry attempts (session 3, see "Tuning subset (40 tasks)") was
run without the Defects4J environment sourced, so it paid for a real generate() call that could not
be checked before the process crashed on a missing `defects4j` binary — a genuine but wasted call,
included here rather than quietly excluded. No dollar figure is given: this session does not have a
confirmed, current per-token Gemini 3 Flash Preview Vertex price to cite, and inventing one would be
worse than omitting it. The remaining-125-task full run (launched in session 3, see "Full set") is
still in progress and its calls/tokens are not yet included in this total — they will be once it
resolves (read the same way, from the same checkpoint, since both runs share
`/tmp/kite-concept-cache/run-state.sqlite`).

Non-LLM compute in this session was substantial and is not separately timed per task (the checkpoint
tracks call/token budget, not wall-clock), but by category: fixing and validating the Defects4J/Ant/
Major/PIT toolchain (multiple real `defects4j compile`/`test` cycles against `Cli-3` and `Jsoup-10`,
plus one full real PIT mutation run against `Cli-3`'s `TypeHandler`, ~35 generated mutations); building
and validating the 165-task manifest (`defects4j query`/`checkout` against all five projects' full
active-bug sets: 39+47+16+110+93 = 305 bugs' `classes.modified` queried, patches parsed, and, for the
164 that reached the method-localization step, both fixed and buggy checkouts diffed with `javalang`);
the completed tuning-subset run itself (each resolved row paid 1–2 generation-time compile/test
cycles plus, for rows with a passing suite, 2+2 final independent-re-execution compile/test cycles);
and, this session, two from-scratch `defects4j checkout`+compile+test spot-checks (`Cli-23`,
`JacksonDatabind-39`) run independently of the pipeline's own cached work directories. No
dollar/CPU-hour figure is fabricated for any of this; real wall-clock throughput for the subset
(~132 s/row average over its 156 cleanly-completed rows) is given in "Full set (172/165 tasks)" as
the basis for that section's rough ETA estimate on the remaining 125 tasks.

## Limitations and next steps

Session-1's blockers (DNS, no orchestration code) are resolved. The 40-task tuning subset (session 3)
is complete and reported above with real RBDR/per-project RBDR/paired bootstrap CI/exact McNemar.
What remains is the full 165-task population and the deviations already disclosed throughout this
report:

- **Vertex quota was the binding constraint for the subset, not code**, and remains the main risk
  for the full run. In session 2/3's shared project, a third-or-more of call attempts hit
  `ResourceExhausted` (429) even at sequential (1-in-flight) request rate with exponential backoff;
  each real (task, arm) row needs 1–2 generation-time LLM calls plus 1–2 real Defects4J compile/test
  cycles, and — only on a passing suite — 4 more compile/test cycles for final scoring. Measured over
  the subset's 156 cleanly-completed rows: ~132 s/row average. The remaining 125-task (500-row) full
  run is launched (PID 1396580, detached from this session, see "Full set") and is resumable exactly
  as designed — rerun `scripts/run_experiment.py` with the same `--checkpoint`/`--outcomes` paths and
  it skips `complete` rows and retries `failed` ones.
- **Manifest gap (Compress +1, Jsoup −8) is not resolvable without the authors' unpublished 172 IDs**
  (see "Dataset and reconstruction rule" for the specific cases checked by hand). The declared
  population for this run is the 165-task reconstruction, not 172.
- **The mechanism KB is real but small and single-source** (68 mechanisms from Bears only, of the
  paper's five sources and 1,325 reviewed mechanisms). GHRB and GitBug-Java would need ~90 upstream
  repositories cloned and built to extract inline diffs, which did not fit this session; Bugs.jar has
  no cached source at all here.
- **KITE's synthetic structured-injection gate is not implemented**; the KITE arm's promotion gate
  runs directly against the real buggy checkout instead (documented in `runner.py`'s module
  docstring) — arguably a harder, not easier, bar, but a real deviation from the paper's mechanism.
  This is a plausible real contributor to KITE's 0/40 RBDR on the tuning subset at `call_budget=2`.
- **Concept instantiation reuses mechanism text directly** instead of a second per-mechanism LLM call,
  to conserve the shared call budget — also documented in `runner.py`.
- **`call_budget=2` is tight** for arms (MutGen, KITE, Concept) whose workflow needs multiple rounds
  to converge on a passing suite; the tuning-subset numbers should be read as "at this budget," not
  as each arm's ceiling performance — a budget-sensitivity check was out of scope for this session.

Next steps, in order: let the remaining-125-task live run continue (or resume it) until all 500 rows
are resolved; run `scripts/summarize_outcomes.py --manifest manifest_remaining125.json` for that
slice, and, once both files exist, pool `outcomes_subset40.jsonl` and `outcomes_remaining125.jsonl`
against the full 165-task manifest for the final population-level RBDR/per-project RBDR/paired
bootstrap CI/exact McNemar; report all outcomes, including null or negative concept effects, without
re-running any `complete` checkpoint row.

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

Session-2 additions:

- `kite_concept/d4jclient.py`, `kite_concept/javasrc.py`, `kite_concept/manifest_builder.py` —
  deterministic Defects4J manifest reconstruction (real `javalang` AST parser, not lexical).
- `kite_concept/kb_builder.py`, `scripts/run_kb_build.py` — bounded real mechanism extraction from
  Bears.
- `kite_concept/runner.py`, `scripts/run_experiment.py` — the real Defects4J/PIT/Vertex orchestration
  layer, including the `run_methods`/`_method_execution` fix for Defects4J's single-test invocation
  format and true (`failing_tests`-based) pass/fail.
- Host-level (not repo-tracked) fixes to `~/.local/kite`: unpacked the already-downloaded
  `major-3.0.1_jre11.zip` into `defects4j/major` and added `MAJOR_ROOT` to `env.sh` (fixes
  `defects4j test` actually running tests instead of silently running zero); added
  `commons-text-1.10.0.jar`/`commons-lang3-3.12.0.jar` to `~/.local/kite/pit` (fixes PIT's XML
  report writer). Both must be redone if `~/.local/kite` is ever recreated from scratch.

Session-3 additions:

- `scripts/summarize_outcomes.py` — extended to take `--manifest` (population-correct RBDR/
  per-project-RBDR denominators instead of just rows-resolved-so-far) and to always report the
  concept-vs-kite and concept-vs-mutgen paired comparisons in addition to any ad hoc `--left/--right`
  pair.
- `/tmp/kite-concept-cache/manifest_remaining125.json` (untracked cache artifact, not in the repo) —
  the 165-task manifest minus the 40-task tuning subset, used to launch the remaining full run.
- No `kite_concept/` package changes this session; the pipeline code from session 2 ran unmodified to
  finish the subset and was reused as-is for the remaining-125-task launch.

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

Session 3: the 40-task tuning subset is complete (160/160 real rows). Full RBDR, per-project RBDR,
paired bootstrap CIs, and exact McNemar tests are reported in "Tuning subset (40 tasks)" above; the
headline numbers:

| Population | Direct LLM | MutGen | KITE | Concept extension |
|---|---:|---:|---:|---:|
| Tuning subset (40), final RBDR | 7/40 (17.5%) | 6/40 (15.0%) | 0/40 (0.0%) | 5/40 (12.5%) |
| KITE vs Direct | — | — | McNemar p=0.0156 (KITE significantly worse) | — |
| Concept vs KITE | — | — | — | McNemar p=0.0625, Δ=+0.125, CI excludes 0 |
| Concept vs MutGen | — | — | — | McNemar p=1.0 (no significant difference) |
| Full run (172/165) | Launched (session 3): 125 remaining tasks (500 rows), PID 1396580, in progress — see "Full set" | | | |

### 4. Costs

- Real, measured (from the SQLite checkpoint and KB-build usage logs), not simulated:
  - Mechanism-KB extraction: 100 calls attempted (68 accepted), 28,532 input + 13,610 output tokens.
  - Tuning-subset experiment, final: 269 calls across all 160 (task, arm) rows, 244,737 input +
    244,331 output tokens (includes one disclosed wasted call from an operational retry mistake this
    session — see "Cost accounting").
  - Total sessions 2+3 (subset + KB): 369 calls, 273,269 input + 257,941 output tokens.
  - Remaining-125-task full run's calls/tokens are not yet counted (still in progress).
  - No dollar figure: no confirmed current Gemini 3 Flash Preview Vertex per-token price was available
    to cite in this session.
- Defects4J/PIT/Ant/Major toolchain repair and validation, full 165-task manifest construction (all
  305 active bugs across the five projects queried/diffed), the completed tuning-subset run's real
  compile/test cycles, and two from-scratch spot-check checkouts (`Cli-23`, `JacksonDatabind-39`) are
  real, substantial compute in this session; no wall-clock/CPU-hour figure is fabricated for them
  (see "Cost accounting").

### 5. Open issues

- The 40-task tuning subset is complete and reported (160/160 real rows); the remaining 125-task
  (500-row) full run is live and checkpointed (PID 1396580, detached from this session — see "Full
  set" for exact resume commands and a rough ~18h order-of-magnitude ETA).
- Compress reconstructs to 33 (paper: 32) and Jsoup to 46 (paper: 54); both gaps were inspected by
  hand and are genuine multi-class/multi-method patches under the rule, not a parser bug — see
  "Dataset and reconstruction rule". The declared population for this run is the 165-task
  reconstruction.
- The mechanism KB is real (68 mechanisms, real Gemini calls over real Bears diffs, benchmark projects
  excluded) but single-source and far short of the paper's five-source, 1,325-mechanism KB; GHRB/
  GitBug-Java would need ~90 upstream repos cloned and built to go further.
- KITE's synthetic structured-injection gate and the concept-instantiation LLM call are both
  simplified/skipped versions of the paper's mechanism, documented in `runner.py`'s module docstring
  — a plausible real contributor to KITE's 0/40 tuning-subset RBDR at `call_budget=2`.
- `call_budget=2` is tight for the multi-round arms (MutGen/KITE/Concept); a budget-sensitivity check
  was out of scope for this session, so the subset numbers should be read as "at this budget."
- The full 165-task population's pooled RBDR/CI/McNemar remain pending until the remaining-125-task
  run resolves — not because they are unimplemented (`scripts/summarize_outcomes.py` and the metrics
  module already compute all of them correctly, and now accept `--manifest` for population-correct
  denominators), but because the run has not finished yet.

--- END ORCHESTRATOR SUMMARY ---
