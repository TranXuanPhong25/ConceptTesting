#!/usr/bin/env python3
"""Few-shot examples cho prompt sinh-input Magma. 2 NGUON (2 ban):
  - authored (tu che): vi du build()->bytes viet tay, generic (day dinh dang OUTPUT + reasoning size/index).
  - juliet: cap vuln/fixed THAT tu Juliet (C, tu-chua) lam vi du day REASONING (guard thieu -> gia tri vi pham).
KHONG leak: vi du tu codebase KHAC (synthetic/generic), khong lien quan bug Magma dang test.
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

# ============ Ban 1: TU CHE — vi du build() (khop dinh dang Magma: Python -> bytes) ============
AUTHORED = """VI DU (cach suy tu concept -> input, va DINH DANG output `build()`):

Vi du A — buffer overflow do TRUONG KICH THUOC khong chan tren:
  Concept: ghi N byte vao buffer 16B; N doc tu header; guard chi kiem N>0 (thieu chan tren).
  Suy luan: de vuot bien, dat truong size LON hon 16.
```python
def build():
    import struct
    body = b"A" * 64
    return struct.pack("<I", len(body)) + body   # size=64 >> 16 -> tran
```

Vi du B — CHI SO mang tu input khong chan tren:
  Concept: doc buffer[idx] (mang 10 phan tu); idx tu input; guard chi kiem idx>=0.
  Suy luan: dat idx VUOT so phan tu.
```python
def build():
    import struct
    return struct.pack("<i", 100000)   # idx qua lon -> doc ngoai bien
```
"""


# Loi suy luan phai KHOP HO — ban cu hardcode 1 cau kieu OOB, dung cho ca vi du null_deref/uaf => day SAI.
_REASON = {
    "oob":         "guard hien co khong chan het mien gia tri cua bien input -> chon gia tri VUOT bien buffer.",
    "oob_write":   "guard hien co khong chan het -> chon chi so/kich thuoc VUOT bien de GHI ngoai buffer.",
    "oob_read":    "guard hien co khong chan het -> chon chi so VUOT bien de DOC ngoai buffer.",
    "null_deref":  "ham deref con tro ma KHONG kiem NULL -> truyen thang NULL vao.",
    "uaf":         "con tro bi free roi van duoc dung lai -> di dung duong dan cham vao no SAU khi free.",
    "double_free": "cung mot con tro bi free HAI lan -> di duong dan lam ca hai lan free deu chay.",
    "int_overflow": "phep tinh kich thuoc bi tran -> chon gia tri lam ket qua wrap ve nho/am.",
    None:          "tim gia tri input lam VI PHAM gia dinh an toan cua doan code nguy hiem.",
}


def _fmt_juliet(it):
    """Vi du phai MIRROR dung format bai that: [block CONCEPT] -> [suy luan] -> [input kich hoat].

    !! SUA 2026-09-13: ban cu CHI dua source + test, KHONG dua block concept => model khong he duoc day
    'doc block concept nhu the nao'. Bai that lai dua dung block do (Buffer/sink/guard/bien) => vi du va
    bai that LECH FORMAT, few-shot mat phan lon tac dung. Gio chay CHINH `concept_static.concept_text()`
    (cung ham dung cho bai that) len vi du Juliet -> day tron chuoi suy luan concept -> input.
    """
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(ROOT, "magma"))
    import concept_static as cs                                   # cung bo trich concept voi bai that
    block = cs.concept_text(it)
    # bo dong ket "=> HAY TU SUY..." cua vi du: o day ta TRA LOI thay vi hoi
    block = "\n".join(l for l in block.split("\n") if not l.startswith("=> HAY TU SUY"))
    return ("--- Vi du (Juliet %s) ---\n%s\nSOURCE:\n```c\n%s\n```\n"
            "SUY LUAN: %s\n"
            "INPUT KICH HOAT: `%s`\n"
            % (it.get("cwe", ""), block, (it["func_vuln"] or "").strip(),
               _REASON.get(it.get("family_pred") or it.get("family"), _REASON[None]),
               it.get("ref_test", "")))


def juliet_examples(k=2, target_family=None):
    """k vi du Juliet. Neu co `target_family` -> KHOP HO (retrieval few-shot): vi du dau tien CUNG HO voi
    bug dang giai, vi du sau khac ho (doi chieu).

    !! SUA 2026-09-13 (user chi ra thieu da dang). Ban cu: chon CO DINH `oob`+`double_free` cho ca 100 bug
    => `null_deref` (31/100 bug Magma — ho lon thu 2) KHONG co vi du nao, `uaf` cung khong.
    Kho Juliet co du: oob 7, double_free 5, null_deref 4, uaf 3.
    HAN CHE CON LAI (khong sua duoc bang Juliet): vi du dai 3-7 dong (median 4) trong khi ham Magma
    median 55 / max 782 dong -> lech quy mo ~14x. Vi du day duoc LOI SUY LUAN, khong day duoc do phuc tap that.
    """
    p = os.path.join(ROOT, "bench", "items", "gold_juliet.jsonl")
    if not os.path.exists(p):
        return ""
    items = [it for it in (json.loads(l) for l in open(p) if l.strip())
             if it.get("func_vuln") and it.get("ref_test")]
    fam = lambda it: it.get("family_pred") or it.get("family")
    pick, seen = [], set()
    if target_family:                                   # uu tien vi du CUNG HO voi bug muc tieu
        for it in items:
            if fam(it) == target_family:
                pick.append(it); seen.add(fam(it)); break
    for it in items:                                    # bu them cac ho KHAC (doi chieu)
        if len(pick) >= k:
            break
        if fam(it) not in seen:
            seen.add(fam(it)); pick.append(it)
    if not pick:
        return ""
    return ("VI DU (cap vuln/fixed THAT — hoc cach: guard thieu gi -> gia tri nao vi pham):\n\n"
            + "\n".join(_fmt_juliet(it) for it in pick)
            + "\n(Voi thu vien duoi day, ap dung cung loi suy luan roi xuat `build()`->bytes.)\n")
