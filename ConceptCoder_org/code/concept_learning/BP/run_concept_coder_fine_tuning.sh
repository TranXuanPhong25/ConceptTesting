#!/bin/bash

mode="$1"
model="$2"
shift
shift
extra_args=$@

concept_weight=0.20
seed=123456
port=29500

suffix="${extra_args// /}"
suffix="${suffix//--/_}"
# suffix="${extra_args// /_}"

echo "${extra_args} ${suffix}"

PROJECT="statement_level_parallel"

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
elif [ "${model}" = "magicoder" ]; then
    TYPE="magicoder"
    MODEL="ise-uiuc/Magicoder-S-CL-7B"
    TOKENIZER="ise-uiuc/Magicoder-S-CL-7B"
else
  echo "❌ Error: Unknown command '$1'" >&2
  echo "Usage: $0 [run|stop]" >&2
  exit 1
fi


echo ${TYPE}
echo ${MODEL}
echo ${TOKENIZER}
MOD_ID="${MODEL#*/}"
MOD_ID="${MODEL#*/}"

data_dir="../../../data/BP"
OUTPUT_DIR=../../../data/saved_models/BP/${MOD_ID}
RUN_DIR="../../../data/runs/"
REPR_DIR="../../../data/representation/BP//${MOD_ID}/${PROJECT}/"
LOG_DIR="../../../data/logs/concept_learning/BP/${MOD_ID}/${PROJECT}/"

echo ${LOG_DIR}
mkdir -p ${LOG_DIR}

if [ "${mode}" = "train" ]; then
    accelerate launch --config_file ../default_config.yaml --main_process_port ${port} statement_level_parallel_multi_tasking.py \
        --project ${PROJECT} \
        --model_dir ${MODEL} \
        --output_dir=${OUTPUT_DIR} \
        --run_dir=${RUN_DIR} \
        --model_type=${TYPE} \
        --tokenizer_name=${TOKENIZER} \
        --model_name_or_path=${MODEL} \
        --do_train \
        --do_test \
        --train_data_file=${data_dir}/train.jsonl \
        --eval_data_file=${data_dir}/valid.jsonl \
        --test_data_file=${data_dir}/test.jsonl \
        --gradient_accumulation_steps 2 \
        --epoch 10 \
        --block_size 512 \
        --train_batch_size 16 \
        --eval_batch_size 16 \
        --learning_rate 2e-5 \
        --warmup_steps 1000 \
        --max_grad_norm 1.0 \
        --evaluate_during_training \
        --logging_steps 500 \
        --train_concept \
        --concept_weight ${concept_weight} \
        --seed ${seed} ${extra_args} > ${LOG_DIR}/${log}.log 2>&1
fi

if [ "${mode}" = "test" ]; then
    test_datas=(
        test.jsonl
    )
    log_files=(
        evaluate_test
    )
    for i in "${!test_datas[@]}"; do
        echo ${test_datas[i]}
        echo ${log_files[i]}
        accelerate launch --config_file ../default_config.yaml --main_process_port ${port} statement_level_parallel_multi_tasking.py \
            --project ${PROJECT} \
            --model_dir ${MODEL} \
            --output_dir=${OUTPUT_DIR} \
            --run_dir=${RUN_DIR} \
            --model_type=${TYPE} \
            --tokenizer_name=${TOKENIZER} \
            --model_name_or_path=${MODEL} \
            --do_test_with_accelerator \
            --train_data_file=${data_dir}/train.jsonl \
            --eval_data_file=${data_dir}/valid.jsonl \
            --test_data_file=${data_dir}/${test_datas[i]} \
            --gradient_accumulation_steps 2 \
            --epoch 10 \
            --block_size 512 \
            --train_batch_size 16 \
            --eval_batch_size 16 \
            --learning_rate 2e-5 \
            --warmup_steps 1000 \
            --max_grad_norm 1.0 \
            --evaluate_during_training \
            --logging_steps 500 \
            --train_concept \
            --concept_weight ${concept_weight} \
            --seed ${seed} ${extra_args} > ${LOG_DIR}/${log_files[i]}.log 2>&1
    done
fi

if [ "${mode}" = "repr" ]; then
    test_datas=(
        train_concept_probing.jsonl
        valid_concept_probing.jsonl
        test_concept_probing.jsonl
    )
    log_files=(
        representation_collection_train
        representation_collection_valid
        representation_collection_test
    )
    for i in "${!test_datas[@]}"; do
        echo ${test_datas[i]}
        echo ${log_files[i]}
        accelerate launch --config_file ../default_config.yaml --main_process_port ${port} statement_level_parallel_multi_tasking.py \
            --project ${PROJECT} \
            --model_dir ${MODEL} \
            --output_dir=${OUTPUT_DIR} \
            --run_dir=${RUN_DIR} \
            --model_type=${TYPE} \
            --tokenizer_name=${TOKENIZER} \
            --model_name_or_path=${MODEL} \
            --do_test_with_accelerator \
            --train_data_file=${data_dir}/train.jsonl \
            --eval_data_file=${data_dir}/valid.jsonl \
            --test_data_file=${data_dir}/${test_datas[i]} \
            --gradient_accumulation_steps 2 \
            --epoch 10 \
            --block_size 512 \
            --train_batch_size 16 \
            --eval_batch_size 16 \
            --learning_rate 2e-5 \
            --warmup_steps 1000 \
            --max_grad_norm 1.0 \
            --evaluate_during_training \
            --logging_steps 500 \
            --train_concept \
            --concept_weight ${concept_weight} \
            --collect_representation \
            --representation_dir ${REPR_DIR} \
            --seed ${seed} ${extra_args} > ${LOG_DIR}/${log_files[i]}.log 2>&1
    done
fi