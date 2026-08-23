#!/usr/bin/env python3
"""Concept augmenter + family predictor (bench-local; KHONG sua annotator goc / common.py).

Va 2 diem yeu khi suy family tu 8 concept memory-safety:
  (1) Annotator goc bo sot DEREF DON `*ptr` (chi bat `->`, `[]`) -> Juliet `*data` ra vector RONG.
      -> augment(): danh dau ptr_deref cho `*name` trong ngu canh BIEU THUC `( , = { [` truoc `*`
         (tranh khai bao `TYPE *name` va phep nhan `a*b`).
  (2) family cu: `bound_chk` (tu dieu kien vong lap) VO TINH tat luat oob.
      -> family_of(): co BUFFER THAT (buf_alloc + buf_access) => oob DU co bound_chk.

Trung thuc: `[buf_access + ptr_deref]` KHONG co buf_alloc la NHAP NHANG giua oob_read (index
pointer) va null_deref (deref pointer) — 8 concept khong tach duoc. Giu 'oob' (khop oob_read),
chap nhan null_02/03 mislabel. Day la han che cua BO CONCEPT, khong phai heuristic tune duoc.
"""
import os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline_v3"))
import common  # noqa: E402

N = len(common.PROPS)                       # 8
# index: 0 null_assign 1 null_check 2 ptr_deref 3 buf_alloc 4 buf_access 5 bound_chk 6 free 7 if
_DEREF = re.compile(r"[(,={\[]\s*\*\s*[A-Za-z_]")   # `*name` sau ( , = { [  -> deref (khong phai TYPE* / a*b)


def augment(func, concepts, lc):
    """Them ptr_deref cho deref don `*name`. Tra (concepts, lines_concept) da chuan hoa do dai N."""
    lc = {k: (list(v) + [0] * N)[:N] for k, v in (lc or {}).items()}
    for i, ln in enumerate(func.split("\n")):
        if _DEREF.search(ln):
            lc.setdefault(str(i), [0] * N)[2] = 1
    concepts = [0] * N
    for v in lc.values():
        for j in range(N):
            if v[j]:
                concepts[j] = 1
    return concepts, lc


def family_of(func, lc):
    """Suy ho loi tu lines_concept (khong leak nhan CWE). Thu tu quan trong."""
    lc = lc or {}
    def has(i): return any(len(v) > i and v[i] for v in lc.values())
    free_ln = sorted(int(i) for i, v in lc.items() if len(v) > 6 and v[6])
    if len(free_ln) >= 2:
        return "double_free"
    if free_ln and any(int(i) > free_ln[0] and len(v) > 2 and v[2] for i, v in lc.items()):
        return "uaf"                                    # free roi deref sau do
    if has(3) and has(4):
        return "oob"                                    # buffer THAT bi truy cap (du co bound_chk)
    if has(4) and not has(5):
        return "oob"                                    # index pointer khong bound (nhap nhang, khop oob_read)
    if has(2) and not has(1):
        return "null_deref"                             # deref pointer thuan (gom `*data` da augment)
    return None
