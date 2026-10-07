import sys; sys.path[:0] = ['/repo', '/repo/run']

# ---- cell 0
import os
import glob
import json
import re
import subprocess
from gemini_shim import GeminiChat
import shutil
import hashlib

# ---- cell 1
from data.configuration import d4j_proj_base, code_base, d4j_command

# ---- cell 2
import_json_path = "data/import_v2.json"
with open(import_json_path, "r") as file:
    import_json = json.load(file)
with open(os.path.join(code_base, "data/test_src.json"), "r") as f:
    content_path = json.load(f)

# ---- cell 4
# Retrieve the current PATH
current_path = os.environ.get('PATH')
print(f"Current PATH: {current_path}")

# Define the new directory you want to add
new_directory = '/defects4j/framework/bin'

# Update the PATH environment variable
os.environ['PATH'] = f"{new_directory}:{current_path}"

# Verify the update
updated_path = os.environ.get('PATH')
print(f"Updated PATH: {updated_path}")

# ---- cell 5
# Set up OpenAI client
openai_client = GeminiChat()

# Check if the API key is set
if not openai_client.api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# ---- cell 8
tgt_model = 'GPT-O4-MINI'
format = 'comment'
strategy = 'generation'
ablation = 'full'
version = 'buggy'
min_test_num = 10

# ---- override after cell 8
tgt_model = os.environ['TGT_MODEL']
version = os.environ['VERSION']


# ---- cell 9
# file_post_fix = f'unified_invoked'
file_post_fix = f'unified_invoked_docstring_prompt'
# file_post_fix = f'unified_invoked_advanced_docstring_prompt'
# file_post_fix = f'unified_invoked_docstring_code_prompt'
# file_post_fix = f'unified_invoked_docstring_cot_prompt'
# file_post_fix = f'unified_invoked_docstring_cot_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_docstring_cot_prompt_min_test_num_{min_test_num}_err_msg_prompt'
# file_post_fix = f'unified_invoked_docstring_cot_few_shot_prompt'
# file_post_fix = f'unified_invoked_code_cot_few_shot_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_docstring_cot_few_shot_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_docstring_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_docstring_few_shot_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_generated_focal_prompt_min_test_num_{min_test_num}'
# file_post_fix = f'unified_invoked_generated_focal_prompt'
# file_post_fix = f'unified_invoked_generated_focal_err_msg_prompt_min_test_num_{min_test_num}'

# ---- override after cell 9
file_post_fix = os.environ['FILE_POST_FIX']


# ---- cell 10
# Define the path to the JSONL file
# jsonl_file_path = f'/repo/data/prompts/rq1/{tgt_model}_{format}_{strategy}_{ablation}_{version}_unified_invoked_generated_focal_err_msg_prompt_min_test_num_{min_test_num}.jsonl'
# jsonl_file_path = f'/repo/data/prompts/rq1/chatgpt_{format}_{strategy}_{ablation}_{version}_unified_invoked.jsonl'
jsonl_file_path = f'/repo/data/prompts/rq1/{tgt_model}_{format}_{strategy}_{ablation}_{version}_{file_post_fix}.jsonl'


# ---- cell 12
deprecated_bugs = ["Cli_6_", "Closure_63_", "Closure_93_", "JacksonDatabind_65_", "JacksonDatabind_89_", "Lang_2_", "Lang_18_", "Lang_25_", "Lang_48_", "Time_21_"]

# ---- cell 13
# Read the JSONL file and load the data
data = []
with open(jsonl_file_path, 'r') as f:
    for line in f:
        curr_json = json.loads(line)
        # check if curr_json['id'] starts with any of the deprecated_bugs
        if any(curr_json['id'].startswith(bug_id) for bug_id in deprecated_bugs):
            print(f"Skipping deprecated bug: {curr_json['id']}")
            continue
        data.append(curr_json)

# Check if data is loaded
if not data:
    raise ValueError("No data found in the JSONL file.")

print(f"Total items in data: {len(data)}")

# ---- cell 27
item_with_completion_path = f'/repo/data/prompts/rq1/{tgt_model}_{format}_{strategy}_{ablation}_{version}_{file_post_fix}_with_completion.jsonl'

# ---- cell 29
failed_items = []

# ---- cell 31
test_data = data

# ---- cell 32
print(len([data_inst for data_inst in test_data if 'completion' in data_inst]))

# ---- cell 33
# add tqdm for progress bar
from tqdm import tqdm

# ---- cell 34

with_completion = []
failed_items = []  # Initialize list for failed items
pbar = tqdm(test_data, desc="Processing items", unit="item", total=len(test_data))

# Loop through each item in the data
for item in pbar:
    # Parse project info
    if 'completion' in item:
        with_completion.append(item)
        continue
    method_id = item['id']
    prompt = item['content']
    if prompt:
        pbar.set_description(f"Generating unit test for {method_id}")

        chat_completion = None
        max_retries = 20  # Define maximum number of retries

        # Retry the API call up to max_retries times.
        for attempt in range(max_retries):
            try:
                # Generate unit test using OpenAI API
                chat_completion = openai_client.chat.completions.create(
                    model="o4-mini",
                    reasoning_effort="high",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    # temperature=0.0,
                    # max_tokens=8192
                )
                # Print success message only if it wasn't the first attempt.
                if attempt > 0:
                    print(f"Retry success for method {method_id} after {attempt + 1} attempts")
                break  # Successful API call; exit the retry loop.
            except Exception as e:
                print(f"Attempt {attempt + 1} for method {method_id} failed: {e}")
                # Check if maximum retries have been reached
                if attempt == max_retries - 1:
                    print(f"Maximum retry attempts reached for method {method_id}. Breaking the loop.")
                    failed_items.append(item)
                    chat_completion = None

        # If no successful API call after all retries, break out of the outer loop.
        if chat_completion is None:
            break

        # Extract the assistant's reply
        generated_test = chat_completion.choices[0].message.content.strip()
        item['reasoning_token_count'] = chat_completion.usage.completion_tokens_details.reasoning_tokens
        item['completion'] = generated_test

    # assert 'completion' in item and not none and not empty
    assert 'completion' in item and item['completion'] is not None and item['completion'].strip() != ''

    # Append the item with completion to the list
    with_completion.append(item)

# ---- cell 35
len(with_completion)

# ---- cell 37
# Write the items with completion to the file
with open(item_with_completion_path, 'w') as f:
    for item in with_completion:
        f.write(json.dumps(item))
        f.write('\n')

# ---- cell 38
item_with_completion_path

# ---- cell 39
failed_items

# ---- cell 40
# read the new json file to see if all the completions are written
with open(item_with_completion_path, 'r') as f:
    completion_json = []
    for line in f:
        completion_json.append(json.loads(line))
    print(len(completion_json))

for item in completion_json:
    if 'completion' not in item:
        print(item['id'])
