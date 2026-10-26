# V77 combined — prospective registration (2026-10-25)

Status: preparation only. Zero paid calls; no experiment launch or outcome computed.
Parent: v11_fair; all strict_round2/placebo_matched/caps/shared_scorer ON.
K=3, fixed seeds, 8 logical calls and 20 assertions per arm/sample. Physical retries
are separately charged, at most 3 per logical call, with durable reservations.

## Cohorts and decisions
HumanEval: exactly the 113 v11 dev tasks (exclude design6/pilot20), oracle_b01
ref (primary) and full (sensitivity). VibePass: frozen v31 vibepass_half 33 PUTs,
public base tests only, v7_vp class-method hooks, silver reference + contract
scoring after generation freeze. Contract-invalid claimed failures are false positives.
No enlargement, replacement tasks, additional seeds, K increase or completed-run
rerun regardless of outcome. Transport resume reuses identical source/config/cache.

For EACH dataset separately, primary = concept-hybrid-ft vs placebo-hybrid,
paired per task by number of detecting samples among K=3. Ties excluded.
Pass requires wins > losses AND total false-positive assertion count <= placebo.
HumanEval ref uses oracle_b01's emitted invalid/wrong-reference assertions as FP;
full reported separately using the same decision rule. VibePass uses v34's
false_alarm definition on final assertions, including contract-invalid failures.
Secondary pairs: combined vs concept-hybrid, plain-hybrid, toolinput.
Report all tasks, samples, abstentions, unknowns and actual costs; incomplete run
is incomplete, never interpreted as a negative/positive efficacy finding.

## Arms and request matching
Six exported arms: plain, plain-hybrid, toolinput, placebo-hybrid,
concept-hybrid (unaltered v11 fact bundle), concept-hybrid-ft (combined).
Internal concept round1 is shared logically with concept-hybrid as in v11;
plain round1 is shared with plain-hybrid. It is not a seventh reported arm.
Combined gets its own concept round1. Legacy seed formula stays unchanged;
combined seeds use reserved +100000000 offset. Run baseline concept-hybrid then
combined before placebo/plain-hybrid. Placebo/plain strategy request count,
INCLUDING correction retries, equals combined's actual count, as v11 matched
controls do. Baseline concept-hybrid keeps v11 natural missed-hint budget.
Expected-value calls occur only for retained verified round2 inputs. All arms
obey caps; logical shared round1 is counted toward both arm budgets.

## Frozen merge rule (before any outputs)
Fault concepts are line + fault type + surviving alternatives. Port
ft_concepts.py byte-for-byte from v31. Rank by decreasing distinguished surviving
alternatives, decreasing survivor count, v31 type priority, increasing line.
Only groups with a successful distinguishing template witness are eligible;
retain at most one per line. MISSING_CASE supplies witness candidates, not a
line-level fault concept. No reference or scorer participates in construction.
V7 list = original facts.pick(full fact pool with ALL MUTANT/MUTANT-X removed,
k=all), retaining v7 block/DU dedup and eligible kinds, including SPEC fallback.
Merge by alternating V7, FT, V7, FT,..., skipping any line already selected;
when one list exhausts, drain the other. Stop at <=3. No forced empty placeholders.
This gives 2 v7 + 1 FT when available without tuning to scores.
Concept text contains line, behaviour/fault meaning and surviving code edits;
never witness arguments, PUT outputs or alternative outputs. Private mutant
sources are used only for concept-hit verification (difference from PUT on at
least one surviving alternative), never rendered in model prompts.
All v31 template candidates join v7 fuzz witnesses (deduplicated, stable v7-first
order); toolinput takes first3 valid candidates as v11. Combined gets witnesses
only through tool-side tracing; concrete inputs never enter its concept prompt.
Fault-disabled bundling is identity on v11 bundles and uses v11 prompts/seeds.

## Public preprocessing and historical reuse
HumanEval reuses frozen v11 mining/domain strategies and fact/spec bundles,
SHA-pinned with original model/seed provenance; generation alone switches model.
VibePass reuses public-only v7_vp validators/domain strategies/facts if available;
otherwise deterministic public-example type/domain strategy and always-True
validator are used (unknown spec validity, not inferred silver contracts).
V7 machinery still constructs full facts/spec fallback and validates traces.
V31 VibePass phase1/phase2/tool.json reuse requires pinned historical freeze,
matching PUT/public inputs, SHA checks and successful phase outcomes. Tool
subfiles absent from historical freeze are prospectively pinned and checked
against v34 copy. Missing/invalid cache is rebuilt CPU-only, never inferred from
reference or copied historical LLM responses. Generation is entirely fresh.

## Transport, contexts and cost
openai/gpt-oss-120b via official OpenRouter; v76 provider sort=price,
require_parameters=true, max_price prompt .05/M completion .25/M request0;
reasoning low/exclude; temperature .6/top_p .95; no provider/model substitution.
Native Python prompts require text response format (v76 JSON-object format is
incompatible); the content of v11 Python prompts is preserved. Max output16384
including reasoning, max3 charged incomplete attempts, SDK retries0. Exact local
Harmony BPE preflight and runtime input+16384<=131072 gate, never truncate.
Estimate uses current public endpoint metadata, maximum logical call counts
(1,8,1,8,8,8) x tasks x K, planning4096 prompt +2048 completion tokens/call.
This is a planning estimate, not a worst-case spend promise. Record the full
16384-output worst-case separately. Shared calls can reduce physical dispatches.
Total BOTH datasets + any fresh scoring dispatches share one ledger and cap:
min(1.5 * estimate, $10). Frozen HumanEval ref/post responses are reused;
full judges, if needed at launch, use this same model/client/global cap.
403 daily/monthly workspace $2 caps stop immediately; only identical-run resume
after reset/admin change, with denial logs archived outside pipeline, no budget
increase. Unknown usage keeps reservation and blocks subsequent dispatches.

