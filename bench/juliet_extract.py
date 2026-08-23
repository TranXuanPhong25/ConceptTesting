#!/usr/bin/env python3
"""Trich Juliet Test Suite (CWE476 NULL-deref, Flow Variant 01) -> schema benchmark.

Juliet _bad()/good() KHONG nhan tham so (self-trigger). Ta THAM-SO-HOA sink:
  bad:      TYPE *data; data=NULL; SINK(deref data);
  goodB2G:  ... if (data != NULL) { SINK; }
-> focal(TYPE *data):  vuln = SINK ;  fixed = if(data!=NULL){ SINK }
   test truyen data=NULL -> vuln deref NULL (no) ; fixed check (sach).
Cung schema/pipeline voi seed -> qua build() (self-check + annotate concept).

Chuan bi:  git clone --filter=blob:none --sparse .../juliet-test-suite-c vendor/juliet
           (bench/juliet_extract.py da tu sparse-checkout neu thieu)
Chay TU REPO ROOT:  .venv/bin/python bench/juliet_extract.py
"""
import os, re, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_items import build   # noqa: E402

JROOT = os.path.join(ROOT, "vendor", "juliet")
CWE476 = os.path.join(JROOT, "testcases", "CWE476_NULL_Pointer_Dereference")

# Stub helper Juliet (Apple clang bao LOI voi implicit decl -> phai khai bao) + type ho tro.
PRELUDE = (
    "#include <wchar.h>\n"
    "typedef struct { int intOne; int intTwo; } twoIntsStruct;\n"
    "static void printIntLine(int v){ (void)v; }\n"
    "static void printLongLine(long v){ (void)v; }\n"
    "static void printLongLongLine(int64_t v){ (void)v; }\n"
    "static void printHexCharLine(char v){ (void)v; }\n"
    "static void printWcharLine(wchar_t v){ (void)v; }\n"
    "static void printWLine(const wchar_t* v){ (void)v; }\n"
)


def _bad_body(src):
    """Lay than _bad() (khop ngoac). _01 khong long ngoac -> du dung."""
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


def extract(path):
    src = open(path, errors="ignore").read()
    b = _bad_body(src)
    if not b:
        return None
    mt = re.search(r"^\s*([A-Za-z_][\w ]*?)\s*\*\s*data\s*;", b, re.M)     # TYPE * data;
    ms = re.search(r"(print\w*Line\s*\([^;]*\bdata\b[^;]*\))\s*;", b)      # SINK dung data
    if not (mt and ms):
        return None
    typ, sink = mt.group(1).strip(), ms.group(1).strip()
    if not re.search(r"\*\s*data|data\s*->", sink):     # PHAI la deref data (khong phai &data ...)
        return None
    var = re.search(r"__([A-Za-z0-9_]+)_01\.c$", os.path.basename(path))
    var = var.group(1) if var else "x"
    fn = re.sub(r"\W", "_", "nd_" + var)
    return {"id": "juliet_476_" + var, "cwe": "CWE-476", "family": "null_deref", "focal": fn,
            "signature": "void %s(%s * data)" % (fn, typ),
            "driver_prelude": PRELUDE,
            "func_vuln":  "void %s(%s * data){ %s; }" % (fn, typ, sink),
            "func_fixed": "void %s(%s * data){ if (data != NULL) { %s; } }" % (fn, typ, sink),
            "ref_test":   "int main(void){ %s * data = NULL; %s(data); return 0; }" % (typ, fn),
            "expect": "fires_on_vuln", "note": "Juliet CWE476 Flow-01: deref NULL data"}


def _ensure_source():
    if os.path.isdir(CWE476) and glob.glob(os.path.join(CWE476, "*_01.c")):
        return True
    if not os.path.isdir(os.path.join(JROOT, ".git")):
        print("[!] Thieu vendor/juliet. Chay:\n"
              "    git clone --depth 1 --filter=blob:none --sparse "
              "https://github.com/arichardson/juliet-test-suite-c.git vendor/juliet")
        return False
    subprocess.run(["git", "-C", JROOT, "sparse-checkout", "set", "testcasesupport",
                    "testcases/CWE476_NULL_Pointer_Dereference"], check=False)
    return bool(glob.glob(os.path.join(CWE476, "*_01.c")))


def main():
    if not _ensure_source():
        raise SystemExit("Khong co nguon Juliet CWE476.")
    files = sorted(glob.glob(os.path.join(CWE476, "*_01.c")))
    items, skip = [], []
    for f in files:
        it = extract(f)
        (items.append(it) if it else skip.append(os.path.basename(f)))
    print("CWE476 _01: %d file -> %d item (skip %d: %s)\n"
          % (len(files), len(items), len(skip), ", ".join(skip) or "-"))
    build(items, "gold_juliet.jsonl")


if __name__ == "__main__":
    main()
