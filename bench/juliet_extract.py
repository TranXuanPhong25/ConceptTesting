#!/usr/bin/env python3
"""Trich Juliet Test Suite -> schema benchmark (parametrized vuln/fixed), qua CUNG pipeline build().

Ho da ho tro (in-scope voi 8 concept memory-safety):
  TEMPORAL (con tro, sink `data`):
    CWE476 NULL Pointer Deref -> null_deref   (`*data`, `data[0]`, `data->f` tren con tro NULL)
    CWE416 Use-After-Free     -> uaf          (free(data) roi DEREF data sau do)
    CWE415 Double-Free        -> double_free  (free(data) HAI lan)
  SPATIAL (chi so `buffer[data]`, kieu CWE839 — bound check THIEU):
    CWE121 Stack Overflow     -> oob_write over  (buffer[data]=... , data>=size)
    CWE122 Heap Overflow      -> oob_write over  (buffer heap, data>=size)
    CWE124 Buffer Underwrite  -> oob_write under (data<0)
    CWE126 Buffer Overread    -> oob_read  over  (doc buffer[data], data>=size)
    CWE127 Buffer Underread   -> oob_read  under (data<0)

Tham-so-hoa: bo 'source flow' cua Juliet (fscanf/rand/socket/fixed...), thay bang THAM SO focal.
  - Con tro: focal(TYPE*) nhan NULL / buffer malloc tu test.
  - Chi so:  focal(int data) — buffer khai bao TRONG focal, `data` la chi so tu test.
Guard vuln = guard cua bad() (THIEU, vd `if(data>=0)`); guard fixed = guard cua goodB2G()
(`if(data>=0 && data<N)`) — tuc DUNG BAN VA CUA NIST, khong tu che.

** Vi sao BO subfamily "hardcode-constant" (memcpy sizeof(struct), strcpy(SRC), loop SRC_STRING)? **
KHONG phai vi "khong co cho input" (bai toan la SINH UNIT TEST — `main(){bad();}` cung la unit test hop le).
Ma vi chung KHONG PHAN BIET duoc concept: trigger nhoi cung -> MOI dieu kien (blind/concept/shuffle) deu
sinh dung 1 driver tam thuong `bad();` -> DISCRIM = 1 cho tat ca -> benchmark do duoc CON SO 0 ve dong gop
cua concept. Ngoai ra ban va cua chung la "sua HANG SO" chu khong phai "them bound check theo input" ->
tham-so-hoa se thanh TU CHE ban va. Nguoc lai, subfamily CWE839 (buffer[data]) co INPUT THAT (chi so) +
ban va input-conditioned cua NIST -> vua faithful vua PHAN BIET duoc concept. Do la ly do chi lay no.

** Vi sao KHONG "chay full 100%% Juliet"? ** ~64k case Juliet la boi so cua {sink x source-flow x data-type x
 flow-variant obfuscation (if(5==5), goto, con tro ham, da-TU...)} tren MOT SO IT flaw goc. Voi bai toan sinh
test, flow-variant CUNG sink la trung-lap ngu nghia (test giong het) -> dedup theo focal la DUNG. Moi
(family x type x sink) chi con ~vai focal unique; "100%%" chi bom n bang ban sao gan-trung, KHONG them do kho.

CWE690 (calloc it khi NULL) -> bo. Flow-variant trung focal -> dedup.

Chuan bi:  git clone --depth 1 --filter=blob:none --sparse .../juliet-test-suite-c vendor/juliet
           git -C vendor/juliet sparse-checkout add testcases/CWE121_... (extractor tu add neu thieu)
Chay TU REPO ROOT:  .venv/bin/python bench/juliet_extract.py
"""
import os, re, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_items import build   # noqa: E402

JROOT = os.path.join(ROOT, "vendor", "juliet")
DIRS = {"CWE476": "testcases/CWE476_NULL_Pointer_Dereference",
        "CWE416": "testcases/CWE416_Use_After_Free",
        "CWE415": "testcases/CWE415_Double_Free",
        "CWE121": "testcases/CWE121_Stack_Based_Buffer_Overflow",
        "CWE122": "testcases/CWE122_Heap_Based_Buffer_Overflow",
        "CWE124": "testcases/CWE124_Buffer_Underwrite",
        "CWE126": "testcases/CWE126_Buffer_Overread",
        "CWE127": "testcases/CWE127_Buffer_Underread"}

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


