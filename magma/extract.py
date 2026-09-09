#!/usr/bin/env python3
"""Trich bug Magma -> item benchmark. Nguon = patch THAT cua Magma (targets/<t>/patches/bugs/*.patch).

Moi patch chen `MAGMA_LOG("%MAGMA_BUG%", <fault_cond>)` tai vi tri bug + bao b?n va bang
`#ifdef MAGMA_ENABLE_FIXES`. Ta rut:
  bug_id, focal_file, focal_func (ham chua canary), fault_cond (dieu kien loi - CONCEPT, khong phai input),
  fix_hint (dong va them = bound/null check con THIEU o ban vuln).
Nguon ham vuln lay tu IMAGE vuln (source da fetch trong Docker), strip #ifdef MAGMA_* -> ban vuln sach,
roi dien concept qua load_annotator (tree-sitter, ConceptCoder). Corpus seed lam mo hinh mutation.

Chay TU REPO ROOT (sau setup.sh):  .venv/bin/python magma/extract.py [--target libpng]
"""
import os, sys, re, json, glob, subprocess, importlib.util, argparse

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "bench"))            # concepts
sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))      # common
from concepts import augment, family_of                    # noqa: E402
import common                                               # noqa: E402

MAGMA = os.path.join(ROOT, "vendor", "magma")
REPO_IN_IMG = "/magma/targets/%s/repo"                      # source da fetch trong image


