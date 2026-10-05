"""m9 mechanism (offline, no LLM): does the Advanced prompt's Part 2 (the "corrected implementation") fix the bug?

Per arm and method: the first ```java block of the completion that declares the focal method (same name, same parameter
count) is taken as Part 2. The focal method of a scratch copy of the buggy source file (byte span from m8's
out/mutants.jsonl) is replaced by that method plus any new helper members of the block (methods/fields whose name and
arity are not already declared in the file); imports of the block that the file lacks are added; non-ASCII becomes
Java \\u escapes. The file is compiled alone against the checkout's cp.test and the bug's trigger tests run on it.
fix = compiles and every trigger test passes (all fail on the recompiled buggy original: m8 phase0_base.json).
Per bug: the Part 2s of all focal methods of the bug substituted together (11 bugs have 2-6 methods, always one file).
Reused from m8 (read-only): phase0.py (compile_file, run_tests, export_cp, M8Runner), out/env.json (classpaths, trigger
tests), out/mutants.jsonl (focal spans), mutate.py (tree-sitter parser). Trigger tests and the fixed version are used
here only, never in a prompt.

Runs in the m9 sandbox (dock9.sh: no credentials, no network, checkouts read-only, scratch in volume m9scratch):
  bash m9_concept_advanced/dock9.sh python3 m9_concept_advanced/fixrate.py selftest      extraction only (no checkouts)
  bash m9_concept_advanced/dock9.sh python3 m9_concept_advanced/fixrate.py check         harness validation: per bug, the
        FIXED checkout's focal methods as "Part 2" (expect fix) and the buggy methods (expect no fix) -> out/fixrate_check.json
  bash m9_concept_advanced/dock9.sh python3 m9_concept_advanced/fixrate.py run <arm>     -> out/fixrate_<arm>.json
Each of check/run ends by asserting `git diff --quiet HEAD -- <main src dir>` on every shared buggy and fixed checkout.
"""
import hashlib, importlib.util, json, os, re, sys
from collections import defaultdict

REPO = "/repo"
sys.path[:0] = [REPO]
OUT = os.environ.get("M9_OUT") or f"{REPO}/m9_concept_advanced/out"  # dock9.sh: /m9out (top-level mount)
M8 = f"{REPO}/m8_concept_mutants"
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


P0 = _load("m8phase0", f"{M8}/phase0.py")
MU = _load("m8mutate", f"{M8}/mutate.py")
T, walk = MU.T, MU.walk
DECL = ("method_declaration", "constructor_declaration")


def arity(n):
    p = n.child_by_field_name("parameters")
    return sum(c.type in ("formal_parameter", "spread_parameter") for c in p.children) if p else 0


def declared(root):
    """{(name, arity)} of methods/ctors and {(name, None)} of fields and classes declared anywhere in a file."""
    out = set()
    for n in walk(root):
        if n.type in DECL:
            out.add((T(n.child_by_field_name("name")), arity(n)))
        elif n.type == "field_declaration":
            out |= {(T(d.child_by_field_name("name")), None) for d in n.children if d.type == "variable_declarator"}
        elif n.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            out.add((T(n.child_by_field_name("name")), None))
    return out


def member_key(n):
    if n.type in DECL:
        return [(T(n.child_by_field_name("name")), arity(n))]
    if n.type == "field_declaration":
        return [(T(d.child_by_field_name("name")), None) for d in n.children if d.type == "variable_declarator"]
    nm = n.child_by_field_name("name")
    return [(T(nm), None)] if nm else []


def part2(completion, rec, existing):
    """(member texts, import lines) for the focal method's Part 2, or (None, reason)."""
    name, n_par = rec["source:source_method_name"], len(rec["source:source_method_parameters"])
    for block in re.findall(r"```java(.*?)```", completion or "", re.DOTALL):
        imports = [re.sub(r"\s+", " ", x.strip()) for x in re.findall(r"^\s*import\s+[\w.*\s]+;", block, re.M)]
        body = re.sub(r"^\s*(import|package)\s+[\w.*\s]+;", "", block, flags=re.M)
        src = ("class M9Wrap {\n" + body + "\n}\n").encode()
        root = MU.parser().parse(src).root_node
        hits = [n for n in walk(root) if n.type in DECL and T(n.child_by_field_name("name")) == name]
        hits = [n for n in hits if arity(n) == n_par] or hits
        if not hits:
            continue
        focal = hits[0]
        cbody = focal.parent  # class_body that holds the focal method (the wrapper's or an LLM-written class)
        keep = []
        for m in cbody.children:
            if m.type in ("{", "}", ";", "line_comment", "block_comment"):
                continue
            if (m.start_byte, m.end_byte) == (focal.start_byte, focal.end_byte) or (m.type in DECL + ("field_declaration",) and not set(member_key(m)) & existing):
                keep.append(src[m.start_byte:m.end_byte].decode("utf-8", "replace"))
        return keep, imports
    return None, "no ```java block declares the focal method"


