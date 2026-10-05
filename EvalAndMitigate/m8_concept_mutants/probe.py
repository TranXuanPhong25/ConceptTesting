"""m8 Phase 1, step 3: a probe harness per focal method (one LLM call, shared by both arms), executed on the original,
on every selected mutant and (offline, for the arbiter-accuracy analysis only) on the fixed checkout.

The probe prompt holds the Advanced docstring, m6's blind evidence pack (declaration, method and class Javadoc,
constructors, fields, other signatures, same-name methods, caller snippets) and nothing else: no focal body, no fixed
version, no trigger test. The LLM writes `static void cases()` = a list of `probe("label", () -> expr)` calls; the
harness (PROBE_TEMPLATE) runs each case in its own thread (5 s), prints `M8P <k> <label> returns <repr>` /
`throws <class>: <message>` / `timeout`. A probe that does not compile against the buggy classes is re-asked with the
compiler errors (at most 2 re-asks; LLM-written code is compiled only in the sandbox).

usage:
  bash run/dock.sh -- python3 m8_concept_mutants/probe.py gen [idx ...]        LLM (credentials, no code execution)
  bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py check [idx ...]   compile + parse cases (sandbox)
  bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py run [idx ...]     execute (sandbox) -> out/probe_runs.jsonl
  python3 m8_concept_mutants/probe.py prompts                                  leak check of every prompt (container)
"""
import datetime, json, os, re, shutil, sys, time

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run", f"{REPO}/m6_agent_oracle", f"{REPO}/m8_concept_mutants"]
D = f"{REPO}/m8_concept_mutants"
OUT = os.environ.get("M8_OUT") or f"{D}/out"  # dock8.sh: /m8out (top-level mount)
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
ADV = f"{REPO}/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"
GEN = f"{OUT}/probe_gen.jsonl"
CHECK = f"{OUT}/probe_check.json"
RUNS = f"{OUT}/probe_runs.jsonl"
MAX_ATTEMPTS = 3
CASE_MS = 5000

# ---------------------------------------------------------------- LLM wrapper: run/gemini_shim.py, every billed response logged
PRICE_IN, PRICE_OUT = 0.30e-6, 2.50e-6  # Vertex AI gemini-2.5-flash, USD per token (text input / output incl. thinking)
CAP_USD = 8.0
LLM_LOG = f"{OUT}/llm_calls.jsonl"


def spent():
    return sum(r["usd"] for r in map(json.loads, open(LLM_LOG))) if os.path.exists(LLM_LOG) else 0.0


class Chat:
    """GeminiChat (thinking off, 429 backoff built in) with a per-response token log and a hard spend cap; sequential."""

    def __init__(self):
        from gemini_shim import GeminiChat
        self.g = GeminiChat()
        orig = self.g.client.models.generate_content

        def logged(**kw):
            r = orig(**kw)
            u = r.usage_metadata
            pin, pout, th = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
            with open(LLM_LOG, "a") as f:
                f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "step": self.step, "key": self.key,
                                    "model": self.g.model, "prompt_tokens": pin, "output_tokens": pout, "thought_tokens": th,
                                    "usd": round(pin * PRICE_IN + (pout + th) * PRICE_OUT, 6)}) + "\n")
            return r
        self.g.client.models.generate_content = logged

    def __call__(self, prompt, step, key, temperature=0):
        s = spent()
        if s > CAP_USD - 0.25:
            sys.exit(f"spend cap: {s:.2f} USD logged, cap {CAP_USD}")
        self.step, self.key = step, key
        return self.g.create(messages=[{"role": "user", "content": prompt}], temperature=temperature, max_tokens=16000).choices[0].message.content


# ---------------------------------------------------------------- prompt
def load():
    import oracle as O  # m6: records, evidence, render_pack, body_leaks
    recs = O.load_records()
    adv = [json.loads(l) for l in open(ADV)]
    assert [a["source:source_method_signature"] for a in adv] == [r["source:source_method_signature"] for r in recs]
    return O, recs, adv, O.load_evidence()


