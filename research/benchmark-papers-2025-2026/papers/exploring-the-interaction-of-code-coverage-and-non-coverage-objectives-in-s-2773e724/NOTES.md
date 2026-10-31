# Exploring the Interaction of Code Coverage and Non‐Coverage Objectives in Search‐Based Test Generation

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [Exploring the Interaction of Code Coverage and Non‐Coverage Objectives in Search‐Based Test Generation](https://doi.org/10.1002/stvr.70009)

Year/venue: 2025 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W4414839202

Discovery query: Defects4J; keyword hit is not dataset-use verification.


## Full-text/public-source audit — 2026-10-15

Read the complete 31-page Chalmers-hosted published PDF. Study uses EvoSuite 1.2.1 whole-suite GA on 93 Defects4J 2.0.1 faults/14 Java projects, six objective settings, 180/300 s budgets, 10 trials each (11,160 generated suites). It compares Branch Coverage with Exception Count, Output Coverage, and Execution Time. Multi-objective configurations maintain near-identical branch coverage and detect more faults on average than goal-only settings, but gains over Branch Coverage alone are not statistically significant. Defects are run on fixed code then generated tests are applied to buggy versions; this is not bug-report reproduction/LLM or root-cause analysis.

Author EvoSuite fork and Defects4J fork are public and directly linked in paper. EvoSuite fork `207c2b1d7da86cb93268d37e08cb71cd1fd18e3e` differs from upstream across 72 files, including ExecutionTime fitness; license LGPL-3.0. Defects4J fork pinned `00b83d3bb1c02a6ed599b90fa342a6bdea1ecc8f`, MIT. Matching-title Zenodo package 11047568 is open and includes algorithms/data (`defects4j.zip`, 5.6GB); published PDF instead cites 11047567, so exact archive identity is unresolved. Good conditional supporting baseline; a full rerun is large, but results are public. No code run or edited. See `audit/reviews/051.json`.
