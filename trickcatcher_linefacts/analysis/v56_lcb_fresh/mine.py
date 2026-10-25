"""v56 fresh LiveCodeBench cohort: manifest -> PUT generation -> public/hidden classification.

Data (downloaded, untrusted, never imported): out/v56_lcb_fresh/data/lcb/test{5,6}.jsonl from
HF livecodebench/code_generation_lite @ 0fe84c3912ea0c4d4a78037083943e8f0c4dd505.
Dataset rows and generated programs run only in the sandbox child of analysis/vibepass_feasibility.py
(unshare -rn, empty cwd, RLIMIT_AS, timeouts); that file is imported read-only, never edited.

  python3 -I -B analysis/v56_lcb_fresh/mine.py manifest   # metadata-only eligibility, newest 60, hashes
  python3 -I -B analysis/v56_lcb_fresh/mine.py generate   # 60 x 2 Qwen attempts (cached, 1 worker)
  python3 -I -B analysis/v56_lcb_fresh/mine.py evaluate   # public -> hidden classification, cohort.json

Endpoint: QWEN_BASE_URL / QWEN_MODEL from a private env file (never printed or stored here).
"""
import ast, hashlib, json, os, re, socket, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import vibepass_feasibility as vf  # noqa: E402  (sandbox, run_program, same)

OUT = os.path.join(ROOT, "out", "v56_lcb_fresh")
DATA = os.path.join(OUT, "data", "lcb")
TESTS = os.path.join(OUT, "tests")
CALLS = os.path.join(OUT, "calls")
LCB_REV = "0fe84c3912ea0c4d4a78037083943e8f0c4dd505"
LCB_FILES = ["test6.jsonl", "test5.jsonl"]
VIBEPASS = os.path.join(ROOT, "out", "heldout_vibepass", "data", "vibepass", "test.jsonl")
N_PROBLEMS, N_ATTEMPTS = 60, 2
GEN = dict(temperature=0.8, top_p=0.95, max_tokens=4096)   # seed = 1000 * problem rank + attempt
CALL_TIMEOUT = 1800
TRANSPORT_RETRIES = 3   # only when the connection itself failed (no HTTP status received); content is never retried
MODEL = "qwen2.5-coder-32b-instruct"   # registered served-model-name
MANIFEST_SHA256 = "7cfdf89f87d0bc5a59ecdb9f54ebb2e4e884c16b3a5ccae8224a232406a534c2"
JOURNAL = os.path.join(OUT, "journal.jsonl")

# LiveCodeBench lcb_runner/prompts/code_generation.py (functional problems with starter code)
SYSTEM = ("You are an expert Python programmer. You will be given a question (problem specification) and will "
          "generate a correct Python program that matches the specification and passes all tests.")
USER = ("### Question:\n{q}\n\n### Format: You will use the following starter code to write the solution to the "
        "problem and enclose your code within delimiters.\n```python\n{s}\n```\n\n"
        "### Answer: (use the provided format with backticks)\n\n")


