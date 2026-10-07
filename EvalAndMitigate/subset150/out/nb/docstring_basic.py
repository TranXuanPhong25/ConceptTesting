import sys; sys.path[:0] = ['/repo', '/repo/run']

# ---- cell 0
import os.path
import re
import sys
from gemini_shim import GeminiChat
import time

sys.path.extend([".", ".."])
import time
from tqdm import tqdm
import json
import cProfile

# from transformers import AutoTokenizer
from utils.java_parser import parse_fields_from_class_code
from data.configuration import code_base
from utils.prompt_formats.new_prompt_formatter import PromptFormatter

# ---- cell 2
# Set up OpenAI client
openai_client = GeminiChat()

# Check if the API key is set
if not openai_client.api_key:
    raise ValueError("Please set the DEEPSEEK_API_KEY environment variable.")

# ---- cell 4
profiler = cProfile.Profile()
focal_method_key = "source:source_method_code_format"
focal_method_name_key = "source:source_method_name"
focal_method_signature_key = "source:source_method_signature"
focal_method_docstring_key = "source:source_method_docstring"
focal_method_param_key = "source:source_method_parameters"
focal_method_return_type_key = "source:source_return_type"
focal_class_other_methods_key = "source:source_other_method_signature"
focal_class_fields_key = "source_class_fields"
focal_class_constructor_key = "content:source_class_constructors"
focal_class_name_key = "content:source_class_name"
focal_class_code_key = "content:source_class_code_format"
focal_class_docstring_key = "content:source_class_docstring"
source_method_type_constructor_key = "content:parameter_class_constructors"
source_method_return_type_constructor_key = "content:return_type_class_constructors"
source_method_parameter_key = "content:parameter_list"
parameter_classes_key = "content:parameter_class_signature"
source_method_signature_key = "source:source_method_signature"
source_class_imports_key = "content:source_class_code_imports"
project_name_key = 'extra:project_name'

# ---- cell 5
model_name = 'chatgpt'
tgt_model = 'GPT-4-1'
format = 'comment'
strategy = 'generation'
ignore_feature = "full"
version = 'buggy'

# ---- override after cell 5
# run/docstring.ovr, unchanged
tgt_model = os.environ['TGT_MODEL']
version = os.environ['VERSION']
print(len(data) if 'data' in dir() else '', tgt_model, version)


# ---- cell 6
formatter = PromptFormatter()

# ---- cell 7
# Load the data
data = []
source_data_file = os.path.join(code_base, f"data/prompts/{version}_source_data_unified_invoked.jsonl")
if os.path.exists(source_data_file):
    with open(source_data_file, "r") as f:
        for line in f:
            data.append(json.loads(line))

# ---- override after cell 7
# subset150: the new methods only (the 78 keep their existing docstrings), read from S150_SRC
data = [json.loads(l) for l in open(os.path.join(code_base, os.environ['S150_SRC']))]


# ---- cell 8
len(data)

# ---- cell 18
source_data_file_with_docstring = os.path.join(
    code_base,
    f"data/prompts/{tgt_model}_{version}_source_data_unified_invoked_with_docstring.jsonl"
)
source_data_file_with_docstring

# ---- override after cell 18
# subset150: new output name, the existing docstring files stay untouched
source_data_file_with_docstring = os.path.join(code_base, os.environ['S150_DOC_OUT'])


# ---- cell 19
new_instance_data = []

# ---- cell 20
pbar = tqdm(data, unit="item", total=len(data))
for idx, instance in enumerate(pbar):

    new_inst = {}
    bug_id = instance["extra:project_name"]
    new_inst["focal_method_invoked"] = instance["focal_method_invoked"]
    new_inst["id"] = bug_id
    new_inst["strategy"] = strategy
    new_inst["format"] = format
    new_inst["ablation"] = ignore_feature
    new_inst["focal_method"] = instance[focal_method_key]

    is_public, new_inst['docstring_prompt'] = formatter.apply_format_summarize(
        instance,
        model_name,
        strategy=strategy,
        formatting=format,
        ignore_feature=ignore_feature,
        project_name=bug_id,
    )

    prompt = new_inst['docstring_prompt']
    pbar.set_description(f"Generating docstring for {bug_id}")

    # Retry logic for the API call (up to 10 attempts)
    chat_completion = None
    max_retries = 1000
    for attempt in range(max_retries):
        try:
            chat_completion = openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=8192
            )
            # Only print if it succeeded after a retry (i.e. not the first attempt)
            if attempt > 0:
                print(f"Retry success for method {bug_id} after {attempt + 1} attempts")
            break  # Successful API call; exit retry loop.
        except Exception as e:
            print(f"Attempt {attempt + 1} for method {bug_id} failed: {e}")
            if attempt == max_retries - 1:
                print(f"Maximum retry attempts reached for method {bug_id}. Raising exception.")
                raise e

    generated_docstring = chat_completion.choices[0].message.content.strip()
    docstring_blocks = re.findall(r'/\*\*(.*?)\*/', generated_docstring, re.DOTALL)

    if not docstring_blocks:
        new_inst['generated_docstring'] = generated_docstring
        instance['generated_docstring'] = generated_docstring
    else:
        new_inst['generated_docstring'] = "\n/**" + docstring_blocks[0] + "*/\n"
        instance['generated_docstring'] = "\n/**" + docstring_blocks[0] + "*/\n"

    new_inst["class_name"] = bug_id
    new_inst["method_signature"] = instance['source:source_method_signature']
    new_inst["is_public"] = "1" if is_public else "0"
    new_inst["role"] = "user"

    new_instance_data.append(new_inst)

# ---- cell 21
# Write the new source data instance with generated docstring to file
with open(source_data_file_with_docstring, "w") as f:
    for instance in data:
        f.write(json.dumps(instance) + "\n")

# ---- cell 22
# open the file to see if the generated docstrings are written
with open(source_data_file_with_docstring, "r") as f:
    # load the jsons
    for line in f:
        curr_json = json.loads(line)
        if 'invoking_test_cases' not in curr_json or not curr_json['invoking_test_cases']:
            print(json.loads(line))
        if 'generated_docstring' not in curr_json or not curr_json['generated_docstring']:
            print(json.loads(line))
