#!/bin/bash
set -e
##
# symcc_std/fetch.sh — chi clone SymCC + Z3. Commit GHIM y nguyen ban Magma dung (tai lap duoc).
#
# BO so voi symcc_afl/fetch.sh:
#   - google/AFL       : khong ghep AFL (ta khong chay chien dich fuzzing, chi giai rang buoc)
#   - llvm/llvm-project: chi de build libc++ co instrument cho target C++; target cua ta la C
#                        => tiet kiem khoang cuoc build dat nhat (nhieu gio duoi QEMU).
##

git clone --no-checkout https://github.com/eurecom-s3/symcc.git "$FUZZER/symcc"
git -C "$FUZZER/symcc" checkout 82151a62e3b702a2c699ca4d8ef91d3bf9beeb2b
git -C "$FUZZER/symcc" submodule init
git -C "$FUZZER/symcc" submodule update

git clone --no-checkout https://github.com/Z3Prover/z3.git "$FUZZER/z3"
git -C "$FUZZER/z3" checkout 897cbf347bcf73ac986d50636b15f09968130880
