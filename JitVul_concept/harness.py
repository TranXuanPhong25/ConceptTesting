#!/usr/bin/env python3
"""JitVul + concept facts. Additive wrapper: the authors' code (vendor/JitVul) and the official
ConceptCoder annotator (../ConceptCoder_org) are imported unmodified.

  check                      dataset + annotator + get_callees-fix sanity
  annotate                   offline: annotate targets + callees, render per-arm blocks -> out/blocks.jsonl
  ide                        offline: cppcheck + flawfinder warnings -> out/ide_blocks.jsonl (ide arm)
  verify                     re-render every cached prompt and compare with its stored sha1
  run ARM [--smoke|--limit N]  LLM calls, cached per (arm, pair, side) in out/responses/ARM.jsonl
  show ARM [--pair I --side S] print one rendered prompt
"""
import argparse, hashlib, json, os, random, re, sys, threading, time, warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
VENDOR = HERE / "vendor" / "JitVul"
DATA = VENDOR / "data" / "final_benchmark.jsonl"
ANN = HERE / "cache" / "annotations.jsonl"
OUT = HERE / "out"
BLOCKS = OUT / "blocks.jsonl"
ARMS = ("base", "concept", "placebo", "callee_code", "ide")  # ide last: added after the full run of the first four started
SIDES = ("vulnerable", "non_vulnerable")  # vulnerable = intro commit, non_vulnerable = fix commit
SEED = 20251007
MAX_CALLEES = 15         # callee lines listed per block
MAX_LINE_REFS = 6        # line numbers listed per label for the target function
SMOKE_N = 5
PRICE_IN, PRICE_OUT = 0.30e-6, 2.50e-6  # USD/token, Gemini 2.5 Flash on Vertex (output price also covers thoughts)

warnings.filterwarnings("ignore", category=FutureWarning)  # tree_sitter Language(path, name) deprecation
sys.path[:0] = [str(VENDOR / "code" / "evaluation_pipeline"), str(REPO / "ConceptCoder_org" / "code" / "design_concept"), str(REPO)]


def read_jsonl(path):
    return [json.loads(l) for l in open(path)] if Path(path).exists() else []


def sha1(s):
    return hashlib.sha1(s.encode()).hexdigest()


# ---------------------------------------------------------------- data

def strip_fence(body):
    # Dataset artifact: 875/879 non_vulnerable bodies start with a leftover markdown-fence language
    # line ("c"/"cpp"), 0/879 vulnerable ones do -> a label leak. Every arm sees the stripped body.
    first, _, rest = body.partition("\n")
    return rest if first.strip().lower() in ("c", "cpp", "c++") else body


def load_pairs():
    return read_jsonl(DATA)


_NAME = re.compile(r"([A-Za-z_][\w:~]*)\s*\(")


def target_and_callees(pair, side):
    """Direct callees of the target function, deduplicated, in call order.

    Fixes the released tools.get_callees, which reads session.caller_graph and so returns callers.
    In the dataset the inner key of {side}_callee_graph is also named "callers", but it lists callees.
    """
    body = strip_fence(pair[f"{side}_function_body"])
    graph = pair[f"{side}_callee_graph"]
    head = body[: body.find("{")] if "{" in body else body[:300]
    m = _NAME.findall(head)
    name = m[0].split("::")[-1] if m else None
    target = name if name in graph else next(iter(graph), name)  # graph's first key is the target
    names = dict.fromkeys(graph.get(target, {}).get("callers", []))
    names.pop(target, None)
    return target, list(names)


def source_callees(pair, side):
    target, names = target_and_callees(pair, side)
    bodies = pair[f"{side}_function_bodies"]
    return target, [n for n in names if bodies.get(n)]


# ---------------------------------------------------------------- annotation (official ConceptCoder VD annotator)

def load_annotator():
    import design_and_annotate_VD_concepts as cc  # ConceptCoder_org, unmodified (tree_sitter_languages, cpp grammar)
    from conceptcoder_bridge.paper_labels import PAPER_LABELS
    labels = dict(zip(cc.props, PAPER_LABELS))  # 7 paper labels; zip drops the 8th prop, if_statement
    assert len(labels) == 7 and "if_statement" not in labels

    def annotate(text):
        props = cc.bfs(text, cc.parser)
        out = {}
        for key, label in labels.items():  # same line projection as the official main(), 1-based here
            lines = sorted({li + 1 for x in props[key] for li in x["lines"]})
            if lines:
                out[label] = lines
        return out

    return annotate, list(labels.values())


