"""$0 audit of agentic-pbt saved results: which property pattern produced tests and bug reports.

Usage: python -I pattern_audit.py <agentic-pbt/paper dir> <out.json>
Rule-based labels (test name + docstring first, then body shape); one label per test, first match wins.
The 8 patterns are the list in paper/hypo.md "Propose properties"; 'claim' and 'other' are outside the list.
"""
import ast
import collections
import csv
import glob
import json
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

INV_PAIRS = [("encode", "decode"), ("dumps", "loads"), ("dump", "load"), ("serialize", "deserialize"),
             ("compress", "decompress"), ("quote", "unquote"), ("escape", "unescape"), ("pack", "unpack"),
             ("encrypt", "decrypt"), ("parse", "format"), ("parse", "unparse"), ("to_", "from_"),
             ("marshal", "unmarshal"), ("tokenize", "untokenize"), ("join", "split"), ("str", "parse")]
OPS_PAIRS = [("add", "remove"), ("push", "pop"), ("insert", "delete"), ("connect", "disconnect"),
             ("register", "unregister"), ("set", "unset"), ("append", "pop"), ("put", "get"), ("set", "get"),
             ("acquire", "release"), ("open", "close"), ("create", "destroy"), ("enable", "disable")]

# (label, regex over name+docstring); order = priority
KEYWORDS = [
    ("round_trip", r"round.?trip|roundtrip|encode.?decode|serializ\w*.?deserializ|reversib"),
    ("inverse_ops", r"inverse|undo|cancel|add.?remove|push.?pop|connect.?disconnect|register.?unregister"),
    ("multi_impl", r"equivalen|reference|naive|\bvs\b|_vs_|matches|agree|same.as|consisten\w* with|differential|oracle|alternative"),
    ("math", r"idempot|commut|associat|distribut|identity|symmetr|monoton|transitiv|absorb|neutral"),
    ("confluence", r"confluen|order.?independ|order.doesn|any order|regardless of order"),
    ("metamorphic", r"metamorph|scal(e|ing)|shift|translat|permut|shuffl|reorder"),
    ("single_entry", r"no.?crash|not.?crash|doesn.?t.?crash|does.?not.?(raise|crash)|never.?(raise|crash)|robust|handles?.(any|arbitrary|all)|fuzz"),
    ("invariant", r"invariant|preserv|length|\blen\b|bound|range|non.?neg|positive|sorted|subset|unique|always|never|at most|at least"),
]


def calls_in(node):
    out = []
    for x in ast.walk(node):
        if isinstance(x, ast.Call):
            f = x.func
            out.append(f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else "")
    return [c.lower() for c in out if c]


def nested_same_call(node):
    for x in ast.walk(node):
        if isinstance(x, ast.Call) and x.args and isinstance(x.args[0], ast.Call):
            try:
                if ast.unparse(x.func) == ast.unparse(x.args[0].func):
                    return True
            except Exception:
                pass
    return False


def label(fn):
    doc = ast.get_docstring(fn) or ""
    text = (fn.name.replace("_", " ") + " " + doc).lower()
    for lab, rx in KEYWORDS:
        if re.search(rx, text):
            return lab, "keyword"
    cs = calls_in(fn)
    joined = " ".join(cs)
    for a, b in INV_PAIRS:
        if any(c.startswith(a) or c.endswith(a) for c in cs) and any(c.startswith(b) or c.endswith(b) for c in cs) and a != b:
            return "round_trip", "body"
    for a, b in OPS_PAIRS:
        if any(c.startswith(a) for c in cs) and any(c.startswith(b) for c in cs):
            return "inverse_ops", "body"
    if nested_same_call(fn):
        return "math", "body"
    asserts = [x for x in ast.walk(fn) if isinstance(x, ast.Assert)]
    if not asserts and not re.search(r"pytest\.raises|raise\b", ast.unparse(fn)):
        return "single_entry", "body"
    if any(re.search(r"\blen\(|isinstance\(|<=|>=|\bin\b|all\(|set\(|sorted\(", ast.unparse(a.test)) for a in asserts):
        return "invariant", "body"
    if re.search(r"docstring|document|claim|contract|spec|should|must|expected", text):
        return "claim", "keyword"
    return "other", "none"


