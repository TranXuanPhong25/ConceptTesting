#!/bin/bash



mode="$1"
model="$2"
dataset="$3"
shift
shift
shift
extra_args=$@
seed=123456

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

PROJECT="fine_tune_baseline"
MOD_ID="${MODEL#*/}"
data_dir="../../../data/VD/"
OUTPUT_DIR=../../../data/saved_models/VD/${dataset}/${MOD_ID}
RUN_DIR="../../../data/runs/"
LOG_DIR="../../../data/logs/concept_learning/VD/${dataset}/${MOD_ID}/${PROJECT}/"

mkdir -p ${LOG_DIR}
if [ "${mode}" = "train" ]; then
    accelerate launch  --config_file ../default_config.yaml vulnerability_detection_regular_finetune.py \
        --project ${PROJECT} \
        --model_dir ${MODEL} \
        --output_dir=${OUTPUT_DIR} \
        --run_dir=${RUN_DIR} \
        --model_type=${TYPE} \
        --tokenizer_name=${TOKENIZER} \
        --model_name_or_path=${MODEL} \
        --do_train \
        --do_test \
        --train_data_file=${data_dir}/train_${dataset}.jsonl \
        --eval_data_file=${data_dir}/valid_${dataset}.jsonl \
        --test_data_file=${data_dir}/test_${dataset}.jsonl  \
        --gradient_accumulation_steps 2 \
        --epoch 10 \
        --block_size 512 \
        --train_batch_size 16 \
        --eval_batch_size 16 \
        --learning_rate 2e-5 \
        --warmup_steps 1000 \
        --max_grad_norm 1.0 \
        --evaluate_during_training \
        --seed ${seed} > "${LOG_DIR}/train_model.log" 2>&1
fi

if [ "${mode}" = "test" ]; then
    test_datas=(
        "test_${dataset}.jsonl"
        "test_${dataset}_robustness.jsonl"
    )
    log_files=(
        "evaluate_test"
        "evaluate_test_robustness"
    )
    for i in "${!test_datas[@]}"; do
        echo ${test_datas[i]}
        echo ${log_files[i]}
        accelerate launch  --config_file ../default_config.yaml vulnerability_detection_regular_finetune.py \
            --project ${PROJECT} \
            --model_dir ${MODEL} \
            --output_dir=${OUTPUT_DIR} \
            --run_dir=${RUN_DIR} \
            --model_type=${TYPE} \
            --tokenizer_name=${TOKENIZER} \
            --model_name_or_path=${MODEL} \
            --do_test_with_accelerator \
            --train_data_file=${data_dir}/train_${dataset}.jsonl \
            --eval_data_file=${data_dir}/valid_${dataset}.jsonl \
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
            --seed ${seed} > "${LOG_DIR}/${log_files[i]}.log" 2>&1
    done
fi



if [ "${mode}" = "repr" ]; then
    test_datas=(
        "test_concept_probing.jsonl"
        "train_concept_probing.jsonl"
        "valid_concept_probing.jsonl"
    )
    log_files=(
        "representation_collect_for_test"
        "representation_collect_for_train"
        "representation_collect_for_valid"
    )
    REPR_DIR="../../../data/representation/VD/${dataset}/${MOD_ID}/${PROJECT}/"
    for i in "${!test_datas[@]}"; do
        echo ${test_datas[i]}
        echo ${log_files[i]}
        accelerate launch  --config_file ../default_config.yaml vulnerability_detection_regular_finetune.py \
            --project ${PROJECT} \
            --model_dir ${MODEL} \
            --output_dir=${OUTPUT_DIR} \
            --run_dir=${RUN_DIR} \
            --model_type=${TYPE} \
            --tokenizer_name=${TOKENIZER} \
            --model_name_or_path=${MODEL} \
            --do_test_with_accelerator \
            --train_data_file=${data_dir}/train_${dataset}.jsonl \
            --eval_data_file=${data_dir}/valid_${dataset}.jsonl \
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
            --representation_dir=${REPR_DIR} \
            --collect_representation \
            --seed ${seed} > "${LOG_DIR}/${log_files[i]}.log" 2>&1
    done
fi