# ===== SPATIAL: chi so buffer[data] (CWE839) — guard vuln=bad(), guard fixed=goodB2G() =====
# fam, direction(over/under), heap?  -> trigger: over=size, under=-1
IDX_MAP = {"CWE121": ("oob_write", "over", False), "CWE122": ("oob_write", "over", True),
           "CWE124": ("oob_write", "under", False), "CWE126": ("oob_read", "over", False),
           "CWE127": ("oob_read", "under", False)}


def _fn_body(src, pat):
    """Than `{...}` cua ham dau tien khop pat (brace-match)."""
    m = re.search(pat, src)
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


def _if_cond(body, need_and=False):
    """Dieu kien cua `if (...)` dau tien co 'data' (paren-balanced, giu nested `(N)`).
    need_and=True -> chi lay guard DAY DU (co '&&', tuc goodB2G)."""
    for m in re.finditer(r"if\s*\(", body):
        depth = 0; start = m.end() - 1
        for j in range(start, len(body)):
            if body[j] == "(":
                depth += 1
            elif body[j] == ")":
                depth -= 1
                if depth == 0:
                    cond = body[start + 1:j].strip()
                    if "data" in cond and (not need_and or "&&" in cond):
                        return re.sub(r"\s+", " ", cond)
                    break
    return None


def handler_index(path, cwe):
    """CWE839 index sink: buffer[data] duoi guard THIEU (bad) -> vuln; guard DU (goodB2G) -> fixed.
    Tham-so-hoa: source flow (fscanf/rand/...) -> tham so `int data`. Buffer nam TRONG focal."""
    fam, direction, heap = IDX_MAP[cwe]
    src = open(path, errors="ignore").read()
    bad = _fn_body(src, r"_bad\s*\(\s*\)\s*\{")
    if not bad:
        return None
    bad = _clean(bad)
    if "buffer[data]" not in re.sub(r"\s", "", bad):
        return None
    mst = re.search(r"([A-Za-z_][\w ]*?)\s+buffer\s*\[\s*(\d+)\s*\]", bad)          # stack: TYPE buffer[N]
    mhp = re.search(r"([A-Za-z_][\w ]*?)\s*\*\s*buffer\s*=\s*.*?(?:malloc|c?alloca|ALLOCA)\s*\(\s*(\d+)", bad)
    if mst and not heap:
        typ, size = mst.group(1).strip(), mst.group(2)
    elif mhp:
        typ, size = mhp.group(1).strip(), mhp.group(2)
    else:
        return None
    bad_guard = _if_cond(bad)                                                       # guard THIEU cua bad()
    if not bad_guard:
        return None
    write = bool(re.search(r"buffer\s*\[\s*data\s*\]\s*=", bad))
    good = _clean(_fn_body(src, r"goodB2G\s*\(\s*\)\s*\{") or "")                   # guard DU cua goodB2G()
    good_guard = _if_cond(good, need_and=True) or ("data >= 0 && data < (%s)" % size)

    if heap:
        decl = ("%s * buffer = (%s *)malloc((%s) * sizeof(%s));\n    if (buffer == NULL) return;"
                % (typ, typ, size, typ))
    else:
        decl = "%s buffer[%s] = {0};" % (typ, size)
    sink = "buffer[data] = 1;" if write else "volatile %s _sink = buffer[data]; (void)_sink;" % typ
    tmpl = "void %%s(int data){\n    %s\n    if (%%s) {\n        %s\n    }\n}" % (decl, sink)
    tag = ("ow" if write else "or") + "_" + direction + ("_heap" if heap else "")
    fn = "idx_%s_%s" % (cwe[3:], tag)
    trig = size if direction == "over" else "-1"
    return {"id": "juliet_%s_%s" % (cwe[3:], tag), "cwe": "CWE-%s" % cwe[3:], "family": fam,
            "focal": fn, "signature": "void %s(int data)" % fn, "driver_prelude": PRELUDE,
            "func_vuln": tmpl % (fn, bad_guard), "func_fixed": tmpl % (fn, good_guard),
            "ref_test": "int main(void){ %s(%s); return 0; }" % (fn, trig),
            "expect": "fires_on_vuln",
            "note": "Juliet CWE%s idx %s %s: vuln guard `%s`, fix `%s`"
                    % (cwe[3:], "write" if write else "read", direction, bad_guard, good_guard)}


HANDLERS = [("CWE476", handler_null), ("CWE416", handler_free), ("CWE415", handler_free),
            ("CWE121", handler_index), ("CWE122", handler_index), ("CWE124", handler_index),
            ("CWE126", handler_index), ("CWE127", handler_index)]


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
