# Knowledge-Guided Synthetic Bug Feedback for LLM-Based Unit Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Knowledge-Guided Synthetic Bug Feedback for LLM-Based Unit Test Generation](https://arxiv.org/abs/2607.11573)

Year/venue: 2026 arXiv

Dataset: 172 Defects4J method tasks; historical KB from five Java bug sources

Input setting: correct-version code; buggy counterpart reserved for final evaluation

Model: GPT-5.4; temperature 0.1

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Historical bug → semantic mechanism + structural applicability → executable injected feedback. Rất gần concept direction.

Limitation: No public source verified; fixed-input setting; substantial KB construction/injection cost. GPT-5.4 pipeline chưa được chạy. Không nhầm với paper KITE khác đã lưu trong repo.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:25:55.792335+07:00

Highest-priorityclosepriorworkforconcept/mechanismnovelty;keepoutofimmediatereproductionbaseuntiloriginalKB/source/evaluatoravailable. Separatefixed-referencegenerationfrombuggyinputresearch.

Blockers: Noauthorimplementation,1325mechanismKB,172taskmanifest or evaluatorreleaseverified; Currentpaperdoesnotspecifyretrievalembeddingcheckpoint,thresholds,constructionreviewdetails or executablegatewitnessprocedure sufficientlyforexactrun; Usesfixedreferencecodeandrelatedtests;notbuggy-inputunknown-bugdiscovery; RBDRall172tasksbutcoverage/mutation/tokencostoncommon-successsubset;ablationfullmetricsdifferentcohortasexplicitlynoted; Approximately177k–225ktokens/method;noAPIbudgetspendauthorized; Noindependentmatched-budget placebo/no-mechanismcontrol established beyondreportedablations;onebackend,stochasticrepetition/confidenceevidenceabsent; Noauthorcode/modelrunorreimplementation

Sources: https://arxiv.org/html/2607.11573v1, https://arxiv.org/abs/2607.11573
