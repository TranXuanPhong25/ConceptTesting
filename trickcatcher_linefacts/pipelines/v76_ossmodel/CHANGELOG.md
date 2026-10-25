# CHANGELOG v76_ossmodel

Registered as v74_ossmodel, renumbered before any output (2026-10-25).
Status: **PREPARED ONLY**. No paid calls, launch, efficacy outputs or git commit.
This continuation supersedes earlier launch/retry/source-equivalence defaults below.

## Continuation changes

- Continued the existing v34 copy; no restart and no parent/vendor edits. Renamed
  config/package/module/test/script/PREREG/REVIEW/lock paths and memory note.
- Two CLI/config choices, gpt-oss-120b and deepseek-v4-flash. Separate output roots,
  caches, ledger and freeze per model; $3/model. DeepSeek exact provider/reasoning
  settings in pre-output amendment A. Output131072, no unsupported budget/seed.
- All requests are system+user; feedback remains in user JSON, no assistant
  reasoning_details passback. One physical attempt per logical request, empty
  answer fails the arm, no resend. Ledger stores reasoning tokens, finish_reason,
  empty-answer count, actual cost and unresolved reservations.
- Serial task-major dispatch; exact 403/login/usage errors propagate immediately.
  Guarded same-run resume archives 403 attempts and unrecorded tool ledgers.
  CPU --finalize-partial freezes only the whole paired prefix, descriptive only.
- v34 prompts/schemas/arms/scorer preserved. ft_run.py changes only generation
  scheduling and empty handling; AST checks protect score/score_record/guidance.
  ft_concepts.py and tracer.py unchanged. Parent historical hashes remain parent
  hashes; new prepared/asset manifests describe this version separately.

## Costs and context (public OpenRouter metadata 2026-10-25)

| Model | Planning estimate | Full-output projection | Hard cap |
|---|---:|---:|---:|
| GPT-OSS120B | $0.13117713 | $0.76984593 | $3 |
| DeepSeek V4 Flash | $2.0273659448 | $6.9732171320 | $3 |

297 requests. GPT-OSS planning uses actual historical Harmony input count plus
2048 output tokens/call, Near AI price .03/.15 USD/M; route ceiling .05/.25 still
binds dispatch reservations. The full-output GPT ceiling projection is
$1.28307655. DeepSeek planning uses the conservative byte-envelope input count
plus32768 output tokens/call, Relace .0422/.1694 USD/M. Full projections use max
outputs16384/131072. These are estimates, not a promise of full completion.
The $3 cap and workspace daily/monthly $2 caps are independent and binding.

GPT preflight:297 requests, max input9229 +output16384 <131072.
DeepSeek:297 requests, conservative max input53084 +output131072 <1048576.
Exact Harmony counts apply only to GPT-OSS; DeepSeek is a conservative UTF8
bound, not a claim about its provider tokenizer. Every actual future feedback
request passes a runtime context gate. See assets/cost_estimates_20261025.json
and context_preflight_<model>_20261025.json. Preparation spend $0.

## Verification and launch commands

Final test counts are recorded in REVIEW_V76.md. Reproduce CPU verification:

```bash
/tmp/concepttester-v74-venv/bin/python -B -m pytest -q -p no:cacheprovider trickcatcher_linefacts/pipelines/v76_ossmodel
```

Only after new explicit user go-ahead, from repo root:

```bash
bash trickcatcher_linefacts/pipelines/v76_ossmodel/run_openrouter.sh --launch --model gpt-oss-120b
bash trickcatcher_linefacts/pipelines/v76_ossmodel/run_openrouter.sh --launch --model deepseek-v4-flash
```

Each command is a separate run. Output roots:
`trickcatcher_linefacts/out/pipelines/v76_ossmodel/humaneval/faulttemplate/<model>/vibepass_half/`.
The wrapper sources scripts/openrouter_env.sh silently after argument validation,
then forces registered model and cap. V76_PYTHON defaults to the existing local
harness /tmp/concepttester-v74-venv/bin/python (temporary environment was not
renamed; this is not an old pipeline package path). Worker config unchanged.

CPU terminal partial reporting (no model calls):
`python -B -m trickcatcher_linefacts.pipelines.v76_ossmodel.run_v76 --finalize-partial --model MODEL`.
Do not finalize a workspace pause if an identical resume is intended. Finalized
partial runs cannot resume. Completed runs never rerun, enlarge or increase K.
No current-session commit/bundle/push was created; main session handles commits.
Other sessions' analysis folders and memory notes were not edited.

## Superseded lost-session preparation record

The following is historical; amendment A and commands above take precedence.


