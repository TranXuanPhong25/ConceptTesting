# v50: independent semantic review của full-revision diagnostic

Ngày 2026-10-24. Scope: toàn bộ 8 initial và 16 final raw responses trong `out/pipelines/v50_binding_revision/humaneval/revision8`, theo rubric prospective `analysis/v50_binding_revision_20261023/EVALUATION.md`. Không gọi model/HTTP, không chạy PUT, không sửa source, frozen artifacts hoặc reports cũ.

**Kết luận: NO-GO theo registered gate.** Không có tool-only semantic episode success, không có raw-only loss; E8 cả hai arms đều invent requirement thay vì nhận ra spec không định nghĩa “suitable”. Tool không chứng minh thêm semantic capability trong diagnostic này. Đây là seen-fixture binding/judgment diagnostic, chưa phải concept-guided input-generation hoặc transfer experiment.

**Cách review và giới hạn**

Reviewer đọc mọi raw item, gồm `rejected`, `unknown`, phần reason và evidence references; đối chiếu prepared spec/code và 78 saved observations. Final replies được đổi thành A/B độc lập từng episode bằng deterministic shuffle trước đánh giá; mapping được reveal sau lượt đọc. E1 raw đã được xem khi kiểm tra schema nên không blind hoàn toàn. Masking này không bảo đảm suy luận mù tuyệt đối vì wording có thể gợi ý tool feedback. Một reviewer thực hiện pass này; chưa có second independent semantic adjudication.

Chấm riêng (1) relation/facet coverage và truthful judgment, (2) concrete concept-label compatibility, (3) interface errors. E2 là điểm cần ghi rõ: `count_ge(xs,limit)` đúng và được justify, nhưng label `quantified_decision` không tương thích với vocabulary đã freeze (`count_ge` thuộc `eligible_contribution`; `quantified_decision` dùng `all_even`/`any_even`). Theo câu “A concrete concept label must be semantically compatible”, strict complete success không tính E2; label-neutral relation/judgment metric vẫn nhận E2. Gate verdict không thay đổi theo cách adjudicate này.

E7 có optional `ascending(arguments=[])` sai arity. Không tự sửa item này thành executable; `preserve_occurrences(xs)` riêng đã admitted/executable và được justify đúng, nên vẫn tính primary facet coverage theo rubric “An unrelated malformed item does not erase a valid supporting item”. Readable ascending property là đúng theo spec/code; không có false normative endorsement ở optional property này.

**Denominators và outcomes**

| Metric | Initial | Final raw | Final tool |
|---|---:|---:|---:|
| Assigned/received replies | 8/8 | 8/8 | 8/8 |
| Parseable replies | 8 | 8 | 8 |
| Envelope-valid replies | 8 | 7 | 7 |
| Admitted bindings / raw binding items | 24/24 | 20/21 | 20/21 |
| Justified correct required relation with executable binding, label-neutral | 2/8: E2,E4 | 3/8: E2,E4,E7 | 3/8: E2,E4,E7 |
| Strict label-compatible complete semantic success | Initial requirement only: 1/8, E4 | 2/8: E4,E7 | 2/8: E4,E7 |
| Correct implementation judgment enum | Not requested | 7/8 | 7/8 |
| Final evidence IDs mechanically valid | Not requested | 8/8 | 8/8 |
| Correct ambiguity handling E8 | No | No | No |

Initial stage did not request implementation judgment, so initial requirement coverage is not directly comparable to full final success. All rejected/unknown items remain in the review; they do not supply normative required-facet credit. Correct enum and valid evidence IDs do not imply truthful reasoning.

