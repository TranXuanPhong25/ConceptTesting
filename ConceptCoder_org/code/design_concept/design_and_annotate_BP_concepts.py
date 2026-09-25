import re
import os
import glob
import json
import copy
import random
import argparse
import itertools

from typing import List, Dict
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from collections import defaultdict
from tree_sitter_languages import get_parser
from tree_climber.ast_creator import AstErrorException

from tree_climber.tree_sitter_utils import c_parser, cpp_parser
from tree_climber.ast_creator import ASTCreator
from tree_climber.cfg_creator import CFGCreator

from utils_BP import *

language="c"
parser = get_parser(language)

def read_file(path):
    with open(path, "r") as f:
        data = f.read()
    return data
def read_jsonl(path):
    with open(path, "r") as f:
        data = [json.loads(ex) for ex in f]
    return data

project_codenet_data_path="../../../TRACED_ICSE_24/tracer/Project_CodeNet/data"
result_path="../../../TRACED_ICSE_24/tracer/results"


def read_xml_condition(xml_file, schema='tree', considered_lines =[], concepts = None, adj=None):
    with open(xml_file) as f:
        tree = ET.parse(f)
    root = tree.getroot()
    root.attrib["schema"] = schema
    states = {}
    states_after_line = {}
    before_states = {}
    next_sibling = {}
    for i, child in enumerate(root):
        if i > 0:
            next_sibling[i-1] = child
        next_sibling[i] = None
    for i, child in enumerate(root):
        # print(child)
        assert child.tag == "line", f"'{child.tag}' should be 'line'"
        # print(child.attrib)
        
        lineno = int(child.attrib["line"])
        # print(lineno)
        # new_or_modified = False
        before_states = copy.deepcopy(states)
        for variable in child:
            # print(variable.attrib)
            # print(dir(variable))
            # if variable.attrib["age"] in ("new", "modified"):
            #     new_or_modified = True
                # print(variable.attrib["name"], variable.attrib["age"], variable.text)
            states[variable.attrib["name"]] = variable.text
        
        # if lineno in considered_lines and new_or_modified:
        #     states_after_line[lineno] = [before_states, copy.deepcopy(states)]
        if lineno in considered_lines:
            sib = next_sibling[i]
            if sib != None:
                # print(lineno, int(sib.attrib["line"]))
                next_line =  int(sib.attrib["line"])
                # print(lineno, adj)
                adja_ = adj[lineno]
                output = None
                if adja_['True'] == next_line:
                    output = True
                elif adja_['False'] == next_line:
                    output = False
                
                if "states" not in concepts[lineno]:
                    concepts[lineno]['states'] = []
                concepts[lineno]['states'].append({"output": output})
                variables = states
                state_vars = set(variables.keys())
                concept_vars = set(concepts[lineno]['variables'])
                # print(variables.keys())
                # print(concepts[lineno]['variables'])
                considered_vars = state_vars & concept_vars
                concepts[lineno]['states'][-1]['variables_state'] = {}
                for var in considered_vars:
                    if var in before_states:
                        concepts[lineno]['states'][-1]['variables_state'][var] = states[var]
                # assert len(state_vars & concept_vars) == len(concept_vars)
                # print(len(considered_vars))
                
                # if output == None:
                #     print(concepts[lineno], output)
        for lineno in concepts:
            if "states" in concepts[lineno]:
                concepts[lineno]['states'] = random.sample(concepts[lineno]['states'], min(len(concepts[lineno]['states']), 2))
    return states_after_line


def bfs_condition(code_str):
    lines = code_str.split("\n")
    if isinstance(code_str, str):
        code_str = code_str.encode()
    root = parser.parse(code_str).root_node
    
    q = [root]
    concepts = {}
    while len(q) > 0:
        n = q.pop()
        
        if n.type in ("for_statement", "while_statement", "if_statement", "do_statement"):
            condition = n.child_by_field_name("condition")
            if condition:
                line_no = condition.start_point[0] + 1
                concepts[line_no] = condition.text.decode()
                identifiers = set()
                extract_identifiers(condition, identifiers)
                concepts[line_no] = {
                    "condition_type": n.type,
                    "code": condition.text.decode(),
                    "variables": identifiers,
                }
                # print(condition.text.decode()
        q.extend(reversed(list(n.children)))
    return concepts

