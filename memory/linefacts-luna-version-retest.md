---
name: linefacts-luna-version-retest
description: User-authorized exact gpt-5.6-luna low native v23/v24/v25 retest; preserve separate CLI/Qwen provenance and execution-host limits
metadata:
  type: project
---
2026-10-19 FINAL (supersedes running/quota checkpoints): all16/9/5 native diagnostics
complete. v23 concept/direct/hyp-only correct-assertion bug tasks5/7,7/7,5/7; concept
has1falsealarm and2hypothesisJSONfailures. v24 verifiedselected1/3 vs text/tool/witness3/3;
f06validgeneratedwitness rejected by frozen support gate. v25Afailed on3validator false
rejections (comprehension x scope), B/Cuntested. No concept task gain orpromotion.
Read RESULTS §11.72 and analysis/luna_versions_continue_20261019/REPORT.md, results.json,
finalize.py and full independent16/9/5reviews. Source/raw/rejectedcode untouched.
Target253CLIinvocations/251responses,2quotausagesunknown; costknown2,010,148/54,531,
canaryseparate13,565/199. Zero tasktool attempts, schemasstill exposed/hostdisabled.
No active jobs/retries; futurevalidator/gating/serializationfix needs a newfrozenvariant.

2026-10-18 user asks retest thread versions using gpt-5.6-luna/low subagents, tools
optionally disabled. Exact model is one model ID, not GPT-5.6 plus another Luna.
See RESULTS §11.70 and analysis/luna_versions_20261018/PREREG.md/AUDIT.md. Native
engines/source/fixtures preserved, new output root
out/model_probes/luna_versions_20261018/{v23,v24,v25}; launches16:36UTC.

**Why:** isolate model-capability/harness/interface bottlenecks without endpoint work.
**How to apply:** actual CLI schemas remain exposed although execution host disabled;
canary original exposure gate FAILED and denied tool attempt preserved. Scientific
router/tool attempts reject output/abort version. Different role/base/sampling budgets,
requested CLI model identity only unless server reports ID; no causal equal-budget or
Qwen attribution. Max280task CLI single-attempt invocations+1actual canary, no retries/
fallback/held-out/benchmark/automatic comparison expansion. Existing prior Luna/Qwen
results unpooled; native CPU tools are separate from model tool use.

v25 terminal9responses: A failed/B-C blocked.5metadata faithful; f13 correct unknown,
f06 calibrated2028rows. f02/f04/f14 rejected because validator globally rejects reused
comprehension x across separate scopes; independent static review says relations
correct in-domain. Never repair/execute/rescore rejected code or change frozen sources.
Read V25_REVIEW.md for practical limits. v23/v24 still running at checkpoint; inspect
luna_status.json and do not duplicate. Root owns terminal reporting/review.

2026-10-19 quota interruption correction: v23/v24 had actually stopped at73/65accepted
responses plus1usage-limit attempt each; not tool use. Epoch1 results.json preserves
partial/full denominators, no partial efficacy claim. User explicitly says continue.
Fresh continuation root out/model_probes/luna_versions_continue_20261019 imports old
responses/native caches byte-identically; new transport onlymissing stages, max87/25
single attempts. Prior quota ledgers retained, at most2cumulative attempts at those
slots under fresh authorization. Accepted old responses are reuse, not new samples.
No v25 rerun/validator repair/newcanary/Qwen/paid/benchmark. Independent continuation
audit passed and first freshv23responses confirm quota access; v24then launched.
Read analysis/luna_versions_continue_20261019/PREREG.md and resume_protocol.json.
Native cost reports omit fresh transport; external must aggregate old+new once,
retaining original2unknown usages. Originalsource/oldoutputs remain frozen.
