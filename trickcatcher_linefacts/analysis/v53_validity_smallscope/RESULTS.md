# v53 Stage 1 results: validity checks from the statement (dev run, vibepass_half, 33 tasks / 24 problems)

Source: `out/analysis/v53_validity_smallscope/score.json` (72/72 Sonnet answers, all parseable; every subagent used only
Read(own prompt) + Write(own answer) + hand-back, checked from transcripts; 0 excluded). Truth = hidden reference contract
on the v49 decisive universe. PREREG + amendment 1 (Codex review).

| arm | checks written | invalid caught (recall) | valid rejected | exposing rejected | Sonnet defn FA (6 tasks) | Qwen defn FA (33) |
|---|---|---|---|---|---|---|
| concept (RANGE/RELATION/STRUCTURE, line by line) | 81 | 12842/12842 (1.000) | 0 | 0/4084 | 56 → **0** | 145 → 108 |
| lines (line by line, untyped) | 79 | 12842/12842 (1.000) | 0 | 0 | 56 → 0 | 145 → 108 |
| open (F1b-style) | 224 | 12842/12842 (1.000) | 0 | 0 | 56 → 0 | 145 → 108 |
| tool (numeric bounds) | — | 1854/12842 (0.144) | 0 | 0 | 56 → 36 | 145 → 125 |

No public input was rejected by any LLM check (0 drops). Confirmed tests lost: 0 everywhere; after filtering, the cap-20
lists refill with correct tests (+36 Sonnet, +9 Qwen confirmed tests), no confirmed task lost or gained.

**Verdict (registered): not promising** — recall margin concept − open = 0.00 (< 0.10); taxonomy effect (concept −
lines) = 0.00. All safety checks pass for every arm.

## Reading
- Ceiling: with a strong writer, translating the statement's Constraints into executable checks is solved by any
  prompt (the three answers differ — 224 vs 81 vs 79 checks — but classify every universe input identically and exactly
  like the hidden contract). The constraint concept adds nothing measurable; the numeric tool catches 14%.
- Practical result: Sonnet `defn` oracle + any Sonnet validity filter has **0 FA** on the v52 tasks (56 → 0) while
  keeping every confirmed test. The remaining Qwen FA (108) are wrong programs, not invalid inputs.
- So FA is closed for strong writers; what remains is reach/abstention (DIAGNOSTICS D2) → Stage 2 (small-scope
  generation). If a concept is to matter there, it has to be in *what is enumerated* (v52 task 65), not in validity.
