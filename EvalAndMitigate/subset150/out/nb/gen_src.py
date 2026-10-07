import sys; sys.path[:0] = ['/repo', '/repo/run']

# ---- cell 0
import json
import os
import sys
import re
from utils.java_parser import parse_import_stmts_from_file_code, parse_fields_from_class_code, parse_method_invocation, parse_param_declaration_from_method_code
from data.configuration import code_base
from utils.prompt_formats.prompt_formatter import PromptFormatter
from tree_sitter import Parser
from data.configuration import JAVA_LANGUAGE
from typing import List
import pickle
from tqdm import tqdm

# ---- cell 1

parser = Parser()
parser.set_language(JAVA_LANGUAGE)

# ---- cell 2
import pickle
from tree_sitter import Parser
from data.configuration import JAVA_LANGUAGE

import re

def complete_parse_param_declaration_from_method_code(method_code: str):
    """
    Given a Java method (or constructor) signature as a string, return a list of (type, name)
    tuples from its parameter list.

    Example:
        Input:
            "BasicBlock(BasicBlock parent, Node root) { ... }"
        Output:
            [("BasicBlock", "parent"), ("Node", "root")]
    """
    # replace \n with space
    method_code = method_code.replace('\n', ' ')
    # 1. Extract everything inside the first set of parentheses
    #    e.g. "BasicBlock parent, Node root" from "BasicBlock(BasicBlock parent, Node root) { ... }"
    match = re.search(r'\((.*?)\)', method_code, re.DOTALL)
    if not match:
        # No parentheses = no parameters
        return []

    param_str = match.group(1).strip()
    if not param_str:
        # Empty parentheses = no parameters
        return []

    # 2. Split the parameter list by commas
    #    e.g. ["BasicBlock parent", "Node root"]
    param_list = [p.strip() for p in param_str.split(',')]

    result = []
    for p in param_list:
        # e.g. p = "BasicBlock parent"
        # We'll do a naive split by whitespace
        parts = p.split()
        if len(parts) < 2:
            # Possibly an invalid or incomplete param, skip
            continue

        # type might consist of multiple tokens (e.g., generics like "List<String>")
        # so we take everything except the last token as the type, and the last token as the name.
        raw_type_tokens = [t for t in parts[:-1] if not t.startswith('@')]
        param_type = " ".join(raw_type_tokens)
        param_name = parts[-1]

        result.append((param_type, param_name))

    if not result:
        other_parsed_params = parse_param_declaration_from_method_code(method_code)
        for param_name in other_parsed_params:
            result.append((other_parsed_params[param_name], param_name))

    return result


def parse_class_docstring(class_code: str, class_name: str, need_prefix=False) -> str:
    """
    Retrieve the docstring of the specified class (class_name) in the given Java code.
    If there is no preceding comment or no class with matching name, returns an empty string.

    :param class_code: The Java code as a string (may or may not be a complete file).
    :param class_name: The name of the class whose docstring we want.
    :param need_prefix: If True, wrap code in a dummy class so Tree-sitter can parse it.
    :return: The docstring text (or empty string if none is found).
    """

    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    # 1. Optionally wrap the code in a dummy class so that Tree-sitter
    #    sees a valid compilation unit, if needed
    tmp_code = pickle.loads(pickle.dumps(class_code))
    if need_prefix:
        tmp_code = f"public class TmpClass {{\n{tmp_code}\n}}"

    # 2. Parse the code
    tree = parser.parse(tmp_code.encode("utf-8"))
    root_node = tree.root_node

    # 3. Query for all class_declaration nodes
    class_query = JAVA_LANGUAGE.query(
        """
        (class_declaration) @cls
        """
    )
    class_captures = class_query.captures(root_node)

    # Helper function: get the identifier (class name) from a class_declaration node
    def get_class_node_name(node):
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return ""

    # 4. Capture all comments (line_comment or block_comment)
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    comment_captures = comment_query.captures(root_node)

    # Build a list of {text, start_line, end_line} for each comment
    comments = []
    for comment_node, _ in comment_captures:
        c_text = comment_node.text.decode("utf-8")
        c_start_line = comment_node.start_point[0]
        c_end_line = comment_node.end_point[0]
        comments.append({
            "text": c_text,
            "start_line": c_start_line,
            "end_line": c_end_line
        })

    # 5. Find the class whose name matches class_name
    for (node, capture_name) in class_captures:
        if capture_name == "cls":
            found_class_name = get_class_node_name(node)
            if found_class_name == class_name:
                # Found the matching class node
                class_start_line = node.start_point[0]
                docstring = ""
                closest_line = -1

                # 6. Find the "closest preceding" comment
                for c in comments:
                    # We only consider comments that end before the class starts
                    if c["end_line"] < class_start_line and c["end_line"] >= closest_line:
                        closest_line = c["end_line"]
                        docstring = c["text"].strip()

                return docstring

    # If no class with matching name is found, or no docstring is found, return ""
    return ""

