# Engineering review before outcome computation

Self-review and CPU regressions; no independent reviewer/model was invoked.
No paper method was reimplemented. Frozen old engine is preserved as a copied
module; no target execution, canonical/reference lookup or old labels in runtime.

Must-fixes found and applied before first v5 scoring:
- guard state invalidated by alias/unknown calls, slice writes and deletes;
- loop proof invalidated by index reassignment and mutation;
- rebinding before a guard overrides parameter annotation assumptions;
- builtin first-tie behavior is not a proof about reversed/reassigned/mutated
  input order; exclude only unchanged input parameters and simple builtin keys;
- unknown inference remains unknown; source spans convert AST UTF8 byte columns
  to LibCST character columns;
- local origin expansion has depth and node budgets;
- same-scope fixed initializer binds at its definition rather than its update;
- native utility or actual semantic truth is never inferred from static support.

Pair score is original v2 priority/spec/API score, plus6 when the fact is an
observed local output dependency, plus12 for a same-scope fixed initialization
site. These generic weights are fixed before new outcomes; no task-specific IDs.
One record per concept in final top-k, additional sites remain inspectable.

Remaining limits: alias analysis incomplete, domain facts can depend on recorded
annotations/public-doc assumptions, local origins are not a sound full Python
abstract interpreter, and existing benchmark labels are incomplete/single-author.
No generalization, actual-bug precision or test-generation improvement is claimed
from unit tests. Default stays v2; v5 explicit opt-in.
