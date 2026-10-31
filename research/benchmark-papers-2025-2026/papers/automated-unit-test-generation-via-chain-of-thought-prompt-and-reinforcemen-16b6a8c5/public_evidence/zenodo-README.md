# Introduction
This is the replication package for the paper "TestCTRL: Automated Unit Test Generation via Chain of Thought Prompt and Reinforcement Learning".

# Requirements
## Softwares
- python: 3.10.12
- CUDA: 11.7
- torch==1.13.1+cu111
- scikit-learn==1.3.0
- peft==0.5.0
- transformers==4.33.0
- numpy==1.25.2
- scipy==1.10.1
- torchaudio==0.13.1
- torchvision==0.14.1+cu117

## Hardwares (opt.)
- GPU: 8 * A800 80GB


# Organization of the Replication Package
- `checkpoints`: fine-tuned models, including TestCTRL, TestCT, TestCT-no-cot, TestCT-intention, TestCT-input, TestCT-ti, CodeBERT-line, CodeT5-line, CodeGPT-line, CodeBERT-branch, CodeT5-branch, and CodeGPT-branch.
- `dataset`: Datasets for fine-tuning and reinforcement learning, including the CoT dataset, reward dataset (reward folder), and the dataset for PPO optimization (rl folder).
- `evaluation`: scripts for evaluating the generated tests, including CodeBLEU, syntactic correct rate, compilation passing rate, line coverage rate, and branch coverage rate.
- `finetune`: scripts and configs for fine-tuning large language models for test generation.
- `generated_test_result`: the generated tests.
- `pretrain`: pre-trained models, including CodeLlama, CodeBERT, CodeT5, and CodeBERT. 
- `CoT_quality`: the example of evaluating CoT prompts.


