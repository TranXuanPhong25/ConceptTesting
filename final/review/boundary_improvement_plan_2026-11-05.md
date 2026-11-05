# BVA: mechanism audit và đề xuất cải thiện

Update:user authorized implementation. Main repairs are now implemented in the
existing code and165checks pass. No new generation/benchmark run. See
[implementation report](boundary_repair_2026-11-05.md). Proposal/history below
describes the observed failures and design,not a new measured efficacy result.

Scope: audit generation đã lưu của boundary/all44,đối chiếu code và chấm lại
đúng inputs bằng corrected HumanEval+ references. Không gọi model thêm,không
implement thuật toán BVA mới,không mở rộng dataset để tìm gain.

## Trạng thái oracle đã sửa

User đã đồng ý đổi oracle. Rescore44/44complete bằng HumanEval+v0.1.10:
plain595validinputs/0detectedPUTs;BVA121/0.0newmodelcalls. Original freeze giữ
nguyên và1,336original artifact files không đổi byte. Corrected full-summary
read-only replay khớp;118source/datahashes verified. Modern pipeline hiện mặc
định corrected references;original-task references được chọn rõ cho legacy/tests.

Các raw3vs3detections trước đó đều biến mất dưới corrected references. Không
dùng chúng làm bằng chứng BVA tìm được bug. Sửa oracle là điều kiện cần của việc
đo bugfinding;không tự sửa được applicability/binding/construction của BVA.

## Evidence từ generation44task

| Bước | Quan sát |
|---|---|
| Selection |49boundary proposals được schema accept;chưa phải49semantically correct concepts |
| Vai trò được model gắn |41domainbounds,8behaviorboundaries |
| Abstention |17no_boundary,1invalid_selection |
| Construction |26calls,trả473input records |
| Giữ lại |121records,25.6%;21task có input |
| Target misses |272boundary_not_hit |
| Format/literal |41invalid_input_record:20syntax errors,21nonliteral expressions |
| Metadata/duplicate |21undeclared_side,18duplicate_input |
| Không giữ được input |5task no_inputs |

Machine-readable:[mechanism audit](boundary_mechanism_audit_2026-11-05.json).
Không quy toàn bộ17abstentions thành lỗi;some characteristics cần operators mà
V1chưa hỗ trợ. Những ví dụ rõ dưới đây đủ cho mechanism decision trước run mới.

## Ba nguyên nhân chính

### 1. LLM đang phải làm công việc cơ học dễ sai

Task0chọn threshold0,float_adjacent,above. Target thực là5e-324nhưng cả20records
không chạm target. Task81sinh literals chứa arithmetic như`3.7 + 5e-18`;ngoài việc
không phải literal,biểu thức này còn có thể round về3.7,chưa thật sự vượt boundary.
Task115cả20records lỗi syntax;task120/122dùng list multiplication trong literal.

Đó là mất input trước khi thử behavior. Nới target validator hoặc eval model code
sẽ che lỗi;phải sửa cách instantiate/serialize inputs.

### 2. Quote/schema đúng chưa đồng nghĩa characteristic và role đúng

- Task140:prose nói consecutive-space count,nhưng selected expression làlen(text).
  Chỉ các all-space strings mới làm hai đại lượng bằng nhau;18contextual records
  bị target validator loại. Cần run-length characteristic đúng.
- Task138:model gọi8là domain lower bound,nhưng spec có input4và6với outputFalse.
  Đây là behavior threshold;input dưới8vẫn hợp lệ. Sai role làm mất phía cần test.
- Task21:quote/max>min bị bind thành element-versus-sum boundary. Một vector có
  element bằng sum không chứng minh minimum và maximum đang sát nhau.

49proposals chỉ qua structural validation và quote presence;chưa có con số
semantic precision đáng tin. Đếm proposals không thay việc kiểm binding này.

### 3. Model đang abstain cả các boundary có thể biểu diễn

- Task30:reason tự nhắc`x > 0`rồi kết luận không có numeric threshold;0là threshold.
- Task52:`all elements < t`có relational threshold t.V1đã hỗ trợ threshold lấy từ
  parameter khác;không cần constant finite min/max để test equality/two sides.
- Task146:spec nói`greater than 10`,vẫn bị no_boundary. Element-value candidate
  đang có đủ khả năng biểu diễn threshold10.
- Task99:là numeric text rounding nhưng type step chỉ cung cấp stringlength;
  đây là unsupported characteristic,khác với chứng minh không có boundary.

## Đề xuất kiến trúc

Giữ concept selection làm quyết định semantic của LLM. Chuyển việc tính target,
instantiate supported shapes và đóng gói call cho code:

```text
Types / templates + public spec / domain
  → LLM chọn characteristic, predicate, role, constraints
  → Binding validation / unsupported-or-unknown
  → Code compile các target và allowed sides
  → LLM bổ sung context cho những targets cần context
  → Code instantiate + encode args/kwargs
  → Domain + actual-characteristic checks
  → INPUTS ONLY → freeze → corrected reference
```

