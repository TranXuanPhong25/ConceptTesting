"""Deterministic concept tool (no LLM) + derangement placebo for the PBT_EdgeCases pilot.

Input: ONLY the HumanEval `prompt` field (signature + docstring), parsed with `ast` (never executed). The canonical
solution, HumanEval/HumanEval+ tests and the HumanEval+ inputs are never read.
Output per task: concept lines (input-domain edges per parameter, docstring constraints, Hypothesis strategy bounds,
@example witnesses). Placebo per task: another task's lines (derangement, different signature), renamed onto this
task's function/parameters, padded/truncated to the same line count, @example kwargs repaired to match the signature.

usage: python run/concepts.py   -> writes run/concepts/{concept,placebo}/HumanEval_<n>.txt + run/concepts/summary.json
Rules were written from the type/docstring vocabulary and frozen before any generation or failure-input inspection.
"""
import ast, json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = [22, 44, 49, 55, 63, 64, 76, 95, 97, 122, 123, 124, 127, 132, 140, 150]
HEADER = ("**Concept hints** (tool-computed from the signature and docstring only). Use them to choose Hypothesis "
          "strategy bounds and to add `@example(...)` witnesses next to `@given`; keep every assertion a property "
          "stated by the docstring:")
CHARSETS = {"square bracket": "[]", "bracket": "[]", "parenthes": "()", "digit": "0123456789",
            "lowercase": "abcdefghijklmnopqrstuvwxyz", "lower case": "abcdefghijklmnopqrstuvwxyz",
            "uppercase": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "upper case": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
BIG = "2**53 + 1"  # first int that a float cannot represent exactly


def _fam(v):
    if isinstance(v, bool): return "bool"
    if isinstance(v, int): return "int"
    if isinstance(v, float): return "float"
    if isinstance(v, str): return "str"
    if isinstance(v, (list, tuple)):
        inner = sorted({_fam(x) for x in v}) or ["int"]
        kind = "list" if isinstance(v, list) else "tuple"
        return f"{kind}[{inner[0] if len(inner) == 1 else 'Any'}]"
    if isinstance(v, dict): return "dict"
    return "Any"


def _ann_fam(ann):
    a = (ann or "").replace("typing.", "")
    m = re.match(r"(List|list|Tuple|tuple)\[(.*)\]$", a)
    if m:
        inner = _ann_fam(m.group(2).split(",")[0].strip())
        return f"{m.group(1).lower()}[{inner}]"
    return {"int": "int", "float": "float", "str": "str", "bool": "bool", "dict": "dict", "Dict": "dict",
            "Any": "Any"}.get(a.split("[")[0], None)


def parse(prompt, entry):
    """-> name, params [(name, annotation|None)], docstring, example calls [[arg values]] (literals only)."""
    tree = ast.parse(prompt)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == entry)
    params = [(a.arg, ast.unparse(a.annotation) if a.annotation else None) for a in fn.args.args]
    doc = ast.get_docstring(fn) or ""
    examples = []
    for m in re.finditer(rf"\b{entry}\s*\(", doc):  # balanced-paren scan, then literal_eval the args
        i, depth = m.end(), 1
        while i < len(doc) and depth:
            depth += {"(": 1, ")": -1}.get(doc[i], 0); i += 1
        try:
            call = ast.parse(doc[m.start():i], mode="eval").body
            examples.append([ast.literal_eval(a) for a in call.args])
        except Exception:
            pass
    vals = {p: [e[i] for e in examples if len(e) == len(params)] for i, (p, _) in enumerate(params)}
    for p, _ in params:  # docstring assignments such as "Input: arr = [1, 2], k = 4"
        for m in re.finditer(rf"\b{re.escape(p)}\s*=\s*", doc):
            v = _literal_at(doc, m.end())
            if v is not _NO: vals[p].append(v)
    return fn.name, params, doc, vals


_NO = object()


def _literal_at(text, i):
    """Literal starting at text[i], ending at a depth-0 comma / newline / end; _NO if not a literal."""
    j, depth, q = i, 0, None
    while j < len(text):
        ch = text[j]
        if q:
            q = None if ch == q else q
        elif ch in "'\"": q = ch
        elif ch in "([{": depth += 1
        elif ch in ")]}": depth -= 1
        elif depth == 0 and ch in ",\n": break
        if depth < 0: break
        j += 1
    try:
        return ast.literal_eval(text[i:j].strip())
    except Exception:
        return _NO


