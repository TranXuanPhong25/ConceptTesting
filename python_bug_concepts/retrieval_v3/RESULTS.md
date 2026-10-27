# Đánh giá chất lượng Python bug concept retrieval

Kết quả trên 113 buggy PUT HumanEval. Hit yêu cầu concept mô tả actual bug; chỉ liên quan đến một operation không được tính. Corpus và các task đã được xem khi phát triển, nên các số dưới đây không phải đánh giá generalization độc lập.

## Retrieval và cải thiện

| Retriever | Bug family hit@3 /113 | Family + first faulty site /113 | Hit@1 /113 | Returned cards | Frozen-label precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| V2 structural | 88 | 74 | 73 | 275 | 34.9% |
| V3 Qwen nguyên bản | 77 | 67 | 73 | 167 | 49.1% |
| V3 + phục hồi duplicate ID | 85 | 73 | 81 | 181 | 50.3% |
| V4 hybrid, post-hoc | 90 | 78 | 82 | 281 | 35.2% |

V4 giữ row đầu của ID trùng, áp dụng các parser check còn lại, rồi xen kẽ Qwen rank1 / v2 rank1 / Qwen rank2… đến ba ID duy nhất. Response invalid/empty dùng v2 fallback. Không dùng gold/reference/judge tại retrieval. Không sửa raw hay kết quả v3 gốc. V4 tăng coverage, nhưng không chứng minh precision cao hơn: trả nhiều card hơn và precision theo label gần như v2. Gold chỉ có 91/113 task được gán mechanism và chưa đầy đủ; unmatched card không tự động là sai.

## Review chất lượng trực tiếp

Mẫu cố định 20 trong 167 row v3 được chọn bằng SHA256, không thay mẫu. Review source/spec/reference và replay native có official-contract check; reviewer là cùng tác giả của project, không phải independent annotator. Packet không chứa gold hoặc judge score.

- Concept mô tả actual bug family: **13/20 (65%)**.
- Đúng cả where/how/what: **9/20 (45%)**.
- Where đúng 12/20; how đúng 11/20; what đúng 10/20.
- Một concept có thể đúng cơ chế nhưng ví dụ/expected output trong what sai. Đánh giá strict: ví dụ cụ thể sai làm what không đạt.
- Mẫu nhỏ; khoảng Wilson danh nghĩa cho 13/20 là 43–82%, chưa tính clustering theo task. Không suy rộng 65% thành precision đã xác minh trên toàn corpus.

## Kiểm tra judge bằng execution

Review có chủ đích các claim sai và positive controls; đây là diagnostic, không phải mẫu dùng ước lượng precision. Cả tám input kiểm tra claim sai đều hợp lệ và PUT trả giống reference. Trong đó năm card vẫn bị Qwen judge chấm grade 2. Source/spec reasoning, cùng replay, bác bỏ claim cụ thể; equality trên một ví dụ riêng lẻ không đủ chứng minh mọi ứng dụng của card đều sai.

| Task | Claim sai / vì sao | PUT và reference | Judge grade |
| --- | --- | --- | ---: |
| HumanEval/12 | Qwen claims max retains the last tied maximum; Python retains the first. Lowercasing changes neither input in this case. | `'a'` | 2 |
| HumanEval/54 | False contract: same character sets may have different multiplicities; public examples explicitly permit this. | `True` | 2 |
| HumanEval/66 | False control flow: every recursive invocation checks the empty-string guard before indexing. | `0` | 2 |
| HumanEval/68 | False mechanism: index(min_value) returns the first occurrence required by the specification. A separate first-even fallback bug exists. | `[2, 1]` | 2 |
| HumanEval/68 | False prediction: all-odd input reaches the final empty-list return. | `[]` | 0 |
| HumanEval/71 | False oracle: a degenerate triangle is invalid under the strict triangle-inequality contract. | `-1` | 2 |
| HumanEval/5 | False bounds claim: two inserted sentinels and range(len-1) keep every adjacent index in bounds. | `[]` | 0 |
| HumanEval/48 | False requirement: a single-character string is a palindrome; no minimum length of two is specified. | `True` | 0 |

