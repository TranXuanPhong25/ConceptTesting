#!/bin/bash
# Compute line facts for every PUT in tasks.txt (no network, one process per task).
#   OUT=trickcatcher_linefacts/out/facts_v3c NON_DESIGN=1 bash trickcatcher_linefacts/run_facts.sh [jobs]
cd "$(dirname "$0")/.."
D=PBT_EdgeCases/run/data
P=vendor/TrickCatcher/Datasets/EvalPlus/PUTs
O=${OUT:-trickcatcher_linefacts/out/facts}
V=${VALIDITY:-evalplus}
mkdir -p $O
xargs -P ${1:-8} -I{} sh -c "[ -s $O/{}.json ] || timeout -k 5 3600 unshare -rn python3 -I -B trickcatcher_linefacts/facts.py {} $P/HumanEval_{}/put0.py $D/humaneval.jsonl $O/{}.json --validity $V > $O/{}.log 2>&1 || echo 'task {} rc='\$?" < <(tr ' ' '\n' < trickcatcher_linefacts/tasks.txt | awk -v non_design="${NON_DESIGN:-0}" 'NF && (!non_design || ($0 != 22 && $0 != 33 && $0 != 111 && $0 != 122 && $0 != 123 && $0 != 139))')
