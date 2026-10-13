---
name: test-aware-mutants-candidate
description: "Candidate base paper (ESEM'26 test-aware LLM mutants, arXiv 2609.35841) — artifact and Zenodo facts checked 2026-10-09, plus the proposed test-gen extension"
metadata:
  node_type: memory
  type: project
  originSessionId: c7ea6648-d230-4c4d-8eab-acba360b8de8
  modified: 2026-10-08T17:28:13.870Z
---

**Paper.** Kiele et al., "Beyond Rule-Based Mutation Testing: Test-Aware Mutant Generation Using LLMs", ESEM 2026, arXiv 2609.35841. The LLM sees the spec, the canonical solution and the base tests, and writes a mutant that passes the base tests. EvalPlus plus tests serve as the oracle. Gemini 3.1 Pro AGENT1-TA reaches 144/164 SUCCESS on HumanEval and 299/378 on MBPP; Gemini 3 Flash reaches 117/274. In Fig. 1, "create test case to fill the gap" is drawn as out of scope.

**Artifact.**
- github.com/codingWhale13/test-aware-mutants, commit fa0313e, about 1.5k lines of Python 3.12.
- Gemini is called through Vertex (`google-genai`, `vertexai=True`, `GCP_PROJECT_ID` / `GCP_REGION`).
- The code has no LICENSE file. The pyproject pins `evalplus[vllm]`; the vllm extra is not needed.

**Data.** Zenodo record 20195774 (CC-BY-4.0, 25 MB zip) has success/rejected/undetected/invalid jsonl for 6 sources x 4 prompts, iterative runs included. Its counts match Table 4. The mutant code is in the field `mutated_code`.
- Pool of distinct verified faults: 891 on HumanEval (162/164 problems) and 2,016 on MBPP (368/378). Median 5 per problem.
- Median oracle kill rate is 0.07 on HumanEval and 0.18 on MBPP.
- Rejected mutants usable as placebos: 3,090 on HumanEval and 4,645 on MBPP.

**Proposed extension** (waiting for the user's go-ahead as of 2026-10-09):
- The concept is a test gap: either a natural-language blind spot or a mutant that passes the base tests, selected without using the plus oracle.
- Arms: plain / gap-nl / gap-mutant / placebo (a rejected mutant from the same problem).
- Score test generation on held-out verified faults from the other sources.

**The paper has no test-generation step**, so no arm can be "the paper's method" as-is. The user asked for a paper-original arm, so the design was revised:
- `paper` = the artifact's verbatim AGENT1-TA mutant plus a minimal "write a test that kills this mutant". This is our literal completion of Fig. 1 and must be labelled that way, not called original.
- `concept` = the same mutant abstracted into a gap concept, i.e. the input class that the base tests miss, with tests asked to cover the whole class.
- Remaining arms: `plain` and `placebo`.
- The paper's own method is reproduced separately on its own success-rate metric.

**Design refined on 2026-10-09 to cost $0 for concepts.** Mutant generation stays exactly as in the paper, with no concept added. All guidance comes from the Zenodo outputs of the paper's Gemini 3 Flash AGENT2-TA prompt, so no new mutant or concept calls are needed:
- `paper` = the AGENT2-TA mutant (SUCCESS or UNDETECTED, i.e. it passes the base tests) plus "kill this mutant".
- `concept` = the same mutant plus that output's BLIND SPOTS field.
- `placebo` = the same mutant plus that output's BASE TEST COVERAGE field, which describes already-tested behavior in the same format.
- `plain` = no gap information.
- Held-out pool: all sources except Gemini 3 Flash.
- Example for the user: HumanEval/18. Its blind spots are "substring == whole string", "multi-char match at the end", and "empty substring". The mutant is `len(string[i:]) != len(substring)+1`.

Budget estimate:
- Test generation runs on Gemini 2.5 Flash with thinking 0.
- A pilot of 100 problems x 4 arms costs about $1.
- The full run (about 400 problems x 4 arms x K=2) costs about $9.
- A live reproduction slice of 30 HumanEval problems on Gemini 3 Flash costs about $0.6.

**Novelty risk:** AdverTest (arXiv 2602.08146) already runs an adversarial mutant-agent vs test-agent loop on Defects4J. Related: [[thesis-concept-requirement]].
