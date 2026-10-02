"""Concept-Spec: one LLM call per focal method turns the buggy-code context into a JSON spec table with one section per
facet, then a deterministic renderer turns the table into a Javadoc-style docstring for the unchanged Only Doc pipeline.

arms: spec    = C0 core logic + the shared bug-concept vocabulary C1-C8
      placebo = C0 core logic + eight bug-irrelevant facets P1-P8 (same skeleton, same JSON format, same renderer)

usage (in the container): python3 m3_concept_spec/spec.py <spec|placebo> [idx ...]
writes m3_concept_spec/out/specs_<arm>.jsonl (one line per method: idx, id, signature, calls, reply, spec; also the
resume cache) and data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m3_concept_<arm>[_smoke].jsonl
(source records + rendered `generated_docstring`; `_smoke` when idx are given).
`python3 m3_concept_spec/spec.py selftest` checks the parser and renderer (no LLM, runs on the host too).
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run"]
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
OUT = f"{REPO}/m3_concept_spec/out"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m3_concept_{}.jsonl"

CORE = ("C0", "core logic", "the main functional behaviour on typical, valid inputs")
FACETS = {
    "spec": [CORE,
                ("C1", "null input", "behaviour when an argument, a field it depends on, or an element inside an argument is null"),
                ("C2", "empty/blank input", "behaviour for empty strings, whitespace-only strings, and empty arrays or collections"),
                ("C3", "boundary/index/length", "behaviour at the edges of the valid range: first and last index, lengths 0, 1 and the maximum, limits reached exactly or exceeded by one"),
                ("C4", "error contract", "which invalid inputs raise which exception type, and which situations return an error value (such as null, -1 or false) instead"),
                ("C5", "escaping/normalisation/format", "handling of special or reserved characters, escape sequences, whitespace or case normalisation, and the exact format of produced or accepted text"),
                ("C6", "numeric range/overflow/precision", "behaviour for very large, very small, negative or zero numbers, overflow, rounding and floating-point precision"),
                ("C7", "characters/locale/unicode", "behaviour for non-ASCII characters, supplementary (surrogate-pair) characters, case conversion and locale-dependent input"),
                ("C8", "state/mutation/idempotence", "effects on the object's or the arguments' state, repeated or consecutive calls, and whether returned objects are shared or copies")],
    "placebo": [CORE,
                ("P1", "naming", "how the method, its parameters and its return value are named, and whether these names follow the conventions of the surrounding class"),
                ("P2", "documentation", "which parts of the method's behaviour are documented for callers, and how the parameters and the return value are described"),
                ("P3", "performance", "the expected time and memory cost for small and large inputs, and whether results are cached or recomputed"),
                ("P4", "thread-safety", "whether the method may be called concurrently from several threads, and what synchronisation the callers need"),
                ("P5", "logging", "whether the method writes log messages or console output, at which level, and what information they contain"),
                ("P6", "API stability", "whether the method is part of the public API, whether it may change in future versions, and its deprecation status"),
                ("P7", "readability", "how easy the method is to read and maintain: its length, its structure and the clarity of its steps"),
                ("P8", "dependencies", "which other classes, methods and libraries the method relies on, and which callers rely on it")],
}

POSTFIX = """Please assume the role of an expert software engineer performing a critical code review. Your task is to produce a two-part response: a detailed analysis, and a structured specification that captures the method's intended requirement.

**Part 1: Critical Analysis**
First, provide your analysis by completing the following sections. For each point, state your findings clearly. If no issues are found in a category, you must explicitly state "No issues found."

1.  **Logical Mistakes:** Scrutinize the algorithm's logic. Based on the method's name and context, does its implementation correctly achieve its apparent goal, or are there logical flaws that would produce an incorrect result even on a "happy path"?
2.  **Robustness Omissions:** Check for missing but necessary steps that production-quality code would include. This includes, but is not limited to, input validation (e.g., null checks, boundary conditions), proper error handling, and necessary data sanitization or escaping.
Your analysis should be very detailed and step by step for the given code, make sure you clearly write out your entire analysis.

**Part 2: Structured Specification**
Based on your analysis in Part 1, specify the method's intended behaviour (what a correct implementation must do, not what the given code happens to do). Go through every facet below and take a position on each one:

{facets}

