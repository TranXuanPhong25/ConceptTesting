# v19 flow implementation audit — 2026-10-15

The implemented treatment is typed candidate-model parameters plus AST pseudocode in an LLM strategy prompt. It is not yet the connected behavioral reasoning/FSM/spec-mutation engine discussed with the user. Output-format rejection is one bottleneck, but fixing extraction alone would not close the methodological gaps below. Frozen hashes/tests establish reproducibility and some local checks, not semantic correctness of the full flow.

## Actual code flow

1. v18 parent preparation parses Python AST into statement blocks and syntactic control edges. Each block has shallow read/write/mutation metadata. Pseudocode preserves Python expressions, source line IDs and control edges. It is mostly a source rendering, not relational semantic lifting or symbolic execution.
2. Original PUT runs on at most8 public-base inputs with instrumented concrete execution. Integer values become negative/zero/positive; collections become empty/singleton/many. Observed projected states/edges are stored as a finite under-approximation. Replay/native output comparison checks instrumentation on those inputs. It does not check that generated CFG edges faithfully encode all supported control semantics.
3. Independently, v18 enumerates up to2048 parameterizations of nine hand-authored templates. Argument/output types and public native base outputs constrain candidates; all observed public base outcomes must match. A lexical score over the docstring plus a default-parameter preference ranks candidates. v19 reuses the top model unchanged. This is feature engineering and bounded compatibility, not semantic entailment from spec clauses or derivation from code flow.
4. v19 takes up to3 semantic parameter mutations in fixed enumeration order. It creates cards with constant explanatory text and `block_ids=[]`. It does not use v18 explanatory discrepancy traces to bind these cards to actual source nodes. Alternative feasibility, compatibility with existing base evidence and ability to explain current PUT behavior are not checked here.
5. LLM receives original PUT/spec, base tests, pseudocode and one model/fault JSON card per available slot. The observed FSM, replay states, node-local discrepancies, read/write metadata and model catalog definitions are not passed to generation. No choose-node/execute-path/refine-hypothesis interaction exists.
6. LLM writes a Hypothesis strategy. Static syntax/purity check, bounded draws and the shared admissibility filter run; up to2 valid inputs per slot are sampled uniformly. There is no trigger/path satisfaction check or concept-based ranking. Model/fault activation is merely logged after selection; no mismatch feedback returns to the LLM.
7. Generation freezes; saved spec-only references and canonical evaluation score selected inputs. This measures end-to-end detection under the implemented prompt treatment, not correctness of causal localization or the proposed reasoning mechanism.

## Findings

| Finding | Evidence / consequence |
|---|---|
| Missing concept-to-source connection | `behavior_experiment.rule_cards` sets `block_ids=[]` and a constant `reasoning` string. All29 actual concept-bearing slots checked have empty bindings. No obligation → node → effect → trigger chain. |
| FSM built but unused by guidance | `guidance()` reads pseudocode and cards only. No machine/state/replay-guided branch selection. Stored FSM is not an execution/search engine. |
| Missing template definitions | All39 slots on13 model-covered tasks lack the catalog definition used in v18 selection. LLM must infer precise semantics from parameter names. |
| Syntactic source rendering | `behavior.pseudocode()` prints `ast.unparse` expressions and edges. Task149 still contains `sorted(list(set(lst) - set(odd_lst)), ...)`, without lifting the critical conversion to a multiplicity-changing operation. |
| Fixed-order fault truncation | Task149 selects predicate inversion, predicate removal and index parity; drops fourth mutation `distinct=false → true`. This is exactly the semantic loss visible in `set(...)`. No source-grounded priority. |
| Trigger unverified | `templates.activates()` is called after random selection only. Prompt instruction to distinguish faults is not backed by an executable discrimination gate. |
| Read metadata incorrect for AugAssign | CPU counterexample `total += x` records reads=`['x']`, writes=`['total']`; omits reading old total. This affects any later use as a dependency graph. Current v19 does not pass these reads to generation. |
| Unsupported branch accepted as supported | CPU counterexample with `match/case` gets `structural_supported=True`, one STEP and next→EXIT, no case branches or inner returns. Not asserted to occur in the current20-task cohort; demonstrates incomplete support validation. |
| Limited concept expressiveness | Fixed predicate enums and nine templates do not encode arbitrary Boolean formulas, temporal90-day windows, general quantified obligations, or arbitrary relation compositions. CONTAINMENT supports several set/count modes, but the system cannot infer arbitrary business constraints. |
| Gate does not validate method completeness | 17/20 means supported-by-current-checks and bounded replay compatible.13/20 means a base-compatible model with generated alternatives exists. Neither checks semantic concept entailment, source binding, fault localization, or a discriminating path. |

## Concrete example: task149

Spec requires filtering odd-length strings and sorting while preserving permitted duplicates. PUT converts the collection to a set and loses multiplicity.

A connected explanation should carry:

- Obligation: retained duplicate strings preserve occurrence count.
- Source effect: converting `lst` through `set` collapses equal occurrences before return.
- Predicate over inputs: an even-length string occurs at least twice.
- Discrimination: `['aa','aa']` yields2 occurrences under the model,1 under a deduplicating implementation.
- Evidence: replay confirms actual set conversion and returned multiplicity; broader checks distinguish competing hypotheses.

v19 supplies a FILTER model with `distinct=false` and unabstracted source text, but it omits the dedup mutation from its first3 cards. It neither constructs nor verifies that explanation. The LLM could infer it independently; that is not an implemented tool-supported reasoning chain.

Task110 gives another gap: an unnecessary `len(lst1) != len(lst2)` guard precedes an exchange algorithm. The selected CAPACITY model and its count-comparison alternatives do not explicitly bind to or mutate that length guard. Stored source/trace data alone does not close this gap.

## What is supported by evidence

- Local infrastructure exists: source IDs/basic CFG, concrete replay, bounded state projection, typed executable candidate models, exact caching/isolation, common input filter and post-freeze scoring.
- The registered experiment was followed, frozen artifacts verified, and scored detection counts are actual outputs of this implementation.
- The requested reasoning mechanism has not been implemented in full. Current results cannot settle whether a properly connected semantic behavior model would improve detection.
- Audit script is CPU-only, with handcrafted counterexamples to our own code; it does not simulate a paper. No frozen pipeline/prompt/validator/output was changed and no additional GPU experiment was run.

## Minimum contract before another claimed behavioral-reasoning experiment

Require each usable example to produce an inspectable artifact: spec obligation with scope/precondition; semantic implementation operation; source binding; preservation/loss condition; a concrete discriminating input; native trace and output evidence. Missing or unsupported links must be explicit abstentions. Correctly handle read-modify-write operations and reject unsupported control constructs. Validate CFG/abstraction against independent semantic expectations, not merely a replay of the original function. Rank semantic alternatives using the actual implementation effect rather than registry order. Supply precise concept definitions and verify the intended discrimination before attributing success to the concept mechanism. Freeze this contract in a new pipeline before GPU comparison; do not repair v19 in place.

Files: `pipelines/v19_rulegen/behavior.py`, `behavior_worker.py`, `candidate_models.py`, `selection_worker.py`, `templates.py`, `behavior_experiment.py`. Reproduce audit with `python -B trickcatcher_linefacts/analysis/v19_flow_audit.py`; JSON holds the exact counterexamples and task149 evidence.
