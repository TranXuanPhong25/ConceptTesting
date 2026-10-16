# Replication notes (added by us; upstream files untouched)

Upstream: https://github.com/drixs2050/EvalAndMitigate @ 751f9f4 (cloned 2026-10-15). `git status` must stay clean
except this file. Byte-identical to ../eval-and-mitigate/ (no diff).

## Static findings (before any run)
1. No generated tests, completions, or result JSONs are released (`data/rq1/logs/` is empty). Paper numbers can only be
   checked by regenerating with paid OpenAI calls (gpt-4.1 docstrings, o4-mini reasoning_effort=high tests).
   OpenAI model output is not deterministic (o4-mini takes no temperature) -> reproduction is statistical, not exact.
2. `conda env create -f environment.yml` FAILS: pip cannot find `torch==2.7.1+cu126` on PyPI (no extra index URL).
   The conda part installs fine (micromamba 2.9.0). torch is only needed for seq_score_calc.py.
3. `generate_source_data_for_prompt.ipynb` "Run all" fails: cell 5 reads `data/prompts/source_data.jsonl` and cell 91
   reads `data/prompts/buggy_source_data_testable.jsonl`; neither is shipped. Only the batch loop (cells 0-4, 8, 75, 77+)
   can run.
4. `UT_Test_Generation.ipynb` writes to the author's home `/home/drixs2050/Documents/LLM4UT/...` (not a placeholder).
5. Defaults disagree across notebooks (tgt_model GPT-4-1 / GPT-O3-MINI / GPT-O4-MINI; different file_post_fix);
   the user must set them by hand (README says so).
6. Advanced docstring: earlier replication (../EvalAndMitigate/RESULTS.md) found the release lacks the advanced-prompt
   code in new_prompt_formatter.py -> to be confirmed here without editing.
7. Placeholders `/path/to/repo`, `/path/to/defects4j` -> plan: symlinks, no file edits.

## Environment blockers in this cloud container (2026-10-15)
- Network policy denies defects4j.org (Defects4J init.sh downloads project repos there) and cpanmetadb/metacpan
  (Perl deps). Defects4J cannot be initialised here until these hosts are allowed.
- No OPENAI_API_KEY.
