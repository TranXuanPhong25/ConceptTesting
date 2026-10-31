# Escaping the Self-Repair Trap: Improving Test Oracle Generation via Dual-Context Awareness

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: X.

Paper/record: [Escaping the Self-Repair Trap: Improving Test Oracle Generation via Dual-Context Awareness](https://arxiv.org/abs/2608.05917)

Year/venue: 2026 ASE

Dataset: Regression-oracle/mutation subjects; exact target benchmark not verified

Input setting: current code assumed correct + selectively retrieved runtime states

Model: Exact model/config not audited

Artifact: https://zenodo.org/records/21357436

License: Artifact access/license not verified

Concept hook (research judgment): Self-repair degeneration và static/dynamic context hữu ích về reasoning.

Limitation: No Defects4J use found in inspected paper; không tính là exact-dataset paper. Correct-current-version oracle setting.

Local reproduction: **not performed**. No author source modified.


## Full-text and artifact audit — 2026-10-15

Đã đọc toàn bộ arXiv v2 (10,169 words). DCAware là regression-oracle completion: test prefix có sẵn, current implementation được xem là expected; không phải generation test cho historical bug. Pipeline gồm static context folding, LLM-chosen JDB queries để lấy runtime state, rồi generate oracle một lần không repair. Đánh giá bằng execution Pass Rate và PIT Kill Golden trên TECO-derived 500 prefixes/38 Java projects, mutation-valid N=362. GPT-5-mini đạt 88.2% pass/78.17 KG; Qwen3-Coder-30B đạt 80.8%/73.2.

Đã xác minh author Zenodo artifact `21357436` / concept DOI `19238006`, CC BY 4.0; archive khai báo MD5 `2fbe9471653b1e5093e317ab3db3c619`. Range-based ZIP central-directory inspection (không tải archive đầy đủ/extract/run) thấy 18,134 files, 1.69GB expanded; source MIT, README/requirements/status, JavaServer, Docker runner, dataset, cached outputs. DCAware results có 500 outputs cho mỗi model; ChatAssert 494 mỗi model. Script `context_aware.py` mặc định Qwen3-Coder-30B, temp=.2. Paper setup: 1 A100 40GB, Java8/21, Maven, Docker, PIT; GPT5-mini qua Azure. Artifact có smoke tests không cần model và result-print scripts. Paper nêu GPT5-mini cost $0.87/500. Không gọi API/không execute source.

Rất gần oracle thesis qua “Self-Repair Trap” và distinction execution success vs fault-revealing strength; nhưng không phải SWT/Defects4J/BugsInPy issue reproduction. Verdict public implementation, full reproduction conditional on infra/model. Evidence `audit/reviews/032.json`, `public_evidence/source-audit.json`.


### Artifact linkage correction — 2026-10-15

The paper links both `SecurityLab-UCD/CNTG` and `CGNTG`; these are component repositories (CNTG invariant generation, CGNTG PromptFuzz seed generation), neither with a declared GitHub license. The complete DCAware implementation/data/results are in Zenodo 21357436 (CC BY 4.0), whose archive contains an MIT LICENSE. Its STATUS points to prior concept DOI 19238006; the API resolves to the latest version/archive 21357436. Archive was only range-inspected, not downloaded/executed.
