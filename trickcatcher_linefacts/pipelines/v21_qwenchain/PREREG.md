# v21 P1 offline preregistration — 2026-10-16

Written before offline adapter check outputs. User scheduled implementation of P1 only. Reviewed plan: root PLAN_QWEN_REASONING_CHAIN.md v3; independent review: analysis/qwen_chain_plan_review.md.

Scope: source/quote coordinate mapping; independently isolated S1/S2 contexts; strict/unique-fenced JSON; stage schemas/references/immutable version lineage; literal/arity/type/identity validation; mechanical prediction/observation checks; cumulative attempts/cache/context bounds; blocked/terminal stage accounting; bounded local execution adapter checks. New source copy from v7, no prior outputs imported. No static semantic matching or normative model enumeration.

No model/client/endpoint requests, Qwen simulation, GPU, canonical/ref scoring or16-case semantic pilot. Hand-authored response fixtures test contracts only and carry offline_fixture provenance. No model accuracy or semantic performance is inferred.

Production ceilings encoded in config as future interface constraints:5 stages, slot output caps768/1024/1024/768/1024, up to3 cumulative identical attempts,120s timeout and2/8s backoff; no content retry. Source size65536/AST4096/depth64. Proposals≤6 per S4/S5,≤12 unique inputs, at most24 ordinary+traced PUT executions per task plus separate validity checks. Actual Qwen context/tokenizer/server metadata unknown; future online request requires an explicit token counter/window, no silent truncation or token claims from character counts.

Source IDs use original UTF8 byte columns/hash, quote spans use character offsets in decoded spec. S2 receives masked executable module view including helpers/imports/globals, no docs/comments/spec/concept facts or fixture labels. Missing context is explicit unknown. S1 receives only spec/signature/public base. S3/S4/S5 original context + valid predecessor artifacts, no upstream reconstruction. S5 versions/supersedes preserve original H. Typed failures and legitimate terminal records remain visible; no replaced missing artifacts.

Tool supports type-aware bounded exact-output/status comparison; relation_text stays unverified. Observation requests are explicit source IDs/kinds; line/statement scope cannot certify expression/operation activation. Unsupported requested observations remain unknown. Feedback retains every attempted input summary/counterevidence; trace retention/omission counts deterministic, not result-ranked.

Offline checks include adversarial Unicode/multiline/comment/source scope, malformed/truncated/ambiguous JSON, cross-task/stage/version refs, extra semantic fields, correct terminal/blocked flows, validation signature, alias/cycle topology, bool/int and list/tuple output types, unsupported relation/observation and timeout, attempt limits/resume/cache drift, context/feedback overflow, failed prerequisites and no live network dependency.

P1 is development verification, not a frozen Qwen treatment. Each check invocation records run ID and source hashes before results and keeps earlier failures. Routine implementation fixes may be verified in new logged check invocations within this initial folder before final P1 freeze; any contract change is appended here before rerunning. Future P2/model outputs require a separate pre-output registration/freeze and explicit authorization. Preserve all prior pipelines and other sessions' files. Commit only own source/reports; memory local.

## P1 pre-final-freeze audit correction — 2026-10-16

Initial logged44 checks passed. Independent read-only code audit found additional cache-root drift and malformed-Unicode counterexamples not covered there. Routine offline-development correction (no model treatment/output): pin execution cache under chain directory, reject directory overrides, retain malformed raw response with ASCII-safe JSON while rejecting invalid Unicode before artifact hashes/save. Add same/cross-stage cache reuse and escaped/raw surrogate regression checks. Prior run/source hashes preserved. Repeat only updated offline suite in a new logged invocation. No model/GPU/semantic experiment.
