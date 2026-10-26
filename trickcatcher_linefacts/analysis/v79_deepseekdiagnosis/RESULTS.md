# v79 DeepSeek diagnosis — terminal provider 429, 2026-10-26

**No model response and no semantic result.** The first of four planned calls
(case85/raw_known) returned HTTP429 before a completion. Exact provider error:

> deepseek/deepseek-v4-flash-0731 is temporarily rate-limited upstream.

OpenRouter identifies provider Relace and limit_source
`upstream_provider_shared_pool`. This is provider rate limiting, not a model
reasoning failure. Three slots remain unattempted; no automatic retry/fallback.
The Qwen endpoint probe was cancelled before any Qwen completion; v77 was not run.

## Frozen experiment

Isolated copy of v73; same four v72 messages/cases85,124/order/known-bug premise:
raw diagnosis versus full structured hypothesis contract. DeepSeek V4 Flash0731,
Relace/fp4 only, enabled reasoning, max output131072, no API seed, temperature.2,
top_p.95, JSON object, streaming. This two-case diagnostic cannot establish a
concept effect, even if successful; budgets/providers differ from v72/v73.
Independent pre-dispatch review and19 targeted tests passed. Review must-fixes
(context gate, exact API errors when usage missing) were applied before freeze.

## Cost and integrity

Cap $0.15. Four worstcase reservations total $0.09967314. Live captured pricing
Relace input .0422/output .1637 USD/M. One attempted dispatch, zero usage/cost
receipts, one unresolved reservation; see terminal_audit.json for its amount.
**Actual charge is unknown**, not claimed zero. No additional spend, private
oracle, constructor, native execution or paid judge. The raw provider error is
kept in ignored run artifacts; no credentials or Qwen endpoint are in this report.

Owner terminal audit verified source/config/protocol/runtime identity, output
freeze and the entire prior v72 freeze. SUMMARY.json and terminal_audit.json
record denominator, error and cost status. CURRENT_RUN.json records the terminal
run location/PID; controller has exited. No efficacy GO/NO-GO is issued.

Version lineage: v72(Qwen diagnosis) → v73(GPT-OSS replay) → v79(DeepSeek replay).
This changes model/transport budget only, not the diagnostic prompts.

## User-authorized retry — 2026-10-26

After user says continue, amendment B authorizes one fresh four-slot root with
the same prompts/wire/provider. The original unknown reservation $0.02449286 is
subtracted from $0.15 before preparation; retry cap $0.12550714, prospective
four-call reserve $0.09967314. Original run artifacts remain untouched. Three
changed source/protocol/review versions were saved from the original staged
snapshot; their source digest agrees with the original plan.

Retry first request again returns HTTP429, Relace upstream shared pool, without
completion/usage. Cumulative: **2 attempted requests, 0 model responses, 2 unknown
charges, $0.04898572 unresolved reservation**. Actual cost is unknown; reservation
is not a bill. Three remaining retry slots unattempted. No further automatic
calls, native probes, private labels or fallback. Separate RETRY_RUN/RETRY_SUMMARY
and retry_terminal_audit.json preserve lifecycle and verified freeze. Independent
read-only review verified both freezes, prompt identity, original source snapshot
and cumulative accounting after retry terminal.
