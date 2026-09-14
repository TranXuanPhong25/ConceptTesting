#!/bin/bash
set -e
##
# symcc_std/build.sh — build Z3 (chi thu vien) + SymCC (backend QSYM) + driver standalone.
#
# So voi symcc_afl/build.sh, BO 3 cuoc build:
#   1) AFL + llvm_mode            -> khong chay chien dich fuzzing
#   2) libc++ tu llvm-project     -> target C, khong can libc++ co instrument (DAT NHAT)
#   3) cargo symcc_fuzzing_helper -> chi dung de ghep vong lap AFL<->SymCC
# Con lai dung 2 thu BAT BUOC de giai rang buoc: Z3 + SymCC.
#
# Z3: repo Ubuntu 18.04 chi co 4.4.1, qua cu cho API C++ ma SymCC can (4.8.x) => phai build tu nguon.
# Tat Z3_BUILD_EXECUTABLE/TEST de khoi bien dich binary `z3` + test (khong dung, ton hang chuc phut QEMU).
##

NPROC="$(nproc)"

# ---------- Z3 (thu vien dong + cmake package config cho SymCC) ----------
(
    cd "$FUZZER/z3"
    mkdir -p build install cmake_conf
    cd build
    CXX=clang++ CC=clang cmake ../ -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DZ3_BUILD_EXECUTABLE=OFF \
        -DZ3_BUILD_TEST_EXECUTABLES=OFF \
        -DZ3_BUILD_LIBZ3_SHARED=ON \
        -DCMAKE_INSTALL_PREFIX="$FUZZER/z3/install" \
        -DCMAKE_INSTALL_Z3_CMAKE_PACKAGE_DIR="$FUZZER/z3/cmake_conf"
    ninja -j "$NPROC"
    ninja install
)

# ---------- SymCC (pass LLVM + runtime) ----------
(
    cd "$FUZZER/symcc"
    export CXXFLAGS="$CXXFLAGS -DNDEBUG"
    mkdir -p build && cd build
    cmake -G Ninja ../ \
        -DCMAKE_BUILD_TYPE=Release \
        -DQSYM_BACKEND=ON \
        -DZ3_DIR="$FUZZER/z3/cmake_conf"
    ninja -j "$NPROC"
)

# runtime .so phai tim thay duoc luc CHAY binary co instrument
mkdir -p "$OUT"
find "$FUZZER/symcc/build" "$FUZZER/z3/install" -name 'libSymRuntime.so*' -o -name 'libz3.so*' \
    | xargs -I{} cp -a {} "$OUT/" 2>/dev/null || true

# Driver standalone: doc file -> LLVMFuzzerTestOneInput.
#
# PHAI bien bang `sym++`, KHONG duoc dung g++ (toi da lam sai va mat 1 vong build):
# SymCC khong interpose libc bang ten symbol. `runtime/LibcWrappers.cpp` dinh nghia `SYM(fread)` voi
# `#define SYM(x) x##_symbolized`, va PASS cua SymCC viet lai loi goi `fread` -> `fread_symbolized`
# CHI TRONG CODE DO NO BIEN DICH. Driver moi la cho DOC FILE. Bien driver bang g++ => `fread` giu
# nguyen => du lieu KHONG BAO GIO thanh symbolic => chay xong tra ve 0 input (da do: dung 0).
# Bien bang sym++ => 467 input giai duoc tu 1 seed.
#
# SYMCC_REGULAR_LIBCXX=1: bao sym++ dung libstdc++ he thong. Neu khong dat, sym++ doi
# SYMCC_LIBCXX_PATH (libc++ co instrument) va `exit 255`. Ta co tinh KHONG build libc++ do.
# -fPIC tuong minh: o buoc nay CXXFLAGS con RONG (Dockerfile set ENV CFLAGS/CXXFLAGS SAU layer nay).
export SYMCC_REGULAR_LIBCXX=1
"$FUZZER/symcc/build/sym++" $CXXFLAGS -std=c++11 -c "$FUZZER/src/afl_driver.cpp" -fPIC \
    -o "$OUT/afl_driver.o"

echo "[symcc_std] xong: symcc=$FUZZER/symcc/build/symcc  z3=$FUZZER/z3/install"
