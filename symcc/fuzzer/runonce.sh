#!/bin/bash -e
##
# symcc_std/runonce.sh — chay 1 input (giong vanilla) de monitor Magma doc canary.
# Noi long TIMELIMIT/MEMLIMIT so voi ban goc 0.1s/50MB: binary co instrument SymCC cham hon nhieu,
# va MEMLIMIT chat se giet no truoc khi tra loi (chinh loi da gap voi ban vanilla goc).
##

export TIMELIMIT="${TIMELIMIT:-30s}"
export MEMLIMIT_MB="${MEMLIMIT_MB:-4000}"

run_limited()
{
    ulimit -Sv $[MEMLIMIT_MB << 10];
    ${@:1}
    test $? -lt 128
}
export -f run_limited

export LD_LIBRARY_PATH="$OUT:$FUZZER/z3/install/lib:$LD_LIBRARY_PATH"
# KHONG dat SYMCC_INPUT_FILE -> khong symbolic -> chay nhu binary thuong (nhanh), chi doc canary.

args="${ARGS/@@/"'$1'"}"
if [ -z "$args" ]; then
    args="'$1'"
fi

timeout -s KILL --preserve-status $TIMELIMIT bash -c \
    "run_limited '$OUT/$PROGRAM' $args"
