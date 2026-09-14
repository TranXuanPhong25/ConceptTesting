#!/bin/bash
# Dung lai TOAN BO pipeline SymCC tren may x86-64 (Linux hoac Mac Intel), chay NATIVE — khong QEMU.
# Tren may nay (Apple Silicon/arm64) moi image phai emulate amd64 qua QEMU => cham 3-5x va build de vap.
# Tren x86-64 thi amd64 la native => nhanh han va it rui ro han.
#
# YEU CAU: docker (dang chay), git, python3 (>=3.6). KHONG can venv/pip:
#   loop_symcc.py + magma/oracle.py + reach/taint.py chi dung thu vien chuan.
#
# Chay TU REPO ROOT:  bash symcc/x86_setup.sh
#   TARGETS="libpng" mac dinh. Vd nhieu target: TARGETS="libpng libxml2" bash symcc/x86_setup.sh
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export TARGETS="${TARGETS:-libpng}"

echo "== [1/3] vendor/magma (bi gitignore -> clone rieng, dung tag Magma da dung) =="
if [ ! -d vendor/magma/.git ]; then
    git clone --depth 1 --branch v1.2.1 https://github.com/HexHive/magma.git vendor/magma
else
    echo "   da co vendor/magma"
fi

echo "== [2/3] build cap image ORACLE (vuln/fixed) cho: $TARGETS =="
bash magma/setup.sh                      # magma-<t>-vuln + magma-<t>-fixed (canary vi-phan)

echo "== [3/3] build image SYMCC cho: $TARGETS =="
bash symcc/setup.sh                      # magma-<t>-symcc (co instrument SymCC de giai rang buoc)

# extract items neu chua co (loop_symcc doc magma/items/*.jsonl)
for t in $TARGETS; do
    [ -f "magma/items/$t.jsonl" ] || python3 magma/extract.py --target "$t" || true
done

cat <<'EOF'

======================================================================
XONG. Chay do (khong can API key — SymCC khong goi LLM):

  # SymCC THUAN (con so trung thuc — khong dan duong bang canary):
  ROUNDS=2 SEED_SRC=corpus GUIDE=none  SOLVE_TIMELIMIT=120s MAX_CAND=80 \
    python3 symcc/loop_symcc.py

  # co dan duong bang canary (tran tren — canary la tin hieu tu patch):
  ROUNDS=2 SEED_SRC=corpus GUIDE=canary SOLVE_TIMELIMIT=120s MAX_CAND=80 \
    python3 symcc/loop_symcc.py

Ket qua ghi symcc/results_symcc.json. Gui lai file do (hoac copy vao chat) de doi chieu voi bang LLM.
======================================================================
EOF
