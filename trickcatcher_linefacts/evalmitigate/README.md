# EvalAndMitigate baselines for TrickCatcher/HumanEval

This folder adapts **Only Doc** (`onlydoc`) and **Advanced Doc** (`advdoc`) from
the ISSTA'26 paper *Evaluating and Mitigating the Misguidance Effect of Buggy
Code in LLM-Generated Unit Tests*. Prompt sources are the local replication
package's `EvalAndMitigate/Prompt_example/Test_Generation_Prompt` and
`Advanced_Docstring_Prompt_Base_Model`. The replication package is read-only.

The default input is `../out/tasks_v3m2_all.json`: 133 tasks, 113 dev and 20
pilot. The bundle and its mined validators are used unchanged; generation
does not load canonical solutions, evaluation labels, or run the PUT.

| File | Purpose |
| --- | --- |
| `prompts.py` | Exact adapted templates, prompt construction, seeds, Part 3 parser |
| `run.py` | Cached generation/resume, existing evaluator, existing oracle pipeline |
| `test_evalmitigate.py` | Canned CPU tests and frozen existing-prompt checks |
| `__init__.py` | Package marker |

## Method and adaptations

`onlydoc` passes only the original function signature and docstring to test
generation. `preconditions.specification(task)` removes implementation,
decorators, and surrounding module code. Metadata comes from this stripped
AST; missing annotations are reported as `unspecified`. Base tests, mined
requirements, coverage facts, and witnesses are absent from both test prompts.

`advdoc` first presents the full PUT, including its original docstring, in the
adapted three-part review prompt: critical analysis, corrected implementation,
final requirement docstring. This stage runs once per task and is shared by
all K samples. The corrected implementation is saved as part of the response
and is never executed or passed to test generation. Stage 2 uses exactly the
`onlydoc` template with the original signature and generated docstring, in a
fresh conversation containing no stage-1 analysis, implementation, or history.

Every deviation from the Java prompt examples:

1. Java developer/test methods become Python developer/test functions. Java 11
   and JUnit 4 become Python assertions; Java code fences become Python fences;
   `null` checks become `None` checks. The wording and ordering of the coverage
   request and all three review parts are retained.
2. The example Java method/docstring is replaced with the task's actual
   specification or PUT. Java package/class ownership, constructors, and other
   methods are omitted because these tasks are standalone functions. The
   full signature, name (test prompt), parameter names/types, and return type
   are derived from the Python signature. Python parameter types replace
   Java's “parameters come from” field; unspecified types are not inferred.
3. Python triple quotes replace `/** ... */`. The final docstring is requested
   inside `<FINAL_DOCSTRING>...</FINAL_DOCSTRING>` to disambiguate it from the
   corrected implementation's docstring. The parser accepts either triple-quote
   style, a quoted docstring under the Part 3 heading without the marker, or
   plain prose within the explicit marker. Missing, empty, unclosed, invalid,
   or ambiguous results fall back to the **original** docstring. `parsed.json`
   records `parse_failure` and `used_fallback`; every advdoc row carries the
   failure reason. Part 2's docstring is never used as a fallback.
4. Both requests add the harness's existing expert-tester system message.
   Test generation appends `prompts.TAIL` verbatim, preserving the existing
   limit of 10 assertions, equality-oracle syntax, valid-input instruction,
   specification-derived expectations, and single Python block output. Its
   reference to “this implementation” is retained even when only the spec is
   visible, to keep the common assertion instruction byte-identical.
5. The harness uses K=3 independently seeded test samples and its existing
   scoring instead of Java compilation/JUnit execution. There is no repair,
   regeneration, filtering, or execution of the proposed corrected implementation.

Test generation uses temperature **0.7**, top_p **0.95**, max_tokens **1024**.
Advanced Doc stage 1 uses temperature **0**, top_p **1**, max_tokens **4096**.
Requests go through `llm_client.Client`, which hashes messages and all sampling
parameters for its response cache. The model must be Qwen2.5-Coder-7B-Instruct.

The seed scheme preserves `run_gen`'s 1000-sample stride and 8-stage stride,
while assigning new arms a disjoint range without editing existing seeds:

```text
arm_index: onlydoc=0, advdoc=1
index = 250000 + task_id * 2 + arm_index
seed = 20261010 + ((index * 1000 + sample) * 8 + stage * 2)
stage=0 for test generation; stage=1, sample=0 for Advanced Doc stage 1
```

