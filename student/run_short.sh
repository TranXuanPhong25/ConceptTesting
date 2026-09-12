#!/bin/bash
# ConceptCoder VD finetune RUT GON cho Kaggle (<=10h/session). Tai dung script GOC cua ho, chi doi:
#   - epoch 10 -> EPOCH (mac dinh 3)   - accelerate config -> ban Kaggle (2xT4 zero3 offload fp16)
# So concept (conceptcoder multitask) vs baseline (regular SFT) tren cung model/dataset.
#
# Chay tren Kaggle (da upload ConceptCoder/ + data/VD/ theo dung layout repo):
#   VARIANT=conceptcoder EPOCH=3 bash student/run_short.sh      # phien 1: concept (quan trong)
#   VARIANT=regular      EPOCH=3 bash student/run_short.sh      # phien 2: baseline de so
# Env: MODEL(qwen3b) | DATASET(concept) | VARIANT(conceptcoder|regular) | EPOCH(3)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VD="$ROOT/ConceptCoder/code/concept_learning/VD"
EPOCH="${EPOCH:-3}"; MODEL="${MODEL:-qwen3b}"; DATASET="${DATASET:-concept}"; VARIANT="${VARIANT:-conceptcoder}"

cp "$ROOT/student/accelerate_kaggle.yaml" "$ROOT/ConceptCoder/code/concept_learning/default_config.yaml"
sed -i "s/--epoch 10/--epoch ${EPOCH}/g" \
    "$VD/run_conceptcoder_fine_tuning.sh" "$VD/run_regular_fine_tuning.sh"   # rut epoch (idempotent-ish)

cd "$VD"
SCRIPT="run_${VARIANT}_fine_tuning.sh"     # conceptcoder | regular
echo "== TRAIN $VARIANT $MODEL $DATASET (epoch=$EPOCH) =="
bash "$SCRIPT" train "$MODEL" "$DATASET"
echo "== TEST  $VARIANT $MODEL $DATASET =="
bash "$SCRIPT" test  "$MODEL" "$DATASET"
echo "XONG $VARIANT. Doc F1 trong log: $ROOT/data/logs/concept_learning/VD/$DATASET/"