def jescape(s):
    """non-ASCII as Java \\u escapes (UTF-16 units), so the text is valid in UTF-8 and Latin-1 source files."""
    u16 = lambda b: "".join(f"\\u{int.from_bytes(b[k:k + 2], 'big'):04x}" for k in range(0, len(b), 2))
    return "".join(c if ord(c) < 128 else u16(c.encode("utf-16-be")) for c in s)


def substitute(src, edits):
    """edits: [(mstart, mend, members, imports)] in one file -> new file bytes."""
    for s, e, members, _ in sorted(edits, key=lambda x: -x[0]):
        src = src[:s] + jescape("\n\n    ".join(members)).encode() + src[e:]
    have = {re.sub(r"\s+", " ", x.strip()) for x in re.findall(r"^\s*import\s+[\w.*\s]+;", src.decode("latin-1"), re.M)}
    add = sorted({i for *_, imps in edits for i in imps} - have)
    if add:
        m = re.search(rb"^\s*package\s+[\w.]+\s*;", src, re.M)
        at = m.end() if m else 0
        src = src[:at] + ("\n" + "\n".join(jescape(a) for a in add) + "\n").encode() + src[at:]
    return src


# ------------------------------------------------------------------ sandbox helpers
_ENV = None


def env():
    """m8 env.json (paths at /d4j), the focal spans, and the buggy roots (re-made in /scratch when m8 used a scratch copy)."""
    global _ENV
    if _ENV is None:
        e = P0.load_env()
        spans = {m["idx"]: {k: m[k] for k in ("bug", "file", "mstart", "mend", "src_md5")} for m in map(json.loads, open(f"{M8}/out/mutants.jsonl"))}
        for b, x in e["bugs"].items():
            if not os.path.isdir(x["root_buggy"]):  # Gson_14: no compiled classes in the shared checkout
                x["cp_buggy"], x["root_buggy"] = P0.export_cp(b, "buggy")
        if not os.path.exists(f"{P0.RUNNER}/M8Runner.class"):
            os.makedirs(P0.RUNNER, exist_ok=True)
            r = P0.sh(["javac", "-nowarn", "-d", P0.RUNNER, "-cp", P0.JUNIT, f"{M8}/M8Runner.java"])
            assert r.returncode == 0, r.stderr
        _ENV = e, spans
    return _ENV


def evaluate(bug, edits_by_idx, tag):
    try:
        return _evaluate(bug, edits_by_idx, tag)
    except Exception as e:  # a harness failure on one method must not abort the arm; it is reported as not compiled
        return {"compiled": False, "err": f"harness exception: {e!r}"[:300], "fixed": False, "any_pass": False}


def _evaluate(bug, edits_by_idx, tag):
    """substitute, compile, run the bug's trigger tests. edits_by_idx: {idx: (members, imports)}."""
    e, spans = env()
    b = e["bugs"][bug]
    files = {spans[i]["file"] for i in edits_by_idx}
    assert len(files) == 1, files
    f = files.pop()
    src = open(f"{b['root_buggy']}/{f}", "rb").read()
    assert hashlib.md5(src).hexdigest() == spans[next(iter(edits_by_idx))]["src_md5"], f"{bug}: buggy source changed"
    data = substitute(src, [(spans[i]["mstart"], spans[i]["mend"], *edits_by_idx[i]) for i in edits_by_idx])
    d = f"{P0.SCR}/m9fix/{tag}"
    ok, err = P0.compile_file(data, f, b["cp_buggy"], d)
    res = {"compiled": ok, "err": "" if ok else err}
    if ok:
        res["tests"] = P0.run_tests(b["trigger"], [f"{d}/cls", P0.RUNNER] + b["cp_buggy"], b["root_buggy"])
        res["fixed"] = all(v[0] == "PASS" for v in res["tests"].values())
        res["any_pass"] = any(v[0] == "PASS" for v in res["tests"].values())
    else:
        res["fixed"] = res["any_pass"] = False
    return res


