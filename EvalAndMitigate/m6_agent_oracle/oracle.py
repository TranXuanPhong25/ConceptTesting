"""m6 agent oracle: neutral questions about intended behaviour -> an independent answering agent -> clarified spec.

1. questions (one LLM call per method, sees the buggy code, the Advanced docstring prompt's context and Part 1):
   at most MAX_Q neutral questions, each with a concrete input. A deterministic guard (`question_issues`) rejects
   questions that quote the body, name implementation-only identifiers or use wording such as "currently"; the method
   is re-asked once with the rejected questions listed, and questions that still fail are dropped.
2. answers (one LLM call per method and arm, identical prompt and evidence pack except the focal body):
   oracle_blind     = the evidence pack only (signature, declaration, method Javadoc, class Javadoc, constructors,
                      fields, other signatures, same-name methods in the file, mentions in the MAIN source dir)
   oracle_sees_code = the same pack + the focal method body
3. docs: the Advanced docstring unchanged + "Clarified requirements" (input -> expected) + "Undetermined (do not assume)".

usage (container unless noted):
  python3 m6_agent_oracle/oracle.py evidence            -> out/evidence.jsonl (needs the d4jproj volume)
  python3 m6_agent_oracle/oracle.py questions [idx ...] -> out/questions.jsonl
  python3 m6_agent_oracle/oracle.py answers <arm> [idx ...] -> out/answers_<arm>.jsonl
  python3 m6_agent_oracle/oracle.py docs <arm> [idx ...] -> data/prompts/..._with_m6_<arm>[_smoke].jsonl (host ok)
  python3 m6_agent_oracle/oracle.py selftest            -> guard / parser / renderer checks (host ok)
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, f"{REPO}/run"]
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
ADV = f"{REPO}/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"
JAVADOC = f"{REPO}/m5_blind_concept_spec/out/javadoc.jsonl"  # m5's re-extracted method Javadoc (buggy class code)
OUT = f"{REPO}/m6_agent_oracle/out"
DOC_OUT = REPO + "/data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m6_{}.jsonl"
ARMS = ("oracle_blind", "oracle_sees_code")

MAX_Q = 6
CTX = 5                      # caller snippets: +-5 lines around each mention
MAX_CALLERS = 8              # caller snippets per method (after merging overlapping windows)
MAX_CALLER_CHARS = 8000      # total chars of caller snippets per method
MAX_OVERLOADS = 6            # same-name methods per method
MAX_OVERLOAD_CHARS = 2500    # per same-name method (Javadoc + code), truncated beyond
MAX_OVERLOADS_TOTAL = 8000   # total chars of same-name methods per method
SOURCES = ("javadoc", "caller", "overload", "class_context", "naming", "standard", "implementation")


def load_records():
    return [json.loads(l) for l in open(SRC)]


# ---- copied from m5_blind_concept_spec/spec.py (unchanged)
_PARSER = None


def parser():
    global _PARSER
    if _PARSER is None:
        from data.configuration import JAVA_LANGUAGE
        from tree_sitter import Parser
        _PARSER = Parser(); _PARSER.set_language(JAVA_LANGUAGE)
    return _PARSER


def focal_node(record):
    """tree-sitter node of the focal method inside the buggy class code (the body occurs exactly once there)."""
    code, body = record["content:source_class_code_format"].encode(), record["source:source_method_code_format"].encode()
    assert code.count(body) == 1
    s = code.find(body)
    n = parser().parse(code).root_node.descendant_for_byte_range(s, s + len(body))
    while n.type not in ("method_declaration", "constructor_declaration"):
        n = n.parent
    assert (n.start_byte, n.end_byte) == (s, s + len(body))
    return n


def declaration(record):
    """modifiers, type parameters, return type, name, parameters, throws: the method text before its body block."""
    n = focal_node(record)
    b = n.child_by_field_name("body")
    return re.sub(r"\s+", " ", n.text[:b.start_byte - n.start_byte].decode()).strip() + ";"


CONTEXT_KEYS = ("source:source_other_method_signature", "source_class_fields", "content:source_class_constructors",
                "content:parameter_class_constructors", "content:return_type_class_constructors")


def body_leaks(record, text, w=40):
    """whitespace-normalised windows (w chars, stride w/2) of the focal body *after* its declaration found in text,
    except windows that also occur in the upstream non-body context and windows made only of words, spaces, commas."""
    norm = lambda s: re.sub(r"\s+", " ", s)
    body = norm(record["source:source_method_code_format"])
    body = body[body.find("{") + 1:]
    t, ctx = norm(text), norm("\n".join(x for k in CONTEXT_KEYS for x in record.get(k, [])))
    wins = [body[i:i + w] for i in range(0, max(1, len(body) - w), w // 2)]
    return [x for x in wins if len(x.strip()) >= w // 2 and not re.fullmatch(r"[\w\s,]+", x) and x in t and x not in ctx]
# ----


def method_range(lines, body):
    """0-based [start, end] line range of the method in the file (stripped line sequence match; m2 labels.py)."""
    want = [l.strip() for l in body.splitlines() if l.strip()]
    have = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]
    for k in range(len(have) - len(want) + 1):
        if have[k][1] == want[0] and [h for _, h in have[k:k + len(want)]] == want:
            return have[k][0], have[k + len(want) - 1][0]
    return None


def dedent(lines):
    ind = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return "\n".join(l[ind:].rstrip() for l in lines)


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------- 1. evidence (container)
def collect(record, jd, cache):
    """evidence for one focal method from the buggy checkout's main source dir (never the test dir)."""
    bug = record["extra:project_name"].replace("_buggy", "")
    d = f"{REPO}/d4j_proj_base/{bug}/buggy"
    if bug not in cache:
        src = sh(["defects4j", "export", "-p", "dir.src.classes"], d).stdout.strip()
        tests = sh(["defects4j", "export", "-p", "dir.src.tests"], d).stdout.strip()
        assert src and tests and not src.startswith(tests) and not tests.startswith(src), (bug, src, tests)
        files = [f for f in sh(["git", "ls-files", "--", src], d).stdout.split() if f.endswith(".java")]
        assert files and not any(f.startswith(tests + "/") for f in files)
        clean = sh(["git", "diff", "--quiet", "HEAD", "--", src], d).returncode == 0  # tracked main sources unmodified
        cache[bug] = (src, tests, files, clean, {})
    src, tests, files, clean, texts = cache[bug]
    read = lambda f: texts.setdefault(f, open(f"{d}/{f}", encoding="utf-8", errors="replace").read())

    sig, name, body = record["source:source_method_signature"], record["source:source_method_name"], record["source:source_method_code_format"]
    pkg, cls = sig.split("#")[0].replace(".", "/"), sig.split("#")[1]
    hits = [(f, method_range(read(f).splitlines(), body)) for f in files if f.startswith(f"{src}/{pkg}/") and "/" not in f[len(src) + len(pkg) + 2:]]
    hits = [(f, r) for f, r in hits if r]
    assert len(hits) == 1, (record["extra:project_name"], name, hits)
    ffile, (fs, fe) = hits[0]
    flines = read(ffile).splitlines()

    # same-name methods in the focal file (overloads, and same-name methods of nested classes), with their Javadoc
    tree = parser().parse(read(ffile).encode())
    nodes, stack = [], [tree.root_node]
    while stack:
        n = stack.pop()
        stack += n.children
        if n.type in ("method_declaration", "constructor_declaration") and n.child_by_field_name("name").text.decode() == name:
            nodes.append(n)
    nparams = lambda n: len([c for c in n.child_by_field_name("parameters").children if c.type in ("formal_parameter", "spread_parameter")])
    focal = [n for n in nodes if n.start_point[0] <= fs <= n.end_point[0]]
    assert len(focal) == 1, (record["extra:project_name"], name)
    others = sorted((n for n in nodes if n is not focal[0]), key=lambda n: (abs(nparams(n) - nparams(focal[0])), n.start_point[0]))
    overloads, ranges, total = [], [], 0
    for n in others[:MAX_OVERLOADS]:
        p = n.prev_sibling
        start = p.start_point[0] if p is not None and p.type == "block_comment" and p.text.startswith(b"/**") else n.start_point[0]
        text = dedent(flines[start:n.end_point[0] + 1])
        if len(text) > MAX_OVERLOAD_CHARS:
            text = text[:MAX_OVERLOAD_CHARS] + "\n... (truncated)"
        if total + len(text) > MAX_OVERLOADS_TOTAL:
            break
        decl = re.sub(r"\s+", " ", n.text[:n.child_by_field_name("body").start_byte - n.start_byte].decode()).strip() if n.child_by_field_name("body") else ""
        overloads.append({"file": ffile, "start": start + 1, "end": n.end_point[0] + 1, "declaration": decl, "text": text})
        ranges.append((start, n.end_point[0])); total += len(text)

    # mentions of `name(` in the main source dir, excluding the focal method (with its Javadoc) and the included same-name methods
    p = focal[0].prev_sibling
    focal_lo = p.start_point[0] if p is not None and p.type == "block_comment" and p.text.startswith(b"/**") else focal[0].start_point[0]
    pat = re.compile(r"(?<![\w$])" + re.escape(name) + r"\s*\(")
    cands = []
    for f in files:
        txt = read(f)
        if not pat.search(txt):
            continue
        mentions_cls = re.search(r"(?<![\w$])" + re.escape(cls) + r"(?![\w$])", txt) is not None
        for ln, line in enumerate(txt.splitlines()):
            if f == ffile and (focal_lo <= ln <= fe or any(a <= ln <= b for a, b in ranges)):
                continue
            for m in pat.finditer(line):
                q = re.search(r"([\w$]+)\s*\.\s*$", line[:m.start()])
                qual = q.group(1) if q else None
                if f == ffile:
                    rank = 0 if qual in (None, "this", cls) else 3
                else:
                    rank = 1 if qual == cls else 2 if mentions_cls else 4
                cands.append((rank, f, ln))
                break
    cands.sort(key=lambda c: (c[0], c[1] != ffile, c[1], c[2]))
    windows = []  # [rank, file, lo, hi] merged per file
    for rank, f, ln in cands:
        lo, hi = max(0, ln - CTX), min(len(read(f).splitlines()) - 1, ln + CTX)
        if f == ffile:  # never show any line of the focal method
            lo, hi = (lo, min(hi, focal_lo - 1)) if ln < focal_lo else (max(lo, fe + 1), hi)
        for w in windows:
            if w[1] == f and lo <= w[3] + 1 and hi >= w[2] - 1:
                w[2], w[3] = min(w[2], lo), max(w[3], hi)
                break
        else:
            windows.append([rank, f, lo, hi])
    callers, total, n_cands = [], 0, len(cands)
    for rank, f, lo, hi in windows:
        if len(callers) >= MAX_CALLERS:
            break
        text = dedent(read(f).splitlines()[lo:hi + 1])
        if total + len(text) > MAX_CALLER_CHARS:
            continue
        callers.append({"file": f, "start": lo + 1, "end": hi + 1, "rank": rank, "text": text}); total += len(text)

    # strict blindness: drop any same-name method or snippet that shares a 40-char window with the focal body
    dropped = [x for x in overloads + callers if body_leaks(record, x["text"])]
    overloads = [x for x in overloads if x not in dropped]
    callers = [x for x in callers if x not in dropped]
    assert all(x["file"].startswith(src + "/") for x in overloads + callers)
    return {"bug": bug, "src_dir": src, "test_dir": tests, "src_unmodified": clean, "file": ffile, "focal_lines": [focal_lo + 1, fe + 1],
            "signature": sig, "declaration": declaration(record), "javadoc": jd, "class_javadoc": (record.get("content:source_class_docstring") or "").strip(),
            "class": cls, "name": name, "overloads": overloads, "callers": callers, "mentions_found": n_cands,
            "dropped_for_body_overlap": [{k: x[k] for k in ("file", "start", "end")} for x in dropped]}


