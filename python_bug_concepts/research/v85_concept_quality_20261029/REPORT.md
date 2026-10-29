# V85: concept quality, cost, and a ConceptCoder-compatible representation

2026-10-29. Phân tích hậu nghiệm trên run đã hoàn tất; không gọi model hoặc chạy
lại target. V2/default, pipeline và source tác giả đều giữ nguyên. Có5candidate
concept definitions ở CANDIDATE_CONCEPTS.json; chưa tích hợp vào runtime.

## 1. Kết quả thực sự cho biết gì

| Chỉ số /113 task | V11 | Retrieval |
|---|---:|---:|
| Primary ref confirmed tasks |77|78|
| Primary ref false-alarm tasks |13|10|
| Input-only bug reach, D_I_samples |84|85|
| Round1 ref confirmed tasks |72|73|
| Task phát hiện thêm sau round2 |5|5|
| Task kích hoạt round2 |60|19|
| Generation calls, gồm round1 và round2 một lần |268|154|
| Generation prompt tokens |231638|148410|
| Generation completion tokens |41636|39158|
| Generation total tokens |273274|187568|

Retrieval giảm42.54%generation calls và31.36%known generation tokens, với primary
outcome gần hòa (10wins/9losses,p1.0). Đây là tradeoff đáng nghiên cứu; chưa phải
bằng chứng concept tốt hơn hoặc equivalence/noninferiority đã được chứng minh.

Round1 dùng113calls mỗi arm, nhưng token retrieval CAO HƠN:128699vs102891.
Round2 giảm155→41calls và170383→58869tokens. Tiết kiệm nằm chủ yếu ở ít kích hoạt
vòng bổ sung, không phải mọi prompt retrieval đều ngắn hơn hoặc rẻ hơn.

Shared preparation dùng480calls/193276tokens; shared refs1130calls/461201tokens.
Nếu quy cùng toàn bộ shared cost cho mỗi pipeline chạy riêng, tổng attributable
cost là1878vs1764calls (-6.07%),927751vs842045tokens (-9.24%). Đây là phép quy
chi phí trên saved receipts, không phải hai standalone runs đã đo độc lập.

Hai generation request có body giống nhau được cache dùng chung giữa hai arm.
Không cộng cả row concept lẫn row concept-hybrid: row cuối đã chứa round1.
Accounting toàn run:2030unique received+13received duplicates+5failed=2048physical
attempts;1118505known tokens và4unknown usages. Trong generation có1failed
unknown của v11 và2của retrieval;shared refs có1unknown503 và1known404failure.
Các phần trăm token phía trên chỉ tính received usage, không phải exact billed
cost khi4attempt còn unknown. COST_AUDIT.json và cost_audit.py đối soát từng key
và tổng usage với RESULTS.json.

## 2. Gate đang đo khác nghĩa với card

Adapter chọn evidence span đầu tiên, lấy bất kỳ v11fact cùng span; nếu không có
thì dùng STMT reachability. Không có kiểm tra rằng fact đó hiện thực hóa semantic
property của card. run_v4 chỉ đưa target có shown_hit_count=0 vào round2.

| Binding trên275card instances | Instances | Gate hit ngay R1 | Gate chưa hit |
|---|---:|---:|---:|
| line_reachability_only |206|204|2|
| existing_v11_gap |69|51|18|

94/113tasks đã hit tất cả retrieval gates sauR1;29/94không có primaryref detection
kể cả ở kết quả cuối. Cả11recursive-base-progress và11aggregation-scope instances
đều là STMT và đều được hit. Một dòng recursion được chạy không chứng minh đã thử
base-case coverage, progress, depth hay repeated-work growth.

**STMT reachability vẫn là một concept control-flow hợp lệ.** Sai lệch nằm ở việc
lấy nó đại diện cho một concept KHÁC, ví dụ membership completeness hoặc recursive
progress. Cùng source line không có nghĩa là cùng semantic obligation. Đó là vấn
đề fidelity của binding/coverage, không phải phủ nhận mọi concept cấp statement.

Thống kê này giải thích trực tiếp điều kiện điều khiển của scheduler, nhưng chưa
ước lượng causal gain nếu thay gate: card wording, chọn targets, inputs và realized
budgets đều khác. Không suy ra29task sẽ được cứu bằng thêmround2.

## 3. Phân loại9paired losses, tránh sửa nhầm

