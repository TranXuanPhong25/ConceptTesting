# Hybrid retrieval v4

Explicit opt-in API; the default public API remains structural v2. Uses the
unchanged 162-card corpus. Recovers duplicate-ID responses by keeping the first
row, applies the remaining v3 parser checks, then interleaves Qwen rank1 / v2
rank1 / Qwen rank2 / v2 rank2, retaining at most three unique cards. Invalid or
empty Qwen results fall back to v2. Truncated JSON is never semantically repaired.

```python
from python_bug_concepts.retrieval_v4.engine import retrieve
# Offline, no API calls:
result = retrieve(code, response=saved_response)
# Explicit live mode, endpoint from CT_RETRIEVAL_BASE_URL:
result = retrieve(code, out=cache_directory)
```

Each result includes the concept, instantiated where/how/what, origin and
`unverified_fault_hypothesis` status. The ranker does not read gold, references,
judge scores, or native outcomes. No new inference was performed for the study.

On the existing 113-task development-informed cohort, family hit@3 is 90/113,
family + first faulty site 78/113, versus v2 88/74 and original v3 77/67.
Frozen-label precision is 35.2% (v2 34.9%; original v3 49.1%); higher coverage
comes with more returned candidates. Labels are incomplete and the previous
40-task audit has already been inspected. These are post-hoc engineering scores,
not independent accuracy or test-generation efficacy. The registered native
utility comparison applies to original v3, not this fusion.

See ../retrieval_v3/continuation_20261027/RANKING.json for every selected row,
and ../retrieval_v3/RESULTS.md for the full quality study.