PROBE_PROMPT = """You will write a probe: a small piece of Java that calls the method under test on concrete inputs, so that its observable behaviour on each input can be recorded and compared between implementations. You do not see the method's implementation; use only the documentation and evidence below.

// Documentation of the method under test:
{docstring}

{pack}
Write between 10 and 20 probe cases. Choose the inputs a careful tester would use to check the documented contract: typical inputs, and the edge points of the input space where the method can receive them (null, empty or blank values, boundaries and off-by-one positions, invalid arguments and the error contract, special or escaped characters, letter case and locale, numeric extremes or precision, repeated calls or object state).

Output exactly one ```java block that contains:
1. the import statements the cases need (the probe class is in package {pkg}, so classes of that package need no import);
2. one method `static void cases() throws Exception` whose body is only a sequence of calls
       probe("<short label describing the input>", () -> <expression>);
   Each lambda is self-contained: it builds its own inputs (and objects), calls {name} exactly once and returns the observable result: the return value, or, for a void method or a method that changes state, the resulting state (for example the text written to a StringWriter, or the object's toString() or getter values). Use a block lambda `() -> {{ ...; return <value>; }}` when you need statements. Exceptions are recorded automatically: do not catch them.
Do not write assertions, loops, fields or other methods. Every lambda must compile as a java.util.concurrent.Callable<Object>; labels must be distinct."""

RETRY = """

Your previous probe did not compile against the library. Compiler errors:
{errors}
Write the complete probe again (same output format) and fix these errors."""


def prompt(O, rec, adv, ev, errors=None):
    pkg = rec["source:source_method_signature"].split("#")[0]
    p = PROBE_PROMPT.format(docstring=adv["generated_docstring"].strip(), pack=O.render_pack(rec, ev, False), pkg=pkg,
                            name=rec["source:source_method_name"])
    return p + (RETRY.format(errors=errors) if errors else "")


def appended_leaks(O, rec, adv, p):
    """focal-body windows in the prompt outside the Advanced docstring (which is inherited from the baseline as is)."""
    return O.body_leaks(rec, p.replace(adv["generated_docstring"].strip(), ""))


def prompts_check():
    O, recs, adv, evs = load()
    n, inherited = [], []
    for i, r in enumerate(recs):
        p = prompt(O, r, adv[i], evs[i])
        assert not appended_leaks(O, r, adv[i], p), i
        n.append(len(p))
        if O.body_leaks(r, p):
            inherited.append(r["extra:project_name"])
    print(f"probe prompts {len(n)}, chars median {sorted(n)[len(n) // 2]}, max {max(n)}; outside the docstring no focal-body window "
          f"(asserted); prompts whose Advanced docstring quotes the body (inherited from the baseline): {inherited}")


def code_of(reply):
    blocks = re.findall(r"```java(.*?)```", reply or "", re.DOTALL)
    return blocks[-1].strip() if blocks else None


def gen(idx):
    O, recs, adv, evs = load()
    chat = Chat()
    done = {r["idx"]: r for r in map(json.loads, open(GEN))} if os.path.exists(GEN) else {}
    chk = json.load(open(CHECK)) if os.path.exists(CHECK) else {}
    for i in idx or range(len(recs)):
        d = done.get(i, {"idx": i, "id": recs[i]["extra:project_name"], "attempts": []})
        c = chk.get(str(i))
        if d["attempts"] and (c is None or c["attempt"] != len(d["attempts"]) - 1 or c["ok"] or len(d["attempts"]) >= MAX_ATTEMPTS):
            continue  # waiting for `check`, accepted, or out of attempts
        errors = c["errors"] if d["attempts"] else None
        p = prompt(O, recs[i], adv[i], evs[i], errors)
        assert not appended_leaks(O, recs[i], adv[i], p), f"focal body in probe prompt {i}"
        temp = 0.5 if errors and errors.startswith("no ```java") else 0  # an unparsable reply (e.g. a repetition loop) would repeat at T=0
        reply = chat(p, "probe", i, temperature=temp)
        d["attempts"].append({"prompt": p, "reply": reply, "code": code_of(reply), "temperature": temp})
        done[i] = d
        with open(GEN, "w") as f:
            f.writelines(json.dumps(done[k]) + "\n" for k in sorted(done))
        print(i, d["id"], "attempt", len(d["attempts"]), "code chars", len(d["attempts"][-1]["code"] or ""), f"spent {spent():.3f} USD", flush=True)


