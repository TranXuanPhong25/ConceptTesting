# Scoped-fact retrieval v5

Copied from the committed v2 baseline before editing (`COPY_MANIFEST.json`).
Adds LibCST positions/scopes/qualified names, bounded local value-origin chains,
conditional applicability/exclusion records and concept/site pair ranking. This
is project-specific engineering, not a reproduction of a paper's model.

**Measured result:** 113/113 sources analyzed without scoped-backend fallback;
family hit@3 remains88/113 and family+first site74/113, equal to v2. All275 returned
bindings have exact source spans/fact IDs. Four lower-ranked bindings were
excluded by guarded/bounded indexing checks, without changing top-3 metrics.
This is source-grounding fidelity, not actual-bug precision. See [RESULTS](RESULTS.md).
Public default stays v2; v5 is opt-in. No new model/API or native utility run.

## Install and use

```bash
python -m venv python_bug_concepts/retrieval_v5/.venv
python_bug_concepts/retrieval_v5/.venv/bin/pip install -r python_bug_concepts/retrieval_v5/requirements.txt
python_bug_concepts/retrieval_v5/.venv/bin/python -m python_bug_concepts search \
  --retriever v5 --code path/to/program.py --top-k 3 --json
```

Or using Python with that environment:

```python
from python_bug_concepts import search
packet = search(code=source, retriever="v5", top_k=3)
for hit in packet["results"]:
    print(hit["concept"]["id"], hit["instantiated"])
```

`instantiated.where` cites actual source/node/scope; `how` includes observed local
dependencies and the conditional mechanism; `what` retains a failure/input-class
template and **no invented expected output**. Public spec text and requires/excludes
are inspectable. Status stays `unverified_fault_hypothesis` until independently
validated. `facts` contains source records/output origins; `excluded_bindings`
records every exclusion and its assumptions. Model explanations are not involved.

Nine mechanism families have explicit condition definitions; automatic exclusions
currently implement guarded index/reduction, bounded loop indexing, builtin-first
selection with unchanged input order, and public examples refuting count equality.
Other conditions remain unknown. This does not formalize all162 cards/contracts.

Guards rely on recorded builtin/type/public-domain assumptions and local value
stability checks. Origins are conservative local dependencies, not a complete
alias analysis, full DFG or proof engine. Unknown facts do not automatically
exclude candidates. Invalid syntax/backend failure retains lexical/v2 fallback
with an explicit warning. Target code is never executed by retrieval.

## Verification and frozen results

```bash
python_bug_concepts/retrieval_v5/.venv/bin/python -m unittest discover \
  -s python_bug_concepts -t . -p '*test*.py'
```

118tests pass, including32new scoped tests. `evaluation_v5/FREEZE.json` preceded
scoring; results are in `evaluation_v5/RESULTS.json`. Scoring refuses code/input
drift or overwriting an existing result. Do not delete freeze/results to retune.
The inherited `evaluation/` and original helper scripts are historical v2 copies;
use `evaluation_v5/` and the new evaluator for v5, not copied historical results.

The explicit API needs LibCST1.9.0. Existing original/v2/v4 APIs do not import it
unless v5 is selected. No changes to v2, vendor sources or original corpus.