def read_xml_quantized(xml_file, schema='tree', considered_lines =None, concepts=None):
    with open(xml_file) as f:
        tree = ET.parse(f)
    root = tree.getroot()
    root.attrib["schema"] = schema
    
    data_types = set()
    line_to_value = {}
    var_states = {}
    states, before_states = {}, {}
    for child in root:
        # print(child)
        assert child.tag == "line", f"'{child.tag}' should be 'line'"
        # print(child.attrib)
        lineno = int(child.attrib["line"])
        # print(lineno)
        before_states = copy.deepcopy(states)

        # changed_variables = 
        for variable in child:
            states[variable.attrib["name"]] = variable.text
            data_type, value_type, quantized_value =  quantized_variable(variable, var_states)
            var_name = variable.attrib['name']
            var_states[var_name] = [data_type, value_type, quantized_value]
            
        # print(lineno, var_states)
        # print(lineno, considered_lines, lineno in considered_lines)
        # if lineno in considered_lines and len(states):
        if lineno in considered_lines:
            if "states" not in concepts[lineno]:
                concepts[lineno]['states'] = []
            # print(concepts[lineno])
            # if concepts[lineno]['modified_variable'] not in var_states:
            #     print(child)
            #     for variable in child:
            #         print(variable)
            #     print(var_states)
            #     print(concepts[lineno]['modified_variable'])
            #     print(states)
            # print(lineno,states, concepts[lineno])
            concepts[lineno]['states'].append({"output": var_states[concepts[lineno]['modified_variable']]})
            variables = states
            state_vars = set(variables.keys())
            concept_vars = set(concepts[lineno]['variables'])
            # print(variables.keys())
            # print(concepts[lineno]['variables'])
            considered_vars = state_vars & concept_vars
            concepts[lineno]['states'][-1]['variables_state'] = {}
            for var in considered_vars:
                if var in before_states:
                    concepts[lineno]['states'][-1]['variables_state'][var] = states[var]
    for lineno in concepts:
        if "states" in concepts[lineno]:
            concepts[lineno]['states'] = random.sample(concepts[lineno]['states'], min(len(concepts[lineno]['states']), 2))
    return concepts

def bfs_quantized(code_str):
    src = code_str
    lines = code_str.split("\n")
    if isinstance(code_str, str):
        code_str = code_str.encode()
    # print(code_str)
    root = parser.parse(code_str).root_node
    
    q = [root]
    concepts = {}
    while len(q) > 0:
        n = q.pop()
        # print(dir(n))
        # if any("call" in ch.type for ch in n.children):
        #         print(n.text.decode())
        if "expression_statement" in n.type and any("assignment" in ch.type for ch in n.children):
            # print(n.type, n.text.decode())
            # if is_call(n):
            #     print("found ")
            line_no = n.start_point[0] + 1
            identifiers = set()
            extract_identifiers(n, identifiers)
            left_var = extract_left_identifier(n)
            # print(left_var)

            concepts[line_no] = {
                "code": n.text.decode(),
                "variables": list(identifiers),
                "modified_variable": left_var,
            }
        q.extend(reversed(list(n.children)))
    # print(concepts)
    return concepts


labels_map = {
    False: 0,
    True: 1,
    'ALPHA': 2,
     'INITIALIZED': 3,
     'NEGATIVE-REG': 4,
     'NEGATIVE-VL': 5,
     'NOT_ALPHA': 6,
     'NOT_INITIALIZED': 7,
     'NOT_NULL': 8,
     'NULL': 9,
     'POSITIVE-REG': 10,
     'POSITIVE-VL': 11,
     'UNKNOWN': 12,
     'ZERO': 13,
}


full_data = read_jsonl(f"{result_path}/sequences/sequences_langC_from0_to4052_limitNone_full.jsonl")

cnt = 0
er = 0
condition = {}
for ex in full_data:
    # print(ex)
    try:
        src = read_file(f"{project_codenet_data_path}/{ex['filepath']}")

        cnt += 1
        concepts = bfs_condition(src)
        # print(concepts)
        # print(ex["src"])
        branch, dest = get_parsed_info(ex['src'], ex['lang'])

        adj = {}
        for bra, dst in zip(branch, dest):
            if len(dst) != 2 or  "True" not in dst or "False" not in dst:
                dst
                continue
            if bra == dst['True'] or bra == dst['False']:
                continue

            # # print(bra, dst)
            # print(bra)
            if bra == None:
                continue
            bra_no = int(bra[1:])
            # print()
            tr_no = int(dst['True'][1:]) if dst['True'] != None else None
            fal_no = int(dst['False'][1:]) if dst['False'] != None else None
            adj[bra_no] = {
                "True": tr_no,
                "False": fal_no
            }

        # print(concepts.keys())
        concept_lines = set(concepts.keys())
        # print(concept_lines)
        branch_lines = set([x for x in adj])
        # print(branch_lines)

        common_lines = concept_lines & branch_lines
        # print(common_lines)
        # print(adj)
        path_ = ex['filepath'].split(".")[0]
        read_xml_condition(f"{result_path}/tree/{path_}/{ex['input_no']}.txt_log.xml", considered_lines=common_lines, concepts=concepts, adj=adj)
        for con in concepts:
            # print(con)
            concepts[con]['variables']= list(concepts[con]['variables'])

        condition[ex["idx"]] = concepts
    except  AstErrorException as e:
        er += 1
    except Exception as e:
        er += 1
        print(str(e))
    # print(ex['idx'], ex['filepath'], ex['input_no'])
    # print(concepts)
    if cnt == 1000:
        break


