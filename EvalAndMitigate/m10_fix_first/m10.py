"""m10_fix_first: raise the fix rate of the Advanced prompt's Part 2 ("corrected implementation"), then check whether
better fixes give better tests (m9: a Part 2 that really fixes the bug gives more E tests and no M, but Part 2 fixes
only ~17-19 of 60 bugs).

Phase A arms (Part 2 fix rate on the 78 focal methods):
  A0   m9 adv_rerun completions, reused (Flash, thinking off, T=0; no new call)
  A1   the same upstream Advanced prompt, Flash, thinking on (dynamic budget), T=0
  A1r  the paper's reasoning-model prompt (Prompt_example/Advanced_Docstring_Prompt_Reasoning_Model), Flash thinking on, T=0
  A2   K=5 samples, Flash thinking off, T=1.0 (the Gemini default); per method: regression filter (drop candidates that
       fail any test passing on the current buggy code), then behavioural consensus on m8's blind probe inputs
  A3   Gemini 2.5 Pro (default = dynamic thinking), T=0, one sample
The prompt is m9's builder (= Advanced_Docstring_Generation.ipynb's PromptFormatter call); A1r swaps only the
instruction block. Trigger tests and the fixed version are used OFFLINE only (scoring, harness check, similarity),
never in a prompt or in the A2 selection.
Phase B: the Part 3 docstring of the chosen candidate (A2: plus "// Undetermined (do not assume): <probe input>"
lines where the surviving candidates disagree) -> the unchanged upstream test generation and evaluation.

usage (from EvalAndMitigate/; run.sh wraps everything):
  python3 m10_fix_first/m10.py selftest | install | cost | docs <arm> [idx ...]       host, stdlib
  NO_ADC=1 bash run/dock.sh -- python3 m10_fix_first/m10.py checkout [bug ...]        sequential defects4j checkouts
  M10_NET=1 bash m10_fix_first/dock10.sh python3 m10_fix_first/m10.py env [--jobs N] [bug ...]
  bash run/dock.sh -- python3 m10_fix_first/m10.py gen <arm> [--jobs N] [idx ...]     LLM (credentials, runs no code)
  bash run/dock.sh -- python3 m10_fix_first/m10.py vertexcheck                        3 tiny calls: models + thinking
  bash m10_fix_first/dock10.sh python3 m10_fix_first/m10.py fix <arm ...> [--jobs N] [--bugs bug ...]
  python3 m10_fix_first/m10.py make-inputs     (source machine only) copy the gitignored inputs + MANIFEST.sha256
"""
import ast, difflib, hashlib, importlib.util, json, multiprocessing, os, platform, re, shutil, subprocess, sys, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run"]
D = f"{REPO}/m10_fix_first"
INP = f"{D}/inputs"
OUT = os.environ.get("M10_OUT") or f"{D}/out"  # dock10.sh: /m10out (top-level mount of the same folder)
RECORDS = f"{INP}/buggy_source_data_unified_invoked.jsonl"
ADV_FILE = "Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"
A0_DOCS = f"{INP}/m9_docs_adv_rerun.jsonl"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m10_{}.jsonl"
LLM_LOG = f"{OUT}/llm_calls.jsonl"
SCR, CK, D4J = "/scratch", "/scratch/ck", "/d4j"  # sandbox paths (dock10.sh)
RUNNER = f"{SCR}/runner10"
SMOKE = [3, 33, 53]  # Cli_32, Lang_20 (1 of its 2 methods), Lang_40

# arm: model, thinking budget (run/gemini_shim.py: 0 = off, -1 = dynamic), temperature, samples K, prompt
ARMS = {"A0": ("gemini-2.5-flash", 0, 0, 1, "advanced"),  # m9 adv_rerun, reused
        "A1": ("gemini-2.5-flash", -1, 0, 1, "advanced"),
        "A1r": ("gemini-2.5-flash", -1, 0, 1, "reasoning"),
        "A2": ("gemini-2.5-flash", 0, 1.0, 5, "advanced"),
        "A3": ("gemini-2.5-pro", -1, 0, 1, "advanced")}
# Vertex AI list price, USD per token (input, output incl. thinking), prompts < 200k tokens
PRICE = {"gemini-2.5-flash": (0.30e-6, 2.50e-6), "gemini-2.5-pro": (1.25e-6, 10.0e-6)}
CAP_USD = float(os.environ.get("M10_CAP_USD", "60"))  # gen refuses new calls above this logged spend (safety stop only)
HTTP_TIMEOUT_MS = 1_200_000  # per request (a 65,536-token Pro completion fits); the shim's client has none
CLASS_MS = 180_000         # per test class (M10Runner)
JVM = ["java", "-Xmx1g", "-XX:+UseSerialGC", "-Djava.awt.headless=true", f"-Dm10.timeout={CLASS_MS}"]
MAX_UND = 8                # Undetermined lines per docstring
NEAR_VERBATIM = 0.95       # token similarity to the developer's fixed method


# ------------------------------------------------------------------ small helpers
def read_jsonl(p):
    """records of a JSONL cache; a line torn by a killed process is skipped (its work is simply redone)."""
    out = []
    for l in open(p) if os.path.exists(p) else []:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sh(cmd, cwd=None, timeout=None):
    """subprocess.run with a timeout (rc 124, partial stdout kept) and retries on transient ENOENT of the cwd."""
    for k in range(3):
        try:
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            return subprocess.CompletedProcess(cmd, 124, out, "TIMEOUT")
        except FileNotFoundError:
            if k == 2:
                raise
            time.sleep(3)


def opt(args, name, default=None, many=False):
    """pops `name value` (or `name v1 v2 ...` up to the next --option) from args."""
    if name not in args:
        return default
    i = args.index(name)
    j = i + 1
    while j < len(args) and not args[j].startswith("--") and (many or j == i + 1):
        j += 1
    vals = args[i + 1:j]
    del args[i:j]
    return vals if many else vals[0]


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


_MODS = {}


def mod(name):
    """reused code, loaded on first use: m9.py (prompt builder, notebook docstring parser, fix_info), m9's fixrate.py
    (Part 2 extraction + substitution, m8 phase0 javac helpers; container only: tree-sitter), m8's probe.py (probe harness)."""
    if name not in _MODS:
        _MODS[name] = _load(f"m10_{name}", {"m9": f"{REPO}/m9_concept_advanced/m9.py",
                                            "fixrate": f"{REPO}/m9_concept_advanced/fixrate.py",
                                            "probe": f"{REPO}/m8_concept_mutants/probe.py"}[name])
    return _MODS[name]


def records():
    return read_jsonl(RECORDS)


