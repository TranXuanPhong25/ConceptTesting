import json
import os
import difflib
from datasets import load_dataset
from argparse import ArgumentParser
from llm_utils import filter_prompt_list, get_model, get_sampling_params, query_vllm_batch
import re

SEARCH_REPLACE_REGEX = r"```.*?\n### (.*)\n<<<<<<< SEARCH\n([\s\S]*?)\n=======\n([\s\S]*?)\n>>>>>>> REPLACE\n```"
MAX_MODEL_LENGTH = 32768
NUM_RETRIES = 10

def parse_search_replace(text: str) -> dict[str, list[tuple[str, str]]]:
    """
    Parse the search/replace blocks from the text.

    Returns:
        A dictionary where the key is the file path and the value is a list of search/replace pairs.
    """
    path_search_replaces: list[tuple[str, str, str]] = re.findall(
        SEARCH_REPLACE_REGEX, text
    )
    path_search_replace_dict = dict[str, list[tuple[str, str]]]()
    for path, search, replace in path_search_replaces:
        path_search_replace_dict.setdefault(path, []).append((search, replace))
    return path_search_replace_dict

def apply_search_replace_edit(output, test_code_file):
    search_replaces = parse_search_replace(output)
    if len(search_replaces) == 0:
        print(f"No valid search blocks found in output")
        return None
    new_content = "\n" + test_code_file

    if len(search_replaces) > 1:
        return None
    path = list(search_replaces.keys())[0]
    search_replaces = search_replaces[path]
    for search, replace in search_replaces:
        # Ensure search block can be matched
        # "\n" + search to ensure the indentations are correct
        if len(search) == len(replace) and search == replace:
            print("Search block same as replace block")
            return None
        search = "\n" + search
        replace = "\n" + replace
        if search not in new_content:
            print("Search block not present in the file")
            return None
        new_content = new_content.replace(search, replace)
    return new_content

def generate_unified_diff(
    old_code: str,
    new_code: str,
    filename: str,
    n_context: int = 3,
) -> str:
    """Generate a unified diff between two code.

    Args:
        old_code: The original code.
        new_code: The modified code.
        n_context: The number of context lines to show.

    Returns:
        A string representing the unified diff."""

    original_lines = old_code.splitlines()
    modified_lines = new_code.splitlines()

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
        n=n_context,
    )
    try:
        diff_code = "\n".join(diff)
        diff_code = f"diff --git a/{filename} b/{filename}\n{diff_code}"
        return diff_code
    except Exception as e:
        print(f"Error while creating unified diff: {str(e)}")
        return ""

def process_output(output_dict, model_name, test_file_map):
    processed_output_list = []
    err_cnt = 0
    for instance_id, output in output_dict.items():
        model_diff = ""
        test_filename, old_code = test_file_map[instance_id]
        if output is not None and output != "":
            output = output.strip()
            if "<solution>" in output and "</solution>" in output:
                parsed_output = output.split("<solution>")[1].split("</solution>")[0]
                new_code = apply_search_replace_edit(parsed_output, old_code)
                if new_code is not None:
                    model_diff = generate_unified_diff(old_code, new_code, test_filename)
            else:
                print(f"No <solution> block found in output for instance {instance_id}")
                model_diff = ""
        else:
            model_diff = ""
        
        if model_diff == "":
            err_cnt += 1
        else:
            processed_output_list.append({
                "instance_id": instance_id,
                "model_name_or_path": model_name,
                "model_patch": model_diff,
                "full_output": output
            })
    print(f"Error count: {err_cnt} out of {len(output_dict)}")
    return processed_output_list

def main(args):
    dataset = load_dataset(args.dataset, split=args.dataset_split)
    data = [instance for instance in dataset]

    valid_ids = set([item["instance_id"] for item in data])
    test_file_map = {}
    for item in data:
        instance_id = item["instance_id"]
        test_file_name = item["test_file"]
        test_code = item["test_code"]
        test_file_map[instance_id] = [test_file_name, test_code]

    output_list = []
    model = get_model(args)
    data = filter_prompt_list(data, model, MAX_MODEL_LENGTH)

    for i in range(NUM_RETRIES):
        sampling_params = get_sampling_params(args, temperature=0.1*i)
        data = [item for item in data if item["instance_id"] in valid_ids]
        print(f"Querying {len(data)} instances")
        prompt_list = [item["prompt"] for item in data]
        ids = [item["instance_id"] for item in data]
        output_dict = query_vllm_batch(
            prompt_list,
            ids,
            model,
            sampling_params
        )
        output_list.extend(process_output(output_dict, args.model_name, test_file_map))
        valid_ids = valid_ids - set([item["instance_id"] for item in output_list])
        if len(valid_ids) == 0:
            break
    
    swe_bench_data_split = "verified" if "verified" in args.dataset else "lite"
    output_filename = os.path.join(args.output_dir, f"{swe_bench_data_split}_run{args.run_number}.jsonl")

    with open(output_filename, "w") as f:
        for output in output_list:
            f.write(json.dumps(output) + "\n")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default="Nutanix/swe_bench_verified_swe_rl_no_cot_format")
    parser.add_argument("--dataset_split", type=str, default="train")
    parser.add_argument("--model_name", type=str, required=True)
    parser.add_argument("--lora_request", type=str, default=None)
    parser.add_argument("--run_number", type=int, required=True)
    parser.add_argument("--num_gpus", type=int, default=4)
    parser.add_argument("--max_output_length", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--n", type=int, default=1)
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    args.output_dir = os.path.join(args.output_dir, args.model_name.replace('/', '__'))
    os.makedirs(args.output_dir, exist_ok=True)
    
    main(args)
