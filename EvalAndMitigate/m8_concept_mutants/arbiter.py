"""m8 Phase 1, steps 4-5: distinguishing items -> blind A/B arbiter (one LLM call per method and arm) -> JUnit tests.

items  (host)    per method and arm: (probe case, original output, mutant output) where a selected mutant differs from the
                 original on a deterministic case (two original runs agree; timeouts dropped), deduplicated; at most
                 MAX_ITEMS per method (round robin over cases, most frequent difference first). A/B order per item from a
                 seeded RNG. The arbiter is never told which side is the current code.
ask    (LLM)     spec = Advanced docstring + m6 blind pack (no focal body), items as "A gives P, B gives Q"; answers
                 A / B / UNDETERMINED with evidence (no evidence counts as UNDETERMINED).
tests  (sandbox) one JUnit test per decided item from a deterministic template (the probe case inlined as an anonymous
                 Callable, Java 7 compatible; assertEquals on the harness's repr, or the exception class); compiled against the buggy classes, non-compiling methods dropped.
completions (host) -> data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_m8_<arm>[_smoke]_with_completion.jsonl

usage:
  python3 m8_concept_mutants/arbiter.py items
  bash run/dock.sh -- python3 m8_concept_mutants/arbiter.py ask <concept|generic> [idx ...]
  bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/arbiter.py tests <arm> [idx ...]
  python3 m8_concept_mutants/arbiter.py completions <arm> [idx ...]      (idx given: a _smoke file with those records)
"""
import json, os, random, re, sys
from collections import Counter, defaultdict

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run", f"{REPO}/m6_agent_oracle", f"{REPO}/m8_concept_mutants"]
D = f"{REPO}/m8_concept_mutants"
OUT = os.environ.get("M8_OUT") or f"{D}/out"  # dock8.sh: /m8out (top-level mount)
ARMS = ("concept", "generic")
MAX_ITEMS = 10
BASE_RQ1 = f"{REPO}/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_unified_invoked_advanced_docstring_prompt.jsonl"
RQ1 = REPO + "/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"


