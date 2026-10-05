"""m9: the upstream Advanced docstring prompt, verbatim, plus one extra Part 1 item (item 3) after "2. Robustness Omissions".

arms (identical script, call, parsing; only the inserted item differs):
  adv_rerun = nothing inserted (A/A re-run of Advanced Doc through this script)
  concept   = item 3 lists the shared bug-concept vocabulary C1-C8 (m3's facet definitions)
  placebo   = item 3 lists m3's eight bug-irrelevant facets P1-P8 (same header, format, count, ~length)

Faithful to Advanced_Docstring_Generation.ipynb (cell 20): prompt = PromptFormatter().apply_format_summarize(record,
'chatgpt', strategy='generation', formatting='comment', ignore_feature='full', project_name=bug_id, advanced_analysis=True,
is_base=True, base_cot=True, corrected_code=True); call = openai_client.chat.completions.create(model="gpt-4.1",
messages=[user prompt], temperature=0) with no max_tokens, through run/gemini_shim.py (gemini-2.5-flash, Vertex,
thinking off); docstring = the notebook's own parsing code (cell 16, exec'd verbatim) on completion.strip().
One call per method and arm, sequential (concurrency 1); the shim backs off on 429.

usage (container):  python3 m9_concept_advanced/m9.py prompts               leak check + sizes -> out/prompts_check.txt (no LLM)
                    python3 m9_concept_advanced/m9.py gen <arm> [idx ...]   LLM; out/docs_<arm>.jsonl cache, out/llm_calls.jsonl
                    python3 m9_concept_advanced/m9.py selftest
host or container:  python3 m9_concept_advanced/m9.py cost                  spend ledger (logged docstring calls + test-gen estimate)
"""
import glob, hashlib, importlib.util, json, os, re, sys, time

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run"]
D = f"{REPO}/m9_concept_advanced"
OUT = f"{D}/out"
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
NB = f"{REPO}/Advanced_Docstring_Generation.ipynb"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m9_{}.jsonl"
RQ1 = REPO + "/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
ARMS = ("adv_rerun", "concept", "placebo")
# Vertex AI list price, gemini-2.5-flash, USD per token (thinking is off, so no thought tokens)
PRICE_IN, PRICE_OUT = 0.30e-6, 2.50e-6
CAP = 8.0          # hard cap for all m9 Vertex spend (raised from 5.0: user approved directly, 2026-10-05)
DOC_BUDGET = 3.9   # docstring calls stop above this; the rest of the cap is for the three test-generation runs (~$0.4 each)
# (raised from 2.5 to 3.5, then 3.9 during phase B, total cap unchanged: like the baseline, Lang_36/Lang_3/Lang_44 run into 65,536-token repetition loops, ~$0.165 each)

_s = importlib.util.spec_from_file_location("m3spec", f"{REPO}/m3_concept_spec/spec.py")
M3 = importlib.util.module_from_spec(_s); _s.loader.exec_module(M3)  # reuse m3's facet names + definitions
ANCHOR = "necessary data sanitization or escaping.\n"  # end of Part 1 item 2 in ADVANCED_SUMMARIZATION_POST_FIX_BASE
HEAD = ('3.  **Checklist Review:** Go through each of the following aspects for the given code. For each aspect, state your '
        'finding, or explicitly state "No issues found." if there is none.\n')
ITEM = {"adv_rerun": ""}
for arm, m3arm in (("concept", "spec"), ("placebo", "placebo")):
    ITEM[arm] = HEAD + "".join(f"    - {k} {name}: {d}.\n" for k, name, d in M3.FACETS[m3arm][1:])  # [0] is C0 core logic


def base_prompt(record):
    """the notebook's prompt (cell 20 arguments; the restored formatter ignores is_base/base_cot/corrected_code, see its comment)."""
    from utils.prompt_formats.new_prompt_formatter import PromptFormatter
    return PromptFormatter().apply_format_summarize(record, "chatgpt", strategy="generation", formatting="comment",
                                                    ignore_feature="full", project_name=record["extra:project_name"],
                                                    advanced_analysis=True, is_base=True, base_cot=True, corrected_code=True)


def build_prompt(record, arm):
    is_public, p = base_prompt(record)
    assert p.count(ANCHOR) == 1
    return is_public, p.replace(ANCHOR, ANCHOR + ITEM[arm])


_NB_PARSE = None


def nb_parse(completion):
    """Advanced_Docstring_Generation.ipynb cell 16 (same code as in the cell 20 loop), executed verbatim."""
    global _NB_PARSE
    if _NB_PARSE is None:
        cells = [c for c in json.load(open(NB))["cells"] if c["cell_type"] == "code"]
        _NB_PARSE = "".join(cells[16]["source"])
        loop = "".join(cells[20]["source"])
        ws = lambda s: re.sub(r"\s+", " ", s).strip()
        assert "docstring_blocks = re.findall" in _NB_PARSE and all(
            ws(l).replace("example_", "") in ws(loop) for l in _NB_PARSE.splitlines() if l.strip()), "notebook parsing changed"
    ns = {"re": re, "generated_docstring": completion, "example_new_inst": {}, "example_instance": {}}
    exec(_NB_PARSE, ns)
    return ns["example_instance"]["generated_docstring"]


