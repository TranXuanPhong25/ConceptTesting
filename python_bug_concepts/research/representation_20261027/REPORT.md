# Research: cải thiện Python bug concept representation và retrieval

2026-10-27. Phạm vi: đọc paper/docs và phân tích retriever đã có. Không triển khai
lại paper, không cài dependency/model mới, không gọi Qwen hay paid API, không đổi
corpus/ranker/default hoặc các frozen outputs. Mỗi paper có notes trong folder riêng.

**Đề xuất ưu tiên:** giữ v2 làm baseline; thử biểu diễn mỗi candidate bằng
`concept + source span + public-contract clause + semantic facts`, rồi kiểm tra
applicability và chọn site. Giữ where/how/what làm output, bổ sung cấu trúc để hỗ
trợ chúng. Embedding là một channel bổ sung, chưa phải giải pháp chính.
Đây là đề xuất thiết kế từ evidence, chưa có kết quả cải thiện của implementation.

## 1. Bottleneck thực tế

[Diagnostic](DIAGNOSTIC.json) chạy lại analysis của engine v2 trên đúng inputs
đã có, không execute PUT. Có thể tái tạo bằng:

```bash
python -m python_bug_concepts.research.representation_20261027.diagnose
```

| Diagnostic trên 113 task | Số task |
| --- | ---: |
| AST parse thành công | 113 |
| Có ít nhất một frozen actual-bug family label | 91 |
| Có đúng family trong toàn bộ structural candidate pool | 89 |
| Family hit@3 | 88 |
| Family hit@5 | 89 |
| Family + first selected site hit@3 | 74 |
| Giữ tất cả candidate, vẫn dùng site ưu tiên đầu của mỗi card | 75 |
| Chọn bằng oracle từ mọi raw evidence site của mọi card | 87 |

**Suy luận:** trên phần đã có labels, family ranking chỉ bỏ lỡ một task mà pool
đã chứa; tăng top-k không giải quyết phần lớn lỗi. Site selection có headroom rõ
hơn: 87 là oracle ceiling của evidence đã có, không phải kết quả của retriever mới.
Hai task mất gold family từ structural gate là /19 và /27; hai task khác chưa có
đúng evidence site là /57 và /69. Cần sửa generalization của extraction chứ không
thêm rule theo task ID.

22 task chưa có labels là unknown, không phải 22 task thiếu concept trong corpus.
Không dùng diagnostic này để kết luận corpus đầy đủ. Frozen labels/site vẫn là
single-author, development-informed và chưa exhaustively graded.

[Quality report](../../retrieval_v3/RESULTS.md) còn cho thấy:

- V3 có 13 schema failures; duplicate recovery là engineering fix riêng.
- Mẫu 20 V3 rows: 13 đúng family, 9 đúng đủ where/how/what.
- Năm false-positive grade2 của judge bị source/spec reasoning và native replay bác bỏ.
- Utility40: plain4, v2 18, v3 15 confirmed bug tasks; false-alarm tasks0/2/4.

Trong engine hiện tại, `has_set`, `has_sort`, symbols và một phần spec matching
được tổng hợp trên cả tree; `initial` map dùng tên biến, trong khi alias/shadowing
đã có một phần scope handling riêng. Vì vậy không nên coi toàn bộ extraction là
scope-aware hoặc value-flow-aware. Structural score chủ yếu là priority theo rule,
BM25 cộng thêm; first evidence site cũng chọn theo priority. Đây là các điểm có
thể cải thiện mà không thay language parser.

## 2. Paper nào liên quan và nên lấy gì