def given_tests(src):
    try:
        tree = ast.parse(src)
    except Exception:
        return []
    return [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)
            and any("given" in ast.unparse(d) for d in x.decorator_list)]


def main(paper, out):
    res = os.path.join(paper, "results")
    # population: every Hypothesis test the agent wrote
    pop = collections.Counter()
    pop_how = collections.Counter()
    for f in glob.glob(os.path.join(res, "*/aux_files/*/*.py")):
        for fn in given_tests(open(f, errors="ignore").read()):
            lab, how = label(fn)
            pop[lab] += 1
            pop_how[how] += 1
    # bug reports: label the tests in the "Property-Based Test" block
    scores = {}
    for r in csv.DictReader(open(os.path.join(paper, "score_results_final.csv"))):
        scores[os.path.basename(r["file"])] = r
    reps = []
    for f in sorted(glob.glob(os.path.join(res, "*/bug_reports/*.md"))):
        s = open(f, errors="ignore").read()
        m = re.search(r"## Property-Based Test\s*```python\n(.*?)```", s, re.S)
        fns = given_tests(m.group(1)) if m else []
        lab = label(fns[0])[0] if fns else "no_test"
        bt = re.search(r"\*\*Bug Type\*\*:\s*(.+)", s)
        sc = scores.get(os.path.basename(f), {})
        reps.append({"file": os.path.relpath(f, res), "pattern": lab,
                     "bug_type": bt.group(1).strip() if bt else None,
                     "score": int(sc["score"]) if sc.get("score", "").isdigit() else None,
                     "valid": sc.get("valid") or None, "reportable": sc.get("reportable") or None})
    by = collections.defaultdict(list)
    for r in reps:
        by[r["pattern"]].append(r)
    tot_pop = sum(pop.values())
    table = []
    for lab in sorted(set(pop) | set(by), key=lambda k: -pop.get(k, 0)):
        rs = by.get(lab, [])
        sc = [r["score"] for r in rs if r["score"] is not None]
        table.append({"pattern": lab, "tests": pop.get(lab, 0), "tests_share": round(pop.get(lab, 0) / tot_pop, 3),
                      "reports": len(rs), "reports_share": round(len(rs) / len(reps), 3),
                      "reports_per_1k_tests": round(1000 * len(rs) / pop[lab], 1) if pop.get(lab) else None,
                      "mean_score": round(sum(sc) / len(sc), 2) if sc else None,
                      "score_ge_13": sum(s >= 13 for s in sc),
                      "labeled": sum(r["valid"] is not None for r in rs),
                      "valid": sum(r["valid"] == "1" for r in rs),
                      "reportable": sum(r["reportable"] == "1" for r in rs),
                      "bug_types": dict(collections.Counter(r["bug_type"] for r in rs).most_common(3))})
    json.dump({"tests_total": tot_pop, "label_source": dict(pop_how), "reports_total": len(reps),
               "table": table, "reports": reps}, open(out, "w"), indent=1)
    print(f"tests {tot_pop} label_source {dict(pop_how)} reports {len(reps)}")
    print(f"{'pattern':13} {'tests':>6} {'t%':>5} {'rep':>4} {'r%':>5} {'/1k':>5} {'score':>5} {'>=13':>4} {'lab':>3} {'val':>3} {'rpt':>3}")
    for t in table:
        print(f"{t['pattern']:13} {t['tests']:6} {t['tests_share']:5} {t['reports']:4} {t['reports_share']:5} "
              f"{t['reports_per_1k_tests'] or '-':>5} {t['mean_score'] or '-':>5} {t['score_ge_13']:4} {t['labeled']:3} {t['valid']:3} {t['reportable']:3}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
