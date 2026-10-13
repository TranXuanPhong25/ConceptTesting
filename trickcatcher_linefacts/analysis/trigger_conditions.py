"""Trigger inference (CONCEPT_WEAKNESS.md plan rank 3, offline, CPU only, no LLM, no HumanEval+ labels).

Turns each code-level fact ("the True branch of `len(numbers) < 2` is never taken") into an input-level condition
("no existing test passes `numbers` with fewer than 2 elements") using only method-visible material:
PUT source, base-test inputs (tracer.run_base), and the v3m2 fuzz inputs (regenerated with facts.main, same
seed / mined validator out/precond_qwen7b_v2, checked against out/facts_v3m2 witnesses).

  python3 analysis/trigger_conditions.py run [--jobs 8] [--tasks 2 3 ...]   # sandboxed workers + analysis
  python3 analysis/trigger_conditions.py analyze                            # analysis only (worker files exist)
  python3 analysis/trigger_conditions.py worker <task>                      # internal: one task, run in sandbox

Each worker runs as `unshare -rn python3 -I -B ... worker N` (no network) under `timeout`.
Outputs: out/trigger_conditions/{regen,worker}/<task>.json, conditions.json, cases.json, summary.json, summary.txt.

Pre-registered decision rules (fixed before looking at any outcome numbers):
  * feature library: FEATURE FAMILIES below (per parameter, per element, parameter pairs); optional per-fact
    guard feature derived from the source when the branch condition / mutated expression reads only parameters
    that the function never reassigns or mutates.
  * a candidate condition C (1 feature, or a conjunction of 2) must hold for the witness and for no base input.
  * predictive on the regenerated fuzz inputs (all mined-valid, base inputs excluded):
      precision = P(hit | C) >= 0.5  and  (P(hit | not C) == 0  or  precision >= 3 * P(hit | not C)).
  * smallest first: a passing singleton beats any pair; among same size pick max F1, then precision, then
    library order. If nothing passes, the best separating candidate (same order) is kept as "weak".
  * a miss is "explained" when none of Qwen's valid round-1 inputs for that sample satisfies C.
"""
import ast, collections, contextlib, copy, io, inspect, json, math, os, re, string, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../trickcatcher_linefacts/analysis
TL = HERE.parent                                # .../trickcatcher_linefacts
ROOT = TL.parent
OUT = TL / "out/trigger_conditions"
TASKS = TL / "out/gen2_qwen7b_v3m2/tasks.json"
FACTS = TL / "out/facts_v3m2"
PRECOND = TL / "out/precond_qwen7b_v2"
HE = ROOT / "PBT_EdgeCases/run/data/humaneval.jsonl"
CASES = TL / "out/analysis_weak/follow_cases.json"
BUILD_PAGE = TL / "out/analysis_weak/build_page.py"

MIN_PREC, MIN_LIFT = 0.5, 3.0
CAT = {1: "did not try the simple input form", 2: "right direction but off", 3: "only invalid inputs reach",
       4: "needs a specific computed value/combination"}


# ============================================================ feature library (fixed)
def isnum(v):
    return type(v) in (int, float)


def isseq(v):
    return isinstance(v, (list, tuple, str, dict))


def islist(v):
    return isinstance(v, (list, tuple))


def nonint(x):
    return type(x) is float and math.isfinite(x) and x != int(x)


def nums(v):
    return [x for x in v if isnum(x)] if islist(v) and v and all(isnum(x) for x in v) else None


def strs(v):
    return list(v) if islist(v) and v and all(isinstance(x, str) for x in v) else None


PUNCT = set(string.punctuation)


def cased(s):
    return [c for c in s if c.isalpha() and c.lower() != c.upper()]


def safe(fn):
    def g(b):
        try:
            return bool(fn(b))
        except Exception:
            return False
    return g


def q(p):
    return f"`{p}`"