cnt = 0
assignment = {}
cnt_ = 0
states_found = 0
err_ = 0
for ex in full_data:
    # if ex['idx'] != 705 :
    #     continue
    cnt += 1
    # if cnt_ <= 13000:
    #     continue
    try:
            # print(ex['idx'])
        src = read_file(f"{project_codenet_data_path}/{ex['filepath']}")
        # print(src)
        lines = src.splitlines(keepends=True)
        concepts = bfs_quantized(src)
        # print(concepts)


        path_ = ex['filepath'].split(".")[0]
        concept_lines = set(concepts.keys())
        # print(concept_lines)
        # print(path_)
        states = read_xml_quantized(f"{result_path}/tree/{path_}/{ex['input_no']}.txt_log.xml", considered_lines=concept_lines, concepts=concepts)
        # print("After States: ", states)

        # print(states)
        # print(states)
        assignment[ex["idx"]] = states
        
        flag = 0
        for line in states:
            if "states" in states[line] and len(states[line]['states']) > 0:
                flag = 1
        states_found += flag
        # cnt += 1
        if cnt % 1000 == 0:
            print("Done with ", cnt, "states found", states_found)
        if cnt == 1000:
            break
    except Exception as E:
        # print(str(E), ex['idx'])
        # pass
        # print(ex['idx'], str(E))
        err_ += 1


branch_data = read_jsonl(f"{result_path}/sequences/sequences_BRANCH.jsonl")

final_data = []
for ex in branch_data:
    try:
        # cond = condition.get(ex["idx"], {})
        # assin = assignment.get(ex["idx"], {})
        cond = condition[ex["idx"]]
        assign = assignment[ex["idx"]]
        refined_cond = {}
        for line in cond:
            lineno = int(line)
            if "states" not in cond[line]:
                continue
            for state in cond[line]['states']:
                if state['output'] != None:
                    state['output'] = labels_map[state['output']]
                    # print("here")
            refined_cond[lineno] = cond[line]
        refined_assign = {}
        for line in assign:
            lineno = int(line)
            if "states" not in assign[line]:
                continue
            for state in assign[line]['states']:
                # print(state["output"])
            #     print(state)
                if state['output'] != None:
                    state['output'] = labels_map[state['output'][-1]]
            refined_assign[lineno] = assign[line]
        # print(cond, refined_cond)
        ex1 = {
            'idx': ex['idx'],
            'src_lines': ex['src_lines'],
            'src_linenos': ex['src_linenos'],
            'covered_in_trace': ex['covered_in_trace'],
            'filepath': ex['filepath'],
            'input': ex['input'],
            'condition': refined_cond,
            'quantized': refined_assign,
        }
        final_data.append(ex1)
    except Exception as e:
        # print(str(e))
        pass

print(len(final_data))
for ex in final_data:
    lines = {}
    for line in ex["condition"]:
        if line not in lines:
            lines[line] = []
        lines[line].append(ex["condition"][line])
    for line in ex["quantized"]:
        if line not in lines:
            lines[line] = []
        lines[line].append(ex["quantized"][line])
    # print(len(lines))
    # print(ex["src_lines"], ex['src_linenos'])
    # print(lines)
    # print(lines)
    ex["lines_concept"]= []
    for lineno, line,  coverage in zip(ex["src_linenos"], ex["src_lines"], ex["covered_in_trace"]):
        concept = [0] * 14
        for con in lines.get(int(lineno[1:]), []):
            # print(con)
            # print(len(con['states']))
            for state in con["states"]:
                if state['output'] == None:
                    continue
                concept[state['output']] = 1
        ex["lines_concept"].append(concept)

with open(f"{result_path}/sequences/sequences_BRANCH_with_concept_ground_truth.jsonl", "w") as f:
    f.write("\n".join([json.dumps(ex) for ex in final_data]))