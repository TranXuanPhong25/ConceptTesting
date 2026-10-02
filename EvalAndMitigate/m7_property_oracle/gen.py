"""m7 property oracle: test generation for the two arms (one LLM call per method and arm, T=0).

prompt = the upstream Advanced-Doc test-generation prompt (`content` of the Advanced Doc rq1 file, unchanged)
       + m6's blind evidence pack (method Javadoc, class Javadoc, same-name methods, caller snippets; m6's caps)
       + relation candidates (relations.py, no LLM)
       + one assertion-form paragraph, the only difference between the arms:
         prop    = relation-only oracles (literal outputs only if quoted from the Javadoc, marked `// from Javadoc`)
         example = concrete expected output per input (control)

usage (container, LLM):  python3 m7_property_oracle/gen.py <prop|example> [idx ...]
  -> m7_property_oracle/out/gen_<arm>.jsonl (cache: idx, calls, temperature, prompt, completion)
  -> data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_m7_<arm>[_smoke]_with_completion.jsonl
     (idx given = smoke file with those records only)
                         python3 m7_property_oracle/gen.py <arm> redo idx ...   (redo cached unparsable records, full file)
       python3 m7_property_oracle/gen.py prompts   -> leak checks and prompt sizes of both arms (host ok, no LLM)
"""
import json, os, re, sys

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run", f"{REPO}/m7_property_oracle", f"{REPO}/m5_blind_concept_spec", f"{REPO}/m6_agent_oracle"]
from spec import body_leaks  # m5's check: 40-char windows of the focal body (after its declaration)
import relations

SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
BASE = f"{REPO}/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_unified_invoked_advanced_docstring_prompt.jsonl"
EVIDENCE = f"{REPO}/m6_agent_oracle/out/evidence.jsonl"
OUT = f"{REPO}/m7_property_oracle/out"
RQ1 = REPO + "/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
ARMS = ("prop", "example")
CTX = 5  # m6's caller window (+-5 lines); the caps themselves were applied when m6 built evidence.jsonl

# v2 (the one allowed revision, after the smoke: v1 prop had unmarked LITERAL oracles in 68% of tests; v1 text in
# out/v1_smoke/gen_v1.py). Both paragraphs got the same additions: "overrides" header, allowed / forbidden forms, coverage
# through inputs, a final self-check.
FORM = {
    "prop": """ASSERTION STYLE (mandatory, it overrides any habit of asserting concrete outputs): write property-based tests. Every assertion must relate two or more values that the test computes, using the relation families above (R1 round trip through an inverse, R2 agreement between overloads or variants, R3 invariants the Javadoc states, R4 predictable change under a transformed input, R5 agreement with a JDK equivalent the Javadoc names). Allowed forms, e.g.: `assertEquals(x, inverse(m(x)))`, `assertEquals(m(a, b), overload(a, b))`, `assertEquals(m(t(x)), t2(m(x)))`, `assertTrue(m(x).length() <= x.length())`. Forbidden: a literal expected output of the method under test m for a specific input, such as `assertEquals("a,b", m(...))`, `assertEquals(3, m(...))`, `assertTrue(m("abc"))`, `assertFalse(m(...))`, `assertNull(m(...))`. The only exception is an input-output pair quoted in the original Javadoc shown in the evidence (not the docstring at the top): put the comment `// from Javadoc` on the line of such an assertion. Test for an exception only where the original Javadoc states it. Reach coverage through many inputs per relation, including edge cases. Before answering, check every assertion against these rules and rewrite any that compares m's result with a literal.""",
    "example": """ASSERTION STYLE (mandatory, it overrides any habit of asserting relations between results): write example-based tests. For each input, work out the concrete expected output of the method under test m from the documentation above (the docstring at the top and the original Javadoc in the evidence) and the relation context, and assert m's result against that literal value. Allowed forms, e.g.: `assertEquals("a,b", m(...))`, `assertEquals(3, m(...))`, `assertTrue(m("abc"))`, `assertFalse(m(...))`, `assertNull(m(...))`, `assertArrayEquals(new int[]{1, 2}, m(...))`. The relation candidates may help you choose inputs and derive the expected values, but each assertion compares m's result for one input with one concrete expected value (a literal, a constant, or an array or collection of literals), not with the result of another call. Test for an exception only where the documentation states it. Reach coverage through many inputs per behaviour, including edge cases. Before answering, check every assertion against these rules and rewrite any that compares m's result with another computed value.""",
}
TAIL = "Keep the output format required above: Markdown with one ```java block containing one public test class (JUnit 4), no explanations."


def load():
    recs = [json.loads(l) for l in open(SRC)]
    evs = {e["idx"]: e for e in map(json.loads, open(EVIDENCE))}
    return recs, evs


def pack(ev):
    """m6's blind pack without the class context that the base prompt already lists (constructors, fields, signatures)."""
    p = ["// Evidence from the library itself (the method's implementation is intentionally not shown).",
         "// Declaration of the method under test:", ev["declaration"], "",
         "// The method's original Javadoc comment (written by the library's developers):", ev["javadoc"] or "(the method has no Javadoc comment)", "",
         f"// The Javadoc comment of the class {ev['class']}:", ev["class_javadoc"] or "(none)", "",
         f"// Other methods named {ev['name']} in the same source file (overloads), with their Javadoc and code:"]
    p += [f"// [{k}] {o['file']}:{o['start']}-{o['end']}\n{o['text']}" for k, o in enumerate(ev["overloads"], 1)] or ["(none)"]
    p += ["", f"// Places in the library's main source code that mention {ev['name']}( (+-{CTX} lines each; the method itself is excluded):"]
    p += [f"// [{k}] {c['file']}:{c['start']}-{c['end']}\n{c['text']}" for k, c in enumerate(ev["callers"], 1)] or ["(none)"]
    return "\n".join(p)