# ---------------------------------------------------------------- harness (sandbox)
REPR = r'''
    static String m8repr(Object o) {
        String s = m8repr0(o, 0);
        return s.length() > 400 ? s.substring(0, 400) + "..." : s;
    }
    static String m8repr0(Object o, int depth) {
        if (o == null) return "null";
        if (depth > 3) return "...";
        if (o instanceof String) return "\"" + m8esc((String) o) + "\"";
        if (o instanceof Character) return "'" + m8esc(String.valueOf(o)) + "'";
        if (o instanceof Boolean) return String.valueOf(o);
        if (o instanceof Number) return o.getClass().getSimpleName() + ":" + o;
        if (o instanceof CharSequence) return o.getClass().getSimpleName() + ":\"" + m8esc(o.toString()) + "\"";
        if (o instanceof Class) return "class " + ((Class<?>) o).getName();
        if (o.getClass().isArray()) {
            StringBuilder b = new StringBuilder(o.getClass().getComponentType().getSimpleName() + "[");
            int n = java.lang.reflect.Array.getLength(o);
            for (int i = 0; i < n && i < 50; i++) b.append(i > 0 ? ", " : "").append(m8repr0(java.lang.reflect.Array.get(o, i), depth + 1));
            return b.append(n > 50 ? ", ...]" : "]").toString();
        }
        if (o instanceof java.util.Map) {
            StringBuilder b = new StringBuilder(o.getClass().getSimpleName() + "{");
            int i = 0;
            for (Object e : ((java.util.Map<?, ?>) o).entrySet()) {
                if (i++ >= 50) { b.append(", ..."); break; }
                java.util.Map.Entry<?, ?> en = (java.util.Map.Entry<?, ?>) e;
                b.append(i > 1 ? ", " : "").append(m8repr0(en.getKey(), depth + 1)).append("=").append(m8repr0(en.getValue(), depth + 1));
            }
            return b.append("}").toString();
        }
        if (o instanceof java.util.Collection) {
            StringBuilder b = new StringBuilder(o.getClass().getSimpleName() + "[");
            int i = 0;
            for (Object e : (java.util.Collection<?>) o) {
                if (i++ >= 50) { b.append(", ..."); break; }
                b.append(i > 1 ? ", " : "").append(m8repr0(e, depth + 1));
            }
            return b.append("]").toString();
        }
        return o.getClass().getSimpleName() + ":" + m8esc(String.valueOf(o).replaceAll("@[0-9a-f]{4,}", "@?"));
    }
    static String m8esc(String s) {
        StringBuilder b = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (c == '\\' || c == '"') b.append('\\').append(c);
            else if (c == '\n') b.append("\\n");
            else if (c == '\t') b.append("\\t");
            else if (c == '\r') b.append("\\r");
            else if (c < 32 || c > 126) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.toString();
    }
    static String m8outcome(Throwable e) {
        String m = e.getMessage() == null ? "" : ": " + m8esc(e.getMessage().replaceAll("@[0-9a-f]{4,}", "@?"));
        return "throws " + e.getClass().getName() + (m.length() > 200 ? m.substring(0, 200) + "..." : m);
    }
'''

PROBE_TEMPLATE = """package {pkg};

{imports}

public class M8Probe {{
    static void probe(int k, String label, java.util.concurrent.Callable<Object> c) {{
        final String[] out = {{"timeout"}};
        Thread t = new Thread(() -> {{
            try {{ out[0] = "returns " + m8repr(c.call()); }} catch (Throwable e) {{ out[0] = m8outcome(e); }}
        }});
        t.setDaemon(true);
        t.start();
        try {{ t.join({ms}); }} catch (InterruptedException e) {{ }}
        String o = t.isAlive() ? "timeout" : out[0];
        if (t.isAlive()) t.stop();
        System.out.println("M8P\\t" + k + "\\t" + m8esc(label) + "\\t" + o);
        System.out.flush();
    }}
{repr}
{cases}

    public static void main(String[] a) {{
        try {{ cases(); }} catch (Throwable e) {{ System.out.println("M8P_ABORT\\t" + m8outcome(e)); }}
        System.exit(0);
    }}
}}
"""


def java_str(lit):
    """value of a Java string literal (JSON-compatible escapes; anything else is kept as written)."""
    try:
        return json.loads(lit)
    except ValueError:
        return lit[1:-1]


