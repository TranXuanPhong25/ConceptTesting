# UnitCon: Synthesizing Targeted Unit Tests for Java Runtime Exceptions

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [UnitCon: Synthesizing Targeted Unit Tests for Java Runtime Exceptions](https://doi.org/10.1145/3729362)

Year/venue: 2025 FSE

Dataset: Java runtime-exception subjects; exact Defects4J use pending

Input setting: target location + static analysis

Model: No LLM required

Artifact: https://github.com/prosyslab/unitcon-artifact

License: Artifact license not audited

Concept hook (research judgment): Sufficient failure conditions + search pruning; support for concept-directed synthesis.

Limitation: Source/Zenodo artifact verified, but target dataset use not established. Full archived package large; original minimal experiment still hours.

Local reproduction: **not performed**. No author source modified.


## Full paper and source review — 2026-10-15 (#36)

Full FSE 2025 paper (22 pages; 12,516 extracted words) read from the author artifact commit. UnitCon synthesizes a public-method call sequence that triggers a runtime exception at a supplied location. Infer-derived path/error conditions prioritize candidates; method summaries prune semantically redundant candidates. RQ1 has 198 cases from Bears, Genesis, NPEX, VFix and Defects4J (80 cases), with 104 reproduced in 10 minutes; RQ2 applies to 51 current open-source repos and reports 21 newly found NPE bugs from manual review of 26 of 256 generated crashes.

The artifact repo is public at commit `f7ab2e23a57e12060b50af91cf7098dfc347b9ff`, BSD-3-Clause, with submodule `unitcon` and data, Dockerfiles, scripts, expected bug metadata, and result archives. The README documents runnable full and minimal routes. Full replay is conditional because authors report 512GB RAM/188GB storage and extremely long baseline runs; 8-project minimal route is estimated two days for RQ1. No run was performed. Excellent targeted-error/root-condition support, but no LLM and only runtime exceptions.
