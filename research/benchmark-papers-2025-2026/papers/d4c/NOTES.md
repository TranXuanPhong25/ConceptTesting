# Aligning the Objective of LLM-based Program Repair

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [Aligning the Objective of LLM-based Program Repair](https://github.com/CUHK-Shenzhen-SE/D4C)

Year/venue: 2025 ICSE

Dataset: Defects4J

Input setting: buggy code; direct debugging vs hunk repair

Model: Exact backbone/checkpoint not audited in this scan

Artifact: https://github.com/CUHK-Shenzhen-SE/D4C

License: License not verified

Concept hook (research judgment): Support paper về objective alignment; không phải test-generation base.

Limitation: Training/model availability audit needed; task is APR.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc toàn bộ arXiv v5 (11,573 words). D4C là APR method, không sinh test; đầu vào buggy function + documents/tests/error artifacts, output là cả refined function để align decoder-only completion objective và tránh exact hunk FL. Paper dùng Defects4J v1.2+2.0 (437 single-function bugs, 180 correct patches), DebugBench 590 tasks; GPT-4-0613 và local Mixtral-8x7B-Instruct-v0.1, 10 candidates, temp=1, 8xA100.

Public source chính thức tại HEAD `33f63280da92951cbb07078ccbfda06bee4e3a3e`, MIT; có generators/prompts/validator/dataset/archived outputs. Checksum-verify count-only cho archived outputs: 180 IDs trong `correct_id.txt`, 437 Defects4J eval rows, 1,770 rows mỗi DebugBench model eval. README cảnh báo Defects4J v3.0 đổi/deprecate case và DebugBench cần LeetCode cookies. No source run/API calls.

Study hữu ích cho FL/context analysis trên D4J, không có bug-cause labels hoặc generated-test evaluation. Reproduction conditional do GPT-4-0613 paid/historical, Mixtral cần resource lớn, benchmark version. Paper cost wording mơ hồ ($.023/patch, ×10 rồi gọi $.23 “entire dataset”; không kết luận total budget). Evidence: `audit/reviews/031.json`, `public_evidence/source-audit.json`.
