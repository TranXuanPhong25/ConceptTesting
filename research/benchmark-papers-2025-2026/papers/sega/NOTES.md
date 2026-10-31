# Uncovering Business Logic Bugs via Semantics-Driven Unit Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: X.

Paper/record: [Uncovering Business Logic Bugs via Semantics-Driven Unit Test Generation](https://arxiv.org/abs/2604.23509)

Year/venue: 2026 ISSTA experience paper

Dataset: Private industrial Go repositories

Input setting: PRDs + production repo

Model: Not audited

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Normative business semantics là concept source.

Limitation: Paper explicitly says Defects4J/BugsInPy are poor proxies and evaluates industrial Go. Metadata keyword hit không phải dataset use.

Local reproduction: **not performed**. No author source modified.


## Full-text and artifact audit — 2026-10-15

Đã đọc toàn bộ arXiv v3 (12,356 words). SeGa là semantics-driven Go unit-test generation cho business logic bugs: PRD → functionality (intent + requirements) → per-method business scenarios (preconditions/action/expected outcomes/constraints) → test. Bốn private production repos có 60 labeled P0–P1 bugs; deployment thêm 6 private repos, 16 new bugs confirmed/fixed. Tests chạy trên MR/current code; failure/panic khớp annotation là true positive. Không phải Defects4J/BugsInPy/SWT historical reproduction.

Public repo ở HEAD `be63f3e87c828a71a3a0b39f75156963ddebc068` có core semantic agent, prompts, Go AST tools, Swerex/Docker runtime và desensitized examples. README xác nhận đây chỉ là core implementation; PRDs, industrial repositories, 60 labels và deployment results không phát hành. SeedCode API/model exact không public, dù source có alternative Claude/DeepSeek configs. Không có root license. `.env` tracked có credential-named fields; values withheld and not used. No source run/API calls.

Very high concept novelty relevance: requirement/functionality/scenario DSL is close prior art for concept-guided test obligations; reproducibility of headline study is not feasible due private industrial data and proprietary model. Evidence in `audit/reviews/033.json`, `public_evidence/source-audit.json`.
