"""Code-blind Concept-Spec: m3's JSON spec table (C0 + C1-C8) and deterministic renderer, but the spec-generation prompt
has NO focal method body. Context = the non-body part of the upstream `apply_format_summarize` prompt (parameters,
parameter classes and their constructors, return type and its constructors, class name, class constructors, fields,
other method signatures) + the fully qualified signature, the method name and the declaration header.

arms: blind_concept         = no body, no Javadoc
      blind_concept_javadoc = no body + the method's original Javadoc, re-extracted from the buggy class code with tree-sitter

usage (in the container): python3 m5_blind_concept_spec/spec.py <arm> [idx ...]
  writes m5_blind_concept_spec/out/specs_<arm>.jsonl (idx, id, signature, calls, temperature, prompt, reply, spec; also
  the resume cache) and data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m5_<arm>[_smoke].jsonl
  python3 m5_blind_concept_spec/spec.py javadoc   -> out/javadoc.jsonl (extracted vs dataset Javadoc) + body-leak checks of all prompts
  python3 m5_blind_concept_spec/spec.py selftest  -> parser/renderer check (no LLM, host too)
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run"]
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
OUT = f"{REPO}/m5_blind_concept_spec/out"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m5_{}.jsonl"
ARMS = ("blind_concept", "blind_concept_javadoc")

# copied from m3_concept_spec/spec.py (FACETS["spec"]), unchanged
FACETS = [("C0", "core logic", "the main functional behaviour on typical, valid inputs"),
          ("C1", "null input", "behaviour when an argument, a field it depends on, or an element inside an argument is null"),
          ("C2", "empty/blank input", "behaviour for empty strings, whitespace-only strings, and empty arrays or collections"),
          ("C3", "boundary/index/length", "behaviour at the edges of the valid range: first and last index, lengths 0, 1 and the maximum, limits reached exactly or exceeded by one"),
          ("C4", "error contract", "which invalid inputs raise which exception type, and which situations return an error value (such as null, -1 or false) instead"),
          ("C5", "escaping/normalisation/format", "handling of special or reserved characters, escape sequences, whitespace or case normalisation, and the exact format of produced or accepted text"),
          ("C6", "numeric range/overflow/precision", "behaviour for very large, very small, negative or zero numbers, overflow, rounding and floating-point precision"),
          ("C7", "characters/locale/unicode", "behaviour for non-ASCII characters, supplementary (surrogate-pair) characters, case conversion and locale-dependent input"),
          ("C8", "state/mutation/idempotence", "effects on the object's or the arguments' state, repeated or consecutive calls, and whether returned objects are shared or copies")]

# m3's POSTFIX with Part 1 "critical analysis of the code" replaced by an analysis of the intended contract, and the
# code-quoting lines dropped (there is no code). {jd*} slots are filled only for the Javadoc arm.
POSTFIX = """Please assume the role of an expert software engineer who writes the specification of a method from its interface. The method's implementation is intentionally not shown to you: you only have its declaration and the context of its class{jd_have}. Your task is to produce a two-part response: an analysis of the method's intended contract, and a structured specification that captures the method's intended requirement.

**Part 1: Contract Analysis**
First, provide your analysis by completing the following sections.

1.  **Intended Purpose:** From the method name, the parameter names and types, the return type, the enclosing class, its fields, constructors and other methods{jd_list}, what is this method meant to do, and what does a caller expect from it?
2.  **Conventions and Constraints:** Which conventions of Java, of this library and of the related methods in this class constrain its behaviour (for example null handling, empty inputs, boundaries, exceptions, formats)? For each, state the evidence and how certain it is. Say explicitly where the evidence does not determine the behaviour.
Your analysis should be very detailed and step by step, make sure you clearly write out your entire analysis.

**Part 2: Structured Specification**
Based on your analysis in Part 1, specify the method's intended behaviour (what a correct implementation must do). Go through every facet below and take a position on each one:

{facets}

