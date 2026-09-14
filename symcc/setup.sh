#!/bin/bash
# Build image `magma-<target>-symcc`: code VULN (bug hien dien) + canary, bien bang SymCC.
# Dung de GIAI RANG BUOC (path constraint + Z3), khong phai de cham diem —
# cham diem van dung cap image magma-<target>-{vuln,fixed} san co (magma/oracle.py).
#
# Chay TU REPO ROOT:  bash symcc/setup.sh              (mac dinh libpng)
#                     TARGETS="libpng libxml2" bash symcc/setup.sh
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAGMA="$ROOT/vendor/magma"
TARGETS="${TARGETS:-${TARGET:-libpng}}"
FUZZER_DIR="$MAGMA/fuzzers/symcc_std"

[ -d "$MAGMA/.git" ] || { echo "[!] Thieu vendor/magma (xem magma/setup.sh)"; exit 1; }

# vendor/ bi gitignore => file tu viet phai o symcc/fuzzer/ (co track) roi COPY vao. Idempotent.
echo "[1/2] Dat fuzzers/symcc_std vao vendor/magma"
mkdir -p "$FUZZER_DIR/src"
cp "$ROOT/symcc/fuzzer/"*.sh "$FUZZER_DIR/"
cp "$MAGMA/fuzzers/vanilla/src/afl_driver.cpp" "$FUZZER_DIR/src/"   # driver standalone, dung y vanilla
chmod +x "$FUZZER_DIR/"*.sh

# canaries=1, KHONG isan: muon binary CHAY TIEP sau khi cham bug de SymCC di het duong dan va giai
# duoc nhieu nhanh; neu -DMAGMA_FATAL_CANARIES thi trigger -> abort ngay -> mat phan duong con lai.
# USER_ID/GROUP_ID=1000: tren macOS `id -g`=20 trung group co san cua Ubuntu -> groupadd exit 4.
echo "[2/2] docker build"
for TARGET in $TARGETS; do
    echo "=================== BUILD magma-$TARGET-symcc ==================="
    docker build --platform linux/amd64 -t "magma-$TARGET-symcc" \
        --build-arg fuzzer_name=symcc_std \
        --build-arg target_name="$TARGET" \
        --build-arg USER_ID=1000 --build-arg GROUP_ID=1000 \
        --build-arg canaries=1 \
        -f "$MAGMA/docker/Dockerfile" "$MAGMA"
    echo "-> built magma-$TARGET-symcc"
done

cat <<'EOF'

XONG. LUU Y: image nay ton 2-4h build duoi QEMU — LUU LAI de khoi build lai khi `docker prune`:
    docker save magma-libpng-symcc | gzip > ~/magma-libpng-symcc.tgz
    # phuc hoi: gunzip -c ~/magma-libpng-symcc.tgz | docker load
EOF