def parse_methods_from_class_node(class_str: str, need_prefix=False):
    """
    Analyze methods defined in the class_str.

    :param class_str: Java code string (optionally missing a class wrapper).
    :param need_prefix: Whether to wrap code in "public class TmpClass{\n...}\n".
    :return: list of collected methods. Each element is a dict like:
        {
            "method_name": method_name,
            "method_modifiers": method_modifiers,
            "method_return_type": method_return_type,
            "method_body": method_body,
            "method_text": method_text,
            "method_start_line": method_start_line,
            "method_end_line": method_end_line,
            "docstring": docstring_text_or_empty
        }
    """

    # Create a copy of the string so we don't mutate the original
    tmp_class_str = pickle.loads(pickle.dumps(class_str))

    # Optionally wrap in a dummy class so Tree-sitter sees a valid compilation unit
    if need_prefix:
        tmp_class_str = "public class TmpClass {\n" + tmp_class_str + "\n}"

    # Parse the code into a syntax tree
    tree = parser.parse(tmp_class_str.encode("utf-8"))
    rets = []

    # ------------------------------------------------------------------------
    # 1. CAPTURE METHOD DECLARATIONS (Just to find all 'method_declaration' nodes)
    # ------------------------------------------------------------------------
    method_query = JAVA_LANGUAGE.query(
        """
        (method_declaration) @method_decl
        """
    )
    methods = method_query.captures(tree.root_node)

    # ------------------------------------------------------------------------
    # 2. CAPTURE METHOD ATTRIBUTES (modifiers, return type, name, body)
    #    NOTE: In some versions of tree-sitter-java, return type is "_type" not "type".
    #          Adjust accordingly if you see a NameError for 'type' node.
    # ------------------------------------------------------------------------
    method_attr_query = JAVA_LANGUAGE.query(
        """
        (method_declaration [
            (modifiers) @modifier
            type:(_) @ret_type
            name:(identifier) @name
            body:(block) @body
            ])
        """
    )

    # ------------------------------------------------------------------------
    # 3. CAPTURE ALL COMMENTS (line_comment OR block_comment)
    # ------------------------------------------------------------------------
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    comment_nodes = comment_query.captures(tree.root_node)

    # Convert comment nodes into a convenient list
    # Each comment is a dict with "text", "start_line", "end_line"
    comment_list = []
    for comment_node, capture_name in comment_nodes:
        c_text = comment_node.text.decode("utf-8")
        c_start_line = comment_node.start_point[0]
        c_end_line = comment_node.end_point[0]
        comment_list.append({
            "text": c_text,
            "start_line": c_start_line,
            "end_line": c_end_line
        })

    # ------------------------------------------------------------------------
    # 4. BUILD METHOD STRUCTS
    # ------------------------------------------------------------------------
    unique_methods = set()

    for method_node, _ in methods:
        # Gather attribute captures for this particular method node
        attrs = method_attr_query.captures(method_node)

        # We expect 4 captures: (modifier, ret_type, name, body)
        # If we have a mismatch, skip this node
        if len(attrs) % 4 != 0:
            continue

        num_iter = len(attrs) // 4
        for i in range(num_iter):
            # Just a sanity check that the second capture is "ret_type"
            assert attrs[i * 4 + 1][1] == "ret_type"

            method_text = method_node.text.decode("utf-8")
            method_modifiers = attrs[i * 4][0].text.decode("utf-8")
            method_return_type = attrs[i * 4 + 1][0].text.decode("utf-8")
            method_name = attrs[i * 4 + 2][0].text.decode("utf-8")
            method_body = attrs[i * 4 + 3][0].text.decode("utf-8")

            method_start_line = method_node.start_point[0]
            method_end_line = method_node.end_point[0]

            # ----------------------------------------------------------------
            # 5. DETECT A "DOCSTRING" (closest preceding comment)
            # ----------------------------------------------------------------
            docstring = ""
            closest_end_line = -1
            for c in comment_list:
                # We want the comment that appears strictly before the method_start_line
                # but is closest. So we track the largest c["end_line"] that is < method_start_line
                if c["end_line"] < method_start_line and c["end_line"] >= closest_end_line:
                    closest_end_line = c["end_line"]
                    docstring = c["text"].strip()

            # Optional dedup logic by method_body
            if method_body not in unique_methods and method_body.strip() != "":
                unique_methods.add(method_body)
                rets.append({
                    "method_name": method_name,
                    "method_modifiers": method_modifiers,
                    "method_return_type": method_return_type,
                    "method_body": method_body,
                    "method_text": method_text,
                    "method_start_line": method_start_line,
                    "method_end_line": method_end_line,
                    "docstring": docstring,
                })

    # Finally, return the collected list of method dictionaries
    return rets


def parse_methods_from_class_node_no_return_type_needed(class_str: str, need_prefix=False):
    """
    Analyze methods defined in the class_str, *without assuming* a declared return type.

    :param class_str: Java code string (optionally missing a class wrapper).
    :param need_prefix: Whether to wrap code in "public class TmpClass{\n...}\n".
    :return: list of collected methods. Each element is a dict like:
        {
            "method_name": method_name,
            "method_modifiers": method_modifiers,
            "method_return_type": method_return_type_or_empty,
            "method_body": method_body,
            "method_text": method_text,
            "method_start_line": method_start_line,
            "method_end_line": method_end_line,
            "docstring": docstring_text_or_empty
        }
    """

    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    # Make a safe copy of the input string
    tmp_class_str = pickle.loads(pickle.dumps(class_str))

    # Optionally wrap the snippet so it's seen as a valid compilation unit
    if need_prefix:
        tmp_class_str = "public class TmpClass {\n" + tmp_class_str + "\n}"

    # Parse the code
    tree = parser.parse(tmp_class_str.encode("utf-8"))
    root_node = tree.root_node
    rets = []

    # 1. Capture all method_declaration nodes
    method_query = JAVA_LANGUAGE.query(
        """
        (method_declaration) @method_decl
        """
    )
    methods = method_query.captures(root_node)

    # 2. Make the return type optional in our attribute query:
    #    - (modifiers)? @modifier
    #    - (type:(_))? @ret_type  <-- optionally capture return type if present
    #    - name:(identifier) @name
    #    - body:(block) @body
    #
    # We'll have either 3 or 4 captures, depending on whether the type is present.
    method_attr_query = JAVA_LANGUAGE.query(
        """
        (method_declaration [
            (modifiers)? @modifier
            name:(identifier) @name
            body:(block) @body
        ])
        """
    )

    # 3. Capture all comments (line_comment OR block_comment)
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    comment_nodes = comment_query.captures(root_node)

    # Store comments in a list of dicts
    comment_list = []
    for comment_node, capture_name in comment_nodes:
        c_text = comment_node.text.decode("utf-8")
        c_start_line = comment_node.start_point[0]
        c_end_line = comment_node.end_point[0]
        comment_list.append({
            "text": c_text,
            "start_line": c_start_line,
            "end_line": c_end_line
        })

    unique_methods = set()

    # 4. Build method dicts
    for method_node, _ in methods:
        attrs = method_attr_query.captures(method_node)

        # Possible captures:
        #    - 3 captures if no return type: [ (modifier)?, (name), (body) ]
        #    - 4 captures if there's a return type: [ (modifier)?, (ret_type), (name), (body) ]
        # We'll parse them by label rather than index.
        captures_by_name = {}
        for (node_obj, node_label) in attrs:
            captures_by_name[node_label] = node_obj

        # Extract them if they exist
        modifier_node = captures_by_name.get("modifier", None)
        ret_type_node = captures_by_name.get("ret_type", None)
        name_node = captures_by_name.get("name", None)
        body_node = captures_by_name.get("body", None)

        # Must have a name and body at least
        if not name_node or not body_node:
            continue

        method_modifiers = modifier_node.text.decode("utf-8") if modifier_node else ""
        method_return_type = ret_type_node.text.decode("utf-8") if ret_type_node else ""

        method_name = name_node.text.decode("utf-8")
        method_body = body_node.text.decode("utf-8")

        method_text = method_node.text.decode("utf-8")
        method_start_line = method_node.start_point[0]
        method_end_line = method_node.end_point[0]

        # Find docstring
        docstring = ""
        closest_end_line = -1
        for c in comment_list:
            if c["end_line"] < method_start_line and c["end_line"] >= closest_end_line:
                closest_end_line = c["end_line"]
                docstring = c["text"].strip()

        # Deduplicate by method_body
        if method_body not in unique_methods and method_body.strip():
            unique_methods.add(method_body)
            rets.append({
                "method_name": method_name,
                "method_modifiers": method_modifiers,
                "method_return_type": method_return_type,  # Might be "" if no type
                "method_body": method_body,
                "method_text": method_text,
                "method_start_line": method_start_line,
                "method_end_line": method_end_line,
                "docstring": docstring,
            })

    return rets