def sha(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def dump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def starter_ok(starter, func):
    """Starter parses (with a stub body) and class Solution defines method `func`."""
    try:
        tree = ast.parse(starter.rstrip() + "\n        pass\n")
    except SyntaxError:
        return False
    return any(isinstance(c, ast.ClassDef) and c.name == "Solution" and
               any(isinstance(f, ast.FunctionDef) and f.name == func for f in c.body) for c in tree.body)


def load_manifest():
    path = os.path.join(OUT, "manifest.json")
    raw = open(path, "rb").read()
    if sha(raw) != MANIFEST_SHA256:
        raise SystemExit("manifest.json does not match the frozen hash")
    man = json.loads(raw)
    for p in man["problems"]:
        t = json.load(open(os.path.join(TESTS, p["question_id"] + ".json")))
        if sha(json.dumps([t["public"], t["private"]], sort_keys=True)) != p["tests_sha256"] or \
                sha(t["question_content"]) != p["statement_sha256"] or sha(t["starter_code"]) != p["starter_sha256"]:
            raise SystemExit(f"tests/statement hash mismatch for {p['question_id']}")
        p["_t"] = t
    return man


def journal(**kw):
    with open(JOURNAL, "a") as f:
        f.write(json.dumps(dict(kw, ts=time.time())) + "\n")
        f.flush(); os.fsync(f.fileno())


# ---------------------------------------------------------------- manifest (metadata/schema only)
def cmd_manifest():
    vp = [json.loads(l) for l in open(VIBEPASS)]
    vp_ids = {r["question_id"] for r in vp}
    vp_text = {norm(r["question_content"]) for r in vp if r.get("question_content")}
    os.makedirs(TESTS, exist_ok=True)
    rows, excluded = [], dict(vibepass_id=0, vibepass_text=0, not_leetcode=0, no_func=0, no_starter=0,
                              no_public=0, decode_fail=0, no_hidden=0)
    file_hash = {}
    for f in LCB_FILES:
        path = os.path.join(DATA, f)
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        file_hash[f] = h.hexdigest()
        for line in open(path):
            r = json.loads(line)
            qid = r["question_id"]
            if qid in vp_ids:
                excluded["vibepass_id"] += 1; continue
            if norm(r["question_content"]) in vp_text:
                excluded["vibepass_text"] += 1; continue
            if r["platform"] != "leetcode":
                excluded["not_leetcode"] += 1; continue
            func = json.loads(r.get("metadata") or "{}").get("func_name")
            starter = r.get("starter_code") or ""
            if not func:
                excluded["no_func"] += 1; continue
            if not starter_ok(starter, func):
                excluded["no_starter"] += 1; continue
            if not json.loads(r["public_test_cases"]):
                excluded["no_public"] += 1; continue
            rows.append((r["contest_date"], qid, f, line))
    rows.sort(key=lambda x: x[1])                  # question_id lexical tie-break (ascending) ...
    rows.sort(key=lambda x: x[0], reverse=True)    # ... under a stable contest_date-descending sort
    chosen = []
    for date, qid, f, line in rows:
        if len(chosen) == N_PROBLEMS:
            break
        res = vf.sandbox([vf.ME, "_decode", "row.json"], files={"row.json": line}, timeout=300)
        m = vf._marked(res)
        if m is None:   # infrastructure failure: stop instead of silently moving to the next problem
            raise SystemExit(f"decode failed for {qid}: {res['err'][-200:]}")
        if not m["private"]:
            excluded["no_hidden"] += 1; continue
        r = json.loads(line)
        m.update(lcb_file=f, question_title=r["question_title"], question_content=r["question_content"],
                 starter_code=r["starter_code"])
        dump(m, os.path.join(TESTS, qid + ".json"))
        chosen.append(dict(rank=len(chosen), question_id=qid, contest_date=date, lcb_file=f,
                           difficulty=m["difficulty"], func_name=m["func_name"], n_public=len(m["public"]),
                           n_private=len(m["private"]), statement_sha256=sha(r["question_content"]),
                           starter_sha256=sha(r["starter_code"]), tests_sha256=sha(json.dumps(
                               [m["public"], m["private"]], sort_keys=True))))
    man = dict(lcb_revision=LCB_REV, lcb_files=file_hash, vibepass_ids_excluded=len(vp_ids),
               eligible_pool=len(rows), excluded=excluded, n=len(chosen), problems=chosen,
               generation=dict(GEN, attempts=N_ATTEMPTS, system=SYSTEM, user_template=USER,
                               system_sha256=sha(SYSTEM), user_template_sha256=sha(USER)))
    dump(man, os.path.join(OUT, "manifest.json"))
    print(json.dumps(dict(eligible_pool=len(rows), chosen=len(chosen), excluded=excluded,
                          dates=[chosen[0]["contest_date"], chosen[-1]["contest_date"]] if chosen else None,
                          difficulty={d: sum(p["difficulty"] == d for p in chosen) for d in ("easy", "medium", "hard")})))


# ---------------------------------------------------------------- generation
HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"}


def _headers():
    return dict(HEADERS, Authorization="Bearer " + os.environ.get("OPENAI_API_KEY", "EMPTY"))


def check_model():
    """GET /models: the registered served name must be present; returns its metadata for the record."""
    url = os.environ["QWEN_BASE_URL"].rstrip("/") + "/models"
    with urllib.request.urlopen(urllib.request.Request(url, headers=_headers()), timeout=60) as resp:
        data = json.loads(resp.read())["data"]
    m = [x for x in data if x["id"] == MODEL]
    if not m:
        raise SystemExit(f"served models {[x['id'] for x in data]} lack registered {MODEL}")
    return {k: m[0].get(k) for k in ("id", "root", "max_model_len")}


def _chat(body, key):
    url = os.environ["QWEN_BASE_URL"].rstrip("/") + "/chat/completions"
    for attempt in range(TRANSPORT_RETRIES):
        journal(event="send", key=key, try_=attempt)
        try:
            resp = urllib.request.urlopen(urllib.request.Request(url, body, _headers()), timeout=CALL_TIMEOUT)
        except urllib.error.HTTPError as e:   # an HTTP status was received: final, never retried
            return dict(http_error=e.code, body=e.read()[:500].decode("utf-8", "replace")), attempt
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", None)
            # only DNS failure / refused connection prove the request never reached the server: retry those
            if isinstance(reason, (socket.gaierror, ConnectionRefusedError)):
                journal(event="connect_error", key=key, try_=attempt, error=type(reason).__name__)
                time.sleep(30 * (attempt + 1))
                continue
            return dict(unknown="urlerror_" + type(reason).__name__), attempt
        except (TimeoutError, OSError) as e:   # request may have been received: final unknown, never resent
            return dict(unknown=type(e).__name__), attempt
        try:   # status received: any failure while reading the body is final (generation may have happened)
            with resp:
                return json.loads(resp.read()), attempt
        except Exception as e:  # noqa
            return dict(read_error=type(e).__name__), attempt
    return dict(transport_error="connect_failed"), TRANSPORT_RETRIES


def extract_code(text):
    """Registered rule: the last fenced block that defines class Solution; else None."""
    blocks = [b for b in re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S) if "class Solution" in b]
    return blocks[-1] if blocks else None