def jl(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


# ---------------------------------------------------------------- items
def items():
    chk = json.load(open(f"{OUT}/probe_check.json"))
    sel = json.load(open(f"{OUT}/selection.json"))
    out = {}
    for r in jl(f"{OUT}/probe_runs.jsonl"):
        i = r["idx"]
        cases = {str(c[0]): (c[1], c[2], c[3] if len(c) > 3 else "") for c in chk[str(i)]["cases"]}
        det = [k for k, v in r["orig"].items() if v == r["orig2"].get(k) and v not in ("timeout", "DUP") and k in cases]
        out[str(i)] = {}
        for arm in ARMS:
            diff = defaultdict(list)
            for mid in sel[str(i)][arm]:
                mo = r["mutants"][mid]
                for k in det:
                    v = mo.get(k)
                    if v is not None and v not in ("timeout", "DUP") and v != r["orig"][k]:
                        diff[(k, v)].append(mid)
            by_case = defaultdict(list)
            for (k, v), mids in sorted(diff.items(), key=lambda x: (-len(x[1]), int(x[0][0]), x[0][1])):
                by_case[k].append((v, mids))
            order, ks = [], sorted(by_case, key=lambda k: (-len(by_case[k][0][1]), int(k)))
            while any(by_case[k] for k in ks) and len(order) < MAX_ITEMS:
                for k in ks:
                    if by_case[k] and len(order) < MAX_ITEMS:
                        order.append((k, *by_case[k].pop(0)))
            its = []
            for j, (k, v, mids) in enumerate(order, 1):
                a_is_orig = random.Random(f"m8-{i}-{arm}-{k}-{v}").random() < 0.5
                its.append({"item": j, "k": k, "label": cases[k][0], "code": cases[k][1], "prelude": cases[k][2], "orig": r["orig"][k], "mut": v, "mutants": mids,
                            "a_is_orig": a_is_orig, "A": r["orig"][k] if a_is_orig else v, "B": v if a_is_orig else r["orig"][k]})
            out[str(i)][arm] = {"n_diff": len(diff), "n_cases_diff": len({k for k, _ in diff}), "items": its}
    json.dump(out, open(f"{OUT}/items.json", "w"), indent=1)
    for arm in ARMS:
        n = [len(v[arm]["items"]) for v in out.values()]
        print(f"{arm}: methods {len(n)}, with ≥1 item {sum(x > 0 for x in n)}, items {sum(n)}, distinct differences "
              f"{sum(v[arm]['n_diff'] for v in out.values())}")


# ---------------------------------------------------------------- ask (LLM)
ARBITER_PROMPT = """You are checking which of two behaviours of a Java method is the intended one. The method's implementation is not shown; decide only from its documentation and the evidence from the library below.

// Documentation of the method under test:
{docstring}

{pack}
Two implementations, A and B, of this method were run on the same probe inputs. On each item below they behave differently. Results are written as `returns <value>` (strings in double quotes with Java escapes, characters in single quotes, numbers as Type:value, arrays as Type[...], collections and maps with their class name, other objects as Type:toString()) or `throws <exception class>: <message>`.

{items}

For each item, decide which result a correct implementation of the documented method must produce: "A" or "B". Answer "UNDETERMINED" when the documentation and the evidence do not settle it (for example both results are consistent with them, or neither is); do not guess. Support each decision with at least one verbatim quote from the material above, or name the documented Java or library convention you rely on.
Output a single JSON object inside one ```json block:
{{"items": [{{"id": 1, "reasoning": "<one or two sentences>", "choice": "A | B | UNDETERMINED", "evidence": [{{"source": "docstring | javadoc | caller | overload | class_context | naming | standard", "quote": "<verbatim quote>"}}]}}]}}
"""


def item_text(it):
    code = "\n".join("      " + l for l in ((it.get("prelude") or "") + "\n" + it["code"]).strip().splitlines())
    return f"Item {it['item']}. Probe input ({it['label']}):\n{code}\n  Implementation A: {it['A']}\n  Implementation B: {it['B']}"


def arbiter_prompt(O, rec, adv, ev, its):
    return ARBITER_PROMPT.format(docstring=adv["generated_docstring"].strip(), pack=O.render_pack(rec, ev, False),
                                 items="\n\n".join(item_text(it) for it in its))


def parse_choices(reply, its):
    from oracle import last_json
    obj = last_json(reply)
    ans = obj.get("items") if obj else None
    if not isinstance(ans, list):
        return None
    by = {str(a.get("id", "")).strip(): a for a in ans if isinstance(a, dict)}
    out = {}
    for it in its:
        a = by.get(str(it["item"]), {})
        ch = str(a.get("choice", "")).strip().upper()
        ev = [e for e in a.get("evidence") or [] if isinstance(e, dict) and str(e.get("quote", "")).strip()]
        ch = ch if ch in ("A", "B") and ev else "UNDETERMINED"
        out[str(it["item"])] = {"choice": ch, "raw_choice": a.get("choice"), "evidence": ev, "reasoning": a.get("reasoning", "")}
    return out


def ask(arm, idx):
    import probe as PR
    O, recs, adv, evs = PR.load()
    its = json.load(open(f"{OUT}/items.json"))
    path = f"{OUT}/arbiter_{arm}.jsonl"
    done = {r["idx"]: r for r in jl(path)}
    chat = PR.Chat()
    for i in idx or sorted(int(k) for k in its):
        it = its[str(i)][arm]["items"]
        if i in done and done[i]["answers"] is not None:  # cached: must come from the current prompt (no silent reuse)
            assert done[i]["prompt"] == (arbiter_prompt(O, recs[i], adv[i], evs[i], it) if it else None), f"stale cache for {i}"
            continue
        if not it:
            done[i] = {"idx": i, "id": recs[i]["extra:project_name"], "calls": 0, "answers": {}, "prompt": None}
        else:
            p = arbiter_prompt(O, recs[i], adv[i], evs[i], it)
            # the guard covers everything but the observed outputs: an output can repeat a string literal of the method
            # (an exception message), which is behaviour any caller sees, not code; those prompts are listed in analyze.py
            outs = sorted({x for t in it for x in (t["A"], t["B"])}, key=len, reverse=True)
            stripped = p
            for x in outs:
                stripped = stripped.replace(x, "")
            assert not PR.appended_leaks(O, recs[i], adv[i], stripped), f"focal body in arbiter prompt {i}"
            calls, parsed = 0, None
            for temp in (0, 0.5, 0.5):  # re-ask only an unparsable reply
                calls += 1
                reply = chat(p, f"arbiter_{arm}", i, temperature=temp)
                parsed = parse_choices(reply, it)
                if parsed is not None:
                    break
            done[i] = {"idx": i, "id": recs[i]["extra:project_name"], "calls": calls, "prompt": p, "reply": reply, "answers": parsed}
        with open(path, "w") as f:
            f.writelines(json.dumps(done[k]) + "\n" for k in sorted(done))
        a = done[i]["answers"] or {}
        print(i, recs[i]["extra:project_name"], arm, "items", len(it), "calls", done[i]["calls"], dict(Counter(x["choice"] for x in a.values())),
              f"spent {PR.spent():.3f} USD", flush=True)


# ---------------------------------------------------------------- tests (sandbox) and completions (host)
def jstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def call_expr(it):
    """the probe case as a Java 7 expression (Codec compiles its tests with -source 1.7: no lambdas): an anonymous
    Callable whose call() holds the case's prelude and body, so the focal call stays inside the test method (the
    pipeline keeps only @Test methods that invoke the focal method) and no outer local is captured."""
    lam = it["code"]
    body = lam[lam.index("->") + 2:].strip()
    inner = body[1:-1].strip() if body.startswith("{") and body.endswith("}") else f"return {body};"
    lines = [l.strip() for l in (it.get("prelude") or "").splitlines() + inner.splitlines() if l.strip()]
    return ("new java.util.concurrent.Callable<Object>() {\n            public Object call() throws Exception {\n"
            + "".join(f"                {l}\n" for l in lines) + "            }\n        }.call()")


def test_method(arm, it, chosen, other):
    head = f"    @Test\n    public void m8{arm.capitalize()}Item{it['item']}() throws Exception {{\n" \
           f"        // input: {it['label'].replace(chr(10), ' ')}\n"
    if chosen.startswith("returns "):
        body = f"        Object m8r = {call_expr(it)};\n        assertEquals({jstr(chosen[len('returns '):])}, m8repr(m8r));\n"
    else:
        cls = chosen[len("throws "):].split(":")[0].strip()
        same = other.startswith("throws ") and other[len("throws "):].split(":")[0].strip() == cls
        body = (f"        Throwable t = null;\n        try {{\n        {call_expr(it)};\n        }} catch (Throwable e) {{\n            t = e;\n        }}\n"
                f"        assertNotNull({jstr('expected ' + cls)}, t);\n        assertEquals({jstr(cls)}, t.getClass().getName());\n"
                + (f"        assertEquals({jstr(chosen)}, m8outcome(t));\n" if same else ""))
    return head + body + "    }\n"


def decided(arm):
    its = json.load(open(f"{OUT}/items.json"))
    ans = {r["idx"]: r["answers"] or {} for r in jl(f"{OUT}/arbiter_{arm}.jsonl")}
    out = {}
    for i, a in ans.items():
        out[i] = []
        for it in its[str(i)][arm]["items"]:
            ch = a.get(str(it["item"]), {}).get("choice", "UNDETERMINED")
            if ch in ("A", "B"):
                chosen, other = (it["A"], it["B"]) if ch == "A" else (it["B"], it["A"])
                out[i].append((it, chosen, other))
    return out


def test_class(rec, arm, imports, methods):
    import probe as PR
    pkg = rec["source:source_method_signature"].split("#")[0]
    name = f"{rec['source:source_method_signature'].split('#')[1].replace('$', '')}M8{arm.capitalize()}Test"
    imp = "\n".join(dict.fromkeys(["import org.junit.Test;", "import static org.junit.Assert.*;"] + imports))
    return pkg, name, f"{imp}\n\npublic class {name} {{\n\n" + "\n".join(methods) + PR.REPR + "}\n"


def tests(arm, idx):
    import phase0 as P, probe as PR
    recs = [json.loads(l) for l in open(PR.SRC)]
    env = P.load_env()
    chk = json.load(open(PR.CHECK))
    gen_ = {r["idx"]: r for r in jl(PR.GEN)}
    res = {}
    for i, dec in sorted(decided(arm).items()):
        if idx and i not in idx:
            continue
        rec = recs[i]
        b = env["bugs"][rec["extra:project_name"].replace("_buggy", "")]
        imports = PR.parse_code(gen_[i]["attempts"][chk[str(i)]["attempt"]]["code"])[0]
        methods = {it["item"]: test_method(arm, it, ch, ot) for it, ch, ot in dec}
        # the pipeline compiles tests with the project's build: Codec uses source/target 1.7, the others 11
        builds = [f for f in (f"{b['root_buggy']}/build.xml", f"{b['root_buggy']}/maven-build.xml", f"{b['root_buggy']}/gson/maven-build.xml") if os.path.exists(f)]
        level = ["-source", "7", "-target", "7"] if any(re.search(r'source="1\.7"', open(f).read()) for f in builds) else []
        expect = {it["item"]: ch == it["orig"] for it, ch, ot in dec}  # passes on the current (buggy) code?
        dropped, ran = [], {}
        for _ in range(6):  # drop test methods the compiler rejects (javac reports a bounded number of errors per round)
            if not methods:
                break
            pkg, name, code = test_class(rec, arm, imports, list(methods.values()))
            d = f"{P.SCR}/tests/{arm}/{i}"
            P.shutil.rmtree(d, ignore_errors=True); os.makedirs(f"{d}/cls")
            src = f"package {pkg};\n\n{code}"
            open(f"{d}/{name}.java", "w").write(src)
            r = P.sh(["javac", "-nowarn", "-proc:none", "-encoding", "UTF-8", *level, "-d", f"{d}/cls", "-cp",
                      ":".join([f"{P.SCR}/orig/{i}/cls"] + b["cp_buggy"] + [P.JUNIT]), f"{d}/{name}.java"], timeout=180)
            if r.returncode == 0:
                break
            lines = src.splitlines()
            bad = set()
            for m in re.finditer(rf"{re.escape(name)}\.java:(\d+): error", r.stderr):
                ln = int(m.group(1)) - 1
                for j in range(ln, -1, -1):
                    mm = re.search(r"public void m8\w+?Item(\d+)\(", lines[j])
                    if mm:
                        bad.add(int(mm.group(1))); break
            if not bad:
                dropped += list(methods); methods = {}; break
            dropped += sorted(bad)
            methods = {k: v for k, v in methods.items() if k not in bad}
        bad_sc = []
        if methods:  # self-check on the buggy code: a test asserting the original's output must pass, the mutant's must fail
            tl = [f"{pkg}.{name}::m8{arm.capitalize()}Item{k}" for k in methods]
            out = P.run_tests(tl, [f"{d}/cls", f"{P.SCR}/orig/{i}/cls", P.RUNNER] + b["cp_buggy"], b["root_buggy"])
            ran = {k: out[f"{pkg}.{name}::m8{arm.capitalize()}Item{k}"][0] for k in methods}
            # a mismatch means the test does not reproduce its probe record (time- or state-dependent case): drop it
            bad_sc = [k for k in methods if (ran[k] == "PASS") != expect[k]]
        sc = {k: [ran[k], expect[k]] for k in methods}
        methods = {k: v for k, v in methods.items() if k not in bad_sc}
        res[str(i)] = {"code": test_class(rec, arm, imports, list(methods.values()))[2] if methods else "", "kept": sorted(methods),
                       "dropped_compile": dropped, "dropped_self_check": bad_sc, "self_check": sc}
        print(i, rec["extra:project_name"], arm, "decided", len(dec), "tests", len(methods), "dropped", dropped, "self-check mismatches (dropped)", bad_sc, flush=True)
    path = f"{OUT}/tests_{arm}.json"
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(res)
    json.dump(old, open(path, "w"), indent=1)


def completions(arm, idx):
    base = [json.loads(l) for l in open(BASE_RQ1)]
    t = json.load(open(f"{OUT}/tests_{arm}.json"))
    sel = idx or range(len(base))
    fpf = f"m8_{arm}" + ("_smoke" if idx else "")
    with open(RQ1.format(fpf), "w") as f:
        for i in sel:
            code = t.get(str(i), {}).get("code", "")
            f.write(json.dumps({**base[i], "content": "m8: deterministic tests from blind A/B arbiter decisions (no test-generation prompt)",
                                "reasoning_token_count": 0, "completion": f"```java\n{code}```\n" if code else ""}) + "\n")
    print("wrote", RQ1.format(fpf), "records", len(sel), "with tests", sum(bool(t.get(str(i), {}).get("code")) for i in sel))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "items":
        items()
    else:
        assert sys.argv[2] in ARMS
        {"ask": ask, "tests": tests, "completions": completions}[cmd](sys.argv[2], [int(x) for x in sys.argv[3:]])
