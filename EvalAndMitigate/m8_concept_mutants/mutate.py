"""m8 mutate: deterministic first-order mutants of each focal method (tree-sitter Java, no LLM).

Two operator sets, applied to the focal method of the BUGGY checkout (the source file is read, never written):
  concept  = the C1-C8 catalogue (shared vocabulary of run/METHODS_BRIEF.md), 2-5 operators per concept (OPS below)
  generic  = PIT-default-style control operators unrelated to the catalogue (negate conditionals, math, return values,
             void-call removal, increments, invert negatives); no conditionals-boundary (that is C3)
Each mutant is one edit inside the focal method; applied to the file it is a full replacement of the focal method.
Mutants are deduplicated per arm by the mutated method text; generic mutants whose text equals a concept mutant are
dropped (overlap reported). At most MAX_CAND candidates per method and arm are kept (stratified round robin over
operators, seeded); phase0.py compiles them and equalises the compiled count per method between the arms.

usage (container, needs the d4jproj volume):  python3 m8_concept_mutants/mutate.py      -> out/mutants.jsonl
                                              python3 m8_concept_mutants/mutate.py selftest
"""
import hashlib, json, os, random, re, sys
from collections import Counter, defaultdict

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO]
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
EVIDENCE = f"{REPO}/m6_agent_oracle/out/evidence.jsonl"
OUT = os.environ.get("M8_OUT") or f"{REPO}/m8_concept_mutants/out"  # dock8.sh: /m8out (top-level mount)
MAX_CAND = 80
SEED = 8

PRIM_INT = {"int", "long", "short", "byte"}
PRIM = PRIM_INT | {"boolean", "char", "float", "double"}
STRINGY = {"String", "CharSequence", "StringBuffer", "StringBuilder"}
COLL = re.compile(r"^(java\.util\.)?(Collection|List|ArrayList|Set|HashSet|Map|HashMap|LinkedList|TreeSet|TreeMap)\b")

_P = None


def parser():
    global _P
    if _P is None:
        from data.configuration import JAVA_LANGUAGE
        from tree_sitter import Parser
        _P = Parser(); _P.set_language(JAVA_LANGUAGE)
    return _P


def walk(n):
    st = [n]
    while st:
        x = st.pop()
        yield x
        st.extend(reversed(x.children))


T = lambda n: n.text.decode("utf-8", "replace")
norm = lambda s: re.sub(r"\s+", " ", s).strip()


def defaults(ret):
    """default return statements for an inserted guard / a replaced throw, by return type text."""
    r = ret.split("<")[0].strip()
    if r == "void":
        return ["return;"]
    if r == "boolean":
        return ["return false;", "return true;"]
    if r in PRIM_INT:
        return ["return 0;", "return -1;"]
    if r in ("float", "double"):
        return ["return 0;"]
    if r == "char":
        return ["return (char) 0;"]
    if r in STRINGY:
        return ["return null;", 'return "";']
    return ["return null;"]


class Ctx:
    def __init__(self, src, node, fields):
        self.src, self.node = src, node
        self.body = node.child_by_field_name("body")
        t = node.child_by_field_name("type")
        self.ret = T(t) if t is not None else "void"  # constructor: plain `return;`
        self.params = []
        for p in node.child_by_field_name("parameters").children:
            if p.type in ("formal_parameter", "spread_parameter"):
                name = p.child_by_field_name("name") or [c for c in p.children if c.type in ("identifier", "variable_declarator")][-1]
                ptype = T(p.child_by_field_name("type") or p.children[0])
                if p.type == "spread_parameter":
                    ptype += "[]"
                    name = name.child_by_field_name("name") if name.type == "variable_declarator" else name
                self.params.append((T(name), ptype.replace("final ", "").strip()))
        self.locals = {T(d.child_by_field_name("name")) for d in walk(self.body) if d.type == "variable_declarator"} | {p for p, _ in self.params}
        self.field_types = fields  # name -> declared type
        self.fields = set(fields) - self.locals
        self.nodes = list(walk(self.body))
        # insertion point for guards: after `{`, or after an explicit this(...)/super(...) call
        first = [c for c in self.body.children if c.is_named and c.type not in ("line_comment", "block_comment")]
        self.ins = first[0].end_byte if first and first[0].type == "explicit_constructor_invocation" else self.body.start_byte + 1


def E(n_or_s, e, repl, op, desc):
    s = n_or_s if isinstance(n_or_s, int) else n_or_s.start_byte
    return (s, e, repl, op, desc)


def rep(n, repl, op, desc=None):
    return (n.start_byte, n.end_byte, repl, op, desc or f"{T(n)[:60]} -> {repl[:60]}")


def op_tok(n):
    return n.child_by_field_name("operator")


def is_lit(n, *types):
    return n is not None and n.type in types


def call_name(n):
    return T(n.child_by_field_name("name")) if n.type == "method_invocation" else None


