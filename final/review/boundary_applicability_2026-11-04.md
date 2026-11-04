# Điều kiện áp dụng boundary testing

Research ngày 2026-11-04. Đối chiếu toàn bộ phần boundary trong test_slides,
ISTQB CTFL v4.0.1, Python documentation và paper formal contracts đã có trong repo.
Đây là synthesis và applicability review; không thay generator hoặc chạy experiment.

Update sau research: user đã yêu cầu implement flow type→templates→LLM chọn
boundary/domain→LLM sinh input. Module độc lập theo PUT đã có tại
[BoundaryValueAnalysis](../modular/boundary_value_analysis/README.md), với
41engineering checks và6PUT offline extraction; chưa có live inference/results.
Phần research dưới đây vẫn phân biệt semantic grounding với schema/quote checks.

## Kết luận

**Điều kiện cốt lõi là xác định được boundary có ý nghĩa và tạo được input
chạm/sát boundary đó mà vẫn thỏa các constraint liên quan.** Để kết luận test
pass/fail, cần thêm oracle.

Cần tách ba mức: nhận diện boundary; tạo concrete input; đánh giá output.
BVA là input selection technique, không tự cung cấp oracle hoặc bảo đảm tìm bug.

| Điều kiện | Kết luận áp dụng |
|---|---|
| Test basis | Spec/contract đủ rõ cho domain hoặc rule đang xét, gồm `<` hay `<=`; constant trong PUT chỉ là candidate |
| Meaningful order | Characteristic có order liên quan đến behavior, như numeric value, date, length, count; category chỉ có tên không tự có boundary |
| Boundary và neighborhood | Xác định threshold và bước sát boundary theo domain/resolution; không dùng một epsilon cho mọi bài toán |
| Feasibility | Tạo được concrete input thỏa type, preconditions và joint constraints; có threshold chưa đồng nghĩa có executable test |
| Oracle | Cần để đánh giá pass/fail; không phải prerequisite riêng của bước chọn input bằng BVA |

Các kết luận cần giữ khi áp dụng:

- **Independence không phải điều kiện bắt buộc của mọi boundary testing.**
  Independence và single-fault assumption hỗ trợ biến thể thay từng biến với
  `4n+1` tests trong slide. Khi parameters phụ thuộc nhau, phải xét joint constraints.
- **Domain boundary và behavior boundary khác nhau.** Cover min/max của từng
  parameter chưa chắc chạm threshold của expression kết hợp nhiều parameters.
  Ví dụ tổng điểm `t+l+h=28` được phân tích bên dưới.
- **Không cần finite min/max cho toàn bộ domain.** Có thể test lower boundary
  hoặc internal threshold; generation cap không tự trở thành semantic boundary.
- **Invalid input cần expected handling để kết luận correctness.** Failure trên
  input bị contract loại không tự chứng minh PUT có bug.
- **Boundary-ready hiện tại chỉ là development eligibility.** Manual label và
  base-pass chưa verify boundary, feasible witness hoặc base coverage gap.
- **Base chưa cover là tiêu chí chọn target mới của pipeline**, không phải điều
  kiện áp dụng BVA nói chung. Input coverage, assertion adequacy và bug detection
  là các loại evidence khác nhau.

Các kết luận này tổng hợp từ slide pp.5–17, ISTQB §4.2.2 và việc đọc code hiện
tại; phần dưới ghi rõ nguồn, ví dụ và giới hạn của từng kết luận.

## Evidence từ test_slides

Nguồn: [03. Kiem thu chuc nang.pdf](../../test_slides/03.%20Kiem%20thu%20chuc%20nang.pdf),
số trang PDF tính từ 1.

