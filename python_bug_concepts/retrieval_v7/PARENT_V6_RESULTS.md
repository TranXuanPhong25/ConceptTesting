# Parent V6 results copied unchanged in substance; these are NOT V7 outcomes

V6 là copy của v5; corpus162card, source/vendor và labels cũ giữ nguyên. User cho phép cải thiện lặp từ các kết quả sai. Các số dưới đây là development-informed trên113source đã xem, không phải independent holdout. Không gọi Qwen/paid API, không training hay tái hiện paper.

## Kết quả cùng cohort, cùng frozen labels

| Retriever/policy | Family hit@1 | Family hit@3 | Family + first site hit@3 | Returned cards | Matched frozen labels / returned |
| --- | ---: | ---: | ---: | ---: | ---: |
| V2/V5 | 73 | 88 | 74 | 275 | 34.9% |
| V6 coverage | 90 | 91 | 90 | 270 | 36.3% |
| V6 balanced | 90 | 91 | 90 | 126 | 74.6% |
| V6 precise | 62 | 63 | 63 | 82 | 80.5% |

**Balanced tăng16site hits, không mất site/family hit cũ; giảm149returned cards.** Top1 family tăng73→90. Corpus/labels chỉ có91task đã gán family;22task chưa gán vẫn là misses trong denominator113.

**Label-match rate không phải precision độc lập.** Labels chưa đầy đủ, được gán bởi cùng project author và dùng để phân tích phát triển. Không diễn giải74.6% hay80.5% thành xác suất card đúng ngoài cohort.

## Quality control trên canonical code

Reference implementation được đưa vào như một standalone source query để kiểm tra over-retrieval, không được cung cấp cùng buggy query. Runtime chỉ nhận source. Canonical được tin cậy dưới benchmark contracts; một phần input-domain restriction không có trong public docs.

| Method | Correct-program queries có candidate /113 | Returned cards |
| --- | ---: | ---: |
| v2 | 100 | 222 |
| coverage | 99 | 212 |
| balanced | 99 | 99 |
| precise | 5 | 5 |

**Đây là over-retrieval diagnostic, không phải bug-report false-positive rate.** Primary results vẫn là hypotheses. Balanced giữ weak fallback khi thiếu evidence nên không phù hợp nếu muốn abstain trên code có thể đúng. Precise loại weak fallback, nhưng chỉ đạt63/113site hits; đây là tradeoff coverage/chất lượng, không được giấu bằng một số tổng hợp.

## Native audit của các mechanism cụ thể

21/21 input hợp lệ theo official contract và làm PUT khác reference hoặc raise; cả ba policy retrieve đúng concept được kiểm tra. Inputs được chọn có chủ đích từ source/error audit, **không phải một mẫu để ước lượng precision**.21case gồm20outcomes đã có và một correction; proposal cũ truyền sai shape ở task23 giữ trong iter03, không được tính hợp lệ.

| Task | Mechanism | Input | Reference | PUT |
| --- | --- | --- | --- | --- |
| HumanEval/19 | `py.presence-frequency-confusion` | `["one one"]` | `'one one'` | `'one'` |
| HumanEval/20 | `py.negative-index-sentinel` | `[[1.0, 2.0]]` | `(1.0, 2.0)` | `(2.0, 1.0)` |
| HumanEval/23 | `py.unicode-text-byte-domain` | `["é"]` | `1` | `UnicodeEncodeError` |
| HumanEval/27 | `py.ascii-unicode-classification` | `["É"]` | `'é'` | `'É'` |
| HumanEval/62 | `py.index-origin-domain` | `[[1, 2]]` | `[2]` | `[4]` |
| HumanEval/68 | `py.first-match-vs-optimum` | `[[1, 4, 2]]` | `[2, 2]` | `[4, 1]` |
| HumanEval/74 | `py.aggregation-scope` | `[["aaa"], ["b", "c"]]` | `['b', 'c']` | `['aaa']` |
| HumanEval/126 | `py.index-out-of-bounds` | `[[1, 1]]` | `True` | `IndexError` |
| HumanEval/136 | `py.empty-reduction-domain` | `[[0, 0]]` | `(None, None)` | `ValueError` |
| HumanEval/163 | `py.index-origin-domain` | `[1, 4]` | `[2, 4]` | `[1, 3]` |

