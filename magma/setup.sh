#!/bin/bash
# Build Magma libpng images: VULN (bug hien dien + canary + fatal) va FIXED (bug da va).
# Vuln  = CANARY_MODE=1 (fixes EXCLUDED) + ISAN=1 (-DMAGMA_FATAL_CANARIES: trigger -> abort).
# Fixed = CANARY_MODE=3 (fixes INCLUDED, canaries off).
# Oracle vi-phan: input kich hoat bug tren VULN (abort + canary bug) nhung SACH tren FIXED.
#
# One-time, can Docker. Chay TU REPO ROOT:  bash magma/setup.sh
# Binaries la Linux -> oracle.py chay chung TRONG container (docker run).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export MAGMA="$ROOT/vendor/magma"
export USER="${USER:-$(whoami)}"
# TARGETS: danh sach target (space-separated). Vd: TARGETS="libtiff libxml2 lua" bash magma/setup.sh
TARGETS="${TARGETS:-${TARGET:-libpng}}"

if [ ! -d "$MAGMA/.git" ]; then
    echo "[!] Thieu vendor/magma. Chay:"
    echo "    git clone --depth 1 --branch v1.2.1 https://github.com/HexHive/magma.git vendor/magma"
    exit 1
fi

# FUZZER=vanilla: build harness bang g++ (StandaloneFuzzTargetMain, chay 1 input/lan) — KHONG can clang.
# (libfuzzer preinstall keo clang-11 tu apt.llvm.org/bionic da bi go -> exit 100. vanilla dung gcc base.)
# Goi docker build TRUC TIEP (khong qua tools/captain/build.sh) de tranh USER_ID/GROUP_ID cua host:
# tren macOS `id -g` = 20 (staff) trung group co san trong Ubuntu -> groupadd exit 4. Dung 1000/1000.
# Crash-signal = ISAN (-DMAGMA_FATAL_CANARIES: canary trigger -> abort), khong can ASAN.
build_one() {   # $1=tag | $2=CANARY_MODE(1|3) | $3=isan(0|1)
    local tag="$1" mode="$2" isan="$3" margs=""
    case "$mode" in 1) margs="--build-arg canaries=1";; 3) margs="--build-arg fixes=1";; esac
    [ "$isan" = "1" ] && margs="$margs --build-arg isan=1"
    echo "=================== BUILD $tag ($TARGET) mode=$mode isan=$isan ==================="
    # --platform linux/amd64: Magma ky vong amd64. Tren Apple Silicon (arm64), libpng configure bat
    # ARM NEON -> compile arm/*.S; Magma ep -include canary.h (C) vao assembler -> loi. amd64 (QEMU)
    # khong build file .S do -> qua. docker run cung phai --platform linux/amd64 (xem oracle.py).
    docker build --platform linux/amd64 -t "$tag" \
        --build-arg fuzzer_name=vanilla \
        --build-arg target_name="$TARGET" \
        --build-arg USER_ID=1000 --build-arg GROUP_ID=1000 \
        $margs -f "$MAGMA/docker/Dockerfile" "$MAGMA" || return 1
    echo "-> built $tag"
}

# FIXUP libtiff: autogen.sh tai config.guess/config.sub tu savannah.gnu.org; server tra loi -> wget exit 8
# -> `exit $retval` giet build. Nhung `automake --add-missing` DA cai san config.guess roi => tai la THUA.
# Bo `exit $retval` (tai loi thi khong mv, giu file automake da cai). Idempotent.
_tiff_build="$MAGMA/targets/libtiff/build.sh"
if [ -f "$_tiff_build" ] && ! grep -q 'FIX-autogen' "$_tiff_build"; then
    perl -0pi -e 's{\./autogen\.sh}{# FIX-autogen: bo qua loi tai config.guess (savannah tra loi -> wget exit 8)\nsed -i "s/exit \\\$retval/true/g" autogen.sh\n./autogen.sh}' "$_tiff_build"
    echo "[fixup] libtiff/build.sh: vo hieu 'exit \$retval' trong autogen.sh"
fi

set +e                                    # 1 target hong KHONG lam abort ca batch
OKS=""; FAILS=""
for TARGET in $TARGETS; do
    if build_one "magma-$TARGET-vuln" 1 1 && build_one "magma-$TARGET-fixed" 3 0; then
        OKS="$OKS $TARGET"; echo "== DONE $TARGET =="
    else
        FAILS="$FAILS $TARGET"; echo "== [FAIL] $TARGET =="
    fi
done

echo
echo "XONG. OK:$OKS  | FAIL:$FAILS"
echo "-> Trich:  for t in$OKS; do .venv/bin/python magma/extract.py --target \$t; done"
