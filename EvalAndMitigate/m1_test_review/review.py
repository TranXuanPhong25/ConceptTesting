"""Spec-grounded review of generated tests: one reviewer call per test file, KEEP / REWRITE / ABSTAIN per @Test.

The reviewer sees only the test-generation prompt (docstring + signature/context, no focal body) and the test file.
It never sees execution results or the focal method body (both would let it erase effective tests).

usage (in the container): python3 m1_test_review/review.py <src FILE_POST_FIX> <arm FILE_POST_FIX> [id ...]
writes data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_<arm>_with_completion.jsonl,
       m1_test_review/out/<arm>_decisions.jsonl (per test) and m1_test_review/out/<arm>_raw.jsonl (reviewer replies).
"""
import json, os, re, sys

sys.path.insert(0, "/repo"); sys.path.insert(0, "/repo/run")
from data.configuration import JAVA_LANGUAGE
from tree_sitter import Parser

PARSER = Parser(); PARSER.set_language(JAVA_LANGUAGE)
RQ1 = "/repo/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
OUT = "/repo/m1_test_review/out"

PROMPT = """You review JUnit tests that were written from a specification only. You get the specification (the exact prompt the test writer received) and the test file. You do NOT get the implementation; do not guess what it does. Judge each @Test method only against the specification text.

Decide for every @Test method:
- KEEP: every assertion (expected values, expected exceptions, expected null/empty results) follows from a specific sentence of the specification.
- ABSTAIN: an assertion checks behaviour the specification does not state; or an expected value cannot be derived from the specification (a "magic" value that depends on implementation details); or the test mixes specified and unspecified behaviour.
- REWRITE: only if (a) an assertion explicitly contradicts a specification sentence, or (b) the test misuses the API or setup (wrong constructor, wrong argument order, a method not listed in the specification context). Change as little as possible. List every changed expected value in "value_changes" with the specification sentence that states or directly implies the new value. If a rewrite cannot be justified from the specification, ABSTAIN instead.

A value counts as derived from the specification when it follows from a specification sentence together with a well-known standard or definition that sentence names (e.g. Base64, ISO-8601, Java's documented String/Math semantics) or from simple arithmetic on the test's inputs. Reasoning about how the implementation or other classes probably work does not count.

"This test would probably pass" is not a reason to KEEP, and "this test would probably fail" is not a reason to ABSTAIN or REWRITE.

Return only a JSON array, one object per @Test method, in file order:
[{{"test": "<method name>", "decision": "KEEP|REWRITE|ABSTAIN", "reason": "<one sentence>", "spec_quote": "<verbatim specification sentence, or empty>", "value_changes": [{{"old": "...", "new": "...", "spec_quote": "..."}}], "rewritten_method": "<complete Java method with its annotations; REWRITE only, else empty>"}}]

=== SPECIFICATION (test-generation prompt) ===
{spec}
=== END SPECIFICATION ===

=== TEST FILE (@Test methods: {names}) ===
{tests}
=== END TEST FILE ==="""


def test_methods(code: bytes):
    """[(name, start_byte, end_byte)] of methods carrying an @Test annotation."""
    found, stack = [], [PARSER.parse(code).root_node]
    while stack:
        n = stack.pop()
        if n.type == "method_declaration":
            mods = next((c for c in n.children if c.type == "modifiers"), None)
            anns = [a for a in (mods.children if mods else []) if a.type in ("marker_annotation", "annotation")]
            if any(code[a.child_by_field_name("name").start_byte:a.child_by_field_name("name").end_byte] == b"Test" for a in anns):
                name = n.child_by_field_name("name")
                found.append((code[name.start_byte:name.end_byte].decode(), n.start_byte, n.end_byte))
        stack.extend(n.children)
    return sorted(found, key=lambda t: t[1])


def parses_as_method(src: str) -> bool:
    root = PARSER.parse(f"class X {{\n{src}\n}}".encode()).root_node
    return not root.has_error and len(test_methods(f"class X {{\n{src}\n}}".encode())) == 1


def apply(code: str, decisions: dict):
    """Remove ABSTAIN methods, splice REWRITE methods; everything else (imports, helpers, fields) is kept."""
    b = code.encode()
    for name, s, e in reversed(test_methods(b)):
        d = decisions.get(name, {})
        if d.get("final") == "ABSTAIN":
            s = b.rfind(b"\n", 0, s) + 1  # drop the method's leading indentation too
            e = e + 1 if b[e:e + 1] == b"\n" else e
            b = b[:s] + b[e:]
        elif d.get("final") == "REWRITE":
            b = b[:s] + d["rewritten_method"].strip().encode() + b[e:]
    return b.decode()


def parse_reply(text):
    try:
        out = json.loads(text[text.index("["):text.rindex("]") + 1])
        return out if isinstance(out, list) else None
    except (ValueError, json.JSONDecodeError):
        return None


