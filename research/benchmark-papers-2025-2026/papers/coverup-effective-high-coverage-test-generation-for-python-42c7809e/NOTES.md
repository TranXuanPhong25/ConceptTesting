# CoverUp: Effective High Coverage Test Generation for Python

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [CoverUp: Effective High Coverage Test Generation for Python](https://doi.org/10.1145/3729398)

Year/venue: 2025 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W4411450140

Discovery query: BugsInPy; keyword hit is not dataset-use verification.


## Full paper and artifact review — 2026-10-15 (#37)

Read full arXiv v4 (11,328 words). CoverUp uses coverage-guided prompt construction, extra source via get_info, tests execution/isolation and up to two follow-up prompts to increase Python line/branch coverage. Its CM suite has 425 modules from 35 open-source projects selected from projects used in prior BugsInPy/Pynguin evaluation; it is not BugsInPy bug instances or buggy/fixed pairs. PY has 84 modules and MT 163 HumanEval functions. It measures regression coverage, not fault-revealing oracle quality or root cause.

Public Apache-2.0 CoverUp and evaluation repositories pinned at `d9ca25b...` and `f317319...`; replication package includes Docker run scripts, data, generated tests, logs and cached results. Exact config pins GPT-4o-2024-05-13, temp 0, with 5 test repeats. Paper reports $399 for main CM run; repository README estimates full rerun at thousands of dollars. LiteLLM config can evaluate another model without altering source, but results are not exact reproduction. Static inspection only; no API/code run.
