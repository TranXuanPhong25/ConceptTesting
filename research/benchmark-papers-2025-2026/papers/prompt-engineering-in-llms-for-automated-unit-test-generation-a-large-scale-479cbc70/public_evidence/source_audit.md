# Full-text and public-source audit — #91

Checked 2026-10-15. Full final 58-page article read from the author's institutional repository; no code was executed.

## Full paper identity and access

- 2026 version: Ouédraogo et al., “Prompt engineering in LLMs for automated unit test generation: A large-scale study,” EMSE 31(4), Article 103, DOI `10.1007/s10664-026-10840-4`, published 28 March 2026.
- Full author manuscript retrieved from ORBilu, University of Luxembourg: `https://orbilu.uni.lu/bitstream/10993/68099/1/s10664-026-10840-4.pdf` (58 pages, SHA-256 PDF `6649619590661b82066101689ed139a3df5ddcf7d6522c2fbab5a1b003596b36`; extracted text SHA in `reviews/091.json`). This is an institutional author-hosted PDF; Springer page in cache was only a paywall/abstract page.
- ORBilu metadata confirms peer review, DOI, publication date and links this article to the artifact below.
- Earlier arXiv `2407.00225` has a different earlier title/version and reports fault-detection experiments. Do not use its bug-detection experiment as evidence for the final 2026 article.

## Author-linked replication package check

The final paper Data Availability statement links anonymous 4open repository `LLM4TS-0F76`. Read-only repository API confirmed public files and MIT `LICENSE`. Repository options report source commit date 2024-09-26 / last update 2024-09-30. Its saved [README](author_artifact_README.md) identifies the package as a 2024 study titled “Exploring Prompt Engineering in LLMs for Automated Unit Test Generation,” describes 216,300 tests, datasets, dependencies and generated outputs.

Inventory observations from public 4open API:

- `Datasets/`: CMD JSON (131 B), Defects4J dataset JSON (~4.24 MB), SF110 dataset JSON (~1.39 MB).
- `Dependencies/`: 391 JAR/library files.
- `Generated-test-suites/`: only visible top-level roots `GPT-3.5-Turbo` and `EvoSuite` (not all models claimed by paper/README).
- `Experiments-Scripts-And-Results/`: only visible `RQ1` and `RQ2` directories plus preprocessing; no `RQ3`, `RQ4`, or `Test-Generation` directories were returned by the current public tree, although README claims these folders exist.
- RQ1 folder includes small extraction/MSR/CSR CSV summaries for several models. RQ2 includes compilability, Checkstyle and PMD subfolders.

The public package is relevant and contains datasets/results/tools, but its README/version and source date predate the final 2026 article; visible package tree is incomplete relative to its own README and final paper. It is not a stable complete implementation for exact 2026 replication. MIT applies to package code, while bundled dependencies and source datasets retain upstream terms. The final manuscript says the author-accepted version is CC BY 4.0; Springer version of record is under exclusive publisher terms.

## Experimental scope caution

The final article uses Defects4J but in §5.2.1 expressly states that it did not implement paired buggy/fixed regression testing, exception-oriented fault detection, or mutation analysis. Future work would add those. Elsewhere §6.5 contains a contradictory sentence claiming mutation testing was integrated, but no mutation-score RQ/table/results appear. Treat the explicit limitation and actual RQ/result sections as authoritative, while flagging the manuscript inconsistency. It is not an issue-to-reproduction/F2P baseline.
