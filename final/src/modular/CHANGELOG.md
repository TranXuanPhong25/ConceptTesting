# CHANGELOG

## 2026-11-08 — resume full matched batch evaluation after blocked C call

- Giữ nguyên314responses, frozen inputs/settings và confirm-first-failures scorer;
  tiếp tục từ60task checkpoints trong output mới,0model/tokenizercalls.
- Thêm active-user-call marker để outer wall guard chỉ ghi single-input timeout
  khi C call không dispatch SIGALRM;startup hang vẫn là infrastructure error.
- Copy frozen runtime với đúng2file executor/worker được sửa;giữ nguồn cũ,ghi
  before/after hashes,checkpoint receipts và yêu cầu immutable replay.
- Dùng native lock cũ;report tiếng Việt phân biệt detection và wrong-value witness.

## 2026-11-08 — Prefect local preset console

- Use Prefect3.9.2for editable run forms,presets,scheduling,history and artifacts;
  isolated orchestration venv leaves benchmark dependencies unchanged.
- Add full/known10/smoke paired-batch and per-PUT shared-budget presets with
  complete resolved settings and explicit input-budget units.
- Freeze config/code/cohort per launch;keep endpoint credentials outside tracked
  parameters;retain transport budgets,source guards,native lock and replay.
- Import historical records read-only. Preview-only runs make0model/nativecalls.
  New model experiments are started by the user from the console.
- Validation:444testsPASS,independent console reviewPASS;UI smoke preview-only.

## 2026-11-08 — continue paired batch without repeating saved responses

- Add isolated recovery for the stopped matched batch: retain226received calls,
  frozen314request plan/visibility and unknown transport history;only88responses
  remain to generate. Preserve request attempt caps and original run bytes.
- Re-decode imported batches with cached responses,then reuse the exact frozen
  generator/scorer. Keep cumulative imports once and separate continuation costs.
- Preserve one-shot launch,source guards,native lock,input freeze and replay.

## 2026-11-08 — packaging audit and scheduled matched batch comparison

- Audit all historical plain responses with static signature/contract evidence.
  Repair only provably invalid argument wrapping, preserving literal values and
  one encoding per original raw slot; authenticate sources and save old/new proofs.
- Add opt-in Direct/Soft BVA batch arms sharing the same prompt packet, schema,
  parser, CallBuilder, sampling and 20-input budget. Only guidance differs.
- Pre-tokenize both arms and freeze joint visibility/requests before generation.
  Alternate arm order, retain empty outputs, record exact PUT overlap/witnesses.
- Schedule one-shot detached generation at the requested 40-minute deadline.
  Frozen runtime, review/test gates, metadata-only endpoint waiting and a shared
  native lock prevent early inference and concurrent timeout-sensitive scoring.
- Validation: 422 checks passed before CPU audit launch; 31 targeted offline
  checks passed after final reporting/scheduler changes. Independent review PASS.
  Existing production per-PUT BVA default and historical runs are preserved.

## 2026-11-08 — reuse cached naive inputs for the full BVA comparison

- Export the original admitted `plain` records with receipts for their source
  freezes. Preserve empty/rejected batches and historical resource skips; make
  no new model calls and do not repair raw responses.
- Continue evaluation in an isolated frozen runtime with preserved checkpoints,
  bounded infrastructure recovery, input hashes and immutable read-only replay.
- Compare exact task-local PUT identities on all 1,454 targets and the historical
  common 1,437 targets. Report input coverage, failure witnesses, writer costs
  and the preregistered secondary uniform valid-input-budget expectation.
- Completed report: `final/review/naive_vs_soft_bva_full164_2026-11-08.md`.
  BVA 61 versus naive 44; all 30 BVA-only detections have no executable novel
  naive input, so the raw gain does not demonstrate better boundary selection.
- Validation: 396 checks before scoring; three comparator tests separately,
  rerun after report formatting. Both completed input/hash and replay checks pass.

## 2026-11-07 — retry only first-run PUT failures

- Skip second PUT executions for first-run passes. Confirm fail/error/timeout
  using the same seed and the independent repeat1cache slot before detection.
