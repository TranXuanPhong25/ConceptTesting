"""Rule-based bug-concept labels (C0-C8) from the part of the fixing patch inside each focal method.

Run in the container (needs the buggy checkouts in d4j_proj_base to map diff line numbers to the method):
    bash run/dock.sh -- python3 m2_concept_diag/labels.py
Writes m2_concept_diag/labels.jsonl, one record per focal method, in dataset order.
Offline analysis only: the patch never enters any generation prompt.
"""
import json, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "m2_concept_diag/labels.jsonl")

# A concept fires when the number of matches of one of its patterns differs between the removed (buggy) and the added
# (fixed) code lines of the method (compared as multisets of the matched text), i.e. the patch inserts, deletes or changes that construct. Evidence = matching lines.
RULES = {
    "C1": [r"(==|!=)\s*null\b", r"\bnull\s*(==|!=)", r"NullPointerException", r"requireNonNull|isNull\(|notNull\("],
    "C2": [r"\bis(Not)?(Empty|Blank)\s*\(", r"(length\(\)|\.length|size\(\))\s*(==|!=|>|<=|<|>=)\s*0\b",
           r"\b0\s*(==|!=|<|>=)\s*\w+\.(length|size)", r'""\.equals|equals\(""\)', r'==\s*""'],
    "C3": [r"(?<![<>=!&|+\-*/])(<=|>=|<|>)(?![<>=])", r"[+-]\s*1\b(?!\.)", r"\+\+|--", r"\blength\(\)|\.length\b|\bsize\(\)",
           r"\b(charAt|substring|subSequence|indexOf|lastIndexOf|regionMatches)\(", r"\w\[[^\]]+\]"],
    "C4": [r"\bthrow\b", r"\bcatch\s*\(", r"\btry\b", r"\w+(Exception|Error)\b"],
    "C5": [r"escape|Escape|quote|Quote|\\\\", r"\b(format|replace|replaceAll|trim|strip|normali[sz]e)\w*\(", r"\bappend\(\s*'[\\\"'`]"],
    "C6": [r"\b(long|double|float|short|byte|BigDecimal|BigInteger)\b", r"\b(Integer|Long|Double|Float)\.(MAX|MIN)_VALUE",
           r"\(\s*(int|long|double|float)\s*\)", r"\b\d+[LlFfDd]\b|\d\.\d", r"\bMath\.\w+|overflow|isNaN|isInfinite"],
    "C7": [r"\bchar\b|Character\.|codePoint|Locale|surrogate", r"'(\\.|[^'\\])'", r"to(Lower|Upper)Case"],
    "C8": [r"\bthis\.\w+\s*=[^=]", r"\bclone\(\)|\bcopyOf|new (Array|Hash|Linked|Tree)\w*\(\w+|unmodifiable|\breset\(",
           r"\bsynchronized\b"],
}


def code_only(line):
    """Drop comments/javadoc and collapse generics so '<' '>' in types do not look like relational operators."""
    s = line.strip()
    if s.startswith(("//", "*", "/*")):
        return ""
    s = re.sub(r"//.*$", "", s)
    s = re.sub(r'"(\\.|[^"\\])*"', lambda m: '""' if m.group() == '""' else '"S"', s)  # string literal contents
    for _ in range(3):
        s = re.sub(r"(?<=\w)<[\w\s,.?\[\]]*>", "", s)
    return s.strip()


def fields_rule(fields):
    names = [re.escape(n) for n in fields if n]
    return rf"^\s*({'|'.join(names)})\s*(=[^=]|\+=|-=|\+\+|--)|\b({'|'.join(names)})\.(add|put|remove|clear|set)\w*\(" if names else None


def label(removed, added, fields):
    rem = [code_only(l) for l in removed]; add = [code_only(l) for l in added]
    extra = {"C8": [fields_rule(fields)]} if fields_rule(fields) else {}
    concepts, evidence = [], {}
    for c, pats in RULES.items():
        for p in pats + extra.get(c, []):
            hits = lambda ls: Counter(re.sub(r"\s+", "", m.group()) for l in ls for m in re.finditer(p, l))
            nr, na = hits(rem), hits(add)
            if nr != na:
                ev = [f"-{l}" for l in rem if re.search(p, l)] + [f"+{l}" for l in add if re.search(p, l)]
                evidence.setdefault(c, []).append({"pattern": "<class-field mutation>" if p in extra.get(c, []) else p, "removed": sum(nr.values()), "added": sum(na.values()), "lines": ev})
        if c in evidence:
            concepts.append(c)
    return concepts or ["C0"], evidence


