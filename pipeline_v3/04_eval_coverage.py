#!/usr/bin/env python3
"""04 - EXECUTED eval + TEST-COVERAGE (chay LOCAL, khong GPU).

An `results_v3.json` (tai tu Kaggle) = {seed: {cond: [records]}}, record co:
  func, target, cwe, family_pred, lines_concept, output.

Do:
  - FIRES        : test compile + chay -> ASAN/UBSAN bao loi (chi tinh tren target=1)   [BUG CAUGHT]
  - false_fire   : test lam ham AN TOAN (target=0) crash oan                             [FALSE ALARM]
  - ConceptCov   : ty le DONG RUI RO cua ham duoc test cham toi
                     * exec (gcov) neu build duoc; * static reachability neu khong        [cov_kind]

Coverage 'ca hai': gcov noi build duoc, reachability tinh cho phan con lai.
Chay:  python pipeline_v3/04_eval_coverage.py results_v3.json
"""
import os, re, sys, json, shutil, tempfile, subprocess, collections

RISK = {2, 3, 4, 5, 6}  # ptr_deref, buffer_allocation, buffer_access, bound_check, free
CXX = next((c for c in ("cc", "gcc", "clang") if shutil.which(c)), None)
GCOV = next((c for c in ("gcov",) if shutil.which(c)), None)  # llvm-cov gcov cung ten 'gcov' tren nhieu he
HEADER = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n"
          "#include <stdint.h>\n#include <assert.h>\n")
_KW = {"if", "else", "for", "while", "return", "int", "void", "char", "const", "static",
       "struct", "sizeof", "unsigned", "long", "short", "size_t", "NULL", "nullptr", "case", "switch"}


def extract_code(text):
    m = re.search(r"```[a-zA-Z0-9+_-]*\s*([\s\S]*?)```", text or "")
    return (m.group(1) if m else (text or "")).strip()


def focal(func):
    m = re.search(r"([A-Za-z_]\w*)\s*\([^{;]*\)\s*(?:/\*[\s\S]*?\*/\s*)?\{", func)
    return m.group(1) if m else None


def risky_lines(rec):
    lc = rec.get("lines_concept") or {}
    return [int(i) for i, v in lc.items() if any(len(v) > j and v[j] for j in RISK)]


def idents(s):
    return set(re.findall(r"[A-Za-z_]\w*", s)) - _KW


def static_reach(rec, test):
    """Reachability tinh: ty le dong rui ro co identifier xuat hien trong test (gate: co goi focal)."""
    rl = risky_lines(rec)
    if not rl:
        return None
    fn = focal(rec["func"])
    if not (fn and re.search(r"\b" + re.escape(fn) + r"\s*\(", test)):
        return 0.0
    toks = idents(test)
    lines = rec["func"].split("\n")
    hit = 0
    for i in rl:
        if 0 <= i < len(lines) and (idents(lines[i]) & toks):
            hit += 1
    return hit / len(rl)


def build_unit(rec, test):
    """Dung 1 chuong trinh C: neu test da tu chua (co main) -> dung nguyen;
    neu chi la snippet goi focal -> ghep [func + test] (van co the fail vi thieu kieu ngoai)."""
    if "main" in test and rec["func"].split("(")[0].split()[-1] not in test:
        return HEADER + test                      # test tu chua (thuong tu 120b PoC-style)
    return HEADER + rec["func"] + "\n\n" + test    # ghep func + test


