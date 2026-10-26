# v79 DeepSeek writer diagnostic — 2026-10-26, before paid calls

User authorizes a short DeepSeek run after cancelling the Qwen endpoint probe.
Repeat exactly the four frozen v72 prompts on cases 85/124, raw_known/full_known,
in their original counterbalanced order. Known-bug premise, source/spec/examples
and prompt contents are unchanged. No v77, new task, full pipeline or paid judge.
Prior art: v72 Qwen raw semantic errors/full abstentions; v73 GPT-OSS raw85 correct,
raw124 wrong/full abstentions. v75 tested DeepSeek menu selection, not diagnosis.

Copy v73 into isolated v79; preserve all parents and their outputs. Exact model
deepseek/deepseek-v4-flash-0731, provider only relace/fp4, fallback disabled,
require_parameters true. Reasoning {enabled:true}, max_tokens 131072 includes
reasoning; no unsupported seed/effort/max_tokens reasoning budget. Temperature .2,
top_p .95, JSON object, streaming curl-N, one physical dispatch per slot. No Hello
completion or retry for empty/length/transport errors. This is a model-package
diagnostic, not matched-compute attribution or a concept-efficacy experiment.

Overall cap min(environment cap, $0.15). Reserve each call using 2*serialized
message UTF8 bytes+4096 prompt tokens and output131072 at ceiling prices .05/.18
USD/M input/output; check sum of all four reservations before dispatch. Freeze
live metadata and verify exact provider/model, supported parameters and context.
Live metadata captured 2026-10-26: Relace .0422/.1637 USD/M, context1048576.
Require actual usage.cost before next call. Missing billing/stream error/403/login
stops immediately, unknown reservation preserved. No key inspection or logging;
source scripts/research_env.sh and scripts/openrouter_env.sh silently.

Freeze source/config/protocol/review/runtime, exact prompts and endpoint metadata
before first call; persist attempts, SSE and cost receipts, then all four outputs
before semantic review. Do not infer correctness from nonempty answers. Review
public spec/source, with at most two public-input native probes per response,
eight total, only after freeze. No private oracle/contract/canonical reference,
replacement reference program, automatic follow-on run or task enlargement.

Assessment separates schema validity, hypothesis plausibility, demonstrated input
and correct expected value; raw expected values are optional in the prompt.
Full hypotheses may abstain. Report known cost, reasoning/output tokens,
truncation, attempts/unknowns and model/provider; no efficacy GO from two cases.

Pre-dispatch amendment A (2026-10-26): independent read-only Codex review requires
explicit context checking using the same prompt envelope as budget reservations,
persisted per job, and preserving exact API/stream errors alongside missing-cost
status. Both fixes applied before preparation/paid calls. No treatment change.
