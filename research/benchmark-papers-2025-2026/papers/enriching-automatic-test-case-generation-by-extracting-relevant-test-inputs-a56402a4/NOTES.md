# Enriching automatic test case generation by extracting relevant test inputs from bug reports

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [Enriching automatic test case generation by extracting relevant test inputs from bug reports](https://doi.org/10.1007/s10664-025-10635-z)

Year/venue: 2025 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W4408838832

Discovery query: Defects4J; keyword hit is not dataset-use verification.


## Full-text and source audit — 2026-10-15 (#42)

Read arXiv v2 (26,434 words) and fetched the final Springer publisher PDF through the German National Library mirror (60 pages; published 2025-03-24, CC BY 4.0). BRMiner extracts strings/numeric literals from bug reports with Javalang and regex, then filters with GPT-3.5 ToT and injects selected values into modified EvoSuite; Randoop is also tested. Defects4J 2.0 includes 809 bug cases and 22,111 reports across 17 projects; 7,855 human-test literals yield 1,129 exact report/test overlaps. Main run reports BRMiner AllLitLLM 313 EvoSuite detections vs NoLit 295 and 111 Randoop vs 93; 58 unique bugs across configurations, 13 exclusive to BRMiner in the full-report sample.

Publisher text and author ORBilu profile link an anonymous 4Open repo and GitHub `Cwendkuuni/BRMiner`, but 4Open API is 401 `not_connected`, `git ls-remote` returns not found, and GitHub is 404. Thus no BRMiner implementation/source license is accessible; source is restricted/unavailable and exact reproduction is not feasible currently. Reproduction also uses GPT-3.5-turbo (temp .7), modified EvoSuite 1.2.1/Randoop 4.3.1, Defects4J, five 3-minute runs and 640GB RAM. Metric caveat: relevant inputs are operationalized through exact literal overlap with post-fix human tests, even though authors acknowledge non-identical values/patterns can still be relevant. No code/model run.
