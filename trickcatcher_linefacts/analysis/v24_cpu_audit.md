# v24 executable-obligation increment — code/CPU review

2026-10-17. User approved implementation after the v23 semantic failure analysis.
Source parent: best v7; new copy v24_obligations. PARENT.json/PORTS.json record lineage.
Original v7, v23 and existing untracked v21_flowtools remain untouched. No paper
reimplementation, paid fallback, benchmark/held-out extension or prior-output import.

Independent clean-context plan reviewer v24_plan_audit required explicit pure-code
scope, S2→S3 linkage, locked S1 in revision, common concrete evidence, target-line
semantics, ambiguity/domain accounting, frozen preparation and durable attempt logic.
These were recorded before implementation/model calls in PLAN_EXECUTABLE_OBLIGATIONS_V24.

Independent clean-context code reviewer v24_code_audit found and rechecked:

| Finding | Pre-output resolution |
| --- | --- |
| Scalar floats and bool/float list elements slipped through calibration | Typed negative probes at scalar and element level; strict CPU controls; regression tests reject loose Python equality |
| Interrupted worker could silently rerun | Durable reservation before process launch; one attempt; missing result cached unknown without retry |
| Partial/orphan worker output could break or overwrite resume | Worker writes .part only; controller validates/atomically promotes canonical cache; recovery preserves unknown launch uncertainty |
| Hypothesis revision did not receive reach counterevidence | Initial support state and per-row target reach/native check/trace omissions/counterexample fields from same fixed pool |
| Output report incomplete | Stage/qualification/support/fallback/unknown coverage, all novel generated inputs, duplicate slots, raw/selected bug yield, whole-pool novelty |
| Worker cost uncertainty hidden | Durable recorded launches, reported PUT/predicate calls and interrupted upper bounds; actual worker binary/version pinned |

Final CPU suite29 tests: source restrictions, membership/count/sorted-output semantics,
constant predicate rejection, scalar/recursive strict types, domain/binding/JSON caps,
runtime errors, unsupported/ambiguous contracts, observed trigger/reach/violation support,
unused/unreachable negative controls, shared evidence parity, obligation identity,
full scripted end-to-end/resume/frozen scoring, terminal slot failure, novel-input vs
new-task distinction, durable partial-result/unknown-launch recovery. Scripted artifacts
are authored CPU controls, never Qwen success or paper simulation evidence.

Full9 preflight passes using authored CPU obligations:8 calibrated contracts plus1
ambiguous unknown; public-base native/traced agreement, all3 evaluator-only bug
witnesses violate their proper contracts. These are execution/calibration controls,
not success of model extraction. Exact source/fixtures/pools/bank/dependencies bind
the online gate; earlier CPU attempts are archived rather than overwritten.

Online scope9 seen authored fixtures (3buggy,5correct,1ambiguous), one full returned-JSON
relation/function. Qwen supplies semantics/trigger, tools supply bounded execution
evidence. Qualification explicitly uses diagnostic gold; passing finite calibration
is neither universal spec proof nor a deployable reference-free verifier. Three
generation arms share the same concrete witnesses/native traces and same independent
post-freeze scoring oracle. Input-generation-only; no model exact-output claim.

Fixed common24+base pool may saturate3 bugs, leaving no possible new-task headroom.
Pool is not changed based on detections. Report mechanism support, new inputs beyond
the whole pool and witness-only task yield separately; no promotion from a small pilot.

Source freezes before the first completion; max90 logical/270 physical completion
attempts, no content repair,1 predeclared hypothesis feedback revision,2 generation
calls/arm×3 named JSON inputs. Same-session watcher handles completion without duplicate
launch. Latest status lives under out/pipelines/v24_obligations/humaneval/obligation_diagnostic/.
