# A Framework for Creating Non-Regressive Test Cases via Branch Consistency Analysis Driven by Descriptions

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [A Framework for Creating Non-Regressive Test Cases via Branch Consistency Analysis Driven by Descriptions](https://arxiv.org/abs/2506.07486)

Year/venue: 2025 arXiv

Dataset: Defects4J-Desc + QuixBugs-Desc

Input setting: buggy method + natural-language description

Model: DeepSeek-V3 in paper; repository includes Qianfan and DeepSeek scripts

Artifact: https://github.com/anonymous-user-2309/DISTINCT

License: No software license verified

Concept hook (research judgment): Description → corrected logic branches → consistency → distinguishing tests.

Limitation: NLDs được tạo từ repaired methods: supplied-spec setting, không chứng minh suy ra intent từ buggy code. Scripts use local paths; low compilation rate in reported Defects4J experiment.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:18:52.797297+07:00

Read substantive full paper; author source inspected at `ae28e128f36ae82fdadc8505af72a8ca6687bd28`. No code/model run.

Top concept-aligned Defects4J candidate, but reproduction readiness below clean artifact candidates. Use fixed-derived descriptions as privileged specification and report that explicitly.

Blockers: Public dataset count 442 differs from paper 441; exact evaluated manifest unresolved; Scripts contain author-local absolute paths and inconsistent helper import case: Test_one_Buggy vs distributed Test_one_buggy.py; Paper temperature 0 versus Qianfan code 0.1; Analyzer outer loop exits once tests pass; exact implementation of claimed repeated semantic consistency must be reconciled; Source repairs failing tests using project execution; confirm buggy/fixed project mapping before any evaluation to avoid deleting bug-revealing failures; README MIT badge has no accompanying license file; No local author evaluator/model run; publication tables have inconsistencies in baseline coverage and repeated headline metrics

Sources: https://arxiv.org/html/2506.07486v3, https://github.com/anonymous-user-2309/DISTINCT/tree/ae28e128f36ae82fdadc8505af72a8ca6687bd28
