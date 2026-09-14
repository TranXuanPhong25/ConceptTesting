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

# driver standalone (giong vanilla): doc file -> LLVMFuzzerTestOneInput. Bien bang g++ THUONG —
# driver khong phai phan ta muon theo vet symbolic, va tranh phai dung sym++ (can libc++ instrument).
g++ $CXXFLAGS -std=c++11 -c "$FUZZER/src/afl_driver.cpp" -fPIC -o "$OUT/afl_driver.o"

echo "[symcc_std] xong: symcc=$FUZZER/symcc/build/symcc  z3=$FUZZER/z3/install"
