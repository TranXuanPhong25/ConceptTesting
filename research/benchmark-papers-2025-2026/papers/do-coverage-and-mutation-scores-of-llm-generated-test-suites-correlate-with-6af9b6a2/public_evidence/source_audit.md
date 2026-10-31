# Public source and reproduction audit — #74

Checked 2026-10-15. No source code was executed.

## Identity and author relationship

- Paper: [arXiv:2607.22880](https://arxiv.org/abs/2607.22880), DOI `10.1145/3832093`.
- The paper's Data Availability section links `https://github.com/drixs2050/Cov_mut_bug_detect_correlation`.
- The repository README names the same paper/authors/venue/DOI; LICENSE copyright names Zhao, Zhou and Cohen.
- GitHub API: public repository, default branch `main`, HEAD `4bc2ed63917557a8c879e6c733b8fa41c15b9871` dated 2026-07-24; 2,688 tree entries (148,436,496 bytes of blobs, including bundled libraries, test outputs and data).
- Main repository license: MIT. NOTICE documents LLM4UT adaptations under Mulan PSL v2, CodeCover/JaCoCo/PIT/JUnit/Apache component licenses, and Defects4J-derived source snippets under upstream project terms.
- The repository README and article contain inconsistent Zenodo DOI suffixes. Public Zenodo record `21429529` identifies this exact replication package/title/authors and points back to GitHub. Prefer the stable repository URL for citation and pin the Git commit.

## Substantive artifact inspected

Static inspection at the pinned HEAD covered README, LICENSE, NOTICE, `environment.yml`, `data/configuration.py`, `checkout_all.sh`, the prompt example, `UT_Test_Generation.ipynb`, and `analyze_sampled_fixed.ipynb` / `analyze_sampled_buggy.ipynb`.

The author README lists processed per-focal-method CSVs for fixed and buggy inputs and fixed-size 3/5/10 variants, with compilation, bug-detection, coverage and mutation columns. The two analysis notebooks load these CSVs, perform the 1,000-sample/100-method analyses and need no Defects4J installation or API key. They provide the easiest route to evaluate/recalculate the paper's statistics. README warns some fixed-analysis camera-ready boxplots use values transcribed from the paper's tables rather than recomputing those values from loaded data.

The generation notebook uses an API key and an `o4-mini` call (reasoning effort `high` in its cells). README documents changing the model/client for a different model. It does not identify immutable model snapshots. Thus Qwen can be tested as a new model after adapting the client, but cannot recover the original study's generations exactly.

The documented full generation route requires Defects4J v3 and Java 11; checking out buggy/fixed versions; building prompts for 318 focal methods; model calls; compiling and running generated JUnit suites on both versions; and measuring with JaCoCo, CodeCover MC/DC, and PIT mutation. The repository bundles many dependencies and tools. This is substantial; do a bounded subset for an independent Qwen evaluation.

## Reproduction verdict

**Conditional.** Public processed data and analysis code make the reported statistical analysis substantially reproducible without new generation or model cost. Exact full reproduction of generation + all measurements is conditional on environment/setup, API/model access and reconstructing exact original model versions. A small number of plot cells rely on table-transcribed values. No execution or reproduction was performed in this audit.

Primary source references:

- [Pinned GitHub tree](https://github.com/drixs2050/Cov_mut_bug_detect_correlation/tree/4bc2ed63917557a8c879e6c733b8fa41c15b9871)
- [README / reproduction instructions](https://github.com/drixs2050/Cov_mut_bug_detect_correlation/blob/4bc2ed63917557a8c879e6c733b8fa41c15b9871/README.md)
- [LICENSE](https://github.com/drixs2050/Cov_mut_bug_detect_correlation/blob/4bc2ed63917557a8c879e6c733b8fa41c15b9871/LICENSE)
- [NOTICE](https://github.com/drixs2050/Cov_mut_bug_detect_correlation/blob/4bc2ed63917557a8c879e6c733b8fa41c15b9871/NOTICE)
- [Zenodo package record](https://zenodo.org/records/21429529)
