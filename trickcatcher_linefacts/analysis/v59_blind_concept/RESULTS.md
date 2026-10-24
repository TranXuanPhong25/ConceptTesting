# v59 results: fault concept as the only PUT information for a code-blind Sonnet generator (pilot, 2026-10-24)

PREREG + Amendment 1 (commits fc02b20, 840963a, 103bd29). 57 Sonnet answers (`claude-sonnet-5-5`) from 21 writers on
neutral paths, audit 21/21 (exactly 2n+1 tool calls), frozen (sha 1fc55992…) before scoring. Dispatch 1 (57 answers made
before the review) discarded unscored. Score: `out/analysis/v59_blind_concept/score.json` (Stage 2 oracle/filter/judging).

| arm (k = 3 per task) | confirmed tasks /6 | tasks | confirmed tests | FA | per-answer reach /18 | exposing inputs from template inputs |
|---|---|---|---|---|---|---|
| `blind` (Stage 2 plain prompt) | 1 | 70 | 1 | 0 | 1 | — |
| `concept` (+ v34 fault concept) | 1 | 70 | 2 | 0 | 2 | 0 of 2 |
| `placebo` (+ same template inputs, no concept) | 2 | 69, 70 | 6 | 0 | 4 | 0 of 6 |
| `code` (+ PUT source, masked) | **3** | 6, 69, 70 | 16 | 0 | **6** | — |

Precision 1.0 in every arm; strict = tolerant; no task reached without being confirmed. Task 48 and 39/58 reached by no arm.

## Verdict (registered): **no signal**
`concept` − `placebo` = −1 task (placebo-only: 69), − `blind` = 0. Not "uninformative": `code` reaches 3 tasks, so the
harness and oracle can confirm these bugs when the generator has the right information.

## Reading
- **The code carries information the concept does not.** Showing the PUT to the code-blind generator triples task reach
  (3 vs 1) and per-answer reach (6/18 vs 1–2/18). The v34 fault concept — the same PUT information compressed into
  sites, fault types, alternatives and template inputs — transmits none of it: concept = blind, and below placebo.
- **Template inputs are not the route either**: 0 exposing inputs in concept or placebo equal a template input; the
  placebo's extra task (69) came from the writer's own inputs.
- So, even where the writer lacks the information, this concept form is a lossy channel: the bug-relevant content (e.g.
  task 6's `max_trials` cap; 69's adjacency condition) is in the code, but the tool's ranked mutation sites do not convey
  it. A concept would have to carry that *specific* behavioural fact, not a generic fault-type label.
- Pilot scale: 6 tasks / 4 problems, k = 3, selected on Stage 2 failure; 1–2 task differences are not evidence. The
  code-vs-concept gap (6 vs 2 answers reaching) is the clearest effect.