def build_library(params, base_bound, extra_bound, int_consts, str_consts):
    """Returns [(name, description, predicate(bound_args) -> bool)]. Families are added only for the value types a
    parameter takes in the base or fuzz inputs; thresholds 'seen in base' come from the base inputs only."""
    lib = []

    def add(name, desc, fn):
        lib.append((name, desc, safe(fn)))

    allb = base_bound + extra_bound
    for p in params:
        vals = [b[p] for b in allb if p in b]
        bvals = [b[p] for b in base_bound if p in b]
        types = {type(v) for v in vals}
        P = q(p)
        # ---- type
        for t, tn in ((int, "an int"), (float, "a float"), (str, "a string"), (list, "a list"), (tuple, "a tuple"),
                      (dict, "a dict"), (bool, "a bool"), (type(None), "None")):
            if t in types:
                add(f"{p}:type={t.__name__}", f"{P} {tn}", lambda b, p=p, t=t: type(b[p]) is t)
        # ---- numeric
        if any(isnum(v) for v in vals):
            bn = [v for v in bvals if isnum(v)]
            add(f"{p}:zero", f"{P} = 0", lambda b, p=p: isnum(b[p]) and b[p] == 0)
            add(f"{p}:neg", f"{P} negative", lambda b, p=p: isnum(b[p]) and b[p] < 0)
            add(f"{p}:pos", f"{P} positive", lambda b, p=p: isnum(b[p]) and b[p] > 0)
            add(f"{p}:one", f"{P} = 1", lambda b, p=p: isnum(b[p]) and b[p] == 1)
            add(f"{p}:minus_one", f"{P} = -1", lambda b, p=p: isnum(b[p]) and b[p] == -1)
            add(f"{p}:nonint", f"{P} a non-integer number", lambda b, p=p: nonint(b[p]))
            add(f"{p}:intval_float", f"{P} a whole-number float (e.g. 3.0)", lambda b, p=p: type(b[p]) is float and b[p] == int(b[p]))
            add(f"{p}:odd", f"{P} odd", lambda b, p=p: type(b[p]) is int and b[p] % 2 == 1)
            add(f"{p}:even", f"{P} even", lambda b, p=p: type(b[p]) is int and b[p] % 2 == 0)
            add(f"{p}:large", f"{P} very large in size (|x| >= 10**6)", lambda b, p=p: isnum(b[p]) and abs(b[p]) >= 1e6)
            if bn:
                mx, mn = max(bn), min(bn)
                add(f"{p}:gt_basemax", f"{P} larger than any tested value ({mx!r})", lambda b, p=p, mx=mx: isnum(b[p]) and b[p] > mx)
                add(f"{p}:lt_basemin", f"{P} smaller than any tested value ({mn!r})", lambda b, p=p, mn=mn: isnum(b[p]) and b[p] < mn)
            for c in int_consts:
                add(f"{p}:eq_{c}", f"{P} = {c!r} (a constant in the code)", lambda b, p=p, c=c: isnum(b[p]) and b[p] == c)
                add(f"{p}:gt_{c}", f"{P} > {c!r} (a constant in the code)", lambda b, p=p, c=c: isnum(b[p]) and b[p] > c)
                add(f"{p}:lt_{c}", f"{P} < {c!r} (a constant in the code)", lambda b, p=p, c=c: isnum(b[p]) and b[p] < c)
        # ---- length / emptiness
        if any(isseq(v) for v in vals):
            bl = [len(v) for v in bvals if isseq(v)]
            unit = "characters" if any(isinstance(v, str) for v in vals) and not any(islist(v) for v in vals) else "elements"
            L = lambda b, p=p: len(b[p]) if isseq(b[p]) else None
            add(f"{p}:len0", f"{P} empty", lambda b, L=L: L(b) == 0)
            add(f"{p}:len1", f"{P} with exactly 1 {unit[:-1]}", lambda b, L=L: L(b) == 1)
            add(f"{p}:len2", f"{P} with exactly 2 {unit}", lambda b, L=L: L(b) == 2)
            add(f"{p}:len_le1", f"{P} with fewer than 2 {unit}", lambda b, L=L: L(b) is not None and L(b) <= 1)
            add(f"{p}:len_le2", f"{P} with at most 2 {unit}", lambda b, L=L: L(b) is not None and L(b) <= 2)
            add(f"{p}:len_ge3", f"{P} with at least 3 {unit}", lambda b, L=L: L(b) is not None and L(b) >= 3)
            add(f"{p}:len_ge5", f"{P} with at least 5 {unit}", lambda b, L=L: L(b) is not None and L(b) >= 5)
            add(f"{p}:len_ge10", f"{P} with at least 10 {unit}", lambda b, L=L: L(b) is not None and L(b) >= 10)
            add(f"{p}:len_odd", f"{P} of odd length", lambda b, L=L: L(b) is not None and L(b) % 2 == 1)
            add(f"{p}:len_even", f"{P} of even length", lambda b, L=L: L(b) is not None and L(b) % 2 == 0)
            if bl:
                mx, mn = max(bl), min(bl)
                add(f"{p}:len_gt_basemax", f"{P} longer than any tested one (> {mx} {unit})", lambda b, L=L, mx=mx: L(b) is not None and L(b) > mx)
                add(f"{p}:len_lt_basemin", f"{P} shorter than any tested one (< {mn} {unit})", lambda b, L=L, mn=mn: L(b) is not None and L(b) < mn)
            for c in int_consts:
                if 2 <= c <= 50:
                    add(f"{p}:len_eq_{c}", f"{P} of length {c} (a constant in the code)", lambda b, L=L, c=c: L(b) == c)
        # ---- string character classes
        if any(isinstance(v, str) for v in vals):
            S = lambda b, p=p: b[p] if isinstance(b[p], str) else None
            add(f"{p}:has_upper", f"{P} containing an uppercase letter", lambda b, S=S: any(c.isupper() for c in S(b)))
            add(f"{p}:all_upper", f"{P} all uppercase", lambda b, S=S: cased(S(b)) and all(c.isupper() for c in cased(S(b))))
            add(f"{p}:has_lower", f"{P} containing a lowercase letter", lambda b, S=S: any(c.islower() for c in S(b)))
            add(f"{p}:all_lower", f"{P} all lowercase", lambda b, S=S: cased(S(b)) and all(c.islower() for c in cased(S(b))))
            add(f"{p}:first_upper", f"{P} starting with an uppercase letter", lambda b, S=S: S(b)[:1].isupper())
            add(f"{p}:has_digit", f"{P} containing a digit", lambda b, S=S: any(c.isdigit() for c in S(b)))
            add(f"{p}:all_digit", f"{P} made only of digits", lambda b, S=S: S(b) != "" and S(b).isdigit())
            add(f"{p}:no_alpha", f"{P} non-empty with no letters", lambda b, S=S: S(b) != "" and not any(c.isalpha() for c in S(b)))
            add(f"{p}:has_space", f"{P} containing whitespace", lambda b, S=S: any(c.isspace() for c in S(b)))
            add(f"{p}:only_space", f"{P} non-empty and only whitespace", lambda b, S=S: S(b) != "" and S(b).isspace())
            add(f"{p}:lead_space", f"{P} with leading whitespace", lambda b, S=S: S(b)[:1].isspace())
            add(f"{p}:trail_space", f"{P} with trailing whitespace", lambda b, S=S: S(b)[-1:].isspace())
            add(f"{p}:double_space", f"{P} containing two spaces in a row", lambda b, S=S: "  " in S(b))
            add(f"{p}:nonascii", f"{P} containing a non-ASCII character", lambda b, S=S: any(ord(c) > 127 for c in S(b)))
            add(f"{p}:has_punct", f"{P} containing punctuation", lambda b, S=S: any(c in PUNCT for c in S(b)))
            add(f"{p}:dup_char", f"{P} with a repeated character", lambda b, S=S: len(set(S(b))) < len(S(b)))
            for c in str_consts:
                add(f"{p}:contains_{c!r}", f"{P} containing {c!r} (a string in the code)", lambda b, S=S, c=c: c in S(b))
                add(f"{p}:eq_{c!r}", f"{P} = {c!r} (a string in the code)", lambda b, S=S, c=c: S(b) == c)
                if len(c) > 1:
                    add(f"{p}:charof_{c!r}", f"{P} containing a character of {c!r} (from the code)", lambda b, S=S, c=c: any(x in c for x in S(b)))
        # ---- list elements
        if any(islist(v) for v in vals):
            N = lambda b, p=p: nums(b[p])
            be = [x for v in bvals if nums(v) for x in nums(v)]
            if any(nums(v) for v in vals):
                add(f"{p}:el_any_neg", f"{P} containing a negative number", lambda b, N=N: any(x < 0 for x in N(b)))
                add(f"{p}:el_all_neg", f"{P} with only negative numbers", lambda b, N=N: all(x < 0 for x in N(b)))
                add(f"{p}:el_any_zero", f"{P} containing 0", lambda b, N=N: any(x == 0 for x in N(b)))
                add(f"{p}:el_all_pos", f"{P} with only positive numbers", lambda b, N=N: all(x > 0 for x in N(b)))
                add(f"{p}:el_any_nonint", f"{P} containing a non-integer number", lambda b, N=N: any(nonint(x) for x in N(b)))
                add(f"{p}:el_any_float", f"{P} containing a float", lambda b, N=N: any(type(x) is float for x in N(b)))
                add(f"{p}:el_any_large", f"{P} containing a very large number (|x| >= 10**6)", lambda b, N=N: any(abs(x) >= 1e6 for x in N(b)))
                add(f"{p}:el_first_neg", f"{P} whose first element is negative", lambda b, N=N: N(b)[0] < 0)
                add(f"{p}:el_last_neg", f"{P} whose last element is negative", lambda b, N=N: N(b)[-1] < 0)
                add(f"{p}:el_any_odd", f"{P} containing an odd number", lambda b, N=N: any(type(x) is int and x % 2 for x in N(b)))
                add(f"{p}:el_all_odd", f"{P} with only odd numbers", lambda b, N=N: all(type(x) is int and x % 2 for x in N(b)))
                add(f"{p}:el_all_even", f"{P} with only even numbers", lambda b, N=N: all(type(x) is int and x % 2 == 0 for x in N(b)))
                if be:
                    mx, mn = max(be), min(be)
                    add(f"{p}:el_gt_basemax", f"{P} containing a number larger than any tested element ({mx!r})", lambda b, N=N, mx=mx: any(x > mx for x in N(b)))
                    add(f"{p}:el_lt_basemin", f"{P} containing a number smaller than any tested element ({mn!r})", lambda b, N=N, mn=mn: any(x < mn for x in N(b)))
                for c in int_consts:
                    add(f"{p}:el_has_{c}", f"{P} containing {c!r} (a constant in the code)", lambda b, N=N, c=c: c in N(b))
            E = lambda b, p=p: list(b[p]) if islist(b[p]) else None
            add(f"{p}:sorted_asc", f"{P} sorted ascending (2+ elements)", lambda b, E=E: len(E(b)) >= 2 and all(x <= y for x, y in zip(E(b), E(b)[1:])))
            add(f"{p}:strict_asc", f"{P} strictly increasing (2+ elements)", lambda b, E=E: len(E(b)) >= 2 and all(x < y for x, y in zip(E(b), E(b)[1:])))
            add(f"{p}:sorted_desc", f"{P} sorted descending (2+ elements)", lambda b, E=E: len(E(b)) >= 2 and all(x >= y for x, y in zip(E(b), E(b)[1:])))
            add(f"{p}:unsorted", f"{P} neither ascending nor descending", lambda b, E=E: len(E(b)) >= 3 and not all(x <= y for x, y in zip(E(b), E(b)[1:])) and not all(x >= y for x, y in zip(E(b), E(b)[1:])))
            add(f"{p}:has_dup", f"{P} with a repeated element", lambda b, E=E: len({repr(x) for x in E(b)}) < len(E(b)))
            add(f"{p}:all_equal", f"{P} whose elements are all equal (2+ elements)", lambda b, E=E: len(E(b)) >= 2 and len({repr(x) for x in E(b)}) == 1)
            add(f"{p}:mixed_types", f"{P} mixing element types", lambda b, E=E: len({type(x) for x in E(b)}) > 1)
            if any(strs(v) for v in vals):
                T = lambda b, p=p: strs(b[p])
                add(f"{p}:el_any_empty_str", f"{P} containing an empty string", lambda b, T=T: "" in T(b))
                add(f"{p}:el_any_upper", f"{P} containing a string with an uppercase letter", lambda b, T=T: any(any(c.isupper() for c in s) for s in T(b)))
                add(f"{p}:el_any_space", f"{P} containing a string with whitespace", lambda b, T=T: any(any(c.isspace() for c in s) for s in T(b)))
                add(f"{p}:el_any_nonascii", f"{P} containing a string with a non-ASCII character", lambda b, T=T: any(any(ord(c) > 127 for c in s) for s in T(b)))
                add(f"{p}:el_any_punct", f"{P} containing a string with punctuation", lambda b, T=T: any(any(c in PUNCT for c in s) for s in T(b)))
                add(f"{p}:el_any_digit", f"{P} containing a string with a digit", lambda b, T=T: any(any(c.isdigit() for c in s) for s in T(b)))
                add(f"{p}:el_any_len1", f"{P} containing a 1-character string", lambda b, T=T: any(len(s) == 1 for s in T(b)))
            if any(islist(v) and v and all(islist(x) for x in v) for v in vals):
                I = lambda b, p=p: list(b[p]) if islist(b[p]) and b[p] and all(islist(x) for x in b[p]) else None
                add(f"{p}:inner_any_empty", f"{P} containing an empty inner list", lambda b, I=I: any(len(x) == 0 for x in I(b)))
                add(f"{p}:inner_len_differ", f"{P} with inner lists of different lengths", lambda b, I=I: len({len(x) for x in I(b)}) > 1)
        # ---- dict keys
        if any(isinstance(v, dict) for v in vals):
            K = lambda b, p=p: list(b[p].keys()) if isinstance(b[p], dict) else None
            add(f"{p}:keys_nonstr", f"{P} with a non-string key", lambda b, K=K: any(not isinstance(k, str) for k in K(b)))
            add(f"{p}:keys_mixed_case", f"{P} with both lowercase and uppercase keys", lambda b, K=K: any(isinstance(k, str) and k.islower() for k in K(b)) and any(isinstance(k, str) and k.isupper() for k in K(b)))
    # ---- relations between parameters
    for i, p in enumerate(params):
        for r in params[i + 1:]:
            pv = [b[p] for b in allb if p in b]; rv = [b[r] for b in allb if r in b]
            P, R = q(p), q(r)
            if any(isnum(v) for v in pv) and any(isnum(v) for v in rv):
                add(f"{p}=={r}", f"{P} equal to {R}", lambda b, p=p, r=r: isnum(b[p]) and isnum(b[r]) and b[p] == b[r])
                add(f"{p}>{r}", f"{P} > {R}", lambda b, p=p, r=r: isnum(b[p]) and isnum(b[r]) and b[p] > b[r])
                add(f"{p}<{r}", f"{P} < {R}", lambda b, p=p, r=r: isnum(b[p]) and isnum(b[r]) and b[p] < b[r])
            if any(isseq(v) for v in pv) and any(isseq(v) for v in rv):
                add(f"len({p})==len({r})", f"{P} and {R} of the same length", lambda b, p=p, r=r: isseq(b[p]) and isseq(b[r]) and len(b[p]) == len(b[r]))
                add(f"len({p})!=len({r})", f"{P} and {R} of different lengths", lambda b, p=p, r=r: isseq(b[p]) and isseq(b[r]) and len(b[p]) != len(b[r]))
                add(f"len({p})>len({r})", f"{P} longer than {R}", lambda b, p=p, r=r: isseq(b[p]) and isseq(b[r]) and len(b[p]) > len(b[r]))
                add(f"len({p})<len({r})", f"{P} shorter than {R}", lambda b, p=p, r=r: isseq(b[p]) and isseq(b[r]) and len(b[p]) < len(b[r]))
                add(f"{p}=={r}:seq", f"{P} equal to {R}", lambda b, p=p, r=r: isseq(b[p]) and b[p] == b[r])
            if any(isinstance(v, str) for v in pv) and any(isinstance(v, str) for v in rv):
                add(f"{p} in {r}", f"{P} a substring of {R}", lambda b, p=p, r=r: isinstance(b[p], str) and isinstance(b[r], str) and b[p] in b[r])
                add(f"{r} in {p}", f"{R} a substring of {P}", lambda b, p=p, r=r: isinstance(b[p], str) and isinstance(b[r], str) and b[r] in b[p])
            for a, s, A, Sx, av, sv in ((p, r, P, R, pv, rv), (r, p, R, P, rv, pv)):
                if any(type(v) is int for v in av) and any(isseq(v) for v in sv):
                    add(f"{a}==len({s})", f"{A} equal to the length of {Sx}", lambda b, a=a, s=s: type(b[a]) is int and isseq(b[s]) and b[a] == len(b[s]))
                    add(f"{a}>len({s})", f"{A} larger than the length of {Sx}", lambda b, a=a, s=s: type(b[a]) is int and isseq(b[s]) and b[a] > len(b[s]))
                    add(f"{a}>=len({s})", f"{A} at least the length of {Sx}", lambda b, a=a, s=s: type(b[a]) is int and isseq(b[s]) and b[a] >= len(b[s]))
                if any(isnum(v) for v in av) and any(islist(v) for v in sv):
                    add(f"{a} in {s}", f"{A} one of the elements of {Sx}", lambda b, a=a, s=s: isnum(b[a]) and islist(b[s]) and b[a] in b[s])
    return lib


