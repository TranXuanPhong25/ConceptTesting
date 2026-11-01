# Readability audit — 2026-10-31

User quen đọc Java và thấy source Python khó đọc vì tên biến ngắn, cách viết gộp.
Audit chỉ xét source runtime viết cho `final/`; không tính tests, PUT do model sinh,
dataset gốc, dependencies hay validation fixtures. Không sửa source/checkpoint.

## Kết quả

- 18 runtime files; 13 files có binding tên dài 1–2 ký tự.
- 162 vị trí binding như vậy. Đây là số lần xuất hiện trong AST, không phải 162
  biến độc lập và không phải tự động là 162 lỗi.
- 136 comprehensions/generator expressions. Nhiều đoạn ngắn vẫn rõ; vấn đề là các
  expression nhiều bước đi cùng tên biến mơ hồ.
- Nặng nhất: `benchmark.py` có43 short-binding occurrences, `analysis.py` có40;
  `worker.py` có16, `cohort.py` có13, `run.py` có12 trong experiment hiện tại.
- Không thấy semicolon để gộp statements hoặc compound blocks viết một dòng trong
  phạm vi audit. Khó đọc chủ yếu đến từ naming, expressions dày và function dài.

Inventory kèm source hashes: `readability_inventory.json`.

## Những chỗ nên đổi

| Vị trí trong concept_reference_v1 | Hiện tại | Tên rõ nghĩa hơn |
|---|---|---|
| benchmark.py:141 | `a`, `b` | `first_reference_result`, `second_reference_result` |
| benchmark.py:197 | `a`, `b` | `left_input_indices`, `right_input_indices` |
| benchmark.py:201 | `da`, `db` | `left_detected_count`, `right_detected_count` |
| benchmark.py:209 | lại dùng `a`, `b` cho NumPy arrays | `left_detection_rates`, `right_detection_rates` |
| analysis.py:112 | `a`, `b` | `source_line`, `target_line` |
| cohort.py:124, run.py:101 | `mp` | `manifest_path` |
| run.py:124 | `fp` | `generation_freeze_path` |
| worker.py | `fn`, `ns`, `cov` | `candidate_function`, `execution_namespace`, `coverage_collector` |

Ở `matched_pair`, cùng tên `a/b` lần lượt mang ý nghĩa input indices rồi detection
rate arrays; đọc tiếp function phải nhớ lúc nào ý nghĩa đã đổi. Đây là vấn đề naming
cụ thể, không phải vấn đề người đọc không quen Python.

`arm_indices` ở benchmark.py:156–157, `failing`/`unstable` ở:172–174 và expression
đóng băng input hashes ở run.py:122 nên tách thành loop với tên trung gian rõ nghĩa.
`report` hiện trộn đọc artifact, thống kê, diagnostics, statistics và render Markdown;
nên chia theo các trách nhiệm đó khi làm bản refactor.

## Style áp dụng từ nay

- Giữ Python `snake_case`, đặt tên theo ý nghĩa nghiệp vụ thay vì viết tắt tùy ý.
- Ưu tiên `task`, `program`, `input_record`, `reference_result`, `file_path`.
- Mỗi bước tính toán có biến trung gian; dùng `for`/`if` tường minh cho logic nhiều bước.
- Comprehension đơn giản vẫn dùng được; tránh nesting hoặc nhồi nhiều phép biến đổi.
- Type hints cho interface và các collection quan trọng; helper functions có một việc.
- Refactor ở folder mới theo rule repo, dùng lại frozen PUT cohort; giữ nguyên prompt,
  seed, kết quả, artifact keys và kiểm tra behavior trước khi thay entry point.