Native replay chứng minh input validity và outcome mismatch, không tự chứng minh causal attribution cho mọi card. Reference/contract chỉ có ở grading, không đi vào index/query/ranking. Không gán các kết quả này thành efficacy của một test generator.

## Sửa lỗi ở đâu

- `semantic.py` / `roles.py`: requires được kết nối với vai trò operation/public contract; tier có tác dụng lên ranking. Correct API usage không còn tự động là mechanism có support.
- `engine.py`: rank concept/site pairs, consume exclusions, phân biệt coverage/balanced/precise và review candidates; giữ nguyên status unverified.
- `facts.py`: qualified-symbol provenance qua comprehension/tuple/branch; inherited helper purpose; annotations phải resolve builtin; scope và exact span giữ được.
- Recognizers mới: ASCII ranges, sorted-input multiplicity, unsafe loop offsets, zero sentinel khi dùng index−1, compound frequency criteria, derivative coefficient roles và shortcut bỏ conjunct.
- Chặn false positives đã thấy: hash encoding ≠ character counting; len(set) không quan sát order; modulo==0 không phụ thuộc dấu; lambda không capture biến loop không phải late binding; boolean short circuit vẫn có thể trả bool.

## Iteration history

| Iteration | Coverage family/site | Balanced-equivalent family/site | Notes |
| --- | --- | --- | --- |
| iter01 | 90/88 | 79/79 | Semantic tiers; precise khi đó còn weak fallback. |
| iter02 | 91/90 | 90/89 | Sửa operator-role false positives; precise khi đó tương đương balanced. |
| iter03 | 91/90 | 91/90 | Tách strict abstention; sửa branch/tuple provenance và role checks. |
| iter04 | 91/90 | 91/90 | Inherited helper purpose và delimiter normalization. |
| iter05 | 91/90 | 91/90 | Module fragment robustness. |
| iter06 | 91/90 | 91/90 | Exported fact-ID integrity; final shipped source. |

Mỗi iteration có freeze, source snapshot và per-task output riêng. Không overwrite bản cũ hay sửa label để tạo gain. Iteration01 có regression được giữ lại; final balanced có16wins/0losses về first-site so với v2/v5.

## Verification và giới hạn

- 242unit/regression tests pass; parser/analyzer không execute target. CLI/API v6 và cả ba policy đã test.
- Final semantic source/config freeze; parent-copy hashes, old corpus và source snapshots được kiểm tra. Fact IDs/source spans được đối chiếu trên cả113query.
- Rule matching vẫn partial, phụ thuộc public semantics và domain assumptions; không phải complete alias analysis, formal verifier hay calibrated classifier.
- Chưa có independent heldout, independent annotator hoặc native test-generation utility run cho v6. Không tuyên bố v6 hơn v11 về bug detection.

## Dùng bản mới

```python
from python_bug_concepts import search
packet = search(code=source, retriever="v6", policy="balanced", top_k=3)
```

Cần LibCST1.9.0; xem [README](README.md). Public auto vẫn v2 để giữ compatibility. Chọn explicit v6 để dùng ranking đã cải thiện; chọn precise khi ưu tiên abstention.

[Final machine-readable results](evaluation_v6/iter06/RESULTS.json) · [Correct-program controls](evaluation_v6/iter06/CANONICAL_CONTROLS.json) · [Native cases](evaluation_v6/iter06/NATIVE_AUDIT_FINAL.json) · [Implementation audit](AUDIT.md)
