"""Small C++ source helpers for the gap extractor: comment stripping, balanced scanning, tree-sitter function/class index."""
import re
import tree_sitter as ts
import tree_sitter_cpp

PARSER = ts.Parser(ts.Language(tree_sitter_cpp.language()))


def strip_comments(s):
    """Blank out comments (offsets and newlines kept, string literals untouched)."""
    out, i, n = list(s), 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            i = j + 1
        elif s.startswith("//", i):
            j = s.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = [ch if ch == "\n" else " " for ch in s[i:j]]
            i = j
        else:
            i += 1
    return "".join(out)


def match_close(s, i):
    """s[i] is an opening bracket; return index just past its match (string literals skipped)."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack, n = [], len(s)
    while i < n:
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            i = j + 1
            continue
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            if not stack or stack.pop() != c:
                return i + 1
            if not stack:
                return i + 1
        i += 1
    return n


def split_top(s, sep=","):
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < len(s) and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def calls(s, name_re):
    """Yield (start, name, args_text, end) for calls name(...) in s, where name matches name_re."""
    for m in re.finditer(r"\b(" + name_re + r")\s*(?:<[^<>;(){}]*(?:<[^<>;(){}]*>[^<>;(){}]*)*>)?\s*\(", s):
        o = m.end() - 1
        e = match_close(s, o)
        yield m.start(), m.group(1), s[o + 1:e - 1], e


def _name(node):
    """Declarator name of a function_definition (qualified names kept, e.g. 'Foo<T>::Compute')."""
    d = node.child_by_field_name("declarator")
    while d is not None and d.type not in ("function_declarator",):
        d = d.child_by_field_name("declarator")
    if d is None:
        return None, None
    nm = d.child_by_field_name("declarator")
    params = d.child_by_field_name("parameters")
    return (nm.text.decode(errors="replace") if nm else None), (params.text.decode(errors="replace") if params else "")


def index_file(path, text=None):
    """-> (functions, classes). functions: [{name, params, body, start}] (free and out-of-class definitions);
    classes: {name: {bases: [..], methods: {name: [{params, body, start}]}}}. Bodies are taken from the comment-stripped
    text so byte offsets match strip_comments(file)."""
    src = strip_comments(text if text is not None else open(path, errors="replace").read())
    b = src.encode()
    tree = PARSER.parse(b)
    funcs, classes = [], {}

    def body_of(n):
        bd = n.child_by_field_name("body")
        return (b[bd.start_byte:bd.end_byte].decode(errors="replace"), bd.start_byte) if bd else (None, None)

    def walk(node, cls=None):
        for ch in node.children:
            t = ch.type
            if t in ("class_specifier", "struct_specifier") and ch.child_by_field_name("body") is not None:
                nm = ch.child_by_field_name("name")
                cname = nm.text.decode(errors="replace") if nm else None
                if cname:
                    cname = re.sub(r"<.*", "", cname).strip()
                    bases = []
                    for bc in ch.children:
                        if bc.type == "base_class_clause":
                            for x in bc.children:
                                if x.type in ("type_identifier", "qualified_identifier", "template_type"):
                                    bases.append(re.sub(r"<.*", "", x.text.decode(errors="replace")).split("::")[-1])
                    classes.setdefault(cname, {"bases": bases, "methods": {}, "file": path})
                walk(ch.child_by_field_name("body"), cname)
            elif t == "function_definition":
                name, params = _name(ch)
                body, start = body_of(ch)
                if name and body is not None:
                    short = re.sub(r"<[^<>]*>", "", name)
                    if cls and "::" not in short:
                        classes[cls]["methods"].setdefault(short, []).append({"params": params, "body": body, "start": start})
                    elif "::" in short:  # out-of-class member definition Foo<T>::Compute
                        owner, meth = short.split("::")[-2:]
                        classes.setdefault(owner, {"bases": [], "methods": {}, "file": path})
                        classes[owner]["methods"].setdefault(meth, []).append({"params": params, "body": body, "start": start})
                        funcs.append({"name": meth, "params": params, "body": body, "start": start})
                    else:
                        funcs.append({"name": short, "params": params, "body": body, "start": start})
            elif t in ("template_declaration", "namespace_definition", "declaration_list", "linkage_specification",
                       "preproc_if", "preproc_ifdef", "preproc_else", "preproc_elif", "field_declaration_list", "ERROR",
                       "expression_statement", "declaration"):
                walk(ch, cls)
    walk(tree.root_node)
    # regex supplement: macro-heavy files (ATen) leave tree-sitter ERROR nodes that hide definitions. A definition =
    # a line starting at column 0 with '<type> name(' whose balanced parameter list is followed by '{'.
    seen = {f["start"] for f in funcs} | {d["start"] for c in classes.values() for ds in c["methods"].values() for d in ds}
    for m in re.finditer(r"(?m)^(?:template\s*<[^\n]*>\s*)?(?:(?:static|inline|C10_ALWAYS_INLINE|TORCH_API|constexpr|"
                         r"C10_EXPORT)\s+)*[A-Za-z_][\w:<>,\s*&]*?[\s*&]((?:\w+::)*~?\w+)\s*\(", src):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof", "TORCH_CHECK") or name.isupper():
            continue
        o = m.end() - 1
        e = match_close(src, o)
        k = e
        while k < len(src) and src[k] not in "{;=":
            k += 1
        if k >= len(src) or src[k] != "{" or not re.fullmatch(r"[\s\w:&()<>,]*", src[e:k]) or "->" in src[e:k]:
            continue
        if k in seen:
            continue
        end = match_close(src, k)
        short = re.sub(r"<[^<>]*>", "", name)
        rec = {"name": short.split("::")[-1], "params": src[o:e], "body": src[k:end], "start": k}
        if "::" in short:
            owner = short.split("::")[-2]
            if owner not in ("at", "native", "meta", "detail", "std", "c10", "impl", "tensorflow", "functor", "internal"):
                classes.setdefault(owner, {"bases": [], "methods": {}, "file": path})
                classes[owner]["methods"].setdefault(rec["name"], []).append(rec)
        funcs.append(rec)
    # regex supplement for classes tree-sitter lost inside ERROR nodes: 'class Name : public Base {' + indented methods
    for m in re.finditer(r"(?m)^\s*(?:template\s*<[^;{]*?>\s*)?(?:class|struct)\s+(\w+)(?:\s+final)?\s*:\s*"
                         r"(?:public|protected|private)?\s*([\w:]+)[^;{]*\{", src):
        cname = m.group(1)
        if cname in classes and classes[cname]["methods"]:
            continue
        o = m.end() - 1
        body = src[o:match_close(src, o)]
        info = classes.setdefault(cname, {"bases": [], "methods": {}, "file": path})
        info["bases"] = info["bases"] or [m.group(2).split("::")[-1]]
        for mm in re.finditer(r"(?m)^[ \t]+(?:(?:virtual|static|inline|explicit)\s+)*[\w:<>,*&]+(?:[ \t]+[\w:<>,*&]+)*"
                              r"[ \t*&]+(~?\w+)\s*\(", body):
            mo = mm.end() - 1
            me = match_close(body, mo)
            k = me
            while k < len(body) and body[k] not in "{;=":
                k += 1
            if k >= len(body) or body[k] != "{" or not re.fullmatch(r"[\s\w:&()<>,]*", body[me:k]):
                continue
            info["methods"].setdefault(mm.group(1), []).append(
                {"params": body[mo:me], "body": body[k:match_close(body, k)], "start": o + k})
    return src, funcs, classes


def param_names(params):
    """'(const Tensor& a, OpKernelContext* ctx, int n = 3)' -> ['a', 'ctx', 'n']"""
    out = []
    for p in split_top(params.strip()[1:-1]):
        p = p.split("=")[0].strip()
        m = re.search(r"(\w+)\s*(\[\s*\])?$", p)
        if m and p not in ("void", ""):
            out.append(m.group(1))
    return out
