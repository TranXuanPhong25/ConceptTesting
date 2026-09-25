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