def checkouts_clean():
    """the shared checkouts' main sources equal HEAD (they are mounted read-only here; this checks nothing else wrote them)."""
    e, _ = env()
    src_dir = {x["bug"]: x["src_dir"] for x in map(json.loads, open(f"{REPO}/m6_agent_oracle/out/evidence.jsonl"))}
    dirty = [f"{b}/{v}" for b in sorted(e["bugs"]) for v in ("buggy", "fixed")
             if P0.sh(["git", "--no-optional-locks", "diff", "--quiet", "HEAD", "--", src_dir[b]], cwd=f"{P0.CK2}/{b}/{v}").returncode != 0]
    print("checkouts with modified main sources:", dirty, flush=True)
    assert not dirty


def by_bug(idxs):
    _, spans = env()
    g = defaultdict(list)
    for i in idxs:
        g[spans[i]["bug"]].append(i)
    return g


def run(arm):
    recs = [json.loads(l) for l in open(SRC)]
    docs = {r["idx"]: r for r in map(json.loads, open(f"{OUT}/docs_{arm}.jsonl"))}
    e, spans = env()
    out = {"arm": arm, "methods": {}, "bugs": {}}
    edits = {}
    for i in sorted(docs):
        src = open(f"{e['bugs'][spans[i]['bug']]['root_buggy']}/{spans[i]['file']}", "rb").read()
        members, imports = part2(docs[i]["completion"], recs[i], declared(MU.parser().parse(src).root_node))
        if members is None:
            out["methods"][str(i)] = {"bug": spans[i]["bug"], "part2": False, "err": imports, "compiled": False, "fixed": False, "any_pass": False}
        else:
            edits[i] = (members, imports)
            out["methods"][str(i)] = {"bug": spans[i]["bug"], "part2": True, "n_members": len(members),
                                      **evaluate(spans[i]["bug"], {i: edits[i]}, f"{arm}/m{i}")}
        m = out["methods"][str(i)]
        print(arm, i, m["bug"], "part2" if m["part2"] else "NO PART2", "compiled" if m["compiled"] else m["err"][:120],
              "FIXED" if m["fixed"] else "", flush=True)
    for bug, idxs in by_bug(sorted(docs)).items():
        if len(idxs) == 1:
            out["bugs"][bug] = {**{k: out["methods"][str(idxs[0])][k] for k in ("compiled", "fixed", "any_pass")}, "idx": idxs}
        else:
            have = {i: edits[i] for i in idxs if i in edits}
            r = evaluate(bug, have, f"{arm}/b{bug}") if have else {"compiled": False, "fixed": False, "any_pass": False}
            out["bugs"][bug] = {**r, "idx": idxs, "with_part2": sorted(have)}
            print(arm, bug, idxs, "per bug:", "compiled" if r["compiled"] else r.get("err", "")[:120], "FIXED" if r["fixed"] else "", flush=True)
    json.dump(out, open(f"{OUT}/fixrate_{arm}.json", "w"), indent=1)
    n = len(out["methods"])
    print(f"{arm}: methods with Part 2 {sum(m['part2'] for m in out['methods'].values())}/{n}, compiled "
          f"{sum(m['compiled'] for m in out['methods'].values())}, fixed {sum(m['fixed'] for m in out['methods'].values())}; "
          f"bugs fixed {sum(b['fixed'] for b in out['bugs'].values())}/{len(out['bugs'])}")
    checkouts_clean()


