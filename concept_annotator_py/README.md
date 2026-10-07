# concept_annotator_py

Python/TestEval-specific concept annotator.

This package targets the official TestEval schema rather than the C/C++ vulnerability benchmark code. It reads TestEval records with:

- `python_solution`
- `target_lines`
- `blocks`
- optional `sampled_paths` / `sampled_condition_paths` from `tgt_paths.jsonl`

and adds `concept_annotation_py` (`concept_annotator_py.v4`) with AST-backed
target annotations:

- line target code, AST node, concepts, reads/writes, and control context
- branch target condition and branch concepts
- path constraints parsed from TestEval condition paths
- program-level concepts such as `loop`, `hash_map`, `membership_test`, `sorting`, `binary_search`, `dynamic_programming`
- target-specific symbolic synthesis: branch polarity, alias-expanded input
  constraints, prior exit guards, simple state updates, map population across
  iterations, and conservative sequence-index facts

The broad AST labels remain in the annotation for analysis; the paper-protocol
concept prompt uses target-specific reachability facts. Facts are heuristic and
do not establish that a concrete input satisfies every condition.

For example, a target guarded by `n1 > n2` after `n1 = len(nums1)` and
`n2 = len(nums2)` is rendered as `len(nums1) > len(nums2)`, with
`len(nums1) <= len(nums2)` as the relation to avoid and
`len(nums1) = len(nums2) + 1` as the nearest satisfying boundary.

## Annotate TestEval Data

```bash
.venv/bin/python -m concept_annotator_py.run \
  --in /path/to/TestEval/data/leetcode-py.jsonl \
  --paths /path/to/TestEval/data/tgt_paths.jsonl \
  --out /tmp/testeval_concepts.jsonl \
  --limit 5
```

The output is prompt-ready and still compatible with TestEval's own line/branch/path evaluation format.

## Function-level C1-C8 tags for real-world code (`functions.py`)

Independent of the TestEval schema: give it the source of one function or method (e.g. a `text` entry of an
Agentless/CoSIL repo structure) and get bug-oriented concepts with evidence, in the repo's shared vocabulary
(C1 None, C2 empty/blank, C3 boundary/index/length, C4 error contract, C5 format/escape/parse, C6 numeric,
C7 chars/case/encoding/locale, C8 state/mutation). Stdlib `ast` only; Python 2 code returns an `error`.

```python
from concept_annotator_py import annotate_function, render_tags
ann = annotate_function(method_source, line_offset=start_line - 1)   # facts: concept, kind, line, detail
render_tags(ann)   # 'C1 None-check self.fp is None · C8 sets self.fp'  (ids are never dropped when shortening)
```

Notable facts: `unchecked-none` (a parameter defaulting to None / Optional that no test ever checks: a likely C1
gap), `catches everything`, raised/caught exception types, ±1 indexes and slices, length bounds, string formatting
outside error/log messages (messages are excluded), parameter mutation and `self.attr` writes.

Checks: `python3 -m concept_annotator_py.functions selftest`; `tests/test_concept_annotator_py_functions.py`.
`python3 -m concept_annotator_py.functions stats <dir|file>` prints the share of functions tagged per concept.
On 7,042 stdlib functions there are 0 parse errors and no fact kind fires on more than 19% of functions (raise 19%,
None-check 16%, self.attr writes 15%, …; `unchecked-none` 7%), so tags discriminate between candidates.
Facts are syntactic: they show where a concept is handled, not whether it is handled correctly.
