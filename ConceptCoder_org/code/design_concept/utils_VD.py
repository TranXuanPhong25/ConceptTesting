import os
import re
import json
import random
import pandas as pd

from tree_sitter_languages import get_parser



def get_pointer_from_argument(node):
    if node.type == "pointer_declarator":
        return [node.children[1].text.decode()]
    ptrs = []
    for child in node.children:
        ptrs.extend(get_pointer_from_argument(child))
    return ptrs

def get_pointers(root, code):
    pointers = []
    q = [root]
    function_param_ptrs = []
    while len(q) > 0:
        n = q.pop()
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue
        if n.type == "function_declarator":
            function_param_ptrs = get_pointer_from_argument(n)
        
        if n.type == "pointer_declarator" and n.children[1].type in ("identifier", "pointer_declarator"):
            pointers.append(n.children[1].text.decode())
        
        if n.type == "field_expression" and n.children[1].type in ("->"):
            pointers.append(n.children[0].text.decode())
    
        if n.type == "assignment_expression":
            # assert len(n.children) == 3
            if n.children[2].type == "null":
                pointers.append(n.children[0].text.decode())
        
        if n.type == "call_expression":
            # assert len(n.children) == 2
            if "free" in n.children[0].text.decode():
                if len(n.children[1].children) == 3:
                    pointers.append(n.children[1].children[1].text.decode())
        if n.type in ("subscript_expression"):
            pointers.append(n.children[0].text.decode())

        q.extend(reversed(list(n.children)))
    # print(function_param_ptrs)
    return list(set(pointers)), function_param_ptrs

def get_indices(root, code):
    indices = []
    q = [root]
    while len(q) > 0:
        n = q.pop()
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue
        if n.type in ("subscript_expression") and n.children[2].type not in ("number_literal", "binary_expression"):
            indices.append(n.children[2].text.decode())
        q.extend(reversed(list(n.children)))
    return list(set(indices))


def is_null_check(node, ptrs):
    if node.type == "condition_clause":
        if len(node.children) != 3:
            return False
        return is_null_check(node.children[1], ptrs)
    # print(node.text.decode(), ptrs)

    if node.text.decode() in ptrs:
        return True
    # if node.text.decode() in ptrs:
    #     return True
    if node.type == "unary_expression":
        # print(node.children[1].text.decode())
        if node.children[1].text.decode() in ptrs:
            return True
    elif node.type == "binary_expression":
        if node.children[1].type == "==" and "null" in node.children[2].text.decode().lower():
            return True
        if node.children[1].type == "!=" and "null" in node.children[2].text.decode().lower():
            return True
        if node.children[1].type in ("&&", "||"):
            return is_null_check(node.children[0], ptrs) | is_null_check(node.children[2], ptrs)
    return False


def get_ptrs_from_null_check(node, ptrs):
    if node.type == "condition_clause":
        if len(node.children) != 3:
            return []
        return get_ptrs_from_null_check(node.children[1], ptrs)
    # print(node.text.decode())
    if node.text.decode() in ptrs:
        return [node.text.decode()]

    if node.type == "unary_expression":
        if node.children[1].text.decode() in ptrs:
            return [node.children[1].text.decode()]
    elif node.type == "binary_expression":
        if node.children[1].type == "==" and "null" in node.children[2].text.decode().lower():
            return [node.children[0].text.decode()]
        if node.children[1].type == "!=" and "null" in node.children[2].text.decode().lower():
            return [node.children[0].text.decode()]
        # print(node.children[1].type)
        if node.children[1].type in ("&&", "||"):
            return get_ptrs_from_null_check(node.children[0], ptrs) + get_ptrs_from_null_check(node.children[2], ptrs)
    return []

def has_callexpression(node):
    if node.type == "call_expression":
        return True
    res = False
    for child in node.children:
        res |= has_callexpression(child)
    return res
def get_call_name(node):
    if node.type == "call_expression":
        return node.children[0].text.decode()
    
    for child in node.children:
        res = get_call_name(child)
        if res:
            return res
    return None

def get_indices(root, code):
    indices = []
    q = [root]
    while len(q) > 0:
        n = q.pop()
        if n.type == "comment":
            continue
        if "string" in str(n.type) or "char" in str(n.type):
            continue
        if len(n.children) == 0:
            continue
        # if n.type in ("subscript_expression"):
        #     print(n.text.decode(), n.children)
        #     print(len(n.children))
        #     for child in n.children:
        #         print("Child: ", child.text.decode())
                # print("Child: ", )
        if n.type in ("subscript_expression") and n.children[2].type not in ("number_literal", "binary_expression"):
            indices.append(n.children[2].text.decode())
        q.extend(reversed(list(n.children)))
    return list(set(indices))