# Training Scripts for SWE-Tester

- Note: All the below instructions assume that your current working directory is `torchtune_train`.

## Environment Setup

To setup the environment, run the following commands:
```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync --all-extras
```

## Data preparation
To prepare training data for torchtune, we fetch pre-processed data from HuggingFace and save it locally as a JSONL file. To do this, run the following command:

```bash
./tune_data_prep.sh
```

## Download pre-trained models from HuggingFace Hub
We need to download pre-trained Qwen2.5-Coder-Instruct models from HuggingFace Hub. Note that this step will take around 106GB of disk space to store the model weights. You can adjust the bash script to download a specific model sizes if required.

For downloading all the models, run the following command:

```bash
./download_models.sh
```

## Single-node Multi-GPU training
We prepare torchtune config `yml` files for different model sizes, amounts of data and different training strategies (with and without thinking). We run finetuning in single-node multi-GPU setup using `tune run` command.

To run finetuning for a specific config, run the following command:

```bash
tune run --nnodes 1 --nproc_per_node <num_gpus> full_finetune_distributed --config <path_to_config_file>
```

where `<num_gpus>` is the number of GPUs to use and `<path_to_config_file>` is the path to the config file in the `configs` directory.

- Note: The configs are written for 8 GPUs to achieve an effective batch size of 32 (per GPU batch size = 1 and gradient accumulation steps = 4). If you want to use a different number of GPUs, you can adjust the batch size/gradient accumulation steps in the config file or by overriding the command line arguments to maintain the same effective batch size.

For example, to finetune Qwen2.5-Coder-7B-Instruct with 4 GPUs, batch size = 1 per GPU and global batch size = 32, no thinking, on entire training data, run the following command:

```bash
tune run --nnodes 1 --nproc_per_node 4 full_finetune_distributed --config configs/qwen_2_5_coder_7b_instruct/without_thinking/tune_full_data.yml gradient_accumulation_steps=8
```

## Single-node Single-GPU training
To run finetuning of 7B model on a single GPU, you can run the following command (this script runs training without thinking on full training data):

```bash
tune run full_finetune_single_device --config configs/qwen_2_5_coder_7b_instruct/without_thinking/tune_single_device.yml
```