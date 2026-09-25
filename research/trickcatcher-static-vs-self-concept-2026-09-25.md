# Static concept vs Gemini self-inferred concept: fresh TrickCatcher slice

## Question and protocol

Can a deterministic, source-only concept card match or improve a Gemini-self-inferred concept card for generating bug-exposing inputs? This is **not** the trained ConceptCoder method. The static card comes from fixed AST rules plus the PUT docstring (`trickcatcher_pilot/static_concepts.py`); the self card is the existing Gemini three-field hypothesis. Both are appended to the same official TrickCatcher direct-input prompt. The unchanged official baseline controls for one-call cost; a generic edge-case-planning arm supplies a two-call reference without concept fields.

We used the next ordered range, HumanEval/96–130: **30 available PUTs** (five IDs had no `put0.py`). The static rules, source selection and card schema were fixed before oracle scoring. Some early PUT source files (not reference solutions or outcome labels) were inspected while designing generic AST rules; this is a new oracle-outcome slice, not a fully blind source holdout. The arms ran sequentially, static then self then generic then baseline, with Vertex `gemini-3-flash-preview`, temperature 0, thinking budget 0, output cap 1200, and at most ten input lists per PUT. Baseline and static use **one** Gemini call per PUT (generation only); self and generic use **two** (planning then generation). Thus generation-call budget is equal, but total LLM cost is not.

The parser and evaluator were frozen from the prior [66-task validation](trickcatcher-concept-validation-2026-09-25.md). The deterministic lenient-wrapper parser changed **zero** parsed input counts in this slice relative to the strict parser. EvalPlus contracts and canonical code were used only after generation. A task is exposed only when a generated input satisfies the contract, the canonical function returns, and the PUT raises or returns a different result.

## Results

| Arm | Gemini calls/task | Exposed PUTs | Contract-valid inputs | Exposing inputs |
| --- | ---: | ---: | ---: | ---: |
| Official direct-input baseline | 1 | 17/30 | 265/276 | 30 |
| Generic edge-case plan | 2 | 19/30 | 254/262 | 34 |
| Static concept card | 1 | 20/30 | 275/280 | 47 |
| Gemini self-inferred concept card | 2 | 22/30 | 263/274 | 45 |

Primary unit is PUT exposure, not individual input. Exact two-sided paired McNemar comparisons:

| A vs B | A-only PUTs | B-only PUTs | p |
| --- | --- | --- | ---: |
| Baseline vs static | none | 108, 122, 128 | 0.250 |
| Baseline vs self | none | 111, 114, 116, 122, 128 | 0.0625 |
| Generic vs static | 101, 111 | 108, 115, 127 | 1.000 |
| Generic vs self | 101 | 114, 115, 116, 127 | 0.375 |
| Static vs self | 108 | 111, 114, 116 | 0.625 |

On the 27 PUTs for which **both** static and self generated at least one contract-valid input, static exposed 19 and self 22 (three self-only, zero static-only; p = 0.25). This filter is a sensitivity check, not the primary endpoint; it excludes task 108, where self generated no valid inputs. Generic-vs-self both-valid: 18/25 vs 20/25 (p = 0.5). Differences in individual exposing-input totals should not be treated as independent observations.

## What happened in the discordant cases

- HumanEval/114: self inferred that the `len(nums) == 2` shortcut returns the smaller element but misses a still-smaller sum of two negatives; `[-1, -2]` is a valid witness. Static rules merely suggested length boundaries and missed this relation.
- HumanEval/116: self inferred that `bins = [[] for _ in range(length + 1)]` can be too short for a one-element input with many set bits; `[255]` is a valid witness. Static saw a subscript but not this cross-variable invariant.
- HumanEval/111: self found a double-space input that makes the PUT count an empty token; static did not generate it. Its written explanation about multi-character words was not itself a valid-domain witness, illustrating that useful inputs can emerge from an imperfect concept card.
- HumanEval/108: static generated four valid exposing inputs involving negative numbers. Self produced three incorrectly wrapped scalar inputs for a list parameter, so none passed the contract. The frozen parser did not repair that shape.

The static annotator's weakness is semantic depth: it extracts the documented behavior and suspicious AST operations but cannot generally infer the relation between a shortcut and its violated property. Its strength is cost and stability: no concept-inference API call, and 275/280 generated inputs were valid here. The LLM arm has richer hypotheses but occasional malformed inputs and unsupported hypotheses. Both concept arms exposed every PUT that the official baseline did, but their extra three/five tasks are too few for a decisive paired result. On **this** fresh 30-PUT slice, neither static nor self differs reliably from generic planning, and self does not reliably beat static. Combined with the earlier 66-PUT generic-vs-self result, this remains promising but insufficient evidence for preferring a self-inferred concept over a cheap static one.

## Reproduce

Code: [`trickcatcher_pilot`](../trickcatcher_pilot/README.md). The official TrickCatcher artifact is pinned to `a0d285a77efff7c93fc280d606497d9de5e1defe`; evaluator uses `evalplus==0.3.1` and HumanEvalPlus `v0.1.10`. Generated raw, parsed and scored JSONL files currently live in `/tmp/trickcatcher_{baseline,generic,static_concept,concept}_96_130*.jsonl` and are ephemeral. Re-run each arm with `python -m trickcatcher_pilot.run --arm ARM --start 96 --limit 35 --out FILE`, then `trickcatcher_pilot.reparse`, `trickcatcher_pilot.evaluate`, and `trickcatcher_pilot.paired` as described in the package README. Seven focused tests pass.

Next experiment: freeze the static rules and compare again on another unseen benchmark/slice with randomized arm order and repeated generation seeds. To test actual ConceptCoder transfer, train or otherwise independently evaluate a concept predictor, then use *predicted* cards in the same generator; these two prompt-only cards cannot establish that result.