def _sentences(doc):
    return [s.strip() for s in re.split(r"(?<=[.\n])\s+", doc) if s.strip()]


def constraints(doc, params, fams):
    """Generic docstring constraint parsing -> {param: {lo, hi, min_size, max_size}} plus quoted human text."""
    c = {p: {} for p, _ in params}
    texts = []
    names = [p for p, _ in params]
    flat = " ".join(doc.split())
    for m in re.finditer(r"(-?\d+)\s*<=\s*(len\()?\s*(\w+)\s*\)?\s*<=\s*(-?\d+|len\(\w+\)|\w+)", flat):
        lo, is_len, name, hi = m.group(1), m.group(2), m.group(3), m.group(4)
        if name in c:
            texts.append(m.group(0))
            key = ("min_size", "max_size") if is_len else ("lo", "hi")
            c[name][key[0]] = int(lo)
            if re.fullmatch(r"-?\d+", hi): c[name][key[1]] = int(hi)
            else: c[name]["hi_expr"] = hi
    for s in _sentences(doc):
        low = " ".join(s.lower().split())
        hit = [p for p in names if re.search(rf"\b{re.escape(p)}\b", s)]
        ints = [p for p in names if fams[p] == "int"]
        lists = [p for p in names if fams[p].startswith(("list", "tuple"))]
        if re.search(r"\bpositive (integer|number|int)", low):
            for p in (hit or ints[:1]):
                if fams[p] == "int": c[p]["lo"] = max(1, c[p].get("lo", 1)); texts.append(f"{p} positive")
        if re.search(r"non-?negative", low):
            for p in (hit or ints[:1]):
                c[p]["lo"] = max(0, c[p].get("lo", 0)); texts.append(f"{p} non-negative")
        if re.search(r"non-?empty", low):
            colls = [q for q in names if fams[q].startswith(("list", "tuple")) or fams[q] in ("str", "dict")]
            for p in ([q for q in hit if q in colls] or colls[:1]):
                c[p]["min_size"] = max(1, c[p].get("min_size", 1)); texts.append(f"{p} non-empty")
        m = re.search(r"less than (\d+)", low)
        if m and hit:
            for p in hit: c[p]["hi"] = int(m.group(1)) - 1; texts.append(f"{p} < {m.group(1)}")
        for m in re.finditer(r"\b(?:modulo|mod|divisible by|divided by)\s+(\w+)", s):
            if m.group(1) in c: c[m.group(1)]["lo"] = max(1, c[m.group(1)].get("lo", 1)); texts.append(f"{m.group(1)} is a divisor (>= 1)")
        m = re.search(r"\bformat:?\s*([A-Za-z]+(?:[-/.:][A-Za-z]+)+)", s)
        if m: texts.append(f"format {m.group(1)}")
        if "only" in low:
            for k, cs in CHARSETS.items():
                if k in low: texts.append(f"alphabet only {cs}"); break
    quoted = sorted({q for q in re.findall(r"'([^'\s])'", doc) + re.findall(r'"([^"\s])"', doc)})
    return c, list(dict.fromkeys(texts)), quoted


