# v55h results: interpretation concept for the definitional oracle, Claude Haiku writer (dev, 33 tasks / 24 problems)

Source: `out/analysis/v55h_haiku_interpretation/score.json`. 264/264 Haiku answers (33 subagents, transcripts clean),
v55 prompts byte-identical; Amendments H and H2. Inputs: v49 universe ∪ Haiku `plain` generator, Haiku `open` filter;
oracle k = 3, primary quorum, cap 20 in hash order; all three arms on the same inputs and filter.

| arm | confirmed tasks /33 | tests | FA | precision | common-mode problems |
|---|---|---|---|---|---|
| `defn` (v49 prompt) | 21 | 411 | 0 | 1.00 | 0 |
| `interpretation` (concept) | 21 | 411 | 0 | 1.00 | 0 |
| `placebo` (equal-length formatting comment) | 21 | 411 | 0 | 1.00 | 0 |

Paired wins/losses of `interpretation` vs both controls: 0/0. **Verdict (registered): not promising.**

## Checks
- Not an artefact: answers differ in every file, and the programs behave differently (non-finishing and abstention
  counts differ between arms on 20/33 tasks, e.g. 77: 785 / 533 / 1013 non-finishing calls). The emitted tests and
  their labels still coincide on every task: given a valid input, all three arms' quorums agree with the reference.
- Every program in every arm passed the public tests (strict = tolerant = 3/3 on all tasks).
- Sensitivity for H2 (8 answers moved by entrypoint, which deviates from v55 Amendment 2's "incomplete" rule): the arms
  are equal on every task, so dropping the affected problems from all arms leaves the result unchanged.

## Reading
- With Haiku as the writer the pipeline confirms **21/33 at precision 1.00 and 0 FA**. For comparison, Sonnet
  reached 24/33 at .96 in v53 Stage 2, with different generator and filter answers. The 161 common-mode error
  of Sonnet does not occur with Haiku's programs.
- There is no common-mode error left for the interpretation concept to remove, so the oracle side is at ceiling for
  this cohort even with a small writer. The unconfirmed tasks are reach/abstention: 141, 61/65/66, 6, 39, 48, 58,
  69, 70, 73, 74.
- Cost: 33 Haiku subagents, about 70–95k subagent tokens each. The 6 Codex calls of v55 used about 23% of the 5-hour
  Codex quota.
