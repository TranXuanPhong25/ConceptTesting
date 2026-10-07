"""m9.py, unchanged, on the new methods: its module globals point to the new-method source file and to subset150 outputs.

Same code path as the 78 (prompt build, call, retries, the notebook's parsing, record format): only
  SRC      -> data/prompts/buggy_source_data_unified_invoked_s150new.jsonl
  OUT      -> subset150/out/m9 (docs_<arm>.jsonl cache, llm_calls.jsonl from m9's own call logger)
  DOC_OUT  -> data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_s150_m9_<arm>.jsonl
  budget   -> subset150's ledger and $25 cap (m9.gen checks it before every method)
usage (container):  python3 subset150/m9new.py gen <adv_rerun|concept|placebo>
                    python3 subset150/m9new.py prompts      m9's leak check on the new methods -> out/m9/prompts_check.txt
"""
import os, sys

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [f"{REPO}/m9_concept_advanced", f"{REPO}/subset150"]
import m9, calllog

m9.SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked_s150new.jsonl"
m9.OUT = f"{REPO}/subset150/out/m9"
m9.DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_s150_m9_{}.jsonl"
m9.CAP = m9.DOC_BUDGET = calllog.CAP
m9.cost = calllog.total  # m9.gen: `cost(quiet=True) < CAP` before each method; prints the ledger at the end

if __name__ == "__main__":
    os.makedirs(m9.OUT, exist_ok=True)
    if sys.argv[1] == "gen":
        m9.gen(sys.argv[2], [])
    else:
        m9.prompts()
