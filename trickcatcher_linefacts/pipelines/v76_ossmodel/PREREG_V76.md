# v76: GPT-OSS-120B matched v34 fault-concept protocol

Registered 2026-10-25 before any v76 output or paid call. Status: prepared, NOT RUN.
Launch requires a new explicit user go-ahead, planned Monday 2026-10-26.

Prior art: v31/v34 Qwen3.5-35B: fault-template 18 / plain 15 / template-placebo
12 confirmed tasks of 33. Concept vs placebo detection 8–2, but false-positive
TESTS 27 > 23: v34 primary rule NOT met. v73 GPT-OSS two-case probe (85,124)
used four raw/full calls, not a concept efficacy experiment. v53 Sonnet tester
5/6 in every arm, v54 Sonnet variants 6/6 in both arms, v55h Haiku oracle
21/33 in all arms (0 FP); strong-model ceiling evidence, with Codex v28
16–17/20 and Sol6.1 6/6 both arms as additional context. No new efficacy claim.

## Fixed design
Exact v34 cohort vibepass_half, frozen 33 PUTs, K=1; six arms and all prompt
text, probe/final JSON schemas, seed formula, sampling (temperature .6,
top_p .95), 16384 completion-token cap, replay loop (two probes + final),
scorer and paired comparison calculations remain unchanged. Only LLM model
and its routing/reasoning/accounting requirements change: openai/gpt-oss-120b,
OpenRouter price-priority + require_parameters, reasoning effort low.
Use v73 price ceilings ($.05/M prompt, $.25/M completion, $0/request).
Reuse hash-checked frozen v31/v34 tool.json, full tool/ and only no-LLM results
(template-only, template-random, witness-only). Generate all plain,
fault-template, template-placebo results afresh: 33 × 3 × 3 = 297 logical
calls. Inherited incomplete-response retry limit remains three attempts;
SDK automatic retries disabled so every dispatch has a reservation/receipt.
No fresh tool search and no reference access before generation freeze.

## Primary rule (identical to v34)
Concept adds value iff fault-template vs template-placebo paired TASK detection
wins > losses AND fault-template false-positive TESTS <= template-placebo
false-positive TESTS. Use the unchanged v34 scorer for all counts and pairs.
Ceiling override: if plain confirms >=28/33 tasks, verdict =
`ceiling, uninformative about concepts`, regardless of the primary comparison.
Otherwise report `concept adds value` only when both conditions hold;
else `rule not met`. No significance or causal attribution claim from K=1.

## Secondary, descriptive only
Fault-template vs plain; template-placebo vs plain; schema failures,
abstentions (valid empty final tests vs invalid final), incomplete calls,
per-arm input/output/reasoning tokens and cost. Preserve original score.json;
supplementary decision/usage reporting does not alter scorer calculations.
Report actual transport receipts including incomplete retries separately
from v34's last-response-only arm accounting. Do not conflate empty response,
transport failure and explicit valid abstention.

## Spending, stopping and integrity
OPENROUTER_MAX_USD=3, clamped at $3 even if environment requests more.
Reserve worst-case price-capped request cost before every dispatch, under
thread/process locks; persistent ledger records all attempts and receipts.
Unknown-cost attempts retain reservations and block further calls pending
manual reconciliation; never silently price missing usage at zero.
Workspace daily/monthly $2 caps may return 403: pause, archive denial logs
and unrecorded-arm ledgers OUTSIDE the pipeline, resume identical source
and cached completions after the workspace permits it. No code edits mid-run.
No enlargement, K increase, automatic rerun or new seed regardless of outcome.
Same-run interrupted transport resume is allowed; paid re-sampling after a
completed run is not. No model calls during preparation; metadata GETs and
CPU/mocked engineering checks only. Dynamic replay feedback is unknown
before launch: preflight exact-tokenizes historical matched requests and
all first requests; runtime exact-tokenizes EVERY actual dispatch and stops
before an over-context request without truncating or changing the prompt.

## Pre-output amendment A — renumber and second model (2026-10-25)

Registered as v74_ossmodel, renumbered before any output to v76_ossmodel. The
unrelated v74_oss_select/v75_deepseek_select and their memories are unchanged.
Second model deepseek/deepseek-v4-flash-0731 is run and reported separately:
EXACT provider `{only:['relace/fp4'],allow_fallbacks:false}`, EXACT reasoning
`{enabled:true}`. OpenRouter metadata confirms Relace context1048576, maximum
completion943718, input$0.0422/M output$0.1694/M; pinned snapshot in assets.
No pooling, substitution or cross-model budget borrowing. Same primary decision
rule, arms, prompts, schemas, cohort33, K=1 and v34 scorer for each model.
Separate model output roots, caches, global per-call ledgers and protocol freezes;
$3 hard cap PER model. One dispatch per slot for BOTH models; no resend of empty
or truncated answers. Any empty response fails the corresponding arm (no final
emitted tests/detections); failures remain in denominators. Ledger records
reasoning_tokens, finish_reason, empty_answer_count, billed usage and cost.

GPT-OSS retains registered low reasoning/routing/output16384. DeepSeek output
cap131072 includes reasoning; do not rely on reasoning.max_tokens (ignored in
v75). This is a prospective mitigation, not proof that answers cannot truncate.
No paid smoke call is authorized. Relace advertises no seed, so omit API seed;
local seeds unchanged. DeepSeek preflight uses conservative 2*UTF8 bytes+4096
framing bound with runtime guard against1048576; never call Harmony counts exact
DeepSeek tokens. All feedback is already serialized inside the user message:
exactly system+user, no assistant turns, no reasoning_details passback needed.

Dispatch is serial task-major (all arms of one task before next). Workspace
403 daily/monthly$2, login or usage-limit error stops immediately with exact
error; zero retries. Identical-run resume only after reset/authorized change,
without altering files/ledger or resampling completed slots. A terminal cap stop
reports only complete paired tasks, incomplete tasks excluded by completion
alone; partial data is descriptive, not an efficacy verdict. No enlargement.
This amendment supersedes earlier three-attempt/concurrent defaults.
