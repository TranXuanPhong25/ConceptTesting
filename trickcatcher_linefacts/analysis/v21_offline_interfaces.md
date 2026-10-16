# v21 Qwen chain P1 offline — 2026-10-16

Scheduled implementation completed for the offline adapter/interface phase only. Parent is a source copy of best v7, with parent manifest and no inherited outputs. New active entrypoint: `v21_qwenchain.chain_offline`. Historical generation/scoring entrypoints and online client are disabled in this copy.

Final checks: **48 passed**, zero failures/errors. Earlier logged invocation:44 passed; independent code review subsequently found counterexamples, corrected during initial offline development and covered by the later run. Both check invocations/source hashes preserved. Final local sources/config/prereg verified against the last run and recorded in `P1_FROZEN.json`.

## Implemented interface

- Source/spec views with original source hashes, UTF8 byte-coordinate AST IDs, decoded-spec character quote spans. S2 includes executable module/helper/global context with docs/comments masked; S1 receives only spec/signature/public examples. No inherited concept facts or model labels.
- Five stage schemas, open semantic vocabulary, strict/unique-fenced JSON extraction, raw provenance/offsets, immutable task/stage/version IDs and S5 supersedes lineage. Wrong references fail; no upstream reconstruction.
- Blocked, failed and legitimate terminal states; per-selected-hypothesis S5 decisions and evidence citations. Original O/B/source records stay immutable. No tool property/effect matcher.
- Bounded positional literal parsing, alias/cycle rejection before serialization, direct input slots and global dedup across S4/S5. Raw execution cache pinned under the chain so directory changes cannot rerun inputs or timeouts.
- Exact-request attempt ledger with cumulative3-attempt limit and resume/cache drift checks. Contract exposes120s timeout and2/8s backoff; no HTTP sender in this P1 entrypoint. Context fit requires an explicitly supplied token counter/window; test counters are labeled test-only, not Qwen token measurements.
- Isolated synthetic native checks use separate ordinary/traced processes with clean environment, namespace isolation and resource/event limits. Typed canonical signatures compare status/output/post-input/within-run alias observations. Opaque/missing values cannot certify native agreement; set/dict repr ordering cannot manufacture a mismatch.
- Mechanical output/exception predictions and fixed feedback projection. Relation prose stays unverified; line reach cannot prove operation activation. Every attempt/counterevidence summary and worker reason retained, with fixed first/last trace retention and explicit omissions.

## Independent code audit

Two prior plan reviewers audited implementation read-only. Findings and resolutions:

| Finding | Resolution/regression |
|---|---|
| Unicode U+2028/U+0085 broke physical line table and leaked comments | Physical LF/CRLF table, explicit standalone-CR rejection; original byte-coordinate tests |
| S5 allowed no decisions despite selected H | Exactly one decision per selected target; keep/revise/withdraw cite feedback |
| Same input/different observation projections collided | Cache raw execution independently; immutable result core, separate projections; both proposals retained |
| Opaque returns falsely counted as native agreement; repr ordering false mismatches | Supported typed canonical output signature required, unknown otherwise |
| Worker errors disappeared before S5 | Separate ordinary/traced statuses/reasons/validity provenance retained |
| Dependency edits could reuse stale results | Owned Python/config/interpreter fingerprint in context/request/execution cache |
| Different execution directory could bypass unique-input budget | Pin chain-native cache root; reject overrides; same/cross-stage reuse regression |
| Raw/escaped surrogate could crash coordinator | ASCII-safe raw ledger; reject invalid Unicode before artifact hash/save; one consumed content attempt |

Both reviewers accepted final P1 freeze within reviewed paths after fixes; no model/GPU/semantic-pilot approval was inferred. Review is finite and implementation-specific, not a correctness proof.

## Current boundary

**0 Qwen/experiment API calls, no GPU, no canonical/reference scoring, no D_IO or Qwen semantic-accuracy result.** Canned response fixtures validate interfaces only. This is not the16-case model pilot or a20-dev diagnostic. The generic observer reports exact operation-value claims as unknown; it supports bounded statement-line reach and whole-function output only, with explicit ambiguity/coverage limits.

Before a later online phase: separately authorize/register the actual16-fixture label packets and exact prompts/schemas, bind the real Qwen tokenizer/context limit and bounded transport, then evaluate S1–S5 quality under the reviewed gates. P1 completion alone does not demonstrate reliable concept extraction or alignment.

Reproduce offline checks: `python -B -m trickcatcher_linefacts.pipelines.v21_qwenchain.chain_offline`. Outputs are new logged invocations under `trickcatcher_linefacts/out/pipelines/v21_qwenchain/humaneval/offline_checks/`; `P1_FROZEN.json` records this final snapshot, not future edited versions.

Experiment request counts concern the pipeline; Codex implementation and independent review activity are not presented as Qwen experiment calls or semantic labels.
