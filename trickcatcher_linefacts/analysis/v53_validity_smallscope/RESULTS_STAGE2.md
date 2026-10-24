# v53 Stage 2 results: small-scope input concept with the Sonnet `defn` oracle (dev run, vibepass_half, 33 tasks)

Source: `out/analysis/v53_validity_smallscope/stage2/score.json` (102/102 Sonnet answers from 17 batched subagents;
every transcript = Read own prompts + Write own answers only; 0 excluded). Pipeline = PREREG_STAGE2 + amendment 1
(self-review): input source → Stage 1 `open` filter → Sonnet `defn` k = 3 primary quorum → cap 20 → hidden reference.

| input source | inputs (accepted) | confirmed tasks /33 | FA tests | precision | reach |
|---|---|---|---|---|---|
| `scope` (concept: DIMENSION scopes, exhaustive) | 7 075 | **18** | 8 | .97 | 20 |
| `plain` (Sonnet, "small inputs likely to reveal a bug") | 8 467 | **24** | 15 | .96 | 27 |
| `typed` (type-driven small domains, $0) | 6 883 | 17 | 0 | 1.00 | 17 |
| `random_small` (v41 pool, size ≤ 10, $0) | 7 685 | 21 | 0 | 1.00 | 21 |
| `universe` (v49 decisive, report) | 19 469 | 22 | 0 | 1.00 | 23 |
| `universe ∪ scope` / `universe ∪ plain` | — | 24 / 24 | 8 / 14 | .98 / .97 | 27 / 27 |

Matched to `scope`'s count: typed 17, random_small 21 (unchanged). Strict v49 oracle validity = resource-tolerant
validity everywhere (every Sonnet program passed the public inputs).

**Verdict (registered): not promising.** `scope` − `plain` = −6 tasks (plain-only: 56, 61, 65, 66, 77, 131; scope-only:
none); − `typed` = +1 (168, 171 vs 56); − `random_small` = −3. The small-scope concept is *worse* than the plain prompt.

## Mechanism
- **Budget-bound scopes are too small.** Asked to enumerate *all* combinations in ≤ 300 inputs, Sonnet shrinks scopes to
  size ≤ 6 (61/65/66: caption length 1..6; 77: max size 6). The smallest exposing universe inputs on these tasks are
  size 7–10 (DIAGNOSTICS D2). `plain` mixes sizes up to 10–52 and reaches them. On 131 the bug needs size 2 but specific
  digits; the scope fixed the alphabet to {0,1,2,3}. Exhaustiveness trades size and value diversity for completeness at
  sizes where these bugs do not live — the small-scope hypothesis holds at "≤ 10", not at "≤ 6".
- **New reach comes from LLM generation, not from the concept**: 168 and 171 (R7 tasks, no exposing universe input)
  are confirmed by both `scope` and `plain`; the $0 tools miss them.
- **Remaining FA are oracle errors**, not invalid inputs: on 161 (problem shared with 73/74) all three Sonnet `defn`
  programs agree on a wrong value for valid inputs with n, m ≥ 100 (e.g. (200, 120): quorum 450, reference 530); the
  universe has few such inputs. 73/74 are reached but never confirmed for the same reason (common-mode spec error).
- 141: `plain` reaches it, but brute force times out on every exposing input (abstention, as v52). Unreached by every
  arm: 6, 39, 48, 58, 69, 70.

## Reading
- With a strong writer the pipeline works end-to-end: Sonnet `defn` + Sonnet filter + Sonnet `plain` inputs confirm
  **24/33 at precision .96** with 8.5k inputs (Qwen v49 `defn`: 12/33, precision ≈ .6; TC-full: 7).
- The concept again does not help; here it hurts because the instruction ("enumerate all within scope") binds the
  input budget to tiny sizes. Input-side concept effects remain null across v41/v44/v47/v48/v53.
- Left for a fresh cohort: common-mode oracle errors (161 family) and abstention on large exposing inputs (141).
- Process note: a post-score diagnostic accidentally rewrote the Stage 2 reference cache job of task 161
  (`stage2/references/161/generated`); `score.json` is immutable and unaffected, and the cache is content-keyed
  (a rerun recomputes it). The diagnostic was rerun under `stage2/diag161/`.
