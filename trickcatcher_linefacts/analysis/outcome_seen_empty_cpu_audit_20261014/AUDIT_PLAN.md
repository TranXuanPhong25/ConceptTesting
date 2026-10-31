# CPU audit of OUTCOME sites with empty base-seen sets

Registered before this audit's execution results on 2026-10-13. User explicitly requested an isolated clone and CPU measurement; no new LLM requests or method deployment.

Source snapshot: copy of current `pipelines/v11_fair`, excluding outputs and Python caches. Its facts.py/tracer.py are byte-identical to current v7. All copied source digests are recorded in clone_manifest.json. Extraction and tracer remain unchanged in this clone as well. Analysis scripts are added alongside them. Outputs stay in this clone's `out/humaneval/outcome_audit/`.

Scope: all 113 tasks with split=dev from the frozen v7 selection. Reject pilot and design IDs before launching workers. Do not remove the DEV task without observed hidden-test failures from structural counts. Baseline method artifacts are the historical v6 code facts and v7 hybrid bundle. B5 validators are copied from historical mining artifacts and hashes checked against both the fact file and bundle. No reference program, canonical solution or hidden label enters extraction jobs.

Extraction: invoke the copied facts.main using its existing evidence hook, with mutant_points=[]; stop inside that hook, before ranking/output. This avoids rerunning mutations that do not affect the base/fuzz traces or STMT/OUTCOME extraction. Compare reproduced pool size/validity stats and every original STMT/OUTCOME witness to historical artifacts; record any disagreement. No new fuzz transformation, seed, budget or filter. No historical trace observations are substituted.

Units: an instrumented condition/subcondition site; an additional candidate is (site, outcome T/F). `seen_empty` means no recorded T/F cell during base executions, not a proof the source expression was never attempted (it may raise during evaluation). Count all cond/subcond sites, empty sites, empty sites reached by the unchanged fuzz pool, and T/F candidates with witnesses.

STMT representation has separate measurements: source line belongs to an existing STMT fact; reached STMT exists; one is in the historical shown top-three; its saved witness actually evaluates the target site/outcome. Same source line/range is a coarse relation, not outcome equivalence. For 'STMT only', exclude sites with another historical reached non-STMT fact grounded at the same site or source line; report this operational definition. Preserve cases where a subcondition was skipped on an already-executed line.

Witness choice: first fuzz input recording each previously unobserved outcome, chosen before scoring. Also score the union of all input indices hitting an empty site and historical shown tool witnesses for context. No label-based witness selection. Canonical/contract appear only in separate scoring jobs after extraction has completed.

Scoring: replay plain PUT and canonical on deep-copied arguments in isolated workers, using cloned tracer.call (200,000 line steps; wall-clock safety net 3 seconds). Apply official contract; contract-invalid and canonical-error are excluded from confirmed bug counts but retained in diagnostics. Successful output comparison uses cloned v11 scorer with official per-task atol; report exact-equality sensitivity and wrong-output / exception / timeout separately. Numeric tolerance follows the shared scorer, no ranking trained on labels.

Reports: counts by cond/subcond and tasks; representation categories; first-witness bug counts and any-hitting-input ceiling; unique calls to avoid double-counting shared witness; comparison to historical shown tool witnesses; full site/candidate tables and concrete examples. These are DEV diagnostics, not an LLM effectiveness experiment. Finding more candidate witnesses does not establish detection improvements under top-three/budget constraints.

Meaningful verification: synthetic nested-guard and short-circuit cases; method-side jobs reject evaluation labels; all DEV workers complete; reproduction drift reported; source snapshot hashes unchanged after the run. No edits to original v7/v11/vendor or historical outputs.
