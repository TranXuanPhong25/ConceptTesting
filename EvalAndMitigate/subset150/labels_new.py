"""Rule concept labels (m2's rules) for the new methods, plus their in-method fix hunks for the manual labels.

m2_concept_diag/labels.py's rule functions (label, method_range, hunks) are imported; its main() loop is copied below
because its input path is hard-coded. Differences: input = the new-method file, output path, the whole patch kept too. Offline analysis only (patch-derived).
usage (container): python3 subset150/labels_new.py  -> subset150/out/labels_rule_new.jsonl
"""
import importlib.util, json, os

REPO = "/repo"
s = importlib.util.spec_from_file_location("m2labels", f"{REPO}/m2_concept_diag/labels.py")
L = importlib.util.module_from_spec(s); s.loader.exec_module(L)
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked_s150new.jsonl"
OUT = f"{REPO}/subset150/out/labels_rule_new.jsonl"


def main():
    import re
    out = []
    for r in map(json.loads, open(SRC)):
        bug = r["extra:project_name"].replace("_buggy", "")
        info = json.load(open(f"{REPO}/data/d4j2_fix_info/{bug}/buggy_fix_info.json"))
        body = r["source:source_method_code_format"]
        fields = [m.group(1) for f in r.get("source_class_fields") or [] for m in [re.search(r"(\w+)\s*(=|;)", f)] if m]
        removed, added, all_rem, all_add, loc, mismatch, in_hunks = [], [], [], [], None, 0, []
        for fc in info["fixing_changes"]:
            path = fc["changed_class"][0]
            f = f"{REPO}/d4j_proj_base/{bug}/buggy/{path}"  # m2 change: a class the fix adds is absent from buggy (Closure_27)
            src = open(f, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(f) else []
            rng = L.method_range(src, body)
            if rng:
                loc = {"file": path, "start": rng[0] + 1, "end": rng[1] + 1}
            cur = []
            for no, kind, text in L.hunks(fc["diff"]):
                if kind != "+" and (no > len(src) or src[no - 1].rstrip() != text.rstrip()):
                    mismatch += 1
                if kind in "+-":
                    (all_rem if kind == "-" else all_add).append(text)
                inside = rng and (rng[0] + 1 <= no <= rng[1] + 1 if kind == "-" else rng[0] + 1 < no <= rng[1] + 1)
                if inside:
                    if kind in "+-":
                        (removed if kind == "-" else added).append(text)
                    cur.append(kind + text)
            if any(l[0] in "+-" for l in cur):
                in_hunks += cur
        in_method = bool(removed or added)
        concepts, evidence = L.label(removed, added, fields) if in_method else L.label(all_rem, all_add, fields)
        out.append({"new_idx": len(out), "project": r["extra:project_name"], "bug": bug, "sig": r["source:source_method_signature"],
                    "located": loc, "diff_lines_mismatch": mismatch, "patch_in_method": in_method,
                    "scope": "method" if in_method else "whole_patch", "concepts": concepts, "evidence": evidence,
                    "method_hunk": in_hunks, "whole_patch": [f"-{l}" for l in all_rem] + [f"+{l}" for l in all_add]})
    with open(OUT, "w") as f:
        f.writelines(json.dumps(o) + "\n" for o in out)
    print(f"methods {len(out)}; located {sum(bool(o['located']) for o in out)}; patch inside method {sum(o['patch_in_method'] for o in out)}; "
          f"diff/buggy-file line mismatches {sum(o['diff_lines_mismatch'] for o in out)}")


if __name__ == "__main__":
    main()