| Episode | Initial requirement state | Final raw | Final tool | Semantic finding |
|---|---|---|---|---|
| E1 | Correct `preserve_occurrences(xs)` rejected; invalid one-argument subset and zero-argument ascending endorsed | FAIL | FAIL | Both identify duplicate loss in prose, yet continue rejecting the required conservation rule; neither has justified executable primary facet. Tool also conflates duplicate preservation with subset membership in reason. |
| E2 | Correct `count_ge(xs,limit)` justified; wrong concrete concept label | Label-neutral PASS; strict label FAIL | Same | Both retain the right relation, reject `count_gt`, and correctly explain equality-boundary bug. No tool-only improvement; label incompatibility remains. |
| E3 | Right subset binding stays unknown; equality rejected | FAIL | FAIL | Neither endorses the normative subset requirement. Raw falsely groups O5/O6/O8 as cases where required is a subset of container; those rows are not such cases. Tool says set equality includes duplicates, contradicting `set` semantics. |
| E4 | Correct `min_positive_none(xs)` justified, with two unrelated unknown local-role candidates | PASS | PASS | Both remove unsupported local-role items and correctly explain ValueError vs None on O1/O2/O5/O6/O7. No new semantic win from tool. |
| E5 | Right `sum_le_limit(xs,limit)` unknown | FAIL | FAIL | Raw keeps correct relation unknown; tool changes it to rejected. Both correctly identify the unsupported length guard in prose but do not justify the required relation. Both emit a fourth binding outside cap=3. |
| E6 | Wrong `sum_gt_one` rejected; no full positive-sum requirement endorsed | FAIL | FAIL | Tool introduces correct `sum_positive(xs)` but leaves status unknown. Raw keeps unknown operator. Both note exclusion of 1; neither supplies an endorsed full eligibility+multiplicity requirement. Tool reason omits deduplication defect. |
| E7 | Conservation rule unknown; ascending endorsed with invalid zero-argument binding | PASS | PASS | Both promote executable `preserve_occurrences(xs)` to justified and correctly report no mismatch. Unused local `set(xs)` does not cause false bug. Optional ascending item remains invalid arity. |
| E8 | Unconditional `first(xs)` incorrectly justified | FAIL | FAIL | Both retain `first` and report no mismatch, treating observed first-item behavior as spec truth. Neither says “suitable” is undefined. |

**Review of raw items beyond the winning relation**

- E1: rejecting `preserve_occurrences` despite a verbatim explicit normative clause is a semantic rejection error, even though mismatch prose is right. Initial `required_subset_container(xs)` is an invalid arity and wrong output kind; final raw rejects it; final tool changes it to equally inapplicable `equal_sets(xs)` and rejects it. `ascending([])` remains only a partial/invalidly bound property, not primary coverage.
- E2: rejected `count_gt` is a legitimate rejected alternative; its bad label does not create a false endorsed relation. Unknown third item is not an invented endorsed requirement. Endorsed `count_ge` label remains incompatible under frozen definitions.
- E3: unknown `required_subset_container(container,required)` is executable and correctly ordered but not a normative endorsement. Rejected `equal_sets` is correctly rejected. Generic unknown third item adds no facet coverage. Raw's cited O3 is a real counterexample, but O5/O6/O8 do not support its stated subset claim; tool has a valid broad explanation of the extra-container issue plus its distinct false duplicate statement.
- E4: initial unknown items refer to local `ys`, which is outside input-role scope. They remain syntax-admitted but are not executable task bindings; final arms remove both without harming the correct first binding.
- E5: the three unknown generic conditions are not executable missing requirements. Fourth item is mechanically rejected; its prose is not a false requirement, so cap violation is reported separately. Even ignoring that interface problem, semantic success still fails.
- E6: rejected `sum_gt_one` is correct rejection. `preserve_occurrences(xs)` predicts a list property and is not a full scalar-sum oracle; rejecting it is not itself rejecting the proper weighted contribution semantics. The tool's new positive-sum relation is a descriptive revision signal, not accepted success, because `spec_status=unknown` cannot substitute for justified.
- E7: unknown `equal_sets(xs)` is wrong arity and not a requirement, but is not endorsed. The valid conservation binding and truthful code/source references are sufficient independently. No fabricated observation claim was found in either E7 reason.
- E8: unrelated initial unknowns do not repair the endorsed `first` assumption; finals actually remove those unknowns and express stronger unjustified confidence.

**Transitions and interface separation**

Raw and tool both retain E2's correct relation, retain E4's correct full requirement and newly justify E7's conservation requirement. These initial→final changes are descriptive; both arms see additional shared observations and revision opportunity, so they do not isolate a causal tool effect. Tool-specific E6 revision (`unknown` → correct operator `sum_positive`, still unknown) does not meet the endorsement requirement. Tool-specific E5 change unknown→rejected moves away from the spec. No resulting primary semantic success/loss differs between arms.