8task thua không có input với saved d_i=True:8,46,63,73,118,119,124,142.
Sáu trong tám task này không kích hoạtR2;73/124đã kích hoạt nhưng vẫn không chạm bug.
Task91 có7bug-revealing inputs, nhưng shared ref emit sai ở cả7: đó là oracle
failure, không thể quy đơn thuần cho thiếu trigger/card. Hai arm dùng chung pool
nhưng hỏi pool trên các input khác nhau, nên lỗi vẫn khác theo arm.

| Case | Evidence đọc được | Cải thiện nên nhắm tới |
|---|---|---|
| /118 get_closest_vowel | Card literal-classification hiện diện, lowercase-only table; R1 không có eligible uppercase-vowel trigger. First-match card nghi ngờ return sớm, nhưng scan phải→trái/first eligible thực hiện đúng rightmost selection. | Bound finite-membership domain + eligibility; benign condition cho scan order khớp required priority. |
| /148 bf (retrieval win) | Card lexical-vs-domain-order phù hợp; companion first-occurrence card nói duplicate positions dù bảng tên planet có các phần tử unique. | Giữ ordering concept; loại/abstain occurrence hypothesis khi có unique-domain evidence. |
| /8,/46,/63 | Naive recursive work; cùng card base/progress/depth, gate chỉ visit recursive line. /63đã progress và base cases hiện diện. | Tách termination/progress, stack depth và repeated subproblem work; hiệu năng cần resource contract, không gọi recursion là bug. |
| /54 same_chars | Đã có normalization card và testcase A/a nhưng predicted expected=True theo PUT; shared ref giúp phát hiện. | Tách observed normalization khỏi required case policy; concept không tự cung cấp oracle đúng. |
| /91 is_bored | Trigger đã có, ref đồng thuận sai trên các bug inputs. | Đánh giá reference oracle độc lập; không ép concept-base giải quyết lỗi pool. |

Đây là purposive post-hoc examples. Các task có thể có nhiều fault, timeout và
spec ambiguity; chưa phải independently annotated error taxonomy hay proof
rằng một sửa card cụ thể sẽ tăng score.

## 4. So với ConceptCoder: đúng một phần, chưa tương đương cơ chế

