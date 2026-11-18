# MBPP+ v0.2.0

`mbppplus_v0.2.0.jsonl.gz` là nguyên bản asset `MbppPlus-OriginFmt.jsonl.gz` (378 task):
https://github.com/evalplus/mbppplus_release/releases/tag/v0.2.0

SHA-256: `7a5aec547b134fa297ee6c45f829298aa3f58de02547b8d8a5c3d85d9cb10efc`.

Từ 2026-11-16, `DatasetLoader('mbpp-py')` và `load_mbpp()` mặc định đọc file này,
không dùng MBPP test split 500 task. Giữ ID `MBPP/<number>` tương thích cohort cũ.
Adapter dùng prompt, code reference và test_list/test_imports của release;
base tests không phải toàn bộ test tăng cường của MBPP+.
Asset nguồn giữ nguyên, bao gồm field `test` chứa full test harness.
MBPP gốc vẫn giữ ở `mbpp.jsonl`; chỉ đọc khi truyền path tường minh.

Sinh tiếp (không tự chạy khi sửa code):

```bash
source scripts/research_env.sh
export FINAL_BASE_URL='<endpoint>/v1'
final/.venv_orchestration/bin/python scripts/continue_mbppplus_puts.py
```

Script mặc định Qwen `qwen3.5-27b-awq`, tối đa 10 PUT/task, lấy đủ 378 task.
Giữ task đã có PUT; sinh task chưa có và thử lại task có programs rỗng.
Lưu sau từng task; không refill task đã có ít hơn 10 PUT hoặc chỉ có PUT fail base tests.
Mỗi lần gọi tạo một Prefect run local và folder output riêng, có source snapshot,
config, progress, report, worker.log. Không ghi đè source cohort.
Sau khi ngắt, dùng `--source <output-cohort-của-run-trước>` để giữ kết quả mới nhất.
Server Prefect local cần đang chạy; không tự launch generation từ preset.