def facts(labels, order, line_refs):
    parts = []
    for lab in order:
        ls = labels.get(lab)
        if not ls:
            continue
        if line_refs:
            more = f" (+{len(ls) - MAX_LINE_REFS})" if len(ls) > MAX_LINE_REFS else ""
            parts.append(f"{lab} " + ",".join(f"L{x}" for x in ls[:MAX_LINE_REFS]) + more)
        else:
            parts.append(f"{lab} x{len(ls)}")
    return "; ".join(parts) or "no labelled statements"


HEADER = "Concept facts (static analysis of the function above and of the functions it calls):"


def render(rec, order):
    out = [HEADER, f"- this function `{rec['target']}`: {facts(rec['t_labels'], order, True)}"]
    out += [f"- callee `{n}`: {facts(l, order, False)}" for n, l in rec["callees"]]
    if not rec["callees"]:
        out.append("- callees: no callee source available")
    if rec["more"]:
        out.append(f"- (+{rec['more']} more callees not listed)")
    return "\n".join(out)


def placebo_rec(rec, donor, n_lines):
    """Same names and line count as the real block; label facts taken from the donor pair."""
    t = {lab: sorted({(x - 1) % n_lines + 1 for x in ls}) for lab, ls in donor["t_labels"].items()}
    dl = [l for _, l in donor["callees"]]
    cal = [(n, dl[j % len(dl)] if dl else {}) for j, (n, _) in enumerate(rec["callees"])]
    return {"target": rec["target"], "t_labels": t, "callees": cal, "more": rec["more"]}


def derangement(pairs, size):
    """Donor per pair: fixed seed, never itself or the same CVE, among pairs of similar callee count and block length."""
    rng = random.Random(SEED)
    order = sorted(range(len(pairs)), key=lambda i: (size(i), rng.random()))
    chunks = [order[k:k + 8] for k in range(0, len(order), 8)]
    if len(chunks[-1]) < 2:
        chunks[-2] += chunks.pop()
    donor, pending = {}, []
    for ch in chunks:
        ch = pending + ch  # a chunk dominated by one CVE has no valid derangement: merge it into the next
        perms = (rng.sample(ch, len(ch)) for _ in range(2000))
        perm = next((q for q in perms if all(a != b and pairs[a]["cve"] != pairs[b]["cve"] for a, b in zip(ch, q))), None)
        pending = ch if perm is None else []
        if perm:
            donor.update(zip(ch, perm))
    if pending:
        raise RuntimeError(f"no derangement for the last chunk {pending}")
    # donor side is a coin flip per pair, so the placebo carries no vulnerable/fixed signal
    flip = {i: rng.random() < 0.5 for i in range(len(pairs))}
    return donor, flip


def callee_code_block(pair, side, names, budget):
    head = "Source of the functions called by the function above (truncated):"
    if not names:
        return head + "\n(no callee source available)"
    bodies = pair[f"{side}_function_bodies"]
    code = "\n".join(f"// callee {n}\n{bodies[n]}" for n in names)
    return head + "\n```c\n" + code[: max(0, budget - len(head) - 10)] + "\n```"


