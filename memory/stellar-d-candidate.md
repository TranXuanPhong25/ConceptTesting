---
name: stellar-d-candidate
description: "STELLAR-D (arXiv 2609.23209, search-based testing of LLM apps) judged the better concept-direction base than scenario NEATEST (2609.28130); artifact facts checked 2026-10-09, proposed failure-mode-concept extension"
metadata:
  node_type: memory
  type: project
  originSessionId: f9d645b0-100e-4d08-8685-75c5b1764435
  modified: 2026-10-08T17:27:17.628Z
---

On 2026-10-09 the user asked whether two papers could be developed in the ConceptCoder/concept direction.

**STELLAR-D** (Sorokin, Vasilev, Friedl, Stocco; EMSE manuscript, arXiv 2609.23209). A test is a style/content/perturbation feature vector; a generator LLM turns it into an utterance; NSGA-II searches. D/DS add an archive of failures scored by all-MiniLM embedding distance, plus uniform (D) or greedy-farthest (DS) repopulation.
- RQ2 diversity (embedding clusters, coverage %/entropy): STELLAR 72/85, S-D 77/88, S-DS 78/89, random 78/89. Non-diversified STELLAR finds the most failures.
- The 6 CarQA failure types (partial ignore, on/off bias, unnecessary clarification, unrequested execution, incorrect confirmation, guard-railing) come from one qualitative config only (CarQA-II, GPT-5).
- Artifact: github.com/ast-fortiss-tum/STELLAR, MIT, Python 3.11, OpenSBT/pymoo, algorithms rs/nsga2/nsga2d/nsga2ds/gs/astral. LLMs via Azure OpenAI (.env) or Ollama; no Gemini client, so wrap one outside vendor code. Open SUTs: SafeQA (any LLM), CarQA (`run_tests_carcontrol.py`), NaviQA-I via github.com/Leviathan321/ConvNavi (MIT). NaviQA-II and CarQA-II are BMW-internal.
- Proposed extension (awaiting approval): failure-mode concepts per failing test, rule-based from CarQA target vs final state plus reply text, used as the archive distance (STELLAR-C) vs embedding (STELLAR-DS) vs a shuffled-label placebo. Score distinct failure modes with an independent labeler. Cheap phase 0: concept fidelity (does the utterance realize the intended features?).

**Scenario-driven NEATEST** (arXiv 2609.28130, Scratch games): no LLM. The model-guided fitness is not in public Whisker (se2p/whisker master has only ReliableCoverage/Score/Survive/Novelty network fitness, checked 2026-10-09). Eval is 13 games x 30 reps x 5 h. Judged a poor fit.

**Why:** the thesis needs concept-guided LLM test generation with a placebo arm ([[thesis-concept-requirement]]).

**How to apply:** don't re-verify these artifact facts unless the repos changed. The open question for the user/advisor is whether testing LLM apps counts as "LLM test-case generation". Related: [[test-aware-mutants-candidate]].
