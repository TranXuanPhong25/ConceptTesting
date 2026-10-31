# Empirical Evaluation of Generalizable Automated Program Repair with Large Language Models

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Empirical Evaluation of Generalizable Automated Program Repair with Large Language Models](https://arxiv.org/abs/2506.03283)

Year/venue: 2025 arXiv

Dataset: Defects4J + BugsInPy + BugsJS + BugsPHP

Input setting: buggy code with varying localization/context

Model: 13 models including Qwen2.5-Coder, Llama3.3, DeepSeek-R1 distills, GPT-4o, Gemini2.0 Flash

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Cross-language và imperfect-localization controls useful for generalization.

Limitation: APR task, không phải test generation base. Public artifact not verified.

Local reproduction: **not performed**. No author source modified.


## Full-text and artifact audit — 2026-10-15

Đã đọc toàn bộ arXiv v2 (12,406 words; §1–8, tables, prompts, threats và references). Đây là APR performance study, không sinh test và không gắn nhãn underlying root causes. Dùng Defects4J, BugsInPy, BugsJS, BugsPHP; prompt có code, failing-test diagnostics, perfect line localization, hoặc FLACOCO top-3 functions. RQ1 13 models, n=15 generations/task; RQ2 sampling 100 tasks/benchmark.

ArXiv Data Availability trỏ Figshare share link 457.69 MB (CC BY 4.0). Page metadata hiện nói item shared privately; web click download trả 403 và anonymous HEAD 202/no content. Paper v2 nói scripts sẽ được thêm vào reproduction package sau acceptance; chưa tìm thấy source repo/scripts qua author page/search. Dataset counts chưa reconcile: Defects4J prose854 vs Table1 845; BugsJS453 vs513; BugsPHP513 vs452; BugsInPy prose 82 reproducible single-hunk RQ1 vs Table1 132. Có thể là filtered/version cohorts nhưng paper không giải thích rõ trong đoạn đã đọc.

Verdict: partial artifact, reproduction conditional; no execution or API calls. Useful supporting context for D4J/BugsInPy reproducibility and imperfect-FL protocol, but not main test-gen/root-cause paper. Evidence in `audit/reviews/028.json`, `public_evidence/source-audit.json`.
