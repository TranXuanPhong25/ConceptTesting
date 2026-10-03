import openai
import copy
import re
import logging
from validate import validate_status_process, ExecutionStatus
import os
import shutil
import time

import json
import random

def request_openai_api(messages, max_retries = 20, temperature = 0, model = "GPT-3.5"):
    with open('../config.json', 'r') as file:
        data = json.load(file)
    api_keys = data['api_keys']
    api_base = data['api_base']

    if model == "GPT-3.5":
        model = "gpt-3.5-turbo-1106"
    elif model == "GPT-4":
        model = "gpt-4-0125-preview"
    else:
        print("Invalid Model")

    start_time = time.time()

    # for key in api_keys:
    attempts = 0
    while attempts < max_retries:
        key = random.choice(api_keys)
        print("key:", key)
        try:
            completion = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                api_key=key,
                request_timeout=20
            )
            break
        except Exception as e:
            attempts += 1
            print(e)

            if "deactivated" in str(e):
              data['api_keys'].remove(key)
              with open('../config.json', 'w') as json_file:
                json.dump(data, json_file)

            
            if attempts == max_retries:
                time.sleep(60)
                attempts = 0

    end_time = time.time()
    request_time = end_time - start_time
    print("---- request time cost:", request_time)

    if not completion:
        return None

    output = completion['choices'][0]['message']['content'].strip()
    return output
  




def reask(dialog, extract_res, MAX_TRY):
    SUCCESS = 0
    try_cnt = 0
    while try_cnt < MAX_TRY:
        # print("\ntry_cnt:", try_cnt)
        # print(dialog)
        raw_llm = request_openai_api(dialog, 20)
        # print("raw_llm:", raw_llm)
        res, valid = extract_res(raw_llm) 
        # print("res:", res)
        # print("valid:", valid)

        if valid:
            SUCCESS = 1
            break
        else:
            dialog.append(
                {"role": "assistant", "content": raw_llm}
            )
            dialog.append(
                {"role": "user", "content": res + " Please generate again."}
            )

        try_cnt += 1
    
    if SUCCESS:
        return res
    else:
        print("---- Can not finish this task. Here are the unsloved problem:", res)
        return None




library_need_to_be_installed = []
debug_cnt = {
    "successful": 0,
    "failed": 0
}



def extract_res_for_code_gen(text):
    res = None
    valid = False

    count = 0
    modified_text = ""
    lines = text.split("\n")
    starts = []
    ends = []
    line_cnt = 0
    for line in lines:
        if line.startswith("```"):
            if count % 2 == 0:
                starts.append(line_cnt)
            else:
                ends.append(line_cnt)
            count += 1
        else:
            modified_text += line + "\n"
        
        line_cnt += 1
    
    if len(starts) == 0 and len(ends) == 0:
        msg = "There is no code block in the input text. Please use Markdown syntax to represent code blocks. Please ensure that there is only one code block."

        res = msg
        valid = False
    elif len(starts) != len(ends):
        msg = "The code blocks in the input text are not conforming to the Markdown syntax."
        
        res = msg
        valid = False
    elif len(starts) > 1:
        msg = "There are several code blocks in the input text. Please ensure that there is only one code block."
        
        res = msg
        valid = False

    if res:
        # did not generate the code block
        return res, valid
    
    res = "\n".join(lines[starts[0]+1:ends[0]])

    valid = True
    return res, valid



def extract_error_info(error_output):
    global library_need_to_be_installed

    # Extract additional error information, e.g., error line and error function
    # This is a basic example, and you might need to customize it based on your specific error format
    lines = error_output.split('\n')
    last_error_item = None
    error_function = None
    msg = None
    for cnt in range(len(lines)):
        
        line = lines[cnt]
        if "/tmp/tmp" in line.lower():
            # print("Error Line:", line.strip())
            # print("Error Function:", lines[cnt + 1].strip())
            error_function = lines[cnt + 1].strip()

        if 'error' in line.lower():
            last_error_item = line
    # print('Error info:', error_function)

    if error_function:
        msg = "Error Function: " + error_function + "\n"
    if last_error_item:
        msg += "Error Information: " + last_error_item.strip()

        if "ModuleNotFoundError" in last_error_item.strip():
            library_need_to_be_installed.append(last_error_item.strip())

    return msg

def gen_code_debug(dialog, MAX_TRY):
    SUCCESS = 0
    try_cnt = 0
    while try_cnt < MAX_TRY:
        raw_llm = request_openai_api(dialog, 20)
        code, msg = extract_res_for_code_gen(raw_llm) 

        if code:
            SUCCESS = 1
            break
        else:
            dialog.append(
                {"role": "assistant", "content": raw_llm}
            )
            dialog.append(
                {"role": "user", "content": msg + " Please generate again."}
            )
            print(msg)

        try_cnt += 1
    
    if SUCCESS:
        return code, raw_llm
    else:
        print("Can not finish this task.")
        return None
    
def display_code(codes):
    codes = codes.split('\n')
    print("++++++++++ code start ++++++++++")
    for line in codes:
        print("+ ", line)
    print("---------- code end ----------")