- Record original retested input indices; unstable now covers only those inputs.
  Use separate retry checkpoints and expose the policy in stage configuration.
- Keep reference/domain validation repeats unchanged; preserve historical runs.
- Validation:378modular/development checks pass, including cache/no-cache subset
  mapping, transient failures, empty/all-pass batches, sandbox execution and replay.

## 2026-11-07 — document evaluation repeats

- Explain why PUT evaluation repeats each test twice with the same seed and
  requires failure in both runs before counting a detection.

## 2026-11-05 — LangChain completion transport

- Replace manual completion JSON serialization/SSE decoding with ChatOpenAI and
  the OpenAI SDK. Keep vLLM tokenizer, endpoint/model checks and context budgets.
- Preserve finish/nonempty acceptance, partial output, raw provider usage,
  sanitized failures, byte/deadline guards and checkpoint-owned retries. Disable
  LangChain tracing and SDK retries. Record transport library versions in new manifests.
- Exercise actual LangChain/SDK code via offline HTTP fixtures; no remote model
  calls or changes to saved run/checkpoint artifacts.

## 2026-11-05 — remove redundant files

- Remove31obsolete baseline/archival/validation/snapshot files; recover historical
  versions from Git instead of carrying duplicate runtime and inventory files.
- Keep shared helpers in runtime/contracts.py and the unchanged writer prompt in
  modular/program_prompts.py. Update audits and source hashing.
- Retain parser/sandbox safety tests against the current runtime; retire2tests for
  the deleted baseline workflow.212tests pass;independent review has no must-fix.
- Preserve current data, research/papers, reports and original run/checkpoints.


## 2026-11-05 — standalone runtime and plain/BVA pipeline

- Extract sandbox execution, streaming transport, checkpoint retry and keepalive
  into `final/src/runtime`; remove active imports of historical experiment packages.
- Remove concept/V11/classical/contrastive/placebo/toolinput/witness arms, their
  preparation/reporting stages, legacy adapter and CLI options from modular.
- Add standalone dataset/cohort helpers and domain metadata. Rename the method
  base to InputGenerationMethod, calls to RecordedModelCalls and optional input
  annotation to guidance_id. Frozen-input rescoring preserves saved records.
- Keep historical results/checkpoints untouched; new manifest protocol is
  input-generation-benchmark-v2 and changed source identities require new runs.


## 2026-11-05 — numeric strings and inferred format boundaries

- Continue from the feasibility audit in the existing BVA module. Add
  `parsed_float`, bounded finite parsing and exact string construction of numeric
  targets. Single controlled numeric strings can complete without a context call.
- Require public-spec projection evidence, including parsed threshold expressions.
  Observed numeric strings and PUT conversions alone do not authorize this binding.
- Reject integer thresholds/targets that cannot be represented exactly as floats;
  preserve the requested boundary instead of silently rounding it during encoding.
- Add inspectable nearest-integer midpoint and fixed-width-format length hints.
  Preserve behavior/domain separation; uncertain selections remain explicit.
- Bump BVA/arm protocol identity to3. Keep previous runs unchanged and reject reuse
  of their generation checkpoints for this source/schema change.
-205 checks pass (196 modular+9 development),including40 new regression cases. Saved
  PUT fixtures99/124 exercise injection,globalfreeze,corrected references and two
  stability repeats with scripted selection/context responses,not fresh LLMs.
- Offline44taskinspection exposes derived guards for99/124;1375oldrunartifacts
  unchanged. No model/benchmark rerun. See review/boundary_string_repair report.

## 2026-11-05 — compiled BVA targets and shared call encoding

- Implement user-authorized BVA repair in place:CallBuilder shared with plain,
  typed run/range/extrema operators,public guard hints,role checks,TargetCompiler,
  named context completion and preallocated obligation quotas.
- Exact scalar/base duplicates skip context calls;unknown/unsupported/resource
  cases retain reasons. Full domain/reference validation remains after freeze.
-165combinedchecks pass,34new mechanism checks. Offline49proposal diagnostic
  blocks6unverified/mismatched bindings;not semantic precision. Original1336
  artifact files unchanged,no live model/benchmark run. See review repair report.

## 2026-11-05 — corrected HumanEval+ oracle and exact-input rescore

