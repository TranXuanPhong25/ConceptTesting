# Follow-through: quyết định sau v40/v41

2026-10-21. User cấp quyền tự quyết tiếp tục research/refinement. Đã kiểm tra saved
results của v40 và v41, không khởi chạy lại hoặc sửa experiments. Tài liệu này cập
nhật conditional recommendation trong [paper comparison](CONCEPT_GUIDED_PROPOSAL_20261021.md).

## Quyết định

**NO-GO cho package concept-guided adaptive testing hiện tại. Không triển khai D2,
không mở benchmark, không tăng n/K và không train concept-to-input từ kết quả này.**
Đây là quyết định về package/model/protocol đã thử; không kết luận concepts nói chung
vô ích hoặc mọi cách adaptive testing đều thất bại.

Lý do: v40 không vượt semantic capability gate và không có incremental concept
discovery. v41 không vượt relation-selection gate. Hai kết quả không được cộng gộp
thành một effect vì khác setting/protocol; chúng chặn hai cơ chế khác nhau.

## 1. v40 đã complete, không còn chỉ là progress snapshot

Authoritative run status: `complete`, ended `2026-10-21T14:07:31.783595+00:00`.
72/72 completions received;65 turns accepted,7 failed admission. Các final turns
đều accepted. Analysis `REPORT.md` còn chứa running snapshot; không dùng snapshot
đó thay cho saved terminal status. `results.json` còn ghi semantic gate pending;
verdict ở đây dựa trên cả hai completed semantic audits và spot-check raw evidence.
Không thay report/flags của owner session.

| Arm | Accepted turns | Accepted finals | Discovery episodes không có supplied revealing witness |
|---|---:|---:|---|
| concept_adaptive |24/24|8/8|E1,E2,E4,E5 —4/4|
| generic_adaptive |23/24|8/8|E1,E2,E4,E5 —4/4|
| concept_committed |18/24|8/8|E1,E2,E4,E5 —4/4|

Input-exposure task sets cũng trùng nhau: E1–E6 ở cả ba arms. E3/E6 có supplied
revealing observations, không được tính thành independent new-task discovery.
E7 correct-code control, E8 normative ambiguity; không tính chúng là hai missed bugs.
Task novelty chỉ trong diagnostic/shared-pool scope, không là historical benchmark novelty.
Model không được yêu cầu viết expected-value assertions; không gọi input exposure là
correct assertion generation.

## 2. Semantic gate thất bại dù concept-adaptive không mất turn vì schema

Đã đọc hai reports [A](../../../trickcatcher_linefacts/analysis/v40_retry3_20261021/SEMANTIC_A.md),
[B](../../../trickcatcher_linefacts/analysis/v40_retry3_20261021/SEMANTIC_B.md) và
spot-check raw final claims/prior native events cho E2/E4/E6. Đây là verification
sau khi đọc reports, không phải một blind independent replication.

| Case | Observation model đã nhận | Final concept-adaptive claim | Assessment |
|---|---|---|---|
| E2 equality boundary | `[2,2,2]`,limit2 →0 | Withdraw strict-`>`; keep implementation `>=` | Đổi observed implementation thành desired behavior, trái evidence |
| E4 empty eligible | Empty/all-negative inputs →ValueError | Withdraw ValueError hypothesis | Bỏ hypothesis đúng sau execution xác nhận |
| E6 multiplicity | `[2,2]` →2; shared `[2]` →2 | Withdraw deduplication hypothesis | Không tích hợp clean multiplicity contrast |

Các mistakes trên nằm trong accepted claims và usable native feedback. Sửa JSON
hoặc tool cap không tự giải thích được chúng. Concept-adaptive có 24/24 accepted
turns, nên không thể quy toàn bộ semantic no-go cho interface.

Gate assessment theo original `d1_protocol.json:go_no_go`:

- Final validity: pass8/8.
- Correct-H retention E2/E4: fail cả hai, requirement2/2 không đạt.
- False/overbroad-H handling: E6 fail; requirement4/4 không đạt.
- Wrong normative binding E3: không coherent reject equality-vs-inclusion; fail.
- E7 không final false bug flag và E8 giữ ambiguity: pass.
- Input discovery trên no-supplied-witness episodes: có4/4 nhưng generic cũng4/4.
- Incremental concept requirement >=2 concept-only discoveries: **0**, fail.

E1/E5 và phần boundary của E6 đã được model nhận ra trước injected feedback.
E7 là genuine unresolved opportunity nhưng CA lặp query/prediction rồi sửa claim
muộn ở final. Chưa có hai eligible evidence-linked query adaptations để support
adaptivity claim. Phần adaptation comparison vì vậy bị giới hạn bởi proactive
reasoning/opportunities, không được diễn giải thành proof mọi adaptive query vô ích.
Combined package vẫn no-go vì các gates khác đã fail rõ ràng.

## 3. v41 đóng nhánh observed-anomaly selection này

[Existing v41 CPU report](../../../trickcatcher_linefacts/analysis/v41_iorel/RESULTS.md):
sampled pool exposure22/33; displayed relation package11/33; expected random-k8.94;
median per-task lift0.38. Registered gate đòi C2>=17 và median lift>=2, nên no-go.
Eight exposed tasks không có relation package theo rule; minority behavior không
tương đương semantic violation.

22/33 là evaluation-only opportunity bound của pool cụ thể với nhiều executions,
không phải một generator đã tự nhận đúng22 bugs. Sample validity53% là limitation.
Không dùng reference-derived exposure labels để tạo guidance hoặc tự lựa chọn
chỉ các successful tasks cho một claimed automatic method.

## 4. Hệ quả cho proposal và contribution

Prior work đã có RCA/trigger/test/feedback. Evidence mới cũng chưa chứng minh
semantic concept thêm giá trị trên cùng raw evidence. Do đó không chốt một new
pipeline/thesis contribution bằng cách ghép các thành phần đã có.

Những gì giữ lại có ích là vocabulary có scope, phân biệt normative với observed
behavior, tools có provenance và per-stage failure accounting. Chúng phục vụ
phân tích; chưa tự thành một improved test-generation method.

Nếu sau này có hypothesis khác, điều kiện để xem xét là evidence mới xác định một
cơ chế khác và có kiểm tra rẻ để bác bỏ nó. Không dùng model swap, prompt tweak,
pool enlargement hoặc tăng benchmark làm mặc định sau no-go này. Không khẳng định
chưa từng có concept-to-input success: nhiều revealing inputs đã được sinh đúng;
vấn đề ở đây là semantic integration và không có incremental task gain.

## Verification và phạm vi hành động

[Saved-data verifier](verify_v40_saved_20261021.py) chỉ dùng stdlib để kiểm tra frozen
file hashes,24rows/72artifacts, input-label consistency và aggregate discovery sets.
Không import pipeline/scorer, không gọi PUT/model/network. Manual semantics có
source/record anchors trong [evidence JSON](CONCEPT_FOLLOWTHROUGH_20261021.evidence.json).
Integrity/cost audit gốc giữ riêng physical worker và logical requests:
[audit](../../../trickcatcher_linefacts/analysis/v40_retry3_20261021/INTEGRITY_COST_AUDIT.md).
Không nhận các historical inference costs là chi phí mới của follow-through này.

Final disposition: current refinement candidate đã được đánh giá và dừng; không có
run mới do task này tạo. Broad autonomy được dùng để chốt negative result và tránh
chi thêm vào một package chưa có go signal.
