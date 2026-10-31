# Hierarchical Knowledge Injection for Improving LLM-based Program Repair

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Hierarchical Knowledge Injection for Improving LLM-based Program Repair](https://arxiv.org/abs/2506.24015)

Year/venue: 2025 arXiv

Dataset: BugsInPy; 314 bugs

Input setting: bug/repository/project knowledge layers

Model: Llama3.3, GPT-4o-mini

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Structured context layers; 6 bug types để analyze scope.

Limitation: APR task. Historical fixes/repo history context cần temporal leakage audit; source release chưa verified.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc hết arXiv v3 (11,943 words, 853-line HTML extraction; methodology, all RQs, threats, conclusion, references). Đây là APR/context-injection paper, không sinh tests; dataset BugsInPy 314 single-function fixes được phân loại thủ công thành sáu nhóm (Program Anomaly 187, Network 47, Configuration 34, GUI 28, Performance 16, Permission/Deprecation 2). Ba lớp knowledge: bug, repository (co-change files, dependencies, recent pre-fix commits), project (docs, resolved issue history). Llama 3.3 đạt 79%, GPT-4o-mini 73%; all-at-once giảm còn 65%/48%. Dataset này phù hợp làm background cho bug-type analysis, nhưng labels không phải causal diagnosis từng bug.

Đã xác minh author package public tại HEAD `74df4532846f0f903907a168b02196196ca61364`. Có 4 notebook code, 314-bug folders với prompt/patch/extracted context, annotation CSV, 8 result CSVs và complexity metrics. Download/hash-only parse cho thấy annotated CSV 314 rows, type counts khớp Table I; cả 8 result CSV đều 314 rows. README nói rõ replication package. Không có license code ở root; CC BY 4.0 của paper không tự cấp license cho repo. README requirements không pin version/lockfile. Model rerun cần GPT API và/hoặc 70B Llama resources; không gọi API/chạy notebook.

Manual annotation kappa tăng .45 lên .8 sau calibration, rồi 214 bugs chia đôi để annotate độc lập. Paper dùng perfect function localization và broad issue-type taxonomy, nên không chứng minh fault diagnosis hoặc end-to-end test generation. Verdict: public implementation, exact regeneration conditional. Xem `audit/reviews/029.json` và `public_evidence/source-audit.json`.