- Add pinned reference-only HumanEval+v0.1.10projection with no hidden input arrays.
  Modern oracle defaults to this provider;spec/hash/domain binding checked before
  reference execution. Archived/synthetic protocols explicitly choose task refs.
- Add FrozenInputsGenerator and model-free rescore entry point;keep original
  generation/spec/PUT contexts and all saved input records unchanged.
-122engineering checks pass. Corrected44taskrescore changes raw3vs3detections to
  0vs0,with595/121valid inputs unchanged.0newmodelcalls,original1336artifactbytes
  preserved,exact generation freeze and118source/datahashes verified;fullreplaypass.
- BVA improvement audit/proposal saved separately;no BVA algorithm change or new
  generation/model benchmark launched for that proposal.

## 2026-11-05 — shared per-input execution cache

- User requests reusing already executed inputs, then launching plain+BVA.
  Add SQLite-backed InputExecutionCache for reference/domain and PUT outcomes,
  shared across modern runs and isolated from generators/model prompts.
- Key by source/context/contract/expected/timeout/seed/tolerance/runtime and typed
  bound inputs; preserve dict order,float bits and separate repeat slots. Execute
  each cache miss in a fresh sandbox; deduplicate matching inputs across arms/runs.
- Keep run checkpoints authoritative for replay; track cache receipts/hits/misses/
  executed inputs in summary/report. Do not reuse timeout or infrastructure failures.
  Corrupt entries recompute; per-key locks prevent concurrent duplicate work.
- Enable on modern pipeline,retain original legacy execution,allow explicit cache
  directory or disable flag. Initial cache population adds sandbox-startup cost;
  do not claim wall-time improvement until repeated workload is measured.
-19cache engineering checks pass,including real sandbox and cross-run reuse.
  Existing19boundary/injection integration checks pass with caching enabled.
- Fullmodular112checks pass. Authorized6PUTplain+BVA smoke complete:80/19valid
  inputs,0/0additional PUTfailures,16responses/0unknown. Warm real-workload audit
  yields432hits/0new executions;fullread-only replay/source/input hashes verified.

## 2026-11-04 — injectable input generator and explicit validation blocks

- User requests removing initial concept stages from the main flow and making
  input generation injectable. Core now depends on `InputGenerator`; methods or
  input-producing stages compose through `MethodInputGenerator` without requiring
  ExperimentArm inheritance, concept packets or a model backend.
- Default method is now plain. Modern plain/boundary use lightweight eligibility/
  visibility preparation; core no longer imports/constructs concept or witness
  stages. Original generation steps remain in an explicit legacy adapter for
  archived experiments; CLI requires --legacy-generation for those methods.
- Shared output contract validates task/method batches and literals before
  checkpoint/freeze. Reference/oracle/evaluation consume the same named batches
  from every generator. Manifest freezes generator source/config; read-only replay
  never invokes a producer on a missing checkpoint.
- Extract selection/generation response validation, per-input validation and task
  signature validation into named functions. Mark validation call sites/API/
  context/cache/reference checks with VALIDATION START / VALIDATION END comments.
- Full regression93checks pass, including8new injection tests: independent producer,
  ordinary input stage, no-model/no-packet flow, invalid output rejection, config
  invalidation, default no-concept flow, checkpoint/replay and all-task freeze.
- No live model or cohort benchmark, source-copying, commit or push.

## 2026-11-04 — integrate boundary into the main modular pipeline

- Add opt-in `BoundaryArm` / `--arms boundary`, keeping default arms unchanged.
  Split the existing task input budget equally across template-eligible visible
  PUTs; fixed shares, no fallback or redistribution; deduplicate merged inputs.
- Reuse generation freeze, trusted contract/reference oracle, PUT evaluation and
  existing caches. Report boundary task/PUT statuses and logical selection/input
  calls through generic arm summary hooks, compatible with V11 reporting.
- Boundary-only generation bypasses shared prompts, CFG/DFG analysis and witness
  sampling. Empty suites do not execute reference/PUT code; arm skip survives
  evaluation. Existing arm prompts and historical replay stay covered by regression.