def concept_lines(prompt, entry):
    name, params, doc, pvals = parse(prompt, entry)
    fams = {}
    for i, (p, ann) in enumerate(params):
        seen = sorted({_fam(v) for v in pvals[p]})
        fams[p] = _ann_fam(ann) or (seen[0] if len(seen) == 1 else ("int" if set(seen) <= {"int", "bool"} else "Any"))
    cons, texts, quoted = constraints(doc, params, fams)
    alpha = next((t.split("only ", 1)[1] for t in texts if t.startswith("alphabet only")), None)
    fmt = next((t.split(" ", 1)[1] for t in texts if t.startswith("format ")), None)
    lines, wit = [], {}
    for i, (p, ann) in enumerate(params):
        f, c = fams[p], cons[p]
        vals = pvals[p]
        nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        src = "annotation" if ann else ("docstring examples" if vals else "unknown")
        lines.append(f"- param `{p}`: {f} (type from {src})")
        if f in ("int", "float"):
            neg = any(v < 0 for v in nums)
            lo = c.get("lo", None if neg or not nums else 0)
            hi = c.get("hi")
            span = f"examples cover {min(nums)}..{max(nums)}; " if nums else ""
            dom = f"[{lo if lo is not None else '-inf'}, {hi if hi is not None else '+inf'}]"
            lines.append(f"- domain `{p}`: {dom} ({span}{'negatives appear in examples' if neg else 'lower bound from docstring/examples'})")
            if f == "int":
                b = lo if lo is not None else 0
                edges = [b, b + 1, b + 2] + ([-1] if lo is None else []) + ([10**4, BIG] if hi is None else [hi - 1, hi])
                rel = c.get("hi_expr", "")
                q = re.fullmatch(r"len\((\w+)\)", rel)
                if q:  # upper bound is the size of another argument: draw that argument first
                    edges = [b, b + 1, rel + " - 1", rel]
                lines.append(f"- edges `{p}`: {', '.join(map(str, dict.fromkeys(edges)))} (lower bound, just above it, "
                             f"large; values beyond the largest example)")
                hi_s = rel if q else (hi if hi is not None else 10**6)
                lines.append(f"- strategy `{p}`: st.integers(min_value={lo}, max_value={hi_s})" + (
                             f" drawn after `{q.group(1)}` (st.data() or flatmap)" if q else ""))
                big = cons[q.group(1)].get("max_size", 1000) if q else (hi if hi is not None else 10**4)
                wit[p] = [b, b + 1, big]
            else:
                lines.append(f"- edges `{p}`: 0.0, -0.0, 1e-09, -1.5, 1e+09 (no nan/inf unless documented)")
                lines.append(f"- strategy `{p}`: st.floats(min_value={lo if lo is not None else -1e9}, max_value=1e9, allow_nan=False, allow_infinity=False)")
                wit[p] = [0.0, 1e-09, 1e9]
        elif f == "str":
            al = alpha or "".join(dict.fromkeys("".join(quoted) + "".join(quoted).upper())) or None
            edges = ["''", "single char", "' '", "leading/trailing spaces", "2 and 3+ consecutive spaces",
                     "mixed case", "non-ASCII 'é'", "length 10**4"]
            if quoted: edges.insert(1, f"docstring characters {' '.join(quoted)} at start, middle, end, upper case")
            if alpha: edges = ["''", f"only {alpha!r}", "unbalanced/odd counts", "long run of one char", "length 10**4"]
            if fmt:
                fields = re.findall(r"[A-Za-z]+", fmt)
                rx = re.sub(r"[A-Za-z]+", lambda m: r"\\d{%d}" % len(m.group(0)), fmt)
                edges = ["''", f"well-formed {fmt} with every field at its minimum, maximum and just outside "
                         f"(0, 1, max, max+1)", "wrong separator", "wrong field widths", "missing/extra field",
                         "surrounding spaces"]
                lines.append(f"- edges `{p}`: {', '.join(edges)}")
                lines.append(f"- strategy `{p}`: st.one_of(st.from_regex(r'{rx}', fullmatch=True), st.text(max_size=20))")
                sep = re.sub(r"[A-Za-z]+", "{}", fmt)
                wit[p] = [repr(sep.format(*("0" * len(f) for f in fields))), repr(sep.format(*("0" * (len(f) - 1) + "1" for f in fields))),
                          repr(sep.format(*("9" * len(f) for f in fields)))]
                continue
            lines.append(f"- edges `{p}`: {', '.join(edges)}")
            mn = c.get("min_size", 0)
            lines.append(f"- strategy `{p}`: st.text({f'alphabet={al!r}, ' if al else ''}min_size={mn}, max_size=200)")
            wit[p] = ["''" if mn == 0 else repr((al or "a")[0]), repr((al or "a ")[:2] * 2), repr((al or "ab")[-1] * 3)]
        elif f.startswith(("list", "tuple")):
            inner = f[f.index("[") + 1:-1]
            mn, mx = c.get("min_size", 0), c.get("max_size")
            if f.startswith("tuple"):
                pair = [n for e in vals for n in e if isinstance(n, (int, float))]
                neg = any(n < 0 for n in pair)
                lines.append(f"- edges `{p}`: degenerate (a, a), touching endpoints, disjoint, nested, "
                             f"{'negative endpoints, ' if neg else ''}huge endpoints ({BIG})")
                lines.append(f"- strategy `{p}`: st.tuples(st.integers(), st.integers()).map(sorted).map(tuple)")
                wit[p] = ["(0, 0)", "(-5, 5)" if neg else "(0, 5)", f"(0, {BIG})"]
            else:
                el = {"int": "st.integers()", "float": "st.floats(allow_nan=False)", "str": "st.text()"}.get(
                    inner, "st.one_of(st.integers(), st.booleans(), st.floats(allow_nan=False), st.text(), st.none(), st.lists(st.integers()), st.dictionaries(st.text(), st.integers()))")
                edges = (["[]"] if mn == 0 else []) + ["[x]", "duplicates", "all equal", "sorted / reversed",
                                                        "negative and zero elements", f"length {mx or '10**4'}"]
                if inner == "Any": edges.insert(1, "bool values (True is an int subclass), floats like 1.0, None, nested containers")
                lines.append(f"- edges `{p}`: {', '.join(edges)}")
                lines.append(f"- strategy `{p}`: st.lists({el}, min_size={mn}, max_size={mx or 1000})")
                wit[p] = ["[]" if mn == 0 else "[0]", "[True, 1, 1.0]" if inner == "Any" else "[-1, 0, 0, 100]",
                          "[0] * " + str(mx or 1000)]
        elif f == "dict":
            lines.append(f"- edges `{p}`: {{}}, one key, lower/UPPER/Mixed-case str keys, non-str keys (int) "
                         f"in first and in later positions, more than 2 keys")
            lines.append(f"- strategy `{p}`: st.dictionaries(st.one_of(st.text(), st.integers()), st.text(), max_size=10)")
            wit[p] = ["{}", "{'a': 'x', 'b': 'y', 5: 'z'}", "{'A': 'x', 'B': 'y', 'c': 'z'}"]
        else:
            lines.append(f"- edges `{p}`: None, 0, '', [], mixed types")
            lines.append(f"- strategy `{p}`: st.from_type(object)")
            wit[p] = ["None", "0", "''"]
    for t in texts:
        lines.append(f"- docstring constraint: {t}")
    for p in params:
        if "hi_expr" in cons[p[0]]: lines.append(f"- docstring constraint: {p[0]} <= {cons[p[0]]['hi_expr']} (draw it from the other argument)")
    for j in range(3):  # witnesses: all-lower, all-just-above, all-large/upper
        lines.append(f"- witness: @example({', '.join(f'{p}={wit[p][j]}' for p, _ in params)})")
    return name, params, fams, lines


