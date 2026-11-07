# Checked grounding: thử nghiệm offline sau checkpoint v5

Update: user đã gửi lại endpoint; [live diagnostic](boundary_checked_grounding_2026-11-06.md)
sau audit này đã COMPLETE:8calls,23valid, bug task16. Phần “chưa chạy” bên dưới
mô tả thời điểm hoàn tất offline audit; live report supersedes trạng thái đó.

Đã restore đúng v5, test234pass và push commit `13d92ee9` lên `main` trước khi
triển khai thử nghiệm này. Compact prompt được archive, không phải default.

Thử nghiệm mới là opt-in `grounding_mode="checked"`; chưa commit/push. Không tái
hiện paper, không thêm task-specific witness vào generator. Dựa trên đề xuất
[semantic grounding](boundary_semantic_grounding_research_2026-11-06.md), nhưng
không claim một phương pháp mới chưa từng thử: v10/v47/v66/v68/v69 đã cung cấp
các giới hạn về spec predicates, ranking và constructor.

## Đã triển khai và thử được gì

1. AST receipts cho các quantity hỗ trợ: string length, encoded byte length,
   code point kèm transform, full sum và một dạng prefix accumulator đơn giản.
2. Nhánh reject False có receipt cho operator bổ sung của điều kiện để tiếp tục;
   không tự gắn nó thành overall function acceptance hoặc spec correctness.
3. Contract type assertions được nhận diện có thể thêm float neighborhood dù
   observed inputs toàn int. Không suy thêm type từ output hoặc PUT behavior.
4. Compiler loại concrete target vi phạm recognized domain guard trước khi chia
   context budget. Joint constraints còn lại vẫn kiểm ở full constructed call.
5. Thêm raw `code_point` characteristic; không tráo nó với `ord` sau `.lower()`.
   Constructor dùng một Unicode scalar và kiểm target sau khi dựng call.
6. Context có thể khai báo `non_ascii` hoặc `prefix_exceeds_limit`. Property sau
   yêu cầu proper prefix > limit và total <= limit; chỉ có số âm là chưa đủ.
   Coverage được ghi riêng theo input cuối, không tự gọi property đó là bug.

Default off mode không thêm receipts/goals/menu vào prompt: cả10saved selection
messages và candidate menus đều khớp byte với v5. Source/settings identity có
đổi do thêm experiment, nên run mới vẫn cần fresh output directory; không sửa
hash guard để ép replay checkpoint cũ.

## Kết quả audit artifact cũ

[JSON đầy đủ](boundary_grounding_offline_2026-11-06.json) được tạo bằng
`python -m final.src.audits.audit_bva_grounding`. Chỉ đọc saved prompts/selections;
không gọi model, chạy PUT hoặc reference. Toàn bộ312file run v5được giữ nguyên.

| Task | Finding/check mới | Giới hạn |
|---|---|---|
| 16 | Nhận ra threshold256của transformed code point bị gắn vào length | Chỉ chẩn đoán saved binding; không tự rewrite nó thành đúng hypothesis |
| 72 | Receipt cho accumulator ở visited prefix, khác full sum | Không chứng minh câu NL đã dịch đúng; scope syntax ngoài subset là unknown |
| 157 | Operator reject `<=0` bổ sung cho tiếp tục `>0`; không hỗ trợ nhãn mismatch cũ | Chỉ xét predicate này; không kết luận toàn hàm đúng |
| 157 | a/b/c đều có float_adjacent từ contract, không bị observed int thu hẹp | Chưa có arithmetic relation/hypotenuse characteristic |
| 157 | Prune below=-1 và at=0, còn above=1.0, quota20 | Giảm wasted budget, chưa làm target đó liên quan bug hơn |
| 23 | Source fact là encoded bytes; menu có code_point | Saved response cũ abstain nên không có constructed input mới trong audit |
| 2/11 | Không có finding phủ định abstention tự động | Chưa giải semantics integer crossing/joint empty edge |

Audit cũng thêm code-point candidates cho các string task khác. Đây là mở rộng
pool và thay guidance, không isolate chất lượng chọn semantic boundary. Cần
random/same-pool controls trước khi claim efficacy của selection.

## Verification và review

-44grounding engineering cases kiểm supported/unsupported syntax, shadowing,
  mutation, numeric widening, real vs false operator mismatch, Unicode targets,
  domain pruning và prefix property/replay. Các fixture dùng condition thiết kế
  sẵn để kiểm constructor, không phải model tự tìm ra bug.
- Independent reviewer tìm và yêu cầu sửa false receipts ở nested functions,
  wildcard imports, prior unsupported loops, annotated/walrus writes, character
  so sánh trực tiếp với integer, shadowed type builtins và `sum(..., start=...)`.
  Đã sửa trước audit/live calls; unsupported cases trả unknown hoặc không emit.
- Amendment ghi review fixes sau offline audit vừa kết thúc, trước khi đọc
  findings; không claim amendment đó đã đăng ký trước offline outcome. Kế hoạch
  tổng thể đã có trong PREREG trước code; live diagnostic chưa chạy.
- Các assumptions về builtin types/finite numeric operations vẫn phải giữ rõ;
  AST receipts không phải một general Python analyzer hay semantic proof.

## Live diagnostic chưa chạy

Đã preregister cùng6PUT miss2/11/16/23/72/157, max12logical calls, input20/task,
selection4096/context8192/generation2048, exact qwen3.5-27b-awq. All-input freeze
trước corrected reference/PUT evaluation. Không thay model/provider hoặc nới run.

Endpoint config trong `/tmp` đã mất; metadata check không có completion dừng
MissingEndpoint. Khôi phục private config từ endpoint user đã cho, `/models`
trả HTTP404. Đã hỏi user replacement; không có model task call mới, không retry
completion/giả lập response. Chưa có detection result cho trial này.

Sau khi có endpoint cần kiểm metadata/tokenization, freeze source/old outputs,
chạy fresh output `final/out/boundary_checked6_20261106` và báo từng stage. Những
task đã nhìn dùng để diagnostic cơ chế, không phải detection-rate/held-out evidence.