- Add explicit CLI task subset, target-program count and task input budget flags
  so the saved1PUT/task smoke cohort can run through the main entry point.
- Validation:11new integration checks; full modular suite85pass. Only synthetic
  fixtures and their sandbox executions; no live model/cohort benchmark or commit.

## 2026-11-04 — BoundaryValueAnalysis module

- Implement user-requested per-PUT flow in `boundary_value_analysis/`: input type
  extraction → reusable templates → LLM boundary/domain selection → LLM inputs.
- Source types from saved input calls plus PUT/task annotations without executing
  PUTs. Support scalar, length, numeric elements and sum; relational thresholds
  may reference another input value/length/sum. Preserve type provenance.
- Explicit no-template/no-boundary/unsupported/invalid/no-input statuses; no plain
  fallback. Two logical LLM calls maximum, configured budgets and prompt limits.
- Check quote presence, schema, literals, signatures, exact declared boundary
  targets and duplicate inputs. Prose constraints remain explicitly unverified;
  external contract/reference validation is still required before scoring.
- Immutable input/source/config/model identities, per-PUT lock, stage checkpoints,
  transport-error propagation and read-only replay. Existing ModelCalls transport
  and artifact store reused; no registration as a default benchmark arm.
- Validation:41engineering checks pass; offline type/template extraction succeeds
  on all6saved boundary-smoke PUTs with0rejected observations. No real LLM/PUT/
  reference calls, no detection results, no commit/push.

## 2026-11-04 — prospective resource exclusions requested by user

- Audit181remaining PUTs,exclude17source-bound likely resource-heavy programs
  from preparation, BOTH generation prompts and evaluation, as explicitly selected
  by user. Keep source cohort/checkpoints; log effective denominators and task160
  all-base-pass exclusion. No outcome-based selection or retroactive result edits.
- Add optional `--v11-resource-exclusions`, immutable per-task markers and plan
  source/spec/cohort integrity checks. Existing source folder and protocol amendment.
-18targeted checks pass (11existing+7new); full regression/review before resume.
  No commit/push requested.

## 2026-11-03 — user authorizes grouped commits

- User reviewed the change categories and explicitly requested separate commits.
  Source, tests, reports and protocol notes may now be committed on main.
- Checkpoints, runtime outputs, virtual environments and detailed development
  inventory stay local/ignored. No benchmark source or running configuration changes.

## 2026-11-01 — V11 concepts with the existing modern test generator

- User changes workflow: modify existing source in place; no new version folder,
  no commit/push before user review. Separate output data for distinct protocols.
- Add `V11ConceptArm` and `V11ConceptStage` to this existing modular pipeline.
  Reuse original V11 mining/facts/top3/spec fallback only, without the full V11
  hybrid/assertion/expected-output generator. Inherit modern one-call/task
  inputs-only generation, prompt, parsing, reference oracle and PUT evaluation.
- Reuse verified upstream concept caches; missing caches run mining/facts only.
  Selected guidance excludes witnesses, tool inputs and mutant source. Rank-first
  round-robin over visible owners,4cards max, translated AST source locations.
- Track preparation progress/cost independently and compare with plain using
  the existing matched-valid-input method. Preserve modern shortfall exclusions.
- Old full V11 run stopped at user request:288durable case results,4533completed
  result/response/concept artifacts verified unchanged; no automatic resume.
- Validation:26engineering checks pass; upstream-cache check imports525cards from
  264PUTs/28tasks without inference/scoring. Default164task/2296event replay matches;
  original23snapshot hashes and4533stopped-run artifact hashes unchanged.
- Status: implemented, awaiting user review; no new inference or benchmark outcomes
  for this arm, no automatic launch, no commit/push.

## 2026-11-01 — class/module refactor

- Source: equivalent orchestration split from completed concept_reference_v1_recovery;
  existing experiments and artifacts preserved. Shared tested low-level libraries.
- Separate six run types in arms/ and each pipeline stage in stages/.
- Explicit TaskContext, ArtifactStore, ModelCalls adapter and stage dependency order.
- BenchmarkPipeline supports stage insertion and an all-task generation/oracle barrier.
- Default CLI is read-only replay of the completed run; no model construction.
- Validation:15engineering checks pass; independent review cleared. Full164task
  read-only replay/2296events matches inputs/outcomes/full historical summary.
  Original23source/cohort/result hashes unchanged; no new model/native benchmark run.