def parse_constructors_from_class_node(class_str: str, need_prefix=False):
    """
    Analyze constructors defined in the class_str.
    Returns a list of collected constructors. The elements are dicts like:
        {
            "method_name": constructor_name,
            "method_modifiers": constructor_modifiers,
            "method_body": constructor_body,
            "method_text": entire_constructor_text,
            "method_start_line": constructor_start_line,
            "method_end_line": constructor_end_line,
            "docstring": docstring_text_or_empty
        }
    """

    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    # Make a copy of the input string
    tmp_class_str = pickle.loads(pickle.dumps(class_str))

    # Optionally wrap in a dummy class, if needed
    if need_prefix:
        tmp_class_str = "public class TmpClass {\n" + tmp_class_str + "\n}"

    # Parse the code
    tree = parser.parse(tmp_class_str.encode("utf-8"))
    root_node = tree.root_node

    rets = []
    unique_ctors = set()

    # -----------------------------------------------------------------
    # 1. Query to find all constructor declarations
    # -----------------------------------------------------------------
    constructor_query = JAVA_LANGUAGE.query(
        """
        (constructor_declaration) @ctor_decl
        """
    )
    ctors = constructor_query.captures(root_node)

    # -----------------------------------------------------------------
    # 2. Query to capture attributes of each constructor
    #    (modifiers)? @modifier, name:(identifier) @name, body:(constructor_body) @body
    # -----------------------------------------------------------------
    constructor_attr_query = JAVA_LANGUAGE.query(
        """
        (constructor_declaration [
            (modifiers)? @modifier
            name:(identifier) @name
            body:(constructor_body) @body
        ])
        """
    )

    # -----------------------------------------------------------------
    # 3. Capture all comments (line_comment or block_comment)
    # -----------------------------------------------------------------
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    comment_captures = comment_query.captures(root_node)

    # Build a list of comment info
    # Each comment is { "text": ..., "start_line": ..., "end_line": ... }
    comments = []
    for comment_node, _ in comment_captures:
        c_text = comment_node.text.decode("utf-8")
        c_start_line = comment_node.start_point[0]
        c_end_line = comment_node.end_point[0]
        comments.append({
            "text": c_text,
            "start_line": c_start_line,
            "end_line": c_end_line
        })

    # -----------------------------------------------------------------
    # 4. Extract info for each constructor node
    # -----------------------------------------------------------------
    for ctor_node, _ in ctors:
        # Extract attributes from this constructor node
        attrs = constructor_attr_query.captures(ctor_node)
        # Example: [ (Node_for_modifiers, "modifier"),
        #            (Node_for_identifier, "name"),
        #            (Node_for_constructor_body, "body") ]

        # Convert the full constructor node text to string
        constructor_text = ctor_node.text.decode("utf-8")

        # Default values
        constructor_modifiers = ""
        constructor_name = ""
        constructor_body = ""

        # We'll store captures in a dict keyed by capture_name
        temp_dict = {}
        for (node_capture, capture_name) in attrs:
            temp_dict[capture_name] = node_capture.text.decode("utf-8")

        # Fill the variables from temp_dict (if missing, default to "")
        constructor_modifiers = temp_dict.get("modifier", "")
        constructor_name = temp_dict.get("name", "")
        constructor_body = temp_dict.get("body", "")

        start_line = ctor_node.start_point[0]
        end_line = ctor_node.end_point[0]

        # -----------------------------------------------------------------
        # 5. Detect a "docstring" (closest preceding comment)
        # -----------------------------------------------------------------
        docstring = ""
        closest_line = -1
        for c in comments:
            # We want the comment that ends strictly before the constructor's start_line
            # and is closest to it
            if c["end_line"] < start_line and c["end_line"] >= closest_line:
                closest_line = c["end_line"]
                docstring = c["text"].strip()

        # Deduplicate if needed
        body_stripped = constructor_body.strip()
        if body_stripped and body_stripped not in unique_ctors:
            unique_ctors.add(body_stripped)

            rets.append({
                "method_name": constructor_name,             # For consistency with your method structure
                "method_modifiers": constructor_modifiers,
                "method_body": constructor_body,
                "method_text": constructor_text,
                "method_start_line": start_line,
                "method_end_line": end_line,
                "docstring": docstring,                      # <-- NEW FIELD
            })

    return rets

def get_node_text(source_code_bytes, node):
    """Return the text of a node (for convenience)."""
    return source_code_bytes[node.start_byte: node.end_byte].decode('utf-8')

def replace_last_dot_with_hash(fqcn: str) -> str:
    """
    Replace the *last* '.' in a fully qualified class name with '#'.
    E.g. "org.jfree.chart.util.ShapeUtilities" => "org.jfree.chart.util#ShapeUtilities"
    """
    idx = fqcn.rfind('.')
    if idx == -1:
        return fqcn
    return fqcn[:idx] + '#' + fqcn[idx+1:]

