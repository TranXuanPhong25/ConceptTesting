#!/usr/bin/env bash
# Sequential execution of everything (one exec container at a time, so the 15 s timeouts see the same CPU load).
cd "$(dirname "$0")/.."
while pgrep -f "evaluate.py ebt" >/dev/null; do sleep 20; done
P="gen/pbt/k* gen/pbt_concept/k* gen/pbt_placebo/k*"
for R in 1 0; do
  MODE=exec REPAIR=$R WORKERS=8 bash run/dock.sh bash -c "python evaluate.py pbt /out/eval_gemini_pbt_r$R.jsonl $P"
  MODE=exec REPAIR=$R WORKERS=8 bash run/dock.sh bash -c "python evaluate.py ebt /out/eval_gemini_ebt_r$R.jsonl gen/ebt/k*"
  MODE=exec REPAIR=$R WORKERS=8 bash run/dock.sh bash -c "python evaluate.py pbt /out/eval_authors_pbt_r$R.jsonl /vendor/output/pbt/anthropic/claude_sonnet_4 && python evaluate.py ebt /out/eval_authors_ebt_r$R.jsonl /vendor/output/ebt/anthropic/claude_sonnet_4"
done
MODE=exec WORKERS=6 bash run/dock.sh bash vendored_run.sh
echo ALL DONE
