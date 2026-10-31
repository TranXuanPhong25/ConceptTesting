# ReProAgent: Tool-Augmented Multi-Stage Agentic Generation of Bug Reproduction Tests from Issue Reports

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [ReProAgent: Tool-Augmented Multi-Stage Agentic Generation of Bug Reproduction Tests from Issue Reports](https://arxiv.org/abs/2607.09123)

Year/venue: 2026 arXiv

Dataset: SWT-Bench

Input setting: localization → root cause analysis → planning → generation

Model: GPT-5-mini per author leaderboard; paper/config consistency audit pending

Artifact: https://github.com/iSEngLab/ReProAgent

License: License not verified

Concept hook (research judgment): Root-cause-analysis stage là vị trí trực tiếp cho concept cards.

Limitation: Tool/retrieval effects cần control; chưa pin exact paper model settings hay reproduce reported scores.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc toàn bộ arXiv v1 (10,854 words; method, RQ1–RQ3, discussion, threats và references). ReProAgent là hướng rất gần concept-guided bug-revealing tests: root-cause report ghi execution path, trigger conditions và expected assertion; sau đó triadic review test với issue và execution. Dataset là SWT-Bench, không phải Defects4J/BugsInPy.

Repo tác giả public tại HEAD `99b112b9e1de88a451d24e273121f8bceaf3c8b4`, có source, tests, uv.lock, Docker eval route và predictions/results cache; không thấy LICENSE ở root. Config dùng alias GPT-5-mini, không có version pin; README cần OpenAI-compatible API endpoint. Không gọi API hay chạy code.

Có các denominator/report discrepancies cần giải quyết: cache có 267/276 Lite và 431/500 Verified predictions, paper không giải thích phần thiếu; Table 8 Verified localization groups chỉ 430; cached Verified JSON báo `completed_instances=0` nhưng resolved=303, unresolved=128, errors=0. Report JSON Lite có completed=261 so với 267 output rows. Vì vậy full rerun conditional; cached prediction evaluation có thể kiểm tra độc lập nếu sau này được yêu cầu. Paper nêu average $0.14/instance; 698 items tương đương khoảng $97.72 theo trung bình paper (ước tính, chưa chi).

Verdict: public implementation; reproduction conditional. Concept fit rất cao; ưu tiên SWT-Bench pipeline/related work, không phải Defects4J/BugsInPy base. Evidence: `audit/reviews/022.json`.
