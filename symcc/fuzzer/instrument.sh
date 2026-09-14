#!/bin/bash
set -e
##
# symcc_std/instrument.sh — bien target bang `symcc` (wrapper clang co pass SymCC).
#
# CC = symcc  : file C cua thu vien (libpng/libtiff/...) -> co theo vet symbolic
# CXX = g++   : chi dung cho driver/khau link C++; KHONG dung sym++ vi sym++ doi libc++ co instrument
#               (ta co tinh bo cuoc build do). Target cua Magma ma ta dung deu la C.
#
# SYMCC_NO_SYMBOLIC_INPUT=1 luc BIEN DICH: mot so target chay binary vua bien ra trong qua trinh build
# (vd sinh bang tra cuu). Neu de symbolic thi cac lan chay do se co gang giai rang buoc -> cham/hong build.
##

export LIBS="$LIBS -l:afl_driver.o -lstdc++"
export CC="$FUZZER/symcc/build/symcc"
export CXX="/usr/bin/g++"
export SYMCC_NO_SYMBOLIC_INPUT=1
export LD_LIBRARY_PATH="$OUT:$FUZZER/z3/install/lib:$LD_LIBRARY_PATH"
export LDFLAGS="$LDFLAGS -L$OUT -Wl,-rpath,$OUT"

"$MAGMA/build.sh"
"$TARGET/build.sh"