# ============================================================ guards from the source (optional)
SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
                 for k in ("len", "abs", "sum", "min", "max", "sorted", "set", "list", "str", "int", "float", "all",
                           "any", "isinstance", "type", "round", "tuple", "range", "reversed", "bool", "ord", "chr",
                           "dict", "enumerate", "zip", "map", "filter")}
MUTATING = {"append", "extend", "insert", "pop", "remove", "sort", "reverse", "clear", "update", "add", "discard", "popitem", "setdefault"}


def direct_params(fn_node, params):
    """Parameters whose value is never reassigned or mutated inside the function."""
    bad = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            bad.add(n.id)
        if isinstance(n, (ast.Subscript, ast.Attribute)) and isinstance(n.ctx, (ast.Store, ast.Del)):
            v = n.value
            while isinstance(v, (ast.Subscript, ast.Attribute)):
                v = v.value
            if isinstance(v, ast.Name):
                bad.add(v.id)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in MUTATING:
            v = n.func.value
            if isinstance(v, ast.Name):
                bad.add(v.id)
    return set(params) - bad


def expr_ok(src, ok_names):
    try:
        e = ast.parse(src, mode="eval")
    except SyntaxError:
        return None
    for n in ast.walk(e):
        if isinstance(n, (ast.Lambda, ast.comprehension, ast.NamedExpr, ast.Await, ast.Yield)):
            return None
        if isinstance(n, ast.Name) and n.id not in ok_names and n.id not in SAFE_BUILTINS:
            return None
    if not any(isinstance(n, ast.Name) and n.id in ok_names for n in ast.walk(e)):
        return None
    return compile(e, "<guard>", "eval")


