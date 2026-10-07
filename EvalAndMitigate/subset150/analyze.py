"""Numbers for subset150/RESULTS.md (host python, stdlib).  usage: python3 subset150/analyze.py > subset150/out/analysis.txt

Each arm = its existing 78-method run (reused as is) + its run on the new methods (this folder), concatenated in the
order of data/prompts/buggy_source_data_unified_invoked_subset150.jsonl. Outcome parsing (load/row/p_mcnemar/HEAD) is
m6_agent_oracle/analyze.py's, body_leaks is m5's. Scoring: the intersection of the clean (non-glitched) methods of all
arms with data. Contrasts: exact McNemar on methods with >=1 E and >=1 M.
"""
import glob, hashlib, importlib.util, json, os, sys
from collections import Counter


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


A6 = _load("m6_analyze", "m6_agent_oracle/analyze.py")
M5 = _load("m5_spec", "m5_blind_concept_spec/spec.py")
sys.path.insert(0, "subset150")
import calllog

P = "data/prompts/"
G = P + "Gemini-2-5-flash_buggy_source_data_unified_invoked_with"
# name, (78: FILE_POST_FIX, parts folder, docstring file), (new: FILE_POST_FIX, docstring file)
ARMS = [("Only Doc", ("unified_invoked_docstring_prompt", None, G + "_docstring.jsonl"), ("s150_onlydoc", G + "_docstring_s150new.jsonl")),
        ("Advanced", ("unified_invoked_advanced_docstring_prompt", None, G + "_advanced_docstring_base_cot_code.jsonl"),
         ("s150_adv", G + "_advanced_docstring_base_cot_code_s150new.jsonl")),
        ("Adv rerun", ("m9_adv_rerun", "m9_concept_advanced", G + "_m9_adv_rerun.jsonl"), ("s150_rerun", G + "_s150_m9_adv_rerun.jsonl")),
        ("m9 concept", ("m9_concept", "m9_concept_advanced", G + "_m9_concept.jsonl"), ("s150_concept", G + "_s150_m9_concept.jsonl")),
        ("m9 placebo", ("m9_placebo", "m9_concept_advanced", G + "_m9_placebo.jsonl"), ("s150_placebo", G + "_s150_m9_placebo.jsonl"))]
PAIRS = [("m9 placebo", "m9 concept", "primary"), ("Only Doc", "Advanced", "paper's mitigation"),
         ("Advanced", "Adv rerun", "A/A noise"), ("Adv rerun", "m9 concept", "secondary")]  # (a, b): "b vs a"
records = [json.loads(l) for l in open(P + "buggy_source_data_unified_invoked_subset150.jsonl")]
N_OLD = 78
ids = [r["extra:project_name"].replace("_buggy", "") for r in records]
proj = [i.rsplit("_", 1)[0] for i in ids]
tag = lambda i: f"{i}:{ids[i]}"


def outcomes():
    data = {}
    for name, (fo, do, _), (fn, _) in ARMS:
        if glob.glob(A6.LOGS.format(fo)) and glob.glob(A6.LOGS.format(fn)):
            data[name] = A6.load(fo, do) + A6.load(fn, "subset150")
            assert [m["sig"] for m in data[name]] == [r["source:source_method_signature"] for r in records], name
    return data


def table(data, idx, title):
    print(f"\n### {title}: {len(idx)} methods\n\n{A6.HEAD}")
    for name, ms in data.items():
        print(A6.row(name, [ms[i] for i in idx]))


def mcnemar(data, idx, pairs=PAIRS):
    has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
    for a, b, why in [p for p in pairs if p[0] in data and p[1] in data]:
        out = []
        for k in ("E", "M"):
            oa, ob, p = A6.p_mcnemar(has(a, k), has(b, k))
            out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.3g}")
        print(f"- {b} vs {a} ({why}): " + "; ".join(out))


def docs(arm_name):
    _, (_, _, fo), (_, fn) = next(a for a in ARMS if a[0] == arm_name)
    if not (os.path.exists(fo) and os.path.exists(fn)):
        return None
    ds = [json.loads(l)["generated_docstring"] for f in (fo, fn) for l in open(f)]
    return ds if len(ds) == len(records) else None