def _rename(lines, src, dst):
    """Rename donor (name, params) onto target (name, params); repair @example kwargs to the target signature."""
    (sname, sparams), (dname, dparams) = src, dst
    sp, dp = [p for p, _ in sparams], [p for p, _ in dparams]
    mapping = {s: dp[i % len(dp)] for i, s in enumerate(sp)}
    out = []
    for ln in lines:
        if ln.startswith("- witness: @example("):
            kw = dict(re.findall(r"(\w+)=((?:\[[^\]]*\](?: \* \d+)?|\([^)]*\)|\{[^}]*\}|'[^']*'|[^,)]+))", ln[len("- witness: @example("):-1]))
            vals = [kw[s] for s in sp if s in kw]
            ln = "- witness: @example(" + ", ".join(f"{p}={vals[i % len(vals)]}" for i, p in enumerate(dp)) + ")"
        else:
            ln = re.sub(rf"\b{re.escape(sname)}\b", dname, ln)
            ln = re.sub(r"`(\w+)`", lambda m: f"`{mapping.get(m.group(1), m.group(1))}`", ln)
            if ln.startswith("- docstring constraint: "):
                ln = re.sub(r"\b(\w+)\b", lambda m: mapping.get(m.group(1), m.group(1)), ln)
        out.append(ln)
    return out