def parse_package_name(code_str):
    """
    Find the package declaration node and return its name (e.g. org.jfree.chart.util).
    """
    # Look for (package_declaration (scoped_identifier))
    # or (package_declaration (identifier)) structures
    # in the Tree-sitter Java grammar.

    # 1. Parse the code with Tree-sitter
    source_code_bytes = code_str.encode("utf-8")
    tree = parser.parse(source_code_bytes)
    root_node = tree.root_node

    for child in root_node.children:
        if child.type == 'package_declaration':
            # The child typically has structure: 'package' <scoped_identifier> ';'
            # We'll read everything except the keyword "package" and the semicolon.
            for sub in child.children:
                if sub.type in ('scoped_identifier', 'identifier'):
                    return get_node_text(source_code_bytes, sub)
    return ""  # default if no package declared

def parse_imports(code_str):
    """
    Parse import declarations and return a dictionary that maps
    short type name -> fully qualified name.

    For wildcard imports, store them in a list to attempt resolution later.
    """
    # 1. Parse the code with Tree-sitter
    source_code_bytes = code_str.encode("utf-8")
    tree = parser.parse(source_code_bytes)
    root_node = tree.root_node

    single_imports = {}
    wildcard_imports = []

    for child in root_node.children:
        if child.type == 'import_declaration':
            text = get_node_text(source_code_bytes, child)
            # text looks like: "import java.awt.geom.GeneralPath;" or "import java.awt.geom.*;"
            text = text.replace('import ', '').replace(';', '').strip()

            if text.endswith('.*'):
                # E.g. "java.awt.geom.*"
                base_package = text[:-2]  # remove .*
                wildcard_imports.append(base_package)
            else:
                # Single import
                # e.g. "java.awt.geom.GeneralPath"
                parts = text.split('.')
                short_name = parts[-1]
                single_imports[short_name] = text

    return single_imports, wildcard_imports


def get_node_subtree_text(source_code_bytes, node):
    """
    Collect all text corresponding to `node` and its descendants in a DFS manner.
    This ensures we don't miss child nodes like annotations or generics.
    """
    fragments = []
    stack = [node]
    while stack:
        n = stack.pop()
        fragments.append(
            source_code_bytes[n.start_byte:n.end_byte].decode('utf-8')
        )
        # push children in reverse so we pop in correct order
        for child in reversed(n.children):
            stack.append(child)
    return "".join(fragments)

def parse_method_signature(signature_str):
    """
    Parses a method signature of the format:
      className:methodName:[paramType1 paramName1, paramType2 paramName2]:returnType

    Example:
      "org.jfree.chart.util.ShapeUtilities:equal:[GeneralPath p1, GeneralPath p2]:boolean"

    Returns a dictionary:
      {
        'class_name': 'org.jfree.chart.util.ShapeUtilities',
        'method_name': 'equal',
        'params': {'p1': 'GeneralPath', 'p2': 'GeneralPath'},
        'return_type': 'boolean'
      }

    This updated version also handles annotations in parameter declarations, e.g.
      "@Nullable AbstractCompiler compiler"
    by stripping any token that starts with '@' from the type.
    """

    # Split by colon
    signature_parts = signature_str.split(':')

    if len(signature_parts) != 4:
        raise ValueError(f"Invalid signature format: '{signature_str}'")

    class_name = signature_parts[0].strip()
    method_name = signature_parts[1].strip()
    params_str = signature_parts[2].strip()
    return_type = signature_parts[3].strip()

    # remove the first [ and the last ] in params_str
    params_str = params_str[1:-1].strip()

    param_list = []
    if params_str:
        # Split by comma for multiple parameters
        for param in params_str.split(', '):
            param = param.strip()
            # Split by whitespace
            parts = param.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid parameter format: '{param}' in signature: {signature_str}")

            # Last token is the param name
            p_name = parts[-1]

            # Everything else is the type, but skip annotation tokens (those starting with '@')
            raw_type_tokens = [t for t in parts[:-1] if not t.startswith('@')]
            p_type = " ".join(raw_type_tokens)
            p_type = p_type.strip()

            param_list.append((p_type, p_name))

    return {
        'class_name': class_name,
        'method_name': method_name,
        'params': param_list,
        'return_type': return_type
    }



def match_method(signature_str, method_info):
    """
    Checks if the given signature matches the method info dictionary.

    method_info is expected to have keys:
      - 'method_name'
      - 'method_params'
      - 'method_return_type'
    """
    # Parse the signature
    parsed = parse_method_signature(signature_str)

    # Check method name
    if parsed['method_name'] != method_info.get('method_name'):
        return False

    # Check parameters (dict comparison)
    if parsed['params'] != method_info.get('method_params'):
        return False

    return True


def resolve_type(short_name, single_imports, wildcard_imports, package_name, same_dir_classes):
    """
    Attempt to resolve a short type name to a fully qualified name.
    1. Primitive -> wrapper class in java.lang
    2. single_imports -> explicit FQN
    3. known java.lang class
    4. naive fallback to wildcard import
    5. fallback: just return the short name
    """

    # 1. Check if it's a primitive -> map to wrapper
    primitives_to_wrappers = {
        "boolean": "java.lang.Boolean",
        "byte":    "java.lang.Byte",
        "char":    "java.lang.Character",
        "short":   "java.lang.Short",
        "int":     "java.lang.Integer",
        "long":    "java.lang.Long",
        "float":   "java.lang.Float",
        "double":  "java.lang.Double",
    }
    if short_name in primitives_to_wrappers:
        return primitives_to_wrappers[short_name]

    # 2. Check single imports
    if short_name in single_imports:
        return single_imports[short_name]

    # 3. Known java.lang classes
    known_java_lang = {
        "String":    "java.lang.String",
        "Boolean":   "java.lang.Boolean",
        "Integer":   "java.lang.Integer",
        "Long":      "java.lang.Long",
        "Double":    "java.lang.Double",
        "Float":     "java.lang.Float",
        "Byte":      "java.lang.Byte",
        "Short":     "java.lang.Short",
        "Character": "java.lang.Character",
        "Object":    "java.lang.Object",
    }
    if short_name in known_java_lang:
        return known_java_lang[short_name]

    # 4. Check if it's in the same package
    if short_name in same_dir_classes:
        return f"{package_name}.{short_name}"

    # 5. Naive fallback to wildcard imports
    for pkg in wildcard_imports:
        # Real logic would do classpath scanning, etc.
        # We'll just guess it belongs to the first wildcard import
        return f"{pkg}.{short_name}"

    # 6. if not find in any of the above, the type might be in the same package, so return the type with package name
    return f"{package_name}.{short_name}"

