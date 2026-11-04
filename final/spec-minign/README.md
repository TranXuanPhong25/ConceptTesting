# Đọc ba paper về spec/constraint mining — 2026-11-04

Giữ nguyên ba PDF user mới thêm. Mỗi paper có một folder notes riêng; không tạo
pipeline,không mô phỏng paper,không gọi model và không đổi run hiện tại.

## Kết luận

**Có phương pháp mining condition từ tài liệu và có framework suy ra condition
chưa được test,nhưng ba paper không cung cấp cùng một chuỗi tự động đã được
kiểm chứng từ HumanEval spec→missing condition→valid concrete input.**

| Paper | Bước thực sự giải quyết | Phần còn thiếu cho bài toán mình |
|---|---|---|
| [Data constraints/S2F](data-constraints-s2f/NOTES.md) | NL document→candidate constraint fragment+operands+type bằng NLP/ML | Binding vào parameters,executable predicate,semantic validation,gap/input solving |
| [Grounding AI Agents in Contracts](grounding-contract-agents/NOTES.md) | Agent infer semi-formal contracts→Tested/Untested→suggestions→tests | Tested/Untested là agent assessment; study dùng fixedcode+emptytests,khác buggyPUT+base |
| [Formal contracts→tests](formal-contract-test-generation/NOTES.md) | Formal guards→ECP/boundaries→SMT inputs | Giả định đã có formal contract; không mining từ docstring hay tự phát hiện base gap |

Grounding(Sec3.1,p.3)khớp trực tiếp nhất với câu hỏi: agent cross-reference inferred
conditions với assertions/tests và tạo suggestion cho điều kiện Untested. Tuy
nhiên study chính(Sec4.3,p.4)strip tests cũ và sinh test từ fixedsource,rồi mới
reverse-patch về buggycode. Đây là giới hạn quyết định khi áp dụng cho mình.

S2F(Sec4.1,pp.9–10)cung cấp hướng NLP không cần LLM cho extraction. Nó không phải
static analyzer của Python.98.6%là correctness của pattern/operand extraction trên
sample emitted fragments; F1constraint-vs-nonconstraint thực chỉ62.34%. Không được
đổi con số98.6%thành độ đúng của predicate hay input-domain inference.

Formal-contract paper(Algorithm1,pp.4–5)hữu ích khi đã có guard chính xác. SMT tạo
input theo `types ∧ global_precondition ∧ case_guard`,blocking để lấy nghiệm khác.
Study đo validity/passrate/coverage trên8subprograms đã verified,không chứng minh
khả năng phát hiện lỗi. Randombaseline có randomexpectedoutput là điểm hạn chế
lớn nếu dùng passrate để suy ra method advantage.

## Liên hệ với những gì repo đã thử

- B5 của v7/v11 đã mine domain preconditions bằng observation→confirmation→code
  và verify trên base/docstring inputs. Đây không phải semantic entailment proof.
- **v10_spechint** đã mine requirement+quote thành applicability predicateD và
  optional relationR; chọn hint khi không base input nào thỏaD và có fuzz witness.
  Audit lịch sử:157requirements,146đã có baseinput thỏa,7hints/5tasks,không tăng
  good@3. Vì vậy spec→predicate→gap không phải ý mới chưa thử; coarse guards và
  role separation cần được xem lại trước khi chạy một biến thể tương tự.
- v14/v15 sentence splitting/AST guards chỉ grounding trong phạm vi đã nêu;
  không có semantic atomic-decomposition hoặc tool-verified spec entailment.
- v66 có CrossHair constructor; v68 ghép evidence vào model chưa cho conceptgain.
  Có input constructor không tự sửa được upstream spec interpretation.

Phần mới đáng cân nhắc là **constraint có provenance+role rõ,và kiểm chứng gap
bằng evidence thực**,không phải chỉ thêm một lần gọi LLM viết prose contract.
Đây là gợi ý thiết kế,sẽ cần registration và authorization riêng nếu triển khai
paper/reproduction; bước đọc này không thay đổi scientific protocol.

## Cách biểu diễn condition phù hợp hơn với pipeline hiện tại

Mỗi condition nên giữ:

- Exact source quote và vị trí trong spec.
- Role: input-domain precondition,behavior-case guard,postcondition,default hay
  undefined behavior. Không gộp chúng thành một `valid()` predicate.
- Operand binding tới parameter/field và quantifier/scope/strictness.
- Applicability guard và consequence tách riêng.
- Coverage evidence: base input IDs,trace locations hoặc assertions liên quan.
- Trạng thái: covered/uncovered/unknown; infeasible chỉ khi có bằng chứng hợp lệ.

Hai câu hỏi phải ghi riêng:

1. **Có input nào của base tests kích hoạt condition không?**
2. **Tests có assert đúng behavior mà condition yêu cầu không?**

Ví dụ `longest(["ab","cd"])`: nếu spec yêu cầu trả string đầu khi bằng length,
base có input này nhưng chỉ assert `len(result)==2`,thì input tie đã được exercise
mà consequence chọn `"ab"` chưa được kiểm đầy đủ. Đổi nhãn đó thành “chưa có input
tie” là sai. Không tự tạo observable identity requirement ngoài spec.

## Ưu tiên cho bốn nhóm development

| Nhóm | Có thể học từ ba paper | Cần tool bổ sung |
|---|---|---|
| Boundary | Comparison/range operands,formalcase guards,strict/inclusive endpoints | Predicate binding,domain validation,target solver/sampler |
| Equivalence | Allowed sets,boolean states,behavior cases và combinations | Kiểm cells có nghĩa,rời nhau/phủ domain nếu claim partition; base membership |
| Statement C1 | Contract giúp tránh input ngoài miền | CFG+execution coverage và reachability; ba paper không thay bước này |
| Def-use | Pre/postconditions giúp hiểu state và input validity | Reaching definitions,dynamic def-clear trace,alias/heap handling khi cần |

Ưu tiên đọc sâu/applicability cho boundary và equivalence trước. Giữ inputs-only
generator và referenceoracle hiện tại; không lấy model-generated postconditions
làm gold khi benchmark mục tiêu là concept giúp chọn input như thế nào.

## Evidence để đọc lại

- Grounding:pp.2–3condition states và phaseI;p.4fixedsource/greenfield;p.7
  detect@1không significant,detect@5+9.8pp;p.9tokens+38%;ContractCoverage ở
  pp.6–8là bug-specific judge metric với fixdiff,nằm ở evaluation-only.
- S2F:pp.3–6scope/constraints/patterns;p.7Table5;p.9extraction;p.10Table6;
  pp.14–16classifier evaluation;p.19limitations.
- Formalcontracts:pp.3–6method;p.7setup/randomexpectedoutput;pp.9–10coverage;
  p.13data-on-request.

Đã xem public Springer article page và arXiv HTML để tìm artifact. Chưa xác minh
được directauthor-code links cho S2F/Grounding; formal-contract PDF nói data on
request. Chưa clone/chạy code tác giả. Không mặc định một tool được paper mô tả
là một package đã có thể import ngay.
