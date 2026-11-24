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

Sinh thêm PUT đã được dừng khỏi đường code hiện tại. Các cohort và output lịch sử
vẫn giữ nguyên để đọc lại.
