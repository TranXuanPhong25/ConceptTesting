#!/bin/bash
set -e
##
# symcc_std/preinstall.sh — goi apt can cho SymCC.
#
# KHAC ban goc `symcc_afl/preinstall.sh` cua Magma:
#   - Goc dung clang-9 + `pip install lit` (python2 pip): PyPI da bo python2 => `pip install` CHET, va
#     `set -e` giet build. lit chi can cho test-suite LLVM — ta khong build LLVM nen bo luon.
#   - Goc cai `rustc cargo` de build symcc_fuzzing_helper (chi dung khi ghep voi AFL). Ta khong dung AFL.
#   - clang-10/llvm-10-dev CO SAN trong repo Ubuntu 18.04 chinh thuc (da kiem tra), nen KHONG can
#     apt.llvm.org — chinh cho da lam build `libfuzzer` that bai (bionic-11 bi go => exit 100).
##

apt-get update && \
    apt-get install -y make build-essential git wget cmake ninja-build \
        clang-10 llvm-10-dev libz3-dev zlib1g-dev python3

# symcc goi `clang`/`clang++`/`llvm-config` khong hau to
update-alternatives \
  --install /usr/bin/clang       clang       /usr/bin/clang-10 20 \
  --slave   /usr/bin/clang++     clang++     /usr/bin/clang++-10 \
  --slave   /usr/bin/clang-cpp   clang-cpp   /usr/bin/clang-cpp-10
update-alternatives \
  --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-10 20
