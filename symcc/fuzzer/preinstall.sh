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

# python3-distutils: BAT BUOC. Build Z3 chay scripts/update_api.py (sinh api_commands.cpp), script do
# `import distutils.sysconfig`. Ubuntu tach distutils khoi python3-minimal => thieu goi nay thi Z3 chet
# o buoc 753/795 voi "ModuleNotFoundError: No module named 'distutils.sysconfig'" (da dinh 2026-09-14).
apt-get update && \
    apt-get install -y make build-essential git wget cmake ninja-build \
        clang-10 llvm-10-dev libz3-dev zlib1g-dev \
        python3 python3-distutils python3-setuptools

# symcc goi `clang`/`clang++`/`llvm-config` khong hau to
update-alternatives \
  --install /usr/bin/clang       clang       /usr/bin/clang-10 20 \
  --slave   /usr/bin/clang++     clang++     /usr/bin/clang++-10 \
  --slave   /usr/bin/clang-cpp   clang-cpp   /usr/bin/clang-cpp-10
update-alternatives \
  --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-10 20