def check():
    """harness validation: Part 2 := the FIXED checkout's version of each focal method (expect: fix, unless the patch
    also changes code outside the focal methods), and := the buggy method itself (expect: no fix)."""
    recs = [json.loads(l) for l in open(SRC)]
    e, spans = env()
    out = {}
    for bug, idxs in by_bug(sorted(spans)).items():
        b = e["bugs"][bug]
        bsrc = open(f"{b['root_buggy']}/{spans[idxs[0]]['file']}", "rb").read()
        froot = MU.parser().parse(fsrc := open(f"{P0.CK2}/{bug}/fixed/{spans[idxs[0]]['file']}", "rb").read()).root_node
        broot = MU.parser().parse(bsrc).root_node
        fixed_edits, buggy_edits, miss = {}, {}, []
        for i in idxs:
            bn = next(n for n in walk(broot) if n.start_byte == spans[i]["mstart"] and n.end_byte == spans[i]["mend"])
            params = MU.norm(T(bn.child_by_field_name("parameters")))
            fn = [n for n in walk(froot) if n.type == bn.type and T(n.child_by_field_name("name")) == T(bn.child_by_field_name("name"))
                  and MU.norm(T(n.child_by_field_name("parameters"))) == params]
            if len(fn) != 1:
                miss.append(i); continue
            for store, text in ((fixed_edits, fsrc[fn[0].start_byte:fn[0].end_byte]), (buggy_edits, bsrc[bn.start_byte:bn.end_byte])):
                comp = "Part 2:\n```java\n" + text.decode("utf-8", "replace") + "\n```\n"
                members, imports = part2(comp, recs[i], declared(broot))
                assert members and len(members) == 1, (bug, i)
                store[i] = (members, imports)
        out[bug] = {"idx": idxs, "unmatched": miss,
                    "fixed_version": evaluate(bug, fixed_edits, f"check/f{bug}") if fixed_edits else None,
                    "buggy_version": evaluate(bug, buggy_edits, f"check/b{bug}") if buggy_edits else None}
        fv, bv = out[bug]["fixed_version"] or {}, out[bug]["buggy_version"] or {}
        print(bug, idxs, "unmatched", miss, "| fixed methods:", "FIX" if fv.get("fixed") else (fv.get("err") or fv.get("tests")),
              "| buggy methods:", "fix?!" if bv.get("fixed") else "no fix", flush=True)
    json.dump(out, open(f"{OUT}/fixrate_check.json", "w"), indent=1)
    print(f"fixed-method substitution fixes {sum(bool((x['fixed_version'] or {}).get('fixed')) for x in out.values())}/{len(out)} bugs; "
          f"buggy-method substitution 'fixes' {sum(bool((x['buggy_version'] or {}).get('fixed')) for x in out.values())} (expect 0)")
    checkouts_clean()


def selftest():
    rec = {"source:source_method_name": "join", "source:source_method_parameters": [["Object[]", "a"], ["char", "sep"]]}
    existing = {("join", 2), ("join", 4), ("EMPTY", None), ("StringUtils", None)}
    c = ("**Part 2**\n```java\nimport java.util.Objects;\n\npublic static String join(Object[] a, char sep) {\n"
         "    return a == null ? null : helper(a, \"é\");\n}\n\nprivate static String helper(Object[] a, String s) { return s; }\n"
         "public static String join(Object[] a, char sep, int s, int e) { return null; }\n```\n**Part 3**\n```java\n/** doc */\n```")
    members, imports = part2(c, rec, existing)
    assert len(members) == 2 and members[0].startswith("public static String join(Object[] a, char sep)") and "helper" in members[1], members
    assert imports == ["import java.util.Objects;"]
    # a whole class in the block: its members are used, existing members dropped
    c2 = "```java\npublic class StringUtils {\n  public static final String EMPTY = \"\";\n  public static String join(Object[] a, char sep) { return EMPTY; }\n}\n```"
    m2, _ = part2(c2, rec, existing)
    assert m2 == ["public static String join(Object[] a, char sep) { return EMPTY; }"], m2
    assert part2("```java\nint x;\n```", rec, existing) == (None, "no ```java block declares the focal method")
    src = b"package p;\n\nimport java.util.List;\nclass A {\n  int f() { return 1; }\n  int g() { return 2; }\n}\n"
    s1, e1 = src.index(b"int f"), src.index(b"}\n  int g") + 1
    out = substitute(src, [(s1, e1, ["int f() { return \"\u00e9\".length(); }", "int h() { return 3; }"], ["import java.util.List;", "import java.util.Map;"])])
    assert out == (b"package p;\nimport java.util.Map;\n\n\nimport java.util.List;\nclass A {\n  int f() { return \"\\u00e9\".length(); }\n\n"
                   b"    int h() { return 3; }\n  int g() { return 2; }\n}\n"), out
    assert jescape("a\U0001F600") == "a\\ud83d\\ude00"
    print("selftest ok")


if __name__ == "__main__":
    {"selftest": selftest, "check": check, "run": lambda: run(sys.argv[2])}[sys.argv[1]]()