def spans():
    """m8's focal method spans in the buggy source file (byte offsets + md5 of the file)."""
    return {int(k): v for k, v in json.load(open(f"{INP}/m8_spans.json")).items()}


def idx_of_bug():
    g = defaultdict(list)
    for i, s in sorted(spans().items()):
        g[s["bug"]].append(i)
    return dict(g)


# ------------------------------------------------------------------ prompts
def _const(path, name):
    """a module-level string constant, read without importing the module (the formatter needs javalang)."""
    return next(ast.literal_eval(n.value) for n in ast.parse(open(path).read()).body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == name)


def example_postfix(name):
    """the instruction block of a Prompt_example file: everything after the closing ``` of its context block."""
    t = open(f"{REPO}/Prompt_example/{name}").read()
    return t[t.rindex("\n```\n") + 5:]


ADV_POST = _const(f"{REPO}/utils/prompt_formats/new_prompt_formatter.py", "ADVANCED_SUMMARIZATION_POST_FIX_BASE")
REASON_POST = example_postfix("Advanced_Docstring_Prompt_Reasoning_Model")


def build_prompt(base, arm):
    """base = the upstream Advanced prompt of a method (m9.base_prompt, the notebook's formatter call). The formatter
    builds context + '\\n```\\n' + instruction block (the base-model block equals Prompt_example's, see selftest); A1r
    puts the reasoning-model block in its place, as upstream would for a reasoning model."""
    assert base.endswith(ADV_POST)
    return base[:len(base) - len(ADV_POST)] + REASON_POST if ARMS[arm][4] == "reasoning" else base


# ------------------------------------------------------------------ LLM
_CTX, _LOG_LOCK = threading.local(), threading.Lock()


def logged_usd():
    with _LOG_LOCK:
        return sum(r["usd"] for r in read_jsonl(LLM_LOG))


