# Independent terminal integrity and cost audit

**Verdict: PASS for artifact integrity, request accounting and paired-context parity.** This does not certify normative binding correctness, tool usefulness or the scientific GO gate; those require the separate semantic review. No integrity must-fix found.

Scope: owned `out/pipelines/v43_concept_identify/humaneval/binding8`, frozen pipeline, external approvals/readiness helpers, and four frozen v40 parent roots. Audit used only stdlib file/JSON/hash/AST/METADATA inspection. No pipeline imports, test/scorer/native worker, relation evaluation, `source.tools`/`compare`, model/network/tokenizer/quota request, retry or mutation of experiment artifacts. Only this report and `INTEGRITY_COST_AUDIT.json` were written. The JSON records 102 passing checks and per-slot usage.

## Frozen identities and provenance

- All 60 current source files exactly match `freeze.sources`, preparation approval and final approval; source membership is exact after the documented cache exclusions. Preparation approved 19 CPU checks; this audit did not rerun them. Five explicitly reviewed source hashes also match.
- All eight prepared pool file hashes match freeze. E1…E8 row counts are 13/7/8/7/9/15/9/10 = **78**. Reconstructed saved-record compaction matches each pool exactly: public spec/source/parameters, native_checked=true/domain_filter=accepted filtering, input deduplication, order and O IDs. There are no conflicting repeated inputs. No candidate relation was evaluated in this provenance check.
- Pools reuse all accepted native observations from v40 retry3 shared/injection and all-arm feedback, including prior Qwen-produced queries/finals. This is a biased reused selection diagnostic, not independent new sampling or discovery. No new PUT/native workers were run by v43; the saved rows retain historical native-execution provenance.
- Stable environment contains exactly the 16 frozen installed distributions, checked from every `.dist-info/METADATA`; versions match freeze and ENVIRONMENT.json. Python executable bytes match frozen SHA256, Python version records agree, all three direct pins agree, and quota script bytes match frozen SHA256. No experiment interpreter or installed package was executed.

| Parent root | Inventoried files | Manifest SHA256 |
| --- | ---: | --- |
| d1 | 162 | `7046515ee6c05cc2ad8f2c355e44bc5a554f92b4a27466898d5e74016f32bcad` |
| d1_retry_20261021 | 151 | `3c3474d5ae6f6ec8dbfabbb5c16edf8f79d3f646c59178b9ff6a569043bd3398` |
| d1_retry2_20261021 | 4 | `4915b2fb8497fd8908ff0107af5814980b4b8f574d96981e2a038299b17afced` |
| d1_retry3_20261021 | 1404 | `7b4091908b7001050aa6fd94f7057ac2b14888cb50d741ae6ac6bf1d4ab59046` |

Each parent manifest hash matches the frozen identity **and** its entire current file set and bytes match the manifest. The retry3 legacy terminal identity also matches. This checks content, not merely manifest self-consistency.

`generation_frozen.json` matches the exact **189** files under prepared/requests/artifacts/blocked/tool_results/selection_checks/transport. `terminal_inventory.json` matches the exact **290** files under binding8, excluding itself. There are no added/unlisted files in either scope. External controller logs and this report are intentionally outside that root.

| Approved identity | SHA256 / parsed digest |
| --- | --- |
| freeze_hash | `2d75578df59e8abc52a6c631c52b72f0c3669bdf2034bcdaf2c58f73d34e3b5d` |
| freeze_file_sha256 | `53940eb79fb68e3bc750c045f392c0abf6e78f6abc4f243a20fef15579a95739` |
| launcher_sha256 | `543ce98e39eadd4095e3829f4547dda2e9d9b21ae428e1b6446fd1db55517038` |
| readiness_script_sha256 | `6fb2b2033a7f8e5caca9a3d24621369ee4da46456ad85228a16e7b4723ba190e` |
| readiness_result_sha256 | `d8aa016dd7cd3143ee970659cc617316d59f7b23344a856c2f08b6fe8ae74ca2` |
| failed_readiness1_status_sha256 | `d9d95ec0478aef3871d39df45a3cdbbc801bc3470ebf2116fe711302353b188b` |
| engineering_amendment_sha256 | `c3cda00dccd5cfeff0eb43b1848141a156deb672f88d11f160588f342700328f` |
| evaluator_rubric_sha256 | `a0b6b9858822f705115e1fe61e5546084da18b3e5949f3e80d7b4e00753198ae` |

