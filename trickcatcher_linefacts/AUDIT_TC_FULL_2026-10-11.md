# Audit tc-full và so sánh với plain

Ngày 2026-10-11. Audit source và dữ liệu đã chạy; không sửa implementation,
không chạy lại LLM, không sửa source của tác giả.

**Kết luận:** luật differential testing chính khớp Algorithm 1. Tuy nhiên có lỗi
transport làm mất input hợp lệ, và bảng so sánh đang tính crash/timeout cho plain
nhưng không tính cho tc-full. Dữ liệu hiện tại không chứng minh plain thắng tc-full.

## Nguồn và kiểm chứng

- [Paper ACL 2025](https://aclanthology.org/2025.acl-long.20.pdf): Sec. 4,
  Algorithm 1, Sec. 5 và Appendix A/B.
- [Artifact, commit a0d285a](https://github.com/RinCloud/TrickCatcher/tree/a0d285a77efff7c93fc280d606497d9de5e1defe),
  đặc biệt `Analysis/utils.py:ep_compute_res` và `Analysis/RQ1&RQ5.ipynb`.
- `out/tcfull_qwen7b/{tasks.json,generation_manifest.json,cpu_manifest.json,eval.jsonl,task_summary.json,report.json}`.
- `out/tcfull_qwen7b/cpu/<task>/...`: log pool, generator và execution.
- `out/gen2_qwen7b_v3m2/{tasks.json,eval.jsonl}` và `out/oracle_b01/exec/<task>.json`.

Đã đối chiếu Git blob SHA-1 của bốn prompt local với tree của commit gốc:
`genprog_tc_sys/usr`, `geninput_generator_sys`, `geninput_usr` đều trùng.
Bốn source hash trong CPU manifest đều khớp file hiện tại. Hai bundle có cùng
133 task và cùng `put`, `base`, `entry`, `split` trên từng task.

## Những phần đúng và giới hạn của tuyên bố faithful

- Sinh variant có xem PUT; chỉ giữ variant qua base `check(candidate)`.
- Bỏ output giống PUT, chọn nhóm đông nhất trong các output còn khác PUT.
  Không cần đa số trên toàn bộ variant. Mô tả “PUT khác đa số variant” trong
  `RESULTS.md` mục 8 là không chính xác.
- Contract/canonical chỉ chấm nhãn; không chọn input hay oracle của tc-full.
- `subset_scores` giữ tất cả nhóm đồng hạng và tính trọng số như
  `ep_compute_res(tc)`; notebook lấy mean precision theo task có phát test.
  Đây là metric riêng, không phải binary detection/any-of-K.
- Bỏ crash/timeout phù hợp phạm vi Appendix A của paper. Bởi vậy việc bỏ chúng
  trong tc-full không phải lỗi Algorithm 1; lỗi nằm ở so sánh khác phạm vi.

Không nên mô tả toàn bộ experiment là “chỉ thay model”: còn tập 133 task,
sampling parameters tự chọn, timeout, ba lần resample chung một pool và quy tắc
serialization/tie-break. Main emission chọn một nhóm đồng hạng đầu tiên;
paper-metric giữ mọi nhóm đồng hạng. Paper báo 151 task, còn notebook gốc dùng
`ep_PUT_len=150` cho TC/DPP; runner hiện tại dùng số task thực tế của từng split.
Các số recall/precision/F1 hiện tại không phải tái lập trực tiếp bảng paper.

## So sánh lại detection trên DEV

113 task, K=3, tổng 339 mẫu mỗi arm. “Bài/lượt” = số mẫu phát hiện / 3,
không phải phần trăm. Chỉ giữ input hợp lệ theo contract.

| Cấu hình | Mẫu phát hiện | Bài/lượt | Bài có ≥1/3 mẫu phát hiện |
|---|---:|---:|---:|
| plain, oracle gốc o0, tính crash/timeout | 123 | 41.0 | 63 |
| plain + ref, tính crash/timeout | 142 | 47.33 | 69 |
| tc-full, phạm vi hiện tại không crash/timeout | 132 | 44.0 | 46 |
| plain, o0, chỉ sai output khi PUT trả về | 108 | 36.0 | 56 |
| plain + ref, chỉ sai output khi PUT trả về | 120 | 40.0 | 59 |

Tính lại bằng cách đọc assertion của từng mẫu plain, lấy call theo
`oracle_b01.call_of`, khử call trùng trong mẫu, ghép với `exec/<task>.json` và dùng
`oracle_b01.decide`. Detection hiện tại là `emit and canon_ok and not put_ok and valid`.
Bản giới hạn functional thêm `rec['put'] == 'ok'` vào từng detection witness,
sau đó OR theo mẫu. Không loại cả mẫu nếu nó đồng thời chứa crash và sai output.

- plain+ref hiện tại so tc-full: thắng/thua theo task 31/24,
  exact two-sided sign p = 0.418754.
- plain+ref chỉ functional so tc-full: 22/25, p = 0.770867.
- plain o0 hiện tại so tc-full: 32/31, p = 1.0.

22 mẫu plain+ref chỉ phát hiện crash/timeout, trên task
4, 12, 23, 55, 79, 83, 89, 91, 136, 158. Ví dụ task 4:
`mean_absolute_deviation([1.0])` là input hợp lệ, canonical trả 0.0,
PUT ném ValueError. Plain+ref được tính detection, tc-full loại input này.
Khoảng hơn ban đầu chỉ 10 mẫu (142 − 132), nhỏ hơn 22 mẫu khác phạm vi.

Đây là phân tích lại log, chưa phải experiment hoàn toàn cân bằng: oracle_b01
có timeout 3 giây, tc-full 1 giây; equality và ngân sách generation khác nhau.
K của tc-full chỉ đổi 100 vị trí lấy từ cùng pool và cùng variant, còn plain
có ba lần sinh assert. Vì vậy any-of-K không đại diện cùng mức độc lập giữa các lần chạy.
Không kết luận bên nào hơn có ý nghĩa thống kê từ các số trên.

## Lỗi implementation xác định được: input tuple bị loại

`generator_worker.py:53–57` JSON-encode rồi decode và kiểm
`decoded != list(restored)`. JSON biến tuple lồng nhau thành list, khiến input như
`[(1, 2), (2, 3)]` bị loại dù `repr`/`ast.literal_eval` giữ nguyên được input này.

Task 127 `intersection(interval1, interval2)` dùng interval dạng tuple ngay
trong spec. Cả bốn generator đều trả list chứa hai tuple đúng dạng, nhưng mỗi
generator có `rejected=100`, `returned=0`, `first_rejection='ValueError: input failed JSON roundtrip'`.
Tổng 400 input bị loại; pool rỗng; 7 variant sống không có input để chạy.
Đây là lỗi adapter/transport, không phải lỗi model và không phải yêu cầu của paper.
Chưa chạy lại sau sửa nên chưa có ước lượng detection phục hồi.

## Vì sao direct input vẫn có thể tốt hơn generator

Task 2 `truncate_number`: PUT có nhánh sai `if number == 1: return 1`.
Cả bốn generator đều dùng `uniform(0,10)`. Pool 400 input có **0 input bằng 1.0**;
mọi output của 10 variant trên 300 lần lấy mẫu đều đồng ý với PUT (3,000 lượt).
Plain mẫu 0 và 2 viết trực tiếp `assert truncate_number(1.0) == 0.0`.
Đây là bằng chứng cụ thể rằng random generator có thể bỏ sót một điểm biên
dù variant đã sửa đúng bug.

Sức khỏe pipeline DEV:

- 82/452 generator không trả được input nào được worker chấp nhận.
- 5 task pool rỗng: 50, 66, 119, 127, 161.
- 5 task không còn variant qua base: 10, 26, 50, 132, 163.
- 798 PUT executions và 3,603 variant executions không `ok` trong ba resample;
  đây là số lượt, có thể lặp cùng input, không phải số bug hay số task.
- Không có output serialization error.

Nhiều generator lỗi API CYaRon/import/name, nhưng 82 ca rỗng còn gồm lỗi arity,
syntax và lỗi tuple nêu trên; không quy tất cả cho chất lượng model.
Prompt gốc cũng chứa ví dụ dễ gây shadow tên `string` khi wildcard import;
chưa tách được ảnh hưởng prompt, model và phiên bản thư viện bằng ablation.

## Các tỷ lệ false alarm cũng cần cùng mẫu số

Plain+ref: 83 assertion sai/2,808 assertion phát ra = 2.96%.
TC-full: 172/3,319 = 5.18%. Nhưng TC chỉ phát assertion khi khác PUT, còn plain+ref
phát cả assertion pass PUT. Nếu chỉ nhìn assertion fail PUT của plain+ref theo
evaluator hiện tại: 20/377 = 5.31%. Đây vẫn là chẩn đoán trên log, chưa cân bằng
crash/timeout/equality. Không dùng 2.96% đối 5.18% để kết luận trực tiếp chất lượng
bug report. Tỷ lệ lỗi assertion cũng không thay thế được RQ2 chạy lại trên PUT đúng.

## Việc nên làm tiếp

1. Sửa adapter tuple, giữ nguyên code generated và cache LLM; chạy CPU ở output
   mới để giữ nguyên artifact cũ và đo tác động thật.
2. Báo hai phạm vi functional-only và including-crashes cho mọi arm, đồng bộ
   timeout/equality nếu cần so sánh chặt chẽ.
3. Ghi rõ `plain + ref` là pipeline có thêm 10 reference programs từ spec;
   không gọi nó là baseline direct assertion đơn thuần của paper.
4. Giữ riêng detection, paper-weighted metrics, false-alarm trên assertion,
   false-alarm trên bug report và RQ2; công khai khác biệt ngân sách/K.

Audit này chỉ thêm tài liệu; các bước sửa/chạy lại trên chưa được thực hiện.
