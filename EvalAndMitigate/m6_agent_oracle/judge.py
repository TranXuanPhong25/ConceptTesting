"""Offline LLM judge (the patch is shown here and nowhere else): does each arm's answer state the buggy or the fixed
behaviour for the question's input?  One call per method; the two arms' answers appear as A/B in a per-method
random order. Prompt style and patch excerpt follow m2_concept_diag/judge.py.

usage (container): THINKING_BUDGET=-1 python3 m6_agent_oracle/judge.py      -> out/judge.jsonl (resumable)
v2 (used): traces both versions per input before the relevance decision, run with dynamic thinking (offline only).
v1 (out/judge_v1.jsonl, thinking off, relevance asked before the traces) over-labelled relevance: in my 20-question
check only 10 of its 20 "relevant" questions were relevant (see RESULTS.md).
"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, f"{ROOT}/run", f"{ROOT}/m6_agent_oracle"]
import oracle as O

OUT = f"{ROOT}/m6_agent_oracle/out/judge.jsonl"
VERDICTS = ("BUGGY", "FIXED", "SAME", "NEITHER")

PROMPT = """You are auditing answers about the intended behaviour of a Java method that has a known bug. The answers were written for unit-test writers, without access to the fix; some may describe the buggy behaviour.

Method: {sig}

Buggy version of the method:
```java
{body}
```

The fix (lines starting with '-' are the buggy version, '+' the fixed version, other lines are unchanged context):
```
{patch}
```
Tests that fail on the buggy version and pass on the fixed version:
{trigger}

Questions, each with two answers (A and B) from different sources:
{qa}

For each question:
1. "buggy_behaviour" and "fixed_behaviour": trace the buggy and the fixed version on exactly that input, using the code above, and state in one short phrase what each does (result, exception or state).
2. "relevant": true only if the two traced behaviours differ observably for that input. Most inputs do not reach the changed code or behave the same in both versions; then relevant is false.
3. A verdict for each answer:
   - if relevant: "BUGGY" if the answer states the buggy version's behaviour, "FIXED" if it states the fixed version's behaviour, "NEITHER" if it is UNDETERMINED, vague, or matches neither version;
   - if not relevant: "SAME" if the answer matches the behaviour both versions share, "NEITHER" if it is UNDETERMINED, vague, or does not match it.
Reply with JSON only: {{"judgements": [{{"id": "Q1", "buggy_behaviour": "...", "fixed_behaviour": "...", "relevant": true, "A": "BUGGY", "B": "FIXED"}}]}}"""


def trim(hunk, ctx=3):  # m2_concept_diag/judge.py
    keep = {j for i, l in enumerate(hunk) if l[:1] in "+-" for j in range(i - ctx, i + ctx + 1)}
    out, last = [], -2
    for i in sorted(k for k in keep if 0 <= k < len(hunk)):
        if i != last + 1:
            out.append("...")
        out.append(hunk[i]); last = i
    return "\n".join(out)


def patch_text(lab):  # m2_concept_diag/judge.py
    if lab["method_hunk"]:
        return trim(lab["method_hunk"])
    info = json.load(open(f"{ROOT}/data/d4j2_fix_info/{lab['bug']}/buggy_fix_info.json"))
    inv = [{"+": "-", "-": "+"}.get(l[:1], l[:1]) + l[1:] for fc in info["fixing_changes"] for l in fc["diff"].splitlines()
           if not l.startswith(("diff", "index", "---", "+++", "@@"))]
    return "(this method itself is not changed; the fix changes methods it may rely on)\n" + trim(inv)


def order(idx):
    """per-method A/B assignment: True = blind is A."""
    return random.Random(idx).random() < 0.5


def main():
    from gemini_shim import GeminiChat
    chat = GeminiChat().chat.completions
    records = O.load_records()
    labels = [json.loads(l) for l in open(f"{ROOT}/m2_concept_diag/labels.jsonl")]
    qs = {r["idx"]: r["questions"] for r in map(json.loads, open(f"{O.OUT}/questions.jsonl"))}
    an = {a: {r["idx"]: r["answers"] for r in map(json.loads, open(f"{O.OUT}/answers_{a}.jsonl"))} for a in O.ARMS}
    prev = {j["idx"]: j for j in map(json.loads, open(OUT))} if os.path.exists(OUT) else {}  # the last record per method wins
    done = {i for i, j in prev.items() if all(x["parsed"] for x in j["judgements"])}  # redo methods with unparsed judgements
    def one(i):
        rec, lab = records[i], labels[i]
        assert rec["source:source_method_signature"] == lab["sig"]
        blind_a = order(i)
        arm = {"A": O.ARMS[0] if blind_a else O.ARMS[1], "B": O.ARMS[1] if blind_a else O.ARMS[0]}
        show = lambda a, q: "UNDETERMINED" if an[a][i][q["id"]]["undetermined"] else O.one_line(an[a][i][q["id"]]["expected"])
        qa = "\n".join(f"{q['id']}. Input: {q['input']}\n    Question: {q['question']}\n    Answer A: {show(arm['A'], q)}\n    Answer B: {show(arm['B'], q)}"
                       for q in qs[i])
        info = json.load(open(f"{ROOT}/data/d4j2_fix_info/{lab['bug']}/buggy_fix_info.json"))
        trig = "\n".join(f"- {t['test_class'].split('.')[-1]}.{t['test_function']}: {t['exception']}: {(t.get('message') or '')[:200]}"
                         for t in info["trigger_tests"])
        prompt = PROMPT.format(sig=lab["sig"], body=rec["source:source_method_code_format"].strip(), patch=patch_text(lab), trigger=trig, qa=qa)
        calls, js = 0, None
        for temp in (0, 0.5):
            calls += 1
            reply = chat.create(messages=[{"role": "user", "content": prompt}], temperature=temp, max_tokens=32000).choices[0].message.content
            m = re.search(r"\{.*\}", reply, re.S)
            try:
                js = {str(j.get("id")): j for j in json.loads(m.group())["judgements"]} if m else None
            except (ValueError, KeyError, TypeError, AttributeError):
                js = None
            if js and all(q["id"] in js for q in qs[i]):
                break
        out = []
        for q in qs[i]:
            j = (js or {}).get(q["id"], {})
            row = {"qid": q["id"], "concept": q["concept"], "relevant": j.get("relevant") is True,
                   "buggy_behaviour": j.get("buggy_behaviour"), "fixed_behaviour": j.get("fixed_behaviour"), "parsed": bool(j)}
            for k in "AB":
                v = str(j.get(k, "")).upper()
                row[arm[k]] = "UNDETERMINED" if an[arm[k]][i][q["id"]]["undetermined"] else (v if v in VERDICTS else None)
            out.append(row)
        return {"idx": i, "id": rec["extra:project_name"], "blind_is_A": blind_a, "calls": calls + prev.get(i, {}).get("calls", 0),
                "judgements": out, "raw": reply}

    with ThreadPoolExecutor(4) as ex, open(OUT, "a") as f:
        futs = {ex.submit(one, i): i for i in range(len(records)) if i not in done}
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as e:  # not persisted; a rerun retries the method
                print(futs[fut], "FAILED", repr(e)[:200], flush=True)
                continue
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["idx"], r["id"], "calls", r["calls"], sum(x["relevant"] for x in r["judgements"]), "relevant of", len(r["judgements"]), flush=True)


if __name__ == "__main__":
    main()