def enclosing_test(fn_node, line):
    best = None
    for n in ast.walk(fn_node):
        if isinstance(n, (ast.If, ast.While)):
            for pol, body in ((True, n.body), (False, n.orelse)):
                if body and body[0].lineno <= line <= max(getattr(x, "end_lineno", x.lineno) for x in body):
                    if best is None or n.lineno >= best[0].lineno:
                        best = (n, pol)
    return best


def guard_for(f, sites, fn_node, params):
    """(description, kind, compiled exprs, polarity) or None."""
    ok = direct_params(fn_node, params)
    if not ok:
        return None
    if f["kind"] == "OUTCOME" and "cell" in f:
        sid, miss = f["cell"]
        src = sites[sid]["src"]
        code = expr_ok(src, ok)
        if code is None:
            return None
        val = "true" if miss == "T" else "false"
        return dict(desc=f"arguments for which `{src}` is {val}", kind="branch", code=[code], pol=miss == "T", src=src)
    if f["kind"] == "STMT":
        enc = enclosing_test(fn_node, f["lines"][0])
        if enc is None:
            return None
        src = ast.unparse(enc[0].test)
        code = expr_ok(src, ok)
        if code is None:
            return None
        return dict(desc=f"arguments for which `{src}` is {'true' if enc[1] else 'false'}", kind="enclosing", code=[code], pol=enc[1], src=src)
    if f["kind"] == "MUTANT":
        m = re.search(r"the mutant `(.+)` -> `(.+)` at line \d+", f["text"])
        if not m:
            return None
        cb, ca = expr_ok(m.group(1), ok), expr_ok(m.group(2), ok)
        if cb is None or ca is None:
            return None
        return dict(desc=f"arguments for which `{m.group(1)}` and `{m.group(2)}` differ", kind="infection", code=[cb, ca], pol=None, src=m.group(1))
    return None


