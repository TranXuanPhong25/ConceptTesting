import os
import re
import json
import random
import pandas as pd

from tree_sitter_languages import get_parser

from utils_VD import *

language="cpp"
parser = get_parser(language)


final_set = set()
def bfs(code_str, parser):
    code_b = code_str
    lines = code_str.split("\n")
    if isinstance(code_b, str):
        code_b = code_b.encode()
    root = parser.parse(code_b).root_node

    ptrs, function_paramt = get_pointers(root, code_b)
    indices = get_indices(root, code_str)
    # print(indices)
    code_properties = {
        "null_assignment": [],
        "null_check": [],
        "ptr_deref":[],
        "buffer_allocation": [],
        "buffer_access": [],
        "bound_check": [],
        "free": [],
        "if_statement": []
    }
    # print(ptrs, function_paramt)

    # print("Pointers: ", ptrs)
    q = [root]
    while len(q) > 0:
        n = q.pop()
        # print(n.start_point)
        # print(n.type, n.text.decode())
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue
        
        if n.type == "if_statement":
            # print(n.text.decode())
            # print(n.children[0].text.decode(), n.children[1].text.decode())
            # for i, child in enumerate(n.children):
            #     if i >= 2:
            #         break
            code_properties["if_statement"].append({
                "lines": [li for li in range(n.children[0].start_point[0], n.children[1].end_point[0]+1)],
                "start_index": n.children[0].start_byte,
                "end_index": n.children[1].end_byte,
            })
            # for child in n.children:
            #     print(child.text.decode())
        # Buffer overflow
        if n.type == "call_expression" and "alloc" in n.children[0].text.decode():
            code_properties["buffer_allocation"].append({
                "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                # "ptr": "",
                "start_index": n.start_byte,
                "end_index": n.end_byte,
            })
            # print(code_str[n.start_byte:n.end_byte])

        if n.type == "array_declarator":
            code_properties["buffer_allocation"].append({
                "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                # "ptr": "",
                "start_index": n.start_byte,
                "end_index": n.end_byte,
            })
            # print(code_str[n.start_byte:n.end_byte])
       
        if n.type == "call_expression" and n.children[0].text.decode() in (
            "strlen", "strcat", "strcpy", "strncpy", "strncat", "sprintf", 
            "snprintf", "fputs", "fread", "fwrite", "memcpy", "memset", "memcmp", "gets"):
            code_properties["buffer_access"].append({
                "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                # "ptr": "",
                "start_index": n.start_byte,
                "end_index": n.end_byte,
            })
            # print(code_str[n.start_byte:n.end_byte])
        
        if n.type in ("subscript_expression"):
            code_properties["buffer_access"].append({
                "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                # "ptr": "",
                "start_index": n.start_byte,
                "end_index": n.end_byte,
            })
            # print(code_str[n.start_byte:n.end_byte])
        
        if n.type in ("binary_expression") and n.children[1].type in (">", "<", ">=", "<="):
            left = n.children[0].text.decode()
            right = n.children[2].text.decode()
            if left in indices or right in indices:
                code_properties["bound_check"].append({
                    "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                    # "ptr": "",
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(code_str[n.start_byte:n.end_byte], n.parent.text.decode())

            if any([x in left for x in ("len", "size")]) or any([x in right for x in ("len", "size")]):
                code_properties["bound_check"].append({
                    "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                    # "ptr": "",
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(code_str[n.start_byte:n.end_byte],  n.parent.text.decode())

        if n.type == "call_expression" and "free" in n.children[0].text.decode():
            arguments = n.children_by_field_name("arguments")
            code_properties["free"].append({
                "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                "ptr": [x.text.decode() for x in arguments[0].children[1:-1] if x.type not in (",")],
                "start_index": n.start_byte,
                "end_index": n.end_byte,
            })
            # print(code_str[n.start_byte:n.end_byte])
        def is_null(nod):
            if nod.type in ("null", "nullptr"):
                return True
            if nod.type == "identifier" and "null" in nod.text.decode():
                return True
            return False

        # Profile pointer assignment
        if n.type == "assignment_expression":
            # if n.children[0].text.decode() in ptrs:
                # print('\n'.join(lines[n.start_point[0]:n.end_point[0]+1]), n.children[0].text.decode())
            # if n.children[2].type == "nullptr":
            #     print(n.text.decode())
            # if "null" in n.children[2].text.decode().lower():
            # print(len(n.children))
            # if len(n.children) == 2: 
            #     print(n.text.decode())
            if len(n.children) == 3 and is_null(n.children[2]):
                code_properties["null_assignment"].append({
                    "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                    "ptr": [n.children[0].text.decode()],
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(n.children[2].type)
                # print(code_str[n.start_byte:n.end_byte])
                # print(n.parent.text.decode(),n.children[0].text.decode())


        if n.type == "init_declarator" and n.children[0].type == "pointer_declarator":
            # code_properties["assignment"].append({
            #     "lines": n.parent.text.decode(),
            #     "ptr": n.children[0].children[1].text.decode(),
            # })
            # if "null" in n.children[2].text.decode().lower():
            # if len(n.children) == 2: 
            #     print(n.text.decode())
            if len(n.children) == 3 and is_null(n.children[2]):
                # print(n.children[0].text.decode(), n.children[0].children[1].text.decode())
                code_properties["null_assignment"].append({
                    "lines": [li for li in range(n.parent.start_point[0], n.parent.end_point[0]+1)],
                    "ptr": [n.children[0].children[1].text.decode()],
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(code_str[n.start_byte:n.end_byte])
        q.extend(reversed(list(n.children)))
    
    # ptrs = []
    for ex in code_properties['null_assignment'] + code_properties['free']:
        ptrs.extend(ex['ptr'])
    ptrs.extend(function_paramt)
    ptrs = list(set(ptrs)) 
    # print(function_paramt)
    # print(ptrs, )
    q = [root]
    while len(q) > 0:
        n = q.pop()
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue

        if n.type == "condition_clause":
            # print(n.text.decode())
            if is_null_check(n, ptrs):
                temp = n
                while temp:
                    if temp.type in ("if_statement", "while_statement", "switch_statement", "for_statement"):
                        break
                    temp = temp.parent
    
                if temp:
                    code_properties["null_check"].append({
                        "lines": [li for li in range(temp.children[0].start_point[0], temp.children[1].end_point[0]+1)],
                        "ptr": get_ptrs_from_null_check(n, ptrs),
                        "start_index": temp.children[0].start_byte,
                        "end_index": temp.children[1].end_byte,
                    })
                    # print(code_str[temp.children[0].start_byte:temp.children[1].end_byte])
        q.extend(reversed(list(n.children)))
    
    
    # print(code_properties['null_check'])
    # ptrs = []
    for ex in code_properties['null_assignment'] + code_properties['free']:
        ptrs.extend(ex['ptr'])
    for ex in code_properties["null_check"]:
        ptrs.extend(ex['ptr'])
    ptrs.extend(function_paramt)
    # print()
    ptrs = list(set(ptrs)) 
    q = [root]
    while len(q) > 0:
        n = q.pop()
        # print(n.start_point)
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue
        
        if n.type == "field_expression" and n.children[1].type in ("->"):
            # print('\n'.join(lines[n.start_point[0]:n.end_point[0]+1]), n.children[0].text.decode())
            if n.children[0].text.decode() in ptrs:
                # print(n.children[0].text.decode(), n.text.decode())
                # print(code_str[n.start_byte:n.end_byte])
                code_properties["ptr_deref"].append({
                    "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                    "ptr": [n.children[0].text.decode()],
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(code_str[n.start_byte:n.end_byte])


        if n.type in ("subscript_expression"):
            if n.children[0].text.decode() in ptrs:
                # print(code_str[n.start_byte:n.end_byte])
                # print(n.children[0].text.decode(), n.text.decode())
                code_properties["ptr_deref"].append({
                    "lines": [li for li in range(n.start_point[0], n.end_point[0]+1)],
                    "ptr": [n.children[0].text.decode()],
                    "start_index": n.start_byte,
                    "end_index": n.end_byte,
                })
                # print(code_str[n.start_byte:n.end_byte])
        q.extend(reversed(list(n.children)))

    return code_properties


def read_jsonl(path):
    f = open(path, "r")
    data = [json.loads(ex) for ex in f]
    f.close()
    return data

props = ["null_assignment", "null_check", "ptr_deref", "buffer_allocation", "buffer_access", "bound_check", "free", "if_statement"]

import sys
from pathlib import Path

def main():
    # Validate the number of arguments
    if len(sys.argv) != 3:
        print("Usage: python validate_paths.py <source_file> <destination_directory>")
        sys.exit(1)

    # Parse arguments
    source_file = Path(sys.argv[1])
    dest_file = Path(sys.argv[2])


    # Validate source file
    if not source_file.exists():
        print(f"Error: Source file '{source_file}' does not exist or is not a file.")
        sys.exit(1)




    data = read_jsonl(source_file)
    processed_data = []
    cnt = 0
    for ex in data:
        props_ = bfs(ex['func'], parser)
        # print(props)
        # print("-------------------------------------")
        # print(ex["func"])
        lines = ex['func'].split("\n")
        # print(len(lines))
        lines_concept = {i: [0] * len(props) for i in range(len(lines))}
        for i, prop in enumerate(props):
            # print(prop)
            for x in props_[prop]:
                # print(x["lines"], x["lines"][0], len)
                # stats = "\n".join([lines[li] for li in x["lines"]])
                # print("****** ", stats)
                for li in x["lines"]:
                    lines_concept[li][i] = 1
        combined_concepts = [0] * len(lines_concept[0])
        for i, li in enumerate(ex["func"].split("\n")):
            # print(li, lines_concept[i])
            for j in range(len(lines_concept[i])):
                combined_concepts[j]= max(combined_concepts[j], lines_concept[i][j])

        cnt += 1
        new_ex = ex.copy()
        del new_ex["token_concepts"]
        new_ex["concepts"] = combined_concepts
        new_ex["lines_concept"] = lines_concept
        processed_data.append(new_ex)
        # print(new_ex.keys())
    #     if cnt == 10:
    #         break
    f = open(dest_file, "w")
    f.write("\n".join(json.dumps(ex) for ex in processed_data))
    f.close()

if __name__ == "__main__":
    main()