Positive controls: Unicode byte-count, negative maximum sentinel, fixed triple-space replacement và signed difference đều có official-valid input làm PUT khác reference. Kết quả và exact argument nằm trong `NATIVE_CLAIM_AUDIT.json`.

## Qwen judge trên toàn bộ returned concepts

Judge schema hợp lệ trên 111/113 task; v3 có 13 response retrieval invalid. Judge cùng model với retriever và có thể đoán method từ style; chỉ là auxiliary score.

| Metric | V2 | V3 original |
| --- | ---: | ---: |
| Grade >=2 / all returned | 41.8% | 65.9% |
| Mean grade 0–3 | 1.178 | 1.822 |
| Where accuracy, graded bindings | 37.0% | 73.6% |
| How accuracy, graded bindings | 31.1% | 69.9% |
| What accuracy, graded bindings | 21.5% | 67.5% |

**Các false positive native ở trên cho thấy không được dùng judge score như ground truth.**

## Native utility: concept có giúp tạo test không?

Trạng thái: **complete**, đã lưu 120/120 arm record, các slot có response thành công 120; native grading đã có. Chưa hoàn tất không được diễn giải thành 0 bug.
Số unique utility request trong các arm đã lưu: 112; 8 arm slot dùng chung exact response do message/seed giống nhau. Không gọi lại các request này.

| Metric | Plain | V2 | V3 original |
| --- | ---: | ---: | ---: |
| Proposed tests | 120 | 114 | 117 |
| Official-valid tests | 119 | 110 | 111 |
| Correct oracle tests | 118 | 106 | 105 |
| Confirmed bug tasks /40 | 4 | 18 | 15 |
| False-alarm tests | 0 | 4 | 5 |
| False-alarm tasks | 0 | 2 | 4 |
| Unresolved workers | 0 | 0 | 0 |

v3_vs_plain: 12 task win / 1 loss.

v3_vs_v2: 2 task win / 5 loss.

Confirmed bug cần input hợp lệ, expected output khớp reference và PUT khác reference hoặc raise. False alarm là assertion fail với expected output sai. Missing/invalid response vẫn giữ task denominator 40. Ba arm có cùng 40 task slots, seed và token cap; exact request giống nhau được dùng chung response như đã ghi. V3 có thêm chi phí retrieval. Utility dùng card definition, không có v3 explanations. Không suy utility v3 thành hiệu quả của v4 hybrid.

Kết luận: V2 tốt hơn original V3 về native bug-task coverage và false alarms trong cohort này. V4 tăng retrieval family/site coverage trên dữ liệu đã xem nhưng chưa có utility riêng; giữ v2 làm default. Concept hints có ích trong phép thử plain-vs-hinted này, nhưng chưa có placebo hoặc independent holdout để khẳng định generalization hay causal attribution cho từng concept.

## Artifacts

- [V4 API](../retrieval_v4/README.md).
- [Ranking từng task](continuation_20261027/RANKING.json).
- [Manual sample review + native replay](continuation_20261027/MANUAL_SAMPLE_REVIEW.json).
- [Native claim audit](continuation_20261027/NATIVE_CLAIM_AUDIT.json).
- [Quality summary và usage](out/run_20261026/QUALITY_SUMMARY.json).
- [Utility native outcomes](out/run_20261026/utility_grading.json).
- [Continuation preregistration](continuation_20261027/PREREG.md).

Verification: 60 unit/regression tests pass, bao gồm đối chiếu V4 API với ranking đã lưu trên đủ 113 task. Frozen v2 labels và ba file run/prompts/client v3 không thay đổi. Raw request/response và original terminal failure giữ nguyên.