def cmd_annotate(_):
    pairs = load_pairs()
    annotate, order = load_annotator()
    cache = {r["h"]: r for r in read_jsonl(ANN)}
    texts = {}
    for p in pairs:
        for s in SIDES:
            for t in [strip_fence(p[f"{s}_function_body"])] + [p[f"{s}_function_bodies"][n] for n in source_callees(p, s)[1]]:
                texts[sha1(t)] = t
    todo = [h for h in texts if h not in cache]
    print(f"annotating {len(todo)} new / {len(texts)} unique functions")
    ANN.parent.mkdir(exist_ok=True)
    with open(ANN, "a") as f:
        for k, h in enumerate(todo, 1):
            try:
                r = {"h": h, "labels": annotate(texts[h])}
            except Exception as e:  # malformed code the official visitor cannot handle
                r = {"h": h, "labels": {}, "err": f"{type(e).__name__}: {e}"[:200]}
            cache[h] = r
            f.write(json.dumps(r) + "\n")
            if k % 2000 == 0:
                print(f"  {k}/{len(todo)}")
    print(f"annotator errors: {sum('err' in cache[h] for h in texts)}")

    recs, src = {}, {}
    for i, p in enumerate(pairs):
        for s in SIDES:
            target, names = source_callees(p, s)
            bodies = p[f"{s}_function_bodies"]
            src[i, s] = names
            recs[i, s] = {"target": target or "?",
                          "t_labels": cache[sha1(strip_fence(p[f"{s}_function_body"]))]["labels"],
                          "callees": [(n, cache[sha1(bodies[n])]["labels"]) for n in names[:MAX_CALLEES]],
                          "more": max(0, len(names) - MAX_CALLEES)}
    donor, flip = derangement(pairs, lambda i: (sum(len(recs[i, s]["callees"]) for s in SIDES),
                                                sum(len(render(recs[i, s], order)) for s in SIDES)))
    assert all(donor[i] != i and pairs[donor[i]]["cve"] != pairs[i]["cve"] for i in donor)

    OUT.mkdir(exist_ok=True)
    gap = []
    with open(BLOCKS, "w") as f:
        for i, p in enumerate(pairs):
            same = strip_fence(p["vulnerable_function_body"]).strip() == strip_fence(p["non_vulnerable_function_body"]).strip()
            for s in SIDES:
                d, ds = donor[i], (SIDES[1 - SIDES.index(s)] if flip[i] else s)
                n_lines = strip_fence(p[f"{s}_function_body"]).count("\n") + 1
                concept = render(recs[i, s], order)
                placebo = render(placebo_rec(recs[i, s], recs[d, ds], n_lines), order)
                gap.append(len(placebo) - len(concept))
                f.write(json.dumps({"pair": i, "side": s, "n_callees": len(target_and_callees(p, s)[1]),
                                    "n_src_callees": len(src[i, s]), "same_body": same, "donor": d, "donor_side": ds,
                                    "concept": concept, "placebo": placebo,
                                    "callee_code": callee_code_block(p, s, src[i, s], len(concept))}) + "\n")
    n = len(pairs)
    print(f"pairs {n}; with callee source on both sides {sum(bool(src[i, 'vulnerable']) and bool(src[i, 'non_vulnerable']) for i in range(n))}; "
          f"same target body {sum(1 for r in read_jsonl(BLOCKS) if r['same_body']) // 2}")
    print(f"placebo: derangement ok (no self, no same-CVE donor); donor side flipped for {sum(flip.values())}/{n}; "
          f"placebo-concept length gap chars mean {sum(gap) / len(gap):+.1f}, mean |gap| {sum(map(abs, gap)) / len(gap):.1f}")
    print(f"wrote {BLOCKS}")


# ---------------------------------------------------------------- ide arm: off-the-shelf analyzer warnings

IDE_BLOCKS = OUT / "ide_blocks.jsonl"
IDE_CACHE = HERE / "cache" / "ide.jsonl"
IDE_HEADER = "Static analyzer warnings (flawfinder and cppcheck on the function above and on the functions it calls):"
CPPCHECK_ARGS = ["--quiet", "--enable=warning,style,portability,performance",
                 "--template={file}|{line}|{severity}|{id}|{message}"]
# cppcheck could not analyse the fragment (recorded as a failure, not a finding)
CPPCHECK_FAIL = {"syntaxError", "unknownMacro", "internalAstError", "internalError", "preprocessorErrorDirective",
                 "cppcheckError", "toomanyconfigs", "normalCheckLevelMaxBranches", "checkersReport",
                 "missingInclude", "missingIncludeSystem"}
# artifacts of analysing a lone function: implicit int from the cut signature / the dataset's dropped return type
CPPCHECK_DROP = {"returnImplicitInt", "unusedFunction", "unusedStructMember"}
CPPCHECK_RANK = {"error": 5, "warning": 4, "portability": 2, "performance": 2, "style": 1}
FLAWFINDER_RANK = {5: 5, 4: 5, 3: 4, 2: 3, 1: 2, 0: 1}  # flawfinder risk level -> same scale
CPP_EXT = (".cc", ".cpp", ".cxx", ".hpp", ".hh")


