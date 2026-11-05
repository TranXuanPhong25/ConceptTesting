# Corrected reference programs

`humanevalplus_v0.1.10_references.json` is a curated evaluation-only projection of
the official EvalPlus HumanEval+ v0.1.10 dataset (EvalPlus package0.3.1).
Upstream dataset SHA256:
`42526ec0e7d5f3ee0b06d6ced98f8c8bae3d76519151bfb3d36f79010645bd7f`.

Retained fields: task ID,reference prompt,corrected canonical_solution,contract,
atol,entry point,original HumanEval prompt hash and compatibility annotation.
No base_input,plus_input,hidden test suite or expected-output dataset is retained.
Apache2.0license copied unchanged from the existing EvalPlus metadata export.

All164task signatures and spec text match the original bundled HumanEval tasks.
Contracts/tolerances exactly match the existing evaluation metadata. Task115moves
`import math` from inside the function to module scope;the signature/spec are
unchanged. Reference source rewrites are not equivalent to counts of fixed bugs.

`HumanEvalPlusReferencePrograms` validates task prompt hash/entry and matching
contract/atol before providing a corrected program. Source data is pinned in the
run manifest. Only the reference stage receives this provider,after input freeze;
generators continue to use original task data and do not receive corrected code.

Upstream:[EvalPlus](https://github.com/evalplus/evalplus).

`contracts.json` is the unchanged domain-contract/tolerance export used by the
current pipeline. It lives here so dataset loading has no historical experiment
package dependency.