def request_body(p, a):
    t = p["_t"]
    messages = [dict(role="system", content=SYSTEM),
                dict(role="user", content=USER.format(q=t["question_content"], s=t["starter_code"]))]
    return json.dumps(dict(model=MODEL, messages=messages, seed=1000 * p["rank"] + a, **GEN), sort_keys=True)


def cmd_generate():
    man = load_manifest()
    if os.environ.get("QWEN_MODEL") != MODEL:
        raise SystemExit("QWEN_MODEL is not the registered served name")
    served = check_model()
    os.makedirs(CALLS, exist_ok=True)
    sent = {json.loads(l)["key"] for l in open(JOURNAL)} if os.path.exists(JOURNAL) else set()
    for p in man["problems"]:
        for a in range(N_ATTEMPTS):
            key = f"{p['question_id']}_{a}"
            path = os.path.join(CALLS, key + ".json")
            seed = 1000 * p["rank"] + a
            body = request_body(p, a)
            if os.path.exists(path):   # any saved outcome (success or error) is final; verify it is ours
                rec = json.load(open(path))
                if rec["request_sha256"] != sha(body):
                    raise SystemExit(f"{key}: cached record was made with a different request")
                continue
            if key in sent:   # sent before but no record (crash mid-call): unknown, never resent
                dump(dict(question_id=p["question_id"], attempt=a, seed=seed, request_sha256=sha(body),
                          served=None, response=dict(unknown="sent_without_record")), path)
                print(p["rank"], key, "unknown (sent without record)", flush=True)
                continue
            t0 = time.time()
            resp, tries = _chat(body.encode(), key)
            rec = dict(question_id=p["question_id"], attempt=a, seed=seed, request_sha256=sha(body), model=MODEL,
                       gen=GEN, served=served, seconds=round(time.time() - t0, 1), transport_retries=tries,
                       response=resp)
            dump(rec, path)
            journal(event="saved", key=key)
            ok = "choices" in resp
            print(p["rank"], p["question_id"], a, "ok" if ok else {k: v for k, v in resp.items() if k != "body"},
                  rec["seconds"], flush=True)