def uniq(xs):
    return list(dict.fromkeys(x.strip() for x in xs or [] if x.strip()))


def render_pack(record, ev, with_body):
    """the evidence pack shown to the answerer; with_body adds the focal implementation (sees-code arm only)."""
    p = ["// The method in question. Fully qualified signature:", ev["signature"], "// Declaration:", ev["declaration"], "",
         "// The method's Javadoc comment:", ev["javadoc"] or "(the method has no Javadoc comment)", ""]
    if with_body:
        p += ["// The method's implementation:", record["source:source_method_code_format"].strip(), ""]
    p += [f"// The Javadoc comment of the class {ev['class']}:", ev["class_javadoc"] or "(none)", "",
          "// Constructors of the class:", *(uniq(record.get("content:source_class_constructors")) or ["(none listed)"]), "",
          "// Fields of the class:", *(uniq(record.get("source_class_fields")) or ["(none listed)"]), "",
          "// Other methods of the class (signatures only):", *(uniq(record.get("source:source_other_method_signature")) or ["(none listed)"]), ""]
    p.append(f"// Other methods named {ev['name']} in the same source file (overloads), with their Javadoc and code:")
    p += [f"// [{k}] {o['file']}:{o['start']}-{o['end']}\n{o['text']}" for k, o in enumerate(ev["overloads"], 1)] or ["(none)"]
    p += ["", f"// Places in the library's main source code that mention {ev['name']}( (+-{CTX} lines each; the method itself is excluded):"]
    p += [f"// [{k}] {c['file']}:{c['start']}-{c['end']}\n{c['text']}" for k, c in enumerate(ev["callers"], 1)] or ["(none)"]
    return "```\n" + "\n".join(p) + "\n```\n"