def self_debug(code, MAX_TRY):
    global debug_cnt

    origin_code = code
    print("---- original code:")
    display_code(origin_code)

    user_debug_init = "Fix the bug in the following code, described as '<BUG_DES>'.\n```python\n<CODE>\n```\n\nPlease use Markdown syntax to represent code blocks."
    user_debug = "The repaired code still has the following errors:'<BUG_DES>'"

    debug_template = [
        {"role": "system", "content": "You are an advanced Language Model assistant that can evaluate, execute, and debug code. Please use Markdown syntax to represent code blocks."},
    ]
    debug = copy.deepcopy(debug_template)

    
    # print("=== start ===")
    '''
        You can generate programs and execute them
    '''



    SUCCESS = 0
    try_cnt = 0
    while try_cnt < MAX_TRY:
        if try_cnt != 0: # need to reask llm to fix the bug
            print("----- try_cnt:", try_cnt)
            # print(debug)
            # display(debug)
            code, raw_llm = gen_code_debug(debug, MAX_TRY)
            print("----- repaired code:")
            display_code(code)
        
        if not code:
            break

        status, msg = validate_status_process(code)
        valid = status == ExecutionStatus.SUCCESS

        

        if valid:
            SUCCESS = 1
            break
        else:
            msg_tmp = extract_error_info(msg)
            if msg_tmp:
                msg = msg_tmp
            else:
                print("---- We can not extract the error info for this msg:")
                print(msg)
                break

            # msg = extract_error_info(msg)

            if try_cnt == 0:
                
                tmp = copy.deepcopy(user_debug_init)
                tmp = tmp.replace('<BUG_DES>', msg)
                tmp = tmp.replace('<CODE>', code)

                debug.append(
                    {"role": "user", "content": tmp}
                )
            else:
                debug.append(
                    {"role": "assistant", "content": raw_llm}
                )

                tmp = copy.deepcopy(user_debug)
                tmp = tmp.replace('<BUG_DES>', msg)
                debug.append(
                    {"role": "user", "content": tmp + " Please generate again."}
                )
            print("---- msg:", msg)
            if "ModuleNotFoundError" in msg:
                break

        try_cnt += 1
    
    if SUCCESS:
        print("---- SUCCESS")
        if try_cnt != 0:
            debug_cnt["successful"] += 1
            print("---- You have repaired the program successfully!!!")
            # print("\n=== debug start ===")
            # print("--> origin_code:")
            # print(origin_code)
            # print("\n--> current code:")
            # print(code)
            # print("=== debug end ===\n")
        return code
    else:
        debug_cnt["failed"] += 1
        print("---- Can not finish this task.")
        return None


prompt_template = """Write a program to generate input data and invoke <API_NAME> to process input data. Please use Markdown syntax to represent code blocks. Please ensure that there is only one code block.

Here are some information of this api:
```
<API_INFO>
```"""

prompt_template_without_info = """Write a program to generate input data and invoke <API_NAME> to process input data. Please use Markdown syntax to represent code blocks. Please ensure that there is only one code block."""


def gen_prompt(api_name, api_info):
  if api_info:
    prompt = prompt_template.replace("API_NAME", api_name)
    prompt = prompt.replace("<API_INFO>", api_info)
  else:
    prompt = prompt_template_without_info.replace("API_NAME", api_name)
  return prompt


def gen_program(api_name, api_info):
    prompt = gen_prompt(api_name, api_info)
    print("\n------- prompt start -------")
    print(prompt)
    print("------- prompt end -------\n")

    messages = [
        {"role": "system", "content": "You are an advanced Language Model assistant that can generate, execute, and evaluate code. Please use Markdown syntax to represent code blocks."},
        {"role": "user", "content": ""}
    ]
    messages[-1]["content"] = prompt

    code = reask(messages, extract_res_for_code_gen, 3)

    if not code:
      return None
    
    generated_code = self_debug(code, 3)

    return generated_code

if __name__ == "__main__":
  api_description_path = "../get_api_reference/api_description.json"
  res_name = "api_programs.json"

  tmp_path = "./tmp" # can not be changed
  if not os.path.exists(tmp_path):
    os.makedirs(tmp_path)

  
  if os.path.exists(api_description_path):
    print("api_description has been extracted")
    with open(api_description_path, 'r') as json_file:
        captured_infos = json.load(json_file)
  else:
    print("There is no api_description.json.")
    exit(0)

  if os.path.exists(res_name):
    with open(res_name, 'r') as json_file:
        api_programs = json.load(json_file)
  else:
    api_programs = {}

  for api_name, info in captured_infos.items():
    if api_name in api_programs.keys():
      print(api_name, "has been analyzed")
      continue

    print("\n\n==========", api_name, "==========")
    info = info.split('\n')
    info = '\n'.join(info[:10])

    print(info)

    code = gen_program(api_name, info)

    if code:
      api_programs[api_name] = code
    else:
      api_programs[api_name] = "none"
      print("Can not generate valid program for:", api_name)
    
    with open(res_name, 'w') as json_file:
      json.dump(api_programs, json_file)
      
  # the performance of debug
  print("successful debug:", debug_cnt["successful"])
  print("failed debug:", debug_cnt["failed"])