| Trang | Nội dung trong slide | Ý nghĩa khi áp dụng |
|---|---|---|
| 3, 5–6 | Functional testing dựa vào requirements; ví dụ domain a≤x1≤b, c≤x2≤d | Cần test basis để biết domain/boundary dự định |
| 7–8 | min, min+, nom, max-, max; ví dụ month 1..12 | Cần endpoints, neighborhood và nominal value của biến thể này |
| 9–11 | Single-fault assumption, thay từng biến, giữ các biến còn lại nominal; 4n+1 | Chiến lược tiết kiệm test, không bảo đảm cover interaction |
| 12 | Enum có thể dùng; boolean không có đủ neighbor/nominal | Numeric type không bắt buộc; không ép mọi input vào bộ 5 giá trị |
| 13 | Thêm min-, max+; 6n+1; kiểm tra input validation | Robust variant cần expected handling của invalid input để kết luận correctness |
| 14 | Cartesian product 5^n; mở rộng bộ 7 giá trị | Có biến thể kiểm tra nhiều biến đồng thời |
| 16 | Điểm t,l,h trong [0,10], pass khi tổng≥28 | Có cả parameter-domain boundary và relational behavior boundary |
| 17 | Biến độc lập thuận lợi; biến có ràng buộc dễ tạo test không hợp lý | Phải xét joint constraints; slide không chứng minh BVA bất khả thi khi phụ thuộc |

Trang 13 ghi nhầm bằng lời “dưới giá trị cực đại (min-)”; ký hiệu min- phải được
hiểu là dưới minimum. Giữ nguyên slide gốc.

Đã search text các PDF còn lại: các occurrence “Boundary condition” trong
`program analysis.pdf` nói về điều kiện tại entry/exit của data-flow analysis,
không phải Boundary Value Analysis.

## Điều kiện và phạm vi

1. **Test basis đủ rõ cho boundary đang xét.** Biết domain, kiểu, guard và
   inclusive/exclusive endpoint. Không nhất thiết có complete formal spec của
   toàn chương trình. Boundary lấy từ PUT chỉ là implementation candidate;
   không tự chứng minh đó là yêu cầu đúng của spec.
2. **Characteristic có order có ý nghĩa.** Có thể là integer, date, length,
   count hoặc derived quantity. ISTQB §4.2.2 yêu cầu ordered partitions và
   các phần tử nằm giữa hai phần tử cùng partition cũng thuộc partition đó.
   Hai lớp odd/even không phải hai interval dưới numeric order; không áp dụng
   min/max BVA máy móc. Enum có order miền ứng dụng thì khác enum chỉ là labels.
3. **Boundary và neighborhood xác định được.** Phân biệt x<k và x≤k; chọn bước
   theo domain: integer thường 1, decimal theo resolution của spec. Real numbers
   toán học không có immediate successor. Float có adjacent representable values,
   có thể dùng `math.nextafter`; với derived expression phải kiểm tra giá trị thực
   sau rounding, không mặc định đổi một operand là đã vượt boundary.
4. **Concrete input khả thi cho từng obligation.** Giữ type/global preconditions
   và các constraint giữa parameters. Một side infeasible không thể được gọi là
   covered; solver timeout/không tìm thấy witness chưa phải bằng chứng infeasible.
   Với internal boundary cần thêm reachability tới đúng site; không cần site trace
   nếu chỉ claim input-domain boundary coverage.
5. **Oracle khi cần verdict.** Expected value, reference implementation hoặc
   property đủ mạnh. Đây là điều kiện của việc đánh giá test, không phải điều kiện
   riêng để dùng BVA chọn input. Robustness probe vẫn có thể chạy khi handling chưa
   rõ, nhưng không được tự suy ra spec violation từ input bị contract loại.

Không cần mọi parameter đều có finite min/max. Ví dụ positive integer có lower
boundary nhưng không có semantic maximum; không tự lấy generation cap 30 hay
32-bit max làm upper boundary cho Python int. List/string có thể test length
boundary khi domain/rule hỗ trợ. Một boolean có hai cases để enumerate, không
cần bịa nominal value.

ISTQB nói về 2-value/3-value coverage quanh partition boundaries; slide dạy bộ
5-value theo parameter domain. Hai cách chọn coverage items này không đồng nhất.
Chỉ claim coverage khi đã nói rõ variant và tập obligations.