- Added writable stage_events.jsonl, optional CLI arm selection, witness-only mode
  without a model and configuration-aware cache invalidation.
- Status: complete, remains uncommitted; see VALIDATION.md and README.md.

## 2026-11-02 — remove redundant source copy

- User requests removing redundant code. Removed obsolete `final/v11_clean/`,
  superseded by runtimefix; no active module imports it.
- Keep `final/v11_clean_runtimefix/`: modern concept-only arm imports its mining,
  facts, view, model and sandbox adapters; source hashes remain unchanged.
- Preserve original V11 paper/history sources and every output/checkpoint.
  Active concept-inputs run continues; no commit/push.

## 2026-11-05 — final/src and final/data

- Move current source, runtime, original plain baseline and audit utilities into
  final/src. Consolidate reference/domain/development/fixture data in final/data.
- Migrate the remaining development selection dependency to neutral cohort/dataset
  helpers; keep pre-layout inventory/subset snapshots and rebuild offline. Exact
  task records and all group selections match; only builder hash changes.
- Remove executable code from retired original/recovery/V11 concept experiments;
  keep historical documentation and results, with source recoverable from Git.
- Current entry points use python -m final.src.modular.run/rescore; preserve final/out
  and final/review output locations after moving source deeper.

## 2026-11-05 — boundary prompt v4

- Replace compiled selection and context prompts with the BVA worksheet from
  final/review/boundary_prompt_v4_proposal_2026-11-05.md; literal mode is unchanged.
- Keep origin, alignment, code_quote, reach, infect, side_rules and better_technique.
  Verify origin values and that code_quote occurs in the PUT source.
- Schema boundary-value-analysis-4; existing checkpoints need a fresh output directory.

## 2026-11-05 — boundary selection/context repair (protocol5)

- Separate public domain/quantity evidence from code/edge threshold evidence;
  the same spec rule across sides does not exclude an implementation boundary.
- Default selection budget4096 in both standalone BVA and BoundaryArm; explicit
  selection_truncated status, with no implicit retry or applicability claim.
- Replace ordinary-only context guidance with valid path-sensitive families and
  supported target placements within the existing per-obligation budgets.
- Optional bounded context_requirements are checked after construction and on
  literal fallbacks. Sum construction can preserve a requested palindrome by
  adjusting the center; incompatible shapes and sign/token violations are explicit
  rejections. Unstated/prose reach and propagation remain unverified.
- Keep numeric-string binding safeguards and existing characteristic coverage.
  Schema boundary-value-analysis-5; fresh outputs required, historical runs intact.
- Validation:223modular tests pass, including context-preservation and truncation
  regressions; git diff --check passes. Offline engineering only; no new
  model/benchmark run or efficacy claim.

### Pre-inference review amendment

- Independent review before the user-requested known-bug10 rerun removed two
  residual spec-threshold/rule-change requirements from candidate metadata and
  the context propagation instruction. Same protocol5; no response observed
  before these changes. See the rerun entry in PREREG.md for fixed scope.

### Known-bug10 diagnostic terminal result

- User-requested protocol5 rerun completed10/10:64valid inputs,16received calls,
  bug tasks76/99/124/140vs v4only124. No unknown task calls. Outcome-selected,
  post-hoc mechanism evidence; no detection-rate or efficacy claim.
- All291v4output files unchanged;10input-freeze hashes and stable repeated
  failure evidence verified. Concurrent runtime/pipeline edits from another
  session after launch block full current-tree replay; no hash-guard bypass.
  Exact launch controller source evidence retained. See
  final/review/boundary_prompt_v5_diagnostic_2026-11-05.md and postrun_audit.json.

## 2026-11-06 — compact BVA selection diagnostic (protocol6)

- Compress selection instructions5908→3347characters; retain the exact output
  JSON example, context instructions, candidate data/menu and budgets. No
  task-specific semantic hints added. Only run identity changes to protocol6.
-234modular tests pass. Independent review clears implementation and requires
  documenting the transport change since v5; prospective amendment adds3fresh
  long-selection controls to3short selections plus at most3short contexts.