def assemble_method_signature(class_name_prefix, class_name, method_name, full_type_params):
    refactored_paramss = []
    for param in full_type_params:
        source = '.'.join(param.split('.')[:-1])
        param_name = param.split('.')[-1]
        refactored_paramss.append(f"{source}#{param_name}")
    params = "(" + ", ".join(refactored_paramss) + ")"
    return f"{class_name_prefix}#{class_name}#{method_name}{params}"

def get_focal_method(class_methods, method_sig):
    focal_method = None
    for method in class_methods:
        if match_method(method_sig, method):
            focal_method = method
            break
    return focal_method

def get_non_focal_methods(class_methods, focal_method_sig):
    non_focal_methods = []
    for method in class_methods:
        if match_method(focal_method_sig, method):
            continue
        non_focal_methods.append(method)
    return non_focal_methods

def get_method_declaration(method_code: str) -> str:
    """
    Find the method declaration from the method code (including any decorator lines
    such as @Override), and return the declaration up to (but not including) the
    opening '{' of the method body.
    """
    # 1. Wrap the snippet in a dummy class so Tree-sitter can parse it as valid Java
    tmp_method_code = "public class TmpClass {\n" + method_code + "}\n"

    # 2. Parse the code snippet
    tree = parser.parse(tmp_method_code.encode("utf-8"))

    # A recursive DFS to traverse the syntax tree
    def traverse(node):
        yield node
        for child in node.children:
            yield from traverse(child)

    root_node = tree.root_node

    # 3. Look for the first 'method_declaration' node
    for node in traverse(root_node):
        if node.type == "method_declaration" or node.type == "constructor_declaration":
            start_byte = node.start_byte
            end_byte = node.end_byte

            ## 4. Extract the raw substring for the method (including any annotations)
            method_decl_substring = tmp_method_code[start_byte:end_byte]

            # 5. Truncate everything after the first '{'
            #    This removes the method body but keeps the method signature + decorators
            parts = method_decl_substring.split('{', 1)
            method_decl_substring = parts[0]

            # 6. Normalize line endings: replace "\r\n" or "\r" with "\n"
            method_decl_substring = re.sub(r'\r\n?', '\n', method_decl_substring)

            # 7. Split into lines
            lines = method_decl_substring.split('\n')

            # 8. We'll collect decorator lines separately (each on its own line)
            #    and collapse everything else into a single 'method signature' line
            decorator_lines = []
            signature_parts = []

            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue  # Skip empty lines
                # If line starts with '@', treat it as a decorator line
                if stripped_line.startswith('@'):
                    decorator_lines.append(stripped_line)
                else:
                    # Accumulate everything else into one line
                    signature_parts.append(stripped_line)

            # 9. Combine decorator lines (each on its own line) + single-line signature
            #    We'll collapse multiple spaces within signature_parts into one
            signature_line = ' '.join(signature_parts)

            # 10. Finally, append a semicolon
            signature_line = signature_line.strip() + ";"

            # 11. Reconstruct the final result
            #     - Decorators each on its own line
            #     - Then the single-line method signature
            if decorator_lines:
                # If there are decorator lines, join them with newlines,
                # then add the signature line on a new line
                final_declaration = "\n".join(decorator_lines) + "\n" + signature_line
            else:
                # No decorator lines, just the signature
                final_declaration = signature_line

            # 12. Return that string
            return final_declaration.strip()

    # If no method_declaration node was found, return an empty string
    return ""

def get_constructor_declaration(method_code: str) -> str:
    """
    Find the method declaration from the method code (including any decorator lines
    such as @Override), and return the declaration up to (but not including) the
    opening '{' of the method body.
    """
    # 1. Wrap the snippet in a dummy class so Tree-sitter can parse it as valid Java
    tmp_method_code = "public class TmpClass {\n" + method_code + "}\n"

    # 2. Parse the code snippet
    tree = parser.parse(tmp_method_code.encode("utf-8"))

    # A recursive DFS to traverse the syntax tree
    def traverse(node):
        yield node
        for child in node.children:
            yield from traverse(child)

    root_node = tree.root_node

    # 3. Look for the first 'method_declaration' node
    for node in traverse(root_node):
        if node.type == "constructor_declaration":
            start_byte = node.start_byte
            end_byte = node.end_byte

            ## 4. Extract the raw substring for the method (including any annotations)
            method_decl_substring = tmp_method_code[start_byte:end_byte]

            # 5. Truncate everything after the first '{'
            #    This removes the method body but keeps the method signature + decorators
            parts = method_decl_substring.split('{', 1)
            method_decl_substring = parts[0]

            # 6. Normalize line endings: replace "\r\n" or "\r" with "\n"
            method_decl_substring = re.sub(r'\r\n?', '\n', method_decl_substring)

            # 7. Split into lines
            lines = method_decl_substring.split('\n')

            # 8. We'll collect decorator lines separately (each on its own line)
            #    and collapse everything else into a single 'method signature' line
            decorator_lines = []
            signature_parts = []

            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue  # Skip empty lines
                # If line starts with '@', treat it as a decorator line
                if stripped_line.startswith('@'):
                    decorator_lines.append(stripped_line)
                else:
                    # Accumulate everything else into one line
                    signature_parts.append(stripped_line)

            # 9. Combine decorator lines (each on its own line) + single-line signature
            #    We'll collapse multiple spaces within signature_parts into one
            signature_line = ' '.join(signature_parts)

            # 10. Finally, append a semicolon
            signature_line = signature_line.strip() + ";"

            # 11. Reconstruct the final result
            #     - Decorators each on its own line
            #     - Then the single-line method signature
            if decorator_lines:
                # If there are decorator lines, join them with newlines,
                # then add the signature line on a new line
                final_declaration = "\n".join(decorator_lines) + "\n" + signature_line
            else:
                # No decorator lines, just the signature
                final_declaration = signature_line

            # 12. Return that string
            return final_declaration.strip()

    # If no method_declaration node was found, return an empty string
    return ""



