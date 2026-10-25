# CHANGELOG v77_combined

Registered as v75_combined, renumbered before any output (2026-10-25).
Status: **PREPARED ONLY**. No paid calls, launch, efficacy output or git commit.
Continued the partial folder; inherited v11_fair history is retained below.

## Completed continuation

- Active PREREG_V77.md and pre-output amendment A specify the exact <=3-hint
  alternating v7/FT merge, controls, primary rules, model packages and stop rule.
- Retained v11 strict round2/Hypothesis selection, K3, matched placebo/plain
  strategy request counts, eight-call/twenty-assertion caps and HumanEval scoring.
  Six exported arms: plain, plain-hybrid, toolinput, placebo-hybrid,
  concept-hybrid and concept-hybrid-ft. ft_concepts.py is unchanged from v31.
- All33 VibePass public bundles built and frozen in assets/public_bundles using
  SHA-pinned v7_vp validity=none fact/fuzz caches and exact frozen v31 phases.
  Corrected missing v31 candidate topology filter/survivor equivalence. No silent
  rebuild on hash/request mismatch. Reconstructed legacy AST mutant sources with
  original index/line/text checks. Included class methods in fresh coverage.
- Fixed failing test fixture's missing entry. Added HumanEval113 fault-disabled
  bundle/prompt/seed equivalence, per-model mock3-task e2e for both datasets,
  ledger/403/cap/context tests and exact DeepSeek payload checks.
- Two models run/report separately; same prompts/schemas/arms/cohorts/scorer/rules
  within each pipeline. Shared public CPU inputs, separate model outputs, caches,
  ledger and protocol freeze. Feedback/correction history packed in user content
  for both models; no assistant turns or reasoning_details passback. This role
  packing is a disclosed difference from legacy v11 correction turns.
- DeepSeek enabled reasoning/output131072; one dispatch per slot for both models.
  Empty answer fails arm/sample, no physical resend or empty-strategy correction
  resend; nonempty malformed-strategy corrections remain registered v11 logic.
  Ledger records reasoning tokens, finish reason, empty counts and billed costs.
- Serial task-major all arms/allK; dataset caps cannot transfer. Terminal partial
  selection is a whole paired prefix, frozen before CPU scoring and descriptive
  only. Workspace403/login/usage errors stop immediately with exact error.

## Costs and context (current public OpenRouter metadata 2026-10-25)

| Model | Estimate HE / VP / total | Cap HE / VP / total |
|---|---|---|
| GPT-OSS120B | $4.95710208 / $1.44764928 / $6.40475136 | $7.43565312 / $2.17147392 / $9.60712704 |
| DeepSeek V4 Flash | $65.9719471104 / $19.2661438464 / $85.2380909568 | $7.73972603 / $2.26027397 / $10 |

Maximum14892 logical calls (shared round1 double-counted conservatively),
planning4096 prompt +2048 GPT /32768 DeepSeek output including reasoning.
At current .03/.15 and .0422/.1694 USD/M prices. Full-output projections:
GPT $38.42850816; DeepSeek $333.230063616 (all calls at output caps16384/131072).
Full-cohort completion, especially DeepSeek, is NOT promised under these caps.
No cap increase, borrowing, pooling or enlargement. Fresh full-oracle scoring
calls share that dataset's ledger; primary ref scoring can be reported CPU-only
if full-sensitivity judges cannot fit the remaining cap.

Preflight730 public baseline/CPU-combined initial requests and labelled future
strategy envelopes: GPT max10140+16384<131072; DeepSeek conservative byte bound
max87224+131072<1048576. All actual corrections/finals gate at dispatch. Future
feedback is unknown. DeepSeek provider tokenizer is unavailable locally: this
is explicitly a conservative envelope, not an exact tokenizer claim. No paid
readiness call proves absence of truncation. Public metadata snapshots and
cost/preflight details are frozen under assets/. Preparation spend $0.

## CPU verification and launch commands

Final tests and mock evidence are recorded in REVIEW_V77.md. CPU preparation:

```bash
/tmp/concepttester-v74-venv/bin/python -B -m trickcatcher_linefacts.pipelines.v77_combined.prepare_cpu
/tmp/concepttester-v74-venv/bin/python -B -m pytest -q -p no:cacheprovider trickcatcher_linefacts/pipelines/v77_combined
```

After new explicit user go-ahead, launch each model/dataset separately:

```bash
bash trickcatcher_linefacts/pipelines/v77_combined/run_openrouter.sh --launch --model gpt-oss-120b --dataset humaneval
bash trickcatcher_linefacts/pipelines/v77_combined/run_openrouter.sh --launch --model gpt-oss-120b --dataset vibepass_half
bash trickcatcher_linefacts/pipelines/v77_combined/run_openrouter.sh --launch --model deepseek-v4-flash --dataset humaneval
bash trickcatcher_linefacts/pipelines/v77_combined/run_openrouter.sh --launch --model deepseek-v4-flash --dataset vibepass_half
```

Outputs: `pipelines/v77_combined/out/combined/<model>/<dataset>/`; each has its
own transport ledger, protocol, prepared bundles and dataset generation freeze.
The wrapper validates args before silently sourcing scripts/openrouter_env.sh;
V77_PYTHON defaults to /tmp/concepttester-v74-venv/bin/python. Worker interpreter
and library versions remain pinned in config; temporary environments must exist.
CPU terminal prefix reporting, without model calls:
`python -B -m trickcatcher_linefacts.pipelines.v77_combined.run_v77 --finalize-partial --model MODEL --dataset DATASET`.
Finalization is terminal. Pause/resume must keep exact code/config/global ledger;
unknown charges stop and retain reservations. No automatic launch or commit.

## Files and limits

Renamed package/config/module/run/test/PREREG/lock references; PARENT.json preserves
historical parent hashes and records new numbering/ports. INPUTS.json pins source
cohorts, public facts and v31/v34 tool phases. ASSETS/PREPARED manifests protect
new assets/protocol files. memory/v77-combined.md, MEMORY.md own line and thesis
framing updated. Other sessions' analysis/memory files remain untouched.
Baseline HE113 complete CPU fault construction remains production preparation;
only3 HE mock fixtures are frozen now (all113 disabled equivalence passed).
VibePass has all33 ready public bundles. No hidden reference enters construction.

## Inherited v11_fair history (superseded operational commands)

# CHANGELOG v11_fair

Status: **implemented, not yet run on GPU**.

Base: copied `pipelines/v7/` into `pipelines/v11_fair/`, removed bytecode directories, set VERSION to `v11_fair`. Implements Final comparison protocol fixes 2, 3, 4 and 6 from `PREREG_PENDING.md` and CONCEPT_WEAKNESS section 4 B1. No commits or pushes, as explicitly requested. The copied PREREG snapshot remains unchanged; central PREREG and all other pipelines remain untouched.

## Changes versus v7

- `strict_round2` (default true): concept-, placebo- and plain-hybrid contribute only verified selected inputs in round 2. Exclude round-1 calls, preserve selection order, and request expected values for exactly the retained calls, with no extra-test wording. Skip that request if none remain or fit the assertion budget. Reject expected assertions containing additional PUT calls. Omitted/invalid expected responses retain v8's explicit None placeholder, counted in `strict_missing_expected`. This is real generation, not a CPU-reconstructed experiment arm.
- `placebo_matched` (default true): placebo's actual round-2 strategy requests, including retries, equal concept-hybrid's for the same task/sample, as plain already does. Cycle through missed placebo hints, or available placebo hints when all are covered; empty hint sets use the existing control prompt. Request count matching and targeted selection are recorded and checked.
- `caps` (default true): all seven generation arms are limited to eight logical LLM calls and twenty assertions per sample. Parse full completions rather than silently cutting each to ten; truncate in generation order and record `dropped_assertions`, including logical shared round-1 drops. Reserve one expected-value call slot. Strict mode separately records `dropped_round2_inputs` for selected inputs excluded before any expected-value request because assertion slots are full.
- `shared_scorer` (default true): export one recursive comparator for floats (task atol, relative 1e-6), lists, tuples and dictionary values, plus an outcome comparator distinguishing exception types/timeouts/success. Both evaluation routes, their input metrics and diagnostics, oracle expected-value comparisons and oracle base filtering use it. The oracle and evaluation now read atol from the same oracle dataset; historical evaluation data omit that metadata. Assertion argument construction keeps Python semantics. Changed-scoring oracle execution caches require a fresh output directory.
- Reports add per-arm D_I, D_IO, detecting-sample counts, correct/all failing assertion counts, precision and false-alarm rate on that same failing-assertion denominator. Invalid-input failures enter only the denominator. Oracle reports expose own-expected and replacement-oracle metrics in `fair_metrics.json`; evaluation retains its v7 columns and writes the added metrics beside eval.jsonl.
- Outputs and verification artifacts stay under this copy's `out/`; workers receive explicit sanitized fairness flags. Generation manifests record enabled flags. With all flags false, v7 prompts, request hashes, seed policy, per-completion extraction cap, result schema and report aggregation are preserved (new package provenance/run IDs necessarily differ).