Không đưa reference source/outputs hoặc PUT verdicts vào generator. Pure trusted
domain checks có thể dùng trước freeze vì contract đã được public cho hai arms;
đó không phải query expected output. Semantic entailment từ prose vẫn phải được
đánh dấu là hypothesis/unknown nếu chưa có evidence đủ mạnh.

## Thứ tự ưu tiên

| Ưu tiên | Thay đổi | Evidence và giới hạn |
|---|---|---|
|P1|Shared CallBuilder cho plain và BVA:LLM trả parameter→value có cấu trúc,code bind signature và tạo tuple/kwargs|Sửa singleton comma,nested list syntax và arity;áp dụng cùng hai arms để tránh format advantage |
|P1|TargetCompiler tính integer neighbors và math.nextafter;code tạo literal round-trip|Nhắm272target misses;không bắt LLM đoán decimal của adjacent floats |
|P2|Typed characteristic operators và binding validation;domain precondition tách behavior guard|Sửa140/138/21;ưu tiên operator có case thực,không thêm taxonomy lớn cho đủ |
|P2|Phân biệt no_applicable_boundary,unsupported_characteristic,uncertain_binding,already_covered_input|Không gộp17abstentions vào một lý do;mở lại30/52/146bằng đúng grammar đã có |
|P3|Budget theo obligations/contexts,không cố lấp20records;phát hiện exact base duplicates trước construction|Scalar một parameter có thể chỉ có1–3target calls,nhiều target đã là base;đừng sinh20interior values rồi reject |

### TargetCompiler làm được gì trước?

- Numeric scalar:code assign target trực tiếp vào selected parameter.
- Length:materialize collection có exact length,dùng Hypothesis/standard library
  cho phần content khi constraints được hỗ trợ;không yêu cầu LLM viết hàng nghìn
  elements hoặc expressions như`[0] * 999`trong literal string.
- Element values:code cấy exact target vào selected element,validate joint domain.
- Run length:prefix + exact run + suffix,với constructor/validator cùng operator.

Mỗi operator cần cả evaluator và input constructor. Có evaluator không có nghĩa
đã solve được inverse construction. Derived expressions như pair distance/range
có thể bị cancellation/rounding;phải verify actual value và báo construction_unknown
nếu không tạo được witness. Không tuyên bố một solver/library giải được toàn bộ
spec mining/binding/input realization. Chỉ cân nhắc SMT cho supported joint
constraints mà constructors đơn giản không giải được.

### Binding biểu diễn rõ hơn

Ví dụ task140:

```json
{
  "characteristic": {"operator": "consecutive_run_length", "parameter": "text", "token": " "},
  "role": "behavior",
  "guard": {"comparison": ">", "threshold": 2},
  "domain": {"type": "str"},
  "targets": [1, 2, 3]
}
```

Code phải kiểm run thực tế,không thay bằnglen(text).Task138tương tự:domain nhận
integer,guard có threshold8và parity;không biến guard thànhvalid(n>=8).
Quote vẫn là provenance,không phải proof rằng operator/quantifier đã được bind đúng.

## Kiểm chứng trước lần model run mới

1. Replay saved raw records qua proposed encoder và báo phần sửa được/không sửa
  được dưới dạng offline diagnostic,không sửa kết quả chính của run đã frozen.
2. Unit/CPU checks cho targets0/81(float),140(runlength),138(role),30/52/146
  (applicability),21(relational binding),115(nested shape). Dùng known inputs/
  requirements để kiểm cơ chế;không tune theo hidden plus tests.
3. Báo riêng semantic binding correctness,feasible targets,domain validity,target
  hit rate,new-input yield,base duplicates và call/token cost. Quote/target hit
  không tự trở thành semantic correctness hoặc bugfinding gain.
4. Nếu implementation sửa được các failure classes thì mới khóa protocol/model
  để so với plain có cùng encoder và appropriate budget controls. Không đề xuất
  mở rộng dataset/chạy thêmKchỉ để cứu raw detection count.

Already exercised input≠assertion adequate. Với một scalar duy nhất,exact call đã
ở base thì không cần generate lại;với length/aggregate feature,base có một input
hit feature không cover mọi combination/context. Không skip hết một obligation
chỉ vì có bất kỳ base input nào cùng length/value.

## Đối chiếu lịch sử trong repo

- V7/V11đã có BOUND/shape và tool-generated witnesses;không gọi việc thêm BVA card
  là novelty. Current change cần sửa cụ thể binding và realization.
- V44generic boundary/class pools không hơn matched random (union21vs21.36);
  tăng số templates/input pool không tự là cải thiện scientific.
- VR14/VR15typed slots/binding có source-only gains nhưng chưa chứng minh testgen
  efficacy. Proposal này thêm supported evaluator/constructor và measured failures,
  không claim typed JSON tự mang lại semantic understanding.
- V66CrossHair construction PASS5/6nhưng V68concept=plain1/6;constructor readiness
  không tự chứng minh concept benefit. Giữ selection correctness và oracle tách ra.

Đề xuất này là sửa engineering/mechanism hiện tại,không phải paper mới hoặc một
run đã được launch. Chưa implement các P1/P2/P3trong module BVA.