- Same saved23/72/157PUTs; fresh output boundary_compact_selection3_20261106.
  Frozen v5remains historical context, not the sole prompt comparison.
- Semantic understanding, schema validity and detection are assessed separately;
  no pure-length, efficacy or generalization claim from these post-hoc cases.

### Compact diagnostic result

- Completed3pairs plus2short context calls:8responses/0unknown,25,308tokens.
  All3fresh long-control response texts match savedv5exactly.
- Short23recognizes non-ASCII byte/character difference but selects length0;
  context generates only duplicate ASCII/empty inputs.72retains false operator
  mismatch;157retains it and adds invalid origin=contract on3boundaries.
- Short pipeline:11valid inputs,0detected;234prelaunch tests pass, full read-only
  replay matches.76source/data and312prior-output hashes unchanged.
- Tested candidate retained for review, no expansion/retuning. Report:
  final/review/boundary_compact_selection_2026-11-06.md. No broad promotion or
  pure-length/efficacy conclusion is supported by this three-case diagnostic.

## 2026-11-06 — restore protocol5 for commit

- User selects v5as the stable default. Restore exact selection/context instruction
  bytes and schema5; preserve compact prompt as a review artifact and keep all
  historical outputs. No claim that v5is globally best or semantically complete.
- Next user-authorized grounding trials start from this committed checkpoint;
  experimental changes remain separate and require their own offline audit/review.

## 2026-11-06 — opt-in checked grounding trial (uncommitted)

- Stable v5checkpoint13d92ee9pushed before this experiment. Keep off mode as
  default; checked mode is explicit on BoundarySettings/BoundaryArm.
- Bounded AST receipts expose quantity/unit/transform/scope and logical complement
  of immediate False-return predicates. Unsupported scopes, mutation and shadowing
  remain unknown; source receipts are not spec entailment or bug verdicts.
- Recognized scalar contract types can widen observed-int float neighborhoods.
  Code-point templates control raw input scalar values, distinct from transformed
  ord/byte length. Concrete domain-excluded sides are pruned before context quotas.
- Context goals use UTF-8/non-ASCII and proper-prefix-vs-final-total properties;
  declared properties are checked after construction and unmet goals are recorded.
-44grounding tests plus independent read-only review. Existing10selection prompts
  and menus reproduce v5byte-for-byte in default off mode. Offline saved-selection
  audit identifies16quantity confusion,72scope confusion and157polarity confusion.
- Live6miss diagnostic is authorized/preregistered but not launched: old endpoint
  /models returned404and replacement requested. No new model task calls or efficacy
  result. Preserve all previous outputs; trial awaits endpoint and user review.

### Checked6 terminal diagnostic after endpoint reply

- User resent endpoint; readiness/tokenization6pass and frozen checked6run
  completed:8responses/0unknown,23valid inputs, bug task16(15stable failing inputs).
  Known task tokens26,573. No semantic retries or cohort expansion.
-16selects raw code_point;23recognizes byte/character distinction but omits the
  boundaries field;72recognizes prefix-vs-total but5targeted contexts fail checked
  property;157uses match/domain_lower but includes forbidden atside.
- Full read-only replay matches;79source/data+723prior-output hashes and6input
  freezes verified. Still opt-in/uncommitted; v5commit13d92ee9remains checkpoint.
  Report:final/review/boundary_checked_grounding_2026-11-06.md. Pool and guidance
  changes are confounded; this is post-hoc mechanism evidence, not efficacy.

## 2026-11-07 — executable full10 prompt-style command (not launched)

- Add final/run_prompt_style10.sh, mode755, plus reusable audits.run_prompt_style
  CLI and byte-identical style config archived from the completed3task diagnostic.
- Same10known-bugPUTs×3prompts; exact-request/model/checksum reuse of9completed
  responses means21new calls by default. --no-reuse explicitly requests30fresh.
- Detached run with one-shot worker, source/request/prior hashes, readiness and
  all-input freeze before corrected scoring/replay. No target adjustment/repair.
- bash-n/help/offline full10check,9decode parity checks, corrupt-reuse negative
  control and independent read-only review pass. No model or evaluation launched.

