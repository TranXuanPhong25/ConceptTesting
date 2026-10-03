# Generate a valid program for each API
```
    python genPrograms.py
```
Then you will get `api_programs.json` that contains all initial programs invoking the target APIs.

# Perform mutation
## For each target API, generate prompts based on the generated valid program and generated mutator.
```
    python gen_prompts_for_mutators.py 
```
Then you will get `outputs/Prompts.jsonl` that contains all mutation prompts.

## Run the prompts
```
    python runPrompts.py
```
Then you will get `outputs/output.jsonl` that contains all responses.

Because we do not have enough API keys, we have to divide the target programs into multiple batches.
After a execution stopped, we rerun `python gen_prompts_for_mutators.py ` and `python run_prompts.py`.

If you want to extract the generated programs, run the following cmd to extract the newest generated programs.
Before run it, you need to define the target fileflod name.
```
    python extract_programs.py
```
