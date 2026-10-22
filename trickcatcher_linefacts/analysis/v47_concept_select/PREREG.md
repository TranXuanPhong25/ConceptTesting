# v47 (registered as "v46"; renumbered) extended tool methods + LLM concept selection (concept accuracy) on vibepass_half

Written 2026-10-22 before any code output. User diagnosis: missing tool-method coverage and concept accuracy/taxonomy.
v44 (no-go) showed: a perfect pick of one concept instance doubles coverage over a random instance (class 20 vs 10),
and 11 tasks were unreachable. v45 exploratory (hidden inputs, diagnosis only): 3 of them show no functional exposure
(likely performance bugs), 4 need values far beyond the public range (spec allows them), 4 need repeated special
values (e.g. consecutive -1 sentinels, specific 0/1/2 grids).

## Prior art
v44 (perfect-pick ceiling only, no LLM selection); v43_concept_identify (fixture binding with a fixed operator
vocabulary, no-go); v36 (LLM localization); v31–v34 (tool-ranked fault concepts given to the LLM). New here: the LLM
**selects** concept instances from a menu built by the tool, scored against random selection and the perfect pick.

## Part A — two new tool methods (CPU, public examples + spec text only)
- `spec_range`: for each spec constraint on elements/int values whose upper bound exceeds the pool's maximum, inputs
  from the first 40 pool samples with values drawn log-uniformly in [lo, hi] (variants: all elements, one element;
  int arguments). Seeded `random.Random(case_id + variant)`.
- `value_biased`: for list arguments of ints (and lists of int lists), 40 inputs whose elements are drawn from the
  multiset of public example values at that position with probability 1.0 (`only_public`) or 0.7 (`mostly_public`,
  else uniform in the public range), lengths uniform in [public min, 2 × public max] (≤ 30), grid rows keep public
  row lengths.
- Reported: C1 over all eight input-side kinds (v44's four + these two... six input kinds) vs v44's 22; per new kind
  ideal coverage, matched random, random instance (v44 definitions). No gate on Part A.

## Part B — LLM concept selection (GPU endpoint, qwen2.5-coder-32b-instruct)
- Menu per task: all input-kind instances (class, boundary, spec_range, value_biased, coverage arcs, surviving
  mutants), deduplicated by flagged set, each with a one-line natural-language description built by the tool (e.g.
  "nums: all elements equal", "nums[i] = 10^9 (spec upper bound)", "code branch L42 -> L43 not run by public tests",
  "mutant L42: `<` -> `<=`"). At most 40 instances, round-robin over kinds in a fixed order, ids M1..Mn.
- Prompt: spec, signature, numbered code, public tests, menu; ask for the 3 ids most likely to reveal a bug where the
  code disagrees with the spec, JSON {"picks": [ids], "reasons": [...]}. Temperature 0, one call per task per arm.
  Arms: `spec+code` (primary) and `spec-only` (no code, no coverage/mutant instances in the menu).
- Score: covered@3 = some picked instance's ≤ 32 shown inputs contain a confirmed exposure (batch AND official, v41).
  Random-3 = exact expected coverage of 3 random menu instances; perfect = some menu instance covers.

## Go / no-go (concept accuracy signal)
LLM selection is a promising concept-accuracy mechanism iff, for `spec+code`: covered@3 ≥ E[random-3] + 3 AND
covered@3 ≥ 0.5 × perfect. Reported: spec-only arm, per-kind share of picks, parse failures.

## Amendment 1 (2026-10-22, after an independent read-only review, before any model call or reference/exposure)
Renumbered v47 (v46_mutoracle_fixed exists; v45_unreachable also collides with v45_mutjudge, kept as is).
- **Part A is exploratory**: its two methods were designed after v45 looked at hidden inputs of these same tasks.
  Reported on v44's definitions: union of v44's four kinds (vs v44 21; task-level reproduction check of the four v44
  kinds), union of six, C1 including confirmed pool exposures (vs 22), per kind ideal / matched random (k = reach) /
  random instance (batch). Generated inputs run one batch per kind; skipped counts reported. ("eight" in Part A was a typo:
  six input kinds.)
- Menu deduplicated **across kinds** on the shown inputs (≤ 32), in round-robin order before the cap of 40; first label
  kept, merged count reported. Perfect is reported over the menu (gated) and over all instances.
- Part B reported baselines (no extra calls): first-3 menu items, one random instance from each of 3 random distinct
  kinds, kind-matched random (random instances of the kinds the model picked), and the Poisson-binomial tail
  P(X ≥ covered@3) under random-3. Gate unchanged.
- Mutant descriptions are diffed on the PUT but displayed from the comment-masked view the model sees. `parse_picks`
  also reads `M<n>` ids from a string or truncated picks field. Call records store a prompt sha256; score requires all
  call records (else verdict `incomplete`) and records per-case errors. Seeds include argument index and kind;
  `log_uniform` returns exactly `lo` 10% of the time when lo ≤ 0 (documented).
- Re-review (before any output): score refuses to run with missing call records and writes `score_incomplete.json`
  (not frozen) if any case errors; generated kinds' matched random uses all flagged inputs as universe (v44). c1 here
  re-checks the first 20 pool exposures (v44 also generated ones and oracle kinds): close to, not identical with, 22.

## Amendment 2 (2026-10-22, transport only, during generation; no score/exposure computed)
The shared Qwen32B endpoint serves one request at a time and another run (v46) queues on it, so queued requests timed
out at 600 s and ngrok returned ERR_NGROK_3004. Generation now uses 1 worker and a 3600 s client timeout. Prompt,
model, temperature, seed, max_tokens and parsing are unchanged; 51/66 call records written before this change are kept
as is (immutable, prompt sha256 stored), and the remaining calls resume from that cache.