def evidence():
    records = load_records()
    jds = {r["idx"]: r["javadoc"] for r in map(json.loads, open(JAVADOC))}
    cache = {}
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/evidence.jsonl", "w") as f:
        for i, r in enumerate(records):
            ev = {"idx": i, "id": r["extra:project_name"], **collect(r, jds[i], cache)}
            blind = render_pack(r, ev, False)
            ev["blind_pack_body_leaks"] = body_leaks(r, blind)
            ev["blind_pack_chars"] = len(blind)
            assert not ev["blind_pack_body_leaks"], (i, ev["blind_pack_body_leaks"])
            f.write(json.dumps(ev) + "\n")
            print(i, ev["id"], ev["name"], "overloads", len(ev["overloads"]), "callers", len(ev["callers"]), "of", ev["mentions_found"],
                  "dropped", len(ev["dropped_for_body_overlap"]), "chars", len(blind), "" if ev["src_unmodified"] else "SRC MODIFIED", flush=True)


def load_evidence():
    return {e["idx"]: e for e in map(json.loads, open(f"{OUT}/evidence.jsonl"))}


# ---------------------------------------------------------------- 2. questions (container, LLM)
QUESTION_POSTFIX = """Please assume the role of an expert software engineer performing a critical code review. Your task is to produce a two-part response: a detailed analysis, and a short list of questions about the method's intended behaviour that you would ask the method's author.

{part1}
**Part 2: Questions about the Intended Behaviour**
Based on your analysis in Part 1, write at most {max_q} questions for the method's author about the intended behaviour on input classes that are ambiguous or bug-prone (for example null, empty, boundaries, the error contract, formatting or escaping, special characters or locale, numeric range, state and repeated calls). The author will answer them without seeing the code above, so:
- Each question asks what a correct implementation must do for one concrete input: give the concrete call or argument values (and the object state, if it matters).
- Ask neutrally. Do not state, quote or hint at what the given code does, do not mention its local variables, loops, branches or conditions, and do not suggest which answer is expected. Phrase each question as "What should ... return / do when ...?".
- Prefer the input classes where you suspect a logical mistake or a robustness omission.
Output the questions as a single JSON object inside one ```json markdown block:
{{"questions": [{{"id": "Q1", "concept": "<C0 core logic | C1 null | C2 empty | C3 boundary | C4 error contract | C5 format | C6 numeric | C7 characters/locale | C8 state>", "input": "<the concrete call or input>", "question": "<the neutral question>"}}]}}
"""

