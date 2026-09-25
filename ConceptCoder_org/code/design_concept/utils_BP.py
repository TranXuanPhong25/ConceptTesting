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


def get_parsed_info(src, lang):
    if lang == "c":
        parser = c_parser
    elif lang == "cpp":
        parser = cpp_parser
    else:
        raise NotImplementedError(lang)
        
    tree = parser.parse(bytes(src, "utf-8"))
    ast = ASTCreator.make_ast(tree.root_node)
    cfg = CFGCreator.make_cfg(ast)
    
        # map nodes based on source code lines to annotated linenos "// LXXX"
    def get_lineno(line):
        """Parse line of code to get lineno comment (// LXXX)"""
        m = re.search(r"// (L[0-9]+)", line)
        if m:
            return m.group(1)
        return None

    src_lines = src.splitlines()

    def get_node_lineno(n):
        """Helper to get LXXX for a CFG node"""
        attr = cfg.nodes[n]
        # print(n)
        # print(attr)
        if "n" not in attr:
            return None  # no ast node - most often this means it's FUNC_EXIT or some other CFG node
        # print(attr["n"])
        # print(attr["n"].start_point[0])
        # print(get_lineno(src_lines[attr["n"].start_point[0]]))
        return get_lineno(src_lines[attr["n"].start_point[0]])

    # get destination nodes
    def get_dest_nodes(n):
        """Return dict of edge_attr -> destination node for a branch node n"""
        d = {}
        for m, m_attr in cfg.adj[n].items():
            label = ",".join(sorted([v["label"] for v in m_attr.values()]))
            d[label] = m
        return d
    # get branch nodes
    branch_nodes = []
    for n in cfg.nodes():
        if len(cfg.adj[n]) > 1:
            branch_nodes.append(n)
    
    # # print("Branch node", branch_nodes)
    # print("Branch Node Line No ", [get_node_lineno(n) for n in branch_nodes])
    dest_nodes = [get_dest_nodes(n) for n in branch_nodes]
    # print(dest_nodes)
    
    # map to lineno
    branch_nodes_linenos = [get_node_lineno(n) for n in branch_nodes]
    dest_node_linenos = [
        {k: get_node_lineno(v) for k, v in d.items()} for d in dest_nodes
    ]
    # print("Destination nodes line number", dest_node_linenos_)
    return branch_nodes_linenos, dest_node_linenos




def get_value_type(typ):
    if "char" in typ:
        return "char"
    elif "double" in typ or "float" in typ:
        return "float"
    elif "int" in typ or "long" in typ:
        return "int"
    elif "bool" in typ:
        return "bool"
    elif "void" in typ:
        return "void"
    return "unknown"

def get_data_type(typ):
    if "*" in typ:
        return "pointer"
    elif "[" in typ:
        return "array"
    else:
        return "basic"
    
def get_quantized_value_for_pointer(variable):
    if variable.text == "0x0":
        return "NULL"
    else:
        return "NOT_NULL"

def get_quantized_value_for_array(variable, var_states):
    if variable.attrib["age"] == "old":
        return var_states[variable.attrib["name"]][2]
    elif variable.attrib["age"] == "modified":
        return "INITIALIZED"
    else:
        return "NOT_INITIALIZED"
        
def get_quantized_value_for_basic(variable, data_type, value_type):
    try:
        if value_type == "int":
            value = int(variable.text)
            if 10000 < value:
                return "POSITIVE-VL"
            elif 0 < value <= 10000:
                return "POSITIVE-REG"
            if value == 0:
                return "ZERO"
            elif -10000 <= value < 0:
                return "NEGATIVE-REG"
            elif value < -10000:
                return "NEGATIVE-VL"
        elif value_type == float:
            value = float(variable.text)
            if 10000 < value:
                return "POSITIVE-VL"
            elif 1 < value <= 10000:
                return "POSITIVE-REG"
            elif 0 < value <= 1:
                return "POSITIVE-VS"
            elif value == 0:
                return "ZERO"
            elif 0 > value >= -1:
                return "NEGATIVE-VS"
            elif -10000 <= value < -1:
                return "NEGATIVE-REG"
            elif value < -10000:
                return "NEGATIVE-VL"
        elif value_type == "char":
            value = variable.text[1:-1]
            value  = "".join(value.split())
            # print(value, end=" ")
            # print(value, value.isalpha(), type(value), len(value))
            if value == "\\000":
                # print("NULL")
                return "NULL"
            elif value.isalpha():
                # print("Alpha")
                return "ALPHA"
            else:
                # print("NOT Alpha")
                # print(value)
                return "NOT_ALPHA"
        elif value_type == "bool":
            value = int(variable.text)
            if value == 1:
                return "TRUE"
            else:
                return "FALSE"
        elif value_type == "void":
            return "VOID"
        else:
            return "UNKNOWN"
    except:
        return "UNKNOWN"
        
    
def quantized_variable(variable, var_states):
    typ = variable.attrib["typ"]
    data_type, value_type = get_data_type(typ), get_value_type(typ)
    if data_type == "array":
        quantized_value = get_quantized_value_for_array(variable, var_states)
    elif data_type == "pointer":
        quantized_value = get_quantized_value_for_pointer(variable)
        
    else:
        quantized_value = get_quantized_value_for_basic(variable, data_type, value_type)
    return data_type, value_type, quantized_value


def extract_base_identifier(node):
    """
    Recursively walk the left-hand side and return the base variable name.
    """
    if node.type == 'identifier':
        return [node]
    vars = []
    for child in node.children:
        result = extract_base_identifier(child)
        if result:
            vars.extend(result)

    return vars
def extract_left_identifier(node):
    """
    Recursively walk the left-hand side and return the base variable name.
    """
    if node.type == 'identifier':
        return node.text.decode()

    for child in node.children:
        result = extract_left_identifier(child)
        if result:
            return result

    return None

def extract_identifiers(node, results):
    if node.type == "identifier":
        results.add(node.text.decode())
    for child in node.children:
        extract_identifiers(child, results)



def is_call(n):
    if "call" in n.type:
        return True
    for child in n.children:
        # print(child.type,)
        if is_call(child):
            return True
    return False
