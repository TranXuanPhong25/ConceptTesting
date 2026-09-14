#!/bin/bash
##
# symcc_std/solve.sh — BUOC CONCOLIC THAT: chay 1 seed, thu path constraint, Z3 lat tung nhanh -> input MOI.
#
# $1 = duong dan seed (input cu the)
# $2 = thu muc ghi cac input giai duoc (mac dinh /tmp/symcc_out)
#
# Co che SymCC:
#   SYMCC_INPUT_FILE=<seed>  -> coi byte DOC TU FILE DO la symbolic (mac dinh SymCC lay stdin)
#   SYMCC_OUTPUT_DIR=<dir>   -> moi lan gap nhanh phu thuoc input, phu dinh dieu kien, goi Z3;
#                               giai duoc thi GHI input moi vao dir nay
# Khac han `byte_sweep` (XOR-flip do byte, khong solver): day la path-constraint + SMT thuc su.
##

seed="$1"
outdir="${2:-/tmp/symcc_out}"
mkdir -p "$outdir"

export SYMCC_INPUT_FILE="$seed"
export SYMCC_OUTPUT_DIR="$outdir"
export LD_LIBRARY_PATH="$OUT:$FUZZER/z3/install/lib:$LD_LIBRARY_PATH"
# Bo gioi han bo nho: QSYM backend + Z3 ngon nhieu RAM; ulimit chat se giet solver truoc khi no giai xong.
SOLVE_TIMELIMIT="${SOLVE_TIMELIMIT:-300s}"

args="${ARGS/@@/"$seed"}"
[ -z "$args" ] && args="$seed"

timeout -s KILL --preserve-status "$SOLVE_TIMELIMIT" "$OUT/$PROGRAM" $args >/dev/null 2>&1
echo "SYMCC_RC=$?"
echo "SYMCC_N=$(find "$outdir" -type f | wc -l)"