def args(n):
    a = n.child_by_field_name("arguments")
    return [c for c in a.children if c.is_named and c.type not in ("line_comment", "block_comment")] if a is not None else []


def stmt_ok(n):
    """an expression statement directly inside a block (deleting / swapping it keeps the code well-formed)."""
    return n.type == "expression_statement" and n.parent is not None and n.parent.type in ("block", "switch_block_statement_group", "constructor_body")


# ------------------------------------------------------------------ concept operators (C1-C8)
def c1(c):
    out = []
    for n in c.nodes:
        if n.type == "binary_expression" and T(op_tok(n)) in ("==", "!=") and any(is_lit(n.child_by_field_name(k), "null_literal") for k in ("left", "right")):
            o = op_tok(n)
            out.append(rep(o, "!=" if T(o) == "==" else "==", "C1_swap_null_cmp", f"{norm(T(n))[:60]}: swap == null / != null"))
            out.append(rep(n, "false" if T(o) == "==" else "true", "C1_drop_null_check", f"{norm(T(n))[:60]} -> no null check"))
        if n.type == "return_statement" and len(n.named_children) == 1 and n.named_children[0].type == "null_literal":
            r = c.ret.split("<")[0].strip()
            d = '""' if r in ("String", "CharSequence") else "Boolean.FALSE" if r == "Boolean" else f"new {r[:-2]}[0]" if r.endswith("[]") else \
                {"List": "java.util.Collections.emptyList()", "Set": "java.util.Collections.emptySet()", "Map": "java.util.Collections.emptyMap()"}.get(r)
            if d:
                out.append(rep(n, f"return {d};", "C1_null_to_default"))
        if n.type == "return_statement" and len(n.named_children) == 1 and T(n.named_children[0]) == '""':
            out.append(rep(n, "return null;", "C1_null_to_default", 'return "" -> return null'))
        if n.type == "method_invocation" and n.child_by_field_name("object") is not None and T(n.child_by_field_name("object")) not in ("this", "super"):
            obj, a = T(n.child_by_field_name("object")), args(n)
            if call_name(n) == "toString" and not a:
                out.append(rep(n, f"String.valueOf({obj})", "C1_null_safe_deref"))
            if call_name(n) == "equals" and len(a) == 1:
                out.append(rep(n, f"java.util.Objects.equals({obj}, {T(a[0])})", "C1_null_safe_deref"))
    # reference-typed fields the method reads (declared type from the dataset's field list) count like parameters
    used = {T(x) for x in c.nodes if x.type == "identifier"} | {T(x.child_by_field_name("field")) for x in c.nodes
                                                                if x.type == "field_access" and T(x.child_by_field_name("object")) == "this"}
    refs = [(p, t) for p, t in c.params] + [(f, t) for f, t in sorted(c.field_types.items()) if f in used and f in c.fields]
    for p, t in refs:
        if t not in PRIM:
            for d in defaults(c.ret):
                out.append(E(c.ins, c.ins, f" if ({p} == null) {{ {d} }}", "C1_insert_null_guard", f"insert: if ({p} == null) {d}"))
            out.append(E(c.ins, c.ins, f' if ({p} == null) {{ throw new IllegalArgumentException("{p}"); }}', "C1_insert_null_guard",
                         f"insert: if ({p} == null) throw IllegalArgumentException"))
    return out


def len_expr(n):
    """x.length() / x.size() / x.length"""
    return (n.type == "method_invocation" and call_name(n) in ("length", "size") and not args(n) and n.child_by_field_name("object") is not None) or \
           (n.type == "field_access" and T(n.child_by_field_name("field")) == "length")