# ------------------------------------------------------------------ leak check
def fix_info(record):
    """offline only: fixed-side lines of the patch (the '-' side: the d4j2 diffs run fixed -> buggy) and trigger test names."""
    fi = json.load(open(f"{REPO}/data/d4j2_fix_info/{record['extra:project_name'].replace('_buggy', '')}/buggy_fix_info.json"))
    fixed = {l[1:].strip() for c in fi["fixing_changes"] for l in c["diff"].splitlines()
             if l.startswith("-") and not l.startswith("---") and len(l[1:].strip()) >= 12}
    trig = {t["test_function"] for t in fi["trigger_tests"]} | {t["test_class"].split(".")[-1] for t in fi["trigger_tests"]}
    return fixed, trig


def prompts():
    records = [json.loads(l) for l in open(SRC)]
    norm = lambda s: re.sub(r"\s+", " ", s)
    lines, sizes = [], {a: [] for a in ARMS}
    for a in ARMS[1:]:
        lines.append(f"inserted item ({a}): {len(ITEM[a])} chars, {len(ITEM[a].split())} words, "
                     f"{ITEM[a].count(chr(10) + '    - ')} facets\n{ITEM[a]}")
    leaks, inherited = [], []
    for i, r in enumerate(records):
        _, base = base_prompt(r)
        fixed, trig = fix_info(r)
        for a in ARMS:
            _, p = build_prompt(r, a)
            assert p.replace(ITEM[a], "", 1) == base if ITEM[a] else p == base  # only the static item differs
            sizes[a].append(len(p))
            for kind, items in (("fixed line", fixed), ("trigger test", trig)):
                for x in items:
                    pat = norm(x) if kind == "fixed line" else r"\b" + re.escape(x) + r"\b"
                    hit = (pat in norm(p)) if kind == "fixed line" else re.search(pat, p)
                    in_base = (pat in norm(base)) if kind == "fixed line" else re.search(pat, base)
                    if hit and not in_base:
                        leaks.append((i, a, kind, x))
                    elif hit and a == "adv_rerun":
                        inherited.append((i, r["extra:project_name"], kind, x))
    for a in ARMS:
        s = sizes[a]
        lines.append(f"{a}: {len(s)} prompts, chars mean {sum(s) / len(s):.0f} min {min(s)} max {max(s)}, total {sum(s)} "
                     f"(~{sum(s) / 3.5:.0f} tokens at 3.5 chars/token)")
    lines.append(f"leaks introduced by m9 (fixed-side patch line or trigger test name in an m9 prompt but not in the upstream "
                 f"prompt): {len(leaks)} {leaks[:10]}")
    lines.append(f"already in the upstream Advanced prompt (inherited, same in the Advanced Doc baseline; a fixed-side line "
                 f"identical to an unchanged buggy-class line, or a test-like name in the class context): {len(inherited)} {inherited}")
    lines.append("item text is static: it contains no per-method content, so it cannot carry the patch, fixed version, trigger "
                 "tests or fix metadata")
    assert not leaks
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/prompts_check.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ------------------------------------------------------------------ cost ledger
def calls():
    p = f"{OUT}/llm_calls.jsonl"
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def cost(quiet=False):
    """exact spend of the logged docstring calls + an estimate for the pipeline's test-generation calls (run/gemini_shim.py
    does not expose token counts): chars of prompt + completion of every m9 rq1 file, at the chars/token ratio measured on
    the logged docstring calls (3.5 if none yet)."""
    cs = calls()
    doc = sum(c["usd"] for c in cs)
    ok = [c for c in cs if c.get("in_tok")]
    cpt = sum(c["in_chars"] for c in ok) / sum(c["in_tok"] for c in ok) if ok else 3.5
    tg = {}
    # _err_msg_ copies (the evaluation) and _part<k>/_redo<k> files (eval_parts.py record subsets): no LLM call
    for f in [f for f in glob.glob(RQ1.format("m9_*")) if "_err_msg_" not in f and not re.search(r"_(part|redo)\d+_with", f)]:
        rs = [json.loads(l) for l in open(f)]
        # digits are one token each (runaway "000..." texts dominate; count_tokens on the baseline test generation:
        # out/count_tokens_baseline_testgen.json); other chars at <= 4.0 chars/token (4.0-4.3 measured there)
        tok = lambda t: sum(ch.isdigit() for ch in t) + sum(not ch.isdigit() for ch in t) / min(cpt, 4.0)
        tg[os.path.basename(f)] = sum(tok(r["content"]) * PRICE_IN + tok(r.get("completion") or "") * PRICE_OUT for r in rs)
    total = doc + sum(tg.values())
    if not quiet:
        by = {}
        for c in cs:
            k = by.setdefault(c["arm"], [0, 0, 0.0])
            k[0] += 1; k[1] += bool(c.get("in_tok")); k[2] += c["usd"]
        for a, (n, n_ok, usd) in sorted(by.items()):
            print(f"docstring {a}: {n} API attempts ({n_ok} billed responses) ${usd:.3f}")
        for f, usd in sorted(tg.items()):
            print(f"test generation (estimate) {f}: ${usd:.3f}")
        print(f"TOTAL ${total:.3f} of cap ${CAP}")
    return total