RETRY_NOTE = """
Note: a previous answer to this request contained the questions below, which were rejected because they are not neutral (they state, quote or hint at what the given code does, or name identifiers that only occur inside the method's code). Write the full list again and phrase every question neutrally.
{rejected}
"""

# wording that states or hints at what the code does (checked on question + input, case-insensitive)
WORDING = re.compile(
    r"\b(currently|at present|right now|as (it is )?(implemented|written|coded)|implementation|implemented|the (given |provided |original |existing |current )?"
    r"(code|loop|condition|branch|check|snippet|body|statement|logic)\b|existing behaviou?r|line \d+|bug\w*|incorrect\w*|correctly|wrong\w*|"
    r"mistake\w*|flaw\w*|instead|still|(the|this) (method|function|code) (\w+ly )?(returns|throws|uses|checks|calls|iterates|compares|converts|ignores|"
    r"skips|treats|handles|does|only|always|never)\b|it (currently |only |always |never )?(returns|throws|ignores|skips|treats))", re.I)
CODE_ID = re.compile(r"(?<![\w$])([A-Za-z_$][\w$]*)(?![\w$])")


def code_like(tok):
    return bool(re.search(r"[a-z][A-Z]", tok) or ("_" in tok.strip("_") and len(tok) >= 3)) and not re.search(r"(Exception|Error)$", tok)


