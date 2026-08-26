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


# ===== Huong 2: extract_facts — dac ta tan cong muc BIEN (giau hon 8 co per-line) =====
def _params(func, fn):
    m = re.search(re.escape(fn) + r"\s*\(([^)]*)\)\s*\{", func)
    if not m:
        return []
    out = []
    for p in m.group(1).split(","):
        p = p.strip()
        if not p or p == "void":
            continue
        w = re.findall(r"[A-Za-z_]\w*", p)
        if w:
            out.append(w[-1])                           # token cuoi = ten bien
    return out


def extract_facts(item):
    """Tra ve DAC TA TAN CONG (text): buffer+size, bien nguy hiem tu tham so, guard, rang buoc kich hoat.
    Dung family_pred (khong leak) + parse nhe tren func_vuln. Best-effort; ho tro tot cho memory-safety."""
    func = item["func_vuln"]; fam = item.get("family_pred")
    concepts = item.get("concepts") or [0] * N
    fn = common.focal(func) or item.get("focal") or "focal"
    params = _params(func, fn)
    pset = set(params)

    _TY = r"(?:unsigned |signed )?(?:char|short|int|long|float|double|wchar_t|u?int\d+_t|size_t)"
    bufs = {m.group(1): m.group(2)                      # KHAI BAO mang stack: TYPE name[SIZE]
            for m in re.finditer(_TY + r"\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", func)}
    heap = {m.group(1): m.group(2).strip()[:36]         # name = malloc/calloc/alloca(EXPR);
            for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*(?:\([^)]*\)\s*)?(?:malloc|calloc|alloca)\s*\((.+?)\)\s*;", func)}

    def _danger_param():                                # THAM SO dieu khien size/index/bound
        for p in params:                                # pass 1: do dai mem*/strn* hoac chi so truc tiep buf[p]
            if re.search(r"(?:mem(?:cpy|move)|strn(?:cpy|cat))\s*\([^;]*,\s*%s\s*\)" % re.escape(p), func) \
               or re.search(r"\[\s*%s\b" % re.escape(p), func):
                return p
        for p in params:                                # pass 2: bien lam loop bound i<p / index>=p
            if re.search(r"[<>]=?\s*%s\b" % re.escape(p), func):
                return p
        return None

    danger, con = None, None
    if fam in ("oob", "oob_write", "oob_read"):
        bname = next(iter(bufs), None); bsz = bufs.get(bname) if bname else None
        hn = next(iter(heap), None); hsz = heap.get(hn) if hn else None
        mstr = re.search(r"\bstrn?(?:cpy|cat)\s*\(\s*([A-Za-z_]\w*)\s*,\s*([^;)]+)\)", func)
        if mstr:                                        # strcpy(dst,src): tran neu strlen(src) >= size(dst)
            src = mstr.group(2).strip(); tgt = bname or hn or "buffer"; tsz = bsz or hsz or "?"
            danger = "do dai chuoi %s" % src
            con = "truyen `%s` DAI hon %s de strcpy tran buffer `%s`" % (src, tsz, tgt)
        else:
            danger = _danger_param()                    # uu tien THAM SO
            if not danger:                              # roi moi den chi so buf[idx] khong-literal
                for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\[\s*([^\]]+?)\s*\]", func):
                    cand = m.group(2).strip()
                    if (m.group(1) in bufs or m.group(1) in heap) and not cand.isdigit():
                        danger = cand; break
            if bname and bsz and danger:
                con = "truyen `%s` > %s (chi so >= %s) de vuot buffer `%s`[%s]" % (danger, bsz, bsz, bname, bsz)
            elif hn and danger:
                con = "truyen `%s` vuot kich thuoc cap phat `%s = %s`" % (danger, hn, hsz)
            elif not bufs and not heap:                 # khong co buffer -> co the deref con tro tho
                con = "khong ro buffer; thu truyen NULL hoac chi so am/rat lon (co the deref con tro tho)"
            else:
                con = "truyen kich thuoc/chi so (tu tham so) VUOT kich thuoc buffer"
    elif fam == "null_deref":
        dp = next((p for p in params if re.search(r"\*\s*%s\b|%s\s*(?:->|\[)" % (re.escape(p), re.escape(p)), func)), None)
        dp = dp or (params[0] if params else "con_tro")
        danger, con = dp, "truyen `%s` = NULL (ham deref khong kiem tra NULL)" % dp
    elif fam == "uaf":
        con = "truyen buffer da malloc; ham free roi DEREF lai -> goi de kich hoat use-after-free"
    elif fam == "double_free":
        con = "truyen buffer da malloc; ham free HAI lan -> double-free"
    else:
        con = "thu input bien (NULL/0/rat lon) de lo dieu kien loi"

    guard = ("CO bound_check (co the CHUA DU)" if concepts[5] else "KHONG thay bound_check") \
        if fam in ("oob", "oob_write", "oob_read") else \
        (("CO null_check" if concepts[1] else "KHONG thay null_check") if fam == "null_deref" else "-")

    out = ["Ham muc tieu: %s(%s)" % (fn, ", ".join(params) or "void")]
    if bufs:
        out.append("Buffer stack: " + ", ".join("`%s`[%s]" % (k, v) for k, v in bufs.items()))
    if heap:
        out.append("Buffer heap: " + ", ".join("`%s` = %s" % (k, v) for k, v in heap.items()))
    if danger:
        out.append("Bien nguy hiem (test DIEU KHIEN duoc): %s" % danger)
    out.append("Guard: %s" % guard)
    out.append("=> RANG BUOC KICH HOAT: %s" % con)
    return "\n".join("  - " + x for x in out)
