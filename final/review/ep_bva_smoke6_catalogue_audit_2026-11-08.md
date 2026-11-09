# Audit catalogue EP+BVA smoke6 — launch 08/11/2026 UTC

**Catalogue chưa đủ để xác nhận arm thực hiện weak EP + normal BVA đúng spec.**
Chỉ 2/6 catalogue qua schema; cả hai còn thiếu nominal và không có class membership
máy kiểm được. Đây là giới hạn interface/measurement và chất lượng khai báo của
model, không phải kết luận EP/BVA không hiệu quả. Kết quả detection đã hoàn tất:
Plain và EP+BVA cùng phát hiện 1/6 eligible PUT, cùng PUT task99; không có
EP+BVA-only win trên smoke này. Không suy rộng từ 6 task.

Run: [Prefect a143aa28](http://127.0.0.1:4200/runs/flow-run/a143aa28-f017-4ab8-a536-09f7816e3149).
Source artifacts: `final/out/console_a143aa28-f017-4ab8-a536-09f7816e3149/run`.
Launch date UTC là 08/11; audit hoàn tất khi local date đã sang 09/11/2026.
Audit chỉ đọc saved artifacts sau global freeze, không gọi model/native workload,
không sửa frozen source/input/result. Đã đọc 6 catalogue và 120 input records của
EP+BVA; semantic review dưới đây là định tính, chưa chấm precision cho mọi label.

## Scope, budget và yield

6 task, mỗi task 1 representative PUT; Plain/EP+BVA mỗi arm 20 inputs/task,
1 completion/task/arm, completion cap4096 tokens/call và context8192. Có12/12
received completions,0unknown;28,321 known tokens (12,430 prompt +15,891 completion).
EP+BVA dùng18,609 total tokens, Plain9,712 total tokens. Reference/scorer/freeze và
immutable replay dùng chung; replay/source checks PASS theo result digest.

| Task | EP+BVA input records trước oracle | Novel valid inputs sau oracle/base dedup | Catalogue status | Số schema diagnostics |
|---|---:|---:|---|---:|
| 0 | 20 | 20 | applicable | 0 |
| 5 | 20 | 18 | catalogue_invalid | 4 |
| 18 | 20 | 20 | catalogue_invalid | 3 |
| 81 | 20 | 19 | catalogue_invalid | 12 |
| 99 | 20 | 12 | catalogue_invalid | 35 |
| 120 | 20 | 20 | applicable | 0 |
| Tổng | 120 | 109 | 2/6 schema-valid | 54 |

Cả6 EP+BVA responses có `finish_reason=stop`, không truncation; decoder giữ đủ
120/120 input records dù catalogue sai. Plain có118 novel valid inputs/120records.
Do đó schema rejection của catalogue không trực tiếp làm mất test inputs. Domain
rejection/base duplicate là accounting riêng, không nhập chung với catalogue lỗi.

## Interface diagnostics đã quan sát

- Task5: `schema:boundaries.0.lower_inclusive:extra_forbidden`,
  `schema:boundaries.0.upper_inclusive:extra_forbidden`,
  `schema:boundaries.1.lower_inclusive:extra_forbidden`,
  `schema:boundaries.1.upper_inclusive:extra_forbidden`.
- Task81: cùng hai suffix `lower_inclusive:extra_forbidden` và
  `upper_inclusive:extra_forbidden` tại mỗi `boundaries.0` đến `boundaries.5`:
  tổng12 diagnostics. Model dùng fields có ý nghĩa cho interval nhưng schema
  hiện chỉ cho chúng ở classes, không cho boundary. Đây là contract mismatch,
  không đủ để kết luận các input GPA được chọn sai.
- Task18: `schema:boundaries.0.context:dict_type`,
  `schema:boundaries.1.context:dict_type`,
  `schema:boundaries.2.context:dict_type`. Model ghi prose như
  `"substring length = 2"`, trong khi schema yêu cầu mapping named arguments.
- Task99: tại mỗi `boundaries.i`, i=0..6, có đúng5 diagnostics:
  `schema:boundaries.i.lower.int:int_type`,
  `schema:boundaries.i.lower.float:float_type`,
  `schema:boundaries.i.upper.int:int_type`,
  `schema:boundaries.i.upper.float:float_type`,
  `schema:boundaries.i.context:dict_type`. Ví dụ lower/upper `"14.5"` là string và
  context `"round up"` là prose; schema đòi numeric endpoints và context dict.

Không normalize hoặc re-measure những catalogue này trong audit. Input arguments
của task99 cần giữ dạng string theo function interface; endpoint catalogue numeric
và input argument string là hai khái niệm khác nhau. Schema error không tự phủ định
ý tưởng kiểm quanh half-integer.

## Semantic/selector findings theo task

- **Task0:** spec chỉ yêu cầu threshold>0 trong contract, không đặt max1 hoặc
  max list length2. Catalogue B1 khai length[0,2], B2 khai threshold[0,1], trong
  khi inputs có length3 và threshold khác các mốc đã khai. Các số này không phải
  domain boundaries được spec xác nhận; threshold0 còn ngoài contract. B3 khai
  `parameter=numbers, transform=parsed_float` để đo pairwise difference, nhưng
  selector này không thể parse cả list thành scalar difference. Classes không
  có `partition`/`parameter`; `members=["L1"]`... là nhãn tượng trưng, không phải
  các input members. Input `[1.0,1.9,2.8], threshold=0.91` gắn C3
  "difference>=threshold" dù có adjacent differences nhỏ hơn threshold. Catalogue
  schema-valid nhưng chưa semantic-valid.
- **Task5:** phân nhóm empty/singleton/multi-element và delimiter trùng/khác là
  các ý tưởng test phù hợp. Tuy nhiên class `members` chứa một ví dụ cụ thể như
  `[5]` rồi `covers=C2` được gắn cho `[10]`: model đang dùng `members` như
  representative, còn checker hiểu là enumeration membership. Boundary upper
  length29..31 và element±100 không được spec/contract đặt ra; prompt nói
  "normally<=30" là resource hint, không biến30 thành semantic upper bound.
  `parsed_int` cho toàn list cũng không đo element value.
- **Task18:** các lớp overlap/no-match/location là các ý tưởng liên quan spec,
  nhưng có label sai: `('testtest','test')` gắn "start only" dù có match cuối;
  `('testtest','estt')` gắn "end only" dù match ở giữa;
  `('zzz','z')` gắn class "Single char string" dù string length3.
  Đây là semantic self-report errors, khác với prose-context schema mismatch.
- **Task81:** nhiều inputs tập trung vào các cutoff GPA trong spec, là ý tưởng
  BVA liên quan. Nhưng class C4 gộp nhiều exact thresholds dẫn tới các letter
  grades khác nhau, chưa thay thế output partition đầy đủ; step0.01 không có
  precision contract hỗ trợ. `parameter=grades, transform=identity` chọn nguyên
  list, còn members/endpoints là scalar GPA; `parsed_int` cho list cũng không
  hợp selector. Không có metadata để chứng minh single-fault hoặc partition.
- **Task99:** positive/negative integer, fraction<0.5/>0.5/=0.5 phù hợp quy tắc
  rounding; nhiều input half-integer hữu ích vẫn được giữ. Nhưng model thêm5/20
  inputs ngoài domain (`abc`, empty string, `nan`, `inf`, `-inf`) dù spec/contract
  không định nghĩa reject behavior cho chúng. `identity` không parse numeric
  string thành numeric dimension; cần phân biệt ý tưởng boundary và selector.
  Các mốc large magnitude±10^10 không phải bounded integer limits trong spec.
- **Task120:** các lớp k=0/k=len(arr)/ở giữa, duplicate/sign/extrema liên quan spec.
  Nhưng max k phụ thuộc len(arr); khai global upper1000 không đủ context cho
  từng list. B1 dùng `transform=count` cho scalar k, B2 dùng `parsed_int` cho
  list arr: hai selector không biểu diễn ý định. C9 khai length1000 nhưng inputs
  dài nhất chỉ5; không có representative cho class này. C10/C11 chỉ thiếu labels
  trong covers dù có input chứa±1000, nên declared coverage thiếu không tự chứng
  minh semantic coverage thiếu. Không được đồng nhất label gap với input gap.

## Cách đọc coverage hiện tại

Hai catalogue qua schema (task0 và120) có18/18 class measurements `pending`,
6/6 boundary single-fault measurements `pending`; không boundary nào có nominal.
Trong toàn bộ raw catalogues có26 boundaries và0/26 nominal objects. Do đó không
xác nhận được normal single-fault design hoặc4n+1 từ metadata này.

Declared coverage của task0 là10/10 catalogue obligations và task120 là11/14;
các mẫu số này là model-declared obligations, không phải đầy đủ requirements
của spec. `covers` là self-report; các phản ví dụ phía trên cho thấy full declared
coverage không đồng nghĩa đúng class membership hoặc đúng BVA.

`numeric_targets_status=checked` chỉ có nghĩa code tính được targets từ endpoints
model khai; không chứng minh endpoints đúng spec hay inputs đã phủ targets.
`matched_values=[]` khi thiếu nominal không được đọc thành zero semantic coverage.
Đặc biệt `uncovered_boundary_values=0` trong hai measurement records là tổng trên
những `missing_values` khác null; ở đây mọi `missing_values=null`, nên giá trị0
này **không có nghĩa không thiếu boundary**. Khi giải thích kết quả phải giữ
uncovered-boundary metric là `pending`, không diễn giải thành0 đã kiểm.

Base-call coverage, đầy đủ/rời nhau của partitions và semantic grounding chưa có
kết luận tự động. Arm này không chạy DT; phần DT không có rules là not applicable.
Những catalogue interface/semantic limitations cần được báo cùng detection;
không đổi treatment hoặc nối thêm run từ audit này.