# ------------------------------------------------------------------ generation
def gen(arm, idx):
    from gemini_shim import GeminiChat
    assert arm in ARMS
    openai_client = GeminiChat()
    log_path = f"{OUT}/llm_calls.jsonl"
    cur = {}
    raw = openai_client.client.models.generate_content

    def logged(**kw):  # every API attempt, with the token counts the shim drops
        t0, err = time.time(), None
        try:
            r = raw(**kw)
            u = r.usage_metadata
            it, ot, tt = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
            entry = {"in_tok": it, "out_tok": ot, "thought_tok": tt, "usd": it * PRICE_IN + (ot + tt) * PRICE_OUT}
        except Exception as ex:  # 429 etc.: not billed
            err, entry = ex, {"error": repr(ex)[:200], "usd": 0.0}
        entry.update(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), secs=round(time.time() - t0, 1), **cur)
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        if err:
            raise err
        return r

    openai_client.client.models.generate_content = logged
    records = [json.loads(l) for l in open(SRC)]
    path = f"{OUT}/docs_{arm}.jsonl"
    done = {r["idx"]: r for r in map(json.loads, open(path))} if os.path.exists(path) else {}
    sel = idx or list(range(len(records)))
    os.makedirs(OUT, exist_ok=True)
    for i in [i for i in sel if i not in done]:
        spent = sum(c["usd"] for c in calls())
        assert spent < DOC_BUDGET and cost(quiet=True) < CAP, f"budget reached: docstring calls ${spent:.3f}"
        instance = records[i]
        bug_id = instance["extra:project_name"]
        is_public, prompt = build_prompt(instance, arm)
        cur.update(arm=arm, idx=i, in_chars=len(prompt))
        for attempt in range(10):  # the notebook retries failed calls (up to 1000 times); the shim already retries 8x
            try:
                chat_completion = openai_client.chat.completions.create(
                    model="gpt-4.1", messages=[{"role": "user", "content": prompt}], temperature=0)
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} for method {bug_id} failed: {e}", flush=True)
                if attempt == 9:
                    raise
                time.sleep(60)
        generated_docstring = chat_completion.choices[0].message.content.strip()
        rec = {"idx": i, "id": bug_id, "method_signature": instance["source:source_method_signature"], "arm": arm,
               "is_public": "1" if is_public else "0", "prompt": prompt, "completion": generated_docstring,
               "generated_docstring": nb_parse(generated_docstring)}
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        done[i] = rec
        print(i, bug_id, len(generated_docstring), "chars", f"${sum(c['usd'] for c in calls()):.3f}", flush=True)
    out = DOC_OUT.format(arm + ("_smoke" if idx else ""))
    with open(out, "w") as f:  # source records + generated_docstring (the notebook's file) + the full completion
        for i in sel:
            f.write(json.dumps({**records[i], "generated_docstring": done[i]["generated_docstring"],
                                "m9_completion": done[i]["completion"]}) + "\n")
    print("wrote", out)
    cost()


def selftest():
    assert set(ITEM) == set(ARMS) and ITEM["adv_rerun"] == ""
    for a in ARMS[1:]:
        assert ITEM[a].startswith(HEAD) and ITEM[a].count("\n    - ") == 8 and ITEM[a].endswith(".\n")
    assert "C1 null input" in ITEM["concept"] and "P5 logging" in ITEM["placebo"] and "C1" not in ITEM["placebo"]
    r = 0.8 < len(ITEM["concept"]) / len(ITEM["placebo"]) < 1.25
    assert r, (len(ITEM["concept"]), len(ITEM["placebo"]))
    c = "## Part 1\n...\n```java\npublic int f() { return 1; }\n```\n**Part 3**\n/**\n * Returns one.\n */\nmore"
    assert nb_parse(c) == "\n/**\n * Returns one.\n */\n"
    assert nb_parse("no blocks") == "no blocks" and nb_parse("x ```java\nint a;\n``` y") == "\nint a;\n"
    assert nb_parse("/** a */ then /** b */") == "\n/** b */\n"  # last /** */ block, as in the notebook
    print("selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "gen":
        gen(sys.argv[2], [int(i) for i in sys.argv[3:]])
    else:
        {"prompts": prompts, "selftest": selftest, "cost": cost}[cmd]()
