#!/usr/bin/env python3
"""Prompt cho benchmark: blind vs concept.

Tai dung NGUON prompt pipeline_v3/common.py (build_blind_adv / build_concept) — byte-identical
voi pipeline that — roi them rang buoc HARNESS: chi GOI focal, dung khai bao co san (prelude),
KHONG dinh nghia lai -> test link duoc voi CA func_vuln lan func_fixed.

Concept dung `family_pred` (heuristic tu concept, khong dung nhan CWE) va concept_lines: khong leak.
Generator CHI thay func_vuln + prelude (khai bao), KHONG BAO GIO thay func_fixed.
"""
import os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pipeline_v3"))
import common                     # noqa: E402
from concepts import extract_facts  # noqa: E402


def _harness_note(item, fn):
    pre = (item.get("driver_prelude") or "").strip()
    blk = ("Khai bao DA CO SAN (struct/typedef/helper — dung tham chieu, KHONG dinh nghia lai):\n"
           "```c\n%s\n```\n" % pre) if pre else ""
    return ("\n\n%sQUAN TRONG (harness — test la CHUONG TRINH C THUAN, bien dich bang "
            "`gcc -fsanitize=address,undefined`, KHONG co gtest/CppUTest):\n"
            "- KHONG dinh nghia lai `%s` hay cac struct/helper tren (se duoc cung cap khi bien dich).\n"
            "- TUYET DOI KHONG dung EXPECT_DEATH/ASSERT_DEATH/TEST()/gtest/CppUTest "
            "(se KHONG bien dich duoc voi gcc thuan).\n"
            "- Chi viet `int main()` GOI `%s(...)` voi input DOC HAI; AddressSanitizer/UBSan TU abort "
            "khi co loi bo nho (KHONG can macro oracle). Chi #include header chuan.\n"
            "- Tra DUY NHAT mot khoi ```c ... ```." % (blk, fn, fn))


def _d(item):
    return {"func": item["func_vuln"],
            "lines_concept": item.get("lines_concept") or {},
            "family_pred": item.get("family_pred")}


