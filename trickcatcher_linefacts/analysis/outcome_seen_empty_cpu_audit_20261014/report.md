# OUTCOME `seen == {}`: kết quả CPU trên DEV

Chạy bắt đầu 2026-10-13, hoàn tất 2026-10-14. **Lỗ hổng extractor có thật nhưng nhỏ trên DEV hiện tại; chỉ mở rộng OUTCOME từ pool fuzz cũ chưa thêm task bug mới.**

Clone: `pipelines/v12_outcome_audit`, từ snapshot hiện tại của `v11_fair`. `facts.py`, `tracer.py`, miner và các module extraction giống v7 byte-for-byte. Source gốc v7/v11, vendor và artifact lịch sử không sửa. Clone giữ extractor nguyên bản khi đo; bản clone và output execution đã được xóa sau khi hoàn tất theo yêu cầu người dùng.

## Trả lời bốn câu hỏi

| Câu hỏi | Kết quả |
|---|---|
| Bao nhiêu condition/subcondition có seen rỗng? | **6/333 sites (1,80%)**, trên **4/113 DEV**; gồm 3 condition + 3 subcondition |
| Bao nhiêu đã được fuzz chạm nhưng extractor bỏ OUTCOME? | **2/6 sites**, ở task **36 và 127**; pool cũ có witness cho **4 outcome candidates** |
| Bao nhiêu chỉ được STMT đại diện? | **4 sites ở task 56/124** chỉ có STMT cùng vị trí theo định nghĩa bên dưới, nhưng cả 4 **chưa có witness**. Tổng 5/6 sites có STMT cùng dòng; chỉ 1 có STMT reached và nằm trong top-three (task 127). Task 36 không có STMT tại dòng đó |
| Witness mới có làm lộ bug không? | 4 first witnesses: **3 hợp contract, 1 invalid**; **1 witness lộ bug** ở task 127, nhưng input đó **đã là witness STMT cũ**. **0 task bug mới** so với shown tool witnesses của pipeline cũ |

Mẫu số 333 là các sites do tracer hiện tại instrument được (263 `cond`, 70 `subcond`), không phải mọi predicate có thể có trong Python. `seen` rỗng là không có cell T/F trong base executions, không nhất thiết chứng minh expression chưa từng được bắt đầu đánh giá.

“Chỉ STMT” ở đây là: site nằm trên một dòng trong STMT fact và không có fact khác **đã reached** gắn cùng site/dòng. Đây là đối chiếu theo vị trí, không phải chứng minh ngữ nghĩa. Nếu yêu cầu STMT đó cũng đã có witness để method dùng được, số “chỉ STMT” là **0**. Tách các định nghĩa để tránh nhầm STMT ghi trong JSON với STMT được đưa vào prompt.

## Tất cả sáu sites

| Task | Loại | Dòng | Expression | Fuzz đã chạm? | STMT |
|---|---|---:|---|---|---|
| 36 | subcond | 13 | `n % 11 == 0 or n % 13 == 0` | T và F dưới B5; witness T trái official contract | Không có: dòng đã được base chạy, operand bị short-circuit |
| 56 | cond | 25 | `bracket == '>>'` | Không | Có STMT lưu, chưa reached, không shown |
| 124 | subcond | 48 | `int(date[1]) > 29` | Không | Có STMT lưu, chưa reached, không shown |
| 124 | subcond | 48 | `int(date[1]) < 1` | Không | Cùng STMT trên dòng 48 |
| 124 | cond | 48 | `int(date[1]) > 29 or int(date[1]) < 1` | Không | Cùng STMT trên dòng 48 |
| 127 | cond | 40 | `i % j == 0` | T và F | Có STMT reached/shown; witness của STMT chạm F |

Task 124 có ba instrumented sites nhưng chỉ một quyết định nguồn. Không diễn giải sáu sites là sáu bug hoặc sáu vùng code độc lập.

## Witness thật và expected độc lập

| Task/outcome | First witness | Contract | PUT | Canonical | Bug? |
|---|---|---|---|---|---|
| 36/T | `fizz_buzz(0)` | Invalid | `1` | `0` | Không tính bug: trái contract |
| 36/F | `fizz_buzz(3)` | Valid | `0` | `0` | Không |
| 127/T | `intersection((-5, 5), (-5, 5))` | Valid | `'NO'` | `'NO'` | Không |
| 127/F | `intersection((0, 4), (0, 4))` | Valid | `'YES'` | `'NO'` | **Có, wrong output** |

Task 127 yêu cầu kiểm tra **độ dài giao hai interval** có nguyên tố không. Với `(0,4)` giao `(0,4)`, độ dài là 4, nên phải `'NO'`. PUT lại kiểm số nguyên tố theo các số trong interval, bỏ qua composite ở upper endpoint do `range(start,end)`; trả `'YES'`.

