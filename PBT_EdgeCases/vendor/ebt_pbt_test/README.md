# ebt_pbt_test

## Preparation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

2. Download the dataset.

    ```bash
    uv run pbteval dataset download
    ```

3. Set up OpenRouter API key in `.env`:

    ```env
    OPENROUTER_API_KEY=your_openrouter_api_key
    ```

## Usage

### Generate test codes

The test codes generated for our case study are already saved in `output/`. If you want to generate new code, please execute the following command.

EBT:
```bash
uv run pbteval generate ebt HumanEval/22 --model anthropic/claude-sonnet-4
```

PBT:
```bash
uv run pbteval generate pbt HumanEval/22 --model anthropic/claude-sonnet-4
```

### Run the tests

EBT:
```bash
uv run pbteval run ebt --canonical --model anthropic/claude-sonnet-4
```

PBT:
```bash
uv run pbteval run pbt --canonical --model anthropic/claude-sonnet-4
```

## Case study
- In the case study, Claude Sonnet 4 was used via OpenRouter.
- When LLMs were used, no parameters were specified and the default values were applied.

## Regarding manual correction of wrong test cases

The test codes for the case study, located in `output/`, includes manually excluded test cases that have been commented out.

### EBT
- In 12 out of 16 cases, at least one wrong test case was excluded.
- A total of 48 out of 468 test cases were excluded.

### PBT
- In 5 out of 16 cases, at least one wrong test case was excluded.
- A total of 7 out of 146 test cases were excluded.

## Datasets

This tool uses the following datasets:
- [AgentCoder](https://github.com/huangd1999/AgentCoder)
- [HumanEval](https://huggingface.co/datasets/openai/openai_humaneval)
- [HumanEval+](https://huggingface.co/datasets/evalplus/humanevalplus)
- [MBPP](https://huggingface.co/datasets/google-research-datasets/mbpp)
- [MBPP+](https://huggingface.co/datasets/evalplus/mbppplus)
