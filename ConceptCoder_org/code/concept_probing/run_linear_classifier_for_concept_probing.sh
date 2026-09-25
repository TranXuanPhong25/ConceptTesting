#!/bin/bash

model="$1"
task="$2"
setting="$3"
dataset="$4"
shift
shift
shift
shift
ratio="5"
PROJECT=${setting}
if [ "${setting}" = "conceptcoder" ]; then
    extra_args="--statement_level"
elif [ "${task}" = "BP" ]; then
    extra_args="--statement_level"
fi



if [ "${model}" = "qwen7b" ]; then
    TYPE="qwen"
    MODEL="Qwen/Qwen2.5-Coder-7B"
    TOKENIZER="Qwen/Qwen2.5-Coder-7B"
elif [ "${model}" = "qwen3b" ]; then
    TYPE="qwen"
    MODEL="Qwen/Qwen2.5-Coder-3B"
    TOKENIZER="Qwen/Qwen2.5-Coder-3B"
elif [ "${model}" = "starcoder3b" ]; then
    TYPE="starcoder"
    MODEL="bigcode/starcoder2-3b"
    TOKENIZER="bigcode/starcoder2-3b"
elif [ "${model}" = "starcoder7b" ]; then
    TYPE="starcoder"
    MODEL="bigcode/starcoder2-7b"
    TOKENIZER="bigcode/starcoder2-7b"
elif [ "${model}" = "codellama7b" ]; then
    TYPE="codellama"
    MODEL="meta-llama/CodeLlama-7b-hf"
    TOKENIZER="meta-llama/CodeLlama-7b-hf"
elif [ "${model}" = "deepseek7b" ]; then
    TYPE="deepseek"
    MODEL="deepseek-ai/deepseek-coder-7b-base-v1.5"
    TOKENIZER="deepseek-ai/deepseek-coder-7b-base-v1.5"
elif [ "${model}" = "magicoder" ]; then
    TYPE="magicoder"
    MODEL="ise-uiuc/Magicoder-S-CL-7B"
    TOKENIZER="ise-uiuc/Magicoder-S-CL-7B"
elif [ "${model}" = "codegemma7b" ]; then
    TYPE="codegemma"
    MODEL="google/codegemma-7b"
    TOKENIZER="google/codegemma-7b"
elif [ "${model}" = "llama3b" ]; then
    TYPE="llama"
    MODEL="meta-llama/Llama-3.2-3B"
    TOKENIZER="meta-llama/Llama-3.2-3B"
elif [ "${model}" = "llama8b" ]; then
    TYPE="llama"
    MODEL="meta-llama/Llama-3.1-8B"
    TOKENIZER="meta-llama/Llama-3.1-8B"
else
  echo "❌ Error: Unknown command '$1'" >&2
  echo "Usage: $0 [run|stop]" >&2
  exit 1
fi

MOD_ID="${MODEL#*/}"
OUTPUT_DIR="../../saved_models/linear_classifiers/${task}/${dataset}/${MOD_ID}/${PROJECT}/"
REPR_DIR="../../data/representation/${task}/${dataset}/${MOD_ID}/${PROJECT}/"
data_dir="../../data/${task}"
LOG_DIR="../../data/logs/linear_classifier/${task}/${dataset}/${MOD_ID}/${PROJECT}/"

mkdir -p ${LOG_DIR}
mkdir -p ${OUTPUT_DIR}

python train_linear_classifier_for_concept_probing.py \
    --project ${PROJECT} \
    --model_type ${MOD_ID} \
    --train_data_file ${data_dir}/train_concept_probing.jsonl \
    --eval_data_file ${data_dir}/valid_concept_probing.jsonl \
    --test_data_file ${data_dir}/test_concept_probing.jsonl \
    --model_saved_dir ${OUTPUT_DIR} \
    --repr_dir ${REPR_DIR} \
    --do_train \
    --do_test \
    --batch_size=32 \
    --num_epochs 100 \
    --repr_dir=${REPR_DIR} ${extra_args} > ${LOG_DIR}/train_concept.log 2>&1
