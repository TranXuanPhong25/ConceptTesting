# v25: small prospective interface/semantic feasibility gate

2026-10-17. User authorizes continuing the five proposed improvements and automatic
use of the previous endpoint when GPU returns in about10 minutes. Best parent v7;
new v25_interface_gate copy, explicit audited v24 runtime ports, no historical edits.
Plan/code clean-context audits and CPU before real model calls. No paid fallback.

## Fixed scope and stages

Five seen fixtures f02/f04/f06/f14/f13:3 known bugs across multiplicity, inclusive count,
inclusion;1 correct unused-operation case;1 ambiguous suitability. Preserve same v24
authored finite calibration banks and24+base pools with dependencies/seed frozen.
One prospectively registered adaptation, no per-response prompt change or repair.

Phase A: spec-only concept metadata JSON (decision, spec_quote, input_domain,
required_relation, uncertainty), then a SEPARATE code-only obligation function when
decision=proposed. Code prompt sees original spec/metadata, never PUT. Exact source
quote and uncertainty are checked; no code/prose field swapping is possible. Predicate
must validate returned observation against input, including strict types, not just
nonnegative output or an input eligibility predicate. Restricted v24 pure-code worker
and finite authored gold qualification unchanged, limitations disclosed. Five metadata
slots plus up to5 code slots. Gate A requires all4 defined predicates calibrated and
f13 model unknown/uncertainty with no code, otherwise STOP with full5 denominator.

Phase B only if A passes: behavior with code-only INPUT context and structured metadata
output, small hypothesis metadata JSON (verdict,
target_line, trigger_condition, explanation) given spec/code/behavior/qualified concept
and common six native/contract-check rows. Separate code-only trigger for each proposed
mismatch. No semantic rewrite/retry. Check trigger, observed primary source-line reach,
output obligation and counterexamples on SAME full pool. Gate B requires all3 bugs
have observed-supported hypotheses, correct f14 consistent, ambiguous f13 unknown,
all metadata valid; otherwise STOP. At most5+5+5 additional slots.
The common-six selector is calibrated-contract violation first, then original pool
index, fixed BEFORE any hypothesis. No hypothesis/oracle-based input reranking.

Phase C only if B passes: ONE named-JSON input call/case, up to3 inputs. Require valid
binding/domain and at least1 contract/trigger/reach-supported discriminator per buggy
case, a valid contrast for f14, proper abstention for f13. No expected outputs requested.
For f14 require >=1 purpose=contrast candidate with valid binding/domain, native_checked
normal observation and qualified obligation=True. f13 requires inputs=[] plus reason;
no normative oracle or arbitrary expected value is invented.
Score with same independent fixture oracle after freeze; report copy/novel input yield
outside entire shared pool and witness-only ceiling. Passing means narrow feasibility,
not concept gain/generalization. No automatic full comparison/benchmark on any gate.

At most30 task completion slots, plus at most1 schema-capability echo. Stop before
dependent phases on failure, preserving failed/blocked/not-applicable slots explicitly.
Temperature0, pinned Qwen/context16384, contract/trigger code caps1536, metadata/hypothesis
caps768, input cap768, behavior768. Cumulative3 transport attempts/slot, no content retry.
Task logical output-token ceiling30720 (before cumulative3 transport attempts); one
echo slot max64 output tokens, seed20261017, cumulative3 transport attempts, no content
retry. Max31 total logical slots/93 physical completion attempts. Capability echo must
be raw bare JSON exactly {"schema_gate":true}, additionalProperties=false; fence decoding
is NOT applied to the backend-enforcement check. Capability usage reported separately.

## Serialization and backend capability

Before any task completion, inspect root OpenAPI metadata for advertised guided_json.
If advertised, at most1 preregistered adversarial echo (prompt asks NOT_JSON; schema
forces {schema_gate:true}) tests enforcement with usage/tokenizer binding. Use guided
JSON for JSON stages only if echo validates; otherwise fixed plain mode. No task-based
mode selection or extra feature probes. Persist selected mode before task requests.

Registered envelope parser accepts either bare JSON/code OR exactly ONE complete
matching ```json / ```python fence, with whitespace outside only. No prose extraction,
multiple blocks, missing fields, swapped fields, syntax fixes or semantic changes.
Raw response, decoded payload, envelope kind, schema/syntax validity and qualification
are distinct immutable artifacts. Decoder rules fixed before outputs; never applied
to historical v24 for recovery. Backend raw text preserved even when rejected.

## Raw control and implementation boundaries

Shared context builder emits verified_hyp/text_hyp/toolinput packets with byte-identical
common concrete inputs/native traces. text_hyp always receives original raw metadata,
predicate and hypothesis/trigger responses with origin/status, independent of parsing,
compilation or calibration; only genuinely missing response is marked missing.
verified uses qualified/observed-supported fields only. Export these packets even on
gate failure and test poisoned/rejected artifacts, without model comparison calls.
This increment runs only the feasibility phases above, not an efficacy arm comparison.

Pure workers, one durable attempt, staging/canonical result isolation, strict typed
oracle/ambiguity handling, source/request/response/pool/bank/cache/interpreter hashes
and protocol quarantine are reused from audited v24. Source freeze before capability
echo; backend selection immutable before task calls. Metadata/wait/liveness counted
separately. Single detached waiter/controller: earliest12:20UTC, then at most60min of
metadata liveness checks every60s; endpoint env-only. Completion callback to same thread.
