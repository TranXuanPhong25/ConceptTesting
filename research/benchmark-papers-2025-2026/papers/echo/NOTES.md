# Echo: Graph-Enhanced Retrieval and Execution Feedback for Issue Reproduction Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [Echo: Graph-Enhanced Retrieval and Execution Feedback for Issue Reproduction Test Generation](https://arxiv.org/abs/2603.07326)

Year/venue: 2026 arXiv

Dataset: SWT-Bench Verified

Input setting: graph retrieval + execution feedback

Model: GPT-4o, Gemini 2.5 family; exact configs pending

Artifact: https://github.com/EuniAI/Echo

License: License not verified

Concept hook (research judgment): Graph context có thể dùng để ground interprocedural obligation.

Limitation: RAG/index và Docker setup thêm complexity; model settings cần pin.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc toàn bộ arXiv v1 (11,135 words; §§1–9, tables, threat và references). Echo dùng SWT-Bench-Verified 433, không phải Defects4J/BugsInPy. Method ghép graph retrieval + regression tests, candidate patch của Prometheus, execution và dual-version refinement. Paper nêu 66.28% success, 287/433; 419 tasks được xử lý và 14 bị skip do giới hạn 500 bước. Cost table là $1.54/instance, không phải vài cent.

Source công khai tại HEAD `89e6e1ebd9d706adf21788f3febed95722d50a51`, gồm implementation LangGraph, Tree-sitter/Neo4j, Docker và dataset loader; không thấy root license. Repo tree không chứa logs/results/predictions/tests dù Data Availability nói các kết quả và logs đều public. Config `example.env` đặt GPT-4o cho cả model roles, khác paper Gemini 2.5 Pro/temp .5; không có lockfile đầy đủ. Source cần Python 3.11, Docker, Neo4j, PostgreSQL và LLM API. Không chạy code, không gọi API.

Code graph source định nghĩa 5 edges: file tree, AST, parent-child, text attachment và next text chunk; không có explicit function-call/import edges. Đây là khác biệt cần giữ rõ khi diễn giải claim về cross-file behavior. Paper cũng thừa nhận candidate-patch oracle có thể sai; stochastic run chỉ làm một lần. Exact reproduction conditional, tốn kém và phức tạp hơn AssertFlip/Issue2Test. Evidence `audit/reviews/023.json` và `public_evidence/source-audit.json`.
