# Author-source audit — #73 CATGen

Checked 2026-10-15. No code or model was executed.

## Verified source identity

- Paper: [arXiv:2607.19682v1](https://arxiv.org/abs/2607.19682), title “Context Matters: Improving the Practical Reliability of LLM-Based Unit Test Generation.”
- The paper Data Availability section explicitly links `https://github.com/CATGen-repository/CATGen`; README names CATGen and this experience study. Author relationship is verified.
- GitHub API: public repo `CATGen-repository/CATGen`, default `main`, HEAD `b60476d34fb3b130dea653588810e482d30fa13d` (commit date 2026-03-27), 62 tree entries, 1,663,436 blob bytes. GitHub metadata has no SPDX license; no LICENSE file in tree.
- Paper license: CC BY 4.0. This is distinct from the code repository's undeclared license.

## What is public

README says the full CATGen source and proprietary industrial benchmark cannot be released. The public tree contains README, design documentation (`docs/`), a JUnit5 skeleton sample, three anonymized example tests/focal methods, Java parser utilities, `core/LLM.py` wrapper, charts, a result workbook, and temperature CSVs. Inspected README, model configuration, context extraction, skeleton and static-repair documentation, LLM wrapper and complete tree.

Model documentation names nine local open-weight configurations, including Qwen2.5-Coder-7B-Instruct and Qwen2.5-Coder-32B-Instruct, deployed with vLLM 0.8.4/temperature 0. The wrapper reads configurable model/API-base settings, but the docs describe local vLLM. This verifies model availability/configuration information, not a runnable CATGen implementation.

## Missing for reproduction

The public tree does not contain full CATGen orchestration, generation/skeleton/repair source, Defects4J project/focal-method manifest, benchmark outputs for all comparisons, or a runnable Defects4J evaluation script. The result files are only an XLSX, temperature CSV and temperature totals; industrial data/results remain private. Therefore exact reproduction is **not feasible from the released public artifact**, and an evaluation with the user's Qwen would require implementing the absent CATGen pieces. No reimplementation is authorized or performed.

Primary source links:

- [Pinned GitHub repository](https://github.com/CATGen-repository/CATGen/tree/b60476d34fb3b130dea653588810e482d30fa13d)
- [Pinned README](https://github.com/CATGen-repository/CATGen/blob/b60476d34fb3b130dea653588810e482d30fa13d/README.md)
- [Model configuration docs](https://github.com/CATGen-repository/CATGen/blob/b60476d34fb3b130dea653588810e482d30fa13d/docs/llm-configuration.md)
- [Static repair docs](https://github.com/CATGen-repository/CATGen/blob/b60476d34fb3b130dea653588810e482d30fa13d/docs/static-repair-stage.md)
