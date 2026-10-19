# CHANGELOG v31_faulttemplate

Parent: `pipelines/v29_vibepass` (PARENT.json). Plan: `trickcatcher_linefacts/PLAN_FAULT_TEMPLATES.md`.

## 2026-10-19 — explicit fault-type concepts + input templates, plain comparison, OpenRouter Qwen3.5-35B-A3B

- New: `ft_concepts.py` (fault-type table, templates, ranking/selection), `ft_worker.py` (batch PUT + mutant execution,
  isolated), `ft_run.py` (tool stage, plain / fault-template / template-only / witness-only arms, freeze, scoring with
  the v29 rules), `openrouter_client.py` (key from env, per-slot cache, USD hard cap), `test_faulttemplate.py` (6 tests).
- `config.json`: VERSION, `openrouter` and `faulttemplate` blocks. Env template `scripts/openrouter_env.example.sh`;
  the filled `scripts/openrouter_env.sh` is gitignored.
- Inherited files unchanged (flow_run plain path reused through imports).
- CPU: 36/36 tests; mock end-to-end OK; mutmut needs a lock (it changes the process cwd; parallel calls failed 18/20
  before the lock). pilot20 dev: template inputs expose PUT ≠ canonical in 8/20 tasks; VibePass tool stage 65/66
  tasks with site concepts (no reference).
- Amendment 1: MVP cohort `vibepass_half` (33 PUTs, `half_split.py`, `vibepass_half.json`), default in `run_openrouter.sh`.
- Amendment 2 (leak fix): VibePass prompt-visible base tests now from `humaneval_mbpp.jsonl` (public asserts); the
  `_plus` `test` embeds canonical solution + contract + hidden inputs. First launch archived (`vibepass_half_attempt1_leak`).
- Amendment 3 (independent Opus review): openai-SDK client (retry, fail-fast 400, no caching of empty/truncated
  replies, provider pinned, 16k tokens), survivor cap 200, PUT-ok kills, public-example domain filter, template-random
  baseline, witness-only race fix, stronger leak guard + CPU leak test, protocol env/evaluator digests. 39 tests pass.
- Status: running MVP (vibepass_half).
