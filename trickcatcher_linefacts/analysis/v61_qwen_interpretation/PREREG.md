# v61: interpretation concept before a definitional oracle, Qwen writer (v55 design on Qwen)

Written 2026-10-25 (Claude), before any v61 call or output. User: "thử mấy cái hướng còn mở … chạy qwen thôi" and
"cho codex review với làm đi". Open direction: v55 (another session, Codex writer) asks whether an explicit
interpretation step removes common-mode oracle errors (v53 Stage 2: 73/74/161 all-Sonnet-wrong on valid inputs).
v61 asks the same with the weak writer used in v49. Review: Codex read-only (`codex exec -s read-only`), no Claude
subagents (user rule); must-fixes become amendments before any score.

## Prior art
v49 (Qwen defn 12 vs brute 10 /33, concept only raises valid yield), v52/v53 Stage 2 (Sonnet defn + open filter 24/33;
remaining FA = common-mode on 161 family), v55 (Codex, same three arms, in progress elsewhere; not duplicated: different
writer). Weak-writer prior from 64 rows (concept ≈ placebo for Qwen) is the expected outcome; the test is cheap because
the `defn` arm is reused.

## Arms (oracle families; 33 vibepass_half tasks, k = 5 programs per task, as v49)
Prompt = v49 `gen.messages(task, arm)` (statement, public tests, signature; no PUT), system v49 SYSTEM, temperature 0.8,
top_p 0.95, max_tokens 1024.
- `defn`: the v49 Qwen defn programs, reused unchanged (v49 seeds `v49/<cid>/defn/<i>`; digest-checked).
- `interp`: "First list in comments every ambiguity in the problem statement (`# AMBIGUITY:` lines), then choose the
  interpretation that agrees with every public example and state it in one `# INTERPRETATION:` comment." + the v49 defn
  instruction verbatim. Seeds `v61/<cid>/interp/<i>`.
- `placebo`: "First write an 80–120 word comment block on the code formatting conventions you will follow." + the v49
  defn instruction verbatim. Seeds `v61/<cid>/placebo/<i>`.
New calls: 33 × 5 × 2 = 330 (1 worker; queued after v60 on the same endpoint).

## Inputs, filter, oracle, scoring (identical for all arms; references only in `score`)
Inputs = the v49 decisive universe per task (`O.score_inputs` records), filtered by the frozen Stage 1 `open` checks
(public drop rule, as Stage 2/v59/v60). Per family: program validity = Stage 2 rule (strict = equals PUT on every public
input; resource-tolerant primary), v49 primary quorum (largest differing group ≥ 2 and > V/2, V = valid programs), cap 20
in sha256 order, v48/v49 official-path judging, own execution/reference roots. Reported per family: confirmed tasks,
confirmed tests, FA tests, precision, valid programs, common-mode (valid exposing inputs where ≥ 2 finishing valid
programs all return the same incorrect value: equal to the PUT = miss, else = FA), abstention.

## Decision (registered; same shape as v55)
**Promising** iff `interp` confirmed tasks ≥ `defn` + 2 and ≥ `placebo` + 2, with positive per-problem net on ≥ 2 distinct
problems against each, `interp` FA tests ≤ min(`defn`, `placebo`) FA tests, and fewer distinct problems with common-mode
wrong values than both. Otherwise **no-go**. No larger run or extra samples to rescue a borderline result.

## Caveats
Reused `defn` programs were generated 2026-10-23 on the same weights (v49 CHANGELOG notes two endpoints with identical
weights); `interp` comments consume part of the same 1024-token budget (equal requested budget, not equal usage; usage
reported). Dev tasks only; Qwen may recall LeetCode problems.

## Amendment 1 (2026-10-25, after the Codex read-only review; before any v61 generation or score)
- **M1 freeze scope:** `frozen.json` also hashes every external file `score` reads — v49 defn programs and task records
  (PUT outcomes, universe), v41 PUT/reference caches of all 33 tasks, Stage 1 `open` checks and the helper sources
  (v49 oracle/gen, v53 smallscope/validity, v59 run, v48 e2e, iorel); `freeze` refuses absent externals and preflights
  every new program record (schema + prompt digest); `score` re-checks the whole frozen state before and after scoring.
- **S1 historical control:** `defn` is a historical control (generated 2026-10-23, same served alias and 8192 context; weight
  revision, tokenizer and quantization identity cannot be proven from the alias). Stated as a limitation, not repaired.
- **S2 reporting:** per-family token usage and finish reasons are added; common-mode is reported with valid-program counts
  (fewer finishing programs can lower common-mode; read it together with `valid` and abstention).
- Notes accepted: conclusions are limited to the fixed v49 universe (39/58 have no accepted inputs; 69/70 and 73/74 have
  no exposing universe input), so interpretation recovery cannot be observed there.