### Full10 endpoint configuration repair

- User's foreground invocation failed MissingEndpoint after /tmpconfig disappeared;
  confirmed0completion attempts in the failed output. Preserve that output.
- Restore shell argument forwarding while preserving the current foreground default.
  --detach is still an explicit option. Resolve private endpoint configuration via
  explicit file/env/process URL, persistent XDG config, then legacy/tmpfallback.
- Validate config before preparing a new run, with actionable sanitized errors.
  Existing transport/model defaults for other pipelines are unchanged.
-8network-free config/CLI tests, shell syntax and outside-repo full10check-only
  pass. Metadata-only check confirms exactQwen27/context8192; no experiment launch.

### Full10 checkpoint continuation after test-file hash interruption

- Exclude tests from new-run production source freezes. An agent test edit during
  the user's run caused the interruption; retain the original snapshot unchanged.
- Add --continue-from for a fresh output directory, importing both received calls
  and inherited reused_calls with exact request/checksum/receipt validation.
  Keep the old worker locked during import; reject unresolved attempts and changes
  to frozen production/data dependencies other than this recovery controller.
-21offline tests PASS. Check-only on the actual interrupted run confirms12reused,
  18remaining calls; all12decoded batches match, old directory hashes unchanged,
  no new completion or native evaluation launched. Prompts/settings unchanged.

## 2026-11-07 — soft BVA is the main boundary pipeline

- Per user instruction, `--arms boundary` now uses soft guidance and a single
  direct JSON-input completion per allocated PUT. Keep the diagnostic prompt
  bytes/settings at20inputs; encode model values without target calculation.
- Move typed selection, templates, compiler/literal construction, context checks,
  worksheet prompts and checked grounding to boundary_value_analysis/legacy/.
  Their audits/tests import legacy explicitly; default generation does not.
- Split task budget equally over visible base-passing PUTs without semantic
  eligibility gating; retain unused-share policy, explicit skips and deduplication.
  Restore the method adapter's invocation loop so CLI methods execute.
- Add soft identity/checkpoints, strict response parser and generation-only
  accounting. Keep old results/manifests; rescore selects original legacy/soft
  accounting from saved configuration. Shared cache imports signature helpers
  directly from CallBuilder, avoiding a dependency on archived BVA types.
-342tests PASS;10saved requests and decoded batches match offline. No live model
  run or new cohort evaluation. Multi-PUT behavior remains an unmeasured extension
  of the one-PUT diagnostic; no general superiority claim or automatic launch.

## 2026-11-07 — opt-in precision tool and concept-direction diagnostics

- Add a scalar float/numeric-string adjacent-neighbor primitive with construction
  receipts and an explicit fixed20seed/expansion policy. Production soft unchanged.
- Phase A uses frozen seeds,0newmodel calls:fixed20detects8PUTs vs soft7,direct6;
  gains99with no original soft loss. Unlimited pool8is reported separately.
- Conditional Phase B uses10newseed+request responses,16206tokens,0unknown or
  truncation. Strict interface admits5responses; seed/concept/generic each4vs
  originalsoft7. Failed gate retained; no repair/retry to rescue primary metrics.
- Separate0model-call envelope audit removes only outer JSON fences. Recovered
  seed/concept/matched-generic each7; only1of8raw directives admitted. Autonomous
  fixed20precision gets8but drops the72negative context while adding2/99.
- Tests cover exact binary64neighbors,string round trips,preserved context,
  raw-index binding,matched quotas,strict parsing and freeze tampering. Reports:
  final/review/boundary_soft_tool_results_2026-11-07.md and phaseA/direction/interface
  JSON receipts. Soft remains main; experimental files uncommitted pending review.

## 2026-11-07 — prepare user-requested full164soft BVA run

- Add run_bva_full controller around the current pipeline, with exact offline
  request identities, source/data copies and guards before dispatch/task stages.
- Full existing cohort:164requested,157eligible,1454base-pass PUTs/call cap;
  preserve7explicit cohort skips.20inputs/task in fixed per-PUT shares, no tools
  or plain regeneration. One-shot detached worker,20minrecorded keepalive,
  progress/checkpoints and automatic terminal replay/report.