def question_issues(record, q, context):
    """reasons why a question is not neutral (empty = accepted)."""
    text = f"{q.get('input', '')} {q.get('question', '')}"
    out = []
    if not str(q.get("input", "")).strip() or not str(q.get("question", "")).strip():
        out.append("missing input or question")
    if body_leaks(record, text):
        out.append("quotes the code")
    m = WORDING.search(text)
    if m:
        out.append(f"wording '{m.group()}'")
    body_ids = set(CODE_ID.findall(record["source:source_method_code_format"]))
    ctx_ids = set(CODE_ID.findall(context))
    ids = sorted({t for t in CODE_ID.findall(text) if code_like(t) and t in body_ids and t not in ctx_ids})
    if ids:
        out.append("names identifiers that only occur in the code: " + ", ".join(ids))
    return out


def question_prompt(record):
    from utils.prompt_formats.new_prompt_formatter import PromptFormatter, ADVANCED_SUMMARIZATION_POST_FIX_BASE as POST
    _, p = PromptFormatter().apply_format_summarize(record, "chatgpt", strategy="generation", formatting="comment", ignore_feature="full",
                                                    project_name=record["extra:project_name"], advanced_analysis=True)
    assert p.endswith(POST)
    part1 = POST[POST.index("**Part 1: Critical Analysis**"):POST.index("**Part 2: Corrected Implementation**")]
    return p[:-len(POST)] + QUESTION_POSTFIX.format(part1=part1, max_q=MAX_Q)


def last_json(reply):
    blocks = re.findall(r"```json\s*(.*?)```", reply, re.DOTALL)
    text = blocks[-1] if blocks else reply[reply.find("{"):reply.rfind("}") + 1]
    t2 = re.sub(r",\s*([}\]])", r"\1", text)
    # trailing commas; invalid JSON escapes from quoted Java code such as \' (Gson_7 sees-code reply)
    fix = re.sub(r"\\(.)", lambda m: m.group(0) if m.group(1) in '\\"/bfnrtu' else "\\\\" + m.group(1), t2, flags=re.S)
    for t in (text, t2, fix):
        try:
            obj = json.loads(t)
            return obj if isinstance(obj, dict) else None
        except ValueError:
            pass
    return None


def parse_questions(reply):
    obj = last_json(reply)
    qs = obj.get("questions") if obj else None
    if not isinstance(qs, list):
        return None
    return [{"concept": str(q.get("concept", "")).strip(), "input": str(q.get("input", "")).strip(), "question": str(q.get("question", "")).strip()}
            for q in qs if isinstance(q, dict)]


