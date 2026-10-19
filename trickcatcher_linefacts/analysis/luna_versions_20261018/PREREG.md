# User-authorized v23/v24/v25 Luna diagnostic rerun —2026-10-18, before outputs

User requests "test lại các ver với subagent gpt-5.6 luna low ... có thể tắt tool".
Local model catalog/other repository harness identifies exact gpt-5.6-luna, effort low.
Scope is the three versions discussed in this thread: original v23 diagnostic16,
v24 diagnostic9, v25 feasibility5, exact native run(client,root) functions in fresh
output roots. No frozen source/prompts/parser edits, old artifact repair, vendor/paper
reimplementation, Qwen endpoint/paidAPI/held-out/real20/benchmark calls. Parent CPU
execution/calibration remains native and separate from model tool use.

One fresh ephemeral Codex CLI subagent per stage. Empty cwd, ignore user config and
rules, project_doc_max_bytes=0, web disabled, tool defaults disabled plus explicit
shell/code-mode/browser/computer/apps/multi-agent flags. Preserve raw CLI JSON events,
stderr, final text, request digest, attempt reservation, actual usage and timeout.
Reject any model item except agent_message/reasoning, including unknown tool types;
any detected tool/protocol/provenance violation aborts that version rather than
silently scoring its output. Readiness canary1 requested model turn checks invocation
and tool exposure; configuration-only errors before thread/turn starts may be corrected
before tasks and are recorded separately, never retried after unknown model usage.
Max1 cumulative attempt per stage, timeout180s, no content/transport retry or fallback
model. Native logical budgets160+90+30=280 plus1 canary turn; at most3 version workers.

Stage-message CONTENT is unchanged but role flattening into a user prompt and Codex
base instructions differ from Qwen system/user roles. CLI does not expose numeric
Qwen max_tokens/seed/temperature/top_p parity; store original requested metadata but
DO NOT claim matched sampling/token budgets. One-shot harness diagnostic, not causal
model isolation or a matched cost comparison. No output-schema/guided JSON enforcement
or prompt edits to improve formatting. v25 explicit plain backend, no capability echo;
strict original A/B/C early stop. No recovery/reformatting of v23/v24 historical outputs.
Finish_reason=stop is an adapter inference only after a successful completed turn and
matching final-message evidence, never an assertion of raw server finish reason.

Native report zeros for missing usage/blocked stages are not actual zero cost/semantic
failures. External aggregates report known tokens, unknown attempts, cached token
fields only when present, and recorded tool calls. Raw origins identify Codex model,
never Qwen; old separate Luna probes stay unpooled. Full16/9/5 denominators and failed/
blocked/abstained/correct/ambiguous/masked cases retained. v23 assertions vs v24/v25
input-only yield separated; expected values there come only from common frozen fixture
scoring. Novel inputs/tasks subtract ENTIRE shared pool, compare witness-only ceiling.
Report within-version controls and overlap5 cases, not cross-version superiority.
Independent clean-context plan audit accepted these safeguards. Code audit + CPU/mock
checks + canary precede task launch; external code/sources/input fixtures frozen.
Terminal actual-output independent semantic review before conclusions. Commit/push own
changes main, preserve unrelated sessions. No automatic full comparison beyond these
native small diagnostics even if v25 passes; no model tool-on expansion without plan.

Tool configuration reference: official OpenAI documentation
https://learn.chatgpt.com/docs/config-file/config-reference (shell_tool, web_search,
MCP enabled flags); actual local CLI help/catalog evidence retained. tools.disable_defaults
will be checked by strict local CLI configuration; no undocumented support is assumed.


## Configuration-only correction before any model turn

Epoch1 strict CLI rejected tools.disable_defaults as an unknown field before thread/turn
start (stdout empty, returncode1). No server model request was made; original failed
preflight reservation and protocol.json preserved. Epoch2 uses supported explicit
feature flags, web_search=disabled, tools.view_image=false, ignore-user-config, empty
MCP/plugins and project_doc_max_bytes=0. Active registration is protocol_v2.json; fresh
canary_v2 namespace, still at most1 actual canary model turn across epochs. No scientific
stage output observed, no prompt/schema/sampling change or fallback model. Tool status
means configured feature disablement + zero event use + canary report, not independent
server schema inventory. Exact model identity is requested CLI ID/local catalog unless
CLI events explicitly report server ID; any explicit mismatch aborts.

Epoch2 likewise rejected tools.view_image before any thread/turn (stderr explicit,
stdout empty). Preserve protocol_v2/canary_v2. Epoch3 uses flags actually enumerated by
local `codex features list`: view_image/image_generation/plugins/remote_plugin/skills/
goals disabled in addition to prior tool flags; skip_host_skill_discovery enabled.
Remove unsupported tools.* overrides; retain web_search disabled, empty MCP, project
doc0 and ignore-user-config. Requested model catalog tool_mode=code_mode_only, while
code_mode_host disabled. Active protocol_v3/canary_v3, still at most1 actual canary
model turn. Config probes are not target model tests and not zero-cost guesses: explicit
pre-start CLI rejections establish0 model turns for those2 invocations.


## Epoch4 operational amendment AFTER canary, BEFORE scientific task outputs

Exactly1 actual canary turn completed13565input/199output tokens, cached12288, reasoning156.
Original exposure gate FAILED: callable schemas exec/wait/request_user_input remain
visible. Canary deliberately requested a tool; router denied code-mode execution. No
external tool result observed. Do not re-label this as passed no-tools exposure. Preserve
all canary_v3 artifacts, failed ledger, protocol_v3 and exact epoch3 source archive.

Independent code auditor accepts new readiness status
host_disabled_fail_closed_with_schemas_exposed, with no additional canary/model turn.
CLI emits2 exact pre-turn configuration-warning items (underdev skill-discovery and
code-mode host disabled); active adapter may permit ONLY these exact strings on
item.completed before turn.started. Any other error/failed/unknown event still fails.
Scientific stage stderr router/tool-attempt evidence also aborts that version before
response caching/scoring, even if JSONL lacks tool events. All task prompts/schemas/
model/effort/native engines unchanged; none of their outputs has been observed.
Active protocol_v4/readiness_v4; sources frozen before task launch. Origins say execution
host disabled with schemas exposed, not tool schemas removed. Internal CLI transport
and base instructions still differ from Qwen; no causal model-only comparison.
