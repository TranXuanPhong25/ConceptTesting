# Can a concept intermediate improve Gemini bug-exposing tests?

## Claim being tested

This experiment tests whether **structured, task-specific semantic hypotheses** help Gemini generate inputs that expose real benchmark bugs. It does **not** use ConceptCoder's trained concept head. In the realistic arm, Gemini derives three fields from the buggy PUT and its docstring: `expected_property`, `suspected_shortcut` (grounded in PUT code), and `separating_input_relation`. A second Gemini call receives this card plus TrickCatcher's official direct-input prompt. The matched generic arm spends the same two calls, first brainstorming three edge cases and then receiving the same input prompt. Canonical solutions and contracts remain private to evaluation.

Source: [TrickCatcher, ACL 2025](https://aclanthology.org/2025.acl-long.20/) and [released artifact](https://github.com/RinCloud/TrickCatcher), pinned at `a0d285a77efff7c93fc280d606497d9de5e1defe`. Oracle: EvalPlus `0.3.1` / HumanEvalPlus `v0.1.10`. Generator: native Vertex `gemini-3-flash-preview`, temperature 0, thinking budget 0, output cap 1200 tokens. Each arm requested at most ten input lists per PUT. Inputs were parsed as Python literals; the EvalPlus contract checked validity; canonical and PUT executions ran in separate timed processes. A PUT is exposed only if a valid input succeeds on the canonical solution and the PUT raises or returns a different value. No canonical code, contract, gold test, or patch was passed to the realistic generator or concept extractor.

The first exploratory 12 PUTs (HumanEval/1–12) gave 7/12 exposed tasks for both generic and concept, versus 5/12 with the one-call official baseline. A separate *leaky ceiling diagnostic* on HumanEval/13–25 (12 available PUTs) gave generic 8/12, source-only concept 9/12, and reference-informed concept 8/12. The reference-informed teacher saw canonical code to produce its card; that arm is not deployable or evidence for the realistic method. No gold card was manually edited after generation.

## Confirmatory slices

After those pilots, we froze the prompt schema and selected the next two ordered ranges without looking at their oracle outcomes: HumanEval/26–60 (32 available PUTs) and HumanEval/61–95 (34 available PUTs). A formatting sensitivity check on the first range found that Gemini sometimes added or omitted one list wrapper despite the official format. We applied a deterministic **lenient wrapper parser** to both arms' saved raw responses and froze it before the second range. It repairs only wrappers inferable from the function signature; it does not invent values or alter model text. Both arms produced 637 parsed inputs over the 66 tasks under this parser.

| Slice | Generic task exposure | Correct concept task exposure | Paired two-sided McNemar p |
| --- | ---: | ---: | ---: |
| HumanEval/26–60 | 21/32 | 25/32 | 0.125 |
| HumanEval/61–95 | 18/34 | 24/34 | 0.146 |
| **Combined** | **39/66** | **49/66** | **0.0213** |

Across the 66 task pairs, 13 were exposed only by correct concepts and 3 only by generic planning. The task-level lift is **+10/66 = +15.2 percentage points**; a seeded nonparametric task bootstrap gave a descriptive 95% interval of **+4.5 to +27.3 points**. Generic produced 83 exposing inputs among 609 contract-valid inputs; concept produced 128 among 617. Input counts are secondary because ten inputs from one PUT are correlated. Restricting to 63 tasks where both arms had at least one valid input still gives **48/63 concept vs 38/63 generic**, exact paired p = 0.0129.

## Content placebo

We rotated saved concept cards to another PUT with the same parameter count and annotation type. Exact-signature singleton groups were excluded. The generator then used the identical concept-formatted prompt with a **wrong** card. This tests whether task-specific content matters beyond extra structured text, while acknowledging that an obviously mismatched card can itself be distracting.

| Matched population | Shuffled concept | Correct concept | Exact paired p |
| --- | ---: | ---: | ---: |
| 58 PUTs with a same-signature donor | 29/58 | 44/58 | 0.000061 |
| 54 PUTs where both generated valid inputs | 29/54 | 41/54 | 0.000488 |

In the both-valid comparison, the arms had nearly identical valid-input counts (shuffled 521, correct 519). Twelve PUTs were exposed only by correct concepts and none only by shuffled cards. This is stronger evidence that the **content** of the hypothesis matters, not merely the ability to emit more parseable inputs.

Representative valid witnesses generated in the concept arm: HumanEval/27 used a non-ASCII string (`'éÀñÖ'`) against an ASCII-only case-flip shortcut; HumanEval/40 used `[0, 0]` against a three-sum implementation that reuses a value as if it were a distinct element; HumanEval/64 used `'yay'` against a vowel counter that compares the character with the final character instead of checking its position; HumanEval/82 used a 31-character string against a hard-coded list of prime lengths; HumanEval/92 used `(1, 1, 1)` against a special case that accepts three equal numbers as a sum triple. All were accepted by the EvalPlus contract and had different canonical/PUT behavior.

## Interpretation and limits

The held-out trend repeats in two adjacent ordered ranges and survives a same-signature content placebo. It supports the narrow claim that **a concept-shaped, task-specific intermediate can improve Gemini's bug-exposing input generation on these EvalPlus PUTs**. It does not establish that ConceptCoder's learned concepts work here: the extractor was Gemini itself, no concept predictor was trained, and the benchmark is public enough for model contamination to be possible. Generic and concept arms ran sequentially rather than in randomized order. The first range's lenient-parser analysis was defined after examining a format failure; the second range used the frozen parser from the start. The placebo card may contain irrelevant identifiers, which could harm it independently of semantic falsity. Report the generic control and both-valid sensitivity alongside the placebo rather than treating the placebo alone as proof.

The next step for an actual ConceptCoder extension is to train or tool-label statement-level `property`, `shortcut`, and `input relation` concepts, measure concept prediction accuracy on held-out code, and feed **predicted** rather than Gemini-self-generated cards to the same generator. Then repeat the paired and shuffled ablations on a fresh benchmark such as TestCase-Eval Task 2 with an adequate correct-solution oracle. Do not give the labeler hidden fixes or canonical outputs at generation time.

## Reproduce

Code: [`trickcatcher_pilot`](../trickcatcher_pilot/README.md). The two primary generated JSONL pairs are `/tmp/trickcatcher_{generic,concept}_{26_60,61_95}.jsonl`; the lenient evaluation files add `_lenient_eval.jsonl`. The shuffled files use `shuffled_concept` in the same pattern. Results can be rechecked with:

```bash
.venv/bin/python -m trickcatcher_pilot.paired \
  --a /tmp/trickcatcher_generic_26_60_lenient_eval.jsonl \
  --a /tmp/trickcatcher_generic_61_95_lenient_eval.jsonl \
  --b /tmp/trickcatcher_concept_26_60_lenient_eval.jsonl \
  --b /tmp/trickcatcher_concept_61_95_lenient_eval.jsonl
.venv/bin/python -m trickcatcher_pilot.paired \
  --a /tmp/trickcatcher_shuffled_concept_26_60_lenient_eval.jsonl \
  --a /tmp/trickcatcher_shuffled_concept_61_95_lenient_eval.jsonl \
  --b /tmp/trickcatcher_concept_26_60_lenient_eval.jsonl \
  --b /tmp/trickcatcher_concept_61_95_lenient_eval.jsonl \
  --both-valid-only
```

Raw outputs live in `/tmp` and are ephemeral; this note preserves the measured counts and protocol.
