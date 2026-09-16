# TestEval Python LLM Runner

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

Cache keys include the prompt version. The current `symbolic-v1` prompt uses
`concept_annotator_py.v2` target-specific constraints, so responses generated
with the earlier AST-tag prompt are never reused in symbolic experiments.

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