The full default job makes **931 logical requests**: 798 test generations and
133 shared docstring generations. Cached requests avoid new model calls.
Shared stage-1 calls/tokens/time are charged only to `advdoc` sample 0, so sums
across `gen.jsonl` count each request once.

## Artifacts, resume, and scoring

Default generation output: `../out/gen2_qwen7b_evalmitigate/`.

- `manifest.json`: normalized task-bundle SHA256, PREREG.md SHA256, source
  hashes, model, K, arms, seed scheme, sampling settings, hashes of both
  original Java prompt files, and hashes of the exact adapted prompt constants,
  system message, and common assertion tail.
- `tasks.json`: copied task bundle, retaining splits, facts, and validators.
- `gen.jsonl`: the direct-arm `run_gen.py` row schema (`task`, `split`, `arm`,
  `sample`, `model`, `text`, `run_id`, `facts_version`, call/token/time metadata),
  plus the seed, exact message SHA256, and advdoc parse status.
- `advanced_doc/<task>/prompt.json`, `response.json`, `parsed.json`: exact
  stage-1 messages, full response, parsed/fallback docstring and provenance.
- `artifacts/<task>/<arm>/<sample>/prompt.json`, `direct_response.json`,
  `result.json`: exact test-generation messages and outputs.
- `eval.jsonl` and `eval_jobs/`: the existing `evaluate.py` o0 scoring path.

Re-run the same generate command to resume. Completed JSONL rows and saved
sample artifacts are reused; stage-1 responses survive interrupted tasks.
Changed inputs, source, prompt constants, model, K, arms, or prereg hash require
a fresh `--out`. Evaluation rejects incomplete or duplicate cohorts.
CLI output directories must be below `trickcatcher_linefacts/out/`; the library
API permits temporary directories for tests. Use a separate output directory
for a subset or K=1 smoke, rather than changing a full run's configuration.

The oracle wrapper delegates `collect`, `llm` (B1/ref/post), and `score` (including
B4 judgments and ref/full reporting) to `oracle_b01.py`. It copies reusable
JSON response entries from `out/oracle_b01/cache/` into the new oracle cache;
lock files and usage logs are omitted. Existing matching ref/post requests
therefore hit cache. Re-oracling uses the tasks' **original** specifications,
as in the existing pipeline, rather than the generated advdoc docstrings.
An oracle manifest freezes the evaluated cohort, generation manifest, oracle
source, and prereg hash to protect execution/judge caches from cohort changes.
`score` can still call Qwen for uncached B4 judgments; `score --no-llm` abstains
on those. Oracle scoring inherits the existing EvalPlus data and variant-path
requirements and expects the full dev/pilot cohort.

The endpoint is read only by `Client` from `QWEN_BASE_URL`; it is absent from
configuration, manifests, artifacts, and logs. Response writes also redact
known endpoint/token values, including old cache hits. Transport failures print
only the exception class. No endpoint or credential belongs in command files.

## Outside edits (complete list)

Only `../gen_evaluation.py` was edited: its local report-arm tuple appends
`("onlydoc", "advdoc")`. The original arm order and input-arm classification
are unchanged; absent new arms produce identical report text. `evaluate.py`
and `oracle_b01.py` already accept arbitrary arm names and were left unchanged.
No existing generation prompts or seeds, `vendor/`, `EvalAndMitigate/`,
PREREG.md, or RESULTS.md were edited. No commit or push was performed.

## Verification and real commands

Run from `/home/phong/dev/ConceptTester`:

```bash
python3 -B -m unittest trickcatcher_linefacts.evalmitigate.test_evalmitigate -v
python3 -B -m unittest trickcatcher_linefacts.test_concept_toolinput -v
```

The new suite covers all 133 tasks' implementation isolation, parser/fallback
cases, K=3 sharing/settings/costs, disjoint seeds, interrupted resume, manifests,
secret redaction, oracle delegation/cache copying, and a real two-task K=1
smoke through namespace-isolated `evaluate.py` workers using canned responses.
It freezes hashes of existing prompt/evaluator/oracle source and of **1,064**
existing prompt messages captured before edits, and checks byte-identical
existing-arm report text. The affected existing combined-arm suite also passes.
The existing evaluator emits ResourceWarnings for its unclosed file handles;
these do not fail either suite. No real model was contacted during verification.

For the real job, provide `QWEN_BASE_URL` through the environment before running
these commands; do not put its value in files or logs:

```bash
source scripts/research_env.sh
export QWEN_MODEL=qwen2.5-coder-7b-instruct
python3 -B -m trickcatcher_linefacts.evalmitigate.run generate --workers 16
python3 -B -m trickcatcher_linefacts.evalmitigate.run evaluate
python3 -B -m trickcatcher_linefacts.evalmitigate.run oracle collect
python3 -B -m trickcatcher_linefacts.evalmitigate.run oracle llm --workers 16
python3 -B -m trickcatcher_linefacts.evalmitigate.run oracle score --workers 12
```

The last three commands can also be run as `oracle all --workers 16`.
The oracle output defaults to `../out/oracle_evalmitigate/`.
Generation supports `--task-ids`, `--k`, `--arms`, `--tasks`, and `--out`;
evaluation supports `--out`; the oracle wrapper supports `--run` and `--out`.

## Advdoc hybrid clone (v4 bundle, two new arms)

`run_advhyb.py` clones the hybrid branch of `run_v4.run()` onto saved Advanced
Doc tests. It defaults to `out/tasks_v3m2hyb_v4.json` (133 tasks, v3m2 facts in
v4 bundle format), K=3, and exactly `advdoc-hybrid` / `advdoc-plainhybrid`.
The existing advdoc job is a required input; it is never regenerated.

For each `(task, sample)`, both arms read the corresponding `advdoc` row from
`out/gen2_qwen7b_evalmitigate/gen.jsonl`. Existing `assertions` are used when
present; otherwise `run_v4.assertions()` extracts them from `text`, with the
same per-completion cap. The saved advdoc logical calls/tokens/time are
attributed to both arms, as run_v4 does for shared round one; these are reused
costs, not new physical requests. Advdoc's shared doc-generation cost remains
charged to sample 0 according to its original row.

`advdoc-hybrid` uses the unchanged `run_v4.classify()` / v4 worker and B5
validator to classify round-one inputs against `task['concept_meta']`. Each
shown fact without a valid hit gets a request built by the unchanged
`v4_prompts.hybrid_messages(task, fact, round1)`, including TARGET, the original
specification, PUT, base tests, and domain strategy. Strategies are checked and
drawn by `v4_strategies` (100 draws), then classified by the same worker.
Only valid inputs hitting the requested fact survive. An error gets exactly
one retry with the unchanged RETRY message. Up to two inputs per request are
sampled with `random.Random(seed(..., stage=3, request, retry))`; the same seed
drives the draws. Selected inputs are deduplicated by `input_repr`.

`advdoc-plainhybrid` uses the unchanged CONTROL prompt (`fact=None`), accepting
any valid input and making no retries. Its request count is the completed
`advdoc-hybrid` row's `round2_strategy_requests` for the same task/sample,
**including targeted retries**. Zero targeted requests means zero plain
requests. As in run_v4, a nonzero strategy count triggers an expectation
request even when selection is empty.

The expectation request is the intentional prompt change: `injected_messages`
adapts the onlydoc test template, lists the selected calls, and asks for exactly
one `assert <entry>(<args>) == <expected>` per input, deriving expected values
from the specification. It uses only signature metadata and the stored
`advanced_doc/<task>/parsed.json` **docstring**. That field already contains
the fallback docstring if parsing failed. No PUT body, base tests, fact text,
Part 2 implementation, or strategy conversation reaches this request;
`gen_prompts.oracle_messages` is never called. Sampling matches run_v4's oracle
query: temperature 0.7, top_p 0.95, max_tokens 1024. Strategy requests match its
temperature 0, top_p 1, max_tokens 4096. Final assertions use the unchanged
`run_v4.merge(round1, injected)`, retaining both rounds without a global cap.

New seeds reserve a separate uint32 range for all new requests and draws:

```text
arm_index: advdoc-hybrid=0, advdoc-plainhybrid=1
seed = 3000000000 + (((task_id*2 + arm_index)*1000 + sample)*512
                     + stage*128 + request*2 + retry)
stage=1 strategy; stage=2 expectation; stage=3 draws/selection
```

Default output is `out/gen2_qwen7b_advhyb_v4/`. `manifest.json` freezes PREREG,
the normalized selected bundle and original bundle-file SHA256 (CLI), v4 and
new source hashes, prompt hashes, model, interpreter/tool versions, sampling,
seed scheme, the original advdoc JSONL byte hash, and every used parsed-doc
byte hash. `tasks.json` preserves the input bundle. `cache/` is the normal
LLM response cache; it may be populated with existing cache entries before the
first run. `artifacts/<task>/<sample>/<arm>/` holds prompts, responses, draws,
classification jobs/results, attempts, and `result.json`. Completed per-arm
results resume independently; the targeted result supplies the plain arm's
budget even after interruption. Re-running with the same inputs reconstructs
`gen.jsonl` atomically. Changed provenance requires a fresh output directory.