Read-only comparison of all eight paired final request packets found exactly one differing field in each pair: `tool_feedback`. Spec, code, initial replies/admission, candidate checks, observations, evidence IDs, vocabulary, instructions and reply schema are identical. This supports evidence parity for this revision experiment; the added field consists of computations from shared observations, not new target executions or gold normative truth. It does not turn the result into a concept-vs-no-concept test: both arms already receive the concept vocabulary and binding interface.

Every reply is readable and all 16 final judgment enums/evidence-ID lists pass mechanical admission. Two final envelopes fail solely because E5 has four items. Seven raw and seven tool final envelopes are valid, but the semantic failures E1/E3/E5/E6/E8 survive interface leniency. This rules out an explanation that the entire null result is caused by all-or-nothing schema rejection; that historical v43 limitation was repaired here.

No observed-mismatch verdict is asserted on the correct E7 or ambiguous E8, so there is no new false-bug enum on those controls. However, E8's invented normative `first` requirement independently violates the registered gate, which forbids invented requirements and requires correct E8 handling. No actual generation, new target execution or bug-discovery gain was measured by this run.

**Integrity and resources checked in this review**

Read-only byte hashing matched 64 frozen source files and all generation inventory entries: prepared 8, requests 24, artifacts 24, feedback 8, transitions 16, transport 222; zero missing, drifted or extra files within those inventoried directories. EVALUATION.md hash matches freeze. Root separately reports exact pinned-interpreter `revision.verify(full=True)` PASS, including dependencies, approvals and v43/v40 parent integrity, plus independent generation inventory PASS. This broader result is not inferred from byte hashing alone.

All 24 artifacts have received model responses. Saved response usage sums to 49,800 prompt + 6,435 completion = **56,235 known task tokens**: initial 10,070; final raw 20,286 (17,931 prompt + 2,355 completion); final tool 25,879 (23,462 prompt + 2,417 completion). Tool final prompts use 5,531 more input tokens than raw; call counts are matched, actual tokens are not. Dollar cost is not recorded in these artifacts; no zero-dollar claim is made. Root transport audit should separately report attempted/unknown requests and metadata/tokenizer activity; response totals alone do not prove transport completeness.

**Registered gate evaluation**

| Gate condition | Finding |
|---|---|
| At least 2 genuine tool-only semantic episode successes | FAIL: 0 |
| Zero raw-only semantic losses | PASS: 0 |
| No added false bug or invented requirement | FAIL on invented E8 requirement; false-bug enum itself absent |
| Tool correctly handles E7 | PASS |
| Tool correctly handles E8 | FAIL |

The NO-GO holds whether E2 is treated as label-neutral primary success (3/8 each) or strict complete success (2/8 each). Do not rewrite old thresholds, compare v43/v50 as a paired efficacy experiment, or promote from these eight authored seen fixtures to new-task capability. The actionable mechanism is normative-status confusion: a relation contradicted by buggy execution is repeatedly marked rejected/unknown even when spec explicitly requires it, while agreement on ambiguous E8 is treated as justification. Reusing the current package in a larger run is not supported.

**Artifact paths**

- Rubric: `trickcatcher_linefacts/analysis/v50_binding_revision_20261023/EVALUATION.md`.
- Frozen run root: `trickcatcher_linefacts/out/pipelines/v50_binding_revision/humaneval/revision8/`.
- Episode context/observations: `prepared/E1.json` … `prepared/E8.json`.
- Raw replies, per-item admission, token usage: `artifacts/E{n}__initial.json`, `artifacts/E{n}__final_raw.json`, `artifacts/E{n}__final_tool.json`.
- Full prompt packets and evidence IDs: corresponding `requests/` files.
- Descriptive operator/status transitions: `transitions/E{n}__raw.json`, `transitions/E{n}__tool.json`; these are not semantic success scores.
- Review annotations: `V50_SEMANTIC_REVIEW.json` beside this report. Paths and counters are sufficient to retrace this pass; no endpoint URL or secret is stored here.