def build_bench_blind(item):
    d = _d(item); msgs = common.build_blind_adv(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


def build_bench_concept(item):
    d = _d(item); msgs = common.build_concept(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


def build_bench_concept2(item):
    """Huong 2 — concept GIAU: concept + DAC TA TAN CONG muc bien (buffer/size/bien-nguy-hiem/
    rang buoc kich hoat) tu extract_facts. Van khong leak func_fixed / nhan CWE."""
    d = _d(item); msgs = common.build_concept(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += "\n\nDAC TA TAN CONG (phan tich tinh muc BIEN):\n" + extract_facts(item)
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


# ===== EN (2026-09-16): ban TIENG ANH cua blind/concept — dung khi chay voi Gemini (router/vertex),
# tranh confound ngon ngu da phat hien o Magma (xem magma/prompts.py PROMPT_VERSION="v3-english").
# KHONG dong pipeline_v3/common.py (file do dung chung byte-identical voi notebook Kaggle distill/finetune,
# doi o do ngoai pham vi cua thu nghiem nay) -> viet lai truc tiep tai day, dung LAI du lieu (family_pred,
# lines_concept, focal) qua common.PROPS / common.focal, chi doi PHAN VAN BAN sang tieng Anh.
_SYS_BLIND_EN = ("You are a C/C++ security test engineer. Task: generate ONE unit test that FINDS a "
                 "memory-safety bug in the function. The test MUST call the original function with "
                 "malicious input and have an ORACLE that reports the bug (EXPECT_DEATH/ASSERT_DEATH, "
                 "or a comment expecting AddressSanitizer to fire). Before writing, reason step by step "
                 "in a comment: (1) where is the risky memory operation, (2) what input triggers it, "
                 "(3) what oracle. Return ONLY C code.")

_SYS_CONCEPT_EN = ("You are a C/C++ security test engineer. Generate a unit test based on STATIC CONCEPT "
                    "ANALYSIS. Call the original function with malicious input and have an ORACLE that "
                    "reports the bug (EXPECT_DEATH/ASSERT_DEATH, or a comment expecting AddressSanitizer). "
                    "Reason step by step in a comment before writing the test. Return ONLY C code.")

_FEWSHOT_EN = """// Example 1 (oob_write): function copy_into(char*dst, const char*src, int n) copies n bytes.
int main(void){
    char dst[8];
    // TARGET: oob_write @ L? -> n (16) > sizeof(dst) (8) causes an OUT-OF-BOUNDS WRITE
    copy_into(dst, "AAAAAAAAAAAAAAAA", 16);   // ASan expected: stack-buffer-overflow
    return 0;
}
// Example 2 (uaf): function use_node(Node*p) reads p->val AFTER p has been freed.
int main(void){
    Node *p = make_node();
    free(p);
    // TARGET: uaf @ L? -> pointer used after free
    use_node(p);                               // ASan expected: heap-use-after-free
    return 0;
}"""

_FAMILY_DESC_EN = {"oob_write": "OUT-OF-BOUNDS WRITE", "oob_read": "OUT-OF-BOUNDS READ",
                   "oob": "out-of-bounds buffer access", "uaf": "use-after-free",
                   "double_free": "double free", "null_deref": "NULL pointer dereference",
                   "int_overflow": "integer overflow when computing a size", "div_zero": "division by zero",
                   "no_target": "no clear dangerous concept interaction detected"}

_RECIPE_EN = {"oob_write": "pass a length/index LARGER than the buffer size to WRITE out of bounds.",
              "oob_read": "an index/length beyond the valid range to READ out of bounds.",
              "oob": "input beyond the buffer size.",
              "uaf": "after the pointer is freed, CALL the path that still USES that pointer.",
              "double_free": "lead to freeing the SAME pointer TWICE.",
              "null_deref": "PASS NULL into the pointer parameter then call the function.",
              "int_overflow": "a value near INT_MAX/SIZE_MAX to cause an OVERFLOW.",
              "div_zero": "denominator = 0.",
              "no_target": "try varied inputs (empty/NULL/0/very large) and EXPECT the function to run "
                           "SAFELY (no crash)."}


def _concept_lines_en(d):
    out = []
    lc = d.get("lines_concept") or {}
    for i, ln in enumerate(d["func"].split("\n")):
        vec = lc.get(str(i)) or [0] * 8
        tags = [common.PROPS[j] for j, v in enumerate(vec) if v]
        if tags:
            out.append("  - line %2d [%s] -> %s" % (i, ", ".join(tags), ln.strip()))
    return "\n".join(out)


def _harness_note_en(item, fn):
    pre = (item.get("driver_prelude") or "").strip()
    blk = ("Declarations ALREADY PROVIDED (struct/typedef/helper — reference them, do NOT redefine):\n"
           "```c\n%s\n```\n" % pre) if pre else ""
    return ("\n\n%sIMPORTANT (harness — the test is a PLAIN C program, compiled with "
            "`gcc -fsanitize=address,undefined`, NO gtest/CppUTest):\n"
            "- Do NOT redefine `%s` or the structs/helpers above (they will be provided at compile time).\n"
            "- Do NOT use EXPECT_DEATH/ASSERT_DEATH/TEST()/gtest/CppUTest "
            "(will NOT compile with plain gcc).\n"
            "- Only write `int main()` CALLING `%s(...)` with malicious input; AddressSanitizer/UBSan "
            "auto-aborts on a memory error (no oracle macro needed). Only #include standard headers.\n"
            "- Return ONLY a single ```c ... ``` block." % (blk, fn, fn))


def build_bench_blind_en(item):
    d = _d(item)
    fn = common.focal(d["func"]) or item["focal"]
    user = ("Sample example:\n%s\n\n"
            "Function under test:\n```c\n%s\n```\n\n"
            "REQUIREMENTS:\n- Reason step by step (comment) then write the test.\n"
            "- The test MUST call `%s(...)` with malicious input.\n"
            "- MUST have an ASan/EXPECT_DEATH oracle.\n"
            "- Every test starts with: // TARGET: <bug type> @ L<line> -> <technique>"
            % (_FEWSHOT_EN, d["func"], fn))
    msgs = [{"role": "system", "content": _SYS_BLIND_EN}, {"role": "user", "content": user}]
    msgs[-1]["content"] += _harness_note_en(item, fn)
    return msgs


def build_bench_concept_en(item):
    d = _d(item)
    fam = d.get("family_pred")
    fn = common.focal(d["func"]) or item["focal"]
    cl = _concept_lines_en(d)
    if fam:
        user = ("Function under test:\n```c\n%s\n```\n\n"
                "CONCEPT ANALYSIS (static, may be noisy): suspect %s = %s.\n"
                "Related operation lines:\n%s\n\n"
                "REQUIREMENTS:\n- %s\n- Reason step by step (comment) then write a test calling `%s(...)`.\n"
                "- MUST have an ASan/EXPECT_DEATH oracle.\n"
                "- Every test starts with: // TARGET: %s @ L<line> -> <technique>"
                % (d["func"], fam, _FAMILY_DESC_EN.get(fam, fam), cl, _RECIPE_EN.get(fam, ""), fn, fam))
    else:
        user = ("Function under test:\n```c\n%s\n```\n\n"
                "CONCEPT ANALYSIS (static): no clear dangerous concept interaction found.\n"
                "Concept-tagged lines:\n%s\n\n"
                "REQUIREMENTS:\n- %s\n- Reason step by step (comment) then write a test calling `%s(...)`.\n"
                "- Every test starts with: // TARGET: no_target @ L<line> -> robustness"
                % (d["func"], cl, _RECIPE_EN["no_target"], fn))
    msgs = [{"role": "system", "content": _SYS_CONCEPT_EN}, {"role": "user", "content": user}]
    msgs[-1]["content"] += _harness_note_en(item, fn)
    return msgs


BUILD = {"bench_blind": build_bench_blind, "bench_concept": build_bench_concept,
         "bench_concept2": build_bench_concept2,
         "bench_blind_en": build_bench_blind_en, "bench_concept_en": build_bench_concept_en}


def prompt_key(model, cond, item):
    """Cache key = hash CUA PROMPT that -> doi prompt (vd family_pred thay) TU dong invalidate."""
    m = BUILD[cond](item)
    blob = "::".join([model, cond, item["id"], m[0]["content"], m[1]["content"]])
    return hashlib.sha1(blob.encode()).hexdigest()
