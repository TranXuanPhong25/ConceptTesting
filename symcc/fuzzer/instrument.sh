#!/bin/bash
set -e
##
# symcc_std/instrument.sh — bien target bang `symcc` (wrapper clang co pass SymCC).
#
# CC  = symcc : file C cua thu vien (libpng/libtiff/...) -> theo vet symbolic
# CXX = sym++ : PHAI dung sym++, khong duoc g++. Ly do (da mat 1 vong build de hoc):
#   - object do symcc/sym++ sinh goi cac ham `_sym_*`; chinh WRAPPER symcc/sym++ moi tu them
#     `-L<runtime_dir> -lSymRuntime -Wl,-rpath,...` luc link (xem compiler/symcc.in:45, sym++.in:63).
#     Link bang g++ => hang loat "undefined reference to `_sym_write_memory`" v.v.
#   - va SYMCC_REGULAR_LIBCXX=1 cho phep sym++ dung libstdc++ he thong, KHONG can libc++ co
#     instrument (ta co tinh bo cuoc build do). Khong dat bien nay thi sym++ `exit 255`.
#
# SYMCC_NO_SYMBOLIC_INPUT=1 luc BIEN DICH: mot so target chay binary vua bien ra trong qua trinh build
# (vd sinh bang tra cuu). Neu de symbolic thi cac lan chay do se co gang giai rang buoc -> cham/hong build.
#
# -fPIC den tu --build-arg BUILD_FLAGS trong symcc/setup.sh (symcc sinh object non-PIC, Ubuntu link PIE).
##

export LIBS="$LIBS -l:afl_driver.o -lstdc++"
export CC="$FUZZER/symcc/build/symcc"
export CXX="$FUZZER/symcc/build/sym++"
export SYMCC_REGULAR_LIBCXX=1
export SYMCC_NO_SYMBOLIC_INPUT=1
export LD_LIBRARY_PATH="$OUT:$FUZZER/z3/install/lib:$LD_LIBRARY_PATH"
export LDFLAGS="$LDFLAGS -L$OUT -Wl,-rpath,$OUT"

"$MAGMA/build.sh"
"$TARGET/build.sh"