| Nguồn primary | Ý tưởng liên quan | Giới hạn khi áp dụng |
| --- | --- | --- |
| [GraphCodeBERT](https://arxiv.org/abs/2009.08366) | Giữ data-flow/value-origin trong code representation. | Code-search benchmark không đo actual semantic bug; checkpoint base không tự thừa hưởng kết quả fine-tuned. |
| [CodeTrek](https://research.google/pubs/codetrek-flexible-modeling-of-code-using-an-extensible-relational-representation/) | Program facts thành relational database; query tạo relation mới. | Mô hình neural của paper khác fact matching được đề xuất ở đây. |
| [BugLab](https://proceedings.neurips.cc/paper/2021/file/ea96efc03b9a050d895110db8c4af057-Paper.pdf) | Entities và typed relations cho Python bug localization/repair. | Cần training; bug distribution khác; không phải concept retriever có sẵn. |
| [UniXcoder](https://arxiv.org/html/2203.03850) | Code/comment/AST representation và code search. | Functional similarity không xác nhận cùng bug mechanism. |
| [CodeRetriever](https://arxiv.org/abs/2201.10866) | Contrastive code–code và code–text retrieval. | Không có supervision tự động cho điều kiện gây bug của corpus này. |
| [Vul-RAG](https://arxiv.org/html/2406.11147v3) | Tách functionality, causes và fixes; multi-view BM25/rank fusion. | Chủ yếu C/C++ vulnerabilities; không suy hiệu quả sang HumanEval. |
| [Revisiting Vul-RAG, 2026](https://arxiv.org/html/2606.04739v1) | Reproduction nhấn mạnh giới hạn phân biệt buggy/fixed code. | Preprint, setting khác; kết quả không phủ định mọi hướng structured retrieval. |

Vul-RAG là nguồn gần bài toán knowledge-base này nhất. Điểm đáng thử là **tách
representation dùng để tìm candidate khỏi representation dùng để xác nhận
applicability**. Không nhất thiết thay BM25 bằng vector search trước. Reproduction
2026 cho thấy pairwise accuracy tốt nhất của các model được xét chỉ 0.29, so với
random0.25; do đó không nên xem semantic RAG hay model lớn là bảo đảm chất lượng.

## 3. Có nên đổi parser?

| Stack | Có thêm gì | Chưa cung cấp gì | Ưu tiên cho case này |
| --- | --- | --- | --- |
| stdlib AST + scope utilities | Syntax tree, spans; có thể dùng làm nền cho extraction hiện tại. | Không tự có complete data flow, path constraints hay task semantics. | Giữ làm baseline; parse coverage hiện đã 113/113. |
| [LibCST metadata](https://libcst.readthedocs.io/en/latest/metadata.html) | Exact source structure, position, parent, scope, qualified-name metadata. | ScopeProvider không phải reaching-definitions/path-sensitive DFG; TypeInferenceProvider cần Pyre setup riêng. | Ưu tiên để làm source binding và scope đúng, nếu triển khai. |
| [Astroid](https://pylint.readthedocs.io/projects/astroid/en/latest/inference.html) | Partial value/type inference qua `infer()`. | Có `Uninferable`; không phải proof engine hoặc đầy đủ cho dynamic Python. | Optional khi cần phân biệt API/type. |
| [CodeQL Python local data flow](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-python/) + [control flow](https://codeql.github.com/docs/codeql-language-guides/analyzing-control-flow-in-python/) | Có library/query cho local value flow, CFG và reachability. | CFG reachability không chứng minh path feasible hoặc đúng public contract. Cần database/toolchain riêng. | Tham chiếu hoặc reuse analysis library nếu engineering cost hợp lý. |
| [Tree-sitter](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html) | Parse/query syntax, biểu diễn ERROR node khi source hỏng. | Đổi syntax tree không tự bổ sung scope/dataflow/spec reasoning. | Fallback cho fragments; ít giá trị trực tiếp với 113 source hiện parse được. |

Hiện default Python chưa có libcst/astroid/tree_sitter/crosshair; chưa cài thêm.
Không cần chuyển cả pipeline sang full PDG/SSA ngay. Với Python dynamic, aliasing,
exceptions, nested scopes và dynamic dispatch đều có thể làm facts không chắc.
Phải lưu `unknown`, không mặc định missing evidence thành safe hay buggy.

## 4. Biểu diễn concept khác: applicability rõ, where/how/what vẫn giữ

Đây là schema minh họa do mình đề xuất, không phải format hay thuật toán sao chép
của một paper:

```yaml
id: py.set-loses-multiplicity
where:
  operation: set_conversion
  source_binding: fact_id + node_span + scope_id
applicability:
  requires:
    - public_contract_requires_occurrence_counts
    - converted_value_flows_to_result_or_decision
  excludes:
    - public_contract_requires_only_distinct_membership
  unknown_policy: keep_as_unverified_candidate
how:
  information_lost: occurrence_count
  causal_relation: multiplicity_removed_before_count_sensitive_observation
what:
  distinguishing_input_class: same_members_different_multiplicities
  failure_relation: count_sensitive_result_disagrees_with_contract
semantics_evidence:
  - pinned_python_set_semantics
```

`requires/excludes` là nghĩa vụ kiểm tra, không tự coi là facts đã đúng. Ví dụ
same_chars cho phép multiplicity khác nhau: thấy `set` không đủ để chọn concept
mất tần suất. Có thể vẫn cần concept normalization nếu contract phân biệt hoa/thường.

Mỗi card nên có thêm một buggy example và một benign example cùng operation,
với source/provenance; ví dụ `max` tie giữ phần tử đầu là benign khi contract yêu
cầu phần tử đầu. Python xác nhận tie behavior trong
[official max documentation](https://docs.python.org/3/library/functions.html#max).
Các examples này là kiến thức generic, không lấy reference/bug labels của target
để nhét vào retrieval index.

## 5. Biểu diễn code khác: facts có source, không chỉ AST-node presence

Đề xuất query theo các local fact records:

- `node_id`, exact span, scope, resolved operation và độ chắc chắn của resolution.
- Input/output value provenance: transform nào cấp giá trị cho decision/return.
- Guards và branch polarity; biết guard có bảo vệ operation ở chính scope đó hay không.
- Semantic effect khi có căn cứ: characters→UTF-8 bytes, occurrences→set membership,
  original text→normalized text, position→first occurrence, fractional value→integer.
- Public-contract clauses riêng, kèm trích dẫn và trạng thái explicit/inferred/unknown.

Ví dụ /16: public requirement đếm distinct characters; observed pipeline là
`string → lower → encode → set → len`. Khác biệt character/byte là quan hệ giữa
các operations và output, nên tốt hơn chỉ thấy có `set` hoặc `encode` ở đâu đó.
Điều này là suy luận từ lỗi cụ thể trong project, không phải performance claim
của GraphCodeBERT.

Ví dụ /66: `if s == '': return 0` bảo vệ `s[0]` trên đường tiếp tục của mỗi lần
invoke. Cần xét branch polarity, type assumptions và value của `s` có đổi không.
Chỉ có dominance edge chưa đủ chứng minh non-empty cho mọi Python object.

## 6. Retrieval nên tách hai bước

1. **Candidate retrieval:** union structural + BM25 trên spec/purpose + BM25 trên
   semantic-effect facts. Có thể thêm code encoder như UniXcoder sau khi baseline
   có ích; không bỏ structural channel bằng một embedding duy nhất.
2. **Bind và kiểm tra candidate pair `(concept, site)`:** chọn source/fact IDs có
   sẵn; kiểm tra required conditions và definite contradictions. Rerank pairs,
   sau đó deduplicate concept khi trả top-3.

Không để model tự tạo source line/where khi đã có node spans. How phải gắn với
facts; what vẫn là hypothesis nếu chưa có correct oracle. Nếu model đề xuất input,
kiểm tra input domain và kết quả thật trước khi chấp nhận claim về PUT. Execution
PUT chỉ xác nhận actual output; **không tự chứng minh expected output đúng**.
Unknown giữ nhãn unknown và có thể trả ít hơn ba supported results.

Chỉ hạ/reject một binding khi có contradiction đã xác nhận. Không hard-filter
cả concept chỉ vì analyzer không hỗ trợ một construct; giữ candidate để bảo toàn
recall. Nếu có bug khác thuộc cùng family thì phải bind lại bằng evidence mới.

## 7. Khác gì những hướng repo đã thử?

- [v36](../../../memory/v36-llm-localize.md): raw code+CFG không tăng localization
  hay inputs. Vì vậy không đề xuất chỉ serialize full graph vào prompt.
- [v47](../../../memory/v47-concept-select.md), [v78](../../../memory/v78-learned-select.md):
  menu/context selectors chưa hơn controls; không có lý do chạy lại LLM chọn card
  từ cùng signals rồi kỳ vọng tăng chất lượng.
- [v50](../../../memory/v50-binding-revision.md), [v63](../../../memory/v63-scopeguard.md):
  tool evidence và native sensitivity không sửa được normative/contract confusion.
- [v65](../../../memory/v65-evidencegate.md), [v66](../../../memory/v66-symbolicpath.md):
  engineering gates/symbolic reach không đồng nghĩa concept true hay oracle đúng.

Hướng đáng thử ở đây hẹp hơn: sửa scope/value provenance/site binding và biểu diễn
explicit applicability để tránh những false claims đã thấy. Chưa có evidence
nó sẽ vượt các negative results trên; không gắn nhãn novelty hoặc efficacy trước.

## 8. Thứ tự diagnostic nếu triển khai bước sau

**P0, source facts và applicability:** dùng các false-claim cases và positive
controls đã lưu để kiểm tra facts giúp phân biệt guarded/unguarded, character/byte,
set membership/counts. Freeze rules trước khi score; báo riêng engineering cases
đã dùng thiết kế. Đo extraction fidelity và unsupported/unknown, chưa cần Qwen.

**P1, representation ablation:** giữ cùng candidate budget/token/calls, so sánh
v2 với structured facts, rồi thêm applicability/benign examples. Thêm embedding
chỉ ở một arm riêng. Giữ original v3 và v4 scores làm context, không tune theo
old audit rồi gọi đó là held-out. Không thay nhiều thứ cùng lúc.

**Quality và utility phải cùng được giữ:** family hit@3; site hit@3; all-returned
actual-bug precision; strict where/how/what; abstention và unknown coverage;
false claims trên benign controls; native confirmed bugs và false alarms. Dùng
arm-masked independent review nếu có; không chỉ same-Qwen judge. Correct reference
và official contracts chỉ ở grading, không đi vào index/query/reranking.

Không chốt hướng chỉ vì recall tăng nhưng card precision giảm như fusion hiện tại.
Gate trước một wider run nên đòi cả precision improvement lẫn không mất observed
recall ở matched coverage; không có claim generalization trên 113 task đã xem.

## Artifacts

- [Diagnostic machine-readable](DIAGNOSTIC.json), [analysis-only script](diagnose.py).
- [Paper sources](SOURCES.json), `papers/<paper>/NOTES.md`.
- [Baseline quality/utility](../../retrieval_v3/RESULTS.md).

Kết quả của lượt này là research/design recommendation và bottleneck diagnosis.
Chưa có retriever mới, benchmark mới, model training hay paper reproduction.