def parse_class_from_code(java_code: str, class_name: str) -> str:
    """
    Extract the entire text of the class with the specified 'class_name' from
    the given 'java_code'. This includes annotations, modifiers, and everything
    up to the closing brace of the class body.

    :param java_code: A string containing Java source code.
    :param class_name: The name of the class to extract.
    :return: The text of the matching class (including decorators/annotations).
             Returns an empty string if no matching class is found.
    """

    # 1. Parse the code with Tree-sitter
    tree = parser.parse(java_code.encode("utf-8"))
    root_node = tree.root_node

    # 2. Query for all class_declaration nodes
    #    (Adjust if your grammar uses a different node name for classes.)
    class_query = JAVA_LANGUAGE.query(
        """
        (class_declaration) @cls
        """
    )
    captures = class_query.captures(root_node)

    # 3. Helper function: extract the name of the class from a class_declaration node
    def get_class_name_from_node(node) -> str:
        """
        Traverses the children of 'node' (which should be a class_declaration).
        Returns the text of the 'identifier' child, which is the class name.
        """
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return ""

    # 4. For each class_declaration node, check if the name matches 'class_name'
    for (node, capture_name) in captures:
        if capture_name == "cls":
            found_name = get_class_name_from_node(node)
            if found_name == class_name:
                # 5. Extract the entire substring from start_byte to end_byte
                start_byte = node.start_byte
                end_byte = node.end_byte
                class_text = java_code[start_byte:end_byte]
                return class_text

    # If no matching class was found, return empty string
    return ""

def parse_classes_from_code(java_code: str) -> List[str]:
    """
    Extract the contents of all classes in the given Java code.

    :param java_code: A string containing Java source code.
    :return: A list of class texts (including decorators/annotations).
    """

    # 1. Parse the code with Tree-sitter
    tree = parser.parse(java_code.encode("utf-8"))
    root_node = tree.root_node

    # 2. Query for all class_declaration nodes
    #    (Adjust if your grammar uses a different node name for classes.)
    class_query = JAVA_LANGUAGE.query(
        """
        (class_declaration) @cls
        """
    )
    captures = class_query.captures(root_node)

    # 3. Helper function: extract the name of the class from a class_declaration
    def get_class_name_from_node(node) -> str:
        """
        Traverses the children of 'node' (which should be a class_declaration
        node). Returns the text of the 'identifier' child, which is the class name.
        """
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return ""

    # 4. Collect the text of each class
    class_texts = {}
    for (node, capture_name) in captures:
        if capture_name == "cls":
            class_name = get_class_name_from_node(node)
            # Extract the entire substring from start_byte to end_byte
            start_byte = node.start_byte
            end_byte = node.end_byte
            class_text = java_code[start_byte:end_byte]
            class_texts[class_name] = class_text

    return class_texts

def check_invocation(class_codes, test_name):
    invoked_methods = []
    for class_code_key in class_codes:
        non_constructor_methods = parse_methods_from_class_node(class_codes[class_code_key])
        non_constructor_method_no_return_type = parse_methods_from_class_node_no_return_type_needed(class_codes[class_code_key])
        all_methods_in_class = set([method['method_text'] for method in non_constructor_methods] + [method['method_text'] for method in non_constructor_method_no_return_type])
        for method_text in all_methods_in_class:
            if test_name in method_text:
                for invocation in parse_method_invocation(method_text):
                    invoked_methods.append(invocation['invoked_method_name'])
    return invoked_methods

def find_invoking_tests(class_codes, method_name):
    invoking_tests = []
    for class_code_key in class_codes:
        non_constructor_methods = parse_methods_from_class_node(class_codes[class_code_key])
        non_constructor_method_no_return_type = parse_methods_from_class_node_no_return_type_needed(class_codes[class_code_key])
        all_methods_text_in_class = set()
        all_methods_in_class = []
        for test_method in non_constructor_methods + non_constructor_method_no_return_type:
            if test_method['method_text'] not in all_methods_text_in_class:
                all_methods_text_in_class.add(test_method['method_text'])
                all_methods_in_class.append(test_method)
        for test_method in all_methods_in_class:
            invocations = parse_method_invocation(test_method['method_text'])
            for invocation in invocations:
                if invocation['invoked_method_name'] == method_name:
                    invoking_tests.append(test_method)
                    break
    return invoking_tests

# ---- cell 3
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

# ---- cell 4
tgt_model = 'chatgpt'
format = 'comment'
strategy = 'generation'
ablation = 'full'
version = 'buggy'
proj_base_dir = '/repo/d4j_proj_base'

# ---- override after cell 4
# run/gen_src.ovr's version line, unchanged
import os
version = os.environ['VERSION']


# ---- cell 8
fix_info_dir = 'data/d4j2_fix_info'
# collect directory of all buggy_fix_info.json in the sub directories (with name of bugs in format name_id such as chart_1) of fix_info dir
buggy_fix_info_dirs = []
for root, dirs, files in os.walk(fix_info_dir):
    for file in files:
        if file == 'buggy_fix_info.json':
            buggy_fix_info_dirs.append(os.path.join(root, file))
buggy_fix_info_dirs

# ---- override after cell 8
# subset150: only the bugs in S150_BUGS that have a checkout of this version (run/gen_src.ovr keeps every checked-out bug)
_s150_bugs = set(os.environ['S150_BUGS'].split())
buggy_fix_info_dirs = [d for d in buggy_fix_info_dirs if os.path.basename(os.path.dirname(d)) in _s150_bugs and os.path.isdir(os.path.join(proj_base_dir, os.path.basename(os.path.dirname(d)), version))]
print(len(buggy_fix_info_dirs), 'bugs with checkout')


# ---- cell 75
test_buggy_fix_info_dirs = buggy_fix_info_dirs