Output the specification as a single JSON object inside one ```json markdown block, with exactly these keys:
{{"purpose": "<one sentence stating what the method is for>", {keys}}}
The value of each facet key is either the string "not applicable" (only when the facet cannot arise for this method) or a list of rules. Each rule is an object:
{{"input": "<a class of inputs or situations, with concrete example inputs>", "expected": "<the expected outcome for that class: return value, exception type, resulting state, or other observable property; or \\"unspecified\\">", "source": "<name-context | type | framework | assumed>"}}
- "source" says where the expectation comes from: "name-context" = the method, parameter and class names and the surrounding class; "type" = the Java types in the signature; "framework" = documented conventions of Java or of this library; "assumed" = your best judgement without such evidence.
- When the intended behaviour for an input class cannot be determined, write "expected": "unspecified" rather than guessing. Unspecified rules are welcome.
- Give concrete example inputs and concrete expected values wherever possible.
- State each expected outcome as a caller would observe it. Do not mention the code's variables, statements or internal steps, and do not justify an outcome by how the given code computes it.
- Please avoid directly quoting from the original focal method code, as it might be buggy.
"""


def build_postfix(arm):
    fs = FACETS[arm]
    facets = "\n".join(f"- {k} {name}: {d}." for k, name, d in fs)
    keys = ", ".join(f'"{k}": [...]' for k, _, _ in fs)
    return POSTFIX.format(facets=facets, keys=keys)


def build_prompt(record, arm):
    """The advanced-docstring context (buggy code + class context), with only the instruction postfix replaced."""
    from utils.prompt_formats.new_prompt_formatter import PromptFormatter, ADVANCED_SUMMARIZATION_POST_FIX_BASE
    _, p = PromptFormatter().apply_format_summarize(record, "chatgpt", strategy="generation", formatting="comment",
                                                     ignore_feature="full", project_name=record["extra:project_name"],
                                                     advanced_analysis=True)
    assert p.endswith(ADVANCED_SUMMARIZATION_POST_FIX_BASE)
    return p[:-len(ADVANCED_SUMMARIZATION_POST_FIX_BASE)] + build_postfix(arm)


def parse(reply, arm):
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
    for k, _, _ in FACETS[arm]:
        v = obj.get(k, "not applicable")
        na = lambda x: str(x).lower().strip(" .") in ("not applicable", "n/a")
        rules = [r for r in v if isinstance(r, dict) and str(r.get("input", "")).strip() and not na(r["input"]) and not na(r.get("expected"))] \
            if isinstance(v, list) else []
        # a missing/null expectation is unspecified; an empty string is the value "" (e.g. "returns the empty string")
        exp = lambda r: "unspecified" if r.get("expected") is None else str(r["expected"]).strip() or '""'
        spec[k] = [{"input": str(r["input"]).strip(), "expected": exp(r), "source": str(r.get("source", "")).strip()} for r in rules] or "not applicable"
    spec["missing_keys"] = [k for k, _, _ in FACETS[arm] if k not in obj]
    return spec


def is_unspecified(rule):
    return rule["expected"].lower().strip(" .\"'") in ("unspecified", "not specified", "undefined")


def render(spec, arm):
    """Javadoc-style docstring: purpose, one section per facet (input -> expected), then the unspecified cases."""
    clean = lambda s: s.strip().replace("*/", "* /").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    lines, unspec = [clean(spec["purpose"]) or "Specification.", ""], []
    for k, name, _ in FACETS[arm]:
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
    done = {r["idx"]: {**r, "spec": parse(r["reply"], arm)} for r in map(json.loads, open(path))} if os.path.exists(path) else {}
    todo = [i for i in (idx or range(len(records))) if not (i in done and done[i]["spec"])]  # retry cached failures

    def one(i):
        prompt, calls = build_prompt(records[i], arm), 0
        # re-ask only when the reply has no parsable JSON table; at T=0 a re-ask repeats the same (often degenerate,
        # repetition-loop) reply, so the re-asks use T>0. max_tokens caps runaway loops (normal replies < 5k tokens).
        # A rerun of a cached failure (first run: T 0, 0.5, 0.5) goes on with T=1.0.
        for temp in ((1.0, 1.0, 1.0) if i in done else (0, 0.5, 0.5)):
            calls += 1
            reply = chat.chat.completions.create(messages=[{"role": "user", "content": prompt}], temperature=temp,
                                                 max_tokens=10000).choices[0].message.content
            spec = parse(reply, arm)
            if spec:
                break
        return {"idx": i, "id": records[i]["extra:project_name"], "method_signature": records[i]["source:source_method_signature"],
                "calls": calls + done.get(i, {}).get("calls", 0), "temperature": temp, "reply": reply, "spec": spec}

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
    with open(DOC_OUT.format(arm + ("_smoke" if idx else "")), "w") as f:
        for i in sel:
            f.write(json.dumps({**records[i], "generated_docstring": render(done[i]["spec"], arm)}) + "\n")
    print("wrote", DOC_OUT.format(arm + ("_smoke" if idx else "")))


def selftest():
    reply = 'analysis...\n```json\n{"purpose": "Joins */ items.", "C0": [{"input": "[\\"a\\",\\"b\\"], sep \';\'", "expected": "\\"a;b\\"", "source": "name-context"}], ' \
            '"C1": [{"input": "array null", "expected": "null", "source": "framework"}, {"input": "null element", "expected": "unspecified", "source": "assumed"}], ' \
            '"C2": "not applicable", "C6": [{"input": "not applicable", "expected": "not applicable"}], "C7": [{"input": "\\"a  b\\tc\\"", "expected": "x"}], "C8": [{"input": "e", "expected": ""}, {"input": "f"}],}\n```'
    s = parse(reply, "spec")
    assert s and s["C2"] == "not applicable" and s["C3"] == "not applicable" and s["C6"] == "not applicable" and s["missing_keys"] == ["C3", "C4", "C5"]
    d = render(s, "spec")
    assert d.startswith("\n/**\n * Joins * / items.\n *\n * Core logic:\n") and "→ \"a;b\"" in d
    assert " * Unspecified (do not assume):\n *   - null input: null element\n *   - state/mutation/idempotence: f\n */\n" in d and "Empty" not in d and 'e → ""' in d and '"a  b\\tc" → x' in d
    assert parse("no json here", "spec") is None
    print(d, "selftest ok")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    else:
        generate(sys.argv[1], [int(i) for i in sys.argv[2:]])