def run_pool(path, todo, one, key):
    """runs one(i) for every i not yet in path; a cached record whose `key` is None (unparsable reply) is redone and
    its earlier calls are added to the new record's count."""
    done = {r["idx"]: r for r in map(json.loads, open(path))} if os.path.exists(path) else {}
    prior = {i: done.pop(i)["calls"] for i in list(done) if done[i][key] is None}
    todo = [i for i in todo if i not in done]
    one_ = one
    one = lambda i: (lambda r: {**r, "calls": r["calls"] + prior.get(i, 0)})(one_(i))
    if prior:
        with open(path, "w") as f:
            f.writelines(json.dumps(done[i]) + "\n" for i in sorted(done))
    with ThreadPoolExecutor(4) as ex, open(path, "a") as f:
        futs = {ex.submit(one, i): i for i in todo}
        for fut in as_completed(futs):
            try:
                res = fut.result()
            except Exception as e:  # e.g. 429 retries exhausted: not persisted, a rerun retries this method
                print(futs[fut], "FAILED", repr(e)[:200], flush=True)
                continue
            f.write(json.dumps(res) + "\n"); f.flush()
            done[res["idx"]] = res
            print(res["idx"], res["id"], "calls", res["calls"], res.get("status", ""), flush=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(done[i]) + "\n" for i in sorted(done))
    return done


def questions(idx):
    from gemini_shim import GeminiChat
    chat = GeminiChat().chat.completions
    records, evs = load_records(), load_evidence()

    def ask(prompt, temp):
        return chat.create(messages=[{"role": "user", "content": prompt}], temperature=temp, max_tokens=12000).choices[0].message.content

    def one(i):
        r = records[i]
        base, ctx = question_prompt(r), render_pack(r, evs[i], False) + "\n".join(x for k in CONTEXT_KEYS for x in r.get(k, []))
        attempts, calls, rejected = [], 0, []
        for note in ("", None):  # first ask; one re-ask with the rejected questions listed
            if note is None:
                if not rejected and attempts and attempts[-1]["parsed"]:
                    break
                note = RETRY_NOTE.format(rejected="\n".join(f"- {q['question']} [input: {q['input']}] ({'; '.join(why)})" for q, why in rejected)) if rejected else ""
            prompt = base + note
            qs = None
            for temp in (0, 0.5, 0.5):  # re-ask only an unparsable reply, with T>0 (T=0 repeats it)
                calls += 1
                reply = ask(prompt, temp)
                qs = parse_questions(reply)
                if qs is not None:
                    break
            checked = [(q, question_issues(r, q, ctx)) for q in (qs or [])[:MAX_Q]]
            attempts.append({"note": note, "temperature": temp, "reply": reply, "parsed": qs is not None,
                             "checked": [{**q, "issues": why} for q, why in checked]})
            rejected = [(q, why) for q, why in checked if why]
        # final: the attempt with more accepted questions (the re-ask on ties)
        best = max(reversed(attempts), key=lambda a: sum(not q["issues"] for q in a["checked"]))
        final = [{"id": f"Q{k}", **{x: q[x] for x in ("concept", "input", "question")}} for k, q in
                 enumerate((q for q in best["checked"] if not q["issues"]), 1)]
        return {"idx": i, "id": r["extra:project_name"], "method_signature": r["source:source_method_signature"], "calls": calls,
                "status": f"{len(final)} questions, {sum(bool(q['issues']) for a in attempts for q in a['checked'])} rejected",
                "prompt": base, "attempts": attempts, "questions": final}

    os.makedirs(OUT, exist_ok=True)
    done = run_pool(f"{OUT}/questions.jsonl", idx or range(len(records)), one, "questions")
    for i in idx or range(len(records)):
        assert done[i]["questions"], f"no question for {i}"


# ---------------------------------------------------------------- 3. answers (container, LLM)
ANSWER_PROMPT = """You are the author of the Java library that contains the method below. A colleague who writes unit tests for it asks you questions about its intended behaviour. Answer each question with what a correct implementation must do, using only the evidence below.

{pack}
Questions:
{questions}

Instructions:
- For each question, state the expected outcome for its input as the caller would observe it: return value, exception type, resulting state, or another observable property.
- Support every answer with evidence: one or more quotes copied verbatim from the material above (or the convention you rely on), each with its source type:
  "javadoc" (the method's or the class's Javadoc), "caller" (code in the library that calls or mentions the method), "overload" (Javadoc or code of a method with the same name), "class_context" (constructors, fields, other method signatures), "naming" (what the method, parameter or class names imply), "standard" (a documented convention of Java or of this library), "implementation" (the method's own implementation, only if it is shown above).
- If the evidence does not determine the expected outcome, write "UNDETERMINED" as the expected outcome instead of guessing. A plausible default that no evidence supports is a guess.
Output a single JSON object inside one ```json markdown block:
{{"answers": [{{"id": "Q1", "reasoning": "<one or two sentences>", "expected": "<the expected outcome, or UNDETERMINED>", "evidence": [{{"source": "<source type>", "quote": "<verbatim quote>"}}]}}]}}
"""