def load_annotator():
    p = os.path.join(ROOT, "pipeline_v3", "02_extract_concept.py")
    spec = importlib.util.spec_from_file_location("extract_concept", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.load_annotator()


def _balanced(s, i):
    """Tu '(' tai s[i], tra chuoi ben trong den ')' can bang."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return s[i + 1:j]
    return s[i + 1:]


def _fault_readable(c):
    c = re.sub(r"\bMAGMA_AND\s*\(", "(", c)
    c = re.sub(r"\bMAGMA_OR\s*\(", "(", c)
    return re.sub(r"\s+", " ", c).strip()


_KW = {"int", "void", "char", "long", "short", "unsigned", "signed", "static", "const", "struct",
       "if", "for", "while", "switch", "return", "sizeof", "defined", "png_debug", "PNG_UNUSED"}


def _ctx_func(hunk_ctx):
    """Ten ham tu context sau '@@ .. @@' cua git (chu ky ham). Bo keyword/type. None neu preprocessor."""
    c = hunk_ctx.strip()
    if not c or c.startswith("#") or c.startswith("defined"):
        return None
    for name in reversed(re.findall(r"([A-Za-z_]\w*)\s*\(", c)):  # identifier-truoc-'(' cuoi, khong phai keyword
        if name not in _KW:
            return name
    return None


def parse_patch(path):
    """-> {bug_id, focal_file, focal_ctx, fault_cond} tu hunk chua MAGMA_LOG."""
    txt = open(path, errors="ignore").read()
    bug_id = os.path.basename(path)[:-6]
    cur_file, last_ctx = None, ""
    for line in txt.splitlines():
        m = re.match(r"\+\+\+ b/(.+)$", line)
        if m:
            cur_file = m.group(1).strip()
        mh = re.match(r"@@ .+ @@\s*(.*)$", line)
        if mh:
            last_ctx = mh.group(1)
        if "MAGMA_LOG" in line and "%MAGMA_BUG%" in line:
            paren = line.find("(", line.find("MAGMA_LOG"))
            inner = _balanced(line, paren)                 # "%MAGMA_BUG%", <cond>
            cond = inner[inner.find(",") + 1:].strip()
            return {"bug_id": bug_id, "focal_file": cur_file, "focal_ctx": _ctx_func(last_ctx),
                    "fault_cond": _fault_readable(cond)}
    return {"bug_id": bug_id, "focal_file": cur_file, "focal_ctx": None, "fault_cond": None}


def fam_of_cond(cond):
    """Ho loi tu dieu kien canary (khong leak input). free > null > int_overflow > oob."""
    c = (cond or "").lower()
    if "free" in c:
        return "uaf"
    if "null" in c:
        return "null_deref"
    if "<<" in c or "overflow" in c or "pixel_depth" in c or "row_factor" in c or "size_t)1" in c:
        return "int_overflow"
    if any(t in c for t in (">", "<", "length", "row_bytes", "num")):
        return "oob"
    return None


def slice_func_by_name(src, name):
    """Than ham `... name(...) { ... }` (brace-match tu dau ham). None neu khong thay."""
    if not name:
        return None
    for m in re.finditer(r"\b" + re.escape(name) + r"\s*\(", src):
        ob = src.find("{", m.end())
        semi = src.find(";", m.end())
        if ob < 0 or (0 <= semi < ob):                     # khai bao/loi goi (co ';' truoc '{') -> bo
            continue
        depth = 0
        for j in range(ob, len(src)):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    start = src.rfind("\n", 0, m.start()) + 1
                    return src[start:j + 1].strip()
    return None


def _fix_hint(path):
    """Dong '+' THEM boi ban va (trong #ifdef MAGMA_ENABLE_FIXES) = check con THIEU o ban vuln."""
    out, infix = [], False
    for line in open(path, errors="ignore"):
        s = line.rstrip("\n")
        if "MAGMA_ENABLE_FIXES" in s:
            infix = True; continue
        if infix and s.startswith("#endif"):
            infix = False; continue
        if infix and s.startswith("+"):
            t = s[1:].strip()
            if t and not t.startswith("#"):
                out.append(t)
    return " ; ".join(out[:4])


def img_cat(image, path):
    r = subprocess.run(["docker", "run", "--rm", "--platform", "linux/amd64",
                        "--entrypoint", "cat", image, path], capture_output=True, timeout=60)
    return r.stdout.decode(errors="ignore") if r.returncode == 0 else ""


def strip_magma(src):
    """Bo khoi #ifdef MAGMA_ENABLE_FIXES/CANARIES (giu #else = code vuln) -> source vuln sach."""
    out, skip = [], []
    for line in src.splitlines():
        st = line.strip()
        if re.match(r"#ifdef\s+MAGMA_ENABLE_(FIXES|CANARIES)", st):
            skip.append("fix"); continue
        if skip and st.startswith("#else"):
            skip[-1] = "keep"; continue
        if skip and st.startswith("#endif"):
            skip.pop(); continue
        if not skip or skip[-1] == "keep":
            out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default="libpng")
    a = ap.parse_args(); target = a.target
    image = "magma-%s-vuln" % target
    prog = os.path.basename(glob.glob(os.path.join(MAGMA, "targets", target, "corpus", "*"))[0])
    seeds = sorted(glob.glob(os.path.join(MAGMA, "targets", target, "corpus", prog, "*")))
    have_img = subprocess.run(["docker", "image", "inspect", image],
                              capture_output=True).returncode == 0
    if have_img:
        annotate = load_annotator()
    N = len(common.PROPS)

    items, srccache = [], {}
    for pt in sorted(glob.glob(os.path.join(MAGMA, "targets", target, "patches", "bugs", "*.patch"))):
        info = parse_patch(pt)
        if not info["fault_cond"] or not info["focal_file"]:
            print("  [skip] %s (khong parse duoc canary)" % os.path.basename(pt)); continue
        info["fix_hint"] = _fix_hint(pt)
        focal = info["focal_ctx"]
        func_src, concepts, lc, fam = "", [0] * N, {}, None
        if have_img and focal:
            f = info["focal_file"]
            if f not in srccache:
                srccache[f] = strip_magma(img_cat(image, "%s/%s" % (REPO_IN_IMG % target, f)))
            func_src = slice_func_by_name(srccache[f], focal) or ""
            if func_src:
                try:
                    concepts, lc = annotate(func_src)
                except Exception as e:
                    print("     [warn] annotate: %s" % str(e)[:70])
                concepts, lc = augment(func_src, concepts, lc)
                fam = family_of(func_src, lc)
        fam = fam or fam_of_cond(info["fault_cond"])        # fallback: ho tu dieu kien canary
        items.append({"id": "magma_%s_%s" % (target, info["bug_id"]), "bug_id": info["bug_id"],
                      "target": target, "program": prog, "focal_file": info["focal_file"],
                      "focal": focal, "fault_cond": info["fault_cond"], "fix_hint": info["fix_hint"],
                      "func_vuln": func_src, "concepts": concepts, "lines_concept": lc,
                      "family_pred": fam, "seed": os.path.basename(seeds[0]) if seeds else None,
                      "expect": "fires_on_vuln"})
        print("  [ok] %-8s file=%-12s func=%-22s fault=%s"
              % (info["bug_id"], info["focal_file"], focal, info["fault_cond"][:40]))

    os.makedirs(os.path.join(HERE, "items"), exist_ok=True)
    out = os.path.join(HERE, "items", "%s.jsonl" % target)
    with open(out, "w") as fh:
        for it in items:
            fh.write(json.dumps(it) + "\n")
    print("\n%d bug -> %s%s" % (len(items), out, "" if have_img else "  (KHONG co image -> thieu concept)"))


if __name__ == "__main__":
    main()
