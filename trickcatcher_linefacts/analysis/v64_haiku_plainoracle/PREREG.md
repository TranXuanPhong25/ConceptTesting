# v64: does the v49 oracle-family effect survive a stronger writer? (Haiku, dev)

Registered 2026-10-25 (Claude), before any new writer answer or outcome. Dev only (33 vibepass_half PUTs, 24
problems); VibePass held-out excluded.

## Question
v49 (Qwen-32B, k=5): spec-only brute-force oracles (defn 12, brute 10 confirmed tasks, precision ≈ .6) beat the plain
"write a correct implementation" oracle (5, .48), largely through valid-program yield. v55h (Haiku, k=3) put defn at
21/33, precision 1.00, 0 FA, but had no plain-implementation arm. Before amending v56 (fresh cohort) to confirm the family
effect, check whether it exists at all with a stronger writer. If plain-impl ≈ defn with Haiku, the family effect is a
weak-writer artefact and v56 should not be spent on it.

## Design
Copy of v55h (`experiment.py`), same 24 problems, same 8-problem batches, 3 samples per problem from different
subagents, same per-problem split prompt header, same scorer (v49 primary quorum, k = 3, public-test filtering,
resource-tolerant primary + strict sensitivity, cap 20 in hash order, v49 universe ∪ Haiku `plain` generator inputs,
Haiku `open` validity filter).
- `defn`: v55h `defn` answers reused byte-for-byte (v49 defn prompt; no new calls).
- `brute` (new): v49 `brute` instruction, otherwise identical prompt.
- `plainimpl` (new): v49 `plain` instruction ("Write a correct implementation of the function."), otherwise identical.
- Shared `plain` input generator and `open` filter answers reused from v55h, so all three arms see the same inputs and
  filter. New prompts end with the same "Use at most 1024 output tokens" line as v55h.
- Writer: Claude Haiku subagents (model `haiku`), one subagent per batch call (9 per new arm, 18 total), allowed only to
  Read their prompt files and Write their answer files. Answers must pass `validate_answer`; misplaced answers are
  relocated by entrypoint name as in v55h H2 (no content change); otherwise the run is incomplete, no regeneration.

## Outcomes and decision (fixed now)
Per arm: confirmed tasks, confirmed tests, tests, FA tests (invalid / wrong value / unknown), precision, common-mode
problems, abstention. Paired task wins/losses for defn vs plainimpl, brute vs plainimpl, defn vs brute.
Family comparison uses precision, not absolute FA count (the v49 rule gap).
- **Family effect holds with Haiku** if defn − plainimpl ≥ 2 confirmed tasks (paired wins − losses), wins on ≥ 2
  distinct problems, and defn precision ≥ plainimpl precision − .02. → next step: amend v56 with plainimpl/brute arms.
- **Weak-writer artefact** if paired wins − losses ≤ 0 and plainimpl precision ≥ defn precision − .02. → do not spend
  v56 on the family effect.
- Anything else: inconclusive; report, no larger run, no extra samples.
defn vs brute (heading effect) is reported, not decisive. No post-outcome prompt or scorer change.

## Amendment 1 (2026-10-25, Claude; all 144 new answers in, before any execution or outcome)
18/18 Haiku subagents finished. Transcript audit (tool names + paths only): every Read was of the subagent's own
`split/` prompt files; no other file was read, no Bash/search. Three Writes went outside the registered answer paths:
`answers/brute/8c4fd2d4f1a7_1.txt` (a duplicate answer under a non-cohort id, written by brute_1_0, which also first
wrote four answers to the wrong ids and then overwrote them with the right ones) and two one-character
`e91e92700d37_{0,1}.txt.tmp` scratch files. All three moved to `out/.../misplaced/brute/`, never scored.
One answer, `brute/f8603e71e802_1.txt`, has a complete function but no closing code fence (the shared `code_block`
regex then returns the fence line as code, a syntax error). A closing fence was appended, no other change; the original
is kept in `out/.../original/`. After this all 144 answers define their entrypoint. No answer was regenerated.
