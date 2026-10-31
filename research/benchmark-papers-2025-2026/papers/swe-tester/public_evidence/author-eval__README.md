## Evaluation Scripts for SWE-Tester

- Note: All the below instructions assume that your current working directory is `eval`.

## Environment Setup

To setup the environment, run the following commands:
```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync --all-extras
```

## Evaluation in oracle retrieval setting
Refer to eval.py, eval_with_think.sh, eval_without_think.sh for instructions on how to evaluate the trained models in the oracle retrieval setting.

```bash
python eval.py --dataset <path to prepared huggingface dataset> --model_name <huggingface model name> --run_number <integer to keep track of multiple runs> --output_dir <output directory>
```

Check Artifacts document for links to models and datasets.