Các count 4n+1, 6n+1, 5^n, 7^n giả định mỗi biến có đủ các giá trị phân biệt và
các tổ hợp cần xét khả thi. Domain nhỏ, duplicate hoặc constraint làm count thay
đổi. Single-fault assumption không có nghĩa chương trình chỉ có đúng một bug.

## Có thể define loại input trước, hay phải suy từ spec?

**Có thể define trước các boundary families và template chọn giá trị. Spec/contract
cung cấp binding, valid domain và semantic threshold cụ thể của từng task.**
Không cần suy lại toàn bộ phương pháp từ đầu cho mỗi task; cũng không thể chỉ
nhìn type rồi xác nhận mọi boundary candidate đều phù hợp.

Đơn vị phân loại nên là **characteristic của input**, không chỉ raw type:
một list có thể có length boundary, element-value boundary và aggregate boundary.
Bảng sau là taxonomy thực dụng tổng hợp cho repo, không phải taxonomy nguyên văn
của ISTQB. Các nhóm có thể overlap.

| Family / input thường gặp | Có thể define trước | Cần xác định từ spec/contract |
|---|---|---|
| Ordered discrete scalar: integer, count | Neighbors quanh k, thường k-1/k/k+1 khi cả ba thuộc value grid | k là endpoint hay behavior threshold nào; strictness; valid range và bước hợp lệ |
| Float / decimal measurement | Các điểm dưới/tại/trên k theo resolution hoặc representable neighbors | Threshold, precision, unit, rounding, finite-only hay cho phép special values |
| Date / time / duration | Neighbors trước/tại/sau endpoint theo đơn vị thời gian | Range, granularity, calendar/timezone rules và cutoff |
| String / list / array / set / map | Chọn theo length/cardinality, ví dụ 0/1 hoặc k-1/k/k+1 | Có cho empty không; min/max length; constraints trên content và quan hệ giữa collections |
| Position / index / window | First/last position và vị trí sát endpoint; boundary phụ thuộc n | Zero/one-based, inclusive/exclusive, index validity, n tối thiểu; n=0 không có valid element index |
| Ordered enum / level | First/last hoặc predecessor/successor theo declared semantic order | Order có thực sự thuộc domain/rule không; underlying integer encoding không đủ |
| Relational / aggregate characteristic | Nhắm g(inputs)=k, hoặc f(inputs)-h(inputs)=0; hai phía trong valid domain | Expression, guard, threshold, joint constraints và feasible witnesses |
| Boolean / unordered category | Enumerate hoặc equivalence partitioning | Không ép vào template 5-value BVA; nếu có ordered derived characteristic thì xét riêng characteristic đó |

Relational family là mở rộng cách nhắm boundary trên characteristic được suy ra,
không mặc định Cartesian input domain là một interval. Chỉ chuyển thành scalar
boundary khi expression/order mô tả đúng rule; giữ các contextual guards và
constraints khác. Một boolean result của predicate không tự tạo ra ordered input
boundary cho predicate đó.

### Type biết được gì, chưa biết được gì?

- `n: int`: biết có numeric order và cách tạo integer neighbors. Chưa biết n có
  phải positive, có giới hạn 100 hay đổi behavior tại 10 không. Zero là giá trị
  đáng thử nhưng chưa tự thành semantic boundary của task.
- `xs: list[int]`: biết length không âm và empty list biểu diễn được. Chưa biết
  function có nhận empty, yêu cầu sorted/nonempty hoặc cần ít nhất hai elements.
- `xs` với contract “at least two elements”: length=2 là lower valid boundary;
  length=3 là neighbor phía trong. Length=1 chỉ dùng để đánh giá invalid handling
  nếu behavior đó được định nghĩa. Không tự lấy 0/1 làm valid tests.
- `xs, limit` với rule `sum(xs) <= limit`: boundary là quan hệ giữa aggregate và
  limit. Chỉ biết cả hai numeric không đủ suy ra expression này.