def derangement(sigs, seed=0):
    rng = random.Random(seed)
    idx = list(range(len(sigs)))
    for _ in range(10000):
        perm = idx[:]; rng.shuffle(perm)
        if all(perm[i] != i and sigs[perm[i]] != sigs[i] for i in idx):
            return perm
    raise RuntimeError("no derangement")


def _cat(line):
    return re.match(r"- (param|domain|edges|strategy|docstring constraint|witness)", line).group(1)


def _pname(line):
    m = re.search(r"`(\w+)`", line)
    return m.group(1) if m else None


def build(prompts):
    """prompts: {task: (prompt, entry)} -> {task: {'concept': [...], 'placebo': [...], 'donors': [...]}}

    Placebo = line-by-line substitution: each concept line is replaced by an unused line of the SAME category
    (param/domain/edges/strategy/docstring constraint/witness) taken from the donor (derangement, different
    signature), then from the following tasks; donor names are renamed onto this task's function/parameters.
    Same line count, same category order, same format; content belongs to other tasks."""
    info = {t: concept_lines(*prompts[t]) for t in TASKS}
    sigs = [tuple(info[t][2].values()) for t in TASKS]
    perm = derangement(sigs)
    out = {}
    for i, t in enumerate(TASKS):
        name, params, _, lines = info[t]
        order = [TASKS[perm[i]]] + [TASKS[(perm[i] + k) % len(TASKS)] for k in range(1, len(TASKS))]
        pool = [(d, l) for d in order if d != t for l in _rename(info[d][3], (info[d][0], info[d][1]), (name, params))]
        used, plac, donors = set(), [], []
        for L in lines:
            c, p = _cat(L), _pname(L)
            cand = [k for k, (d, l) in enumerate(pool) if k not in used and _cat(l) == c and _pname(l) == p] or \
                   [k for k, (d, l) in enumerate(pool) if k not in used and _cat(l) == c] or \
                   [k for k, (d, l) in enumerate(pool) if k not in used and _cat(l) != "witness"]
            k = cand[0]; used.add(k)
            d, l = pool[k]
            if p and _pname(l) and _pname(l) != p:
                l = l.replace(f"`{_pname(l)}`", f"`{p}`")
            plac.append(l)
            if d not in donors: donors.append(d)
        out[t] = {"concept": lines, "placebo": plac, "donors": donors}
    return out


def block(lines):
    return HEADER + "\n" + "\n".join(lines) + "\n"


def load_prompts(path=HERE / "data" / "humaneval.jsonl"):
    rows = {}
    for line in open(path):
        r = json.loads(line)
        n = int(r["task_id"].split("/")[1])
        if n in TASKS:
            rows[n] = (r["prompt"], r["entry_point"])  # prompt + entry point only; canonical_solution/test ignored
    return rows


if __name__ == "__main__":
    prompts = load_prompts()
    res = build(prompts)
    summ = {}
    for t, r in res.items():
        for arm in ("concept", "placebo"):
            d = HERE / "concepts" / arm
            d.mkdir(parents=True, exist_ok=True)
            (d / f"HumanEval_{t}.txt").write_text(block(r[arm]))
        # self-check: same line count, every placebo witness parses as a call with exactly the target's kwargs
        assert len(r["concept"]) == len(r["placebo"]), t
        params = [p for p, _ in parse(*prompts[t])[1]]
        for l in r["concept"] + r["placebo"]:
            if l.startswith("- witness: "):
                call = ast.parse(l[len("- witness: @"):], mode="eval").body
                assert [k.arg for k in call.keywords] == params, (t, l)
        summ[t] = {"lines": len(r["concept"]), "concept_chars": len(block(r["concept"])),
                   "placebo_chars": len(block(r["placebo"])), "donors": r["donors"]}
    (HERE / "concepts" / "summary.json").write_text(json.dumps(summ, indent=1))
    for t in TASKS:
        print(t, summ[t])
    if "-v" in sys.argv:
        for t in TASKS:
            print(f"===== {t} CONCEPT\n" + "\n".join(res[t]["concept"]) + f"\n----- PLACEBO\n" + "\n".join(res[t]["placebo"]))
