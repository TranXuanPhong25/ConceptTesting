# Authored joint-multiplicity example

This is an engineering demonstration, not a benchmark result or an LLM experiment.

Public example: `f([1, 2], 5) == 0`.

The source says to count all occurrences when `k > 0` and `len(xs) == k + 2`, but the return expression is `len(set(xs))`.
The MULTIPLICITY recipe constructs the source-bound alternative `len(xs)` and jointly solves:

- `k > 0`;
- `required = k + 2` and `len(xs) == required`;
- at least two equal elements, so deduplication changes the local result;
- different final outputs on the two execution paths.

Saved solver input: **`([0, 0, 0], 1)`**. PUT output is1; alternative output is3. Concrete replay confirms both branches are taken, the exact target AST site is reached, and predicted/actual outputs match. Both arguments differ from the public seed. A second saved input is `([0, 0, -1], 1)`, outputs2 vs3.

Unlike v31's seed edits, this construction derives several argument values together from assignment/guard/duplicate constraints. It does not simply try every ±1/resize transform. The example's spec is authored and easy; no conclusion about real-task concept accuracy follows.

`prepared.json` is the full immutable report with manifest, constraints, observations and all exported prompt arms. `hypothesis-request.json` demonstrates the explicit semantic-writer interface, but no writer was invoked. The five reported verified alternatives are behavioral ambiguities, not five independently confirmed bugs.