def main():
    data = outcomes()
    print(f"# subset150: {len(records)} methods ({N_OLD} old + {len(records) - N_OLD} new), "
          f"{len(set(ids))} bugs; per project {dict(Counter(proj))}")
    print(f"arms with data: {list(data)}")
    if not data:
        return
    glitched = {n: [tag(i) for i, m in enumerate(ms) if m["glitch"]] for n, ms in data.items()}
    print("glitched (empty error report) per arm:", json.dumps(glitched))
    keep = [i for i in range(len(records)) if all(not ms[i]["glitch"] for ms in data.values())]
    old, new = [i for i in keep if i < N_OLD], [i for i in keep if i >= N_OLD]
    body = sorted({i for n in data for ds in [docs(n)] if ds for i in range(len(records)) if M5.body_leaks(records[i], ds[i])})
    subsets = {"all": keep, "old stratum (Lang, Gson, Codec, Cli, Csv)": old, "new stratum": new,
               "all, without Gson_4 and Cli_1": [i for i in keep if ids[i] not in ("Gson_4", "Cli_1")],
               f"all, without the {len(body)} methods whose docstring carries the focal body (any arm)": [i for i in keep if i not in body]}
    print("\n## Intersection of clean methods")
    for label, idx in subsets.items():
        table(data, idx, label)
        print()
        mcnemar(data, idx)
    print(f"\nfocal body in a docstring (any arm; m5 body_leaks): {[tag(i) for i in body]}")
    print("\n## Each arm on its own clean methods\n\n" + A6.HEAD)
    for name, ms in data.items():
        print(A6.row(f"{name} ({sum(not m['glitch'] for m in ms)} methods)", [m for m in ms if not m["glitch"]]))
    print("\n## Discordant methods (intersection, all)")
    for a, b, why in [p for p in PAIRS if p[0] in data and p[1] in data]:
        for k in ("E", "M"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a} ({why}): only {b} {g}; only {a} {l}")
    print("\nM-methods per arm (method: M tests):")
    for name, ms in data.items():
        print(f"- {name}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]))
    print("\n## Per project (intersection): methods, then per arm ≥1 E / ≥1 M / E tests / M tests")
    print("| project | n | " + " | ".join(data) + " |\n|---|---|" + "---|" * len(data))
    for p in dict.fromkeys(proj):
        idx = [i for i in keep if proj[i] == p]
        cell = lambda ms: (f"{sum(ms[i]['counts']['E'] > 0 for i in idx)} / {sum(ms[i]['counts']['M'] > 0 for i in idx)} / "
                           f"{sum(ms[i]['counts']['E'] for i in idx)} / {sum(ms[i]['counts']['M'] for i in idx)}")
        print(f"| {p} | {len(idx)} | " + " | ".join(cell(ms) for ms in data.values()) + " |")
    concepts(data, keep)
    adv, rerun = docs("Advanced"), docs("Adv rerun")
    if adv and rerun:
        same = lambda idx: sum(adv[i] == rerun[i] for i in idx)
        print(f"\n## Docstrings\n- Advanced vs Adv rerun byte-identical docstrings (T=0, same prompt): old {same(range(N_OLD))}/{N_OLD}, "
              f"new {same(range(N_OLD, len(records)))}/{len(records) - N_OLD}")
    for name in [a[0] for a in ARMS]:
        ds = docs(name)
        if ds:
            print(f"- {name}: mean docstring {sum(map(len, ds[N_OLD:])) // (len(records) - N_OLD)} chars on the new methods; "
                  f"focal body in the docstring: {[tag(i) for i in range(len(records)) if M5.body_leaks(records[i], ds[i])]}")
    cost()


def concepts(data, keep):
    old = json.load(open("m2_concept_diag/manual_labels.json"))
    path = "subset150/manual_labels_new.json"
    new = json.load(open(path)) if os.path.exists(path) else {}
    lab = {i: old[str(i)]["concepts"] for i in range(N_OLD)}
    lab.update({N_OLD + int(k): v["concepts"] for k, v in new.items()})
    print(f"\n## Per concept (manual labels: m2 for the 78, {path} for {len(new)} new methods; "
          f"{sum(bool(v.get('checked_by_hand')) for v in new.values())} new labels checked by hand)")
    print("Methods can carry several concepts. Cells: ≥1 E / ≥1 M among the intersection methods with that label.\n")
    print("| concept | n (old+new) | " + " | ".join(data) + " | concept vs placebo, ≥1 E only-concept/only-placebo |\n|---|---|" + "---|" * (len(data) + 1))
    for c in [f"C{k}" for k in range(9)]:
        idx = [i for i in keep if c in lab.get(i, [])]
        if not idx:
            continue
        cell = lambda ms: f"{sum(ms[i]['counts']['E'] > 0 for i in idx)} / {sum(ms[i]['counts']['M'] > 0 for i in idx)}"
        cp = ""
        if "m9 concept" in data and "m9 placebo" in data:
            e = lambda n: [data[n][i]["counts"]["E"] > 0 for i in idx]
            op, oc, p = A6.p_mcnemar(e("m9 placebo"), e("m9 concept"))
            cp = f"{oc}/{op} (p={p:.2g})"
        print(f"| {c} | {len(idx)} ({sum(i < N_OLD for i in idx)}+{sum(i >= N_OLD for i in idx)}) | "
              + " | ".join(cell(ms) for ms in data.values()) + f" | {cp} |")
    print(f"unlabelled methods in the intersection: {[tag(i) for i in keep if i not in lab]}")


def cost():
    print("\n## LLM calls and cost (new methods only; the 78 reuse earlier runs)\n")
    calllog.total(quiet=False)
    cs = calllog.calls()
    # map test-generation calls back to methods by prompt hash
    for name, _, (fn, _) in ARMS:
        f = f"data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{fn}_with_completion.jsonl"
        if not os.path.exists(f):
            continue
        rs = [json.loads(l) for l in open(f)]
        sha = {hashlib.sha1(r["content"].encode()).hexdigest()[:12]: r["id"] for r in rs}
        mine = [c for c in cs if c.get("stage") == f"testgen_{fn}"]
        loops = [c for c in mine if (c.get("out_tok") or 0) >= 65536]
        print(f"- test generation {name}: {len(rs)} completions, {len(mine)} API attempts, ${sum(c['usd'] for c in mine):.3f}; "
              f"65,536-token completions: {[sha.get(c['prompt_sha'], '?') for c in loops]} (${sum(c['usd'] for c in loops):.3f})")
    for name in [a[0] for a in ARMS]:
        ds = docs(name)
        if ds:
            long = [tag(i) for i in range(N_OLD, len(records)) if len(ds[i]) > 50000]
            print(f"- docstrings {name}, new methods with a >50k-char docstring (whole-text fallback of a repetition loop): {long}")
    for c in [c for c in cs if c["log"].endswith("m9/llm_calls.jsonl") and (c.get("out_tok") or 0) >= 65536]:
        print(f"  m9 {c['arm']} loop: {tag(N_OLD + c['idx'])} ${c['usd']:.3f}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["glitched"]:  # record indexes (new-method file) of glitched blocks of one new-method run, for --redo
        print(" ".join(str(i) for i, m in enumerate(A6.load(sys.argv[2], "subset150")) if m["glitch"]))
    else:
        main()