Nguồn không bắt buộc là natural-language spec: structured schema, refined type,
formal contract, API/protocol definition hoặc platform type contract có thể đã
cung cấp range/order/constraint. Ví dụ fixed-width integer có representation
limits; Python `int` không có fixed 32-bit maximum. Phân biệt representation
boundary với behavior boundary của chức năng.

Code của PUT giúp lấy implementation candidates nhưng có thể chứa chính threshold
sai hoặc thiếu rule. Base tests cho evidence tại các input đã có, không xác định
đầy đủ domain chỉ bằng observed min/max. Cả hai không tự thay normative contract.

### Cách dùng trong pipeline

Ở bước 1, **type/structure là kiểu và cấu trúc của input mà PUT nhận**, không phải
control-flow structure hay toàn bộ nội dung body PUT. Ví dụ scalar integer,
list of integers, tuple, record có fields; chúng xác định template nào có thể
đề xuất. `list[int]` gợi ý length và element-value candidates, nhưng chưa xác
nhận empty hợp lệ, list phải sorted hay threshold cụ thể nào.

Nguồn ưu tiên là task interface/schema và type declarations trong spec/contract.
Type annotations ở signature PUT là evidence bổ sung, có thể thiếu hoặc sai.
Base inputs cho biết concrete types/shapes đã quan sát; không được suy ra toàn
bộ allowed types, min/max length hoặc domain từ sample đó. Thiếu type evidence
thì giữ unknown hoặc candidate có điều kiện, không tự xác nhận applicability.

Body PUT được đọc ở một bước bổ sung để lấy **implementation candidates**:
`len(xs) < 2` gợi ý length threshold 2, `sum(xs) <= limit` gợi ý aggregate boundary,
`xs[i]` gợi ý index/length relation. Những expression này cần đối chiếu contract
và reachability khi thích hợp. PUT có thể sai threshold hoặc thiếu hẳn rule,
nên chỉ mining body sẽ vừa có candidate sai vừa có thể bỏ sót boundary cần test.
Nếu contract đã nêu aggregate/relational rule thì vẫn tạo candidate dù PUT không
implement expression tương ứng.

1. **Input type/schema → candidate families:** xác định kiểu và cấu trúc input
   có characteristic nào thuộc phạm vi hỗ trợ của boundary provider; có thể bổ
   sung implementation candidates từ body PUT nhưng giữ provenance riêng.
2. **Spec/contract → grounded obligations:** bind characteristic, threshold,
   strictness, domain và provenance; unknown khi chưa đủ evidence.
3. **Construction → feasible witnesses:** instantiate template theo joint
   constraints, kiểm tra input có thực sự đạt target; unavailable khác infeasible.
4. **Coverage/oracle → đánh giá:** kiểm base coverage và output theo mục tiêu run.

Vì thế nên giữ riêng `candidate`, `grounded` và `witnessed` khi đánh giá concept;
coverage/verdict là evidence tiếp theo. Có type được hỗ trợ chỉ chứng minh có thể
đề xuất template, chưa chứng minh task đã có usable boundary test. Đây là đề xuất
biểu diễn evidence, chưa được implement trong generator hiện tại.

## Ví dụ phân biệt domain boundary và behavior boundary

Ví dụ gốc trang 16 có D: 0≤t,l,h≤10 và rule t+l+h≥28.

- Domain boundaries của mỗi điểm: 0 và 10.
- Behavior boundary: t+l+h=28, nằm trong valid domain.
- Giữ l=h=5 rồi sweep t từ 0 đến 10 chỉ cho tổng 10..20; không chạm rule 28.
- Giữ l=h=9.5, chọn t=8.5, 9, 9.5: tổng 27.5, 28, 28.5; expected fail/pass/pass.
  Đây là minh họa tự suy ra từ rule slide, không phải test đã thực thi và không
  claim ba điểm là nearest neighbors hay đạt full 3-value BVA coverage.