def ide_inputs(pair, side):
    """[(label, name, analyzer text, prompt-line offset)] for the target and the concept block's callees."""
    body = strip_fence(pair[f"{side}_function_body"])
    m = _NAME.search(body[: body.find("{")] if "{" in body else body[:300])
    # The dataset drops the return-type line from 327/879 vulnerable bodies and from no patched body. Both sides are
    # analysed from the function name on, so implicit-int warnings cannot leak the label.
    cut = m.start() if m else 0
    target, names = source_callees(pair, side)
    bodies = pair[f"{side}_function_bodies"]
    return ([("this function", target or "?", body[cut:], body[:cut].count("\n"))]
            + [("callee", n, f"void {n}() " + bodies[n], 0) for n in names[:MAX_CALLEES]])  # callee bodies lack a signature


def short(msg, n=110):
    msg = " ".join(msg.split())
    msg = msg.split(". ")[0].rstrip(".")
    return msg if len(msg) <= n else msg[: n - 3] + "..."


def run_analyzers(files):
    """{key: (ext, text)} -> {key: {"findings": [[line, tool, rule, rank, msg]], "cppcheck_fail": [ids]}}"""
    import csv, subprocess, tempfile
    tools = Path(sys.executable).parent
    res = {k: {"findings": [], "cppcheck_fail": []} for k in files}
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "src"
        src.mkdir()
        for k, (ext, text) in files.items():
            (src / f"{k}{ext}").write_text(text)
        (Path(d) / "files.txt").write_text("\n".join(str(p) for p in sorted(src.iterdir())))
        r = subprocess.run([str(tools / "cppcheck"), *CPPCHECK_ARGS, f"-j{os.cpu_count() or 2}",
                            f"--file-list={Path(d) / 'files.txt'}"], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"cppcheck failed: {r.stderr[-500:]}")
        for line in r.stderr.splitlines():
            parts = line.split("|", 4)
            if len(parts) != 5 or not parts[1].isdigit():
                continue
            f, ln, sev, rid, msg = parts
            k = Path(f).stem
            if k not in res or rid in CPPCHECK_DROP or sev == "information":
                continue
            if rid in CPPCHECK_FAIL:
                res[k]["cppcheck_fail"].append(rid)
            else:
                res[k]["findings"].append([int(ln), "cppcheck", rid, CPPCHECK_RANK.get(sev, 1), short(msg)])
        r = subprocess.run([str(tools / "flawfinder"), "--csv", "--quiet", str(src)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"flawfinder failed: {r.stderr[-500:]}")
        for row in csv.DictReader(r.stdout.splitlines()):
            k = Path(row["File"]).stem
            if k in res:
                res[k]["findings"].append([int(row["Line"]), "flawfinder", f"{row['Category']}/{row['Name']}",
                                           FLAWFINDER_RANK.get(int(row["Level"]), 1), short(row["Warning"])])
    for v in res.values():
        v["findings"].sort()
    return res


def ide_entries(findings, offset):
    """Group one function's findings by (tool, rule); best rank first, then first line."""
    groups = {}
    for ln, tool, rule, rank, msg in findings:
        g = groups.setdefault((tool, rule), {"lines": [], "rank": rank, "msg": msg})
        g["lines"].append(ln + offset)
        g["rank"] = max(g["rank"], rank)
    out = []
    for (tool, rule), g in groups.items():
        ls = sorted(set(g["lines"]))
        refs = ",".join(f"L{x}" for x in ls[:3]) + (f" (+{len(ls) - 3})" if len(ls) > 3 else "")
        out.append((g["rank"], ls[0], f"{refs} {tool} {rule}: {g['msg']}"))
    return [(rank, text) for rank, _, text in sorted(out, key=lambda e: (-e[0], e[1]))]


def ide_block(funcs, more, budget):
    """Concept-block shape: one line per function. Warnings are added best-rank first while the block fits `budget`
    (the concept block's length); the top warning is kept even if it alone exceeds the budget."""
    keep = [0] * len(funcs)

    def text():
        out = [IDE_HEADER]
        for (label, name, ents), k in zip(funcs, keep):
            shown = [t for _, t in ents[:k]]
            if k < len(ents):
                shown.append(f"+{len(ents) - k} more warning(s) not shown" if k else f"{len(ents)} warning(s) not shown")
            out.append(f"- {label} `{name}`: " + ("; ".join(shown) or "no warnings"))
        if len(funcs) == 1:
            out.append("- callees: no callee source available")
        if more:
            out.append(f"- (+{more} more callees not listed)")
        return "\n".join(out)

    for _, fi, ei in sorted((-r, fi, ei) for fi, f in enumerate(funcs) for ei, (r, _) in enumerate(f[2])):
        if ei == keep[fi]:
            keep[fi] += 1
            if len(text()) > budget and sum(keep) > 1:  # the single best warning is always shown
                keep[fi] -= 1
    return text(), sum(keep)


def cmd_ide(_):
    pairs, blocks = load_pairs(), load_blocks()
    cache = {r["h"]: r for r in read_jsonl(IDE_CACHE)}
    items, files = {}, {}
    for i, p in enumerate(pairs):
        ext = ".cpp" if os.path.splitext(p["file_name"])[1] in CPP_EXT else ".c"
        for s in SIDES:
            items[i, s] = []
            for label, name, text, off in ide_inputs(p, s):
                h = sha1(ext + "\n" + text)
                files[h] = (ext, text)
                items[i, s].append((label, name, h, off))
    todo = {h: v for h, v in files.items() if h not in cache}
    print(f"analyzing {len(todo)} new / {len(files)} unique functions with cppcheck + flawfinder", flush=True)
    if todo:
        IDE_CACHE.parent.mkdir(exist_ok=True)
        with open(IDE_CACHE, "a") as f:
            for h, r in run_analyzers(todo).items():
                cache[h] = {"h": h, **r}
                f.write(json.dumps(cache[h]) + "\n")
    rows = []
    for (i, s), fs in sorted(items.items()):
        funcs = [(label, name, ide_entries(cache[h]["findings"], off)) for label, name, h, off in fs]
        more = max(0, len(source_callees(pairs[i], s)[1]) - MAX_CALLEES)
        block, shown = ide_block(funcs, more, len(blocks[i, s]["concept"]))
        rows.append({"pair": i, "side": s, "n_warnings": sum(len(e) for _, _, e in funcs), "n_shown": shown,
                     "target_cppcheck_fail": bool(cache[fs[0][2]]["cppcheck_fail"]), "ide": block})
    with open(IDE_BLOCKS, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)

    def dist(xs):
        xs = sorted(xs)
        return f"mean {sum(xs) / len(xs):.0f} / median {xs[len(xs) // 2]} / p90 {xs[int(.9 * len(xs))]} / max {xs[-1]}"

    n = len(rows)
    print(f"ide block empty (no warning on target or listed callees): {sum(r['n_warnings'] == 0 for r in rows)}/{n}; "
          f"cut to budget: {sum(r['n_shown'] < r['n_warnings'] for r in rows)}/{n}; "
          f"cppcheck could not parse target: {sum(r['target_cppcheck_fail'] for r in rows)}/{n}")
    print(f"chars ide {dist([len(r['ide']) for r in rows])}")
    print(f"chars concept {dist([len(blocks[r['pair'], r['side']]['concept']) for r in rows])}")
    print(f"wrote {IDE_BLOCKS}")


# ---------------------------------------------------------------- LLM (authors' BaselineAgent + Vertex Gemini)

def load_authors():
    # agent.py imports langchain.agents for the ReAct agent only; the plain-LLM BaselineAgent never uses it.
    lc = ModuleType("langchain.agents")
    lc.initialize_agent = lc.AgentType = None
    sys.modules.setdefault("langchain", ModuleType("langchain"))
    sys.modules.setdefault("langchain.agents", lc)
    import agent as jv_agent, prompt as jv_prompt  # vendor/JitVul/code/evaluation_pipeline, unmodified
    jv_agent.print = lambda *a, **k: None  # silence predict()'s echo of every response (module-level shadow)
    return jv_agent, jv_prompt


class Gemini:
    """Vertex Gemini, thinking off, temperature 0 (authors' --temp 0), identical for every arm."""

    def __init__(self):
        from google import genai
        from google.genai import types
        project = os.environ.get("VERTEX_PROJECT") or os.environ["GOOGLE_CLOUD_PROJECT"]
        location = os.environ.get("VERTEX_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        self.client = genai.Client(vertexai=True, project=project, location=location)
        self.model = os.environ.get("JV_MODEL", "gemini-2.5-flash")
        self.cfg = types.GenerateContentConfig(temperature=0, max_output_tokens=8192,
                                               thinking_config=types.ThinkingConfig(thinking_budget=0),
                                               automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))

    def __call__(self, prompt):
        for attempt in range(10):
            try:
                r = self.client.models.generate_content(model=self.model, contents=prompt, config=self.cfg)
                break
            except Exception as e:
                code = getattr(e, "code", None)
                if attempt == 9 or (isinstance(code, int) and code not in (408, 429, 500, 502, 503, 504)):
                    raise
                wait = min(90, 2 ** attempt) * (0.5 + random.random())
                print(f"  retry {attempt + 1} after {type(e).__name__} {code}, sleeping {wait:.0f}s", flush=True)
                time.sleep(wait)
        u = r.usage_metadata
        tin, tout, tth = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
        cand = r.candidates[0] if r.candidates else None
        return {"raw": r.text or "", "finish": getattr(cand.finish_reason, "name", str(cand.finish_reason)) if cand else str(r.prompt_feedback),
                "tok_in": tin, "tok_out": tout, "tok_thought": tth, "cost": tin * PRICE_IN + (tout + tth) * PRICE_OUT}


class AuthorsLLM:
    """Stands in for langchain ChatOpenAI inside the authors' BaselineAgent: llm(prompt).content."""

    def __init__(self, gem):
        self.gem, self.rec = gem, None

    def __call__(self, prompt):
        self.rec = self.gem(prompt)
        return NS(content=self.rec["raw"])


COT_ANCHOR = "Solve this problem step by step."


def build_prompt(jv_prompt, arm, pair, side, block):
    """Authors' CoT prompt; other arms insert their block between the code and the closing CoT instruction."""
    base = jv_prompt.construct_cot_prompt(strip_fence(pair[f"{side}_function_body"]))
    if arm == "base":
        return base
    k = base.rindex(COT_ANCHOR)
    return base[:k] + block[arm] + "\n\n    " + base[k:]


def smoke_pairs(blocks):
    ok = {i for (i, s), b in blocks.items() if b["n_src_callees"]}
    return [i for i in sorted(ok) if all((i, s) in blocks and blocks[i, s]["n_src_callees"] for s in SIDES)][:SMOKE_N]


def load_blocks():
    if not BLOCKS.exists():
        sys.exit("out/blocks.jsonl missing: run `./run.sh annotate` first")
    blocks = {(b["pair"], b["side"]): b for b in read_jsonl(BLOCKS)}
    for r in read_jsonl(IDE_BLOCKS):  # separate file, so blocks.jsonl and the other arms stay byte-identical
        blocks[r["pair"], r["side"]]["ide"] = r["ide"]
    return blocks


def cmd_run(a):
    assert a.arm in ARMS, a.arm
    if a.arm == "ide" and not IDE_BLOCKS.exists():
        cmd_ide(a)
    pairs, blocks = load_pairs(), load_blocks()
    jv_agent, jv_prompt = load_authors()
    ids = smoke_pairs(blocks) if a.smoke else list(range(len(pairs)))[: a.limit or None]
    path = OUT / "responses" / f"{a.arm}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["pair"], r["side"]) for r in read_jsonl(path) if "error" not in r}
    todo = [(i, s) for i in ids for s in SIDES if (i, s) not in done]
    print(f"[{a.arm}] {len(ids)} pairs, {len(todo)} calls to make ({len(ids) * 2 - len(todo)} cached)", flush=True)
    if not todo:
        return
    gem, lock, tally, t0 = Gemini(), threading.Lock(), [0, 0.0], time.time()

    def one(job):
        i, s = job
        prompt = build_prompt(jv_prompt, a.arm, pairs[i], s, blocks[i, s])
        llm = AuthorsLLM(gem)
        try:
            pred, cwe = jv_agent.BaselineAgent(llm=llm).predict(prompt)
            rec = dict(llm.rec, pred=pred, cwe_pred=cwe)
        except ValueError:  # unterminated "@@CWE:" tag: the released loop drops the whole pair; keep the verdict
            rec = dict(llm.rec, pred=int("@@vulnerable@@" in llm.rec["raw"].lower()), cwe_pred="", parse_error=True)
        except Exception as e:
            rec = {"error": f"{type(e).__name__}: {e}"[:300]}
        rec.update(pair=i, side=s, arm=a.arm, model=gem.model, prompt_sha1=sha1(prompt), prompt_chars=len(prompt))
        with lock:
            with open(path, "a") as f:
                f.write(json.dumps(rec) + "\n")
            tally[0] += 1
            tally[1] += rec.get("cost", 0.0)
            if "error" in rec or tally[0] % 25 == 0 or tally[0] == len(todo):
                print(f"[{a.arm}] {tally[0]}/{len(todo)} calls, ${tally[1]:.3f}, {time.time() - t0:.0f}s"
                      + (f"  ERROR pair {i} {s}: {rec['error']}" if "error" in rec else ""), flush=True)

    with ThreadPoolExecutor(int(os.environ.get("JV_WORKERS", "4"))) as ex:
        list(ex.map(one, todo))


def cmd_show(a):
    pairs, blocks = load_pairs(), load_blocks()
    _, jv_prompt = load_authors()
    i = a.pair if a.pair is not None else smoke_pairs(blocks)[0]
    b = blocks[i, a.side]
    print(build_prompt(jv_prompt, a.arm, pairs[i], a.side, b))
    print(f"--- pair {i} ({pairs[i]['cve']}) side {a.side}; placebo donor pair {b['donor']} "
          f"({pairs[b['donor']]['cve']}) side {b['donor_side']}")


def cmd_check(_):
    pairs = load_pairs()
    print(f"pairs {len(pairs)}, CVEs {len({p['cve'] for p in pairs})}, projects {len({p['project'] for p in pairs})}, "
          f"CWEs {len({c for p in pairs for c in p['cwe']})}")
    for s in SIDES:
        fenced = sum(strip_fence(p[f"{s}_function_body"]) != p[f"{s}_function_body"] for p in pairs)
        print(f"{s}: leading fence line stripped in {fenced}/{len(pairs)} bodies")
    differ = callers = callees = 0
    for p in pairs:
        for s in SIDES:
            t, names = target_and_callees(p, s)
            released = p[f"{s}_caller_graph"].get(t, {}).get("callers", [])  # what tools.get_callees returns
            differ += set(released) != set(names)
            callers += len(released)
            callees += len(names)
    n = 2 * len(pairs)
    print(f"get_callees fix: mean callees {callees / n:.1f} vs released (callers) {callers / n:.1f}; lists differ for {differ}/{n} functions")
    annotate, _ = load_annotator()
    demo = annotate("int f(char *p, int n) {\n  char buf[8];\n  if (p == NULL) return -1;\n  if (n < 8) buf[n] = *p;\n  free(p);\n  return 0;\n}")
    print("annotator demo:", demo)
    assert {"Null check", "Buffer access", "Memory free", "Bounds check"} <= set(demo), demo
    demo = run_analyzers({"demo": (".c", "void g(char *s) {\n  char b[4];\n  strcpy(b, s);\n  int *p = 0;\n  *p = 1;\n}")})["demo"]
    print("analyzer demo:", [f[1:3] for f in demo["findings"]])
    assert {"cppcheck", "flawfinder"} <= {f[1] for f in demo["findings"]}, demo
    load_authors()
    import google.genai  # noqa: F401
    print("check ok")


def cmd_verify(_):
    """Re-render the prompt of every cached response and compare with its stored sha1 (arms must not drift)."""
    pairs, blocks = load_pairs(), load_blocks()
    _, jv_prompt = load_authors()
    for arm in ARMS:
        rows = [r for r in read_jsonl(OUT / "responses" / f"{arm}.jsonl") if "prompt_sha1" in r]
        bad = [r for r in rows if sha1(build_prompt(jv_prompt, arm, pairs[r["pair"]], r["side"], blocks[r["pair"], r["side"]]))
               != r["prompt_sha1"]]
        print(f"{arm}: {len(rows)} cached prompts re-rendered, {len(bad)} differ")
        assert not bad, f"{arm} prompts changed for {[(r['pair'], r['side']) for r in bad[:5]]}"
    print("verify ok")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("annotate")
    sub.add_parser("ide")
    sub.add_parser("verify")
    r = sub.add_parser("run")
    r.add_argument("arm", choices=ARMS)
    r.add_argument("--smoke", action="store_true")
    r.add_argument("--limit", type=int)
    s = sub.add_parser("show")
    s.add_argument("arm", choices=ARMS)
    s.add_argument("--pair", type=int)
    s.add_argument("--side", choices=SIDES, default="vulnerable")
    a = ap.parse_args()
    {"check": cmd_check, "annotate": cmd_annotate, "ide": cmd_ide, "run": cmd_run, "show": cmd_show,
     "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    main()
