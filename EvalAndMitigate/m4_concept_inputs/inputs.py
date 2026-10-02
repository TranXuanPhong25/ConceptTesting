"""Concept-guided inputs: the Advanced docstring stays the only oracle; m3's spec tables contribute only WHICH inputs to
exercise. Deterministic (no LLM): from each rule of m3_concept_spec/out/specs_<spec|placebo>.jsonl only the `input`
field is used (never `expected`), outcome/behaviour wording is stripped, and the survivors are appended to the unchanged
Advanced docstring as a plain `//` comment section.

arms: concept = C1-C8 (+C0) items from specs_spec.jsonl
      placebo = the same method's specs_placebo.jsonl (P1-P8 irrelevant facets + C0), same stripping, matched counts
               (same total number of items and the same number of C0 items as the concept arm, per method)

usage (host python): python3 m4_concept_inputs/inputs.py [idx ...]     (idx given -> *_smoke doc files)
                     python3 m4_concept_inputs/inputs.py selftest
writes data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m4_{concept,placebo}_inputs[_smoke].jsonl
and m4_concept_inputs/out/items_{concept,placebo}.jsonl (the selected items per method, for inspection).
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADV = f"{REPO}/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"
SPECS = REPO + "/m3_concept_spec/out/specs_{}.jsonl"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m4_{}_inputs{}.jsonl"
OUT = f"{REPO}/m4_concept_inputs/out"

MAX_ITEMS = 12  # ~ the 15-17 tests the generator writes per method; the concept specs keep a median of 18 items
# facet order = round-robin order; C0 (typical inputs) last in every round
FACETS = {"concept": [("C1", "null inputs"), ("C2", "empty/blank inputs"), ("C3", "boundaries, indexes, lengths"),
                      ("C4", "invalid or unusual inputs"), ("C5", "escaping, normalisation, format"),
                      ("C6", "numeric range, overflow, precision"), ("C7", "characters, locale, unicode"),
                      ("C8", "state, repeated calls"), ("C0", "typical inputs")],
          "placebo": [("P1", "naming"), ("P2", "documentation"), ("P3", "performance"), ("P4", "thread-safety"),
                      ("P5", "logging"), ("P6", "API stability"), ("P7", "readability"), ("P8", "dependencies"),
                      ("C0", "typical inputs")]}
SPEC_OF = {"concept": "spec", "placebo": "placebo"}
HEADER = ("// Input classes to exercise (derived from a concept checklist; expected results are intentionally not given"
          " - derive them from the specification above):")

# wording that states an outcome or behaviour (of the focal method or of anything else); an item that still contains
# one after removing such parentheticals is dropped whole. "valid"/"invalid" are kept as input-class labels.
OUTCOME = re.compile(r"\b(returns?|returned|returning|throws?|thrown|throwing|\w*exception\w*|\w*error\w*|results?|resulted|"
                     r"resulting|expect\w*|should|must|will|would|fail\w*|succe\w*|handl\w*|ignor\w*|treat\w*|behavio\w*|"
                     r"produc\w*|yield\w*|assum\w*|unlikely|caus\w*|leads?|leading|convert\w*|preserv\w*|output\w*|rais\w*|"
                     r"reject\w*|accept\w*|allow\w*|truncat\w*|escaped|normali[sz]ed|interpreted|parsed|considered|caught|catch\w*)\b"
                     r"|\b(does not|doesn't|do not|never|always)\s+(modif|chang|alter|affect|mutat|creat)\w*|→|->|=>|<-", re.I)
PAREN = re.compile(r"\s*\([^()]*(?:\([^()]*\)[^()]*)*\)")  # one nesting level, e.g. "(e.g., next() throws X)"


def strip(text):
    """input text without outcome wording, or None when the outcome wording is not confined to a parenthetical."""
    t = PAREN.sub(lambda m: "" if OUTCOME.search(m.group()) else m.group(), text)
    t = t.strip()  # literal whitespace inside examples is kept as is
    t = t.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")  # keep it on one comment line, literally
    return None if not t or OUTCOME.search(t) else t


def items(spec, facets):
    """{facet: [stripped inputs]} in spec order; an input already listed under an earlier facet is dropped."""
    out, seen = {}, set()
    for k, _ in facets:
        out[k] = []
        for r in spec[k] if isinstance(spec[k], list) else []:
            s = strip(r["input"])
            if s and s.lower().strip(" .") not in seen:
                seen.add(s.lower().strip(" .")); out[k].append(s)
    return out


def round_robin(pool, keys, n):
    """up to n items, one per facet per round, facets in `keys` order."""
    picked, rnd = [], 0
    while len(picked) < n and any(len(pool[k]) > rnd for k in keys):
        picked += [(k, pool[k][rnd]) for k in keys if len(pool[k]) > rnd][:n - len(picked)]
        rnd += 1
    return picked


def select(concept_spec, placebo_spec):
    """concept items (cap MAX_ITEMS), then placebo items matched in total and in the number of C0 items."""
    c = round_robin(items(concept_spec, FACETS["concept"]), [k for k, _ in FACETS["concept"]], MAX_ITEMS)
    k0 = sum(k == "C0" for k, _ in c)
    pool = items(placebo_spec, FACETS["placebo"])
    p0 = [("C0", s) for s in pool["C0"][:k0]]
    p = round_robin(pool, [k for k, _ in FACETS["placebo"][:-1]], len(c) - len(p0)) + p0
    return c, p


def render(picked, arm):
    """the appended section: header + one line per item, grouped in facet order."""
    names = dict(FACETS[arm])
    lines = [f"// - {names[k]}: {s}" for k, _ in FACETS[arm] for kk, s in picked if kk == k]
    return "\n" + HEADER + "\n" + "\n".join(lines) + "\n"


def build(idx):
    adv = [json.loads(l) for l in open(ADV)]
    specs = {arm: {r["idx"]: r for r in map(json.loads, open(SPECS.format(s)))} for arm, s in SPEC_OF.items()}
    sel = idx or range(len(adv))
    os.makedirs(OUT, exist_ok=True)
    res = {"concept": [], "placebo": []}
    for i in sel:
        assert specs["concept"][i]["id"] == specs["placebo"][i]["id"] == adv[i]["extra:project_name"]
        c, p = select(specs["concept"][i]["spec"], specs["placebo"][i]["spec"])
        for arm, picked in (("concept", c), ("placebo", p)):
            res[arm].append((i, adv[i], picked))
    for arm, rows in res.items():
        suffix = "_smoke" if idx else ""
        with open(DOC_OUT.format(arm, suffix), "w") as f:
            for i, rec, picked in rows:
                f.write(json.dumps({**rec, "generated_docstring": rec["generated_docstring"] + render(picked, arm)}) + "\n")
        if not idx:
            with open(f"{OUT}/items_{arm}.jsonl", "w") as f:
                for i, rec, picked in rows:
                    f.write(json.dumps({"idx": i, "id": rec["extra:project_name"], "items": picked,
                                        "section_chars": len(render(picked, arm))}) + "\n")
        print("wrote", DOC_OUT.format(arm, suffix), len(rows), "records")


def selftest():
    assert strip("opt = null") == "opt = null"
    assert strip("str = \"abc\" (returns -1)") == 'str = "abc"'
    assert strip("Special characters like backslash (\\), double quote (\")") == "Special characters like backslash (\\), double quote (\")"
    assert strip("An IOException occurs during writing") is None
    assert strip("obj is not null, but obj.toString() returns null") is None
    assert strip("The method does not modify the state of c") is None and strip("str does not contain 'a'") == "str does not contain 'a'"
    assert strip("x → 3") is None and strip("No invalid inputs are expected to raise exceptions.") is None
    assert strip("a (e.g., `p.next()` throws `IOException`) b") == "a b"
    assert strip('"a  b" (assuming x), c') == '"a  b", c'
    assert strip("str = \"a\\tb\"\nnext") == 'str = "a\\tb"\\nnext'
    rr = round_robin({"A": ["a1", "a2", "a3"], "B": ["b1"], "C": []}, ["A", "B", "C"], 3)
    assert rr == [("A", "a1"), ("B", "b1"), ("A", "a2")], rr
    # whole data: no outcome wording survives, counts are matched, the Advanced docstring is kept byte for byte
    adv = [json.loads(l) for l in open(ADV)]
    specs = {arm: {r["idx"]: r["spec"] for r in map(json.loads, open(SPECS.format(s)))} for arm, s in SPEC_OF.items()}
    short = 0
    for i in range(len(adv)):
        c, p = select(specs["concept"][i], specs["placebo"][i])
        assert not any(OUTCOME.search(s) for _, s in c + p)
        assert sum(k == "C0" for k, _ in c) >= sum(k == "C0" for k, _ in p)
        short += len(c) - len(p)
        doc = adv[i]["generated_docstring"] + render(c, "concept")
        assert doc.startswith(adv[i]["generated_docstring"]) and doc.count(HEADER) == 1
    print(f"selftest ok (placebo shortfall over all methods: {short} items)")


if __name__ == "__main__":
    selftest() if sys.argv[1:2] == ["selftest"] else build([int(i) for i in sys.argv[1:]])
