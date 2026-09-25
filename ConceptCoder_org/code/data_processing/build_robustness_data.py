import os
import re
import json

import sys
import random
import pandas as pd
from pathlib import Path

from tree_sitter_languages import get_parser


# Check if exactly two arguments are provided (excluding the script name)
if len(sys.argv) != 3:
    print("Usage: python main.py <train_data_path> <test_data_path>")
    sys.exit(1)

train_file = sys.argv[1]
test_file = sys.argv[2]

if not Path(train_file).exists():
    print("Invalid train path file path. File or directory does not exist.")   
    sys.exit(1) 
if not Path(test_file).exists():
    print("Invalid test path file path. File or directory does not exist.")   
    sys.exit(1) 


file_path = Path(test_file)
parent_dir = file_path.parent
print(parent_dir)

# sys.exit(1)

language="cpp"
parser = get_parser(language)

def read_jsonl(path):
    f = open(path, "r")
    data = [json.loads(ex) for ex in f]
    f.close()
    return data


def bfs(code_str, parser):
    code_b = code_str
    lines = code_str.split("\n")
    if isinstance(code_b, str):
        code_b = code_b.encode()
    root = parser.parse(code_b).root_node
    
    q = [root]
    variable_names, function_names = [], []
    while len(q) > 0:
        n = q.pop()
        # print(n.start_point)
        # print(n.type, n.tex?t.decode())
        # print(n.type, n.text.decode())
        # for child in n.children:
        #     print("-------", child.type, child.text.decode())
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue

        if len(n.children) == 0:
            if n.type == "identifier":
                variable_names.append(n.text.decode())
                # print(n.type, n.text.decode())
            continue
        if n.type in ("call_expression", "function_declarator") :
            function_names.append(n.children[0].text.decode())
            
        q.extend(reversed(list(n.children)))
    function_names = set(function_names)
    variable_names = set(variable_names) - function_names
    
    return variable_names, function_names


vul_var_freq, vul_api_freq = {}, {}
nvul_var_freq, nvul_api_freq = {}, {}
for split in ("train", ):
    data = read_jsonl(train_file)
    # print(len(data))
    for ex in data:
        # print(ex['idx'])
        # print(ex['func'])
        variable_names, function_names = bfs(ex['func'], parser)
        if ex['target'] == 1:
            for nm in variable_names:
                vul_var_freq[nm] = vul_var_freq.get(nm, 0) + 1
            for api in function_names:
                vul_api_freq[api] = vul_api_freq.get(api, 0) + 1

        else:
            for nm in variable_names:
                nvul_var_freq[nm] = nvul_var_freq.get(nm, 0) + 1
            for api in function_names:
                nvul_api_freq[api] = nvul_api_freq.get(api, 0) + 1
        # print("Vars: ", variable_names)
        # print("Calls: ", function_names)

common_names = set(vul_var_freq.keys()) & set(nvul_var_freq.keys())
common_names = set(vul_var_freq.keys()) & set(nvul_var_freq.keys())
vul_var_freq = [(vul_var_freq[var], var) for var in vul_var_freq if var not in common_names]
nvul_var_freq = [(nvul_var_freq[var], var) for var in nvul_var_freq if var not in common_names]
vul_var_freq = sorted(vul_var_freq, key=lambda x: -x[0])
nvul_var_freq = sorted(nvul_var_freq, key=lambda x: -x[0])

common_apis = set(vul_api_freq.keys()) & set(nvul_api_freq.keys())
vul_api_freq = [(vul_api_freq[api], api) for api in vul_api_freq if api not in common_apis]
nvul_api_freq = [(nvul_api_freq[api], api) for api in nvul_api_freq if api not in common_apis]
vul_api_freq = sorted(vul_api_freq, key=lambda x: -x[0])
nvul_api_freq = sorted(nvul_api_freq, key=lambda x: -x[0])

names = {
    0: [nm for _, nm in vul_var_freq],
    1: [nm for _, nm in nvul_var_freq]
}
apis = {
    0: [api for _, api in vul_api_freq],
    1: [api for _, api in nvul_api_freq]
}

starters = [
    'while (_i_0 > _i_0){ ',
    'while (_i_1 > _i_1){ ',
    'while (_i_2 > _i_2){ ',
    'while (_i_3 > _i_3){ ',
    'while (_i_4 > _i_4){ ',
    'while (_i_5 > _i_5){ ',
    'while (_i_6 > _i_6){ ',
    'while (_i_7 > _i_7){ ',
    'while (_i_8 > _i_8){ ',
    'while (_i_9 > _i_9){ ',
    'if (_i_0 > _i_0){', 
    'if (_i_1 > _i_1){', 
    'if ( _i_2 > _i_2){',
    'if (_i_3 > _i_3){',
    'if ( _i_4 > _i_4 ) { ',
    'if ( _i_5 > _i_5 ) { ',
    'if ( _i_6 > _i_6 ) { ',
    'if ( _i_7 > _i_7 ) { ', 
    'if ( _i_9 > _i_9 ) { ',
    'while (false) { ',
    'for ( ; false ; ) { ',
    'if (false){'
]

def update(code_str, parser, names=[], apis=[]):
    code_b = code_str
    lines = code_str.split("\n")
    if isinstance(code_b, str):
        code_b = code_b.encode()
    root = parser.parse(code_b).root_node
    
    variable_names, func_names = bfs(code_str, parser)
    
    # print(variable_names)
    # variable_names = variable_names - func_names
    sz = len(variable_names)
    converted_name = {}
    if sz != 0:
        changed_names = names[:sz]
        for cur, nex in zip(variable_names, changed_names):
            converted_name[cur] = nex
            
    q = [root]
    change_ranges = []
    dead_block_places = []
    while len(q) > 0:
        n = q.pop()
        # print(n.start_point)
        # print(n.type, n.text.decode())
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue

        if len(n.children) == 0:
            if n.type == "identifier" and n.text.decode() not in func_names:
                change_ranges.append((n.start_byte, n.end_byte, converted_name[n.text.decode()]))
                # variable_names.append(n.text.decode())
                # print(n.type, n.text.decode())
            continue
        if n.type == "compound_statement":
            for child in n.children:
                if child.type == "}":
                    continue
                dead_block_places.append(child.end_byte)
        q.extend(reversed(list(n.children)))
    
    change_ranges = sorted(change_ranges)
    dead_block_places = list(set(dead_block_places))
    dead_block_places = random.sample(dead_block_places, min(len(dead_block_places), 10))
    dead_block_places = {x: 1 for x in dead_block_places}
    ptr, ptr1 = 0, 0
    func = ""
    # print(code_b)
    cnt = 0
    code_str = code_b.decode()
    while ptr < len(code_b):
        if ptr1 < len(change_ranges) and ptr == change_ranges[ptr1][0]:
            func += change_ranges[ptr1][2]
            ptr = change_ranges[ptr1][1]
            ptr1 += 1
        elif ptr in dead_block_places and dead_block_places[ptr] == 1:
            dead_block_places[ptr] = 0
            func += "\n    "+ random.choice(starters)  + apis[cnt] + "(); }\n"
            cnt+=1
        else:
            func += chr(code_b[ptr])
            ptr += 1
    return func


data = read_jsonl(test_file)
cnt = 0
for ex in data:
    names_ = names[ex['target']]
    apis_ = apis[ex['target']]
    # print(ex['func'])
    func = update(ex['func'], parser, names_, apis_)
    ex["func"] = func

with open(f"{parent_dir}/test_robustness.jsonl", "w") as f:
    f.write("\n".join([json.dumps(ex) for ex in data]))