#!/usr/bin/env python3
"""Offline annotator check (no LLM) over the built structures of one dataset.

Q1  Do gold-patched functions carry tags at a different rate than the other functions of the same files?
Q1b The same for ruff warnings (the `ide` arm's tags, from prepare.py lint), side by side with the concept tag rate.
Q2  Does the concept of the patch lines appear in the tags of the patched (pre-patch) function, which is what the
    concept arm shows? Patch concepts = facts of the post-patch function located on added lines (what the fix adds);
    compared with how often the other candidate functions of the same file carry that concept (chance).

usage: python check_tags.py <dataset> [--ids FILE|ID,ID] [--limit N]
       python check_tags.py selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from prepare import HUNK, STRUCT, VENDOR, file_spans, gt_from_patch, load_rows, locate, patch_changes

sys.path.append(str(Path(__file__).resolve().parent.parent))
from concept_annotator_py.functions import annotate_function  # noqa: E402

CONCEPTS = [f"C{i}" for i in range(1, 9)]


def function_texts(structure: dict) -> dict[tuple[str, str], tuple[int, list[str]]]:
    """(file, "Class.method" | "func") -> (start line, source lines), as CoSIL's structure lists them."""
    sys.path.insert(0, str(VENDOR))
    from CoSIL.util.preprocess_data import extract_structure

    _, classes, functions = extract_structure(structure)
    out = {}
    for c in classes:
        for m in c["methods"]:
            out.setdefault((c["file"], f"{c['name']}.{m['name']}"), (m["start_line"], m["method_content"]))
    for f in functions:
        out.setdefault((f["file"], f["name"]), (f["start_line"], f["text"]))
    return out


def apply_patch(old: list[str], patch: str, path: str) -> list[str]:
    """Post-patch lines of `path` (the gold patch applies cleanly to the base commit)."""
    out, i, rem_old, rem_new, mine = [], 0, 0, 0, False
    for line in patch.splitlines():
        if rem_old > 0 or rem_new > 0:
            if line.startswith("\\"):
                continue
            tag = line[:1]
            if tag != "+":
                rem_old -= 1
                if mine and tag != "-":
                    out.append(old[i])
                i += mine
            if tag != "-":
                rem_new -= 1
                if mine and tag == "+":
                    out.append(line[1:])
            continue
        if line.startswith("--- "):
            mine = line[4:].strip().removeprefix("a/") == path
        elif m := HUNK.match(line):
            rem_old, rem_new = int(m[2] or 1), int(m[4] or 1)
            if mine:
                start = int(m[1]) - (1 if rem_old else 0)
                out += old[i:start]
                i = start
    return out + old[i:]


def concepts_of(text: list[str], start: int) -> tuple[set[str], list[dict]]:
    ann = annotate_function("\n".join(text), start - 1)
    return set(ann["concepts"]), ann["facts"]


def check_instance(row: dict, structure: dict, ide: set | None = None) -> dict:
    """ide: {(file, label, start)} of functions with ruff warnings, or None when the instance is not linted."""
    sys.path.insert(0, str(VENDOR))
    from get_repo_structure.get_repo_structure import parse_python_file

    _, gold = gt_from_patch(row["patch"], structure)
    gold = [(f, s) for f, s in gold if s[0] != "class"]
    texts = function_texts(structure)
    files_text = {k: v for k, v in _file_texts(structure).items() if k in {f for f, _ in gold}}
    gold_keys = {(f, s[1]) for f, s in gold}
    res = {"gold": [], "other": [], "added": []}
    for (f, label), (start, text) in texts.items():
        if f in files_text:
            res["gold" if (f, label) in gold_keys else "other"].append(
                (f, sorted(concepts_of(text, start)[0]), None if ide is None else (f, label, start) in ide))
    changes = patch_changes(row["patch"])
    for f in files_text:
        new = apply_patch(files_text[f], row["patch"], f)
        ci, fn, _ = parse_python_file(None, "\n".join(new))
        new_spans = file_spans({"x.py": {"classes": ci, "functions": fn, "text": new}})["x.py"]
        others = [c for g, c, _ in res["other"] if g == f]
        for line in sorted(changes[f]["added_new"]):
            s = locate(new_spans, line)
            if s is None or (f, s[1]) not in gold_keys:
                continue
            _, facts = concepts_of(new[s[4] - 1:s[5]], s[4])
            start, text = texts[(f, s[1])]
            base = concepts_of(text, start)[0]
            for c in {x["concept"] for x in facts if x["line"] == line}:
                res["added"].append({"fn": f"{f}::{s[1]}", "concept": c, "in_base_tags": c in base,
                                     "chance": sum(c in o for o in others) / len(others) if others else None})
    # one record per (function, concept)
    res["added"] = list({(a["fn"], a["concept"]): a for a in res["added"]}.values())
    return res