def chat(model, budget):
    """run/gemini_shim.GeminiChat for `model` / thinking `budget`, with an HTTP timeout and every API attempt logged
    (tokens incl. thinking, USD) to out/llm_calls.jsonl; the shim retries 429s itself."""
    os.environ.update(GEN_MODEL=model, THINKING_BUDGET=str(budget))
    os.makedirs(OUT, exist_ok=True)
    from gemini_shim import GeminiChat
    from google import genai
    from google.genai import types
    g = GeminiChat()
    g.client = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],  # the shim's settings + a timeout
                            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
                            http_options=types.HttpOptions(timeout=HTTP_TIMEOUT_MS))
    raw = g.client.models.generate_content
    pin, pout = PRICE[model]

    def logged(**kw):
        t0, err = time.time(), None
        try:
            r = raw(**kw)
            u = r.usage_metadata
            it, ot, tt = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
            entry = {"in_tok": it, "out_tok": ot, "thought_tok": tt, "usd": it * pin + (ot + tt) * pout,
                     "finish": str(r.candidates[0].finish_reason) if r.candidates else None}
        except Exception as ex:  # 429, timeout, ...: not billed
            err, entry = ex, {"error": repr(ex)[:200], "usd": 0.0}
        entry.update(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), secs=round(time.time() - t0, 1), model=model,
                     thinking_budget=budget, **getattr(_CTX, "v", {}))
        with _LOG_LOCK, open(LLM_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        if err:
            raise err
        return r

    g.client.models.generate_content = logged
    return g


def gen(arm, idx, jobs):
    assert arm in ARMS and arm != "A0", f"gen arms: {[a for a in ARMS if a != 'A0']}"
    model, budget, temp, K, _ = ARMS[arm]
    recs, a0 = records(), {d["idx"]: d for d in read_jsonl(A0_DOCS)}
    path = f"{OUT}/gen_{arm}.jsonl"
    done = {(r["idx"], r["k"]) for r in read_jsonl(path)}
    todo = [(i, k) for i in (idx or range(len(recs))) for k in range(K) if (i, k) not in done]
    print(f"gen {arm}: {model} thinking_budget={budget} T={temp} K={K}; {len(done)} cached, {len(todo)} to call, "
          f"{jobs} in parallel; logged spend ${logged_usd():.2f} (stop at ${CAP_USD})", flush=True)
    if not todo:
        return
    prompts = {}
    for i in sorted({i for i, _ in todo}):
        # The formatter's constructor listing is order-dependent for a few source files.
        # Use the immutable m9 cache, which is the exact upstream prompt that produced
        # A0, so every Phase A arm receives the same prompt despite that presentation
        # drift.  RECORDS and A0_DOCS are manifest-verified inputs.
        base = a0[i]["prompt"]
        prompts[i] = build_prompt(base, arm)
    g = chat(model, budget)
    nb_parse = mod("m9").nb_parse
    t_start, failed = time.time(), []

    def one(job):
        i, k = job
        if logged_usd() > CAP_USD:
            failed.append(job)
            return f"idx {i} k{k}: skipped, logged spend above M10_CAP_USD={CAP_USD}"
        _CTX.v = {"arm": arm, "idx": i, "k": k}
        t0 = time.time()
        for attempt in range(2):  # the shim already retries 8x with backoff; bounded, never forever
            try:
                r = g.create(messages=[{"role": "user", "content": prompts[i]}], temperature=temp)
                break
            except Exception as e:
                print(f"idx {i} k{k} attempt {attempt + 1} failed: {e!r}"[:300], flush=True)
                if attempt == 1:
                    failed.append(job)
                    return f"idx {i} k{k}: FAILED (not cached; rerun gen to retry)"
                time.sleep(60)
        text = r.choices[0].message.content.strip()  # as the notebook
        rec = {"arm": arm, "idx": i, "k": k, "id": recs[i]["extra:project_name"], "model": model,
               "thinking_budget": budget, "temperature": temp,
               "prompt_sha256": hashlib.sha256(prompts[i].encode()).hexdigest(), "completion": text,
               "generated_docstring": nb_parse(text), "thought_tok": r.usage.completion_tokens_details.reasoning_tokens,
               "secs": round(time.time() - t0, 1)}
        with _LOG_LOCK, open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return f"idx {i} {rec['id']} k{k}: {len(text)} chars, {rec['thought_tok']} thought tokens, {rec['secs']}s"

    with ThreadPoolExecutor(jobs) as ex:
        for n, msg in enumerate(ex.map(one, todo), 1):
            print(f"[{arm} {n}/{len(todo)} {time.time() - t_start:.0f}s ${logged_usd():.2f}] {msg}", flush=True)
    print(f"gen {arm} done: {len(todo) - len(failed)} new, {len(failed)} failed", flush=True)


def candidates(arm):
    """{idx: [{k, completion, generated_docstring}] sorted by k}: A0 = m9 adv_rerun (inputs), others = out/gen_<arm>.jsonl."""
    out = defaultdict(list)
    for r in read_jsonl(A0_DOCS if arm == "A0" else f"{OUT}/gen_{arm}.jsonl"):
        out[r["idx"]].append({"k": r.get("k", 0), "completion": r["completion"], "generated_docstring": r["generated_docstring"]})
    return {i: sorted(v, key=lambda c: c["k"]) for i, v in out.items()}


def vertexcheck():
    """verifies the model ids and thinking configs through the shim (3 tiny calls, logged as arm 'vertexcheck')."""
    for model, budget, temp in (("gemini-2.5-flash", 0, 1.0), ("gemini-2.5-flash", -1, 0), ("gemini-2.5-pro", -1, 0)):
        _CTX.v = {"arm": "vertexcheck"}
        r = chat(model, budget).create(messages=[{"role": "user", "content": "Reply with the single word OK."}], temperature=temp)
        print(f"{model} thinking_budget={budget} T={temp}: {r.choices[0].message.content.strip()!r}, "
              f"thought tokens {r.usage.completion_tokens_details.reasoning_tokens}", flush=True)


# ------------------------------------------------------------------ sandbox: runner, test runs, scoring
def compile_runner():
    os.makedirs(RUNNER, exist_ok=True)
    r = sh(["javac", "-nowarn", "-d", RUNNER, "-cp", mod("fixrate").P0.JUNIT, f"{D}/M10Runner.java"], timeout=300)
    assert r.returncode == 0, r.stderr[-800:]


def run_items(items, cp, cwd):
    """{Class::method: PASS|FAIL} for every test that finished (M10Runner, one JVM); hung or unrun tests are missing."""
    r = sh(JVM + ["-cp", ":".join(cp + [mod("fixrate").P0.JUNIT]), "M10Runner"] + items, cwd=cwd,
           timeout=min(3600, 120 + len(items) * (CLASS_MS / 1000 + 5)))  # M10Runner cuts the per-class limit after a hang
    out = {}
    for l in r.stdout.splitlines():
        p = l.split("\t")
        if len(p) == 3 and p[0] == "M10T" and out.get(p[1]) != "FAIL":
            out[p[1]] = p[2]
    return out


def score(e, res):
    """trigger outcome (offline scoring only) and regression outcome (the developer's view: tests that pass on the
    current code) of one test run. A regression test that did not finish counts as failed."""
    trig = {t: res.get(t, "MISSING") for t in e["trigger"]}
    fail = sorted(t for t in e["regression"] if res.get(t) != "PASS")
    return {"fixed": all(v == "PASS" for v in trig.values()), "any_pass": any(v == "PASS" for v in trig.values()),
            "trigger": trig, "reg_ok": not fail, "reg_fail_n": len(fail), "reg_fail": fail[:20]}


NOT_RUN = {"fixed": False, "any_pass": False, "reg_ok": False}


def select(cands, det):
    """A2's choice for one method. It reads only what a developer has: whether a candidate compiles, whether it passes
    every test that passes on the current code (reg_ok), and its outputs on the blind probe inputs (det = the probe
    cases that are deterministic on the current code). Never the trigger tests or the fixed version.
    Survivors are clustered by their output vector; the largest cluster wins (ties: the earliest sample), its earliest
    sample is the representative. disagree = probe cases on which the survivors' outputs differ."""
    surv = [c for c in cands if c["compiled"] and c["reg_ok"]]
    out = {"n_cand": len(cands), "n_surv": len(surv)}
    if not surv:
        return {**out, "k": cands[0]["k"], "reason": "no survivor: first sample"}
    if det is None:
        return {**out, "k": surv[0]["k"], "reason": "no probe: first survivor"}
    vec = lambda c: tuple((c.get("probe") or {}).get(x, "MISSING") for x in det)
    groups = {}
    for c in surv:
        groups.setdefault(vec(c), []).append(c["k"])
    best = max(groups.values(), key=lambda ks: (len(ks), -min(ks)))
    return {**out, "k": min(best), "reason": "consensus", "clusters": sorted(map(len, groups.values()), reverse=True),
            "disagree": [x for j, x in enumerate(det) if len({vec(c)[j] for c in surv}) > 1]}


def focal_member(members, rec):
    """the focal method among Part 2's members (helpers may come first): same name, then same parameter count."""
    name, n = rec["source:source_method_name"], len(rec["source:source_method_parameters"])
    head = lambda m: m.split("{", 1)[0]
    hits = [m for m in members if re.search(r"\b" + re.escape(name) + r"\s*\(", head(m))]
    npar = lambda m: (lambda p: 0 if not p.strip() else p.count(",") + 1)(head(m)[head(m).find("(") + 1:head(m).rfind(")")])
    return next((m for m in hits if npar(m) == n), hits[0] if hits else members[0])


def undetermined_lines(sel):
    flat = lambda s: re.sub(r"^\(\)\s*->\s*", "", re.sub(r"\s+", " ", s).strip())[:200]
    return [f"// Undetermined (do not assume): {flat(x['input'])}" for x in sel.get("disagree_inputs", [])[:MAX_UND]]


TOK = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|\w+|[^\s\w]', re.S)


def sim(a, b):
    """normalised token similarity of two Java snippets (comments and layout ignored)."""
    tok = lambda s: [t for t in TOK.findall(s or "") if not t.startswith(("//", "/*"))]
    return difflib.SequenceMatcher(None, tok(a), tok(b), autojunk=False).ratio()


# ------------------------------------------------------------------ env: compiled scratch copy + regression oracle per bug
def method_texts(bug, f, idxs, bsrc):
    """offline: {idx: (buggy method text, the fixed checkout's same-signature method text or None)} (m9 check's matching)."""
    FR, SP = mod("fixrate"), spans()
    MU = FR.MU
    fsrc = open(f"{D4J}/{bug}/fixed/{f}", "rb").read()
    broot, froot = MU.parser().parse(bsrc).root_node, MU.parser().parse(fsrc).root_node
    out = {}
    for i in idxs:
        bn = next(n for n in FR.walk(broot) if n.start_byte == SP[i]["mstart"] and n.end_byte == SP[i]["mend"])
        name, params = FR.T(bn.child_by_field_name("name")), MU.norm(FR.T(bn.child_by_field_name("parameters")))
        fn = [n for n in FR.walk(froot) if n.type == bn.type and FR.T(n.child_by_field_name("name")) == name
              and MU.norm(FR.T(n.child_by_field_name("parameters"))) == params]
        out[i] = (FR.T(bn), FR.T(fn[0]) if len(fn) == 1 else None)
    return out


def clean_tests(bug, root):
    """pipeline evaluations write generated tests (and .bak copies of trigger test files) into the shared checkouts'
    test dirs; undo that in the scratch copy (from the checkout's own git; the shared checkout stays untouched)."""
    ck = f"{D4J}/{bug}/buggy"
    tdir = sh(["defects4j", "export", "-p", "dir.src.tests"], cwd=root, timeout=600).stdout.strip()
    git = lambda *a: subprocess.run(["git", "--no-optional-locks", *a], cwd=ck, capture_output=True)
    st = git("status", "--porcelain", "--untracked-files=all", "--", tdir).stdout.decode("utf-8", "replace")
    n = 0
    for line in st.splitlines():
        code, path = line[:2], line[3:].strip('"')
        if " -> " in path or not os.path.lexists(f"{root}/{path}") and code != " D":
            continue
        if code == "??":
            os.remove(f"{root}/{path}")
        else:
            os.makedirs(os.path.dirname(f"{root}/{path}"), exist_ok=True)
            open(f"{root}/{path}", "wb").write(git("show", f"HEAD:{path}").stdout)
        n += 1
    return n


def env_bug(bug):
    """scratch copy of the buggy checkout (/scratch/ck/<bug>), `defects4j compile`, classpath, tests.relevant; the
    regression oracle = relevant tests that pass both on the defects4j-compiled classes and with the focal file
    recompiled alone (as every candidate is), trigger tests excluded; harness check with the fixed focal methods."""
    FR, SP, IDX = mod("fixrate"), spans(), idx_of_bug()
    t0, idxs = time.time(), IDX[bug]
    files = {SP[i]["file"] for i in idxs}
    assert len(files) == 1, files
    f = files.pop()
    root = f"{CK}/{bug}"
    for d in (root, f"{root}.orig", f"{root}.fixedcheck"):
        shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(f"{D4J}/{bug}/buggy", root, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    n_cleaned = clean_tests(bug, root)
    for _ in range(2):
        c = sh(["defects4j", "compile"], cwd=root, timeout=1800)
        if c.returncode == 0:
            break
    assert c.returncode == 0, f"{bug}: defects4j compile failed: {c.stderr[-500:]}"
    exp = lambda prop: sh(["defects4j", "export", "-p", prop], cwd=root, timeout=600).stdout.strip()
    cp = [x.replace(root, "{ROOT}", 1) if x == root or x.startswith(root + "/") else x
          for x in exp("cp.test").split(":") if x and os.path.exists(x)]  # D4J also lists optional jars that do not exist
    cpr = [x.replace("{ROOT}", root) for x in cp]
    relevant = sorted(set(re.split(r"[\s,;:]+", exp("tests.relevant"))) - {""})
    src = open(f"{root}/{f}", "rb").read()
    assert all(hashlib.md5(src).hexdigest() == SP[i]["src_md5"] for i in idxs), f"{bug}: focal file differs from m8's checkout"
    fi = json.load(open(f"{REPO}/data/d4j2_fix_info/{bug}/buggy_fix_info.json"))
    trigger = [f"{t['test_class']}::{t['test_function']}" for t in fi["trigger_tests"]]  # offline scoring only
    items = relevant + [t for t in trigger if t.split("::")[0] not in relevant]
    base = run_items(items, [RUNNER] + cpr, root)  # the classes `defects4j compile` built
    ok, err = FR.P0.compile_file(src, f, cpr, f"{root}.orig")
    assert ok, f"{bug}: the unmodified focal file does not compile alone: {err}"
    orig = run_items(items, [f"{root}.orig/cls", RUNNER] + cpr, root)
    shutil.rmtree(f"{root}.orig", ignore_errors=True)
    # ponytail: two runs catch most flaky tests; a test flaky beyond that can wrongly reject an A2 candidate
    rec = {"bug": bug, "file": f, "cp": cp, "relevant_classes": relevant, "items": items, "trigger": trigger,
           "regression": sorted(t for t, s in orig.items() if s == "PASS" and base.get(t) == "PASS" and t not in trigger),
           "n_tests": len(orig), "n_not_passing_on_buggy": sum(s != "PASS" for s in orig.values()),  # a count: no names kept
           "n_differ_d4j_vs_recompiled": sum(base.get(t) != s for t, s in orig.items()) + sum(t not in orig for t in base),
           "trigger_on_buggy": {t: orig.get(t, "MISSING") for t in trigger}, "test_files_restored": n_cleaned}
    texts = method_texts(bug, f, idxs, src)
    broot = FR.MU.parser().parse(src).root_node
    edits = {i: FR.part2("```java\n" + ft + "\n```\n", RECS[i], FR.declared(broot)) for i, (_, ft) in texts.items() if ft}
    chk = {"methods_matched": len(edits), "of": len(idxs), "compiled": False, **NOT_RUN}
    if edits:
        data = FR.substitute(src, [(SP[i]["mstart"], SP[i]["mend"], *edits[i]) for i in edits])
        ok, err = FR.P0.compile_file(data, f, cpr, f"{root}.fixedcheck")
        chk.update(compiled=ok, err=err[:300])
        if ok:
            s = score(rec, run_items(items, [f"{root}.fixedcheck/cls", RUNNER] + cpr, root))
            chk.update({k: s[k] for k in ("fixed", "any_pass", "reg_ok", "reg_fail_n")})
        shutil.rmtree(f"{root}.fixedcheck", ignore_errors=True)
    rec["fixed_check"] = chk  # offline: does substituting the developer's focal methods fix the bug in this harness?
    rec["methods"] = {str(i): {"buggy": b, "fixed": ft} for i, (b, ft) in texts.items()}
    rec["secs"] = round(time.time() - t0)
    return rec


def _init_env():
    global RECS
    RECS = records()


def _env_safe(bug):
    try:
        return bug, env_bug(bug), None
    except Exception as e:
        return bug, None, repr(e)[:600]


def env_stage(bugs, jobs):
    path = f"{OUT}/env.json"
    E = json.load(open(path)) if os.path.exists(path) else {}
    todo = [b for b in (bugs or sorted(idx_of_bug())) if b not in E]
    print(f"env: {len(E)} bugs cached, {len(todo)} to build, {jobs} in parallel", flush=True)
    compile_runner()
    t0 = time.time()
    with multiprocessing.Pool(jobs, initializer=_init_env) as pool:
        for n, (bug, rec, err) in enumerate(pool.imap_unordered(_env_safe, todo), 1):
            if rec is None:
                print(f"[env {n}/{len(todo)}] {bug} FAILED (rerun env to retry): {err}", flush=True)
                continue
            E[bug] = rec
            json.dump(E, open(path + ".tmp", "w"), indent=1)
            os.replace(path + ".tmp", path)
            c = rec["fixed_check"]
            print(f"[env {n}/{len(todo)} {time.time() - t0:.0f}s] {bug}: {len(rec['relevant_classes'])} relevant classes, "
                  f"{rec['n_tests']} tests, regression oracle {len(rec['regression'])}, not passing on buggy "
                  f"{rec['n_not_passing_on_buggy']}, d4j vs recompiled differ {rec['n_differ_d4j_vs_recompiled']}; trigger "
                  f"fails on buggy: {all(v != 'PASS' for v in rec['trigger_on_buggy'].values())}; fixed methods substituted: "
                  f"{'FIX' if c['fixed'] else 'no fix'} (reg_ok {c['reg_ok']}); {rec['secs']}s", flush=True)
    print(f"env: {len(E)}/{len(idx_of_bug())} bugs ready", flush=True)


# ------------------------------------------------------------------ fix: candidates -> compile, tests, probes, selection
def rkey(r):
    return {"cand": lambda: ("cand", r["idx"], r["k"]), "select": lambda: ("select", r["idx"], r["n"]),
            "bug": lambda: ("bug", tuple(map(tuple, r["pairs"])))}[r["kind"]]()


def _init_fix(lock, arms):
    global LOCK, ENV, CANDS, RECS, SP, IDX, PROBES
    LOCK, ENV, RECS, SP, IDX = lock, json.load(open(f"{OUT}/env.json")), records(), spans(), idx_of_bug()
    CANDS = {a: candidates(a) for a in arms}
    PROBES = json.load(open(f"{INP}/m8_probes.json"))


def prep_probe(i, root, cp, jd):
    """m8's probe for method i (blind: written from the Advanced docstring + interface evidence), compiled against the
    current classes and run twice on them: det = the cases with the same output both times."""
    if str(i) not in PROBES:
        return {"det": None, "reason": "no accepted m8 probe for this method"}
    PR = mod("probe")
    src, cases = PR.probe_source(RECS[i], PROBES[str(i)])
    pdir = f"{jd}/probe{i}"
    ok, err = PR.compile_probe(src, RECS[i], [], cp, pdir)
    if not ok:
        return {"det": None, "reason": "probe does not compile: " + err[:200]}
    main = RECS[i]["source:source_method_signature"].split("#")[0] + ".M8Probe"
    b1, b2 = (PR.run_one(("buggy", [pdir] + cp, root, main)) for _ in range(2))
    det = sorted((k for k, v in b1.items() if k not in ("abort", "jvm") and b2.get(k) == v), key=int)
    return {"det": det, "reason": "ok", "dir": pdir, "main": main, "cases": {str(k): (lab, lam) for k, lab, lam, _ in cases}}


def fix_bug(job):
    arm, bug = job
    FR, K, e = mod("fixrate"), ARMS[arm][3], ENV[bug]
    cands = CANDS[arm]
    path = f"{OUT}/fix_{arm}.jsonl"
    with LOCK:  # other jobs append to the same file
        prev = {rkey(r): r for r in read_jsonl(path) if r["bug"] == bug}
    jd = f"{SCR}/job/{arm}_{bug}"
    shutil.rmtree(jd, ignore_errors=True)
    root = f"{jd}/ck"  # this job's own copy: tests may write into their working directory
    shutil.copytree(f"{CK}/{bug}", root, symlinks=True)
    cp = [x.replace("{ROOT}", root) for x in e["cp"]]
    src = open(f"{root}/{e['file']}", "rb").read()
    existing = FR.declared(FR.MU.parser().parse(src).root_node)
    memo, t_job = {}, time.time()

    def run(edits, tag):  # identical substituted files are compiled and run once per job
        data = FR.substitute(src, [(SP[i]["mstart"], SP[i]["mend"], *edits[i]) for i in edits])
        h = hashlib.sha256(data).hexdigest()
        if h not in memo:
            d = f"{jd}/c/{tag}"
            ok, err = FR.P0.compile_file(data, e["file"], cp, d)
            memo[h] = (ok, err, run_items(e["items"], [f"{d}/cls", RUNNER] + cp, root) if ok else {}, f"{d}/cls")
        return memo[h]

    def put(r):
        with LOCK, open(path, "a") as f:
            f.write(json.dumps(r) + "\n")
        prev[rkey(r)] = r

    sel, msgs = {}, []
    for i in [i for i in IDX[bug] if i in cands]:
        cs = cands[i]
        probe = prep_probe(i, root, cp, jd) if K > 1 and ("select", i, K) not in prev and len(cs) == K else None
        want_probe = bool(probe) and probe["det"] is not None
        rs = []
        for c in cs:
            r = prev.get(("cand", i, c["k"]))
            # cached, unless it is a survivor still without probe outputs (evaluated before all K samples existed)
            if r is not None and not (want_probe and r["reg_ok"] and "probe" not in r):
                rs.append(r)
                continue
            t0 = time.time()
            members, imports = FR.part2(c["completion"], RECS[i], existing)
            r = {"kind": "cand", "arm": arm, "bug": bug, "idx": i, "k": c["k"], "part2": members is not None}
            if members is None:
                r.update(compiled=False, err=imports, **NOT_RUN)
            else:
                ok, err, res, cls = run({i: (members, imports)}, f"{i}_{c['k']}")
                r.update(focal=focal_member(members, RECS[i]), n_members=len(members), compiled=ok, err=err[:300], **(score(e, res) if ok else NOT_RUN))
                if want_probe and r["reg_ok"]:  # probe outputs: survivors only
                    out = mod("probe").run_one(("cand", [cls, probe["dir"]] + cp, root, probe["main"]))
                    r["probe"] = {x: out.get(x, "MISSING") for x in probe["det"]}
            r["secs"] = round(time.time() - t0, 1)
            put(r)
            rs.append(r)
            print(f"  {arm} idx {i} {bug} k{c['k']}: " + ("no Part 2" if not r["part2"] else "compile error" if not r["compiled"]
                  else f"regression {'ok' if r['reg_ok'] else 'FAIL ' + str(r['reg_fail_n'])}, trigger {'FIXED' if r['fixed'] else 'not fixed'}")
                  + f" ({r['secs']}s)", flush=True)
        if len(rs) < K:
            msgs.append(f"idx {i}: {len(rs)}/{K} samples generated, no selection yet")
            continue
        s = prev.get(("select", i, K))
        if s is None:
            s = {"kind": "select", "arm": arm, "bug": bug, "idx": i, "n": K}
            if K == 1:
                s.update(k=rs[0]["k"], reason="single sample")
            else:
                s.update(select(rs, probe["det"]), probe=probe["reason"], det_cases=len(probe["det"] or []))
                s["disagree_inputs"] = [{"case": x, "label": probe["cases"][x][0], "input": probe["cases"][x][1]}
                                        for x in s.get("disagree", []) if x in probe["cases"]]
            put(s)
        sel[i] = s["k"]
        msgs.append(f"idx {i}: k{s['k']} ({s['reason']}" + (f", {s['n_surv']}/{K} survive, {len(s.get('disagree', []))} "
                    f"undetermined inputs" if K > 1 else "") + f", {'FIXED' if prev[('cand', i, s['k'])]['fixed'] else 'not fixed'})")
    if len(IDX[bug]) > 1 and len(sel) == len(IDX[bug]):  # all focal methods of the bug together (always one file)
        pairs = [[i, sel[i]] for i in sorted(sel)]
        if ("bug", tuple(map(tuple, pairs))) not in prev:
            edits = {}
            for i, k in pairs:
                m, imp = FR.part2(next(c for c in cands[i] if c["k"] == k)["completion"], RECS[i], existing)
                if m is not None:
                    edits[i] = (m, imp)
            r = {"kind": "bug", "arm": arm, "bug": bug, "pairs": pairs, "with_part2": sorted(edits)}
            if edits:
                ok, err, res, _ = run(edits, "bug")
                r.update(compiled=ok, err=err[:300], **(score(e, res) if ok else NOT_RUN))
            else:
                r.update(compiled=False, err="no Part 2", **NOT_RUN)
            put(r)
            msgs.append(f"bug (all {len(pairs)} methods): {'FIXED' if r['fixed'] else 'not fixed'}")
    shutil.rmtree(jd, ignore_errors=True)
    return f"{arm} {bug} ({time.time() - t_job:.0f}s): " + "; ".join(msgs)


def _fix_safe(job):
    try:
        return fix_bug(job)
    except Exception as e:
        shutil.rmtree(f"{SCR}/job/{job[0]}_{job[1]}", ignore_errors=True)
        return f"{job[0]} {job[1]}: FAILED (rerun fix to retry): {e!r}"[:600]


def fix_stage(arms, jobs, bugs):
    for a in arms:
        assert a in ARMS, a
    E = json.load(open(f"{OUT}/env.json"))
    IDX = idx_of_bug()
    cands = {a: candidates(a) for a in arms}
    want = bugs or sorted(IDX)
    missing = [b for b in want if b not in E]
    if missing:
        print("no env yet (run env first), skipped:", missing, flush=True)
    work = [(a, b) for b in want if b in E for a in arms if any(i in cands[a] for i in IDX[b])]
    print(f"fix {' '.join(arms)}: {len(work)} (arm, bug) jobs, {jobs} in parallel (cached results are reused)", flush=True)
    compile_runner()
    t0 = time.time()
    with multiprocessing.Pool(jobs, initializer=_init_fix, initargs=(multiprocessing.Lock(), arms)) as pool:
        for n, msg in enumerate(pool.imap_unordered(_fix_safe, work), 1):
            print(f"[fix {n}/{len(work)} {time.time() - t0:.0f}s] {msg}", flush=True)


# ------------------------------------------------------------------ Phase B docstrings
def selections(arm):
    """{idx: the select record with the most samples} from out/fix_<arm>.jsonl."""
    out = {}
    for r in read_jsonl(f"{OUT}/fix_{arm}.jsonl"):
        if r["kind"] == "select" and r["n"] >= out.get(r["idx"], {}).get("n", 0):
            out[r["idx"]] = r
    return out


def docs(arm, idx):
    """data/prompts/..._with_m10_<arm>[_smoke].jsonl: source record + the selected candidate's Part 3 docstring (the
    notebook's parse of its completion), plus for A2 the Undetermined lines. Leak check on the appended lines."""
    recs, sel, cands = records(), selections(arm), candidates(arm)
    a0 = {d["idx"]: d["prompt"] for d in read_jsonl(A0_DOCS)}
    want = idx or list(range(len(recs)))
    missing = [i for i in want if i not in sel or ARMS[arm][3] != sel[i]["n"]]
    assert not missing, f"{arm}: no complete selection for idx {missing} (run gen + fix first)"
    norm = lambda s: re.sub(r"\s+", " ", s)
    rows, n_und = [], 0
    for i in want:
        s = sel[i]
        c = next(c for c in cands[i] if c["k"] == s["k"])
        und = undetermined_lines(s)
        fixed, trig = mod("m9").fix_info(recs[i])  # offline: fixed-side patch lines, trigger test names
        text = "\n".join(und)
        leaks = [x for x in fixed if norm(x) in norm(text) and norm(x) not in norm(a0[i])] + \
                [x for x in trig if re.search(r"\b" + re.escape(x) + r"\b", text) and not re.search(r"\b" + re.escape(x) + r"\b", a0[i])]
        assert not leaks, f"idx {i}: patch line or trigger name in the Undetermined lines: {leaks}"
        n_und += bool(und)
        rows.append({**recs[i], "generated_docstring": c["generated_docstring"] + "".join(l + "\n" for l in und),
                     "m10_arm": arm, "m10_k": s["k"], "m10_completion": c["completion"]})
    out = DOC_OUT.format(arm + ("_smoke" if idx else ""))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"wrote {out}: {len(rows)} docstrings, {n_und} with Undetermined lines")


# ------------------------------------------------------------------ inputs, cost
INPUT_SOURCES = {  # input file: where it came from on the source machine (README: provenance)
    "buggy_source_data_unified_invoked.jsonl": "data/prompts/buggy_source_data_unified_invoked.jsonl",
    ADV_FILE: f"data/prompts/{ADV_FILE}",
    "m9_docs_adv_rerun.jsonl": "m9_concept_advanced/out/docs_adv_rerun.jsonl",
    "m9_fixrate_adv_rerun.json": "m9_concept_advanced/out/fixrate_adv_rerun.json",
}


def make_inputs():
    """source machine only: copy the inputs (some are gitignored) and write MANIFEST.sha256."""
    os.makedirs(INP, exist_ok=True)
    for name, src in INPUT_SOURCES.items():
        shutil.copyfile(f"{REPO}/{src}", f"{INP}/{name}")
    with open(f"{INP}/m9_llm_calls_adv_rerun.jsonl", "w") as f:  # A0's docstring-call cost
        f.writelines(l for l in open(f"{REPO}/m9_concept_advanced/out/llm_calls.jsonl") if json.loads(l)["arm"] == "adv_rerun")
    M8 = f"{REPO}/m8_concept_mutants/out"
    json.dump({m["idx"]: {k: m[k] for k in ("bug", "file", "mstart", "mend", "src_md5")} for m in map(json.loads, open(f"{M8}/mutants.jsonl"))},
              open(f"{INP}/m8_spans.json", "w"), indent=1)
    chk, gen_ = json.load(open(f"{M8}/probe_check.json")), {r["idx"]: r for r in map(json.loads, open(f"{M8}/probe_gen.jsonl"))}
    json.dump({i: gen_[int(i)]["attempts"][c["attempt"]]["code"] for i, c in sorted(chk.items(), key=lambda x: int(x[0])) if c["ok"]},
              open(f"{INP}/m8_probes.json", "w"), indent=1)
    cwd = os.getcwd()
    os.chdir(REPO)  # m6's analyze uses repo-relative paths
    A6 = _load("m6_analyze", "m6_agent_oracle/analyze.py")
    ref = {name: [{k: m[k] for k in ("sig", "counts", "glitch")} for m in A6.load(fpf, folder)]
           for name, fpf, folder in (("Advanced Doc", "unified_invoked_advanced_docstring_prompt", None),
                                     ("A0 (m9 adv_rerun)", "m9_adv_rerun", "m9_concept_advanced"))}
    os.chdir(cwd)
    json.dump(ref, open(f"{INP}/ref_outcomes.json", "w"), indent=1)
    names = sorted(n for n in os.listdir(INP) if n != "MANIFEST.sha256")
    with open(f"{INP}/MANIFEST.sha256", "w") as f:
        f.writelines(f"{sha256(f'{INP}/{n}')}  {n}\n" for n in names)
    for n in names:
        print(f"{os.path.getsize(f'{INP}/{n}') / 1e6:8.2f} MB  {n}")


def verify_manifest():
    bad = []
    for line in open(f"{INP}/MANIFEST.sha256"):
        h, name = line.rstrip("\n").split("  ", 1)
        if not os.path.exists(f"{INP}/{name}") or sha256(f"{INP}/{name}") != h:
            bad.append(name)
    return bad


def install():
    """host: verify the inputs, create the output folders on the host (so that files written later by the host are not
    blocked by root-owned folders a Linux container would create), warn about a tree-sitter library of another arch."""
    bad = verify_manifest()
    assert not bad, f"inputs missing or changed (MANIFEST.sha256): {bad}"
    for d in (OUT, f"{REPO}/data/prompts/rq1", f"{REPO}/data/rq1/logs", f"{REPO}/data/rq1/results_test/chatgpt"):
        os.makedirs(d, exist_ok=True)
    so = f"{REPO}/data/build/java.so"
    if os.path.exists(so):
        head = open(so, "rb").read(20)
        mach = {0x3E: "x86_64", 0xB7: "aarch64"}.get(int.from_bytes(head[18:20], "little")) if head[:4] == b"\x7fELF" else "not ELF"
        host = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x86_64", "AMD64": "x86_64"}.get(platform.machine())
        if mach != host:
            print(f"WARNING: {so} is built for {mach}, this machine is {platform.machine()}: delete it, the container "
                  f"rebuilds it (it is gitignored; a copied working tree can carry one from another machine)")
    print(f"inputs ok ({len(open(f'{INP}/MANIFEST.sha256').readlines())} files); output folders ready")


def cost():
    by = defaultdict(lambda: [0, 0, 0.0, 0])
    for c in read_jsonl(LLM_LOG):
        k = by[c.get("arm", "?")]
        k[0] += 1; k[1] += "in_tok" in c; k[2] += c["usd"]; k[3] += c.get("thought_tok", 0)
    a0 = read_jsonl(f"{INP}/m9_llm_calls_adv_rerun.jsonl")
    print(f"A0 (m9 adv_rerun, reused): {len(a0)} API attempts, ${sum(c['usd'] for c in a0):.3f} (spent in m9)")
    for a, (n, billed, usd, th) in sorted(by.items()):
        print(f"{a}: {n} API attempts ({billed} billed), {th} thinking tokens, ${usd:.3f}")
    print(f"m10 total logged: ${sum(v[2] for v in by.values()):.3f}")


# ------------------------------------------------------------------ selftest
def selftest():
    bad = verify_manifest()
    assert not bad, f"MANIFEST.sha256 mismatch: {bad}"
    recs, a0 = records(), {d["idx"]: d for d in read_jsonl(A0_DOCS)}
    assert len(recs) == 78 and sorted(a0) == list(range(78)) and len(json.load(open(f"{INP}/m8_probes.json"))) == 72
    assert len(spans()) == 78 and len(idx_of_bug()) == 60 and [recs[i]["extra:project_name"] for i in SMOKE] == ["Cli_32_buggy", "Lang_20_buggy", "Lang_40_buggy"]
    # prompts: the restored formatter block is the paper's base-model example; A1r swaps in the reasoning-model block only
    assert ADV_POST == example_postfix("Advanced_Docstring_Prompt_Base_Model")
    assert REASON_POST.startswith("Please provide a formal docstring") and "Corrected Implementation" not in REASON_POST
    for i, d in a0.items():
        for arm in ARMS:
            p = build_prompt(d["prompt"], arm)
            if ARMS[arm][4] == "advanced":
                assert p == d["prompt"]
            else:
                assert p.endswith(REASON_POST) and p[:-len(REASON_POST)] == d["prompt"][:-len(ADV_POST)] and "```" in p[-len(REASON_POST) - 5:]
    # docstring parsing: the notebook's own code (via m9), on an A1r-style answer
    assert mod("m9").nb_parse("analysis ...\n```java\n/**\n * Doc.\n */\n```") == "\n/**\n * Doc.\n */\n"
    # regression filter: a regression test that fails or never finished rejects; trigger tests only score
    e = {"trigger": ["T::t1"], "regression": ["R::a", "R::b"]}
    s = score(e, {"T::t1": "PASS", "R::a": "PASS", "R::b": "PASS"})
    assert s["fixed"] and s["reg_ok"] and s["reg_fail_n"] == 0
    s = score(e, {"T::t1": "FAIL", "R::a": "PASS"})
    assert not s["fixed"] and not s["reg_ok"] and s["reg_fail"] == ["R::b"] and s["trigger"] == {"T::t1": "FAIL"}
    assert score(e, {"R::a": "PASS", "R::b": "PASS"})["trigger"] == {"T::t1": "MISSING"}
    # consensus on synthetic candidates
    c = lambda k, comp, reg, probe, fixed=False: {"k": k, "compiled": comp, "reg_ok": reg, "probe": probe, "fixed": fixed}
    det = ["0", "1", "2"]
    cs = [c(0, True, False, None, True), c(1, True, True, {"0": "a", "1": "x", "2": "z"}), c(2, False, False, None),
          c(3, True, True, {"0": "a", "1": "y", "2": "z"}), c(4, True, True, {"0": "a", "1": "y", "2": "z"})]
    s = select(cs, det)
    assert (s["k"], s["n_surv"], s["clusters"], s["disagree"], s["reason"]) == (3, 3, [2, 1], ["1"], "consensus"), s
    assert select([{**x, "fixed": not x["fixed"], "trigger": {"T::t1": "PASS"}} for x in cs], det) == s  # trigger-blind
    s2 = select([c(0, True, True, {"0": "p"}), c(1, True, True, {"0": "q"})], ["0"])
    assert (s2["k"], s2["disagree"]) == (0, ["0"])  # tie: earliest sample
    s3 = select([c(0, True, True, {"0": "p"}), c(1, True, True, {}), c(2, True, True, {})], ["0"])
    assert (s3["k"], s3["clusters"]) == (1, [2, 1])  # missing outputs cluster together
    assert select([c(0, False, False, None), c(1, True, False, None)], det) == {"n_cand": 2, "n_surv": 0, "k": 0, "reason": "no survivor: first sample"}
    assert select(cs, None)["k"] == 1 and select(cs, None)["reason"] == "no probe: first survivor"
    assert select([c(0, True, True, {"0": "a"}), c(1, True, True, {"0": "a"})], ["0"])["disagree"] == []
    # Undetermined lines and similarity
    u = undetermined_lines({"disagree_inputs": [{"case": "1", "label": "l", "input": "() -> StringUtils.join(new Object[]{null},\n   ',')"}]})
    assert u == ["// Undetermined (do not assume): StringUtils.join(new Object[]{null}, ',')"], u
    assert undetermined_lines({}) == [] and len(undetermined_lines({"disagree_inputs": [{"input": "x"}] * 20})) == MAX_UND
    assert sim("int f() { return a+1; } // c", "int f(){\n  return a + 1; /* d */ }") == 1.0
    assert sim('s.equals("//x")', 's.equals("//y")') < 1.0 and sim("return a;", "throw new X();") < 0.5
    rec = {"source:source_method_name": "join", "source:source_method_parameters": [["Object[]", "a"], ["char", "s"]]}
    assert focal_member(["private int helper() { return 1; }", "public String join(Object[] a) { }",
                         "public String join(Object[] a, char s) { return x; }"], rec).startswith("public String join(Object[] a, char s)")
    # option parsing
    args = ["fix", "A0", "A2", "--jobs", "3", "--bugs", "Cli_32", "Lang_20"]
    assert opt(args, "--jobs") == "3" and opt(args, "--bugs", many=True) == ["Cli_32", "Lang_20"] and args == ["fix", "A0", "A2"]
    print("host checks ok: manifest, prompts per arm (78 x 5), notebook docstring parse, regression filter, consensus, "
          "Undetermined lines, similarity, options")
    # Part 2 extraction / probe parsing need tree-sitter (container); the m9/m8 code is reused unchanged
    try:
        import tree_sitter  # noqa: F401
        assert REPO == "/repo"
    except (ImportError, AssertionError):
        print("SKIPPED here (no tree-sitter / not in the container): Part 2 extraction and probe parsing. Run "
              "`bash m10_fix_first/dock10.sh python3 m10_fix_first/m10.py selftest` for those (run.sh smoke does).")
        return print("selftest ok (host part)")
    FR, PR = mod("fixrate"), mod("probe")
    FR.selftest()
    n = sum(FR.part2(a0[i]["completion"], recs[i], set())[0] is not None for i in range(78))
    assert n == 74, f"Part 2 found in {n}/78 A0 completions; m9 found 74"
    probes = json.load(open(f"{INP}/m8_probes.json"))
    assert all(PR.probe_source(recs[int(i)], code)[1] for i, code in probes.items())
    if shutil.which("javac") and os.access(SCR, os.W_OK):
        compile_runner()
    print(f"container checks ok: fixrate selftest, Part 2 found in {n}/78 A0 completions (m9: 74), 72 probes parse"
          + (", M10Runner compiles" if shutil.which("javac") else ""))
    print("selftest ok")


def checkout(bugs):
    """container (run/dock.sh): sequential `defects4j checkout` of the buggy and fixed version of each bug into
    d4j_proj_base (the d4jproj volume); complete checkouts are kept. Then builds data/build/java.so (tree-sitter,
    gitignored) while the repo is mounted writable: the m10 sandbox mounts it read-only."""
    bugs = bugs or sorted(idx_of_bug())
    t0 = time.time()
    for n, b in enumerate(bugs, 1):
        p, i = b.rsplit("_", 1)
        for v in ("buggy", "fixed"):
            d = f"{REPO}/d4j_proj_base/{b}/{v}"
            if os.path.exists(f"{d}/.defects4j.config"):
                continue
            for attempt in (1, 2):
                shutil.rmtree(d, ignore_errors=True)
                r = sh(["defects4j", "checkout", "-p", p, "-v", f"{i}{v[0]}", "-w", d], timeout=1800)
                if r.returncode == 0 and os.path.exists(f"{d}/.defects4j.config"):
                    break
                print(f"checkout {b} {v} attempt {attempt} failed: {r.stderr[-300:]}", flush=True)
            else:
                shutil.rmtree(d, ignore_errors=True)
                sys.exit(f"checkout failed: {b} {v}")
        print(f"[checkout {n}/{len(bugs)} {time.time() - t0:.0f}s] {b}: buggy + fixed ready", flush=True)
    import data.configuration  # noqa: F401


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args.pop(0) if args else "help"
    jobs = int(opt(args, "--jobs", "4"))
    bugs = opt(args, "--bugs", many=True)
    if cmd == "gen":
        gen(args[0], [int(x) for x in args[1:]], jobs)
    elif cmd == "fix":
        fix_stage(args, jobs, bugs)
    elif cmd in ("env", "checkout"):
        (env_stage(args, jobs) if cmd == "env" else checkout(args))
    elif cmd == "docs":
        docs(args[0], [int(x) for x in args[1:]])
    elif cmd in ("selftest", "install", "cost", "vertexcheck", "make-inputs"):
        {"selftest": selftest, "install": install, "cost": cost, "vertexcheck": vertexcheck, "make-inputs": make_inputs}[cmd]()
    else:
        sys.exit(__doc__)