def answer_prompt(record, ev, qs, arm):
    qtext = "\n".join(f"{q['id']}. Input: {q['input']}\n    Question: {q['question']}" for q in qs)
    return ANSWER_PROMPT.format(pack=render_pack(record, ev, arm == "oracle_sees_code"), questions=qtext)


def is_undetermined(text):
    return not text.strip() or text.strip().strip("\"'").upper().startswith("UNDETERMINED")


def parse_answers(reply, qs):
    """{qid: answer}; a question without a parsable answer or without any evidence item counts as UNDETERMINED."""
    obj = last_json(reply)
    ans = obj.get("answers") if obj else None
    if not isinstance(ans, list):
        return None
    by_id = {str(a.get("id", "")).strip(): a for a in ans if isinstance(a, dict)}
    out = {}
    for q in qs:
        a = by_id.get(q["id"], {})
        ev = [{"source": (str(e.get("source", "")).strip().lower() if str(e.get("source", "")).strip().lower() in SOURCES else "other"),
               "quote": str(e.get("quote", "")).strip()} for e in a.get("evidence") or [] if isinstance(e, dict)]
        exp = str(a.get("expected", "")).strip()
        out[q["id"]] = {"expected": exp, "reasoning": str(a.get("reasoning", "")).strip(), "evidence": ev,
                        "missing": q["id"] not in by_id, "undetermined": is_undetermined(exp) or not ev}
    return out


def answers(arm, idx):
    from gemini_shim import GeminiChat
    chat = GeminiChat().chat.completions
    records, evs = load_records(), load_evidence()
    qs = {r["idx"]: r["questions"] for r in map(json.loads, open(f"{OUT}/questions.jsonl"))}

    def one(i):
        prompt, calls = answer_prompt(records[i], evs[i], qs[i], arm), 0
        if arm == "oracle_blind":
            assert not body_leaks(records[i], prompt), f"focal body in blind prompt {i}"
        for temp in (0, 0.5, 0.5):
            calls += 1
            reply = chat.create(messages=[{"role": "user", "content": prompt}], temperature=temp, max_tokens=12000).choices[0].message.content
            parsed = parse_answers(reply, qs[i])
            if parsed is not None:
                break
        return {"idx": i, "id": records[i]["extra:project_name"], "calls": calls, "temperature": temp, "prompt": prompt, "reply": reply,
                "answers": parsed, "status": "ok" if parsed is not None else "PARSE FAILED"}

    done = run_pool(f"{OUT}/answers_{arm}.jsonl", idx or range(len(records)), one, "answers")
    for i in idx or range(len(records)):
        assert done[i]["answers"] is not None, f"answers failed to parse for {i}"


# ---------------------------------------------------------------- 4. docstrings (host or container)
HEAD_CLARIFIED = "// Clarified requirements (answers to questions about the intended behaviour; input → expected):"
HEAD_UNDET = "// Undetermined (do not assume):"


def one_line(s):
    return s.strip().replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def render(qs, ans):
    known = [f"// - {one_line(q['input'])} → {one_line(ans[q['id']]['expected'])}" for q in qs if not ans[q["id"]]["undetermined"]]
    undet = [f"// - {one_line(q['input'])}: {one_line(q['question'])}" for q in qs if ans[q["id"]]["undetermined"]]
    out = "\n"
    if known:
        out += HEAD_CLARIFIED + "\n" + "\n".join(known) + "\n"
    if undet:
        out += HEAD_UNDET + "\n" + "\n".join(undet) + "\n"
    return out