def c2(c):
    out = []
    for n in c.nodes:
        name = call_name(n)
        if name in ("isEmpty", "isBlank", "isNotEmpty", "isNotBlank"):
            out.append(rep(n, "true" if "Not" in name else "false", "C2_drop_empty_check"))
            swap = {"isEmpty": "isBlank", "isBlank": "isEmpty", "isNotEmpty": "isNotBlank", "isNotBlank": "isNotEmpty"}[name]
            if n.child_by_field_name("object") is None or args(n):  # static StringUtils-style call
                out.append(rep(n.child_by_field_name("name"), swap, "C2_empty_blank_swap", f"{norm(T(n))[:60]}: {name} -> {swap}"))
            elif name == "isEmpty":  # x.isEmpty() -> x.trim().isEmpty() (blank counts as empty; String receivers only)
                o = n.child_by_field_name("object")
                out.append(E(o.end_byte, o.end_byte, ".trim()", "C2_empty_blank_swap", f"{norm(T(n))[:60]}: blank counts as empty"))
        if n.type == "binary_expression" and T(op_tok(n)) in ("==", "!=", "<", "<=", ">", ">="):
            l, r = n.child_by_field_name("left"), n.child_by_field_name("right")
            for a, b, flip in ((l, r, False), (r, l, True)):
                if len_expr(a) and b.type == "decimal_integer_literal" and T(b) in ("0", "1"):
                    o, k = T(op_tok(n)), int(T(b))
                    if flip:
                        o = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}.get(o, o)
                    v = eval(f"5 {o} {k}")  # value when the operand is never empty
                    out.append(rep(n, "true" if v else "false", "C2_drop_empty_check"))
                    if a.type == "method_invocation" and call_name(a) == "length":
                        ob = a.child_by_field_name("object")
                        out.append(E(ob.end_byte, ob.end_byte, ".trim()", "C2_empty_blank_swap", f"{norm(T(n))[:60]}: blank counts as empty"))
    for p, t in c.params:
        base = t.split("<")[0].strip()
        emp = f"{p}.length == 0" if t.endswith("[]") else f"{p}.length() == 0" if base in STRINGY else f"{p}.isEmpty()" if COLL.match(base) else None
        if emp:
            ds = defaults(c.ret) + ([f"return {p};"] if t == c.ret else [])
            for d in ds:
                out.append(E(c.ins, c.ins, f" if ({p} != null && {emp}) {{ {d} }}", "C2_insert_empty_guard", f"insert: if ({emp}) {d}"))
    return out


IDX_CALLS = {"charAt": [0], "codePointAt": [0], "codePointBefore": [0], "substring": [0, 1], "subSequence": [0, 1],
             "deleteCharAt": [0], "setCharAt": [0], "subList": [0, 1], "get": [0], "insert": [0], "delete": [0, 1]}


def c3(c):
    out = []
    in_loop_cond = set()
    for n in c.nodes:
        if n.type in ("for_statement", "while_statement", "do_statement") and n.child_by_field_name("condition") is not None:
            in_loop_cond |= {x.id for x in walk(n.child_by_field_name("condition"))}
    for n in c.nodes:
        if n.type == "binary_expression" and T(op_tok(n)) in ("<", "<=", ">", ">="):
            o = op_tok(n)
            out.append(rep(o, {"<": "<=", "<=": "<", ">": ">=", ">=": ">"}[T(o)], "C3_rel_boundary", f"{norm(T(n))[:60]}: {T(o)} boundary"))
            if n.id in in_loop_cond:
                r = n.child_by_field_name("right")
                for d in ("+ 1", "- 1"):
                    out.append(rep(r, f"({T(r)} {d})", "C3_loop_bound_pm1", f"loop bound {norm(T(n))[:60]}: right {d}"))
        if n.type == "binary_expression" and T(op_tok(n)) in ("<", "<=", ">", ">=", "==", "!="):
            for k in ("left", "right"):
                x = n.child_by_field_name(k)
                if x.type == "decimal_integer_literal" and T(x).isdigit():
                    for d in (1, -1):
                        out.append(rep(x, str(int(T(x)) + d), "C3_const_pm1", f"{norm(T(n))[:60]}: {T(x)} -> {int(T(x)) + d}"))
        if len_expr(n) and not (n.parent.type == "assignment_expression" and n.parent.child_by_field_name("left") == n):
            for d in ("+ 1", "- 1"):
                out.append(rep(n, f"({T(n)} {d})", "C3_len_pm1"))
        idx = []
        if n.type == "array_access":
            idx = [n.child_by_field_name("index")]
        elif call_name(n) in IDX_CALLS and n.child_by_field_name("object") is not None:
            a = args(n)
            idx = [a[i] for i in IDX_CALLS[call_name(n)] if i < len(a) and a[i].type not in ("string_literal", "character_literal")]
        for x in idx:
            if not (n.type == "array_access" and n.parent.type in ("assignment_expression", "update_expression") and n.parent.children[0] == n):
                for d in ("+ 1", "- 1"):
                    out.append(rep(x, f"({T(x)} {d})", "C3_index_pm1", f"{norm(T(n))[:60]}: index {d}"))
    return out


UNCHECKED = {"NumberFormatException", "IllegalArgumentException", "IndexOutOfBoundsException", "StringIndexOutOfBoundsException",
             "ArrayIndexOutOfBoundsException", "NullPointerException", "ClassCastException", "ArithmeticException", "IllegalStateException",
             "UnsupportedOperationException", "NoSuchElementException", "ConcurrentModificationException"}
WIDEN = {"NumberFormatException": "IllegalArgumentException", "StringIndexOutOfBoundsException": "IndexOutOfBoundsException",
         "ArrayIndexOutOfBoundsException": "IndexOutOfBoundsException"}
NARROW = {"Throwable": "Exception", "Exception": "RuntimeException", "RuntimeException": "IllegalArgumentException",
          "IllegalArgumentException": "NumberFormatException", "IndexOutOfBoundsException": "StringIndexOutOfBoundsException"}