OUTCOME bỏ `i % j == 0` vì base chưa đánh giá nó. Tuy nhiên STMT top-three cũ cho lines 39–41 đã có **chính input `(0,4),(0,4)`**, nên mở thêm outcome F không thêm input hay task detection mới. Outcome T có thêm một mô tả mục tiêu nhưng first witness không lộ bug.

Task 36 cho thấy một lỗi khác: B5 cho `n=0` qua, official contract không cho phép. Nếu thêm OUTCOME T mà không kiểm miền hợp lệ, dễ thêm hint/input gây false alarm. Đây là ví dụ không nên hiểu “đã fuzz-confirmed” là “đã hợp spec chính thức”.

Trong tất cả inputs của pool chạm các sites này: **19 unique calls**, **7 call lộ bug**, tất cả ở **task 127** (không cộng trùng input chạm T và F ở các iteration khác nhau). Kể cả chọn witness tốt nhất trong pool với evaluator độc lập, vẫn **0 task bug mới** so với witness top-three cũ. Đây là pool ceiling, không dùng labels để chọn witness cho method.

STMT witness hiện chỉ nhắm 1/4 outcome candidates đã có witness; 3/4 candidates còn lại chưa được STMT witness đại diện. Điều đó xác nhận giới hạn outcome-level của STMT, nhưng hiện chưa chuyển thành thêm task bug mới.

## Kiểm chứng và giới hạn

- 113/113 extraction workers và 113/113 scoring workers hoàn tất; `failures.json` rỗng.
- **113/113** khớp historical fuzz size/validity stats; mọi STMT/OUTCOME cũ và witness tương ứng khớp, **0 reproduction drift**.
- Gọi `facts.main` của clone qua evidence hook; `mutant_points=[]` để không rerun mutation. Base/fuzz RNG và STMT/OUTCOME không thay đổi; so sánh với full historical facts đã xác nhận. Top-three/STMT shown lấy từ bundle lịch sử, không xếp hạng lại trong run bỏ mutation.
- Canonical và official contract chỉ được nạp trong scoring sau khi extraction toàn DEV hoàn tất; không tham gia fuzz, candidate creation hay first-witness selection.
- Replay plain PUT/canonical, tránh tính lỗi instrumentation là bug. So successful outputs bằng v11 shared scorer và official atol, tách wrong output/exception/timeout; 0 exact/tolerant disagreement trên 19 hitting calls.
- 4 tests đã qua: nested guard, short-circuit trên cùng dòng, ngăn gold/pilot vào method job, xác nhận invalid/crash/wrong output/float tolerance.
- Không có LLM call, không generation experiment, không thay đổi ranking/gates/method. Kết quả là chẩn đoán DEV, chưa phải chứng cứ tăng effectiveness trên held-out.

## Quyết định nên rút ra

Sửa schema để biểu diễn `seen_empty` vẫn có ích cho độ đầy đủ của representation, đặc biệt short-circuit. Nhưng **không nên ưu tiên một LLM run chỉ để thêm hai OUTCOME sites fuzz cũ đã chạm**, vì CPU audit chưa thấy task bug mới.

Nếu đi tiếp hướng concept + relation, phần đáng thử là tìm witness cho các candidate chưa reached nhưng có miền hợp lệ và relation dẫn tới chúng, cộng với hypothesis vi phạm spec trên code đã cover. Task 56 còn có expression `bracket == '>>'` trong loop duyệt từng ký tự của string: cần feasibility/domain reasoning, tránh tìm kiếm vô ích. Không coi mọi candidate chưa reached là cơ hội bug như nhau.

## Báo cáo được giữ sau cleanup

Folder clone `pipelines/v12_outcome_audit` và các input/output execution của nó đã được xóa theo yêu cầu người dùng. Không có Git worktree mới; run thực hiện trong folder riêng của repo trên main.

Giữ các bảng số liệu và provenance nhỏ cạnh báo cáo này:

- [Câu trả lời định lượng](answers.json)
- [Tổng hợp](summary.json)
- [Danh sách sites](sites.csv)
- [Witnesses](witnesses.csv)
- [Outcome candidates](candidates.json)
- [Kiểm chứng](verification.json)
- [Snapshot source hashes](clone_manifest.json)
- [Plan trước run](AUDIT_PLAN.md)

Các đường dẫn clone ghi trong provenance là đường dẫn lịch sử và không còn tồn tại. Muốn chạy lại cần tạo bản sao mới từ source; archive này chỉ chứa báo cáo và số liệu, không chứa runnable pipeline.