Output the specification as a single JSON object inside one ```json markdown block, with exactly these keys:
{{"purpose": "<one sentence stating what the method is for>", {keys}}}
The value of each facet key is either the string "not applicable" (only when the facet cannot arise for this method) or a list of rules. Each rule is an object:
{{"input": "<a class of inputs or situations, with concrete example inputs>", "expected": "<the expected outcome for that class: return value, exception type, resulting state, or other observable property; or \\"unspecified\\">", "source": "<{sources}>"}}
- "source" says where the expectation comes from: {jd_src}"name-context" = the method, parameter and class names and the surrounding class; "type" = the Java types in the signature; "framework" = documented conventions of Java or of this library; "assumed" = your best judgement without such evidence.
- When the intended behaviour for an input class cannot be determined from the available evidence, write "expected": "unspecified" rather than guessing. Unspecified rules are welcome: prefer "unspecified" to an expectation that the evidence does not support.
- Give concrete example inputs and concrete expected values wherever the evidence supports them.
- State each expected outcome as a caller would observe it.
"""


def build_postfix(arm):
    jd = arm == "blind_concept_javadoc"
    return POSTFIX.format(
        jd_have=" and the method's original Javadoc comment" if jd else "",
        jd_list=", and the method's Javadoc comment" if jd else "",
        facets="\n".join(f"- {k} {name}: {d}." for k, name, d in FACETS),
        keys=", ".join(f'"{k}": [...]' for k, _, _ in FACETS),
        sources=("javadoc | " if jd else "") + "name-context | type | framework | assumed",
        jd_src='"javadoc" = the method\'s Javadoc comment; ' if jd else "")


_PARSER = None


def focal_node(record):
    """tree-sitter node of the focal method inside the buggy class code (the body occurs exactly once there)."""
    global _PARSER
    if _PARSER is None:
        from data.configuration import JAVA_LANGUAGE
        from tree_sitter import Parser
        _PARSER = Parser(); _PARSER.set_language(JAVA_LANGUAGE)
    code, body = record["content:source_class_code_format"].encode(), record["source:source_method_code_format"].encode()
    assert code.count(body) == 1
    s = code.find(body)
    n = _PARSER.parse(code).root_node.descendant_for_byte_range(s, s + len(body))
    while n.type not in ("method_declaration", "constructor_declaration"):
        n = n.parent
    assert (n.start_byte, n.end_byte) == (s, s + len(body))
    return n


def javadoc(record):
    """the /** */ comment immediately preceding the focal method in the buggy class code, or '' (reindented)."""
    p = focal_node(record).prev_sibling
    if not (p and p.type == "block_comment" and p.text.startswith(b"/**")):
        return ""
    return "\n".join(l.strip() if l.strip().startswith("*") else l.rstrip() for l in p.text.decode().splitlines()).replace("\n*", "\n *")


def declaration(record):
    """modifiers, type parameters, return type, name, parameters, throws: the method text before its body block."""
    n = focal_node(record)
    b = n.child_by_field_name("body")
    return re.sub(r"\s+", " ", n.text[:b.start_byte - n.start_byte].decode()).strip() + ";"


def build_prompt(record, arm):
    """the upstream summarize prompt with the focal body section replaced by a declaration-only header."""
    from utils.prompt_formats.new_prompt_formatter import PromptFormatter, ADVANCED_SUMMARIZATION_POST_FIX_BASE
    pf = PromptFormatter()
    _, p = pf.apply_format_summarize(record, "chatgpt", strategy="generation", formatting="comment", ignore_feature="full",
                                     project_name=record["extra:project_name"], advanced_analysis=True)
    body_section = pf.base_prompt_summarize("comment", record["source:source_method_code_format"])
    assert p.count(body_section) == 1 and p.endswith(ADVANCED_SUMMARIZATION_POST_FIX_BASE)
    head = ("```\n// The method whose specification you are going to write. Its implementation is intentionally not shown.\n"
            + pf.get_focal_method_signature(record["source:source_method_signature"], "comment")
            + pf.get_focal_method_name(record["source:source_method_name"], "comment")
            + "\n// The method declaration:\n" + declaration(record) + "\n")
    if arm == "blind_concept_javadoc":
        jd = javadoc(record)
        head += "\n// The original Javadoc comment of the method:\n" + (jd or "(the method has no Javadoc comment)") + "\n"
    p = p.replace(body_section, head)
    return p[:-len(ADVANCED_SUMMARIZATION_POST_FIX_BASE)] + build_postfix(arm)


CONTEXT_KEYS = ("source:source_other_method_signature", "source_class_fields", "content:source_class_constructors",
                "content:parameter_class_constructors", "content:return_type_class_constructors")