# ---------------------------------------------------------------- evaluation
def _exec(code, func, inp, timeout):
    job = json.dumps(dict(code=code, func=func, input=inp))
    r = vf.sandbox([vf.ME, "_fexec", "job.json"], files={"job.json": job}, timeout=timeout)
    if r["tle"]:
        return dict(status="tle")
    m = vf._marked(r)
    if m is None:   # child died without a result marker: harness/ambiguous, never counted as a PUT exception
        return dict(status="harness")
    if "err" in m:
        return dict(status="exc")
    return dict(status="ok", out=m["out"])


def _one(code, func, tc):
    o = _exec(code, func, tc["input"], vf.TIMEOUT)
    if o["status"] == "tle":   # same policy as vibepass_feasibility.run_program: one retry at 60 s
        o = _exec(code, func, tc["input"], vf.RETRY_TIMEOUT)
    if o["status"] == "ok":
        return "pass" if vf.same("leetcode", o["out"], tc["output"]) else "wrong"
    return o["status"]   # exc | tle | harness


def run_tests(code, func, tests, stop_on_fail):
    if stop_on_fail:
        res = []
        for tc in tests:
            res.append(_one(code, func, tc))
            if res[-1] != "pass":
                break
        return res
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(vf.WORKERS) as ex:
        return list(ex.map(lambda tc: _one(code, func, tc), tests))


def cmd_evaluate():
    man = load_manifest()
    rows, cohort = [], []
    for p in man["problems"]:
        t = p["_t"]
        picked = None
        for a in range(N_ATTEMPTS):
            rec = json.load(open(os.path.join(CALLS, f"{p['question_id']}_{a}.json")))
            if rec["request_sha256"] != sha(request_body(p, a)):
                raise SystemExit(f"{p['question_id']}_{a}: record request differs from the frozen prompt/seed/config")
            resp = rec["response"]
            row = dict(question_id=p["question_id"], attempt=a)
            if "choices" not in resp:
                row.update(status="no_response", detail={k: v for k, v in resp.items() if k != "body"})
            elif rec.get("model") != MODEL:
                raise SystemExit(f"{p['question_id']}_{a}: record model {rec.get('model')} != {MODEL}")
            else:
                choice = resp["choices"][0]
                code = extract_code(choice["message"]["content"] or "")
                row.update(finish=choice.get("finish_reason"), usage=resp.get("usage"))
                if code is None:
                    row["status"] = "no_code"
                else:
                    pub = run_tests(code, p["func_name"], t["public"], stop_on_fail=True)
                    if pub[-1] == "harness":
                        row.update(status="harness_error", phase="public")
                    elif pub[-1] != "pass":
                        row.update(status="public_fail", detail=pub[-1])
                    else:
                        hid = run_tests(code, p["func_name"], t["private"], stop_on_fail=False)
                        kinds = {k: hid.count(k) for k in ("wrong", "exc", "tle", "harness")}
                        if kinds["wrong"] + kinds["exc"] > 0:
                            row["status"] = "hidden_fail"     # unambiguous wrong value / PUT exception
                        elif kinds["harness"] > 0:
                            row["status"] = "harness_error"   # ambiguous: never retained
                        elif kinds["tle"] > 0:
                            row["status"] = "timeout_only"
                        else:
                            row["status"] = "hidden_pass"
                        row.update(hidden=kinds, n_hidden=len(hid), code_sha256=sha(code))
                        if row["status"] == "hidden_fail" and picked is None:
                            picked = dict(question_id=p["question_id"], attempt=a, rank=p["rank"],
                                          contest_date=p["contest_date"], difficulty=p["difficulty"],
                                          func_name=p["func_name"], buggy_solution=code, code_sha256=sha(code),
                                          hidden=kinds, n_hidden=len(hid))
            rows.append(row)
            print(p["rank"], p["question_id"], a, row["status"], row.get("hidden", ""), flush=True)
        if picked:
            cohort.append(picked)
    from collections import Counter
    summary = dict(status=dict(Counter(r["status"] for r in rows)), cohort=len(cohort),
                   cohort_difficulty=dict(Counter(c["difficulty"] for c in cohort)))
    dump(dict(summary=summary, rows=rows), os.path.join(OUT, "evaluation.json"))
    dump(cohort, os.path.join(OUT, "cohort.json"))
    print(json.dumps(summary))


if __name__ == "__main__":
    {"manifest": cmd_manifest, "generate": cmd_generate, "evaluate": cmd_evaluate}[sys.argv[1]]()