def salvage(text):
    """Decisions from a reply whose JSON is malformed (usually bad quote escaping inside rewritten_method).
    rewritten_method is not recovered, so a salvaged REWRITE becomes ABSTAIN downstream."""
    pat = r'"test":\s*"(\w+)",\s*"decision":\s*"(\w+)",\s*"reason":\s*"((?:[^"\\]|\\.)*)"(?:,\s*"spec_quote":\s*"((?:[^"\\]|\\.)*)")?'
    return [{"test": t, "decision": d, "reason": r, "spec_quote": q, "salvaged": True} for t, d, r, q in re.findall(pat, text or "")]


def main(src, arm, only_ids):
    from gemini_shim import GeminiChat
    client = GeminiChat()
    os.makedirs(OUT, exist_ok=True)
    raw_path = f"{OUT}/{arm}_raw.jsonl"
    cache = {r["key"]: r for r in map(json.loads, open(raw_path))} if os.path.exists(raw_path) else {}
    records = [json.loads(l) for l in open(RQ1.format(src))]
    if only_ids:
        records = [r for r in records if r["id"] in only_ids]
    out_recs, log = [], []
    for r in records:
        blocks = re.findall(r"```java(.*?)```", r["completion"], re.DOTALL)
        if not blocks:  # truncated/degenerate generation: the evaluator skips it anyway, pass through
            out_recs.append(r); print(r["id"], "no java block, passed through"); continue
        code = blocks[0]
        names = [n for n, _, _ in test_methods(code.encode())]
        key = r["id"] + "|" + r["method_signature"]  # ids repeat when a bug has several focal methods
        if key not in cache:
            prompt = PROMPT.format(spec=r["content"], names=", ".join(names), tests=code.strip())
            calls, reply = 0, None
            for _ in range(2):  # one call per file; one retry only if the reply is not a JSON array
                calls += 1
                text = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], temperature=0).choices[0].message.content
                reply = parse_reply(text)
                if reply is not None:
                    break
            cache[key] = {"key": key, "calls": calls, "reply": reply, "text": text}
            with open(raw_path, "a") as f:
                f.write(json.dumps(cache[key]) + "\n")
        reply = cache[key]["reply"] or salvage(cache[key]["text"])
        by_name = {d.get("test"): d for d in reply if isinstance(d, dict)}
        decisions = {}
        for n in names:
            d = by_name.get(n)
            if d is None:
                d, final, note = {}, "KEEP", "no decision returned -> KEEP"
            else:
                final, note = str(d.get("decision", "KEEP")).upper(), "salvaged from malformed JSON" if d.get("salvaged") else ""
                if final not in ("KEEP", "REWRITE", "ABSTAIN"):
                    final, note = "KEEP", f"unknown decision {final!r} -> KEEP"
                if final == "REWRITE" and not parses_as_method(d.get("rewritten_method") or ""):
                    final, note = "ABSTAIN", (note + "; " if note else "") + "rewrite did not parse as one @Test method -> ABSTAIN"
            decisions[n] = {"final": final, "rewritten_method": d.get("rewritten_method") or ""}
            log.append({"id": r["id"], "method_signature": r["method_signature"], "test": n, "decision": final, "llm_decision": d.get("decision"), "note": note,
                        "reason": d.get("reason", ""), "spec_quote": d.get("spec_quote", ""),
                        "value_changes": (d.get("value_changes") or []) if final == "REWRITE" else []})
        new = dict(r, completion="```java\n" + apply(code, decisions).strip("\n") + "\n```")
        out_recs.append(new)
        c = [decisions[n]["final"] for n in names]
        print(r["id"], len(names), "keep", c.count("KEEP"), "rewrite", c.count("REWRITE"), "abstain", c.count("ABSTAIN"))
    with open(RQ1.format(arm), "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in out_recs)
    with open(f"{OUT}/{arm}_decisions.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in log)
    keys = {r["id"] + "|" + r["method_signature"] for r in records}
    print("reviewer calls:", sum(v["calls"] for k, v in cache.items() if k in keys))


def selftest():
    code = "class T {\n  @Before void s() {}\n  @Test public void a() { x(1); }\n  @Test(expected = E.class) public void b() { x(2); }\n  @Test public void c() { x(3); }\n}"
    new = apply(code, {"a": {"final": "ABSTAIN"}, "b": {"final": "REWRITE", "rewritten_method": "@Test public void b() { x(9); }"}})
    assert [n for n, _, _ in test_methods(new.encode())] == ["b", "c"] and "x(9)" in new and "@Before" in new, new
    assert parses_as_method("@Test public void b() { }") and not parses_as_method("void b() {")
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        sys.exit(selftest())
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