The original readiness.py hash also matches readiness1 status; launch registration pins the same launcher and freeze file. Final approval passed, pins all 60 sources and parsed freeze digest, cap24, readiness2 and no additional readiness adaptation.

## Readiness chronology and request accounting

**Readiness1 remains FAILED/STOPPED.** Its received GET /models + three POST /tokenize requests are preserved: E1 initial1017/raw2755/tool8359; 8359 exceeds input6144. Zero task completions or PUT calls occurred in that namespace. It is a failed synthetic-envelope engineering gate, not an actual candidate/tool outcome.

`READINESS_AMENDMENT.md` explicitly superseded only the original readiness stop/no automatic repair orchestration rule before inference. It preserved failed readiness1 and unchanged sources/pools/model/schema/prompt/scientific gate/call cap. It authorized one separately consumed readiness2 namespace, <=25 metadata requests, with no third adaptation. The helper and amendment hashes match final approval. Current amendment mtime is 2026-10-21 17:29:44 UTC; readiness2 started17:33:20, ended17:33:39; approval17:36:38 precedes actual start17:37:27. Readiness1 stopped17:23:37. These saved records support the stated pre-inference chronology; filesystem mtimes and recorded/server clocks are not independently attested timestamps.

**Readiness2 READY** preserved one models GET +24 tokenizer POSTs, all received; maximum synthetic input4748 at E6 tool. Both readiness sizes exactly match saved tokenizer result counts. Neither readiness namespace contains a completion attempt. Both models receipts are HTTP200 and advertise exact qwen2.5-coder-32b-instruct/context8192. Only readiness/ and readiness2/ exist; no third adaptation namespace. Synthetic envelopes remain estimates, not universal token bounds.

| Scope | GET /models | POST /tokenize | POST /chat/completions | Total HTTP |
| --- | ---: | ---: | ---: | ---: |
| Failed readiness1 | 1 | 3 | 0 | 4 |
| Ready readiness2 | 1 | 24 | 0 | 25 |
| Actual diagnostic client | 1 | 18 | 18 | 37 |
| **Scoped v43 total** | **3** | **45** | **18** | **66** |

Actual client metadata.jsonl contains19 received records: one GET plus18 tokenizer calls. Do not omit this GET/tokenize traffic or merge readiness into completion counts. Across all three namespaces, all45 tokenizer reservations still say `state=reserved` by design, but each has a received `result.json`; there are zero orphan/unknown tokenizer reservations. They must not be counted as45 unknown attempts. Actual tokenizer result counts match the18 completion input counts; all inputs <=6144 (actual max3111), outputs <=1536, with context8192.

## Full 24-slot terminal denominator

| Episode | Initial | Final raw | Final tool |
| --- | --- | --- | --- |
| E1 | invalid | blocked | blocked |
| E2 | valid | invalid | valid |
| E3 | invalid | blocked | blocked |
| E4 | valid | valid | valid |
| E5 | valid | valid | valid |
| E6 | invalid | blocked | blocked |
| E7 | valid | valid | valid |
| E8 | valid | valid | valid |

There are18 unique single-attempt completion slots: eight initials and ten finals. All18 HTTP responses, normalized responses, wire/request messages, usage and saved artifact raw responses agree. All18 finish_reason=stop and exact model/origin are recorded. Four schema-invalid received outputs still consume calls/usage: E1 initial binding[2].concept enum, E3/E6 initial binding[1].concept enum, E2 raw final evidence maxItems. Three invalid initials block six dependent final slots without completion/tokenizer requests. Thus14 valid +4 invalid +6 blocked =24; tool final validity is5/8, not8/8. No transport/protocol/unknown completion attempt exists in v43.

Controller log contains exactly the same18 artifact events (8initial/10final), with no extra task event. Status complete: 2026-10-21 17:37:27.628100–18:03:20.114084 UTC; controller exited0 with fresh child status. Saved API created times range17:37:31–18:01:56 and all lie within the run window. Per-call logs record monotonic duration rather than a full UTC start/end pair; metadata entries have no per-request UTC timestamps. This audit does not invent finer latency or timestamp provenance.