THROW_ALT = {"IllegalArgumentException": ["NullPointerException", "IllegalStateException"]}


def c4(c):
    out = []
    for n in c.nodes:
        if n.type == "throw_statement":
            out.append(rep(n, defaults(c.ret)[0], "C4_throw_to_return"))
            x = n.named_children[0] if n.named_children else None
            if x is not None and x.type == "object_creation_expression":
                t = x.child_by_field_name("type")
                name = T(t).split(".")[-1]
                for alt in THROW_ALT.get(name, ["IllegalArgumentException"] if name != "IllegalArgumentException" else []):
                    out.append(rep(t, alt, "C4_exception_type", f"throw new {name} -> {alt}"))
        if n.type == "return_statement" and len(n.named_children) == 1:
            v = n.named_children[0]
            lit = v.type in ("null_literal", "true", "false", "decimal_integer_literal") or T(v) in ('""', "-1") or \
                (v.type == "unary_expression" and v.named_children[0].type == "decimal_integer_literal")
            if lit:
                out.append(rep(n, "throw new IllegalArgumentException();", "C4_return_to_throw"))
        if n.type == "catch_clause":
            p = [x for x in n.children if x.type == "catch_formal_parameter"][0]
            ct = [x for x in p.children if x.type == "catch_type"][0]
            types = [x for x in ct.named_children]
            if len(types) == 1:
                name = T(types[0]).split(".")[-1]
                w = WIDEN.get(name, "RuntimeException" if name in UNCHECKED else "Exception")
                if w != name and name not in ("Throwable", "Exception"):
                    out.append(rep(types[0], w, "C4_catch_widen", f"catch {name} -> {w}"))
                if name in NARROW:
                    out.append(rep(types[0], NARROW[name], "C4_catch_narrow", f"catch {name} -> {NARROW[name]}"))
            else:  # multi-catch A | B: drop one alternative
                for t in types:
                    rest = " | ".join(T(x) for x in types if x != t)
                    out.append(rep(ct, rest, "C4_catch_narrow", f"multi-catch without {T(t)}"))
            tr = n.parent
            catches = [x for x in tr.children if x.type == "catch_clause"]
            if tr.type == "try_statement":
                if len(catches) > 1 or any(x.type == "finally_clause" for x in tr.children):
                    out.append(rep(n, "", "C4_remove_catch", f"remove catch ({norm(T(p))})"))
                else:
                    out.append(rep(tr, T(tr.child_by_field_name("body")), "C4_remove_catch", f"remove try/catch ({norm(T(p))})"))
    for p, t in c.params:
        if t in PRIM_INT:
            out.append(E(c.ins, c.ins, f' if ({p} < 0) {{ throw new IllegalArgumentException("{p}"); }}', "C4_insert_range_check",
                         f"insert: if ({p} < 0) throw IllegalArgumentException"))
    return out


TRANSFORMS = ("replace", "replaceAll", "replaceFirst", "replaceChars", "replaceEach", "trim", "strip")


def c5(c):
    out = []
    for n in c.nodes:
        if n.type == "switch_block_statement_group":
            labels = [x for x in n.children if x.type == "switch_label"]
            if any(y.type in ("character_literal", "string_literal") for l in labels for y in walk(l)):
                out.append(rep(n, "", "C5_drop_case", f"drop switch case {norm(' '.join(T(l) for l in labels))[:60]}"))
                stm = [x for x in n.named_children if x.type != "switch_label"]
                if stm and stm[-1].type == "break_statement" and n.next_named_sibling is not None:
                    out.append(rep(stm[-1], "", "C5_case_fallthrough", f"case {norm(T(labels[0]))[:40]} falls through"))
        if n.type == "binary_expression" and T(op_tok(n)) in ("==", "!=") and any(
                is_lit(n.child_by_field_name(k), "character_literal") for k in ("left", "right")):
            out.append(rep(n, "false" if T(op_tok(n)) == "==" else "true", "C5_drop_char_branch"))
        name = call_name(n)
        if name in ("equals", "equalsIgnoreCase", "startsWith", "endsWith") and len(args(n)) == 1 and args(n)[0].type in ("string_literal", "character_literal"):
            out.append(rep(n, "false", "C5_drop_char_branch"))
        if name in TRANSFORMS and n.child_by_field_name("object") is not None:
            out.append(rep(n, T(n.child_by_field_name("object")), "C5_drop_transform"))
        elif name and ("escape" in name.lower() or name in TRANSFORMS) and n.child_by_field_name("object") is not None and args(n) and \
                n.parent.type != "expression_statement":
            out.append(rep(n, T(args(n)[0]), "C5_drop_transform"))
    return out