def parse_code(code):
    """(imports, cases method text with probe(k, ...) indexes, [(k, label, lambda text, prelude)]); None if no cases() method."""
    from mutate import parser, walk, T
    src = code.encode()
    root = parser().parse(src).root_node
    imports = [T(n) for n in root.children if n.type == "import_declaration"]
    meth = [n for n in walk(root) if n.type == "method_declaration" and T(n.child_by_field_name("name")) == "cases"]
    if not meth:
        return None
    m = meth[0]
    calls = [n for n in walk(m) if n.type == "method_invocation" and T(n.child_by_field_name("name")) == "probe"
             and n.child_by_field_name("object") is None]
    # prelude of a case: the top-level non-probe statements of cases() before it (shared locals such as a formatter);
    # the tests repeat it so that each test is self-contained
    body = m.child_by_field_name("body")
    stmts = [x for x in body.named_children if x.type not in ("line_comment", "block_comment")]
    prelude_of = {}
    for st in stmts:
        inner = [c for c in calls if st.start_byte <= c.start_byte < st.end_byte]
        if not inner:
            prelude_of.setdefault("_", []).append(T(st))
        for c in inner:
            prelude_of[c.id] = list(prelude_of.get("_", []))
    cases, edits = [], []
    for k, n in enumerate(calls):
        a = [x for x in n.child_by_field_name("arguments").named_children if x.type not in ("line_comment", "block_comment")]
        if len(a) == 2 and a[0].type == "string_literal" and a[1].type == "lambda_expression":
            cases.append((k, java_str(T(a[0])), T(a[1]), "\n".join(prelude_of.get(n.id, []))))
        args_node = n.child_by_field_name("arguments")
        edits.append((args_node.start_byte + 1, f"{k}, "))
    text = src
    for pos, ins in sorted(edits, reverse=True):
        text = text[:pos] + ins.encode() + text[pos:]
    mt = text[m.start_byte:m.end_byte + sum(len(e[1]) for e in edits)].decode("utf-8", "replace")
    return imports, "    " + mt, cases


def probe_source(rec, code):
    p = parse_code(code)
    if p is None:
        return None, None
    imports, mt, cases = p
    pkg = rec["source:source_method_signature"].split("#")[0]
    return PROBE_TEMPLATE.format(pkg=pkg, imports="\n".join(imports), ms=CASE_MS, repr=REPR, cases=mt), cases


def compile_probe(src, rec, cls_first, cp, out_dir):
    import phase0 as P
    shutil.rmtree(out_dir, ignore_errors=True); os.makedirs(out_dir)
    path = f"{out_dir}/M8Probe.java"
    open(path, "w").write(src)
    r = P.sh(["javac", "-nowarn", "-proc:none", "-encoding", "UTF-8", "-d", out_dir, "-cp", ":".join(cls_first + cp + [P.JUNIT]), path], timeout=180)
    errs = [l for l in r.stderr.splitlines() if l.strip()]
    return r.returncode == 0, "\n".join(errs[:30])[:3000]


def check(idx):
    import phase0 as P
    O, recs, adv, evs = load()
    env = P.load_env()
    gen_ = {r["idx"]: r for r in map(json.loads, open(GEN))}
    chk = json.load(open(CHECK)) if os.path.exists(CHECK) else {}
    for i in idx or sorted(gen_):
        a = len(gen_[i]["attempts"]) - 1
        if str(i) in chk and chk[str(i)]["attempt"] == a:
            continue
        rec, code = recs[i], gen_[i]["attempts"][a]["code"]
        b = env["bugs"][rec["extra:project_name"].replace("_buggy", "")]
        src, cases = probe_source(rec, code) if code else (None, None)
        if src is None:
            ok, errors = False, "no ```java block with a `static void cases()` method"
        else:
            leaks = O.body_leaks(rec, code)
            ok, errors = compile_probe(src, rec, [f"{P.SCR}/orig/{i}/cls"], b["cp_buggy"], f"{P.SCR}/probe/{i}")
            errors = errors.replace(f"{P.SCR}/probe/{i}/", "")
            if ok and not cases:
                ok, errors = False, "no probe(\"label\", () -> ...) case with a string label and a lambda"
        chk[str(i)] = {"attempt": a, "ok": ok, "errors": errors, "cases": cases if ok else None,
                       "body_leaks_in_probe": O.body_leaks(rec, code or "")}
        print(i, rec["extra:project_name"], "attempt", a + 1, "ok" if ok else "FAILED", len(cases or []), "cases", "" if ok else errors[:200], flush=True)
        json.dump(chk, open(CHECK, "w"), indent=1)


