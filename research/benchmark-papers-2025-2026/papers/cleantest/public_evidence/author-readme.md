# Intro
This is the replication package for the paper "Less is More: On the Importance of Data Quality for Unit Test Generation".

## Task Definition
Given the focal method, the task aims to compare the test generation and bug detection performances of different datasets on four large language models. 

## The static of dataset

- **idx:** the index of example
- **src_fm:** the method under test
- **target:** the test case
- **condition_cover_rate:** the predicted branch coverage
- **line_cover_rate:** the predicted line coverage

|  Methods2Test File Name  | #Examples |
| :--------------: | :-------: |
| filter_train.csv |  469174   |
| filter_valid.csv |  117294   |

|  Methods2Test File Name  | #Examples |
| :---------------: | :-------: |
| all_train.csv     |  624022   |
| all_valid.csv     |  156295   |

|        Noise Type       |     #Examples      |
| :---------------------: | :----------------: |
| No Duplicate            |  736598            |
| Ambiguous Data Type     |  22674 (3.0782%)   |
| Unnecessary Annotations |  321420 (43.6357%) |
| Empty Exception         |  5010   (0.6802%)  |
| Empty Function          |  2480   (0.3367%)  |
| Syntax Errors           |  8211   (1.1147%)  |
| Non-Literal             |  1187   (0.1611%)  |
| No Relevance            |  93583  (12.7048%) |
| Low Branch Coverage     |  29111   (3.9521%) |

ATLAS: (188,154)
train.csv: 150,522
eval.csv: 18,816
test.csv: 18,815
|        Noise Type       |    #Examples (No Duplicate) | 
|       :----------:      |    :-185,993 (178052)-:     | 
|   Ambiguous Data Type   |      9 (0.0051%)     | 
| Unnecessary Annotations |      9  (0.0051%).   | 
|     Empty Exception     |      989 (0.5555%)     | 
|     Empty Function      |      53 (0.0298%)     | 
|     Syntax Errors       |      45517+8555 (51174) (28.7410%)  | 
|     Non-Literal         |      65 (0.0365%)     | 
|     No Relevance        |      0 (0%)          | 
|   Low Branch Coverage   |      1,375 (0.7722%)    | 
|   Total no noise data   |      52,798 (29.6531%) | 


## Pipeline-CleanTest
We also provide a pipeline that identify noise in Methodes2test dataset and fine-tunes four LLMs (CodeLlama7B, StarCoder, CodeBERT, CodeT5) on this task.

### Rule-based syntax filter and relevance filter
#### Tree-sitter
```bash
pip install tree_sitter
cd parser
bash build.sh
python rule_filter.py
```

### Model-based coverage filter
#### Train the coverage filter
```bash
cd script
python reward_regression_gpt2.py --model_name_or_path="../models/codegpt" --train_file="./dataset/reward/train_athena.json" --validation_file="./dataset/reward/valid_athena.json" --metric_name="accuracy" --do_regression --shuffle_train_dataset --text_column_names="focal_method,test_case" --text_column_delimiter="\n" --label_column_name="condition_cover_rate" --do_train --do_eval --max_seq_length=512 --per_device_train_batch_size=32 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="../result/reward_model_codegpt_branch/"
```
#### Predict the branch coverage
```bash
cd script
python reward_regression_gpt2.py --model_name_or_path="../result/reward_model_codegpt_branch/checkpoint_last" --train_file="./dataset/test_m2t.csv" --validation_file="./dataset/test_m2t.csv" --test_file="./dataset/filter_m2t.csv" --metric_name="accuracy" --do_regression --text_column_names="src_fm,target" --text_column_delimiter="\n" --label_column_name="condition_cover_rate" --do_predict --max_seq_length=512 --per_device_train_batch_size=32 --learning_rate=1e-5 --num_train_epochs=5 --output_dir="../result/reward_model_codegpt_branch/"
```

### CodeLlama7B and StarCoder
1. Fine-tune CodeLlama7B and StarCoder using three version dataset
```bash
cd script
python -m torch.distributed.launch --nproc_per_node 4 --master_port 29501 run_gen_llama.py --model_path="../models/codellama7B" --train_file='control_train.csv' --valid_file='control_valid.csv' --test_file='control_test.csv' --dataset_name="../dataset/new_filter" --size_valid_set 70000 --streaming --seq_length 1024 --max_steps 250 --batch_size 32 --gradient_accumulation_steps 16 --learning_rate 1e-4 --lr_scheduler_type="cosine" --num_warmup_steps 50 --weight_decay 0.05 --output_dir="./checkpoints_llama7b_m2t_control" --input_column_name="src_fm" --output_column_name="target" --wandb_name="llama7b_m2t_control" --checkpoint="checkpoint_llama7b_m2t_control"

python -m torch.distributed.launch --nproc_per_node 4 --master_port 29502 run_gen_starcoder.py --model_path="../models/starcoder" --train_file='control_train.csv' --valid_file='control_valid.csv' --test_file='control_test.csv' --dataset_name="../dataset/new_filter" --size_valid_set 70000 --streaming --seq_length 1024 --max_steps 500 --batch_size 16 --gradient_accumulation_steps 16 --learning_rate 1e-4 --lr_scheduler_type="cosine" --num_warmup_steps 50 --weight_decay 0.05 --output_dir="./checkpoints_starcoder_m2t_control" --input_column_name="src_fm" --output_column_name="target" --wandb_name="starcoder_m2t_control" --checkpoint="checkpoint_starcoder_m2t_control"
```