def c6(c):
    out = []
    for n in c.nodes:
        if n.type == "local_variable_declaration":
            t = n.child_by_field_name("type")
            if T(t) in ("int", "long"):
                out.append(rep(t, "long" if T(t) == "int" else "int", "C6_int_long", f"{norm(T(n))[:60]}: {T(t)} local"))
        if n.type == "cast_expression":
            t = n.child_by_field_name("type")
            alt = {"int": "long", "long": "int", "float": "double", "double": "float"}.get(T(t))
            if alt:
                out.append(rep(t, alt, "C6_int_long", f"cast ({T(t)}) -> ({alt})"))
        if n.type == "binary_expression" and T(op_tok(n)) in ("+", "-", "*"):
            l, r = n.child_by_field_name("left"), n.child_by_field_name("right")
            if not any(x.type in ("string_literal", "character_literal") for x in (l, r)):
                f = {"+": "addExact", "-": "subtractExact", "*": "multiplyExact"}[T(op_tok(n))]
                out.append(rep(n, f"Math.{f}({T(l)}, {T(r)})", "C6_overflow_guard"))
        if n.type == "binary_expression" and T(op_tok(n)) in ("/", "%"):
            l, r = n.child_by_field_name("left"), n.child_by_field_name("right")
            if T(op_tok(n)) == "/":
                out.append(rep(n, f"(({T(l)}) + ({T(r)}) - 1) / ({T(r)})", "C6_rounding", f"{norm(T(n))[:60]}: ceiling division"))
            else:
                out.append(rep(n, f"Math.floorMod({T(l)}, {T(r)})", "C6_rounding"))
        name = call_name(n)
        o = n.child_by_field_name("object") if n.type == "method_invocation" else None
        if o is not None and T(o) == "Math" and name in ("floor", "ceil", "round", "rint"):
            for alt in {"floor": ["ceil"], "ceil": ["floor"], "round": ["floor", "ceil"], "rint": ["floor"]}[name]:
                out.append(rep(n.child_by_field_name("name"), alt, "C6_rounding", f"Math.{name} -> Math.{alt}"))
        if o is not None and T(o) in ("Double", "Float") and name in ("isNaN", "isInfinite"):
            out.append(rep(n, "false", "C6_special_values"))
    for p, t in c.params:
        if t in ("double", "float", "Double", "Float", "Number"):
            v = f"{p}.doubleValue()" if t in ("Double", "Float", "Number") else p
            g = f"{p} != null && " if t[0].isupper() else ""
            out.append(E(c.ins, c.ins, f' if ({g}(Double.isNaN({v}) || Double.isInfinite({v}))) {{ throw new IllegalArgumentException("{p}"); }}',
                         "C6_special_values", f"insert: reject NaN/infinite {p}"))
    return out


CHAR_PRED = {"isLetter": ["isLetterOrDigit", "isAlphabetic"], "isDigit": ["isLetterOrDigit"], "isLetterOrDigit": ["isLetter", "isDigit"],
             "isWhitespace": ["isSpaceChar"], "isSpaceChar": ["isWhitespace"], "isUpperCase": ["isLowerCase"], "isLowerCase": ["isUpperCase"],
             "isJavaIdentifierStart": ["isJavaIdentifierPart"], "isJavaIdentifierPart": ["isJavaIdentifierStart"],
             "isHighSurrogate": ["isLowSurrogate"], "isLowSurrogate": ["isHighSurrogate"], "isAlphabetic": ["isLetter"],
             "isISOControl": ["isWhitespace"], "isDefined": ["isLetterOrDigit"]}


def c7(c):
    out = []
    for n in c.nodes:
        name = call_name(n)
        if not name:
            continue
        o = n.child_by_field_name("object")
        a, nm = args(n), n.child_by_field_name("name")
        if name in ("toUpperCase", "toLowerCase") and o is not None and T(o) != "Character":
            if not a:
                out.append(rep(n.child_by_field_name("arguments"), "(java.util.Locale.ROOT)", "C7_add_locale"))
                out.append(rep(n, T(o), "C7_case_fold", f"drop .{name}()"))
            else:
                out.append(rep(n.child_by_field_name("arguments"), "()", "C7_remove_locale"))
            out.append(rep(nm, "toLowerCase" if name == "toUpperCase" else "toUpperCase", "C7_case_fold"))
        if name == "format" and o is not None and T(o) == "String" and a and "ocale" not in T(a[0]):
            out.append(E(a[0].start_byte, a[0].start_byte, "java.util.Locale.ROOT, ", "C7_add_locale", "String.format with Locale.ROOT"))
        if len(a) >= 2 and name not in ("toUpperCase", "toLowerCase"):
            for x in a:
                if re.search(r"(?i)locale", T(x)):
                    k = a.index(x)
                    s, e = (a[k - 1].end_byte, x.end_byte) if k else (x.start_byte, a[1].start_byte)
                    out.append(E(s, e, "", "C7_remove_locale", f"{name}(...) without argument {T(x)[:30]}"))
        if o is not None and T(o) == "Character":
            for alt in CHAR_PRED.get(name, []):
                out.append(rep(nm, alt, "C7_swap_char_pred", f"Character.{name} -> {alt}"))
            if name in ("toUpperCase", "toLowerCase"):
                out.append(rep(nm, "toLowerCase" if name == "toUpperCase" else "toUpperCase", "C7_case_fold", f"Character.{name} swapped"))
            if name in ("isHighSurrogate", "isLowSurrogate", "isSurrogate", "isSupplementaryCodePoint"):
                out.append(rep(n, "false", "C7_surrogate"))
            if name == "charCount":
                out.append(rep(n, "1", "C7_surrogate"))
        if name in ("equals", "equalsIgnoreCase", "compareTo", "compareToIgnoreCase") and o is not None and len(a) == 1:
            alt = {"equals": "equalsIgnoreCase", "equalsIgnoreCase": "equals", "compareTo": "compareToIgnoreCase", "compareToIgnoreCase": "compareTo"}[name]
            out.append(rep(nm, alt, "C7_case_fold"))
        if name == "regionMatches" and a and a[0].type in ("true", "false"):
            out.append(rep(a[0], "false" if a[0].type == "true" else "true", "C7_case_fold", "regionMatches ignoreCase flipped"))
        if name == "codePointAt" and o is not None and len(a) == 1:
            out.append(rep(nm, "charAt", "C7_surrogate", "codePointAt -> charAt"))
    return out


