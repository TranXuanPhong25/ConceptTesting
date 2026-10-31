# Issue2Test: Generating Reproducing Test Cases from Issue Reports

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [Issue2Test: Generating Reproducing Test Cases from Issue Reports](https://arxiv.org/abs/2503.16320)

Year/venue: 2026 ICSE; preprint 2025

Dataset: SWT-Bench Lite; 276 issues

Input setting: buggy repo + issue + retrieved context + execution feedback

Model: GPT-4o-mini-2024-07-18 primary; Llama3.3/Claude3.5 comparisons

Artifact: https://github.com/test-generation/issue2test

License: No software license verified

Concept hook (research judgment): Issue comprehension → failure-specific hypothesis → test; thuận lợi để chèn concept.

Limitation: Original model snapshot phải kiểm tra availability trước run. Repo has generation and Docker modules; full runs not performed here.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc toàn bộ arXiv v4 (10,980 words; §1–6, figures/tables/algorithm, discussion, threats, references). Paper dùng SWT-Bench Lite 276 issue và subset SWE-bench Verified 90; không đánh giá Defects4J/BugsInPy. Source chính thức có generation, feedback loop, localization, dataset, Docker per-instance evaluation và cached outputs; HEAD `ff947aec0dd8189514edf91cf4d4d279cb062092`. Không có root license.

Exact paper main model là GPT-4o-mini-2024-07-18, nhưng config công khai mặc định alias `gpt-4o-mini`; YAML để path tuyệt đối, `MAX_ITERATIONS=3`, còn paper Algorithm 1 và code feedback loop default dùng 20. Paper v4 có số liệu không nhất quán giữa abstract/introduction/Table 2/conclusion (GPT headline 30.4%/84 so với Claude 32.9%/91; số unique 20 hay 28, relative improvement 16.3/40.1% hay margin 8.7pp). Exact rerun vì vậy conditional, cần xác định đúng experimental config/version và model snapshot. Không gọi API, không chạy source.

Verdict: public implementation; reproduction conditional. Fit cao cho SWT-Bench issue reproduction và concept/hypothesis-guided oracle; không phải kết quả trên Defects4J/BugsInPy. Evidence trong `audit/reviews/021.json`.