-368tests PASS; full-cohort prepare-only and endpoint/tokenizer readiness PASS.
  Controller stops observer writes before final summary to keep replay accounting
  stable. Source/notes archived; unrelated note/test edits cannot interrupt it.

### Isolated frozen-runtime continuation

- Original full run stopped at493responses/52input batches after a live scorer
  source edit. Preserve the old output and the separately modified current scorer.
- Add resume_bva_full to import received checkpoints/history and completed input
  batches into a new output, running the intact archived generator/scorer/native
  worker with isolated imports. Original policy/request identities retained;
  961newlogical calls remain. No canonical unknown attempt is reset or regenerated.
-4recoverytests and a frozen-runtime native/full-repeat/immutable-replay smoke
  pass. New worker PID103140/outputboundary_soft_humaneval164_resume_20261107_195417
  is running and has produced new responses. Historical observer cost is recorded
  separately from new keepalive receipts; active worktree source edits do not
  affect the isolated runtime.

Launch audit:full run started detached atboundary_soft_humaneval164_20261107_171955,
PID78543,exactmodel/context/tokenizer ready,worker lock held and first generation
response received. Current state running; no terminal detection result claimed.

## 2026-11-07 — confirm only initially failing PUT inputs

- First-pass successes stop;fail/error/timeout inputs receive one confirmation
  with the same seed. Detection still requires two failing observations. Reference
  and domain validation keep their existing two observations for all inputs.
- Record original retested indices and limit unstable status reporting to that
  subset. Use a distinct retry checkpoint and policy identity to prevent old
  full-suite repeat files from being interpreted as a subset.
- Tests cover subset indices, transient failures, empty/all-pass batches, cache
  reuse, real-worker outcomes and immutable replay. No-cache batch execution has
  a different input history from the old second full suite;document that limit.

### Commit review of diagnostics and controllers

- Precision audit readers accept both historical full repeats and indexed failure
  confirmations. They preserve original input indices, retain single observations
  for first-pass successes and require two observations for stable value mismatch.
- Full-run guards include package initializers. Continuation plans expose the
  parent keepalive cost separately;no received request or historical retry is reset.
-387modular/development tests PASS.40saved Phase A audit batches are unchanged
  under the compatible reader,with0newmodel/native calls. Precision stays opt-in;
  current full run retains its isolated original runtime and scoring policy.

## 2026-11-07 — evaluation-only infrastructure continuation

- Full generation completed1454responses/164globally frozen batches;worker then
  stopped at33task results on FileNotFoundError spawning bwrap. No PUT result is
  inferred from that infrastructure failure. Binary currently exists and smoke
  passes;exact transient cause remains unestablished.
- Add a model-free continuation using original frozen runtime/scoring,validated
  input ledger,restored visibility and imported native/reference checkpoints.
  Detached controller pins PATH,archives itself and verifies a cold sandbox before
  execution. No unsandboxed fallback or new model requests;one narrowly bounded
  recorded retry is permitted for the same spawn error after a passing smoke.
-4recovery tests PASS;actual workerPID192257past task33,44task results and0model
  attempts at launch audit. Terminal input-freeze/replay checks remain automatic.

### Full164soft BVA terminal result

- Evaluation completed164task records,157eligible/1454base-pass PUTs:1449novel
  valid inputs,61confirmed detected PUTs across22tasks.46PUTs have stable value
  mismatch witnesses;15detections have no stable value mismatch. Outcome-kind
  counts can overlap;resource/exception detections are disclosed separately.
- Global input freeze and all1454generation response hashes match;immutable
  read-only replay passed. Evaluation-only recovery made0model calls and consumed
  no sandbox retry. Parent stopped outputs/checkpoints remain unchanged.
- Generation used1454received calls/1,423,485known tokens;3034encoded inputs lose
  1550cross-PUT duplicates before1484retained inputs and35reference/base rejects.
  This is descriptive full-cohort behavior under20inputs/task,not a matched plain
  or held-out efficacy comparison. Full report:boundary_soft_humaneval164_results_
  2026-11-07.{md,json};no active benchmark worker or automatic rerun remains.
