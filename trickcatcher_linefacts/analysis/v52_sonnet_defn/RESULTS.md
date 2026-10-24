# v52 pilot results: v49 definitional concept with Claude Sonnet writers (6 tasks, k = 3, exploratory)

Source: `out/analysis/v52_sonnet_defn/score.json` (36/36 programs; every subagent used exactly Read(own prompt) +
Write(own answer) + hand-back, checked from the run transcripts; 0 excluded). Prompts, validity, universe, quorum,
cap and judging = v49. Tasks fixed by the PREREG rule (selected for Qwen failures): 141, 46, 87, 65, 161, 103.

## Headline (decisive universe, primary quorum rule, cap 20)

| writer / arm | confirmed tasks (/6) | correct | tests | FA tests | valid programs |
|---|---|---|---|---|---|
| Sonnet defn | **5** | 62 | 118 | 56 | 18/18 |
| Sonnet brute | 4 | 44 | 100 | 56 | 18/18 |
| Qwen defn (k = 3, same tasks) | 1 | 20 | 40 | 20 | 7/18 |
| Qwen brute (k = 3) | 0 | 0 | 0 | 0 | 3/18 |

Per task (Sonnet defn / brute): 141 0/0, 46 1/1, 87 1/1, **65 1/0**, 161 1/1, 103 1/1. Outcomes are identical on every
task except 65.

## Mechanism (v48 decomposition adapter on all decisive inputs)
- **Every Sonnet FA is an invalid input** (56/56 per arm; 0 PUT-right, 0 wrong value). With Qwen, 55–57% of FA were
  wrong programs (v48/v49). With a strong writer, the spec program oracle is correct wherever the input is valid.
- Remaining misses are **abstention**: 141 (both arms) — all 62 exposing inputs time out (`variants_failed`); 65 brute —
  all 20 exposing inputs time out.
- The one concept win (65) is an enumeration-space effect: `defn` enumerates what the statement quantifies over (splits
  into groups ≥ 3 × one letter per group), `brute` enumerates all 26^n strings (`itertools.product`) and times out.
- Memorization proxy: implementation AST similarity to the PUT 0.09–0.32 (no copies).

## Reading (pilot; 6 tasks, a 1-task difference is not evidence)
- Writer strength dominates: on Qwen's failure tasks Sonnet confirms 4–5/6 vs Qwen 0–1. Contamination is possible
  (LeetCode problems), stated in the PREREG.
- The concept's only effect again comes before the oracle (v49: more valid programs; here: a feasible enumeration
  space); given programs that finish, defn = brute.
- With a correct oracle, the two binding problems left are both on the input side: **validity** (all FA) and
  **size** (brute force cannot judge large exposing inputs). These match PLAN_NEXT_v50 R5 (validator concept, B5/F1b
  baseline) and R2/R7 (small-scope exhaustion), and point to where a concept could act next.
