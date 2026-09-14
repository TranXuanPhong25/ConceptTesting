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

# HAI goi python DEU BAT BUOC (moi cai da lam chet 1 lan build, 2026-09-14):
#  - python3-distutils: Z3 chay scripts/update_api.py (sinh api_commands.cpp) -> `import distutils.sysconfig`.
#    Ubuntu tach distutils khoi python3-minimal => thieu thi Z3 chet o object 753/795.
#  - python-minimal (cho /usr/bin/python2): QSYM backend cua SymCC sinh code bang
#    `COMMAND python2 gen_expr.py` (runtime/qsym_backend/CMakeLists.txt). Ban goc symcc_afl co python2
#    "nho" cai `python-pip`; toi bo pip (vi `pip install lit` chet voi PyPI da bo python2) nen mat luon
#    python2 => SymRuntime chet. Hai script do chi `import os, sys` nen KHONG can module python2 nao khac.
apt-get update && \
    apt-get install -y make build-essential git wget cmake ninja-build \
        clang-10 llvm-10-dev libz3-dev zlib1g-dev \
        python3 python3-distutils python3-setuptools python-minimal

# symcc goi `clang`/`clang++`/`llvm-config` khong hau to
update-alternatives \
  --install /usr/bin/clang       clang       /usr/bin/clang-10 20 \
  --slave   /usr/bin/clang++     clang++     /usr/bin/clang++-10 \
  --slave   /usr/bin/clang-cpp   clang-cpp   /usr/bin/clang-cpp-10
update-alternatives \
  --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-10 20