## Prior art / interpretation
V7/v11 dev: concept-hybrid61.0 vs placebo57.7 vs toolinput64.3; matched fairness
removed most earlier advantage. V31:18 vs plain15/33, paired4–1, FA27<=32,
weak result. V34 vs input placebo:8–2 but FA27>23, registered rule NOT met.
V57 ports unchanged v31 templates as legacy control; its path solver is not
imported here. V77 tests combined package with a new model, not proof that
v31 concepts alone causally locate bugs. HumanEval has memorization risk;
VibePass silver reference has limits. No sample enlargement to salvage results.

## CPU gate
Inherited test suite, byte-exact disabled bundle/prompt equivalence, 3 real tasks
per dataset with deterministic mocked LLM transport and real isolated workers,
class-method/FT hit checks, budget/403/unknown-accounting tests and local context
preflight. Mock artifacts only in temporary directories, never production output.

## Pre-output amendment A — numbering, second model, stop rule (2026-10-25)

Registered as v75_combined, renumbered before any output to v77_combined; the
unrelated analysis/v75_deepseek_select is unchanged. This amendment overrides
conflicting preparation defaults above. No paid call, launch, or efficacy output.

DeepSeek is a second separately run/reported model, never pooled with GPT-OSS.
For EACH model and dataset the same primary wins>losses AND FP<=placebo rule,
secondary pairs, six arms, cohorts, K, prompt contents, schemas and scorer apply.
DeepSeek ID deepseek/deepseek-v4-flash-0731, EXACT provider
`{only:['relace/fp4'],allow_fallbacks:false}`, EXACT reasoning `{enabled:true}`.
Public OpenRouter endpoint metadata confirms context1048576, max completion943718,
input $0.0422/M, output $0.1694/M (snapshot in assets). No substitution if unavailable.
GPT-OSS retains v76 routing/low reasoning, output16384. DeepSeek output cap131072
including reasoning (larger than unsuccessful 8192/16384/32768 in v75 selection).
This mitigates truncation; zero paid readiness calls means it does NOT establish
that truncation is impossible. No unsupported reasoning.max_tokens/effort budget.
Relace does not advertise seed; omit API seed there, retaining deterministic local
seeds. Temperature/top_p/response format remain identical across arms/models.

Every dispatched request has exactly system + user roles. Strategy correction
history (prior proposed strategy plus execution feedback) is serialized inside
that user message, identically for both models. No assistant turns and therefore
no assistant reasoning_details passback. Base v11 initial prompts and disabled
bundles remain byte-identical; correction role packing is a disclosed deviation
from v11. One physical dispatch per slot for BOTH models: empty and length
answers are cached and never resent. Any empty answer makes that arm/sample a
failure (zero emitted tests/detections, not missing data); report empty counts.
Ledger records reasoning tokens, finish_reason, empty_answer_count and cost for
every received response, retaining reservations for unknown charges.

VibePass uses the existing v7_vp **validity=none** public-only CPU fact cache
(all33 SHA-pinned), never the evalplus/contract cache. This is the v7 fact/fuzz
adapter already permitted in public preprocessing above; no reference access.
Deterministic public-example strategy/True validator serves fresh round2 only.
Fault-stage reuse is mandatory with hashes AND exact public source/candidate
matching: no silent rebuild. Candidate filtering and survivor selection match
v31 exactly (including literal topology bounds and comparable outcomes).
All fault-type concepts still use the byte-identical v31 ft_concepts.py.

Launch one model/dataset per process. Serial task-major order: every arm and all
K=3 samples of a task finish before the next task. Dataset cap shares are
proportional to frozen task counts113:33 and cannot transfer. Model hard cap is
min(1.5*current-price planning estimate,$10), sum of its two dataset caps; all
scoring dispatches share the same dataset ledger. DeepSeek planning output32768
includes reasoning; GPT-OSS planning output2048. Full-output cost also reported.
No cap increase, cross-model/dataset borrowing, enlargement, replacement or rerun.
A workspace daily/monthly $2 403 or login/usage error stops immediately with exact
error, no retry. Only explicit same-run resume after workspace reset may replay
cached slots. Unknown costs stop; do not clear reservations.

At a terminal cap stop, unfinished-task artifacts remain, but analysis includes
ONLY the deterministic leading task prefix with all six arms and all3 samples.
The offline --finalize-partial command freezes this selection before scoring;
no efficacy GO/NO-GO is issued for partial data. Report planned/completed/excluded
counts, each arm failure/empty count, spend and stop reason. Once finalized,
partial output is terminal and cannot resume or enlarge. Workspace pauses may
instead resume identically without finalization. Never filter based on outcomes.

DeepSeek context preflight uses a labelled conservative envelope (2 tokens per
UTF-8 byte +4096 framing) rather than misusing the Harmony tokenizer. GPT-OSS
uses pinned official Harmony counts. Both gate input+output at every dispatch;
no prompt truncation. Provider wrapper/billed tokens may differ from local counts.

Legacy v7_vp cache MUTANT metadata omits source for its AST operators. Recover
the source using that exact stored operator index and the original make_mutant
AST routine; require original line and rendered mutant text to match before use.
Source is private verification metadata, not prompt content. Class-method hooks
and legacy mutant helper names are the existing v7_vp fixes. Baseline cached
concept/placebo texts and their order remain unchanged. The v11 coverage adapter
also includes class methods when executing fresh classification; no alternative
fact pools or hidden-contract regeneration is used.