def parse_out(stdout):
    out = {}
    for l in stdout.splitlines():
        p = l.split("\t")
        if p[0] == "M8P" and len(p) >= 4:
            out[p[1]] = "DUP" if p[1] in out else p[3]
    return out


def run(idx):
    import phase0 as P
    from multiprocessing import Pool
    recs = [json.loads(l) for l in open(SRC)]
    env = P.load_env()
    chk = json.load(open(CHECK))
    sel = json.load(open(f"{OUT}/selection.json"))
    gen_ = {r["idx"]: r for r in map(json.loads, open(GEN))}
    done = {r["idx"] for r in map(json.loads, open(RUNS))} if os.path.exists(RUNS) else set()
    todo = [int(i) for i, c in chk.items() if c["ok"] and int(i) not in done and (not idx or int(i) in idx)]
    for i in sorted(todo):
        rec = recs[i]
        b = env["bugs"][rec["extra:project_name"].replace("_buggy", "")]
        src, _ = probe_source(rec, gen_[i]["attempts"][chk[str(i)]["attempt"]]["code"])
        ok, err = compile_probe(src, rec, [f"{P.SCR}/orig/{i}/cls"], b["cp_buggy"], f"{P.SCR}/probe/{i}")
        assert ok, (i, err)
        okf, errf = compile_probe(src, rec, [], b["cp_fixed"], f"{P.SCR}/probe/{i}_fixed")  # offline: fixed outputs
        pkg = rec["source:source_method_signature"].split("#")[0]
        jobs = [("orig", [f"{P.SCR}/orig/{i}/cls", f"{P.SCR}/probe/{i}"] + b["cp_buggy"], b["root_buggy"]),
                ("orig2", [f"{P.SCR}/orig/{i}/cls", f"{P.SCR}/probe/{i}"] + b["cp_buggy"], b["root_buggy"])]
        if okf:
            jobs.append(("fixed", [f"{P.SCR}/probe/{i}_fixed"] + b["cp_fixed"], b["root_fixed"]))
        mids = sorted({m for arm in ("concept", "generic") for m in sel[str(i)][arm]})
        jobs += [(m, [f"{P.SCR}/mut/{m}/cls", f"{P.SCR}/probe/{i}"] + b["cp_buggy"], b["root_buggy"]) for m in mids]
        t0 = time.time()
        with Pool(int(os.environ.get("M8_WORKERS") or 6)) as pool:
            outs = pool.map(run_one, [(name, cp, cwd, f"{pkg}.M8Probe") for name, cp, cwd in jobs])
        res = {name: o for (name, _, _), o in zip(jobs, outs)}
        rec_out = {"idx": i, "id": rec["extra:project_name"], "fixed_compiled": okf, "fixed_error": "" if okf else errf[:500],
                   "orig": res["orig"], "orig2": res["orig2"], "fixed": res.get("fixed"), "mutants": {m: res[m] for m in mids}}
        with open(RUNS, "a") as f:
            f.write(json.dumps(rec_out) + "\n")
        nd = [k for k in res["orig"] if res["orig"][k] != res["orig2"].get(k)]
        print(i, rec["extra:project_name"], "cases", len(res["orig"]), "nondeterministic", nd, "mutants", len(mids),
              "fixed compiled", okf, f"{time.time() - t0:.0f}s", flush=True)


def run_one(job):
    import phase0 as P
    name, cp, cwd, main = job
    r = P.sh(P.JVM + ["-cp", ":".join(cp + [P.JUNIT]), main], cwd=cwd, timeout=30 + 25 * CASE_MS / 1000)
    out = parse_out(r.stdout)
    if "M8P_ABORT" in r.stdout:
        out["abort"] = r.stdout.split("M8P_ABORT\t")[1].splitlines()[0][:300]
    if r.returncode == 124:
        out["jvm"] = "timeout"
    return out


if __name__ == "__main__":
    cmd, ids = sys.argv[1], [int(x) for x in sys.argv[2:]]
    {"gen": gen, "check": check, "run": run}.get(cmd, lambda _: prompts_check())(ids)
