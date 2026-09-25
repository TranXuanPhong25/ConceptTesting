# TestEval Python LLM Runner

## Paper-protocol targeted-line comparison

Use `testeval_py.paper_runner` for a direct ablation of the official TestEval
targeted-line prompt. It loads `prompt/system.txt`, `prompt/template_line.txt`,
`data/leetcode-py.jsonl`, `data_utils.add_lineno`, and `format.py` from a pinned
checkout of the [official TestEval repository](https://github.com/LLM4SoftwareTesting/TestEval).
The baseline prompt is assembled exactly as in its Gemini line generator. The
concept arm appends only target-specific AST-derived reachability facts; targets
without facts use the unchanged official prompt. Both arms use temperature 0,
one candidate, and 256 output tokens by default. Successful raw responses are
cached per model and full prompt, so rerunning the same command resumes.

With native Vertex AI credentials and a checkout at `/tmp/TestEval-upstream`:

```bash
export LLM_PROVIDER=vertex
export VERTEX_PROJECT=your-google-cloud-project-id
export VERTEX_LOCATION=global
export LLM_MODEL=gemini-3-flash-preview

python -m testeval_py.paper_runner \
  --upstream /tmp/TestEval-upstream --arm baseline --limit 100 \
  --out testeval_py/paper_protocol_baseline.jsonl
python -m testeval_py.paper_runner \
  --upstream /tmp/TestEval-upstream --arm concept --limit 100 \
  --out testeval_py/paper_protocol_concept.jsonl
```

The `.raw.jsonl` sidecar contains unformatted model responses. The main output
has the same shape as the official formatted prediction file. To run the
upstream line evaluator, copy each main output to its `predictions/` folder and
run `eval_linecov.py --path <filename>` from inside that checkout. Run the two
evaluations separately and record syntax correctness, executable correctness,
and accuracy in covering the selected line. The official evaluator writes
temporary files in its working directory and removes directories matching
`tmp*`, so use a dedicated checkout.

This follows the paper's task and prompts, but the configured model is Gemini 3
Flash on native Vertex AI; the paper's published model scores are not directly
reproduced by this model substitution or by the first-100-task subset. Earlier
`paper100_vertex_*` runs in this repo used a custom prompt and must not be mixed
with these paper-protocol outputs.

### Two-step reasoning baseline and concept arm

`--protocol two-step` follows the paper's stronger line-coverage setting. It
loads `data/leetcode-py-all.jsonl`, `prompt/system_exec.txt`,
`prompt/line_oneshot_gencond.txt`, and `prompt/line_oneshot_gentest.txt` from the
upstream checkout. Step 1 asks for conditions; step 2 receives those generated
conditions and asks for a test. Both calls use temperature 0 and 1,024 output
tokens by default. The concept arm appends the same target-specific facts to
both official prompts so they remain available during test construction. By
default, this arm uses branch polarity, prior early-exit guards, state updates,
map population, and recursive argument mapping. It omits generic loop-entry
and index facts; `--concept-facts` can override that selection.
Successful conditions and tests are cached independently. The output includes
`conditions` alongside `tests`, as in the upstream CoT generator.

```bash
python -m testeval_py.paper_runner \
  --upstream /tmp/TestEval-upstream --protocol two-step \
  --arm baseline --limit 100 \
  --out testeval_py/paper_cot100_baseline.jsonl
python -m testeval_py.paper_runner \
  --upstream /tmp/TestEval-upstream --protocol two-step \
  --arm concept --limit 100 \
  --out testeval_py/paper_cot100_concept.jsonl
```

Evaluate both formatted prediction files with the same upstream
`eval_linecov.py`. The earlier basic-prompt results are a separate experiment;
CoT doubles the model-call budget for each target.

### Execution-verified witness arm

`--arm concept-witness --protocol two-step` adds a bounded local search before
the two official CoT prompts. For supported parameter types it tries small
deterministic inputs in an isolated process, re-executes the solution for each
candidate, and keeps an input only when a line trace observes the target and
the call returns normally. The prompt receives the concrete call, recent
executed lines, and small scalar locals at the target. The search is cached
separately in `<out>.witnesses.jsonl`; LLM responses retain their existing
per-prompt cache. Search defaults to two seconds and 800 candidates per task.
After formatting, the runner traces the LLM test. If it misses a target for
which a verified witness exists, it replaces that test with a minimal function
that calls the verified input. `witness_fallback_targets` records each such
replacement, and the `.raw.jsonl` file retains the original model response.
Use `--no-witness-fallback` for the prompt-only witness ablation.

```bash
python -m testeval_py.paper_runner \
  --upstream /tmp/TestEval-upstream --protocol two-step \
  --arm concept-witness --limit 100 \
  --out testeval_py/paper_cot100_concept_witness.jsonl
```

This is a distinct method with extra local execution cost. A witness verifies
source execution and target reachability, not every natural-language LeetCode
input constraint; the prompt states that limitation explicitly. Report witness
availability, search cost, and fallback count alongside coverage and assertion
quality. The fallback test has no generated assertion. Do not mix this arm's
cache with the static concept arm.

Generate targeted Python tests with an OpenAI-compatible LLM. The input can be
raw TestEval data; the runner computes `concept_annotation_py` automatically.

## Trial

```bash
source scripts/router_env.sh
.venv/bin/python -m testeval_py.llm_runner \
  --in concept_annotator_py/testeval_py_concepts.jsonl \
  --out /tmp/testeval_py_line_trial.jsonl \
  --mode line --limit 1 --max-targets 1
```

The output follows TestEval's targeted-line format: one JSON object per task,
with `task_num`, `code`, and `tests` keyed by target line. Use
`--mode branch` for targeted branch generation; branch output uses the
`start`/`end`/`test` format expected by TestEval.

Use `--dry-run` to inspect prompts without making an LLM call. `--limit 0`
and `--max-targets 0` mean all tasks and all targets, respectively.

Successful responses are checkpointed after every target in
`<out>.cache.jsonl`. Re-running the same command resumes from that cache and
does not call the provider again for completed targets. Each provider request
times out after 60 seconds by default; change this with `--request-timeout`.
After retries are exhausted, the runner records the failure in
`<out>.errors.jsonl`, leaves that target empty, and continues. Use
`--fail-fast` to stop instead.

Cache keys include the prompt version. The current `reachability-v3` prompt
uses `concept_annotator_py.v4` target-specific facts, so responses generated
with earlier concept prompts are not reused.

The runner supports the existing providers through `magma.llm_client`:
`LLM_PROVIDER=router`, `groq`, or `vertex`. Never commit the local router env
file or generated predictions containing sensitive prompts.

For native Vertex AI, configure ADC once and source the local environment:

```bash
gcloud auth application-default login
source scripts/vertex_env.sh
```

Gemini 3 Flash uses `gemini-3-flash-preview` at the `global` location. The
runner caps output at 4096 tokens by default (`--max-output-tokens`) and
supports `LLM_THINKING_BUDGET=0` for this short test-generation workload.

For execution-feedback generation, use the separate loop runner:

```bash
source scripts/vertex_env.sh
.venv/bin/python -m testeval_py.feedback_loop \
  --in concept_annotator_py/testeval_py_concepts.jsonl \
  --out /tmp/testeval_feedback_symbolic.jsonl \
  --prompt-mode symbolic --rounds 2
```

It generates one test, executes it against the target, feeds back
`not_covered`, `assertion_failed`, or runtime status, and retries the same
target up to `--rounds`. Its cache is separate from one-shot generation.
