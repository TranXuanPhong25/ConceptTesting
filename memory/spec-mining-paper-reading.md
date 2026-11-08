---
name: spec-mining-paper-reading
description: Three user PDFs read: S2F constraint extraction, Grounding Tested/Untested agent, formal-contract SMT generation; preserve role and input/assertion-coverage distinctions
metadata:
  type: project
---

User2026-11-04 explicitly distinguishes finding untested conditions from finding
concrete inputs that satisfy them. Static CFG/dataflow extraction, semantic spec
mining, base-test gap verification and solver/input construction are separate
steps; do not conflate their evidence or claim all are solved by one library.

2026-11-06 follow-up: user asks how to fix BVA semantic grounding. Re-read local
methods against protocol5/6trace; read public Jdoctor/nl2spec/VeriSpecGen PDFs and
ISLa docs plus holistic-spec evaluation. Notes in separate final/spec-minign/
folders; synthesis in final/review/boundary_semantic_grounding_research_2026-11-06.md.
Key protocol limit: VeriSpecGen uses black-box reference/oracle labels during
refinement, whereas current generator sees reference only after input freeze.
Recommendation is scoped quantity/scope/polarity evidence and executable context
obligations, checked against v7/v10/v47/v57/v66/v68/v69/v33 history; not a new
untried spec→predicate→solver claim. No implementation/reproduction/model task
calls/benchmark; one user-requested1token endpoint ping received separately.

Read all3PDFs user added under `final/spec-minign/`. Individual paper folders and
cross-paper synthesis are in that folder; original PDFs unchanged. No paper
simulation/reimplementation, model call, benchmark change or commit authorized
by this reading task.

- S2F/RequirementsEngineering2026: NL→fragment/operands/type with spaCy+ML;
  best classifier P63.63/R61.40/F1=62.34.98.6%is emittedpattern/operand accuracy,
  not semantic predicate accuracy/constraint recall. Single-sentence explicit
  constraints only; excludes cross-sentence/pronouns,GUI,lists/code/tables.
- GroundingAIAgentsinContracts(arXiv2608.17177v2): directly proposes inferred
  pre/postconditions→agent Tested/Untested→suggestions→tests. Actual90bug study
  generates from FIXEDcode and EMPTYtests then reverse-patches bugs. Does not
  establish reliable base-gap inference from buggyPUTs. detect@5+9.8pp,p.0352;
  detect@1p.3075;tokens+38%. ContractCoverage is bug-specific LLMjudge metric,
  not baseinput coverage. No directauthorcode release verified.
- Automatic test cases generation from formal contracts(IST2024/107467): assumes
  formal Spark/Ada contracts; guards→ECP/boundaries→Z3py distinct inputs.
  Does not mine NL or base gaps.8verifiedtiny subprograms;randombaseline uses
  randomexpectedoutputs and often violates preconditions. Passrate/coverage
  findings are not evidence of finding realPUTbugs. Data on request.

Prior-art check: v10_spechint already did specquote→applicabilityD→basegap→witness;
157requirements,146alreadybase-covered,7hints/5tasks,no good@3gain. V66 has
CrossHair construction,v68no efficacygain. Do not sell generic spec→condition→test
as a new untried method. Main useful directions are traceable role-tagged clauses,
correct bindings/quantifiers,verified gap evidence and separated upstream/downstream
failure accounting. Existing inputs-only/referenceprotocol stays authoritative.

Keep domainpreconditions,behaviorguards,postconditions,defaults/undefinedbehavior
separate. Existence of a baseinput hitting guard does not mean assertions verify
the consequence; conversely weak assertions do not mean no input exercised guard.

**Why:** user asks whether new spec-mining papers supply the missing condition/
input machinery. They cover different layers and their evaluation differs from
the current HumanEval setting.

**How to apply:** read `final/spec-minign/README.md` plus each paper NOTES.md before
proposing an adaptation; no code reproduction without explicit user agreement.
