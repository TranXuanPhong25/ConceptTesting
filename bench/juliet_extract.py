#!/usr/bin/env python3
"""Trich Juliet Test Suite -> schema benchmark (parametrized vuln/fixed), qua CUNG pipeline build().

Ho da ho tro (in-scope voi 8 concept memory-safety):
  CWE476 NULL Pointer Deref -> null_deref   (`*data`, `data[0]`, `data->f` tren con tro NULL)
  CWE416 Use-After-Free     -> uaf          (free(data) roi DEREF data sau do)
  CWE415 Double-Free        -> double_free  (free(data) HAI lan)

Tham-so-hoa: bo 'source flow' cua Juliet, focal(TYPE*) nhan input tu TEST (NULL, hoac buffer malloc).
Stub print-helper = NO-OP -> use dang `printLine(data)` (KHONG deref cu phap) se KHONG fire
-> self-check TU LOAI (chi giu case concept PHAT HIEN duoc). Flow-variant trung focal -> dedup.
CWE690 (calloc it khi NULL -> khong trigger duoc), CWE122/124 (attack hardcode trong struct/offset,
self-trigger, khong co input DOF) -> BO qua.

Chuan bi:  git clone --depth 1 --filter=blob:none --sparse .../juliet-test-suite-c vendor/juliet
Chay TU REPO ROOT:  .venv/bin/python bench/juliet_extract.py
"""
import os, re, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_items import build   # noqa: E402

JROOT = os.path.join(ROOT, "vendor", "juliet")
DIRS = {"CWE476": "testcases/CWE476_NULL_Pointer_Dereference",
        "CWE416": "testcases/CWE416_Use_After_Free",
        "CWE415": "testcases/CWE415_Double_Free"}

# Stub NO-OP (khong deref) -> use opaque `printLine(data)` khong fire -> self-check loai.
PRELUDE = (
    "#include <wchar.h>\n"
    "typedef struct { int intOne; int intTwo; } twoIntsStruct;\n"
    "static void printLine(const char* v){ (void)v; }\n"
    "static void printWLine(const wchar_t* v){ (void)v; }\n"
    "static void printIntLine(int v){ (void)v; }\n"
    "static void printLongLine(long v){ (void)v; }\n"
    "static void printLongLongLine(int64_t v){ (void)v; }\n"
    "static void printHexCharLine(char v){ (void)v; }\n"
    "static void printWcharLine(wchar_t v){ (void)v; }\n"
)
_SCALAR = re.compile(r"^(unsigned |signed )?(char|short|int|long|long long|wchar_t|int64_t|size_t)$")


def _bad_body(src):
    m = re.search(r"_bad\s*\(\s*\)\s*\{", src)
    if not m:
        return None
    depth = 0
    for j in range(m.end() - 1, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.end():j]
    return None


def _clean(b):
    b = re.sub(r"/\*.*?\*/", " ", b, flags=re.S)
    return re.sub(r"//[^\n]*", " ", b)


def _type(b):
    m = re.search(r"^\s*([A-Za-z_][\w ]*?)\s*\*\s*data\s*;", b, re.M)
    return m.group(1).strip() if m else None


def _sinkkind(s):
    if re.search(r"data\s*->", s):
        return "field"
    if re.search(r"data\s*\[", s):
        return "idx"
    if re.search(r"\*\s*data\b", s):
        return "deref"
    return None


def handler_null(path, cwe):
    """CWE476: sink deref data -> vuln (khong check) / fixed (if data!=NULL). Test truyen NULL."""
    b = _bad_body(open(path, errors="ignore").read())
    if not b:
        return None
    b = _clean(b); typ = _type(b)
    ms = re.search(r"(print\w*Line\s*\([^;]*?\bdata\b[^;]*?\))\s*;", b)
    if not (typ and ms):
        return None
    sink = ms.group(1).strip(); kind = _sinkkind(sink)
    if not kind:
        return None
    tslug = re.sub(r"\W", "_", typ); fn = "nd_%s_%s" % (tslug, kind)
    vuln = "void %s(%s * data){\n    %s;\n}" % (fn, typ, sink)
    fixed = "void %s(%s * data){\n    if (data != NULL) {\n        %s;\n    }\n}" % (fn, typ, sink)
    return {"id": "juliet_476_%s_%s" % (tslug, kind), "cwe": "CWE-476", "family": "null_deref",
            "focal": fn, "signature": "void %s(%s * data)" % (fn, typ), "driver_prelude": PRELUDE,
            "func_vuln": vuln, "func_fixed": fixed,
            "ref_test": "int main(void){ %s * data = NULL; %s(data); return 0; }" % (typ, fn),
            "expect": "fires_on_vuln", "note": "Juliet CWE476: deref NULL (%s)" % kind}


