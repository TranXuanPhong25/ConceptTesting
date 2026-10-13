---
name: thesis-concept-requirement
description: "The user's thesis must include a \"concept\" that guides LLM test generation to hit targets; dropping concepts entirely is not an option"
metadata:
  node_type: memory
  type: user
  originSessionId: c7ea6648-d230-4c4d-8eab-acba360b8de8
  modified: 2026-10-10T04:17:16.839Z
---

The user's thesis topic requires "something called a concept" that guides LLM test generation toward hitting a target, such as bugs, mutants or gaps. They said this on 2026-10-09 when I proposed abandoning concepts after the null CoverUp results ([[coverup-concept-verdict]]).

**Why:** the topic is fixed (probably by the advisor), so a recommendation to drop concepts is not usable. The concept does not have to be ConceptCoder's C1-C8 labels, though.

On 2026-10-09 the user clarified that a concept must be a human-defined **fact** that the LLM does not know and has to reason from. They rejected LLM self-inferred content, such as the paper's AGENT2 BLIND SPOTS field.

Also on 2026-10-09 they called the static `concept_annotator`/`concept_annotator_py` C1-C8 tags "vớ vẩn": a large model can read those off the code itself, so they carry no value. Don't propose static code-derived tags as the concept arm again.

What I proposed in response:
- Concepts come from textbook test-adequacy criteria: input partitions (empty / one / many), boundary values, loops running 0 / 1 / many times, condition true/false, and the position where a condition holds inside a loop.
- The facts are which criteria the existing tests leave unmet. A tool computes them by running the base tests instrumented, at $0 cost.
- Each criterion comes with a human-written recipe for building an input that meets it.

Worked example, verified by running the code: on HumanEval/18 the base tests never run the loop exactly once (substring == string), never match at the second-to-last iteration (the paper's mutant exploits exactly this; `('abx','ab')` kills it), and never use an empty substring (the gap the authors found by hand in Sec. 4.2).

On 2026-10-10 the user confirmed that "human-defined vocabulary + tool-computed instance" counts as a concept, **as long as the fact is abstract enough for a human to understand**. Example that qualifies: "at line k, `len(str(x))<=2` never evaluated False with x negative".
- A raw failing input does not qualify; it is too concrete.
- A mutant diff such as "`/`→`//` survives" has to be phrased as a behaviour.
- Facts about values that can never occur (≈80% of the raw cells) should be filtered out.

On 2026-10-10, after the ULT probe ([[ult-concept-status]]), the user restated the point: a static prompt concept only mirrors the code. ConceptCoder's concepts act as a signal only because they are trained through a separate head.

I offered two routes:
- Training, with a concept head. It needs a GPU, and the x86_64 machine has none (checked 2026-10-10). Per ConceptCoder Table 6, it also needs a control head with irrelevant concepts.
- Inference, with execution-verified gap facts.

**How to apply:** frame every proposal as concept-guided test generation. Pick concepts that carry information the generator does not already have, such as an execution-verified test gap or blind spot, rather than facts derived only from the code. Keep the oracle independent of the code under test, and always include a matched placebo arm. Candidate base paper: [[test-aware-mutants-candidate]].