def eval_guard(g, bound):
    from tracer import alarm, dcopy
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(1):
            env = dcopy(dict(bound))
            vals = [eval(c, {"__builtins__": SAFE_BUILTINS}, env) for c in g["code"]]
    except BaseException:
        return False
    try:
        if g["pol"] is None:
            a, b = vals
            return not (type(a) == type(b) and a == b)
        return bool(vals[0]) == g["pol"]
    except Exception:
        return False


# ============================================================ worker (runs inside unshare -rn)
def worker(task):
    sys.path[:0] = [str(TL), str(ROOT)]
    import random
    import facts as F
    from tracer import alarm, call, dcopy, fact_hit, instrument, trace
    bundle = next(t for t in json.load(open(TASKS))["tasks"] if t["task"] == task)
    he = next(r for r in map(json.loads, open(HE)) if r["task_id"] == f"HumanEval/{task}")
    cap = {}
    (OUT / "regen").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    F.main(task, bundle["put"], he, str(OUT / "regen" / f"{task}.json"), "mined", None, PRECOND,
           evidence=lambda loc: cap.update({k: loc[k] for k in ("fz", "fz_traces", "base_args", "mfns", "put", "iput", "sites", "entry")}))
    regen = json.load(open(OUT / "regen" / f"{task}.json"))
    orig = json.load(open(FACTS / f"{task}.json"))
    repro = dict(n_fuzz=(regen["n_fuzz"], orig["n_fuzz"]), facts_equal=[f["text"] for f in regen["facts"]] == [f["text"] for f in orig["facts"]],
                 witness_equal=[f["witness"] for f in regen["facts"]] == [f["witness"] for f in orig["facts"]],
                 top3_equal=regen["top3"] == orig["top3"])
    fz, put, entry, sites, mfns = cap["fz"], cap["put"], cap["entry"], cap["sites"], cap["mfns"]
    base = cap["base_args"]
    sig = inspect.signature(put)
    params = list(sig.parameters)
    tree = ast.parse(bundle["put"])
    fn_node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == entry)

    def bind(a):
        try:
            ba = sig.bind(*a[0], **a[1])
            ba.apply_defaults()
            return dict(ba.arguments)
        except Exception:
            return None

    # Qwen round-1 inputs of the concept arm (follow_cases), unique per task
    cases = [c for c in json.load(open(CASES)) if c["task"] == task]
    qreprs = sorted({x[0] for c in cases for x in c["inputs"]})
    qargs = []
    for s in qreprs:
        try:
            a = ast.literal_eval(s)
            qargs.append(((a if isinstance(a, tuple) else (a,)), {}))
        except Exception:
            qargs.append(None)

    int_consts = list(F.CONSTS)
    str_consts = []
    doc = ast.get_docstring(fn_node)
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != doc and 1 <= len(n.value) <= 10 and n.value not in str_consts:
            str_consts.append(n.value)
    str_consts = str_consts[:12]
    bb = [bind(a) for a in base]
    fb = [bind(a) for a in fz]
    qb = [bind(a) if a is not None else None for a in qargs]
    lib = build_library(params, [b for b in bb if b], [b for b in fb if b], int_consts, str_consts)

    def feats(b):
        if b is None:
            return []
        out = []
        for i, (_, _, fn) in enumerate(lib):
            try:
                with alarm(1):
                    if fn(b):
                        out.append(i)
            except BaseException:
                pass
        return out

    res = dict(task=task, entry=entry, params=params, repro=repro, int_consts=int_consts, str_consts=str_consts,
               library=[(n, d) for n, d, _ in lib], n_base=len(base), n_fuzz=len(fz),
               base_feats=[feats(b) for b in bb], fuzz_feats=[feats(b) for b in fb], qwen_reprs=qreprs,
               qwen_feats=[feats(b) for b in qb], qwen_bindable=[b is not None for b in qb],
               base_calls=[F.call_src(entry, a) for a in base], facts=[])
    pouts = {}

    def hits(f, f_args, key):
        out = []
        k = f.get("k")
        for i, a in enumerate(f_args):
            if a is None:
                out.append(False)
                continue
            try:
                tr = trace(cap["iput"], a)
                pk = (key, i)
                if pk not in pouts:
                    pouts[pk] = call(put, a)
                mout = call(mfns[k], a) if f["kind"] == "MUTANT" and k in mfns else None
                out.append(bool(fact_hit(f, tr, pouts[pk], mout)))
            except BaseException:
                out.append(False)
        return out

    for j, f in enumerate(bundle["concept_meta"]):
        rf = next((x for x in regen["facts"] if x["text"] == f["text"]), None)
        g = guard_for(f, sites, fn_node, params)
        rec = dict(idx=j, kind=f["kind"], text=f["text"], witness=f.get("witness"), witness_call=f.get("witness_call"),
                   regen_witness=rf["witness"] if rf else "missing", mutant_fn=f.get("k") in mfns if f["kind"] == "MUTANT" else None,
                   fuzz_hits=hits(f, fz, "fz"), base_hits=hits(f, base, "base"), qwen_hits=hits(f, qargs, "q"))
        if g:
            rec["guard"] = dict(desc=g["desc"], kind=g["kind"], src=g["src"],
                                base=[eval_guard(g, b) if b else False for b in bb], fuzz=[eval_guard(g, b) if b else False for b in fb],
                                qwen=[eval_guard(g, b) if b else False for b in qb])
        res["facts"].append(rec)
    res["secs"] = round(time.time() - t0, 1)
    (OUT / "worker").mkdir(parents=True, exist_ok=True)
    json.dump(res, open(OUT / "worker" / f"{task}.json", "w"))