Rows retain run_v4's schema, including `assertions`, `text`, `calls`,
`selected_inputs`, `round2_strategy_requests`, `generator_attempts`,
`stage1_summaries`, `round1_assertions`, `round1_input_summary`,
`missed_fact_indices`, and the final input summary. Additional fields record
the saved advdoc run ID and docstring parse failure. `evaluate` validates a
complete task × sample × two-arm cohort and calls the unchanged `evaluate.py`
path, which dispatches to v4_evaluation. Its seven-arm report is bypassed;
`eval.jsonl` is written normally and this wrapper supplies `report.txt` and
`report.json` with per-split detection, any-of-K, false alarms, costs, and
paired task comparisons with full and matched assertion budgets.

`oracle` delegates collect/llm/score to unchanged `oracle_b01.py`, with its own
manifest in `out/oracle_advhyb/`. Before any stage it copies JSON response
entries from `out/oracle_v3m2hyb/cache/`, omitting locks/usage logs and preserving
already present entries. The original oracle seeds and original task specs
are retained for ref/post cache reuse. As with the baseline wrapper, oracle
score requires the existing EvalPlus/variant data and the full dev/pilot job;
`--no-llm` is available for collect/score. `--cache-source` overrides the source
cache, and `--run` / `--out` select dedicated runs. The endpoint and key come
only from environment variables; they are redacted from response artifacts.

**Edits for this implementation:** new `evalmitigate/run_advhyb.py`, new
`evalmitigate/test_advhyb.py`, and this README section only. No allowed-arm list
needs extension: both the evaluator and oracle collector accept the new
names. No `run_v4.py`, `v4_*.py`, PREREG.md, RESULTS.md, `vendor/`, or
`EvalAndMitigate/` files were edited. No commit or push was performed.

From the repository root, CPU verification:

```bash
python3 -B -m unittest trickcatcher_linefacts.evalmitigate.test_advhyb -v
```

The suite checks frozen byte hashes of run_v4 and every v4 module, saved
round-one selection and fallback docs, disjoint seeds, matched request counts
including retries, deterministic valid/hit selection, no plain retries,
zero-budget behavior, cached-output resume and interruptions, manifests,
doc-only expectation prompts, secret redaction, and oracle cache/delegation.
Its two-task K=1 smoke uses canned model responses with real pinned-v4 draw,
classification, evaluator sandboxes, and oracle collection. No model is
contacted. It uses `V4_PYTHON`, or discovers the existing codex_v4 scratch venv.

Exact full-job commands from `/home/phong/dev/ConceptTester` (supply
`QWEN_BASE_URL` in the environment beforehand; never save its value in files):

```bash
source scripts/research_env.sh
export QWEN_MODEL=qwen2.5-coder-7b-instruct
export V4_PYTHON=/tmp/claude-1000/-home-phong-dev-ConceptTester/2dddac78-7845-4887-9c28-b6313bcf7c52/scratchpad/codex_v4/venv/bin/python
python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb generate --k 3 --workers 16 --python "$V4_PYTHON"
python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb evaluate
python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb oracle collect
python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb oracle llm --workers 16
python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb oracle score --workers 12
```

These generate 798 rows in `out/gen2_qwen7b_advhyb_v4/` and oracle artifacts
in `out/oracle_advhyb/`. The last three commands can be replaced by
`python3 -B -m trickcatcher_linefacts.evalmitigate.run_advhyb oracle all --workers 16`.
For a subset smoke use `generate --task-ids 2 8 --k 1 --out
trickcatcher_linefacts/out/advhyb_smoke_v4`, then `evaluate --out` that same
directory; keep subset output separate from the full K=3 job.

Optional generation-cache preload before running (copy only responses):

```bash
mkdir -p trickcatcher_linefacts/out/gen2_qwen7b_advhyb_v4/cache
cp -n trickcatcher_linefacts/out/gen2_qwen7b_v3m2hyb_v4/cache/*.json trickcatcher_linefacts/out/gen2_qwen7b_advhyb_v4/cache/
```

Different new seeds/prompts still make new cache keys; copied entries are used
only on exact request matches. Oracle ref/post cache reuse is automatic.
