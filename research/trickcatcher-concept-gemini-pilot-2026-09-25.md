# TrickCatcher / EvalPlus: Gemini concept pilot

## Question and scope

Does a structured, ConceptCoder-inspired intermediate description improve bug-exposing input generation beyond an equally expensive generic planning step? This tests **Gemini-generated concept hypotheses in prompts**, not ConceptCoder's learned statement classifier or multi-task fine-tuning.

Source: [TrickCatcher artifact](https://github.com/RinCloud/TrickCatcher), commit `a0d285a77efff7c93fc280d606497d9de5e1defe`; EvalPlus `0.3.1`, HumanEvalPlus release `v0.1.10`. We used the first 12 `put0.py` Python programs after HumanEval/0 (tasks 1–12). Task 0 appears in the official input-generation prompt example and was excluded. A post-generation scan of up to 150 official EvalPlus plus inputs per task found a canonical/PUT divergence in 11 of the 12; task 1 showed none across its 83 plus inputs.

The source code and docstring were given to native Vertex `gemini-3-flash-preview` at temperature 0. All arms used TrickCatcher's official direct-input template and requested 10 literal input lists per task:

- **Baseline:** the official template, one Gemini call per task.
- **Generic:** one Gemini call for three broad edge-case ideas, then the official template with that plan, two calls per task.
- **Concept:** one Gemini call to extract `expected_property`, `suspected_shortcut`, and `separating_input_relation`, then the official template with that card, two calls per task.

No canonical code, EvalPlus contract, bug label, gold input, or fixed implementation was passed to Gemini or the concept extractor. After generation, `ast.literal_eval` parsed the input lists. The evaluator applied the official EvalPlus contract, executed canonical and PUT code separately with timeouts, and counted a bug exposure only for a valid input on which the canonical succeeded and the PUT raised or produced a different result. This is an ablation of TrickCatcher's **direct-input prompt**, not a reproduction of its full variant-generation and generator-based method.

## Paired results

| Arm | Tasks exposed / 12 | Valid inputs / 120 | Exposing inputs | Minimum Gemini calls |
| --- | ---: | ---: | ---: | ---: |
| Official baseline | 5 | 119 | 8 | 12 |
| Generic plan | 7 | 117 | 16 | 24 |
| Structured concept | 7 | 119 | 15 | 24 |

The generic and concept arms exposed **exactly the same task IDs**: 2, 3, 5, 6, 7, 9, and 12. Both gained tasks 6 and 12 over baseline. At the task level, exact paired McNemar p = 0.5 for baseline vs either planned arm and p = 1.0 for generic vs concept. The sample is far too small for an effectiveness claim, and tasks differ in bug difficulty. The concept arm provides **no observed gain over equal-call generic planning**.

Concrete witnesses include `truncate_number(1.0)` (canonical `0.0`, PUT `1`), `intersperse([0,1,2], 4)` (canonical retains the zero, PUT drops it), and `longest(['A','b','C'])` (canonical `'A'`, PUT `'a'`). The three arms all missed `make_palindrome` (task 10), although 92 of the first 150 official plus inputs produced a canonical/PUT difference in a post-generation screen.

## Failure analysis

- Some concept cards were valid and localized a real shortcut (`if number == 1: return 1`, the zero sentinel in `intersperse`, `max_so_far = 0` in `rolling_max`), but the baseline or generic arm also found those bugs.
- Other cards proposed input relations outside the official valid domain: unbalanced parentheses for tasks 1/6, unequal-length XOR strings for task 11, or very long recursion as the presumed fault for task 8. Those hypotheses were not checked before Gemini generated inputs. Contract filtering prevented invalid inputs from becoming false bug reports, but the extra concept text did not help discovery.
- Task 10 illustrates the remaining challenge: the concept card articulated a plausible palindrome-suffix weakness, yet its ten concrete strings did not realize a distinguishing case. A semantic hypothesis alone did not solve input construction.
- The generic arm generated slightly more exposing inputs (16 vs 15) with the same two-call budget. No shuffled-concept placebo or second model was run because the concept arm failed the pre-set gate of beating generic planning.

## Decision

Do not scale this prompt-only Gemini concept arm or describe it as ConceptCoder working for test generation. A next experiment needs a **verified intermediate representation**: generate a candidate input from the concept, check its documented-domain constraints, and use execution feedback to refine the separating relation. Keep the canonical program private to evaluation. If a trained ConceptCoder-style concept predictor is later built, compare predicted concepts with static labels and shuffled concepts before attributing any gain to concept learning.

The code is in [`trickcatcher_pilot`](../trickcatcher_pilot/README.md). Raw generated and evaluation JSONL files are under `/tmp/trickcatcher_*_12*.jsonl`; this note preserves the measured result because those files are ephemeral. Generated inputs were parsed as literals, and execution took place in child processes with timeouts.