def run_workers(tasks, jobs):
    (OUT / "worker").mkdir(parents=True, exist_ok=True)
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    env = {"PATH": os.defpath + ":/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}

    def one(t):
        if (OUT / "worker" / f"{t}.json").exists():
            return t, "cached"
        with open(OUT / "logs" / f"{t}.log", "w") as log:
            r = subprocess.run(["timeout", "-k", "5", "2400", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                "worker", str(t)], env=env, stdout=log, stderr=subprocess.STDOUT, cwd=str(OUT))
        return t, r.returncode

    with ThreadPoolExecutor(jobs) as ex:
        for t, rc in ex.map(one, tasks):
            if rc not in (0, "cached"):
                print(f"task {t}: rc={rc}", flush=True)


# ============================================================ analysis (pure data)
def masks(feat_lists, nlib):
    m = [0] * nlib
    for i, fl in enumerate(feat_lists):
        for k in fl:
            m[k] |= 1 << i
    return m


def bits(xs):
    m = 0
    for i, x in enumerate(xs):
        if x:
            m |= 1 << i
    return m


def pc(m):
    return bin(m).count("1")


def derive(w, fact, nlib):
    """Search 1-2 feature conjunctions (plus an optional guard feature) for one fact."""
    nf = w["n_fuzz"]
    widx = fact["witness"]
    if widx is None or widx >= nf:
        return None
    fm, bm = masks(w["fuzz_feats"], nlib), masks(w["base_feats"], nlib)
    names = [n for n, _ in w["library"]]
    descs = [d for _, d in w["library"]]
    cand = list(range(nlib))
    if "guard" in fact:
        fm.append(bits(fact["guard"]["fuzz"])); bm.append(bits(fact["guard"]["base"]))
        names.append("GUARD:" + fact["guard"]["src"]); descs.append(fact["guard"]["desc"])
    hit = bits(fact["fuzz_hits"])
    allf = (1 << nf) - 1
    H = pc(hit)
    wbit = 1 << widx

    def score(cm):
        tp, fp = pc(cm & hit), pc(cm & ~hit & allf)
        fn, tn = H - tp, nf - pc(cm) - (H - tp)
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, H)
        notc = fn / max(1, fn + tn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        ok = prec >= MIN_PREC and (notc == 0 or prec >= MIN_LIFT * notc)
        return dict(tp=tp, fp=fp, fn=fn, tn=tn, prec=round(prec, 3), rec=round(rec, 3), p_hit_not=round(notc, 3), f1=round(f1, 3), ok=ok)

    out = {}
    for use_guard in (False, True):
        ids = [i for i in range(len(fm)) if (use_guard or i < nlib)]
        wf = [i for i in ids if fm[i] & wbit]
        sing = [(i,) for i in wf if bm[i] == 0]
        pairs = [(i, j) for a, i in enumerate(wf) for j in wf[a + 1:] if bm[i] & bm[j] == 0]
        best = None
        for size, cs in ((1, sing), (2, pairs)):
            scored = []
            for c in cs:
                cm = allf
                for i in c:
                    cm &= fm[i]
                s = score(cm)
                scored.append((not s["ok"], -s["f1"], -s["prec"], c, s))
            scored.sort(key=lambda x: x[:3] + (x[3],))
            if scored and not scored[0][0]:
                best = (scored[0][3], scored[0][4]); break
            if scored and best is None:
                best = ("weak", scored[0][3], scored[0][4])
        if best is None:
            out["guard" if use_guard else "lib"] = None
            continue
        weak = best[0] == "weak"
        c, s = (best[1], best[2]) if weak else best
        out["guard" if use_guard else "lib"] = dict(status="weak" if weak else "derived", feats=[names[i] for i in c],
                                                     descs=[descs[i] for i in c], ids=list(c), uses_guard=any(i >= nlib for i in c), **s)
    return out


def holds(cond, feats_of_input, guard_vals, qi):
    for i in cond["ids"]:
        if i >= len_lib_marker[0]:
            if not guard_vals[qi]:
                return False
        elif i not in feats_of_input:
            return False
    return True


len_lib_marker = [0]


def render(w, fact, cond):
    entry = w["entry"]
    body = " and ".join(cond["descs"])
    ex = f" (e.g. `{fact['witness_call']}`)" if fact.get("witness_call") else ""
    return f"No existing test calls `{entry}` with {body}{ex}."


def manual_causes():
    """(task, fact text) -> cause, from build_page.py (`order` list over sorted groups with a miss)."""
    tree = ast.parse(BUILD_PAGE.read_text())
    order = note = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id == "order":
                order = ast.literal_eval(n.value)
            if n.targets[0].id == "NOTE":
                note = ast.literal_eval(n.value)
    cases = json.load(open(CASES))
    g = collections.OrderedDict()
    for c in cases:
        g.setdefault((c["task"], c["fact"]), []).append(c)
    groups = [k for k, v in sorted(g.items()) if any(not c["hit"] for c in v)]
    assert len(groups) == len(order)
    return {k: (order[i], note.get(i + 1, ""), i + 1) for i, k in enumerate(groups)}, cases


def analyze():
    bundles = {t["task"]: t for t in json.load(open(TASKS))["tasks"]}
    W = {}
    for p in sorted((OUT / "worker").glob("*.json")):
        w = json.load(open(p)); W[w["task"]] = w
    cause, cases = manual_causes()
    conds, repro_bad = {}, []
    for t, w in sorted(W.items()):
        r = w["repro"]
        if not (r["facts_equal"] and r["witness_equal"] and r["n_fuzz"][0] == r["n_fuzz"][1]):
            repro_bad.append(t)
        nlib = len(w["library"])
        for f in w["facts"]:
            d = derive(w, f, nlib)
            fz_h = sum(f["fuzz_hits"])
            conds[(t, f["text"])] = dict(task=t, kind=f["kind"], text=f["text"], witness_call=f["witness_call"], split=bundles[t]["split"],
                                         witness_ok=(f["witness"] is not None and f["witness"] < w["n_fuzz"] and f["fuzz_hits"][f["witness"]]),
                                         regen_witness_equal=f["regen_witness"] == f["witness"], fuzz_hits=fz_h, n_fuzz=w["n_fuzz"],
                                         base_hits=sum(f["base_hits"]), has_guard="guard" in f, guard=f.get("guard", {}).get("desc"),
                                         lib=d and d["lib"], withguard=d and d["guard"])
            for key in ("lib", "guard"):
                c = d and d[key]
                if c:
                    c["hint"] = render(w, f, c)
    # ---- evaluate cases
    good = {(c["task"], c["fact"]) for c in cases}
    rows = []
    for c in cases:
        t = c["task"]; w = W.get(t)
        key = (t, c["fact"])
        cd = conds.get(key)
        f = next((x for x in w["facts"] if x["text"] == c["fact"]), None) if w else None
        row = dict(task=t, sample=c["sample"], kind=c["kind"], fact=c["fact"], hit=c["hit"], witness=c["witness"],
                   cause=cause.get(key, (None,))[0], note=cause.get(key, (None, ""))[1], group=cause.get(key, (None, None, None))[2],
                   n_inputs=len(c["inputs"]), n_valid=sum(x[1] for x in c["inputs"]))
        for key2 in ("lib", "guard"):
            cond = cd and (cd["lib"] if key2 == "lib" else cd["withguard"])
            r = dict(status=cond["status"] if cond else "none")
            if cond and f is not None:
                len_lib_marker[0] = len(w["library"])
                gv = f.get("guard", {}).get("qwen", [False] * len(w["qwen_reprs"]))
                sat_valid = sat_any = 0; sat_valid_hit = 0; recheck = []
                for x in c["inputs"]:
                    qi = w["qwen_reprs"].index(x[0])
                    s = holds(cond, set(w["qwen_feats"][qi]), gv, qi)
                    sat_any += s
                    if x[1]:
                        sat_valid += s
                        sat_valid_hit += s and x[2]
                    recheck.append(f["qwen_hits"][qi] == bool(x[2]) if x[1] else None)
                r.update(sat_valid=sat_valid, sat_any=sat_any, sat_valid_hit=sat_valid_hit,
                         explains=(sat_valid == 0), hit_recheck_agree=all(v is not False for v in recheck))
            row[key2] = r
        rows.append(row)
    json.dump(rows, open(OUT / "cases.json", "w"), indent=1)
    json.dump([dict(v, key=list(k)) for k, v in conds.items()], open(OUT / "conditions.json", "w"), indent=1)

    # ---- summary
    L = []
    P = lambda s="": L.append(s)
    P(f"workers: {len(W)} tasks; reproduction mismatches (facts/witness/n_fuzz vs out/facts_v3m2): {repro_bad}")
    P(f"shown facts with witness re-hit in regenerated fuzz: {sum(v['witness_ok'] for v in conds.values())}/"
      f"{sum(v['witness_call'] is not None for v in conds.values())} reached; base inputs hitting a shown fact: "
      f"{sum(v['base_hits']>0 for v in conds.values())} facts")
    agree = sum(r["lib"].get("hit_recheck_agree", True) for r in rows)
    P(f"Qwen-input hit recheck agrees with follow_cases flags: {agree}/{len(rows)} cases (cases with a condition)")
    summary = {}
    for key2, label in (("lib", "feature library only"), ("guard", "library + source guard")):
        P(); P(f"=== {label} ===")
        miss = [r for r in rows if not r["hit"]]
        hitr = [r for r in rows if r["hit"]]
        tab = {}
        for cat in (1, 2, 3, 4, "all"):
            rs = [r for r in miss if cat == "all" or r["cause"] == cat]
            der = [r for r in rs if r[key2]["status"] == "derived"]
            weak = [r for r in rs if r[key2]["status"] == "weak"]
            ex = [r for r in der if r[key2].get("explains")]
            exw = [r for r in weak if r[key2].get("explains")]
            tab[cat] = dict(n=len(rs), derived=len(der), derived_explains=len(ex), weak=len(weak), weak_explains=len(exw),
                            none=len(rs) - len(der) - len(weak))
            P(f"missed cases cause {cat!s:3} ({CAT.get(cat,'all')}): n={len(rs)}  derived={len(der)}  derived&explains={len(ex)}  "
              f"weak-only={len(weak)} (explains {len(exw)})  none={tab[cat]['none']}")
        dh = [r for r in hitr if r[key2]["status"] == "derived"]
        cons = [r for r in dh if r[key2]["sat_valid_hit"] > 0]
        P(f"hit cases: n={len(hitr)}; derived={len(dh)}; a hitting Qwen input satisfies C in {len(cons)}/{len(dh)}")
        # discrimination on Qwen inputs: all unique (fact, input) pairs for good facts, valid only
        tp = fp = fn = tn = 0
        for (t, ftxt) in good:
            cd = conds.get((t, ftxt)); w = W.get(t)
            cond = cd and (cd["lib"] if key2 == "lib" else cd["withguard"])
            if not cond or cond["status"] != "derived":
                continue
            f = next(x for x in w["facts"] if x["text"] == ftxt)
            len_lib_marker[0] = len(w["library"])
            gv = f.get("guard", {}).get("qwen", [False] * len(w["qwen_reprs"]))
            seen = set()
            for c in cases:
                if (c["task"], c["fact"]) != (t, ftxt):
                    continue
                for x in c["inputs"]:
                    if not x[1] or x[0] in seen:
                        continue
                    seen.add(x[0])
                    qi = w["qwen_reprs"].index(x[0])
                    s = holds(cond, set(w["qwen_feats"][qi]), gv, qi)
                    tp += s and x[2]; fp += s and not x[2]; fn += (not s) and x[2]; tn += (not s) and not x[2]
        P(f"on Qwen's own valid inputs (good facts with a derived C): P(hit|C)={tp}/{tp+fp}  P(hit|not C)={fn}/{fn+tn}  recall={tp}/{tp+fn}")
        cov = {}
        for name, sel in (("good shown facts (follow_cases)", lambda v: (v["task"], v["text"]) in good),
                          ("all shown facts dev", lambda v: v["split"] == "dev"),
                          ("all shown facts dev+pilot", lambda v: True)):
            vs = [v for v in conds.values() if sel(v)]
            reached = [v for v in vs if v["witness_call"] is not None]
            c = v_ = None
            der = [v for v in vs if (v["lib"] if key2 == "lib" else v["withguard"]) and (v["lib"] if key2 == "lib" else v["withguard"])["status"] == "derived"]
            wk = [v for v in vs if (v["lib"] if key2 == "lib" else v["withguard"]) and (v["lib"] if key2 == "lib" else v["withguard"])["status"] == "weak"]
            cov[name] = dict(n=len(vs), reached=len(reached), derived=len(der), weak=len(wk))
            bykind = collections.Counter(v["kind"] for v in der); kinds = collections.Counter(v["kind"] for v in vs)
            P(f"coverage {name}: derived {len(der)}/{len(vs)} (reached {len(reached)}), weak-only {len(wk)}; by kind "
              + ", ".join(f"{k} {bykind[k]}/{kinds[k]}" for k in sorted(kinds)))
        summary[key2] = dict(miss=tab, hit_cases=dict(n=len(hitr), derived=len(dh), consistent=len(cons)),
                             qwen_discrimination=dict(tp=tp, fp=fp, fn=fn, tn=tn), coverage=cov)
        # guard usage
        if key2 == "guard":
            gfacts = [v for v in conds.values() if v["has_guard"]]
            used = [v for v in conds.values() if v["withguard"] and v["withguard"].get("uses_guard") and v["withguard"]["status"] == "derived"]
            P(f"facts with a source guard: {len(gfacts)}/{len(conds)}; derived conditions using the guard: {len(used)}")
    # per-group table for the report
    P(); P("=== per (task, fact) group with a miss (library + guard) ===")
    grp = collections.OrderedDict()
    for r in rows:
        if r["group"] is not None:
            grp.setdefault(r["group"], []).append(r)
    for gi, rs in sorted(grp.items()):
        r0 = rs[0]; cd = conds.get((r0["task"], r0["fact"]))
        if cd is None:
            continue
        c = cd["withguard"]
        miss = [r for r in rs if not r["hit"]]
        P(f"#{gi} t{r0['task']} cause{r0['cause']} {r0['kind']} miss {len(miss)}/{len(rs)} explains {sum(r['guard'].get('explains', False) for r in miss)} | "
          + (f"{c['status']}: {' AND '.join(c['feats'])} prec={c['prec']} rec={c['rec']} p_not={c['p_hit_not']} (tp {c['tp']}, H {c['tp']+c['fn']}/{cd['n_fuzz']})" if c else "no candidate")
          + f" | {r0['fact'][:110]}")
        P(f"    code-level : {r0['fact']}")
        P(f"    input-level: {c['hint'] if c else '(none)'}")
    # POST HOC (added after seeing the numbers above): a derived condition with tiny support or low recall on fuzz
    # may be a surface correlate rather than the trigger (e.g. 'string with >= 10 characters' for palindrome branches).
    P(); P("=== POST HOC robustness: 'strong' = derived with recall >= 0.5 on fuzz (library + guard) ===")
    strong = lambda c: c and c["status"] == "derived" and c["rec"] >= 0.5
    ph = {}
    for cat in (1, 2, 3, 4, "all"):
        rs = [r for r in rows if not r["hit"] and (cat == "all" or r["cause"] == cat)]
        st = [r for r in rs if strong(conds[(r["task"], r["fact"])]["withguard"])]
        ex = [r for r in st if r["guard"].get("explains")]
        ph[cat] = dict(n=len(rs), strong=len(st), strong_explains=len(ex))
        P(f"missed cause {cat!s:3}: n={len(rs)} strong={len(st)} strong&explains={len(ex)}")
    for name, sel in (("good shown facts", lambda v: (v["task"], v["text"]) in good), ("all shown dev", lambda v: v["split"] == "dev"),
                      ("all shown dev+pilot", lambda v: True)):
        vs = [v for v in conds.values() if sel(v)]
        P(f"coverage {name}: strong {sum(bool(strong(v['withguard'])) for v in vs)}/{len(vs)}")
    summary["post_hoc_strong"] = ph
    summary["repro_bad"] = repro_bad
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    (OUT / "summary.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "worker":
        worker(int(sys.argv[2]))
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--jobs", type=int, default=8)
        ap.add_argument("--tasks", type=int, nargs="*")
        a = ap.parse_args()
        if a.cmd == "run":
            tasks = a.tasks or [t["task"] for t in json.load(open(TASKS))["tasks"] if t["concept_meta"]]
            run_workers(tasks, a.jobs)
        analyze()