2. Generate the fine-tuned LLMs
```bash
python script/merge_peft_adapters_codellama.py --peft_model_path="../checkpoints_llama7b_m2t_control/checkpoint_llama7b_m2t_control"
python script/merge_peft_adapters_starcoder.py --peft_model_path="../checkpoints_starcoder_m2t_control/checkpoint_starcoder_m2t_control"
```

3. Inference the fine-tuned LLMs for the test generation and bug detection tasks
```bash
python inference_m2t_llama.py --model_name="../llama_checkpoints/checkpoint_llama7b_m2t_all" --input_dir="../dataset/modified_14projects_tests_d4j.csv" --output_dir="../result/d4j_fm_codellama_all_greedy.csv"

python inference_m2t_llama_bug.py --model_name="../new_llama_checkpoints/checkpoint_llama7b_m2t_all" --input_dir="../dataset/trigger_bug_fm_all_projects_d4j_processed_final.csv" --output_dir="d4j_fm_codellama_all_bug.csv" 

python inference_m2t_starcoder.py --model_name="../starcoder_checkpoints/checkpoint_starcoder_m2t_control" --input_dir="../dataset/modified_14projects_tests_d4j.csv" --output_dir="d4j_fm_starcoder_control_greedy.csv"

python inference_m2t_starcoder_bug.py --model_name="../starcoder_checkpoints/checkpoint_starcoder_m2t_all" --input_dir="../dataset/trigger_bug_fm_all_projects_d4j_processed_final.csv" --output_dir="d4j_fm_starcoder_all_bug.csv"
```

### CodeBERT and CodeT5 model
1. change the 'train_filename', 'dev_filename', 'output_dir', and 'train_steps' fields in the following script for different dataset version (original, filtered, controlled)
2. run the following scripts to fine-tune pre-trained language models (CodeBERT and CodeT5)

```bash
conda activate test
cd script
python run_bert.py --do_train --model_type=roberta --model_name_or_path='../models/codebert' --config_name='../models/codebert' --tokenizer_name='../models/codebert' --train_filename='../dataset/all_m2t/train.csv' --dev_filename='../dataset/all_m2t/valid.csv' --output_dir='../result/athena_bert_all' --max_source_length=512 --max_target_length=512 --beam_size=5 --train_batch_size=16 --eval_batch_size=16 --learning_rate=5e-5 --train_steps=12400 --eval_steps=50

python run_codet5.py --do_train --model_type=codet5 --model_name_or_path='../models/codet5' --config_name='../models/codet5' --tokenizer_name='../models/codet5' --train_filename='../dataset/all_m2t/train.csv' --dev_filename='./dataset/all_m2t/valid.csv' --output_dir='../result/athena_codet5_all' --max_source_length=1024 --max_target_length=1024 --beam_size=5 --train_batch_size=8 --eval_batch_size=8 --learning_rate=5e-5 --train_steps=25000 --eval_steps=1000
```
3. run the following scripts to inference CodeBERT and CodeT5 and generate test cases in the validation dataset (Defects4J).
```bash
cd script
python run_bert.py --do_test --model_type=roberta --model_name_or_path='../models/codebert' --config_name='../models/codebert' --tokenizer_name='../models/codebert' --load_model_path='../result/athena_bert_all/checkpoint-last/pytorch_model.bin' --test_filename='../dataset/trigger_bug_fm_all_projects_d4j_processed_final.csv' --output_dir='../result/athena_bert_all/bug_trigger' --max_source_length=512 --max_target_length=512 --beam_size=5 --eval_batch_size=128

python run_codet5.py --do_test --model_type=codet5 --model_name_or_path='../models/codet5' --config_name='../models/codet5' --tokenizer_name='../models/codet5' --load_model_path='../result/athena_codet5_all/checkpoint-last/pytorch_model.bin' --test_filename='../dataset/trigger_bug_fm_all_projects_d4j_processed_final.csv' --output_dir='../result/athena_codet5_all/bug_trigger' --max_source_length=512 --max_target_length=512 --beam_size=5 --eval_batch_size=64
```

#### Result Preprocess
1. place the file "../result/d4j_fm_codellama_all_greedy.csv" into the "../result/d4j_fm_codellama_all_greedy_process.csv" using the result_preprocess.py file
2. using the csv reader to check the generated result and generate the "../result/d4j_fm_codellama_all_greedy_processed.csv" file.


## Evaluation
### CodeBLEU
- codeBLEU: target.txt is the original test case written by human, final_target.txt is the generated test case by LLM.
```bash
pip install tree_sitter
cd parser
bash build.sh
cd evaluation/CodeBLEU
modify the file name of the generate_txt.py in line 3
python generate_txt.py
python calc_code_bleu.py --refs target.txt --hyp final_target.txt --lang java --params 0.25,0.25,0.25,0.25
```

### Syntactic (i.e., syntactic correctness rate)
```bash
cd evaluation
Modify the file name in the 21 line in the syntax_check.py file
python syntax_check.py
```

### Code Coverage (including the compilation passing rate, line coverage, and branch coverage)
```bash
cd evaluation
python run_evaluation_d4j.py --input_file="../result/codellama/d4j_fm_codellama_all_greedy_processed.csv" --log_file="../result/log_err_codellama_m2t_all.txt" --output_file="../result/codellama_result_m2t_all.csv"
```

### Bug Detection
```bash
cd evaluation
python eval_bug_detection_fm.py --input_file="../dataset/d4j_fm_codellama_all_trigger_bug_greedy_processed.csv" --log_file="../result/log_err_bug_codellama_all_d4j.txt" --output_file="../result/codellama_all_result_m2t.csv"
```