def c8(c):
    out = []
    def mutates_state(st):
        x = st.named_children[0] if st.named_children else None
        if x is None:
            return False
        if x.type in ("assignment_expression", "update_expression"):
            lhs = x.child_by_field_name("left") if x.type == "assignment_expression" else x.named_children[0]
            return (lhs.type == "field_access" and T(lhs.child_by_field_name("object")) == "this") or (lhs.type == "identifier" and T(lhs) in c.fields) \
                or (lhs.type == "array_access" and T(lhs.child_by_field_name("array")) in c.fields)
        if x.type == "method_invocation" and x.child_by_field_name("object") is not None:
            ob = T(x.child_by_field_name("object"))
            return ob in c.fields or ob.startswith("this.")
        return False
    for n in c.nodes:
        if stmt_ok(n) and mutates_state(n):
            out.append(rep(n, ";", "C8_skip_state_update", f"skip: {norm(T(n))[:60]}"))
            out.append(E(n.end_byte, n.end_byte, " " + T(n), "C8_repeat_state_update", f"repeat: {norm(T(n))[:60]}"))
        if stmt_ok(n):
            nx = n.next_named_sibling
            if nx is not None and stmt_ok(nx) and T(n) != T(nx):
                out.append((n.start_byte, nx.end_byte, T(nx) + " " + T(n), "C8_reorder", f"swap: {norm(T(n))[:40]} <-> {norm(T(nx))[:40]}"))
    return out


# ------------------------------------------------------------------ generic control operators (PIT-default style)
NEG = {"==": "!=", "!=": "==", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}
MATH = {"+": "-", "-": "+", "*": "/", "/": "*", "%": "*", "&": "|", "|": "&", "^": "&", "<<": ">>", ">>": "<<", ">>>": "<<"}
CMATH = {"+=": "-=", "-=": "+=", "*=": "/=", "/=": "*=", "|=": "&=", "&=": "|=", "<<=": ">>=", ">>=": "<<="}


