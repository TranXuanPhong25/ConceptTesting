# Search and relational concepts for LineFacts

2026-10-14. Planning/research only; existing frozen runs are unaffected.

User explored path selection, node pruning, beam search, BFS/DFS, MCTS/minimax, model transparency,
and complex temporal/membership/containment rules. The proposed design extension is recorded in
[PLAN_ABSTRACT_CONCEPTS.md](../../PLAN_ABSTRACT_CONCEPTS.md), sections 3.2 and 4.1.

Our assessment:
- Search over (obligation, block, constrained state, relation class), not source lines alone.
- Non-strict containment permits equality; proper containment excludes it. Preserve operand types,
  collection multiplicity/order, fixed clock, timezone and endpoint assumptions.
- Prioritize distinguishing relation classes while holding other guards true; later explore interactions.
- Local discharged obligations retain scope; passing tests or a low LM score never prove a node correct.
- Use bounded best-first with exploration first. MCTS needs credible values, replayable actions and costs.
  It redistributes a finite budget and does not guarantee finding all relevant paths.
- Observable external decisions and verifier logs improve auditability; they do not expose model internals.
- This is a neuro-symbolic system design. Representation engineering and learned selection can coexist;
  tool-only controls are needed to establish the incremental contribution of LLM/concepts.

Primary references and per-paper notes:
- [LATS](papers/lats/NOTES.md): external action tree with MCTS/environment feedback.
- [Vital](papers/vital/NOTES.md): domain-risk-guided symbolic execution, memory-safety setting.
- [Discriminator study](papers/planning_discriminator/NOTES.md): quality/cost of search judgement.
- [CEGAR](papers/cegar/NOTES.md): refine spurious abstract counterexamples.
- [Tree of Thoughts](papers/tree_of_thoughts/NOTES.md): alternatives/backtracking over reasoning units.
- [MCTS symbolic-path paper](papers/mcts_symbolic_paths/NOTES.md): author abstract only, coverage outcome.
- [KLEE official search options](https://klee-se.org/docs/options/): multiple state-search heuristics and
  interleaving, illustrating that pure BFS/DFS are not the only options.

Candidate search signals use PUT execution and supported local contracts. Canonical/gold/shared-ref
outcomes remain evaluator-only after generation freeze; no reward tuning on those results in the same run.
No scalar reward, MCTS budget or new model-call protocol has been experimentally validated here.

FSM follow-up: [NuSMV official tutorial](https://nusmv.fbk.eu/userman/v21/nusmv_2.html) and
[SLAM project](https://www.microsoft.com/en-us/research/project/slam/) support finite state and
predicate-model terminology; the proposed finite abstraction is in plan §4.3.

Spec/structural mutation follow-up: [NIST prior-work note](papers/spec_mutation_nist/NOTES.md),
plan §4.4. Original specs stay normative; mutant models are fault hypotheses. Bypass FILTER,
delete CHECK, skip/unguard IF, branch change and dependency-safe relocation require explicit
semantics. Natural-language edits alone do not establish meaningful or feasible alternatives.
