# ConceptCoder VD labels in TrickCatcher's original C++ input prompt

## Result

On 26 paired C++ TrickyBugs PUTs, the unchanged [TrickCatcher](https://github.com/RinCloud/TrickCatcher) direct-input prompt exposed **7/26** bugs with Gemini. Appending statement-level labels from the released [ConceptCoder](https://arxiv.org/html/2603.23470) VD annotator also exposed **7/26** after checking the problem's input constraints. There were no task-level wins in either direction (exact paired McNemar p = 1). This pilot finds **no improvement** from directly injecting ConceptCoder's vulnerability concepts into TrickCatcher's C++ prompt.

The initial differential score appeared to be 7/26 versus 8/26. Its sole concept-only witness for `p02616` declared `N=200000` but supplied only 696 integers. Three reference programs agreed on an output while reading incomplete input; the value was outside the task's input format. The post-hoc spec check correctly rejects it. This matters because reference agreement alone is not a validity oracle.

## Paper and prompt provenance

- Target paper: [TrickCatcher, ACL 2025](https://aclanthology.org/2025.acl-long.20/). The baseline uses its released `Datasets/TrickyBugs/PromptTemplates/geninput_direct` **byte-for-byte** at artifact commit `a0d285a77efff7c93fc280d606497d9de5e1defe`, SHA-256 `26d075a69cc99a00b7ddd6095634cdc0468fcc54c6a7b09bc6f4a87498f2832b`. Both arms substitute only `{pro_des}` and `{code}`. The concept arm appends the annotation block afterward and is an extension of that paper prompt.
- Concept source: `ConceptCoder_org/code/design_concept/design_and_annotate_VD_concepts.py`, copied from the authors' released artifact. Only its seven VD labels were passed to Gemini; `if_statement` was omitted. The original `get_indices` raises `IndexError` on a C++ `subscript_expression` with fewer than three child nodes. A wrapper adds a child-count guard while leaving the artifact source untouched. Without that guard, 235/331 PUTs crash the annotator; with it, all 331 run and 239 have at least one of the seven VD labels. This is a documented compatibility patch, not byte-identical annotation execution.
- Specifications and up to three independent C++ references came from [TrickyBugs v2 on Zenodo](https://zenodo.org/records/10252289). The 1.59 GB ZIP matched the published MD5 `93d10f3872957c2a3e549cb0d74e3275`. We selected the first 30 sorted C++ PUTs with at least one VD label; 26 had a description and references in this release. Selection was made before Gemini or oracle scoring.

## Execution

Generator: Vertex `gemini-3-flash-preview`, temperature 0, thinking budget 0, output cap 1600, one call per arm per PUT. Both requested ten stdin inputs through the original `INPUT1: ... INPUT10:` output format. The call order was baseline→concept for the first 13 and concept→baseline for the last 13. One baseline call received HTTP 429 and succeeded on retry. The model saw only the public problem description, buggy PUT source and, in the concept arm, source-derived statement labels. It never saw reference code, expected outputs, fixed code or known triggering tests.

PUT and references were compiled with `g++ -std=gnu++17 -O2`; `-include cassert` was needed because two released sources used `assert` without including its header. Generated inputs ran with a three-second timeout. A differential exposure required all three references to exit successfully and agree after whitespace normalization, and the PUT to crash or return a different output. Reference agreement held for 257/260 generated inputs in each arm.

| Measure | Original prompt | + ConceptCoder VD statements |
| --- | ---: | ---: |
| PUTs with any raw differential | 7/26 | 8/26 |
| PUTs with a spec-valid differential | **7/26** | **7/26** |
| Spec-valid exposing inputs on the eight raw-exposure tasks | 25 | 26 |
| Reference-agreed inputs | 257/260 | 257/260 |

The eight problems that had at least one raw differential were `p02550`, `p02574`, `p02575`, `p02580`, `p02598`, `p02599`, `p02616`, and `p02641`. We encoded their published input shape and numeric constraints as validators in `trickcatcher_pilot/cpp_validity.py`. This validity check was written **after** finding the malformed `p02616` witness, applied identically to both saved arms, and cannot be treated as preregistered. No differential was seen on the other 18 problems, so their full input validity has not been established by these validators.

## Interpretation

ConceptCoder's VD labels mostly identified C++ array access and allocation on these algorithmic tasks. They do not express the logical relation that distinguishes a buggy solution from a correct one. The null result here is narrow: it tests **direct prompt injection of the released VD annotations**, with a one-line parser compatibility patch, on a 26-task TrickyBugs C++ pilot. It does not assess ConceptCoder's original fine-tuning gains or its branch-prediction concepts, and it does not overturn the separate Python EvalPlus pilot with Gemini-inferred behavior hypotheses. The first improvement to test next is a task-behavior relation grounded in a statement and the specification, with an equal-call generic planner control on fresh PUTs.

Code: [`cpp_concepts.py`](../trickcatcher_pilot/cpp_concepts.py), [`cpp_run.py`](../trickcatcher_pilot/cpp_run.py), [`cpp_evaluate.py`](../trickcatcher_pilot/cpp_evaluate.py), [`cpp_validity.py`](../trickcatcher_pilot/cpp_validity.py), [`cpp_stats.py`](../trickcatcher_pilot/cpp_stats.py). The exact 26-task concept cards, raw Gemini responses and scored JSONL for both arms are archived in [`research/results/trickcatcher-cpp-vd-26`](results/trickcatcher-cpp-vd-26). The baseline raw file retains the first failed HTTP 429 row and its successful retry; the evaluator uses the latest row per problem.

To recheck the paired result without further model calls:

```bash
.venv/bin/python -m trickcatcher_pilot.cpp_validity \
  --baseline research/results/trickcatcher-cpp-vd-26/baseline_eval.jsonl \
  --concept research/results/trickcatcher-cpp-vd-26/concept_eval.jsonl
```