def method_range(lines, body):
    """0-based [start, end] line range of the method body in the file (stripped line sequence match)."""
    want = [l.strip() for l in body.splitlines() if l.strip()]
    have = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]
    for k in range(len(have) - len(want) + 1):
        if have[k][1] == want[0] and [h for _, h in have[k:k + len(want)]] == want:
            return have[k][0], have[k + len(want) - 1][0]
    return None


def hunks(diff):
    """Yield (buggy_line_no_1based, kind, text) per hunk line, kind '-' = removed by the fix, '+' = added by the fix.
    The Defects4J patches go fixed -> buggy (checked: their '+' side equals the buggy checkout), so the diff is inverted
    here. For '+' lines the line number is the buggy line the insertion precedes."""
    old = None
    for line in diff.splitlines():
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if m:
            old = int(m.group(1)); continue
        if old is None or line.startswith(("---", "+++", "\\")):
            continue
        kind = {"+": "-", "-": "+"}.get(line[:1], " ")
        yield old, kind, line[1:]
        if kind != "+":
            old += 1


def main():
    recs = [json.loads(l) for l in open(os.path.join(ROOT, "data/prompts/buggy_source_data_unified_invoked.jsonl"))]
    out = []
    for r in recs:
        bug = r["extra:project_name"].replace("_buggy", "")
        info = json.load(open(os.path.join(ROOT, f"data/d4j2_fix_info/{bug}/buggy_fix_info.json")))
        body, fields = r["source:source_method_code_format"], [m.group(1) for f in r.get("source_class_fields") or [] for m in [re.search(r"(\w+)\s*(=|;)", f)] if m]
        removed, added, all_rem, all_add, loc, mismatch, in_hunks = [], [], [], [], None, 0, []
        for fc in info["fixing_changes"]:
            path = fc["changed_class"][0]
            src = open(os.path.join(ROOT, f"d4j_proj_base/{bug}/buggy/{path}"), encoding="utf-8", errors="replace").read().splitlines()
            rng = method_range(src, body)
            if rng:
                loc = {"file": path, "start": rng[0] + 1, "end": rng[1] + 1}
            cur = []
            for no, kind, text in hunks(fc["diff"]):
                if kind != "+" and (no > len(src) or src[no - 1].rstrip() != text.rstrip()):
                    mismatch += 1  # diff side '-'/' ' must equal the buggy file (checks direction buggy -> fixed)
                if kind in "+-":
                    (all_rem if kind == "-" else all_add).append(text)
                inside = rng and (rng[0] + 1 <= no <= rng[1] + 1 if kind == "-" else rng[0] + 1 < no <= rng[1] + 1)
                if inside:
                    if kind in "+-":
                        (removed if kind == "-" else added).append(text)
                    cur.append(kind + text)
            if any(l[0] in "+-" for l in cur):  # keep the in-method part of the hunks, with context, fix direction
                in_hunks += cur
        in_method = bool(removed or added)
        concepts, evidence = label(removed, added, fields) if in_method else label(all_rem, all_add, fields)
        out.append({"idx": len(out), "project": r["extra:project_name"], "bug": bug, "sig": r["source:source_method_signature"],
                    "located": loc, "diff_lines_mismatch": mismatch, "patch_in_method": in_method,
                    "scope": "method" if in_method else "whole_patch", "concepts": concepts, "evidence": evidence,
                    "method_hunk": in_hunks, "changed_functions": sorted({q for fc in info["fixing_changes"] for cf in fc["changed_functions"] for q in cf["qualified_names"]})})
    with open(OUT, "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    print(f"methods {len(out)}; located {sum(bool(o['located']) for o in out)}; patch inside method {sum(o['patch_in_method'] for o in out)}; "
          f"diff/buggy-file line mismatches {sum(o['diff_lines_mismatch'] for o in out)}")
    print("concept counts:", sorted(Counter(c for o in out for c in o["concepts"]).items()))


if __name__ == "__main__":
    assert label(["if (i < n) {"], ["if (i <= n) {"], [])[0] == ["C3"]
    assert label(["return s.trim();"], ["if (s == null) return null;", "return s.trim();"], [])[0] == ["C1"]
    assert label(["x = foo();"], ["x = bar();"], [])[0] == ["C0"]
    assert code_only("Map<String, List<Integer>> m = new HashMap<String, List<Integer>>();").count("<") == 0
    main()