## Files touched

Modified copied files: `EQUIVALENCE.md`, `config.json`, `evaluate.py`, `gen_evaluation.py`, `gen_prompts.py`, `oracle_b01.py`, `paths.py`, `run_v4.py`, `test_equivalence.py`, `v4_evaluation.py`, `v4_runtime.py`, `CHANGELOG.md`.

Added files: `.gitignore`, `README.md`, `equality_audit.py`, `fair_generation.py`, `scorer.py`, `test_fair.py`.

`out/` contains offline CPU verification artifacts and is ignored by the local `.gitignore`; no __pycache__ remains. Other copied source files, templates and paper/vendor sources were not changed.

## Verification results

- 18 unit/integration tests pass, including actual network-isolated CPU evaluation and oracle workers; cached clients raise on cache miss.
- All flags off: both 133-task bundles identical; 2,793 matching first cache requests / 1,995 distinct hashes, zero misses; 21-row generation replay on tasks 0/4/16 at K=1 with 36 cache hits, zero differences.
- All flags off report: 51/51 oracle lines identical on identical recorded observations and cached judge decisions; full evaluation report text and metrics also identical to actual v7 aggregation.
- Shared scorer only: all 29,224 assertions across 2,793 rows audited on the same captured CPU outcomes. **64 assertions changed verdict; all involve floats/tolerance**. The complete list is in `EQUIVALENCE.md`, and compared values/atol are in the JSON artifact linked there.
- All Python sources parse; no bytecode directories remain.

See [EQUIVALENCE.md](EQUIVALENCE.md) for exact commands, scope, artifacts and the two recorded classifier-timeout fallbacks. Optional full fresh execution check c and full K=3 round-2 regeneration were not run; equivalence of the full report is tested on identical observations to avoid v7's documented set-order/deadline/memory nondeterminism. No held-out generation, GPU run or LLM/network call was attempted: this task explicitly required CPU/offline verification. Real strict prompts and matched/capped production outputs therefore remain to be run on GPU with authorization. External baseline adapters are outside this requested folder and were not modified; the cap constants and scorer API are exported for their future integration.
- 2026-10-14 (Claude): check c (fresh full CPU re-execution of v7's recorded run, flags off) finished:
  2785/2793 evaluation rows identical; 8 rows differ in a PUT/canonical outcome of one assertion (set-order /
  deadline / memory boundaries documented in README: tasks around rows 546-562, 966-984, 2726). Oracle: 13,282 calls,
  0 cache misses; report differs by at most 0.3 bug/run per arm (e.g. concept-hybrid ref 67.0 -> 66.7, tc column up
  to 1.3). Accepted as runtime nondeterminism, not a behaviour change. Output: out/humaneval/equivalence/equivalence.json.
- 2026-10-14 03:50 (Claude, PREREG dev sanity amendment 2): v4_evaluation.py MemoryError guard (same as v7_mutref
  1b67d00); evaluate run with a 3600 s sandbox via analysis/v11_eval_longtimeout.py. test_fair 18/18 OK.
