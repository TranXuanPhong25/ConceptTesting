# v57 engineering registration

2026-10-24, before v57 output generation. Scope: implement the user's deeper fault-hypothesis/input construction request, compare engineering behavior on authored fixtures, and prepare equal-evidence prompt artifacts. No effectiveness evaluation, no HumanEval/MBPP/VibePass scoring or held-out preparation, no model/API calls.

Protocol: PLAN.md. Source parent: PARENT_V57.json. Hypotheses are behavioral alternatives, not validated repairs. Z3 queries and concrete replays are bounded, errors/unsupported/unknown are distinct from unsat. All expected-output claims in guidance are marked observations, never oracle answers.

Independent review must finish before any real benchmark outcome. Authored fixtures are engineering regression tests and cannot be reported as research efficacy. No retrospective selection of task/model/budget from those fixture results.

## Amendment 1 — independent plan review, before code/outputs

- New facets require AST bindings and executable construction obligations; names alone do not count as mechanisms.
- Construction is behavioral differential search, not semantic fault diagnosis. Keep reach, local infection and propagation distinct.
- Replay must check the exact expression/statement span and branch events, not just a line hit.
- Fail closed on unsupported Python semantics; preserve partial coverage/unknown/timeout versus bounded UNSAT.
- Concept/raw arms share all factual evidence, order, outputs, predicates and imported quotes/rationales.
- Manifest pins source, config, proposals, actual domain, dependencies and solver version. No stale-cache reuse.

## Amendment 2 — independent code review fixes, before benchmark outcomes

Applied typed local infection, per-check query/deadline enforcement, full0..bound shape lengths, strict context-preserving public adapter, pure proposal allowlist, propagated deadlines and real AugAssign replay semantics. Regression suite expanded to34 authored tests, independently rerun and passing. These fix engineering instruments, not historical v31 scores. REVIEW.md records limitations and review conclusions. No model/benchmark experiment activated.

## Amendment 3 — user's ngrok run request, before model outputs

User explicitly requested ngrok only, no OpenRouter, and is restarting the notebook after the saved endpoint returned404. Add serial `ngrok_client/ngrok_run` with no external-provider fallback. No model request has been sent under this amendment.

Pilot: six existing dev PUTs selected outcome-blind by first6 SHA256(`v57-ngrok-mechanism-20261024:case_id`) over the frozen v31 dev33 list. Public-data adapter and selection manifest frozen before calls. No replacement if extraction/support fails. This is a mechanism/interface pilot, not held-out confirmation; no larger run is automatically authorized if it is weak.

Per case: one shared explicit hypothesis-writer slot, CPU construction, four generator arms (plain/concept/equal-evidence-raw/inputs-only), each two probes plus final. Shared writer cost charged to every arm;13slots/case,78max completed model slots for six. At most2persisted transport dispatches/slot,156max chat POST attempts across the pilot, including interrupted/unknown completions. Requests/attempts freeze before dispatch; a received response survives interrupted publication. Exhausted slots stop the run, never grant unlimited retry. Metadata health requests are separate from model POSTs. Max1536output tokens/call, prompt24000chars, temperature.2/top_p.95, fixed shared stage seeds. Writer may give up to3hypotheses; independently valid proposals retained, rejected ones reported, catalog fallback explicit. Up to6tests per call. Public witnesses are a no-model baseline. These are matched call/token caps, not a claim of equal actual token use or equal tool cost.

Concrete prompt evidence is the same in concept/raw, including ordering; both display at most3hypotheses×2inputs. Full formulas/traces remain in CPU artifacts; compact prompts retain paths and outputs. Truncation/JSON/interface failures are recorded and count against each arm, never silently repaired or rescued with extra model calls. Transport-failed unanswered slots may resume; completions are immutable.

Review refinement before launch: inputs-only receives exactly the displayed concept/raw witness pool, not all hidden prepared inputs. Artifact publication is atomic/no-overwrite; run output has an exclusive process lock. Redirects are refused, truncated HTTP bodies sanitized, and no endpoint/key is persisted. Frozen dev ids are61,66,124,58,131,85; all six public requests adapted with zero skipped asserts. This is not six independent/new problems or a post-cutoff cohort.

Normalized VibePass wrapper resolution may symbolically analyze a simple no-init/no-inheritance Solution method while replay executes the unchanged original wrapper/module at original AST coordinates. Calls/effects outside supported method semantics remain unsupported. Public `_heldout_same` example extraction requires exact known comparator AST and never evaluates helper code. These integration changes need independent review/tests before pilot launch.

Freeze source/config/request/proposal/model-metadata manifests before calls and generation hashes before private scoring. `ngrok_run` itself performs generation/PUT observations only. No trained UTGen reproduction, repair loop, oracle consensus claim or effectiveness verdict until separate scoring is complete. Record actual support coverage and all selected cases, not just successful solver witnesses.