def prompt(base, rec, ev, arm):
    """returns (full prompt, appended part); the appended part must not contain a focal-body window."""
    pk = pack(ev)
    added = f"\n\n```\n{pk}\n\n{relations.block(rec, ev, pk)}\n```\n{FORM[arm]}\n{TAIL}"
    assert not body_leaks(rec, added), (rec["extra:project_name"], body_leaks(rec, added))
    return base["content"] + added, added


def ok(completion):
    """the evaluation extracts ```java blocks and needs a public class; ask again only if that is missing."""
    blocks = re.findall(r"```java(.*?)```", completion or "", re.DOTALL)
    # [\w$]: Gson_14's `$Gson$Types...Test` (the first run used \w+ and re-asked those 2 methods; see RESULTS.md)
    return any("@Test" in b and re.search(r"public\s+class\s+[\w$]+", b) for b in blocks)


def prompts_check():
    recs, evs = load()
    base = [json.loads(l) for l in open(BASE)]
    for arm in ARMS:
        n = [len(prompt(base[i], recs[i], evs[i], arm)[0]) for i in range(len(recs))]
        print(f"{arm}: prompts {len(n)}, chars median {sorted(n)[len(n) // 2]}, max {max(n)}, appended parts with a focal-body window 0 (asserted)")
    print("FORM paragraph chars:", {a: len(t) for a, t in FORM.items()})
    leaks = {base[i]["id"]: len(body_leaks(recs[i], base[i]["content"])) for i in range(len(recs)) if body_leaks(recs[i], base[i]["content"])}
    print("base (upstream Advanced-Doc) prompts with a focal-body window (inherited, also in the baseline):", leaks)


def run(arm, idx, redo=False):
    from gemini_shim import GeminiChat
    from oracle import run_pool  # m6's resumable 4-thread pool
    chat = GeminiChat().chat.completions
    recs, evs = load()
    base = [json.loads(l) for l in open(BASE)]
    assert [b["method_signature"] for b in base] == [r["source:source_method_signature"] for r in recs]
    path = f"{OUT}/gen_{arm}.jsonl"

    def one(i):
        p, _ = prompt(base[i], recs[i], evs[i], arm)
        calls, rejected = 0, []
        for temp in (0, 0.5, 0.5):  # re-ask only an unparsable reply; T=0 would repeat it
            calls += 1
            r = chat.create(messages=[{"role": "user", "content": p}], temperature=temp)
            c = r.choices[0].message.content.strip()
            if ok(c):
                break
            rejected.append({"temperature": temp, "chars": len(c), "head": c[:300], "tail": c[-300:]})
        return {"idx": i, "id": recs[i]["extra:project_name"], "calls": calls, "temperature": temp, "prompt": p,
                "completion": c if ok(c) else None, "rejected": rejected,
                "reasoning_token_count": r.usage.completion_tokens_details.reasoning_tokens}

    os.makedirs(OUT, exist_ok=True)
    todo = idx or list(range(len(recs)))
    if redo:  # re-run only the given cached methods (earlier calls stay counted), then write the full file again
        done = {r["idx"]: r for r in map(json.loads, open(path))}
        for i in idx:
            res = one(i)
            done[i] = {**res, "calls": res["calls"] + done[i]["calls"], "rejected": done[i].get("rejected", []) + res["rejected"]}
            print(i, done[i]["id"], "calls", done[i]["calls"], "parsed", bool(done[i]["completion"]), flush=True)
        with open(path, "w") as f:
            f.writelines(json.dumps(done[k]) + "\n" for k in sorted(done))
        todo = list(range(len(recs)))
    else:
        done = run_pool(path, todo, one, "completion")
    for i in todo:  # a cached record must come from the current prompt (no silent reuse after a prompt change)
        assert done[i]["prompt"] == prompt(base[i], recs[i], evs[i], arm)[0], f"stale cache for {i}; move {path} away"
    fpf = f"m7_{arm}" + ("_smoke" if idx and not redo else "")
    with open(RQ1.format(fpf), "w") as f:
        for i in todo:
            d = done[i]
            f.write(json.dumps({**base[i], "content": d["prompt"], "reasoning_token_count": d["reasoning_token_count"],
                                "completion": d["completion"] or ""}) + "\n")
    print("wrote", RQ1.format(fpf), "records", len(todo), "calls", sum(done[i]["calls"] for i in todo),
          "unparsable", [i for i in todo if not done[i]["completion"]])


if __name__ == "__main__":
    if sys.argv[1] == "prompts":
        prompts_check()
    else:
        assert sys.argv[1] in ARMS
        redo = sys.argv[2:3] == ["redo"]  # gen.py <arm> redo i j ...: re-run those cached methods, rewrite the full file
        run(sys.argv[1], [int(i) for i in sys.argv[2 + redo:]], redo)
