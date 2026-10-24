# v53 Stage 1: validity concept — spec constraints as executable checks (dev run, vibepass_half)

Written 2026-10-24 (Claude) before any v53 model call, after `DIAGNOSTICS.md`. User decisions (2026-10-24): writer =
Claude Sonnet subagents; develop on the dev cohort `vibepass_half` first (this is a **dev run**, no claim), mine a fresh
LiveCodeBench cohort later for the claim; the VibePass held-out (66 PUTs, `HELDOUT_RUNBOOK.md`) stays untouched.
Amendment to `../v49_defn_oracle/PLAN_NEXT_v50.md` R7 ("only on a fresh cohort"): relaxed to "develop on dev, claim on
fresh", by the user's choice.

## Question
v52: with Sonnet the spec brute-force oracle is right on every valid input; all 56 FA were invalid inputs, and all of
them violate a constraint written in the statement (20 numeric bounds, 36 relations between arguments). Does a
**constraint concept** — each line of the statement's Constraints section typed as RANGE / RELATION / STRUCTURE and
written as its own executable check — recover input validity better than open mining (B5/F1b style) and than the
numeric-bound tool, without rejecting valid or bug-exposing inputs?

## Prior art (version tree)
v3m/v3m2/F1 (RBCTest-style mining with quote verification), **B5/F1b** (open mining, per-condition checks, drop checks
that reject a known-valid input: best on HumanEval, FA halved), F4/F4b (15 concept groups: worse with Qwen 7B, it turned
output conditions into input conditions), F5 (conditions in the generation prompt: no effect), v7 mined validity.
External: RBCTest (ICSE'26), AutoCode validator (ICLR'26: best-of-3 on self-written valid/near-valid cases). New here:
the concept is anchored to the Constraints lines with a RELATION type (cross-argument constraints), strong writer.

## Arms (one Sonnet subagent per distinct problem per arm: 24 problems × 2 = 48 calls; k = 1)
Context for both LLM arms = v49 prompt context (statement incl. Constraints, public tests, signature; never the PUT).
Answer = one python code block defining checks `check_1(<params>) -> bool`, `check_2(...)`, … each preceded by a
one-line comment.
- `concept`: "Go through the Constraints section line by line. For each line write one check, preceded by a comment
  `# [RANGE|RELATION|STRUCTURE] <the constraint line>`: RANGE = bounds on one value, length or element; RELATION = a
  condition linking two or more arguments; STRUCTURE = a property of one argument (sorted, distinct, permutation,
  character set, …). Only conditions the caller must guarantee; never conditions on the answer." (No RELATION examples:
  the D1 relations come from this dev set and must not be written into the prompt.)
- `open` (B5/F1b-style): "List every condition the input arguments must satisfy according to the problem statement. For
  each condition write one check, preceded by a comment `# <condition>`."
- `tool` ($0): `menu_fixed.constraints_report` numeric bounds (lengths, values, elements) as checks.
Same tool step for all arms (B5/F1b step 4): a check that returns False or raises on any public input is dropped;
`is_valid` = all kept checks (a check that raises on a universe input counts as rejecting it; reported).
Subagents may use only Read (own prompt) + Write (own answer); verified from transcripts, violators excluded.

## Measurement (no oracle needed; truth = the hidden reference contract, as in v48/v49)
On the v49 decisive universe (33 tasks; inputs per task as executed in v49):
- invalid inputs caught (recall over contract-invalid inputs), valid inputs rejected, **bug-exposing inputs rejected**
  (exposing = official reach where v49 computed it, else valid ∧ ref ≠ PUT, as `plan_rules.exposing`);
- effect on emitted tests (cap 20, v49 order): FA tests removed and confirmed tests lost for v49 Qwen `defn` (33 tasks)
  and v52 Sonnet `defn` (6 tasks), when filtered inputs are dropped before the oracle;
- per check: kind tag, dropped on public inputs, rejections.

## Decision (dev; promising ⇒ Stage 2 + fresh-cohort replication, not a claim)
`concept` is promising iff recall ≥ `open` + 0.10, exposing inputs rejected ≤ `open`'s, and confirmed tests lost ≤
`open`'s (both oracles pooled). Reported against `tool` as well. Otherwise the validity concept is closed for this line
and Stage 2 (small-scope generation) uses the better of `open`/`tool` as its validity filter.

## Stage 2 (not registered yet)
Small-scope exhaustive valid inputs + Sonnet `defn` oracle (k = 3) vs v48 universe and random small inputs; separate
PREREG after Stage 1.

## Amendment 1 (2026-10-24, after an independent read-only Codex review; before any call)
- **Arms**: `concept` (Constraints line by line + RANGE/RELATION/STRUCTURE tags), new **`lines`** control (line by line,
  untyped) to isolate the taxonomy, `open` rewritten as a one-call **F1b analogue** (F1b observation wording: types,
  ranges, lengths, allowed characters or elements, relations between parameters; atomic conditions; stated or
  necessarily implied; reject guesses), `tool`. Shared rules in every LLM prompt: caller-only, never answer conditions,
  unique `check_k`, strict bool, builtins only, never raise. 24 problems × 3 arms = 72 calls.
- **Protocol**: a non-bool return raises (rejection, counted); duplicate names / no code block / syntax error =
  parse error. A violating answer (tool use other than Read own prompt + Write own answer, or parse error) is re-spawned
  once; if still invalid, the problem is dropped from all arms (paired) via `excluded_problems.json`. **No verdict while
  any included answer is missing or unparseable.** `tool` bounds go through the same public-input drop rule.
- **Losses**: confirmed tests lost/gained as set differences (cap-20 refill), task lost/gained per oracle.
- **Decision**: `concept` promising iff recall ≥ `open` + 0.10 AND valid-rejection rate ≤ 1% AND exposing inputs
  rejected ≤ `open`'s AND, separately for the Qwen and Sonnet `defn` oracles, no confirmed task lost and confirmed tests
  lost ≤ `open`'s. `concept` vs `lines` (taxonomy effect) is report-only with the same safety checks.
