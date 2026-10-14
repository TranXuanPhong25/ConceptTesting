# Test Generation Using Model Checking and Specification Mutation

Paul E. Black; NIST publication page (2013, IEEE IT Professional issue 2014).
Reviewed 2026-10-14; publication-page abstract only. Research, not reproduction.

[Primary source](https://www.nist.gov/publications/test-generation-using-model-checking-and-specification-mutation)

NIST describes automatic test generation from models using model checking and specification
mutation, with work dating to 1998, and test-suite coverage independent of implementation details.
This supports treating specification mutation/model-based testing as established prior work.

Our proposed adaptation: typed requirement/behavioral models, finite operators, original-vs-mutant
distinguishing inputs/sequences, then actual PUT checking against the original specification.
Deletion/bypass/relocation semantics must preserve clear bindings and report scope/equivalence.
Abstract mutant coverage is separate from bug-detection performance. No method code implemented.