def generic(c):
    out = []
    for n in c.nodes:
        if n.type == "binary_expression":
            o = T(op_tok(n))
            if o in NEG:
                out.append(rep(op_tok(n), NEG[o], "G_negate_cond", f"{norm(T(n))[:60]}: {o} -> {NEG[o]}"))
            if o in MATH and not any(x.type in ("string_literal", "character_literal") for x in (n.child_by_field_name("left"), n.child_by_field_name("right"))):
                out.append(rep(op_tok(n), MATH[o], "G_math", f"{norm(T(n))[:60]}: {o} -> {MATH[o]}"))
        if n.type in ("if_statement", "while_statement"):
            cond = n.child_by_field_name("condition")
            inner = cond.named_children[0] if cond.named_children else None
            if inner is not None and not (inner.type == "binary_expression" and T(op_tok(inner)) in NEG):
                out.append(rep(cond, f"(!{T(cond)})", "G_negate_cond", f"negate condition {norm(T(cond))[:60]}"))
        if n.type == "assignment_expression" and T(op_tok(n)) in CMATH:
            out.append(rep(op_tok(n), CMATH[T(op_tok(n))], "G_math", f"{norm(T(n))[:60]}: compound op"))
        if n.type == "return_statement" and n.named_children:
            v, r = n.named_children[0], c.ret.split("<")[0].strip()
            if r == "boolean":
                out.append(rep(v, f"!({T(v)})", "G_return_vals"))
            elif r in PRIM_INT | {"double", "float"}:
                out.append(rep(v, f"(({T(v)}) == 0 ? 1 : 0)", "G_return_vals"))
            elif r not in PRIM:
                out.append(rep(n, "throw new RuntimeException();" if v.type == "null_literal" else "return null;", "G_return_vals"))
        if stmt_ok(n) and n.named_children and n.named_children[0].type == "method_invocation":
            out.append(rep(n, ";", "G_void_call", f"remove call: {norm(T(n))[:60]}"))
        if n.type == "update_expression":
            t = T(n)
            out.append(rep(n, t.replace("++", "--") if "++" in t else t.replace("--", "++"), "G_increments"))
        if n.type == "unary_expression" and T(op_tok(n)) == "-" and n.named_children[0].type not in (
                "decimal_integer_literal", "decimal_floating_point_literal", "hex_integer_literal"):
            out.append(rep(n, T(n.named_children[0]), "G_invert_negs"))
        # PIT's non-default but standard operators, so that the generic pool is not smaller than the concept pool
        if n.type in ("if_statement", "while_statement"):
            cond = n.child_by_field_name("condition")
            for v in ("true", "false"):
                out.append(rep(cond, f"({v})", "G_remove_conditionals", f"condition {norm(T(cond))[:60]} -> {v}"))
        if n.type == "method_invocation" and n.parent.type != "expression_statement":
            o, a = n.child_by_field_name("object"), args(n)
            for v in ("null", "0", "false"):  # NON_VOID_METHOD_CALLS: result -> default (the compiler keeps the well-typed one)
                out.append(rep(n, v, "G_non_void_call", f"{norm(T(n))[:60]} -> {v}"))
            if o is not None and o.type != "type_identifier" and not T(o)[:1].isupper():
                out.append(rep(n, T(o), "G_naked_receiver"))
            for x in a[:3]:
                out.append(rep(n, T(x), "G_arg_propagation", f"{norm(T(n))[:60]} -> argument {T(x)[:30]}"))
        if n.type == "object_creation_expression" and n.parent.type != "throw_statement":
            out.append(rep(n, "null", "G_constructor_call"))
        if n.type in ("decimal_integer_literal", "true", "false") and not (n.parent.type == "binary_expression" and T(op_tok(n.parent)) in NEG) \
                and n.parent.type not in ("switch_label", "array_access", "unary_expression"):
            v = {"true": "false", "false": "true"}.get(T(n)) or ("1" if T(n) == "0" else "0" if T(n) == "1" else str(int(T(n).rstrip("lL")) + 1) if T(n).rstrip("lL").isdigit() else None)
            if v is not None:
                out.append(rep(n, v, "G_inline_consts"))
    return out


CONCEPT_OPS = {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5, "C6": c6, "C7": c7, "C8": c8}


# ------------------------------------------------------------------ apply, dedupe, sample
def find_method(tree_root, src, record):
    want = norm(record["source:source_method_code_format"])
    hits = [n for n in walk(tree_root) if n.type in ("method_declaration", "constructor_declaration")
            and T(n.child_by_field_name("name")) == record["source:source_method_name"] and norm(T(n)) == want]
    assert len(hits) == 1, (record["extra:project_name"], record["source:source_method_name"], len(hits))
    return hits[0]


MODS = {"private", "public", "protected", "static", "final", "transient", "volatile"}


def field_names(record):
    """{field name: declared type} from the dataset's field declarations (static fields included)."""
    out = {}
    for f in record.get("source_class_fields") or []:
        m = re.match(r"^([^=;(]*?)([A-Za-z_$][\w$]*)\s*(=|;|$)", f.strip())
        if m:
            out[m.group(2)] = " ".join(w for w in m.group(1).split() if w not in MODS) or "?"
    return out


def stratified(items, key, n, rng):
    """round robin over key groups (each group shuffled), first n items."""
    groups = defaultdict(list)
    for x in items:
        groups[key(x)].append(x)
    for g in groups.values():
        rng.shuffle(g)
    order, ks = [], sorted(groups)
    while any(groups[k] for k in ks):
        for k in ks:
            if groups[k]:
                order.append(groups[k].pop(0))
    return order[:n]


def mutants_for(src, node, record):
    c = Ctx(src, node, field_names(record))
    ms, me = node.start_byte, node.end_byte
    orig = src[ms:me]
    out = {"concept": [], "generic": []}
    seen = {hashlib.md5(norm(orig.decode("utf-8", "replace")).encode()).hexdigest()}
    for arm, gens in (("concept", list(CONCEPT_OPS.items())), ("generic", [("G", generic)])):
        for concept, f in gens:
            for s, e, repl, op, desc in f(c):
                assert ms <= s <= e <= me, (op, s, e, ms, me)
                text = (src[ms:s] + repl.encode() + src[e:me]).decode("utf-8", "replace")
                h = hashlib.md5(norm(text).encode()).hexdigest()
                if h in seen:  # identical to the original, to an earlier mutant, or (generic) to a concept mutant
                    continue
                seen.add(h)
                out[arm].append({"arm": arm, "concept": concept if arm == "concept" else "G", "op": op, "desc": norm(desc or "")[:160],
                                 "s": s, "e": e, "repl": repl, "md5": h})
    return out


