# Boundary v5 và naive trên cùng10PUT known-bug

Theo yêu cầu user, lấy plain inputs đã lưu từ run164`v11_concept_inputs`, giữ
nguyên và chấm lại trên exact10PUT của known_bug_10 bằng corrected HumanEval+
reference hiện tại. Không gọi model mới, không sinh/repair thêm input; source
batch/source-run hashes được giữ, toàn bộ10batch freeze trước reference execution.
Standard FrozenInputsGenerator và pipeline hiện có; full read-only replay khớp.

| Task | PUT | Boundary v5 valid inputs | Boundary bắt bug | Naive valid inputs | Naive bắt bug |
|---|---:|---:|---|---:|---|
|2|6|0|Không|20|Có|
|11|1|0|Không|19|Có|
|16|4|0|Không|19|Không|
|23|7|0|Không|0|Không|
|72|4|7|Không|20|Không|
|76|0|14|Có|20|Có|
|99|1|6|Có|0|Không|
|124|0|19|Có|0|Không|
|140|7|12|Có|0|Không|
|157|3|6|Không|15|Có|
|Tổng||64|4PUT|113|4PUT|

Shared76; boundary-only99/124/140; naive-only2/11/157. Union7không phải kết quả
của một method/run. Không cộng các task thắng từ checked6hoặc Luna direct3vào v5.

Naive cũng sinh input ở/gần boundary dù không được hướng dẫn BVA:2dùng
0.9999999999và999.9999999999gần integer;11dùng hai string rỗng;76có(0,2)và(1,0).
157dùng(0.5,1.2,1.3), residual squared-Pythagorean=-2.220446049250313e-16,
ở gần arithmetic equality trong floating-point semantics của oracle. Đây là
phân loại hậu nghiệm, không chứng minh naive đã áp dụng quy trình BVA hay sinh
đủ below/at/above. Không dùng nhãn naive để suy ra inputs không có boundary values.

Các số0naive ở23/99/124/140không phải do corrected oracle loại toàn bộ input:
source-generation batch đã có0admitted input trước scoring. Naive slice có119
raw admitted records,113novel valid sau oracle/dedup. Original plain generation
trên10task có10calls; boundaryv5có16calls. Rescore mới có0model calls.

Đây là đối chiếu descriptive trên cùng targets/oracle. Historical naive prompt
đã xem original cohort với nhiều PUT/task, còn boundaryv5thấy selectedPUT/task;
generation visibility và request budgets khác. Tập10PUT chọn theo kết quả và đã
dùng để thiết kế các repair, nên không gọi4/10là general detection rate hay
claim superiority từ4vs4.

Baseline44được seal là một run naive khác; trong saved detections của nó chỉ
có124PUT0trùng targets này, còn99làPUT0khác targetPUT1. Không trộn run đó vào
cột naive trên. Có thể đọc [overlap audit](plain_known_bug10_overlap_2026-11-06.json)
để phân biệt các baseline.

Machine-readable [table/receipts](boundary_naive_known_bug10_2026-11-06.json).
Rescore:final/out/naive_known_bug10_rescore_20261106/evaluation. Boundary:
final/out/boundary_known_bug10_prompt_v5_20261105. Corrected native evaluation
giữ2repeat slots; original outputs và sealed44baseline không bị sửa.
