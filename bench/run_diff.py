#!/usr/bin/env python3
"""Harness VI-PHAN: compile + chay test do LLM sinh voi CA func_vuln lan func_fixed.

   test + func_vuln  -> ASAN/UBSan PHAI no  (bat bug = true positive)
   test + func_fixed -> phai SACH           (no o day = bao dong gia = false positive)

Lopic compile/chay + phat hien FIRES mirror pipeline_v3/04_eval_coverage.py
(bo --coverage vi metric vi-phan khong can gcov). Chay 100% local, khong GPU.
"""
import os, re, shutil, tempfile, subprocess

CXX = next((c for c in ("cc", "gcc", "clang") if shutil.which(c)), None)
HEADER = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n"
          "#include <stdint.h>\n#include <limits.h>\n#include <assert.h>\n")


def extract_code(text):
    """Lay khoi ```c ... ``` dau tien; neu khong co code-fence -> ca text."""
    m = re.search(r"```[a-zA-Z0-9+_-]*\s*([\s\S]*?)```", text or "")
    return (m.group(1) if m else (text or "")).strip()


def strip_focal_def(test, focal):
    """Xoa DINH NGHIA `focal(...){...}` neu model tu viet (brace-match) -> tranh trung
    dinh nghia khi link voi impl cua ta. Loi goi `focal(...)` (theo sau ';') duoc GIU."""
    pat = re.compile(r"\b" + re.escape(focal) + r"\s*\([^;{}]*\)\s*\{")
    while True:
        m = pat.search(test)
        if not m:
            return test
        depth = 0; end = None
        for j in range(m.end() - 1, len(test)):
            if test[j] == "{":
                depth += 1
            elif test[j] == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1; break
        if end is None:
            return test
        s = test.rfind("\n", 0, m.start()) + 1      # lui ve dau dong khai bao
        test = test[:s] + test[end:]


def compile_run(src, timeout=20):
    """Compile (ASAN+UBSan) + chay. Tra {compiles, fires}."""
    if not CXX or len(src) < 20 or "main" not in src:
        return {"compiles": 0, "fires": 0}
    d = tempfile.mkdtemp(); cf = os.path.join(d, "t.c"); binf = os.path.join(d, "t.bin")
    open(cf, "w").write(src)
    try:
        r = subprocess.run([CXX, "-fsanitize=address,undefined", "-g", "-O0", "-w", cf, "-o", binf],
                           capture_output=True, timeout=timeout)
    except Exception:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0}
    if r.returncode != 0:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0}
    fires = 0
    try:
        run = subprocess.run([binf], capture_output=True, timeout=timeout,
                             env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0", "UBSAN_OPTIONS": "halt_on_error=1"})
        err = (run.stderr or b"").decode(errors="ignore")
        # CHI dem marker cua CHINH sanitizer -> tranh false-fire khi test tu abort()/in "ERROR:"
        # (nhieu test viet oracle: neu KHONG crash thi abort -> tren ban fixed se abort -> KHONG duoc coi la no).
        fires = 1 if ("AddressSanitizer" in err or "runtime error:" in err
                      or "UndefinedBehaviorSanitizer" in err) else 0
    except subprocess.TimeoutExpired:
        pass
    shutil.rmtree(d, ignore_errors=True)
    return {"compiles": 1, "fires": fires}


def assemble(item, impl_field, raw_test):
    """1 chuong trinh C: HEADER + prelude + (func_vuln|func_fixed) + test-da-lam-sach."""
    test = strip_focal_def(extract_code(raw_test), item["focal"])
    if "int main" not in test:
        test = "int main(void){\n" + test + "\nreturn 0;\n}"
    return (HEADER + (item.get("driver_prelude") or "") + "\n"
            + item[impl_field] + "\n\n" + test)


def run_diff(raw_test, item):
    """Chay test voi CA 2 impl. Tra compiles/fires cho tung ban."""
    v = compile_run(assemble(item, "func_vuln", raw_test))
    f = compile_run(assemble(item, "func_fixed", raw_test))
    return {"compiles_vuln": v["compiles"], "fires_vuln": v["fires"],
            "compiles_fixed": f["compiles"], "fires_fixed": f["fires"]}
