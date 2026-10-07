import sys; sys.path[:0] = ['/repo', '/repo/run']

# ---- cell 0
import os.path
import re
import sys

sys.path.extend([".", ".."])
import time
from tqdm import tqdm
import json
import cProfile

# from transformers import AutoTokenizer
from utils.java_parser import parse_fields_from_class_code
from data.configuration import code_base
from utils.prompt_formats.new_prompt_formatter import PromptFormatter

# ---- cell 1
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

# ---- cell 2
formatter = PromptFormatter()

# ---- override after cell 2
import os
tgt_model = os.environ['TGT_MODEL']
version = os.environ['VERSION']
format, strategy, ignore_feature = 'comment', 'generation', 'full'
DOC_FILE = os.environ['DOC_FILE']          # which *_with_*docstring*.jsonl to read
file_post_fix = os.environ['FILE_POST_FIX']
WITH_CODE = os.environ.get('WITH_CODE') == '1'
data = [json.loads(l) for l in open(os.path.join(code_base, 'data/prompts', DOC_FILE))]
new_instance_data = []
for instance in data:
    bug_id = instance["extra:project_name"]
    new_instance = {"focal_method_invoked": instance["focal_method_invoked"], "id": bug_id, "strategy": strategy,
                    "format": format, "ablation": ignore_feature, "focal_method": instance[focal_method_key]}
    is_public, new_instance['content'] = formatter.apply_format_with_docstring(
        instance, 'chatgpt', strategy=strategy, formatting=format, ignore_feature=ignore_feature,
        project_name=bug_id, with_code=WITH_CODE, with_docstring=True)
    new_instance.update(class_name=bug_id, method_signature=instance['source:source_method_signature'],
                        is_public="1" if is_public else "0", role="user")
    new_instance_data.append(new_instance)
output_file = os.path.join(code_base, "data/prompts/rq1/" + tgt_model + f"_{format}_{strategy}_{ignore_feature}_{version}_{file_post_fix}.jsonl")
with open(output_file, "w") as f:
    for instance in new_instance_data:
        f.write(json.dumps(instance) + "\n")
print(len(new_instance_data), 'prompts ->', output_file)

