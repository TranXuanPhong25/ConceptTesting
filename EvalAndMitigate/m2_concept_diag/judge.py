"""LLM judge: does the generated docstring describe the buggy, the fixed, or neither behaviour for what the fix changes?

Offline analysis only (the patch is shown to the judge; it never enters any test-generation prompt).
Run in the container after labels.py:  bash run/dock.sh -- python3 m2_concept_diag/judge.py
Appends to m2_concept_diag/judge.jsonl (resumable: finished (idx, docset) pairs are skipped).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "run"))
OUT = os.path.join(ROOT, "m2_concept_diag/judge.jsonl")
DOCS = {"basic": "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_docstring.jsonl",
        "advanced": "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"}

PROMPT = """You are auditing a docstring that was written for a Java method from its BUGGY implementation, before the bug was fixed.

Method: {sig}

The fix (lines starting with '-' are the buggy version, '+' the fixed version, other lines are unchanged context):
```
{patch}
```
Tests that fail on the buggy version and pass on the fixed version:
{trigger}

Docstring:
```
{doc}
```

Question: for the behaviour that the fix changes (the inputs/situations where buggy and fixed versions behave differently), what does the docstring describe?
- BUGGY: the docstring states or clearly implies the buggy version's behaviour in that situation.
- FIXED: the docstring states or clearly implies the fixed (correct) behaviour in that situation.
- NEITHER: the docstring is silent or too vague about that situation, so a reader could not tell which behaviour is intended.
Judge only what the docstring says about the changed situation, not whether it is otherwise accurate.
Reply with JSON only: {{"verdict": "BUGGY" | "FIXED" | "NEITHER", "quote": "<exact docstring sentence(s) supporting the verdict, or empty>", "reason": "<one sentence>"}}"""


def trim(hunk, ctx=3):
    keep = {j for i, l in enumerate(hunk) if l[:1] in "+-" for j in range(i - ctx, i + ctx + 1)}
    out, last = [], -2
    for i in sorted(k for k in keep if 0 <= k < len(hunk)):
        if i != last + 1:
            out.append("...")
        out.append(hunk[i]); last = i
    return "\n".join(out)


def patch_text(lab):
    if lab["method_hunk"]:
        return trim(lab["method_hunk"])
    info = json.load(open(os.path.join(ROOT, f"data/d4j2_fix_info/{lab['bug']}/buggy_fix_info.json")))
    inv = [{"+": "-", "-": "+"}.get(l[:1], l[:1]) + l[1:] for fc in info["fixing_changes"] for l in fc["diff"].splitlines()
           if not l.startswith(("diff", "index", "---", "+++", "@@"))]
    return "(this method itself is not changed; the fix changes methods it may rely on)\n" + trim(inv)


def main():
    labels = [json.loads(l) for l in open(os.path.join(ROOT, "m2_concept_diag/labels.jsonl"))]
    done = {(j["idx"], j["docset"]) for j in map(json.loads, open(OUT))} if os.path.exists(OUT) else set()
    from gemini_shim import GeminiChat
    chat = GeminiChat().chat.completions
    for docset, path in DOCS.items():
        docs = [json.loads(l) for l in open(os.path.join(ROOT, path))]
        for lab, rec in zip(labels, docs):
            assert rec["source:source_method_signature"] == lab["sig"]
            if (lab["idx"], docset) in done:
                continue
            info = json.load(open(os.path.join(ROOT, f"data/d4j2_fix_info/{lab['bug']}/buggy_fix_info.json")))
            trig = "\n".join(f"- {t['test_class'].split('.')[-1]}.{t['test_function']}: {t['exception']}: {(t.get('message') or '')[:200]}"
                             for t in info["trigger_tests"])
            prompt = PROMPT.format(sig=lab["sig"], patch=patch_text(lab), trigger=trig, doc=rec["generated_docstring"].strip())
            calls, verdict = 0, None
            for _ in range(2):
                calls += 1
                reply = chat.create(messages=[{"role": "user", "content": prompt}], temperature=0).choices[0].message.content
                m = re.search(r"\{.*\}", reply, re.S)
                try:
                    verdict = json.loads(m.group()) if m else None
                except json.JSONDecodeError:
                    verdict = None
                if verdict and verdict.get("verdict") in ("BUGGY", "FIXED", "NEITHER"):
                    break
            with open(OUT, "a") as f:
                f.write(json.dumps({"idx": lab["idx"], "project": lab["project"], "sig": lab["sig"], "docset": docset,
                                    "verdict": (verdict or {}).get("verdict"), "quote": (verdict or {}).get("quote"),
                                    "reason": (verdict or {}).get("reason"), "calls": calls, "raw": reply}) + "\n")
            print(docset, lab["idx"], lab["project"], (verdict or {}).get("verdict"), flush=True)


if __name__ == "__main__":
    main()