Vì vậy parameter domains độc lập cũng không bảo đảm absence of behavioral
interaction. Muốn nhắm threshold cần xét expression chung, không chỉ từng range.

## Liên hệ với pipeline hiện tại

`final/development_groups.py`, trong `DevelopmentGroups.build`, đặt
`fit[boundary] = True` cho PUT pass base khi task đã có manual boundary label.
Nó chưa chứng minh provenance, exact endpoint, feasibility, witness hoặc base-gap
của từng boundary. “44 ready primary tasks” là development eligibility, không phải
44 task đã có toàn bộ boundary obligations được verify.

Checklist đề xuất để review một boundary concept trước khi sinh input:

Chuỗi evidence cần lưu trong pipeline:
**spec/rule → boundary rõ → constraints → valid witness → base coverage → oracle verdict**.
Đây là chuỗi kiểm tra evidence, không bắt buộc thứ tự thực thi: có thể phân tích
base coverage trước khi sinh witness mới, và oracle chỉ cần khi chấm correctness.

| Field | Evidence cần giữ |
|---|---|
| source / role | Spec quote hoặc implementation site; domain bound hay behavior guard |
| characteristic | Parameter/derived expression, type, order, parameter binding |
| boundary | Threshold, strictness, partition/side đang nhắm |
| neighborhood | Resolution hoặc adjacent representable value, variant áp dụng |
| constraints | Global domain và các quan hệ phụ thuộc |
| feasibility | Concrete witness; nếu chưa có thì unknown, không tự nhận infeasible |
| base evidence | Input IDs có chạm đúng boundary/neighbor; trace nếu nhắm internal site |
| oracle | Reference/property và phạm vi defined behavior |

Đây là synthesis cho việc review, không phải checklist được chép nguyên từ nguồn.
“Base chưa cover boundary” là điều kiện chọn **new coverage target** của pipeline,
không phải prerequisite của BVA nói chung. Base đã cover boundary vẫn có thể cần
test combinations khác. Input coverage và assertion adequacy phải ghi riêng.

Paper formal-contract bên dưới cho thấy cách tạo input khi formal constraints
đã sẵn có. Nó không giải quyết độ đúng của việc suy constraints từ HumanEval
docstring. Reference oracle giúp đánh giá output nhưng không tự chứng minh input
nằm trong intended domain hay boundary đã được xác định đúng.

## Nguồn đối chiếu

- **ISTQB CTFL v4.0.1**, §4.1–4.2.2, PDF pp.39–40:
  [Official syllabus](https://istqb.org/?download_id=3345&sdm_process_download=1).
  Đã đọc trực tiếp phần EP/BVA. Dùng để xác nhận ordered partitions, interval
  property và 2-/3-value coverage; các quy tắc vận hành ở trên là synthesis.
- **Python math documentation**, `math.nextafter`:
  [Official reference](https://docs.python.org/3/library/math.html#math.nextafter).
  Dùng cho adjacent floating-point values; không suy ra một epsilon chung.
- **Jiménez Gil et al., Automatic test cases generation from formal contracts**,
  Information and Software Technology 172 (2024), 107467,
  [DOI](https://doi.org/10.1016/j.infsof.2024.107467).
  Đã đọc lại PDF local pp.3–5, Algorithm 1: types + global preconditions + local
  case guard; outputs checked by associated postconditions. Xem
  [paper notes](../spec-minign/formal-contract-test-generation/NOTES.md).
  Không dùng study này để claim BVA tìm được bug trên HumanEval.
- [Development-group policy](development_groups/README.md) và
  [builder](../development_groups.py): phân biệt semantic boundary với sampling
  cap, input validity và mức độ evidence hiện tại.

Đã tìm được companion page của Ammann–Offutt, nhưng PPTX không tải được qua
web tool (unsupported content type) và HTTP client (403); không dùng nội dung
slide chưa đọc làm evidence. Không sửa source paper/vendor, không gọi model,
không chạy PUT, không commit/push trong research này.