Primary-source audit: [paper §2.1–2.4/A.4](https://arxiv.org/html/2603.23470v1),
[đối chiếu source chi tiết](../../../research/conceptcoder_20261027/V85_DEFINITION_AUDIT_20261029.md).

ConceptCoder định nghĩa concept là semantic property có discrete/continuous
value, ở giữa raw tokens và final verdict. Có thể là thuộc tính, quan hệ hoặc
behavior. Statement granularity là lựa chọn thực nghiệm; ta được dùng collection,
relation, execution hoặc function-level scope nếu measurement được định nghĩa rõ.

| Thành phần hiện tại | Bản chất | Quan hệ với ConceptCoder |
|---|---|---|
| where/how/what card | Knowledge về một cơ chế có thể gây bug và cách test | Hữu ích để thiết kế vocabulary, chưa tự là instance label |
| STMT/BOUND/OUTCOME fact | Measured control/data-flow property | Có thể là concept hợp lệ nếu đúng property và scope được công bố |
| same-line binding | Heuristic nối card với fact | Không chứng minh semantic equivalence |
| Retrieved prose đưa vào prompt | Inference-time hint | Không tương đương learned concept head/bottleneck |
| ConceptCoder VD/BP | Joint concept-supervised training; VD soft sequential bottleneck, BP auxiliary parallel head | Gain của paper không thể chuyển nguyên sang RAG/test generation |

Do đó không nên đổi định nghĩa để gọi toàn bộ bug-hypothesis card là measured
concept. Nên giữ card như knowledge và tạo concept instance có nghĩa kiểm chứng
được. Cũng không cần ép concept của ta thành pointer/null labels cấp statement.

## 5. Chuyển representation, không chỉ sửa wording

Dùng ba đối tượng riêng:

- **OBS:** concept instance `(property, bindings, scope, value, evidence)`.
  Ví dụ `comparison_order=lexicographic` trên hai string operands ở một comparator.
- **REQ:** relation/policy bắt buộc từ public spec/examples, kèm quote và trạng thái
  `supported/unknown/conflicting`. Không lấy từ canonical hoặc từ cách PUT đang làm.
- **TEST obligation:** input/property cần hiện thực hóa để phân biệt các trường hợp;
  có realization predicate, validity và downstream observation được nêu cụ thể.

Viết hình thức: `c = alpha(P, x, trace)` có miền giá trị được định nghĩa;
`r = rho(public_spec)` là requirement riêng. Hypothesis nối c với r; expected
output và confirmed bug là bước sau. Một concept có thể xuất hiện trong correct
code; concept presence không đồng nghĩa bug. Với property tĩnh không cần x/trace.

Ví dụ `"10" < "2"` là True theo lexical order nhưng False theo numeric order.
Chỉ khi public contract yêu cầu numeric ranking thì inversion này là test
obligation liên quan. Nếu task yêu cầu dictionary order, cùng operation là benign.
Line hit không đo được inversion; scope/operand binding và truth predicate mới đo được.

Năm draft candidates đã soạn ở CANDIDATE_CONCEPTS.json:
`text_normalization`, `multiplicity_projection`, `comparison_order`,
`classifier_membership`, `recursive_work_structure`. Mỗi candidate có domains,
bindings, measured meaning, requirement boundary, distinguishing obligation,
benign case, compact hint và generic fixed-implementation guide. Guide mô tả
nguyên tắc repair, không đưa correct implementation của benchmark vào retrieval.

Đây là equivalence với **vai trò semantic intermediate property trong định nghĩa**,
không phải cùng taxonomy, predictive architecture hoặc causal mechanism với paper.
Unknown/unsupported phải được giữ riêng; không đánh dấu đã cover chỉ vì không đo
được. Semantic mismatch với required behavior cũng chưa đủ nếu chưa chứng minh
propagation tới output và chưa có correct oracle.

## 6. Thứ tự sửa và cách thử tiếp

1. Tách semantic measurement khỏi line reachability trong packet; cấm dùng
   same-line fact làm semantic coverage nếu chưa có adapter đúng nghĩa. Giữ
   line reach như một field riêng, vẫn hữu ích cho localization.
2. Tách broad cards thành named subcases, trước hết classifier completeness,
   selection priority, ordering và repeated recursive work. Không tăng catalog
   hàng loạt; không bỏ harmless concepts chỉ vì chúng cũng có trên correct code.
3. Render compact packet về bound property/contrast và spec evidence cần thiết.
   Full v7 hints đã thất bại; không mặc định thêm prose/precondition giúp Qwen.
4. Validate trên generic positive/benign contrasts: cùng line đều chạy nhưng
   semantic predicate khác nhau; thay tên biến không đổi label; unknown spec
   không sinh required label. State-sharing concept phải unsupported nếu harness
   không giữ state xuyên nhiều calls. Tạm không viết detector cho mọi property.
5. Chỉ sau khi measurement pass mới thử model diagnostic có budget cố định:
   giữ IDs/site, model,2round,10refs và maxcalls; so old-text/old-gate,
   new-text/old-gate,old-text/semantic-gate,new-text/semantic-gate. Thêm một
   budget-matched generic-input control để tách concept signal khỏi thêmcalls.
   Dùng saved refs khi cùng task để giảm chi phí và tránh đổi oracle pool.
   Đây là kế hoạch diagnostic, chưa chạy; không mở thêmfull113để cứu signal yếu.

Primary local prior art: v5 bổ sung scoped binding không tăng74/113sitehits;
v6 cải thiện site metric lên90/113nhưng không chứng minh testgen gain; v7full hints
làm giảm18→13/14bugs trong40task ablation. v47/v78selection gần random;
v50/v63và các evidence-gate variants cho thấy semantic verification khó và có thể
triệt tiêu coverage. Proposal này không mới chỉ vì dùng typed fields: phần cần
kiểm chứng riêng là **đúng semantic coverage của card trong v85**, với unknown
fallback và budget-matched controls. Không claim chưa ai thử concept/gate trước.

## 7. Đã làm và chưa làm

Đã đối soát token/call receipts; phân tích275bindings,113pairs và9losses; đọc
paper/source; soạn5data-only candidates và check4primitive contrast examples.
Chưa sửa engine/default, chưa implement detector hoặc learned concept head,
chưa chạy model/target mới, chưa xác nhận efficacy của candidate pack. Dữ liệu
MECHANISM_AUDIT là development analysis, không được import vào runtime retriever
hoặc dùng làm public-spec evidence. Performance/resource claims cần contract riêng.
