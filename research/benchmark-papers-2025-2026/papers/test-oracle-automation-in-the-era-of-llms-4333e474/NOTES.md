# Test Oracle Automation in the Era of LLMs

Reviewed 2026-10-15. Full 5,912-word article read (SHA-256 `158c7467755e242976dbe0d6190cf58fd3670b9886628033963be42889c3d23c`). Final 2025 publication: TOSEM, DOI [10.1145/3715107](https://doi.org/10.1145/3715107); arXiv full text is v1, May 2024, CC BY-NC-SA 4.0.

This is a perspective/vision paper, not an empirical study. It discusses LLM-generated test assertions, contracts and metamorphic relations; emphasizes oracle false positives/false negatives; and proposes an “assurance” layer to validate or strengthen generated oracles. It warns about oracle leakage: the Commons Collections/Defects4J example shows ChatGPT reproducing existing assertions from public tests. Defects4J is illustrative only; there is no dataset experiment, code, model evaluation or reproduction package.

**Relevance:** high conceptual grounding for the thesis oracle: separate behavior expected from code-implemented behavior, detect false-positive assertions, and account for benchmark memorization. **Use:** related-work/threat model. It is not a runnable baseline and does not report a root-cause method. No author source found, no code/model run.

Structured review: [`audit/reviews/093.json`](../../audit/reviews/093.json); source check: [`public_evidence/source_audit.md`](public_evidence/source_audit.md).
