# v60 results: behaviour-fact concept for a code-blind Qwen input generator (2026-10-25)

PREREG + Amendment 1 (commits cef00d3, dcb97ef; Codex read-only review `CODEX_REVIEW1.md`, no Claude subagents).
290 Qwen2.5-Coder-32B calls (66 fact extractions + 224 generator answers), 0 errors, frozen (sha 7ac2c253…) before
scoring. Oracle/filter = frozen Stage 2 Sonnet answers (no new Claude calls). Score: `out/analysis/v60_behavior_fact/score.json`.

| arm (k = 2) | confirmed tasks /33 | confirmed tests | FA | per-answer reach /66 | generator answers that ran |
|---|---|---|---|---|---|
| `blind` (Stage 2 plain prompt) | 5 | 81 | 0 | 8 | 35/66 |
| `concept` (+ FACT lines extracted from the PUT) | 12 | 124 | 0 | 14 | 41/66 |
| `placebo` (+ FACT lines written from the spec only) | **13** | 197 | 0 | 16 | 32/66 |
| `code` (+ masked PUT source) | 10 | 132 | 0 | 12 | 29/66 |

Precision 1.0 everywhere. Failed generator runs are mostly MemoryError (blind 27, code 24, concept 14, placebo 15) and
SyntaxError (placebo 10, concept 4).

## Verdict (registered): **no signal**
`concept` − `placebo` = −1 task (concept-only 56, 66, 96, 171; placebo-only 46, 77, 85, 87, 163). `concept` − `blind` =
+7 on 8 problems (passes that half of the rule). Not uninformative: `code` (10) > `blind` (5).

## Reading
- **Any fact block helps this writer; PUT content does not.** Facts written from the spec alone (no PUT information)
  are as good as facts extracted from the PUT (13 vs 12), and both beat blind by 7–8 tasks. The gain is a generic prompt
  effect (a structured list of input conditions makes Qwen write runnable, targeted generators), not information about
  the program.
- `concept` ≥ `code` (+2): for a weak code-blind writer, Qwen's own fact summary is at least as usable as the raw code —
  but the spec-fact placebo matches it, so this is not evidence that the PUT information is used.
- Same pattern as v59 (Sonnet) and the 64-row synthesis: placebo-matched, the concept content adds nothing.
- Caveats: k = 2; generator failure rates differ by arm (executable-input yield is part of the treatment package);
  budgets equal per task (blind/placebo 24 distinct prompts, concept/code 32).
