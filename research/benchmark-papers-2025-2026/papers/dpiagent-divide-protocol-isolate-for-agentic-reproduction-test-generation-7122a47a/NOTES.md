# DPIAgent: Divide, Protocol, Isolate for Agentic Reproduction Test Generation

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [DPIAgent: Divide, Protocol, Isolate for Agentic Reproduction Test Generation](https://doi.org/10.48550/arxiv.2608.23341)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W7204187346

Discovery query: SWT-Bench; keyword hit is not dataset-use verification.


## Full-text/public-source audit — 2026-10-15

Read all 14,550 extracted words, including the appendices. DPIAgent is the strongest thematic fit so far for the requested root-cause-informed reproduction workflow: it requires a handoff with bug location, explicit root cause, expected/actual behavior, trigger/reproduction strategy, examined tests, and a concrete test plan; the next phase has only test-edit/execute tools. On the 433-case Python SWT-Bench Verified cohort, results average three runs over GPT-5-Mini, GPT-5, and Claude-Opus-4.5; DPI-only success is 74.28%, 81.76%, 78.98%, and optional candidate selection reaches 82.32%, 86.17%, 81.38%. The optional selector uses six issue variants and three SWE-Agent surrogate patches per issue. The evaluation includes function-level localization, but root-cause fields are free-form and there is no separate root-cause accuracy/taxonomy metric.

The paper links a project page, but the page has no code/data link. Checked the first author’s public GitHub profile and repositories, likely related SWE-agent/Echo/RPG-ZeroRepo repositories, exact DPIAgent/Microsoft repository routes (404), and public search; no DPIAgent implementation, stable commit, predictions, or runs found. Public SWT-Bench is not the DPIAgent artifact. Exact reproduction is not feasible without the authors’ implementation; reimplementing has not been authorized. Project and evidence: `public_evidence/source-audit.json`; review `audit/reviews/048.json`.