All wire settings are output cap1536, temperature0, top_p1, seed20261021. Every normalized origin is `user_authorized_Qwen32B_endpoint`; raw messages contain no native model tool_calls. This proves recorded endpoint/model identity, not independently loaded model weights. No retries/reset/recovery fields or second physical slot attempts appear. Frozen source enforces consumed attempts, cap24, fail-closed tokenizer and quota-only continuation; inherited client internal cap72 is narrowed by the active v43 cap24 wrapper. No quota continuation occurred.

## Actual usage and latency

| Stage | Received calls | Input tokens | Output tokens | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| initial | 8 | 8,191 | 1,561 | 9,752 |
| final_raw | 5 | 7,980 | 506 | 8,486 |
| final_tool | 5 | 14,468 | 502 | 14,970 |
| **Total** | **18** | **30,639** | **2,569** | **33,208** |

Known v43 completion usage is33,208 tokens, including schema-invalid responses; unknown v43 completion usage0. Tokenizer counts are context sizes, not additional generated tokens or billable completion usage. No paid API response/cost ledger exists here; dollar cost and GPU/energy cost are unmeasured, not asserted zero.

Completion latency sum1520.922s; mean84.496s; median84.227s; min69.329s; max97.921s. Run wall1552.486s (~25m52s). Duration includes HTTP client timing and is not a pure inference benchmark.

The original v40 d1 still has its distinct historical failed E3__concept_adaptive__1 completion attempt:180.101s, usage_known=false, transport_or_JSON_failure,0response. Its frozen bytes are unchanged. Keep that one historical unknown separate; it is neither recovered nor attributable to v43, and no token/dollar estimate is fabricated.

Saved launch quota53% at17:37:27 and final pre-call quota50% at18:01:55 are both above stop<=15%, should_stop=false. The frozen wrapper checks quota before each completion, but only the latest snapshot is retained; the full per-call quota history cannot be independently reconstructed. This audit made no quota call.

## Tool realization and paired evidence parity

All five schema-valid initial proposals request all three tools. Thus15 requested components produce15 saved feedback components in five tool-result files; no empty selection, component error or extra model/native tool execution is recorded. Three invalid initials have no tool-result file. The JSON records raw saved status/reason/holds counts; no diagnostic tool function was called to reproduce them.

| Episode | Bindings | Saved matrix cells | Computed / unknown | Contrast pairs returned / found |
| --- | ---: | ---: | ---: | ---: |
| E2 | 3 | 21 | 7 / 14 | 4 / 9 |
| E4 | 3 | 21 | 7 / 14 | 4 / 21 |
| E5 | 3 | 27 | 9 / 18 | 4 / 20 |
| E7 | 3 | 27 | 0 / 27 | 4 / 36 |
| E8 | 3 | 30 | 30 / 0 | 4 / 45 |

Totals:126 matrix cells =53 computed +73 unknown; among computed cells44 holds true and9 false. Unknown reasons are39 binding_unknown +34 binding_arguments_or_observation_unsupported. Twenty contrast pairs are returned in total (four/case); `found` is the saved pre-cap pool count, not extra requests or executions. Five partial return-dependency inventories are present. Unknown cells are not transport/tool-component failures and computed/holds does not establish normative truth.

For all five realized pairs, raw and tool persisted messages have identical system message and identical parsed user packets after removing only `tool_feedback`: instruction, exact spec/source/parameters, complete raw observations, global operators/compatibility, shared initial proposal, mechanical candidate_checks and reply schema. Observations/proposal match the frozen pool/received initial. Raw feedback is null; tool feedback exactly equals its saved tool-result record, whose pool hash matches the raw rows. No actual facts were trimmed or arm-specific candidate repair added. All78 reused rows remain the full denominator across eight episodes, even though only42 rows in valid-initial episodes reach paired finals.

Return-read inventory is partial and not sound slicing/causality; contrasts hold one argument fixed rather than guarantee one semantic dimension; relation agreement is observational, not a spec oracle. Finite vocabulary was engineered using these seen fixtures. Those scope limits remain explicit. Semantic review must judge all eight initial slots and16 final slots with failures retained; this integrity PASS provides no efficacy promotion.
