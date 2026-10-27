# Retrieval v6: semantic roles, site repair and explicit abstention

Actual copy of v5, recorded in COPY_MANIFEST.json. V2/v5 and their frozen results
remain unchanged. User explicitly authorizes iterative improvement from returned
results and implementation errors. This is development-informed engineering,
not an independent holdout or a reproduction of a paper model.

**Recommended for the current buggy-PUT retrieval task: `balanced`.** It retains
91/113 frozen family hits and90/113 first-site hits with126returned cards, versus
v2/v5 88/74 with275cards. A retained fallback is explicitly uncertain. `precise`
abstains when no semantic support is available; it trades coverage for fewer
unwarranted suggestions. See [RESULTS](RESULTS.md) for both views and controls.

## Use

Requires Python with LibCST1.9.0. Existing v5 .venv can run this code; for a new
installation:

```bash
python -m venv python_bug_concepts/retrieval_v6/.venv
python_bug_concepts/retrieval_v6/.venv/bin/pip install -r python_bug_concepts/retrieval_v6/requirements.txt
python_bug_concepts/retrieval_v6/.venv/bin/python -m python_bug_concepts search \
  --retriever v6 --policy balanced --code path/to/program.py --top-k 3 --json
```

```python
from python_bug_concepts import search
packet = search(code=source, retriever="v6", policy="balanced", top_k=3)
```

The routed API/CLI default for explicit v6 is `balanced`. The low-level
`retrieval_v6.engine.search` default is `precise`; pass policy explicitly for
reproducible comparisons. Public `auto` remains v2 for compatibility. Other field /
custom-root searches remain available through the original retriever.

| Policy | Selection |
| --- | --- |
| coverage | Up to k ranked concepts, including weak context candidates. |
| balanced | Supported concepts if any; otherwise one explicitly uncertain fallback. |
| precise | Only supported concepts; no automatic filling. Unknown options remain under review_candidates. |

`ranking.semantic_support` exposes the tier and reasons. These are static support
levels, not calibrated bug probabilities. Every primary result remains an
`unverified_fault_hypothesis`; abstention never means the function is proven safe.
`instantiated.where` cites source/fact/scope IDs, `how` exposes the conditional
mechanism and dependencies, and `what` keeps expected_output unset. No generated
oracle or invented distinguishing example is accepted as truth.

## What changed

- Semantic support affects ranking, instead of declared conditions and tiny
  bonuses being overwhelmed by old rule priorities.
- Invalid-offset, consumed-sentinel, compound/ternary and input-shortcut sites
  compete with actual mechanisms rather than the first comparison in the file.
- ASCII literal guards and unique-domain membership are eligible candidates.
- Correct first-index lookup, intended numeric loop bounds, non-capturing lambdas,
  scalar set cardinality, boolean short circuits and hashing have role checks.
- Qualified symbols cross comprehensions; branch-local/tuple definitions preserve
  provenance, while post-join ambiguity stays unknown. Source spans and exported
  fact IDs are checked, including supplemental decisions and module fragments.

No target code/reference/gold execution or lookup occurs in retrieval. Candidate
rules still use partial semantic matching and public-domain assumptions. scope_id denotes the lexical container; qualified names carry resolved symbol binding. Full
alias analysis, arbitrary dynamic Python and natural-language proof are outside
scope. Syntax/backend failures retain explicitly warned legacy fallback behavior.

## Verification and evidence

```bash
python_bug_concepts/retrieval_v6/.venv/bin/python -m unittest discover \
  -s python_bug_concepts -t . -p '*test*.py'
```

242tests pass. Final scored code is under `evaluation_v6/iter06/`; earlier
iterations and source snapshots are preserved. Do not overwrite them. The copied
`evaluation/` and `evaluation_v5/` are historical parent artifacts, not v6 scores.

- [Implementation/error audit](AUDIT.md), [protocol](PREREG.md).
- [Final per-task results](evaluation_v6/iter06/RESULTS.json).
- [Correct-program controls](evaluation_v6/iter06/CANONICAL_CONTROLS.json).
- [Native examples](evaluation_v6/iter06/NATIVE_AUDIT_FINAL.json).
- [Final source/parent validation](evaluation_v6/iter06/VALIDATION.json).

No new Qwen/paid calls, embedding training or test-generation efficacy run.
