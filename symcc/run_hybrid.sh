#!/bin/bash
# HYBRID SymCC->LLM: xuat hint tu SymCC (input cham + byte dieu khien) roi cho LLM gen dua tren hint.
# So voi blind + concept_static tren CUNG cac bug. Tu dong lam viec tren MOI bug co image symcc:
#   - bay gio (chi libpng)              -> hybrid tren 5 bug libpng co seed
#   - sau khi build du target (huong A) -> chay LAI script nay -> hybrid tren toan bo 100 bug co image
# Do la co che "dung A mo rong C": run_hybrid = export_hints (skip bug da co) + gom + gen.
#
# YEU CAU:
#   - GROQ_API_KEY  (gen LLM)
#   - image magma-<t>-symcc + magma-<t>-{vuln,fixed}
#   - python cho loop.py CAN langchain: pip install langchain-groq langchain-core
#     (export_hints/loop_symcc thi KHONG can, chi stdlib; nhung loop.py GEN thi can)
#
# Chay TU REPO ROOT:  GROQ_API_KEY=gsk_... bash symcc/run_hybrid.sh
# Env: PY (python), ROUNDS=3, HINT_PICK=reached|first, SOLVE_TIMELIMIT=120s, MAX_CAND=80
set -e
cd "$(dirname "$0")/.."
PY="${PY:-python3}"

if [ -z "$GROQ_API_KEY" ]; then
    echo "[!] Thieu GROQ_API_KEY -> khong gen duoc (buoc 3). Van xuat hint (buoc 1-2) duoc."
fi

echo "== [1/3] xuat hint SymCC (bo qua bug da co hint) =="
HINT_PICK="${HINT_PICK:-reached}" SOLVE_TIMELIMIT="${SOLVE_TIMELIMIT:-120s}" MAX_CAND="${MAX_CAND:-80}" \
  DOCKER_TIMEOUT="${DOCKER_TIMEOUT:-400}" "$PY" symcc/export_hints.py

echo "== [2/3] gom bug CO hint -> /tmp/hybrid_gold.jsonl =="
"$PY" - <<'PYEOF'
import json, glob, os
hints = {os.path.basename(p)[:-5] for p in glob.glob('symcc/hints/*.json')}
n = 0
with open('/tmp/hybrid_gold.jsonl', 'w') as out:
    for f in glob.glob('magma/items/*.jsonl'):
        for l in open(f):
            if l.strip() and json.loads(l).get('bug_id') in hints:
                out.write(l); n += 1
print('  bug co hint:', n, '->', sorted(hints))
PYEOF

if [ -z "$GROQ_API_KEY" ]; then
    echo "== [3/3] BO QUA gen (thieu GROQ_API_KEY). Chay lai voi key de sinh test. =="
    exit 0
fi
echo "== [3/3] gen hybrid vs baseline (blind, concept_static) tren cung bug =="
GOLD=/tmp/hybrid_gold.jsonl ROUNDS="${ROUNDS:-3}" \
  CONDS=magma_blind,magma_concept_static,magma_hybrid_symcc \
  "$PY" magma/loop.py
