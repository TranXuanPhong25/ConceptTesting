#!/usr/bin/env python3
"""pipeline_v3 — nguon chan ly DUNG CHUNG cho prompt + cache-key.

`_PROMPT_SRC` duoc exec o day (cho cac script local dung) VA nhung nguyen van vao
notebook Kaggle (build_v3_nb.py) -> teacher (distill) & student (finetune/infer)
thay prompt BYTE-IDENTICAL, khong bao gio lech.

Khong leak: dieu kien concept dung `family_pred` (heuristic tu tuong tac concept),
KHONG dung nhan CWE. `family_gold` chi de do cascade-error, khong vao prompt.
"""
import re

# ---- Nguon prompt dung chung (exec vao module + nhung vao notebook) ----
_PROMPT_SRC = r'''
import re, hashlib

PROPS = ["null_assignment","null_check","ptr_deref","buffer_allocation",
         "buffer_access","bound_check","free","if_statement"]
# index:   0               1           2           3                 4              5            6      7

CWE_FAMILY = {"CWE-787":"oob_write","CWE-125":"oob_read","CWE-119":"oob","CWE-120":"oob_write",
              "CWE-131":"oob","CWE-416":"uaf","CWE-415":"double_free","CWE-476":"null_deref",
              "CWE-190":"int_overflow","CWE-369":"div_zero"}

FAMILY_DESC = {"oob_write":"GHI ngoai bien","oob_read":"DOC ngoai bien",
               "oob":"truy cap ngoai bien buffer","uaf":"dung sau khi free (use-after-free)",
               "double_free":"free hai lan","null_deref":"deref con tro NULL",
               "int_overflow":"tran so nguyen khi tinh kich thuoc","div_zero":"chia cho khong",
               "no_target":"khong phat hien tuong tac concept nguy hiem ro rang"}

RECIPE = {"oob_write":"truyen do dai/chi so LON HON kich thuoc buffer (n > sizeof) de GHI vuot bien.",
          "oob_read":"chi so/do dai vuot vung hop le de DOC vuot bien.",
          "oob":"input vuot kich thuoc buffer.",
          "uaf":"sau khi con tro da free, GOI lai duong dan DUNG con tro do.",
          "double_free":"dan toi free CUNG con tro HAI LAN.",
          "null_deref":"TRUYEN NULL vao tham so con tro roi goi ham.",
          "int_overflow":"gia tri gan INT_MAX/SIZE_MAX gay TRAN.",
          "div_zero":"mau so = 0.",
          "no_target":"thu cac input bien (rong/NULL/0/rat lon) va KY VONG ham chay AN TOAN (khong crash)."}

def focal(func):
    m = re.search(r"([A-Za-z_]\w*)\s*\([^{;]*\)\s*(?:/\*[\s\S]*?\*/\s*)?\{", func)
    return m.group(1) if m else None

def concept_lines(d):
    out = []
    lc = d.get("lines_concept") or {}
    for i, ln in enumerate(d["func"].split("\n")):
        vec = lc.get(str(i)) or [0]*8
        tags = [PROPS[j] for j, v in enumerate(vec) if v]
        if tags:
            out.append("  - dong %2d [%s] -> %s" % (i, ", ".join(tags), ln.strip()))
    return "\n".join(out)

def predict_family(d):
    """Suy ho loi tu TUONG TAC concept trong lines_concept (heuristic, khong leak).
    Tra None neu khong thay tuong tac nguy hiem (thuong la ham an toan)."""
    lc = d.get("lines_concept") or {}
    def has(idx):  return any(len(v) > idx and v[idx] for v in lc.values())
    free_ln = sorted(int(i) for i, v in lc.items() if len(v) > 6 and v[6])
    if len(free_ln) >= 2:
        return "double_free"
    if free_ln:
        first_free = free_ln[0]
        if any(int(i) > first_free and len(v) > 2 and v[2] for i, v in lc.items()):
            return "uaf"                              # free roi deref sau do
    if has(4) and not has(5):
        return "oob"                                 # buffer_access thieu bound_check
    if has(2) and not has(1):
        return "null_deref"                          # ptr_deref thieu null_check
    return None

FEWSHOT = r"""// Vi du 1 (oob_write): ham copy_into(char*dst, const char*src, int n) chep n byte.
int main(void){
    char dst[8];
    // TARGET: oob_write @ L? -> n (16) > sizeof(dst) (8) gay GHI vuot bien
    copy_into(dst, "AAAAAAAAAAAAAAAA", 16);   // ASAN ky vong: stack-buffer-overflow
    return 0;
}
// Vi du 2 (uaf): ham use_node(Node*p) doc p->val sau khi p da free.
int main(void){
    Node *p = make_node();
    free(p);
    // TARGET: uaf @ L? -> dung con tro sau khi free
    use_node(p);                               // ASAN ky vong: heap-use-after-free
    return 0;
}"""

SYS_BLIND_ADV = ("Ban la ky su kiem thu bao mat C/C++. Nhiem vu: sinh MOT unit test TIM loi BO NHO cho ham. "
                 "Test PHAI goi ham goc voi input doc hai va co ORACLE bao loi "
                 "(EXPECT_DEATH/ASSERT_DEATH hoac chu thich ky vong AddressSanitizer). "
                 "Truoc khi viet, SUY LUAN tung buoc trong comment: (1) thao tac bo nho rui ro o dau, "
                 "(2) input nao kich hoat, (3) oracle nao. Chi tra code C.")

SYS_CONCEPT = ("Ban la ky su kiem thu bao mat C/C++. Sinh unit test dua tren PHAN TICH CONCEPT tinh. "
               "Goi ham goc voi input doc hai va co ORACLE bao loi (EXPECT_DEATH/ASSERT_DEATH hoac ky vong "
               "AddressSanitizer). Suy luan tung buoc trong comment truoc khi viet test. Chi tra code C.")

def build_blind_adv(d):
    """Dieu kien blind NANG CAO: few-shot + chain-of-thought, KHONG co concept/CWE."""
    fn = focal(d["func"]) or "ham_can_test"
    user = ("Vi du mau:\n%s\n\n"
            "Ham can kiem thu:\n```c\n%s\n```\n\n"
            "YEU CAU:\n- Suy luan tung buoc (comment) roi viet test.\n"
            "- Test PHAI goi `%s(...)` voi input doc hai.\n"
            "- PHAI co oracle ASAN/EXPECT_DEATH.\n"
            "- Moi test bat dau bang: // TARGET: <loai loi> @ L<dong> -> <ky thuat>"
            % (FEWSHOT, d["func"], fn))
    return [{"role": "system", "content": SYS_BLIND_ADV},
            {"role": "user", "content": user}]

def build_concept(d):
    """Dieu kien concept: dung family_pred (heuristic) + concept lines + recipe + CoT.
    family_pred=None (ham an toan) -> yeu cau test robustness ky vong KHONG crash (doi chung am)."""
    fam = d.get("family_pred")
    fn = focal(d["func"]) or "ham_can_test"
    cl = concept_lines(d)
    if fam:
        user = ("Ham can kiem thu:\n```c\n%s\n```\n\n"
                "PHAN TICH CONCEPT (static, co the nhieu): nghi ngo %s = %s.\n"
                "Cac dong thao tac lien quan:\n%s\n\n"
                "YEU CAU:\n- %s\n- Suy luan tung buoc (comment) roi viet test goi `%s(...)`.\n"
                "- PHAI co oracle ASAN/EXPECT_DEATH.\n"
                "- Moi test bat dau bang: // TARGET: %s @ L<dong> -> <ky thuat>"
                % (d["func"], fam, FAMILY_DESC.get(fam, fam), cl, RECIPE.get(fam, ""), fn, fam))
    else:
        user = ("Ham can kiem thu:\n```c\n%s\n```\n\n"
                "PHAN TICH CONCEPT (static): KHONG thay tuong tac concept nguy hiem ro rang.\n"
                "Cac dong co concept:\n%s\n\n"
                "YEU CAU:\n- %s\n- Suy luan tung buoc (comment) roi viet test goi `%s(...)`.\n"
                "- Moi test bat dau bang: // TARGET: no_target @ L<dong> -> robustness"
                % (d["func"], cl, RECIPE["no_target"], fn))
    return [{"role": "system", "content": SYS_CONCEPT},
            {"role": "user", "content": user}]

def cache_key(model, cond, func):
    return hashlib.sha1((model + "::" + cond + "::" + func).encode()).hexdigest()
'''

exec(_PROMPT_SRC, globals())


def notebook_prompt_src():
    """Tra ve nguyen van _PROMPT_SRC de build_v3_nb.py nhung vao Cell 4 notebook."""
    return _PROMPT_SRC


def norm_cwe(c):
    if isinstance(c, list):
        return [x for x in c if isinstance(x, str) and re.match(r"CWE-\d+$", x)]
    if isinstance(c, str) and re.match(r"CWE-\d+$", c):
        return [c]
    return []


def family_from_cwe(cwes):
    for c in (cwes or []):
        if c in CWE_FAMILY:  # noqa: F821 (dinh nghia trong _PROMPT_SRC)
            return CWE_FAMILY[c]  # noqa: F821
    return None