# ---- cell 77
# Now we apply the above steps to all buggy_fix_info.json files
new_source_data = []
failed_bugs = []
# add a progress bar
pbar = tqdm(test_buggy_fix_info_dirs, unit='file', total=len(test_buggy_fix_info_dirs))
for buggy_fix_info_dir in pbar:
    with open(buggy_fix_info_dir, 'r') as f:
        buggy_fix_info = json.load(f)
    bug_name = buggy_fix_info['bug_name']
    bug_fixing_changes = buggy_fix_info['fixing_changes']
    for fixing_change in bug_fixing_changes:
        changed_classes_dir = set(fixing_change['changed_class'])

        all_full_class_dir = []
        for changed_class_dir in changed_classes_dir:
            all_full_class_dir.append(os.path.join(proj_base_dir, bug_name, version, changed_class_dir))

        all_full_class_dir_file_class_code = {}
        for full_class_dir in all_full_class_dir:
            # try to open the file, if file does not exist, continue to next full_class_dir
            try:
                with open(full_class_dir, 'r') as f:
                    curr_file_code = f.read()
                all_full_class_dir_file_class_code[full_class_dir] = parse_classes_from_code(curr_file_code)
            except FileNotFoundError:
                continue

        changed_functions = fixing_change['changed_functions']

        changed_function_names = set()
        for changed_function in changed_functions:
            changed_function_names.update(changed_function['qualified_names'])
        changed_function_names = list(changed_function_names)

        for new_inst_method_sig in changed_function_names:

            new_inst_method_info = parse_method_signature(new_inst_method_sig)
            new_inst_short_class_name = new_inst_method_info['class_name'].split('.')[-1]
            if "\\$" in new_inst_short_class_name:
                new_inst_short_class_name = new_inst_short_class_name.split("\\$")[-1]
            new_inst_class_name_prefix = '.'.join(new_inst_method_info['class_name'].split('.')[:-1])

            new_inst_full_class_dir = None
            for full_class_dir, file_class_code in all_full_class_dir_file_class_code.items():
                if new_inst_short_class_name in file_class_code:
                    new_inst_full_class_dir = full_class_dir
                    break
            if new_inst_full_class_dir is None:
                # continue to the next method if the class directory is not found
                failed_bugs.append([bug_name, new_inst_method_sig, buggy_fix_info_dir, "Class directory not found"])
                continue

            # try to open the file, if file does not exist, skip the current method
            try:
                with open(new_inst_full_class_dir, 'r') as f:
                    new_inst_file_code = f.read()
            except FileNotFoundError:
                failed_bugs.append([bug_name, new_inst_method_sig, buggy_fix_info_dir, "File not found"])
                continue
            new_inst_class_code = parse_class_from_code(new_inst_file_code, new_inst_short_class_name)

            new_inst_package_name = parse_package_name(new_inst_file_code)

            new_inst_same_dir_java_files = []
            new_inst_class_parent_dir = os.path.dirname(new_inst_full_class_dir)
            for files in os.listdir(new_inst_class_parent_dir):
                if files.endswith('.java'):
                    new_inst_same_dir_java_files.append(files)

            new_inst_same_dir_classes = {}
            for file in new_inst_same_dir_java_files:
                with open(os.path.join(new_inst_class_parent_dir, file), 'r') as f:
                    same_dir_file_code = f.read()
                    same_dir_package_name = parse_package_name(same_dir_file_code)
                    if same_dir_package_name:
                        if same_dir_package_name == new_inst_package_name:
                            new_inst_same_dir_classes.update(parse_classes_from_code(same_dir_file_code))

            new_inst_single_imports, new_inst_wildcard_imports = parse_imports(new_inst_file_code)

            new_inst_class_constructors = parse_constructors_from_class_node(new_inst_class_code)
            for constructor in new_inst_class_constructors:
                constructor['method_params'] = complete_parse_param_declaration_from_method_code(constructor['method_text'])

            new_inst_class_all_non_constructor_methods = parse_methods_from_class_node(new_inst_class_code)
            for method in new_inst_class_all_non_constructor_methods:
                method['method_params'] = complete_parse_param_declaration_from_method_code(method['method_text'])

            new_inst_class_all_non_constructor_methods_no_return_type = parse_methods_from_class_node_no_return_type_needed(new_inst_class_code)
            for method in new_inst_class_all_non_constructor_methods_no_return_type:
                method['method_params'] = complete_parse_param_declaration_from_method_code(method['method_text'])

            new_inst_class_all_methods = new_inst_class_constructors + new_inst_class_all_non_constructor_methods + new_inst_class_all_non_constructor_methods_no_return_type

            new_inst_focal_method = get_focal_method(new_inst_class_all_methods, new_inst_method_sig)
            if new_inst_focal_method is None:
                # continue to the next method if the focal method is not found
                failed_bugs.append([bug_name, new_inst_method_sig, buggy_fix_info_dir, "Focal method not found"])
                continue

            new_source_data_inst = {}

            new_source_data_inst["extra:project_name"] = f"{bug_name}_{version}"

            new_source_data_inst[focal_method_key] = new_inst_focal_method['method_text']

            if 'method_return_type' in new_inst_focal_method:
                new_source_data_inst[focal_method_return_type_key] = new_inst_focal_method['method_return_type']
            else:
                new_source_data_inst[focal_method_return_type_key] = ''

            new_source_data_inst[focal_method_name_key] = new_inst_method_info['method_name']

            new_inst_method_info['full_type_params'] = [resolve_type(param_pair[0], new_inst_single_imports, new_inst_wildcard_imports, new_inst_package_name, new_inst_same_dir_classes) for param_pair in new_inst_method_info['params']]
            new_source_data_inst[focal_method_signature_key] = assemble_method_signature(new_inst_class_name_prefix, new_inst_short_class_name, new_inst_method_info['method_name'], new_inst_method_info['full_type_params'])
            new_source_data_inst[focal_method_docstring_key] = new_inst_focal_method['docstring']

            new_source_data_inst[focal_method_param_key] = new_inst_method_info['params']

            new_source_data_inst[focal_class_other_methods_key] = []
            for method in get_non_focal_methods(new_inst_class_all_methods, new_inst_method_sig):
                new_source_data_inst[focal_class_other_methods_key].append(get_method_declaration(method['method_text']))

            new_source_data_inst[focal_class_fields_key] = []
            for class_field in parse_fields_from_class_code(new_inst_class_code):
                new_source_data_inst[focal_class_fields_key].append(class_field['declaration_text'])

            new_source_data_inst[focal_class_constructor_key] = []
            for constructor in new_inst_class_constructors:
                new_source_data_inst[focal_class_constructor_key].append(get_constructor_declaration(constructor['method_text']))

            new_source_data_inst[focal_class_name_key] = new_inst_short_class_name

            new_source_data_inst[focal_class_code_key] = new_inst_class_code

            new_source_data_inst[focal_class_docstring_key] = parse_class_docstring(new_inst_file_code, new_inst_short_class_name)

            new_source_data_inst[source_method_type_constructor_key] = []
            for param_pair in new_inst_method_info['params']:
                param_class_type_code = new_inst_same_dir_classes.get(param_pair[0], None)
                if param_class_type_code:
                    for param_constructor_declare in parse_constructors_from_class_node(param_class_type_code):
                        new_source_data_inst[source_method_type_constructor_key].append(get_constructor_declaration(param_constructor_declare['method_text']))

            new_source_data_inst[source_method_return_type_constructor_key] = []
            if new_source_data_inst[focal_method_return_type_key] != '' and new_source_data_inst[focal_method_return_type_key].lower() != 'void':
                return_type_class_code = new_inst_same_dir_classes.get(new_inst_focal_method['method_return_type'], None)
                if return_type_class_code:
                    for return_type_constructor_declare in parse_constructors_from_class_node(return_type_class_code):
                        new_source_data_inst[source_method_return_type_constructor_key].append(get_constructor_declaration(return_type_constructor_declare['method_text']))

            new_source_data_inst[source_method_parameter_key] = []
            for param_pair in new_inst_method_info['params']:
                new_source_data_inst[source_method_parameter_key].append(f"{param_pair[0]} {param_pair[1]}")

            new_source_data_inst[parameter_classes_key] = []
            for full_type_param in new_inst_method_info['full_type_params']:
                param_short_name = full_type_param.split('.')[-1]
                param_full_type = '.'.join(full_type_param.split('.')[:-1])
                param_class_code = new_inst_same_dir_classes.get(param_short_name, None)
                param_method_declares = []
                if param_class_code:
                    param_methods = parse_methods_from_class_node(param_class_code)
                    for method in param_methods:
                        param_method_declares.append(get_method_declaration(method['method_text']))
                full_param_name = f"{param_full_type}#{param_short_name}"
                if param_method_declares:
                    new_source_data_inst[parameter_classes_key].append(f"{full_param_name} | {' | '.join(param_method_declares)}")
                else:
                    new_source_data_inst[parameter_classes_key].append(full_param_name)

            new_source_data_inst[source_class_imports_key] = parse_import_stmts_from_file_code(new_inst_file_code)

            # confirm if method is invoked in any of the triggered tests
            trigger_test_class = set()
            trigger_test_function = {}
            test_dir = buggy_fix_info["properties"]["test.dir"]
            focal_method_invoked = False
            for trigger_test in buggy_fix_info['trigger_tests']:
                trigger_test_class.add(trigger_test['test_class'])
                if trigger_test['test_class'] not in trigger_test_function:
                    trigger_test_function[trigger_test['test_class']] = [trigger_test['test_function']]
                else:
                    trigger_test_function[trigger_test['test_class']].append(trigger_test['test_function'])
            for test_class in trigger_test_class:
                test_class_dir = test_class.replace('.', '/')
                full_test_class_dir = os.path.join(proj_base_dir, bug_name, version, test_dir, test_class_dir+'.java')
                full_test_class_dir_bak = os.path.join(proj_base_dir, bug_name, version, test_dir, test_class_dir+'.java.bak')
                try:
                    with open(full_test_class_dir, 'r', encoding='utf-8', errors='replace') as f:
                        test_content = f.read()
                except FileNotFoundError:
                    try:
                        with open(full_test_class_dir_bak, 'r', encoding='utf-8', errors='replace') as f:
                            test_content = f.read()
                    except FileNotFoundError:
                        print(f"Test file not found: {full_test_class_dir} and {full_test_class_dir_bak}")
                        continue

                invoked_methods = []
                for test_function in trigger_test_function[test_class]:
                    invoked_methods.extend(check_invocation(parse_classes_from_code(test_content), test_function))
                if new_inst_method_info['method_name'] in invoked_methods:
                    focal_method_invoked = True
                    break
            new_source_data_inst['focal_method_invoked'] = focal_method_invoked

            # collect all test cases that invoked our focal method in the triggered test classes
            invoking_test_cases = []
            invoking_test_cases_text = set()
            for test_class in trigger_test_class:
                test_class_dir = test_class.replace('.', '/')
                full_test_class_dir = os.path.join(proj_base_dir, bug_name, version, test_dir, test_class_dir+'.java')
                full_test_class_dir_bak = os.path.join(proj_base_dir, bug_name, version, test_dir, test_class_dir+'.java.bak')
                try:
                    with open(full_test_class_dir, 'r', encoding='utf-8', errors='replace') as f:
                        test_content = f.read()
                except FileNotFoundError:
                    try:
                        with open(full_test_class_dir_bak, 'r', encoding='utf-8', errors='replace') as f:
                            test_content = f.read()
                    except FileNotFoundError:
                        print(f"Test file not found: {full_test_class_dir} and {full_test_class_dir_bak}")
                        continue
                for invoking in find_invoking_tests(parse_classes_from_code(test_content), new_inst_method_info['method_name']):
                    if invoking['method_text'] not in invoking_test_cases_text:
                        invoking_test_cases_text.add(invoking['method_text'])
                        invoking_test_cases.append(invoking)
            new_source_data_inst['invoking_test_cases'] = invoking_test_cases

            new_source_data_inst['triggered_test_functions'] = trigger_test_function

            new_source_data.append(new_source_data_inst)



# ---- override after cell 77
# subset150: cell 78 would overwrite data/prompts/{version}_source_data_draft.jsonl (the 78-method dataset's file);
# write the same records to S150_OUT instead. Cells 79-86 only reload/print/filter (the invoked filter is unify's job here).
with open(os.environ['S150_OUT'], 'w') as f:
    for new_source_data_inst in new_source_data:
        f.write(json.dumps(new_source_data_inst) + '\n')
print(len(new_source_data), 'records ->', os.environ['S150_OUT'], '| failed:', failed_bugs)