def load():
    recs = [json.loads(l) for l in open(SRC)]
    evs = {e["idx"]: e for e in map(json.loads, open(EVIDENCE))}
    return recs, evs


def main():
    recs, evs = load()
    rng = random.Random(SEED)
    stats = defaultdict(Counter)
    with open(f"{OUT}/mutants.jsonl", "w") as f:
        for i, r in enumerate(recs):
            bug = r["extra:project_name"].replace("_buggy", "")
            path = f"{REPO}/d4j_proj_base/{bug}/buggy/{evs[i]['file']}"
            src = open(path, "rb").read()
            node = find_method(parser().parse(src).root_node, src, r)
            allm = mutants_for(src, node, r)
            keep = []
            for arm, ms in allm.items():
                for m in ms:
                    stats[(arm, m["concept"])]["all"] += 1
                # concept arm: round robin over concepts, within a concept over operators; generic: over operators
                if arm == "concept":
                    by_c = defaultdict(list)
                    for m in ms:
                        by_c[m["concept"]].append(m)
                    ms = [m for k in sorted(by_c) for m in stratified(by_c[k], lambda m: m["op"], len(by_c[k]), rng)]
                    rank = {id(m): j for k in by_c for j, m in enumerate(x for x in ms if x["concept"] == k)}
                    sel = sorted(ms, key=lambda m: (rank[id(m)], m["concept"]))[:MAX_CAND]
                else:
                    sel = stratified(ms, lambda m: m["op"], MAX_CAND, rng)
                for k, m in enumerate(sel):
                    keep.append({**m, "mid": f"{i}_{arm[0]}{k}"})
                    stats[(arm, m["concept"])]["kept"] += 1
            f.write(json.dumps({"idx": i, "id": r["extra:project_name"], "bug": bug, "file": evs[i]["file"],
                                "mstart": node.start_byte, "mend": node.end_byte, "src_md5": hashlib.md5(src).hexdigest(),
                                "n_all": {a: len(m) for a, m in allm.items()}, "mutants": keep}) + "\n")
            print(i, bug, r["source:source_method_name"], {a: len(m) for a, m in allm.items()},
                  dict(Counter(m["concept"] for m in keep if m["arm"] == "concept")), flush=True)
    print("\nper concept: candidates (all) / kept (<= MAX_CAND per method and arm)")
    for k in sorted(stats):
        print(k, dict(stats[k]))


def selftest():
    code = b"""class A { int f; String g(String s, int n, Object[] arr) {
      if (s == null) { return null; }
      for (int i = 0; i < n; i++) { if (s.charAt(i) == 'x') { f = i; } }
      try { return s.substring(1).toUpperCase(); } catch (IndexOutOfBoundsException e) { throw new IllegalArgumentException("bad"); }
    } }"""
    root = parser().parse(code).root_node
    node = [n for n in walk(root) if n.type == "method_declaration"][0]
    rec = {"source_class_fields": ["private int f;", "private final Map<String, Integer> m = null;"]}
    ms = mutants_for(code, node, rec)
    ops = Counter(m["op"] for m in ms["concept"])
    gops = Counter(m["op"] for m in ms["generic"])
    for need in ("C1_swap_null_cmp", "C1_drop_null_check", "C1_insert_null_guard", "C1_null_to_default", "C2_insert_empty_guard",
                 "C3_rel_boundary", "C3_loop_bound_pm1", "C3_index_pm1", "C4_throw_to_return", "C4_catch_widen", "C4_remove_catch",
                 "C4_exception_type", "C4_return_to_throw", "C4_insert_range_check", "C5_drop_char_branch", "C7_add_locale", "C7_case_fold",
                 "C8_skip_state_update", "C6_int_long"):
        assert ops[need], (need, ops)
    for need in ("G_negate_cond", "G_increments", "G_return_vals"):
        assert gops[need], (need, gops)
    texts = {(code[:m["s"]] + m["repl"].encode() + code[m["e"]:]).decode() for m in ms["concept"]}
    assert any("if (s != null) { return null; }" in t for t in texts)
    assert any("i <= n" in t for t in texts) and any("catch (RuntimeException e)" in t for t in texts)
    assert not {m["md5"] for m in ms["concept"]} & {m["md5"] for m in ms["generic"]}  # == null -> != null is only in the concept arm
    print("concept", dict(ops), "\ngeneric", dict(gops), "\nselftest ok")


if __name__ == "__main__":
    selftest() if sys.argv[1:] == ["selftest"] else main()