# How to Run
## Prepare the environment
1. Create a new conda environment and activate it
```bash
conda create -n testctrl python=3.10
conda activate testctrl
```
2. Install the `pytorch` version compatible with your version of cuda [here](https://pytorch.org/get-started/previous-versions/), for example the following command works with cuda 11.6
```bash
conda install pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 pytorch-cuda=11.7 -c pytorch -c nvidia
```
3. Install `transformers` and `peft`
```bash
conda install -c huggingface transformers 
pip install git+https://github.com/huggingface/peft.git
```
Note that you can install the latest stable version of transformers by using
```bash
pip install git+https://github.com/huggingface/transformers
```
4. Install `datasets`, `accelerate` and `huggingface_hub`
```bash
conda install -c huggingface -c conda-forge datasets
conda install -c conda-forge accelerate
conda install -c conda-forge huggingface_hub
```
5. Install `bitsandbytes` and `wandb`
```bash
pip install bitsandbytes (cp libbitsandbytes_cuda117.so libbitsandbytes_cpu.so )
pip install wandb
```
6. Make sure you are logged in `wandb`:
```bash
wandb login
```
7. Put the pre-trained models (codellama, codebert, codet5, codegpt) in the pretrain folder
codellama-7b[here]: https://huggingface.co/codellama/CodeLlama-7b-hf
codellama-13b[here]: https://huggingface.co/codellama/CodeLlama-13b-hf
codebert[here]: https://huggingface.co/microsoft/codebert-base
codet5[here]: https://huggingface.co/Salesforce/codet5-base
codegpt[here]: https://huggingface.co/microsoft/CodeGPT-small-java
8. Generate CoT prompts, add the organization_key, api_key, and openai_api_key in the 8 line, 9 line, and 10 line of the generate_cot_prompt.py. Modify the input filename in the 212 line of the generate_cot_prompt.py，
```bash
python generate_cot_prompt.py
```

## Fine-tune the codellama model as the policy model
1. fine-tune the codellama model using the CoT prompt
```bash
cd TestCTRL
python -m torch.distributed.launch --nproc_per_node 8 finetune/finetune_llama.py --model_path="./pretrain/codellama/7B" --dataset_name="./dataset" --size_valid_set 10000 --streaming --seq_length 2048 --max_steps 350 --batch_size 8 --gradient_accumulation_steps 16 --learning_rate 1e-4 --lr_scheduler_type="cosine" --num_warmup_steps 50 --weight_decay 0.05 --output_dir="./checkpoints" --input_column_name="src_fm_cot_gpt" --output_column_name="target" 
```
2. Modify the 11 line and merge PEFT adapter layers
```bash
python finetune/merge_peft_adapters_codellama.py --base_model_name_or_path='./pretrain/codellama/7B' --peft_model_path='./checkpoints/cot_codellama_7b_combine_50k'
```

## Fine-tune the CodeGPT model as the reward model
```bash
python finetune/reward_regression_codet5.py --model_name_or_path="./pretrain/codet5" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="line_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=4 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codet5_line/"

python finetune/reward_regression_codebert.py --model_name_or_path="./pretrain/codebert" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="line_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=4 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codebert_line/"

python finetune/reward_regression_gpt2.py --model_name_or_path="./pretrain/codegpt" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="line_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=16 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codegpt_line/"

python finetune/reward_regression_codet5.py --model_name_or_path="./pretrain/codet5" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="condition_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=16 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codet5_branch/"

python finetune/reward_regression_codebert.py --model_name_or_path="./pretrain/codebert" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="condition_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=16 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codebert_branch/"

python finetune/reward_regression_gpt2.py --model_name_or_path="./pretrain/codegpt" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="condition_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=16 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="./checkpoints/reward_model_codegpt_branch/"
```

## Using PPO to optimize the policy model
```bash
python finetune/rl.py --base_model_name="./checkpoints/cot_codellama_7b_combine_50k" --base_tokenizer_name="./checkpoints/cot_codellama_7b_combine_50k" --reward_model_name="./reward_model_codegpt_line" --reward_tokenizer_name="./reward_tokenizer_name" --log_with="wandb" --batch_size=8 --ppo_epochs=2 --save_freq=100 --output_dir="./checkpoints"

python finetune/merge_peft_adapters_rl.py --base_model_name="./checkpoints/cot_codellama_7b_combine_50k" --adapter_model_name="./checkpoints/" --output_name="./checkpoints/ppo_final_checkpoint"
```

## Evaluation
1. Generating the test cases using the reinforcement learning model
```bash
python finetune/predict_llama.py --data_file="./dataset/all_tests_d4j.csv" --model_name="./checkpoints/cot_codellama_7b_combine_50k" --output="./checkpoints/"
python finetune/predict_llama.py --data_file="./dataset/trigger_bug_tests_d4j.csv" --model_name="./checkpoints/cot_codellama_7b_combine_50k" --output="./checkpoints/"
```
2. Predicting the line coverage rate based on the fine-tuned model
```bash
python finetune/predict_reward.py --input_file="./dataset/reward/test_athena.json" --model_name="./checkpoints/reward_model_codegpt_line" --output="./result/reward/predict_reward_bert.csv" --model_type="codegpt"
```
3. Using multiple metrics to evaluate the generated unit tests
- codeBLEU: target.txt is the original test case written by human, final_target.txt is the generated test case by large language models.
```bash
pip install tree_sitter
cd parser
bash build.sh
python evaluation/codebleu/calc_code_bleu.py --refs target.txt --hyp final_target.txt --lang java --params 0.25,0.25,0.25,0.25
```
4. Using the defects4j (i.e., Cobertura) to calculate compilation passing rate, line coverage rate, and branch coverage rate.
<!-- - Correct Rate: Using the tree-sitter to parse the code and analyze the correct rate.
- Passing Rate: Using the Cobertura to calculate the passing rate.
- Line Coverage Rate: Using the Cobertura to calculate the line coverage rate.
- Branch Coverage Rate: Using the Cobertura to calculate the branch coverage rate. -->
The script to calculate compilation passing rate, line coverage rate, and branch coverage rate in the defects4j_script.tar.

