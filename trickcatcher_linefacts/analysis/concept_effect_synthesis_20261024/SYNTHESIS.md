# When do concepts help? Synthesis of 64 concept-vs-control comparisons (2026-10-24)

Direction 3 of the user's "thử hết": an empirical-study reading of every experiment that compared a concept arm with a
control (plain, placebo, random, matched no-concept, raw vs tool). Data: `rows.json` (64 rows + 20 skipped, each with a
file:line source; compiled by a read-only subagent, cross-checked against `analysis/concept_mechanism_20261024/
HISTORICAL_MECHANISM_ROWS.json` for v34, v47, v49 and against v52 `score.json`). No new runs.

## 1. Headline
- **No LLM concept arm ever passed a registered GO.** The only GO is offline (rank-2 hint selection, CPU), and its LLM
  run (v7_mutref) had no signal.
- **One registered win over both plain and placebo: hyb-v3m2** (Qwen-7B, 62.0 vs 53.0 / 47.0 bugs per run). It came from
  unequal round-2 budgets (placebo 1.27 vs 3.58 calls/sample); v11_fair matched them and the gap closed (61.0 / 57.7 /
  55.7, concept vs placebo 26/22, p = .67).
- Verdicts by writer tier:

| tier | NO-GO | no signal | ceiling | rule met (weak) | invalid | GO |
|---|---|---|---|---|---|---|
| weak (Qwen 1.5B–35B) | 18 | 18 | 0 | 4 | 1 | 0 |
| strong (Codex, Luna, Sonnet, Gemini) | 3 | 7 | 5 | 0 | 2 | 0 |
| none (CPU proxy) | 3 | 1 | 0 | 0 | 0 | 1 |

## 2. The pattern (what the 64 rows agree on)
1. **Weak writers cannot use the concept; the gain goes to whatever else the arm gets.** Every Qwen "win" decomposes into
   extra calls (hyb-v3m2, v7, v8-strict), concrete tool inputs (witness-only = 43.0 of toolinput's 64.7; c+t ≈ toolinput),
   template inputs (v34: 0/16 confirmed tests reuse concept inputs, placebo-matched 8–2 detection but FA 27 > 23), or
   program yield (v49: concept headings only raise valid programs, 93 vs 78; paired 10/10). Placebo-controlled Qwen rows
   are all "concept = placebo" once budgets match.
2. **Strong writers derive the concept themselves; every arm hits the same ceiling.** v28 (Codex, 16–17/20 every arm),
   v53_sonnet_tester (5/6 every arm), v54 (6/6), v52 (5 vs 4), Sol6.1, Luna v23, ULT C1–C8, hybrid C1. With the code in
   view, a code- or execution-derived concept is redundant.
3. **Input-side concepts never beat matched random or plain** (v41, v42, v44, v47, v48, v53 Stage 2 — weak, strong and CPU
   alike). Selection is not where the bugs are lost; reach comes from sampling (v41: 22/33) or from generation.
4. **Oracle-side, the family matters, not the concept.** Spec-only brute-force programs (v49 defn/brute) confirm 10–12/33
   at precision ≈ .6 vs TC-full's 7 at .23, and remove common-mode (3–5% vs 28%); with Sonnet the same pipeline plus a
   validity filter reaches 24/33 at .96 (v53 Stage 2). The concept headings themselves add nothing (v49, v52).
5. **Concept taxonomies hurt weak models and are neutral for strong ones** (F4/F4b validity groups, v53 validity: typed
   = lines = open masks on all 32,311 inputs).
6. **Revision/identification concepts fail on normative status**, not on extraction (v40, v43, v50: the model explains
   the mismatch correctly but leaves the spec relation unknown/rejected; E8 ambiguity is invented away in every run).

## 3. Why — one sentence
Every concept we gave was derivable from material the writer already had (code, spec, or tool output it also saw), so a
weak writer could not exploit it and a strong writer did not need it. A concept can only add value when it carries
information the writer does not have — tested directly in v59 (fault concept as the *only* PUT information for a
code-blind Sonnet generator). **v59 result: no signal.** On the 6 tasks the Stage 2 pipeline never reached, blind 1/6,
concept 1/6, placebo 2/6, PUT source 3/6 (per-answer reach 1 / 2 / 4 / 6 of 18; FA 0 everywhere). The code carries
bug-relevant information that the fault-concept form does not transmit; a useful concept would have to state the specific
behavioural fact (a cap, a condition), not a fault-type label with mutation sites.

## 4. Direction 2: the definitional concept as the thesis concept
Evidence that survives: an oracle built from the **definition of the task** (enumerate the objects the statement talks
about, check the condition, aggregate — written without the PUT) is a better oracle family than PUT-guided variants:

| oracle family | writer | confirmed /33 | precision | common-mode on exposing inputs | source |
|---|---|---|---|---|---|
| defn (definition headings + brute force) | Qwen-32B, k=5 | 12 | .59 | 3.0% | v49 |
| brute (brute force, no headings) | Qwen-32B, k=5 | 10 | .62 | 4.9% | v49 |
| plain spec implementation | Qwen-32B, k=5 | 5 | .48 | 0.5% (few valid) | v49 |
| TC-full PUT-guided variants (native rule) | Qwen-32B, k=10 | 7 | .23 | 28.2% | v49 |
| defn + `open` validity filter + plain inputs | Sonnet, k=3 | 24 | .96 | 161-family only | v53 Stage 2 |

Caveats a reviewer will raise: (a) defn ≈ brute, so "concept" here must mean *the definitional view itself* (instruction
to follow the statement literally), with plain implementation and PUT-guided variants as controls — not the three comment
headings; (b) v49's family comparisons were secondary/report-only and failed their registered rule on absolute FA count
(a rule gap: the family that emits more tests is penalised); (c) all numbers are on the 33 dev PUTs (24 problems).
Confirmation path already registered by another session: **v55** (Codex: interpretation concept vs defn vs placebo on the
same oracle, dev) and **v56** (fresh LiveCodeBench cohort, 60 problems, defn oracle pipeline with matched placebo and a
public-seeded tool pool). A thesis claim on the definitional oracle should wait for v56 and use a precision-aware rule.

## 5. What this means for the thesis
- Defensible as an empirical contribution: a placebo-controlled, preregistered map of where concept guidance does and does
  not act in LLM test generation, with the weak/strong mechanism split above.
- Defensible as a method contribution only if v56 confirms the definitional-oracle family on fresh tasks, or if v59-type
  concepts (information the writer lacks) show a signal.
- Not defensible: "LLMs write better tests when given concepts derived from the code they already see".
