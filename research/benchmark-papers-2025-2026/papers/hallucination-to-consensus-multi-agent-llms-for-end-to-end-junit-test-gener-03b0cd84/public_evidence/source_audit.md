# Author-source audit — #82 CANDOR

Checked 2026-10-15. Full paper read. Source files were statically inspected; none were executed or modified.

## Source identity and public content

- Paper arXiv v7: [2506.02943](https://arxiv.org/abs/2506.02943v7); final TOSEM 2026 DOI `10.1145/3803418`.
- Paper Section 4.4 directly links [github.com/qiqiguana/candor](https://github.com/qiqiguana/candor/tree/157165cc7ac76d72e59ed60d13084d74822c9e2e) and says code/data are public. README identifies exact CANDOR paper title.
- Public repository HEAD `157165cc7ac76d72e59ed60d13084d74822c9e2e`, commit dated 2026-03-18; 1,356 tree entries, ~20.9 MB.
- Root has no GitHub license metadata and no LICENSE file. Check component and upstream data terms before reuse.
- Full source files and data are present: root Python modules `initialize.py`, `generate.py`, `fix_oracle.py`, `main.py`, `utils.py`, prompts/templates, `create_mutants.py`; HumanEvalJava (160), Leetcode (150), plus three Pitest-mutant variants for each; Maven configs, JaCoCo/Pitest/CFR tools, generated test data and mappings.

## Model/setup route

Static source inspection confirms the implementation uses `langchain_ollama.ChatOllama` and hard-coded model tags `llama3.1:70b` and `deepseek-r1:70b` in initialization, test generation and oracle fixing. Paper reports basic Llama 3.1 70B + reasoning DeepSeek-R1 Llama-distilled 70B, three Panelist/Interpreter pipelines and 48GB+ GPU setup (article says dual RTX 6000 Ada; README says a single 48GB RTX 6000 Ada). README/module docs describe an Ollama route and sample environment/API config, but current code tree is root-level modules while README examples refer to `agents/` and `python -m tgen.main`, so follow exact scripts/config in the pinned code rather than assuming README commands work. A remote Qwen/vLLM endpoint is not a drop-in ChatOllama server; a Qwen variant requires changing model/client configuration. No model was called.

## Dataset and task fit

Repository includes HumanEvalJava and Leetcode clean sources plus three generated Pitest mutant variants. The paper explicitly excludes Defects4J and SF110 due to external dependencies. Its “faulty code” oracle experiments use synthetic mutants of these small method-level programs, not historical Defects4J bugs. Results assess code/branch coverage, mutation scores and oracle correctness against natural-language requirements. This is a useful concept/oracle experiment, but not a directly reproducible SWT-Bench/Defects4J/BugsInPy cohort or root-cause analysis.