def _file_texts(structure: dict) -> dict[str, list[str]]:
    sys.path.insert(0, str(VENDOR))
    from CoSIL.util.preprocess_data import extract_structure
    return {p: t for p, t in (x for x in extract_structure(structure)[0] if isinstance(x, tuple))}


def main(ds: str, ids: str | None, limit: int | None) -> None:
    from scipy.stats import fisher_exact

    gold, other, added, n = [], [], [], 0
    ide_gold, ide_other = [], []  # (has concept tag, has ruff warning) per function, linted instances only
    for row in load_rows(ds, ids, limit):
        p = STRUCT / ds / f"{row['instance_id']}.json"
        if not p.exists():
            continue
        lp = p.with_suffix(".lint.json")
        ide = {(f, f"{c}.{nm}" if c else nm, st) for f, rows in json.load(open(lp))["tags"].items()
               for c, nm, st, _ in rows} if lp.exists() else None
        r = check_instance(row, json.load(open(p))["structure"], ide)
        n += bool(r["gold"])
        gold += [c for _, c, _ in r["gold"]]
        other += [c for _, c, _ in r["other"]]
        ide_gold += [(bool(c), w) for _, c, w in r["gold"] if w is not None]
        ide_other += [(bool(c), w) for _, c, w in r["other"] if w is not None]
        added += r["added"]
    if not gold:
        print(f"[check_tags] {ds}: no instances with built structures and gold functions")
        return
    tg, to = sum(map(bool, gold)), sum(map(bool, other))
    p = fisher_exact([[tg, len(gold) - tg], [to, len(other) - to]])[1]
    print(f"[check_tags] {ds}: {n} instances; gold functions {len(gold)}, other functions in the gold files {len(other)}")
    print(f"Q1 tagged: gold {tg / len(gold):.1%} vs other {to / max(len(other), 1):.1%} (Fisher p={p:.3g}); "
          f"mean #concepts gold {sum(map(len, gold)) / len(gold):.2f} vs other {sum(map(len, other)) / max(len(other), 1):.2f}")
    if ide_gold:
        wg, wo = sum(w for _, w in ide_gold), sum(w for _, w in ide_other)
        pw = fisher_exact([[wg, len(ide_gold) - wg], [wo, len(ide_other) - wo]])[1]
        allf = ide_gold + ide_other
        print(f"Q1b ruff warnings: gold {wg / len(ide_gold):.1%} vs other {wo / max(len(ide_other), 1):.1%} "
              f"(Fisher p={pw:.3g}); tag rate on the same {len(allf)} functions: concept "
              f"{sum(c for c, _ in allf) / len(allf):.1%} vs ide {sum(w for _, w in allf) / len(allf):.1%}")
    cg, co = Counter(c for x in gold for c in x), Counter(c for x in other for c in x)
    print("   per concept (gold vs other): " + "  ".join(
        f"{c} {cg[c] / len(gold):.0%}/{co[c] / max(len(other), 1):.0%}" for c in CONCEPTS))
    if added:
        hit = sum(a["in_base_tags"] for a in added)
        ch = [a["chance"] for a in added if a["chance"] is not None]
        print(f"Q2 concepts the fix adds (on added lines): {len(added)} (function, concept) pairs in "
              f"{len({a['fn'] for a in added})} functions; already in the pre-patch tags {hit / len(added):.1%} vs "
              f"{sum(ch) / max(len(ch), 1):.1%} for other functions of the same file (chance)")
        by = Counter(a["concept"] for a in added)
        print("   by concept (n, in tags): " + "  ".join(
            f"{c} {by[c]},{sum(a['in_base_tags'] for a in added if a['concept'] == c) / by[c]:.0%}" for c in CONCEPTS if by[c]))


def selftest() -> None:
    old = ["def f(x):", "    return x[0]", "", "def g():", "    pass"]
    patch = ("--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,4 @@\n def f(x):\n+    if x is None:\n+        return None\n"
             "     return x[0]\n@@ -5,0 +8,1 @@\n+    return 1\n")
    new = apply_patch(old, patch, "m.py")
    assert new == ["def f(x):", "    if x is None:", "        return None", "    return x[0]", "", "def g():",
                   "    pass", "    return 1"], new
    structure = {"m.py": {"classes": [], "functions": [
        {"name": "f", "start_line": 1, "end_line": 2, "text": old[:2]},
        {"name": "g", "start_line": 4, "end_line": 5, "text": old[3:]}], "text": old}}
    assert gt_from_patch(patch, structure)[0] == ["m.py", "m.py::f", "m.py::g"]
    r = check_instance({"patch": patch}, structure)
    assert {a["fn"]: a["concept"] for a in r["added"]}["m.py::f"] == "C1" and not r["added"][0]["in_base_tags"], r
    print("[selftest] ok: apply_patch, gold location, added-line concepts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    selftest() if a.dataset == "selftest" else main(a.dataset, a.ids, a.limit)