def compile_run_cov(src, timeout=20):
    """Compile (ASAN + coverage) + chay. Tra {compiles, fires, exec_lines|None}."""
    if not CXX or len(src) < 20 or "main" not in src:
        return {"compiles": 0, "fires": 0, "exec_lines": None}
    d = tempfile.mkdtemp(); cf = os.path.join(d, "t.c"); binf = os.path.join(d, "t.bin")
    open(cf, "w").write(src)
    try:
        r = subprocess.run([CXX, "-fsanitize=address,undefined", "--coverage", "-g", "-O0", "-w",
                            cf, "-o", binf], capture_output=True, timeout=timeout, cwd=d)
    except Exception:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0, "exec_lines": None}
    if r.returncode != 0:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0, "exec_lines": None}
    fires = 0
    try:
        run = subprocess.run([binf], capture_output=True, timeout=timeout, cwd=d,
                             env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0", "UBSAN_OPTIONS": "halt_on_error=1"})
        err = (run.stderr or b"").decode(errors="ignore")
        fires = 1 if ("AddressSanitizer" in err or "runtime error" in err or "ERROR:" in err
                      or run.returncode < 0 or run.returncode >= 128) else 0
    except subprocess.TimeoutExpired:
        pass
    exec_lines = _gcov_exec_lines(d) if GCOV else None
    shutil.rmtree(d, ignore_errors=True)
    return {"compiles": 1, "fires": fires, "exec_lines": exec_lines}


def _gcov_exec_lines(d):
    """Tra ve set so-dong (1-based, theo file t.c da bao HEADER) duoc thuc thi (count>0)."""
    try:
        subprocess.run([GCOV, "t.c"], capture_output=True, timeout=20, cwd=d)
        gpath = os.path.join(d, "t.c.gcov")
        if not os.path.exists(gpath):
            return None
        ex = set()
        for line in open(gpath, errors="ignore"):
            parts = line.split(":", 2)
            if len(parts) < 2:
                continue
            cnt = parts[0].strip(); ln = parts[1].strip()
            if not ln.isdigit():
                continue
            if cnt not in ("-", "#####") and cnt and cnt[0].isdigit():
                ex.add(int(ln))
        return ex
    except Exception:
        return None


def concept_cov(rec, test, exec_lines):
    """Tra ve (ratio, kind). exec neu co gcov; nguoc lai static reachability."""
    rl = risky_lines(rec)
    if not rl:
        return (None, "none")
    if exec_lines is not None:
        # offset: func bat dau sau HEADER (HEADER co N dong) trong unit '[HEADER + func + test]'
        off = HEADER.count("\n")
        hit = sum(1 for i in rl if (i + off + 1) in exec_lines)
        return (hit / len(rl), "exec")
    sr = static_reach(rec, test)
    return (sr, "static")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "results_v3.json"
    if not os.path.exists(path):
        raise SystemExit("Thieu %s (tai results_v3.json tu Kaggle)." % path)
    if not CXX:
        print("[warn] khong co compiler -> chi do coverage TINH")
    data = json.load(open(path))
    seeds = list(data)
    conds = list(data[seeds[0]])

    # agg[cond] = {compiles,fires,false_fire,n_pos,n_neg, cov_exec[list], cov_static[list]}
    agg = {c: {"compiles": 0, "fires": 0, "false_fire": 0, "n_pos": 0, "n_neg": 0,
               "cov": [], "cov_exec": 0, "cov_static": 0} for c in conds}
    fam_cov = {c: collections.defaultdict(list) for c in conds}

    for s in seeds:
        for c in conds:
            for rec in data[s][c]:
                test = extract_code(rec.get("output"))
                unit = build_unit(rec, test)
                r = compile_run_cov(unit)
                a = agg[c]
                a["compiles"] += r["compiles"]
                if rec.get("target") == 1:
                    a["n_pos"] += 1; a["fires"] += r["fires"]
                else:
                    a["n_neg"] += 1; a["false_fire"] += r["fires"]
                ratio, kind = concept_cov(rec, test, r["exec_lines"])
                if ratio is not None:
                    a["cov"].append(ratio)
                    a["cov_exec" if kind == "exec" else "cov_static"] += 1
                    fam_cov[c][rec.get("family_pred")].append(ratio)

    def mean(xs): return sum(xs) / len(xs) if xs else float("nan")

    print("compiler:", CXX, "| gcov:", GCOV, "| seeds:", seeds, "\n")
    print("%-14s %8s %10s %12s %12s %8s" % ("cond", "compile%", "FIRES(+)", "false_fire(-)", "ConceptCov", "cov(exec/stat)"))
    for c in conds:
        a = agg[c]; n = a["n_pos"] + a["n_neg"]
        comp = 100 * a["compiles"] / n if n else 0
        fires = 100 * a["fires"] / a["n_pos"] if a["n_pos"] else float("nan")
        ff = 100 * a["false_fire"] / a["n_neg"] if a["n_neg"] else float("nan")
        cov = mean(a["cov"])
        print("%-14s %7.0f%% %8.0f%% %11.0f%% %11.2f   %d/%d"
              % (c, comp, fires, ff, cov, a["cov_exec"], a["cov_static"]))
    print("\nFIRES = bat bug that (target=1). false_fire = bao dong gia (target=0, cang THAP cang tot).")
    print("ConceptCov = ty le dong rui ro duoc cham (exec gcov neu build duoc, nguoc lai static).")

    print("\n=== ConceptCov theo ho (family_pred), mean qua seed ===")
    fams = sorted({f for c in conds for f in fam_cov[c]}, key=lambda x: (x is None, x))
    print("  %-13s " % "family" + " ".join("%12s" % c for c in conds))
    for fam in fams:
        cells = [("%.2f" % mean(fam_cov[c][fam])) if fam_cov[c][fam] else "n/a" for c in conds]
        print("  %-13s " % fam + " ".join("%12s" % x for x in cells))


if __name__ == "__main__":
    main()
