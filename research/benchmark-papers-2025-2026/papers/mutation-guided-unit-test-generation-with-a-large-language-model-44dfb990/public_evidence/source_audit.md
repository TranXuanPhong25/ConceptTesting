# MUTGEN public-source audit

Checked 2026-10-15. Paper: [arXiv:2506.02954 v8](https://arxiv.org/abs/2506.02954), final IEEE TSE DOI 10.1109/TSE.2026.3682975.

- Author-linked repo: [Amocy-Wang/MUTGEN](https://github.com/Amocy-Wang/MUTGEN), checked at commit `69dd37ddfab16b8c5efd22117dc3d213ab05418d` (2026-04-08).
- GitHub API tree has 441 entries, including `dataset.tar.gz` (74,369,230 bytes), HumanEval-Java/Leetcode-Java subjects, MutGen implementation, prompts, EvoSuite/PITest scripts, evaluator, and cached baseline/generated results. No LICENSE file or GitHub-detected license.
- Statically inspected README, requirements, `run.py`, `model.py`, `args_config.py`, `mutahunter/core/router.py`, generation loop and `HumanEval-Java_fromscratch/runeach.sh`. The text LLM router uses LiteLLM and accepts a model name plus `api_base`; the example invokes local `ollama/llama3.3` at localhost:11434. No code executed.
- README advertises local Llama-3.3 70B, the supplied dataset, training, and evaluation commands. It links a Google Drive folder for checkpoints; the link's contents/access were not verified. Main CodeT5 architecture does not accept the user's decoder-only Qwen as a drop-in, but MutGen's LLM generation interface is generic and can plausibly point to a local OpenAI-compatible endpoint.
- Paper's main benchmark is method-level HumanEval-Java (104 retained subjects) + Leetcode-Java (100 subjects), with PITest mutants. Separate Defects4J evaluation adds assertions to EvoSuite prefixes for 835 bugs/17 projects and reports F2P bug detection, 41 vs EditAS 21. This is not Defects4J issue-report generation.
- README extraction command is printed as `tar -xzcf dataset.tar.gz`, which appears to mix conflicting create/extract flags; check before setup. No model/API calls or reproduction.