def body_leaks(record, text, w=40):
    """whitespace-normalised windows (w chars, stride w/2) of the focal body *after* its declaration found in text,
    except windows that also occur in the upstream non-body context (e.g. Gson_8: an anonymous class in the body
    overrides a method whose signature is listed under "Other methods")."""
    norm = lambda s: re.sub(r"\s+", " ", s)
    body = norm(record["source:source_method_code_format"])
    body = body[body.find("{") + 1:]
    t, ctx = norm(text), norm("\n".join(x for k in CONTEXT_KEYS for x in record.get(k, [])))
    wins = [body[i:i + w] for i in range(0, max(1, len(body) - w), w // 2)]
    # a window of only words, spaces and commas is prose-like, not code (Lang_63 B: "years, months, days, hours,
    # minutes, seconds" listed in the spec matched the body's `format(tokens, years, months, ...)` call)
    return [x for x in wins if len(x.strip()) >= w // 2 and not re.fullmatch(r"[\w\s,]+", x) and x in t and x not in ctx]


# ---- parser / renderer: copied from m3_concept_spec/spec.py (spec arm only), unchanged in behaviour
def parse(reply):
    """JSON table from the last ```json block (or the outermost braces); None if it does not parse."""
    blocks = re.findall(r"```json\s*(.*?)```", reply, re.DOTALL)
    text = blocks[-1] if blocks else reply[reply.find("{"):reply.rfind("}") + 1]
    try:
        obj = json.loads(text)
    except ValueError:
        try:
            obj = json.loads(re.sub(r",\s*([}\]])", r"\1", text))  # trailing commas
        except ValueError:
            return None
    if not isinstance(obj, dict):
        return None
    spec = {"purpose": str(obj.get("purpose", "")).strip()}
    for k, _, _ in FACETS:
        v = obj.get(k, "not applicable")
        na = lambda x: str(x).lower().strip(" .") in ("not applicable", "n/a")
        rules = [r for r in v if isinstance(r, dict) and str(r.get("input", "")).strip() and not na(r["input"]) and not na(r.get("expected"))] \
            if isinstance(v, list) else []
        exp = lambda r: "unspecified" if r.get("expected") is None else str(r["expected"]).strip() or '""'
        spec[k] = [{"input": str(r["input"]).strip(), "expected": exp(r), "source": str(r.get("source", "")).strip()} for r in rules] or "not applicable"
    spec["missing_keys"] = [k for k, _, _ in FACETS if k not in obj]
    return spec


def is_unspecified(rule):
    return rule["expected"].lower().strip(" .\"'") in ("unspecified", "not specified", "undefined")


def render(spec):
    """Javadoc-style docstring: purpose, one section per facet (input -> expected), then the unspecified cases."""
    clean = lambda s: s.strip().replace("*/", "* /").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    lines, unspec = [clean(spec["purpose"]) or "Specification.", ""], []
    for k, name, _ in FACETS:
        rules = spec[k] if isinstance(spec[k], list) else []
        known = [r for r in rules if not is_unspecified(r)]
        unspec += [f"{name}: {clean(r['input'])}" for r in rules if is_unspecified(r)]
        if known:
            lines.append(name[0].upper() + name[1:] + ":")
            lines += [f"  - {clean(r['input'])} → {clean(r['expected'])}" for r in known]
    if unspec:
        lines.append("Unspecified (do not assume):")
        lines += [f"  - {u}" for u in unspec]
    while lines[-1] == "":
        lines.pop()
    return "\n/**\n" + "\n".join(f" * {l}".rstrip() for l in lines) + "\n */\n"


def generate(arm, idx):
    from gemini_shim import GeminiChat
    chat = GeminiChat()
    records = [json.loads(l) for l in open(SRC)]
    path = f"{OUT}/specs_{arm}.jsonl"
    done = {r["idx"]: {**r, "spec": parse(r["reply"])} for r in map(json.loads, open(path))} if os.path.exists(path) else {}
    todo = [i for i in (idx or range(len(records))) if not (i in done and done[i]["spec"])]  # retry cached failures

    def one(i):
        prompt, calls = build_prompt(records[i], arm), 0
        assert not body_leaks(records[i], prompt), f"focal body in prompt {i}"
        # same re-ask policy as m3: re-ask only an unparsable reply, with T>0 (T=0 repeats it); max_tokens caps loops
        for temp in ((1.0, 1.0, 1.0) if i in done else (0, 0.5, 0.5)):
            calls += 1
            reply = chat.chat.completions.create(messages=[{"role": "user", "content": prompt}], temperature=temp,
                                                 max_tokens=10000).choices[0].message.content
            spec = parse(reply)
            if spec:
                break
        return {"idx": i, "id": records[i]["extra:project_name"], "method_signature": records[i]["source:source_method_signature"],
                "calls": calls + done.get(i, {}).get("calls", 0), "temperature": temp, "prompt": prompt, "reply": reply, "spec": spec}

    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(4) as ex, open(path, "a") as f:
        for res in ex.map(one, todo):
            f.write(json.dumps(res) + "\n"); f.flush()
            done[res["idx"]] = res
            print(res["idx"], res["id"], "calls", res["calls"], "ok" if res["spec"] else "PARSE FAILED", flush=True)
    with open(path, "w") as f:  # rewrite sorted, with every spec parsed by the current parser
        f.writelines(json.dumps(done[i]) + "\n" for i in sorted(done))
    sel = idx or range(len(records))
    assert all(done[i]["spec"] for i in sel), "some specs failed to parse"
    out = DOC_OUT.format(arm + ("_smoke" if idx else ""))
    with open(out, "w") as f:
        for i in sel:
            doc = render(done[i]["spec"])
            assert not body_leaks(records[i], doc), f"focal body in docstring {i}"
            f.write(json.dumps({**records[i], "generated_docstring": doc}) + "\n")
    print("wrote", out)


def javadoc_check():
    """extracted Javadoc vs the dataset's source:source_method_docstring, and body-leak checks of every prompt."""
    records = [json.loads(l) for l in open(SRC)]
    norm = lambda s: re.sub(r"[\s*]+", " ", s).strip()
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/javadoc.jsonl", "w") as f:
        for i, r in enumerate(records):
            jd, ds = javadoc(r), r["source:source_method_docstring"]
            prompts = {a: build_prompt(r, a) for a in ARMS}
            row = {"idx": i, "id": r["extra:project_name"], "declaration": declaration(r), "javadoc": jd, "dataset_docstring": ds,
                   "same_as_dataset": norm(jd) == norm(ds), "javadoc_body_leaks": body_leaks(r, jd),
                   "prompt_body_leaks": {a: body_leaks(r, p) for a, p in prompts.items()},
                   "prompt_chars": {a: len(p) for a, p in prompts.items()}}
            f.write(json.dumps(row) + "\n")
            flag = "" if row["same_as_dataset"] else "  DIFFERS from dataset docstring"
            print(i, row["id"], row["declaration"][:90], f"javadoc {len(jd)} chars{flag}",
                  "LEAK" if row["javadoc_body_leaks"] or any(row["prompt_body_leaks"].values()) else "")


def selftest():
    reply = 'analysis...\n```json\n{"purpose": "Joins */ items.", "C0": [{"input": "[\\"a\\",\\"b\\"], sep \';\'", "expected": "\\"a;b\\"", "source": "name-context"}], ' \
            '"C1": [{"input": "array null", "expected": "null", "source": "framework"}, {"input": "null element", "expected": "unspecified", "source": "assumed"}], ' \
            '"C2": "not applicable", "C6": [{"input": "not applicable", "expected": "not applicable"}], "C7": [{"input": "\\"a  b\\tc\\"", "expected": "x"}], "C8": [{"input": "e", "expected": ""}, {"input": "f"}],}\n```'
    s = parse(reply)
    assert s and s["C2"] == "not applicable" and s["C3"] == "not applicable" and s["C6"] == "not applicable" and s["missing_keys"] == ["C3", "C4", "C5"]
    d = render(s)
    assert d.startswith("\n/**\n * Joins * / items.\n *\n * Core logic:\n") and "→ \"a;b\"" in d
    assert " * Unspecified (do not assume):\n *   - null input: null element\n *   - state/mutation/idempotence: f\n */\n" in d and "Empty" not in d and 'e → ""' in d and '"a  b\\tc" → x' in d
    assert parse("no json here") is None
    rec = {"source:source_method_code_format": "int f(int a) {\n  return a + 1000000 * someLongName(a, a, a);\n}"}
    assert body_leaks(rec, "x return a + 1000000 * someLongName(a, a, a); y") and not body_leaks(rec, "int f(int a);")
    for a in ARMS:
        pf = build_postfix(a)
        assert ("javadoc" in pf) == (a == "blind_concept_javadoc") and "C8 state/mutation/idempotence" in pf and "{jd" not in pf
    print(d, "selftest ok")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    elif sys.argv[1] == "javadoc":
        javadoc_check()
    else:
        assert sys.argv[1] in ARMS
        generate(sys.argv[1], [int(i) for i in sys.argv[2:]])