def handler_free(path, cwe):
    """CWE415/416: free(data) roi free-lai (double_free) hoac DEREF (uaf). Test truyen buffer malloc.
    Bo qua use opaque (`printLine(data)` khong deref cu phap) -> khong fire / concept khong bat."""
    b = _bad_body(open(path, errors="ignore").read())
    if not b:
        return None
    b = _clean(b); typ = _type(b)
    if not (typ and _SCALAR.match(typ)):          # chi scalar (struct can stub rieng)
        return None
    mf = re.search(r"free\s*\(\s*data\s*\)\s*;", b)
    if not mf:
        return None
    mu = re.search(r"([^;{}]*?\bdata\b[^;{}]*?)\s*;", b[mf.end():])   # thao tac tren data SAU free
    if not mu:
        return None
    use = mu.group(1).strip()
    if re.match(r"free\s*\(\s*data\s*\)\s*$", use):
        fam, kind, cid = "double_free", "free", "CWE-415"
    elif _sinkkind(use):
        fam, kind, cid = "uaf", _sinkkind(use), "CWE-416"
    else:
        return None                               # use opaque -> bo
    tslug = re.sub(r"\W", "_", typ)
    fn = "%s_%s_%s" % ("df" if fam == "double_free" else "uaf", tslug, kind)
    vuln = "void %s(%s * data){\n    free(data);\n    %s;\n}" % (fn, typ, use)
    fixed = "void %s(%s * data){\n    free(data);\n}" % (fn, typ)
    return {"id": "juliet_%s_%s" % (cid[4:], fn), "cwe": cid, "family": fam, "focal": fn,
            "signature": "void %s(%s * data)" % (fn, typ), "driver_prelude": PRELUDE,
            "func_vuln": vuln, "func_fixed": fixed,
            "ref_test": "int main(void){ %s * data = (%s*)malloc(256); %s(data); return 0; }" % (typ, typ, fn),
            "expect": "fires_on_vuln", "note": "Juliet %s: %s" % (cid, fam)}


HANDLERS = [("CWE476", handler_null), ("CWE416", handler_free), ("CWE415", handler_free)]


def _ensure_source():
    need = [DIRS[c] for c, _ in HANDLERS]
    if all(glob.glob(os.path.join(JROOT, d, "**", "*.c"), recursive=True) for d in need):
        return True
    if not os.path.isdir(os.path.join(JROOT, ".git")):
        print("[!] Thieu vendor/juliet. Chay:\n    git clone --depth 1 --filter=blob:none --sparse "
              "https://github.com/arichardson/juliet-test-suite-c.git vendor/juliet")
        return False
    subprocess.run(["git", "-C", JROOT, "sparse-checkout", "set", "testcasesupport"] + need, check=False)
    return all(glob.glob(os.path.join(JROOT, d, "**", "*.c"), recursive=True) for d in need)


def main():
    if not _ensure_source():
        raise SystemExit("Khong co nguon Juliet.")
    allitems, per = {}, {}
    for cwe, h in HANDLERS:
        files = sorted(glob.glob(os.path.join(JROOT, DIRS[cwe], "**", "*.c"), recursive=True))
        seen = {}
        for f in files:
            it = h(f, cwe)
            if it:
                seen.setdefault(it["id"], it)            # 1 dai dien / (family,type,sink); _01 sort dau
        per[cwe] = "%d file -> %d unique" % (len(files), len(seen))
        for it in seen.values():
            allitems.setdefault(it["id"], it)
    items = sorted(allitems.values(), key=lambda x: x["id"])
    for cwe, _ in HANDLERS:
        print("  %s: %s" % (cwe, per[cwe]))
    print("Tong item unique: %d\n" % len(items))
    build(items, "gold_juliet.jsonl")


if __name__ == "__main__":
    main()