def docs(arm, idx):
    records, adv = load_records(), [json.loads(l) for l in open(ADV)]
    qs = {r["idx"]: r["questions"] for r in map(json.loads, open(f"{OUT}/questions.jsonl"))}
    an = {r["idx"]: r["answers"] for r in map(json.loads, open(f"{OUT}/answers_{arm}.jsonl"))}
    sel = idx or range(len(records))
    out, leaks = DOC_OUT.format(arm + ("_smoke" if idx else "")), []
    with open(out, "w") as f:
        for i in sel:
            assert adv[i]["source:source_method_signature"] == records[i]["source:source_method_signature"]
            sec = render(qs[i], an[i])
            if body_leaks(records[i], sec):
                leaks.append(i)
            f.write(json.dumps({**adv[i], "generated_docstring": adv[i]["generated_docstring"] + sec}) + "\n")
    print("wrote", out, len(sel), "records; appended sections with a focal-body window:", leaks)
    assert arm != "oracle_blind" or not leaks


def selftest():
    rec = {"source:source_method_code_format": "int countDigits(String text) {\n  int seqEnd = text.length();\n  return seqEnd - 1 + helperCount(text, seqEnd);\n}",
           "source_class_fields": ["private int limit;"]}
    ok = {"input": 'countDigits("12a")', "question": "What should countDigits return for a string with a non-digit character?"}
    assert question_issues(rec, ok, "int countDigits(String text);") == []
    assert any("wording" in x for x in question_issues(rec, {"input": "null", "question": "The code currently returns 0; what should it return?"}, ""))
    assert any("identifiers" in x for x in question_issues(rec, {"input": "seqEnd = 3", "question": "What should happen?"}, ""))
    assert any("identifiers" in x for x in question_issues(rec, {"input": "x", "question": "Should helperCount be consulted?"}, ""))
    assert not question_issues(rec, {"input": 'countDigits(null)', "question": "Should it throw NullPointerException or return 0?"}, "int countDigits(String text);")
    assert any("quotes" in x for x in question_issues(rec, {"input": "x", "question": "int seqEnd = text.length(); return seqEnd - 1 + helperCount(text, seqEnd); ok?"}, ""))
    assert WORDING.search("as implemented") and WORDING.search("Should it still accept it?") and not WORDING.search("What should join(null, ',') return?")
    qs = parse_questions('x\n```json\n{"questions": [{"id": "Q1", "concept": "C1", "input": "f(null)", "question": "What should f(null) return?"},]}\n```')
    assert qs == [{"concept": "C1", "input": "f(null)", "question": "What should f(null) return?"}]
    qs = [{"id": "Q1", **qs[0]}, {"id": "Q2", "concept": "C2", "input": 'f("")', "question": "What should f(\"\") return?"},
          {"id": "Q3", "concept": "C3", "input": "f(\"a\nb\")", "question": "What should it do?"}]
    reply = '```json\n{"answers": [{"id": "Q1", "expected": "null", "evidence": [{"source": "javadoc", "quote": "@return null if null"}]},' \
            '{"id": "Q2", "expected": "UNDETERMINED", "evidence": []}, {"id": "Q3", "expected": "\\"a\\"", "evidence": []}]}\n```'
    a = parse_answers(reply, qs)
    assert not a["Q1"]["undetermined"] and a["Q2"]["undetermined"] and a["Q3"]["undetermined"]  # Q3: no evidence
    sec = render(qs, a)
    assert sec == f"\n{HEAD_CLARIFIED}\n// - f(null) → null\n{HEAD_UNDET}\n// - f(\"\"): What should f(\"\") return?\n// - f(\"a\\nb\"): What should it do?\n", sec
    assert last_json(r'''```json
{"a": "x = \'y\' \\'", "b": "\"q\"\n"}
```''') == {"a": "x = \\'y\\' \\'", "b": '"q"\n'}
    assert parse_answers("no json", qs) is None and is_undetermined("Undetermined.") and not is_undetermined("returns -1")
    print(sec, "selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "selftest":
        selftest()
    elif cmd == "evidence":
        evidence()
    elif cmd == "questions":
        questions([int(i) for i in sys.argv[2:]])
    elif cmd in ("answers", "docs"):
        assert sys.argv[2] in ARMS
        (answers if cmd == "answers" else docs)(sys.argv[2], [int(i) for i in sys.argv[3:]])
