# Final: HumanEval → diverse programs → additional tests

**Entry point theo class/module:** [modular/README.md](modular/README.md) — mỗi
loại chạy một module, mỗi stage một class, thêm pipe qua `insert_stage()`;
mặc định replay chỉ đọc run đã hoàn thành, không gọi model.

**Active design sau khi user làm rõ mục tiêu:**
[Concept benchmark với reference oracle](experiments/concept_reference_v1/README.md).
Bản sửa transport để tiếp tục run nằm tại
[concept_reference_v1_recovery](experiments/concept_reference_v1_recovery/README.md),
giữ nguyên method/cohort/checkpoints và thêm streaming cùng retry có giới hạn.
Bản mới phân tích base+PUT bằng boundary/equivalence/CFG/def-use, so sánh concept
với plain trên cùng cohort và dùng reference để sinh expected output. PUT chỉ sinh
một lần tại `final/out/cohorts/`; các concept experiments dùng lại cohort đó.
Phần bên dưới lưu hướng dẫn của bản plain ban đầu.

Folder độc lập theo yêu cầu ngày 2026-10-30. Mặc định chạy đủ **164 task**:

1. LLM sinh **10 chương trình khác nhau/task**, đều được yêu cầu giải đúng spec.
2. Chuẩn hóa AST để loại bản chỉ khác format, comment, docstring, annotation hoặc
   tên biến. Yêu cầu nhiều algorithm; tối đa 5 writer calls/task để bổ sung bản trùng.
3. Chạy base tests gốc HumanEval và chỉ giữ chương trình pass.
4. **Một tester call/task** sinh tối đa 30 test mới dùng chung cho tất cả chương
   trình đã pass. Tester thấy spec, base tests, các chương trình; không thấy canonical.
5. Loại input đã chạy trong base tests, input mới bị lặp, test không pass canonical
   qua hai lần chạy. Không sửa expected output bằng kết quả canonical.
6. Chạy test hợp lệ hai lần; đếm mỗi chương trình fail thêm một lần duy nhất.

`CoreModel` ở [core_model.py](core_model.py) là interface duy nhất cho model.
Backend hiện có là API Chat Completions tương thích OpenAI; backend khác chỉ cần
implement `model_id`, `generate()` và trả về `ModelResponse`. Factory
`--backend-factory package.module:function` nhận parsed CLI arguments và trả một
`CoreModel`; pipeline không cần thay đổi.

## Chạy

Linux cần `bwrap` (bubblewrap). Code được sinh chạy trong filesystem/network sandbox,
không nhận API key và không thấy host files ngoài Python runtime. Không có fallback
chạy code trực tiếp trên host. Pipeline chỉ dùng Python standard library; pytest
chỉ dành cho engineering checks. Dùng Python 3.11.14 đã có trong repo:

```bash
CoverUp_concept/.venv/bin/python -m final.run --check
CoverUp_concept/.venv/bin/python -m pytest final/tests -q
```

Model/endpoint đang chờ người dùng cung cấp. Cấu hình qua environment; không ghi
key/endpoint vào code, command log hay manifest. Nạp key theo rule của repo:

```bash
source scripts/research_env.sh >/dev/null 2>&1
# Export FINAL_BASE_URL, FINAL_API_KEY, FINAL_MODEL trong shell từ config phù hợp.
# Nếu dùng biến có sẵn, có thể chỉ định --base-url-env và --api-key-env.
CoverUp_concept/.venv/bin/python -m final.run \
  --out final/out/humaneval164 --workers 2
```

Nếu dùng router config hiện có, chỉ sau khi đã chọn đúng model:

```bash
CoverUp_concept/.venv/bin/python -m final.run \
  --model "$FINAL_MODEL" --base-url-env ROUTER_BASE_URL --api-key-env ROUTER_API_KEY
```

Chạy lại cùng command để resume; response đã lưu sẽ được dùng lại. Run lock ngăn
hai process chạy trùng output directory. Nếu request đã gửi nhưng không có response
được lưu, runner dừng với usage unknown, không tự gọi lại. Source/config/interpreter
khác manifest phải dùng output directory mới. Có `--task-ids` cho engineering subset;
run chính mặc định là đủ 164 task. Log dài nên chạy detached, theo dõi `status.json`.

## Artifacts và cách đọc số liệu

- `manifest.json`: model, settings, Python, task IDs, source/dataset hashes; không có URL/key.
- `tasks/<id>/calls/`: prompt, response, usage và trạng thái từng invocation.
- `tasks/<id>/programs.json`: 10 chương trình, approach, fingerprint và bản bị loại.
- `tasks/<id>/base/`: base-test outcomes.
- `tasks/<id>/tests.json`: test giữ lại và lý do loại test khác.
- `tasks/<id>/new_tests/`, `result.json`: outcome matrix và chương trình bị phát hiện.
- `summary.json`, `REPORT.md`: tổng hợp toàn run; `status.json`: lifecycle.

Metric chính là **số chương trình pass base nhưng fail test mới / số chương trình
pass base**. Báo riêng tỷ lệ chương trình thực sự có test hợp lệ để kiểm tra.
Không gọi đây là recall vì chưa biết tất cả chương trình nào có bug. AST khác nhau
không chứng minh algorithm khác nhau. Canonical check không tự chứng minh input
hợp lệ theo spec hay predicate đúng cho mọi output hợp lệ; các task có nhiều đáp
án cần property và semantic review. Xem [PREREG.md](PREREG.md) trước khi diễn giải.

`data/humaneval.jsonl` được giữ nguyên từ dataset có sẵn trong repo tại
`PBT_EdgeCases/run/data/humaneval.jsonl`; checksum được kiểm tra trước mỗi run.
Không sửa source của bất kỳ paper/vendor nào.

Đã xác minh toàn bộ records khớp dataset gốc OpenAI HumanEval. **17 engineering
checks pass**, **164/164 canonical solutions pass base tests**; independent review
đã hoàn tất. Đây là validation của harness, chưa phải kết quả chạy model.
Chi tiết ở [validation/REPORT.md](validation/REPORT.md).
