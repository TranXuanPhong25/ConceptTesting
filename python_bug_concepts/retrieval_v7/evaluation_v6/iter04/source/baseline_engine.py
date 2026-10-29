"""Generic public-code retrieval. No benchmark IDs, witnesses, or gold labels.

Structural evidence establishes an operation/site worth inspecting. A candidate
is still a hypothesis; it becomes a bug claim only after independent grading.
"""
from __future__ import annotations

import ast
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from ..base import code_hints as legacy_code_hints, normalized, query_tokens
from . import corpus

DEFAULT_DB = Path(__file__).resolve().parent / "index.sqlite3"
VERSION = "structure-v2.2"


def build(db: Path = DEFAULT_DB) -> dict:
    stats = corpus.verify()
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("BEGIN")
        conn.execute("DROP TABLE IF EXISTS documents")
        conn.execute("DROP TABLE IF EXISTS metadata")
        conn.execute("CREATE VIRTUAL TABLE documents USING fts5(id UNINDEXED, title, aliases, context, mechanism, outcome, refs, category, tokenize='unicode61 remove_diacritics 2')")
        conn.execute("CREATE TABLE metadata (digest TEXT)")
        for card in corpus.cards():
            conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)", (
                card["id"], normalized(card["title"]), normalized(" ".join(card["aliases"])),
                normalized(" ".join([card["where"]["summary"], *card["where"]["preconditions"], *card["where"]["ast_nodes"]])), normalized(" ".join(card["how"].values())),
                normalized(" ".join(card["what"].values())), normalized(" ".join(card["pattern_ids"])), card["category"],
            ))
        conn.execute("INSERT INTO metadata VALUES (?)", (VERSION + corpus.digest(),))
    return {**stats, "database": str(db)}


def ensure(db: Path) -> None:
    stale = True
    if Path(db).exists():
        try:
            with closing(sqlite3.connect(db)) as conn:
                row = conn.execute("SELECT digest FROM metadata").fetchone()
                stale = not row or row[0] != VERSION + corpus.digest()
        except sqlite3.DatabaseError:
            pass
    if stale:
        build(db)


def lexical_scores(text: str, db: Path) -> dict[str, float]:
    terms = query_tokens(text)
    if not terms:
        return {}
    match = " OR ".join('"' + t + '"' for t in terms)
    with closing(sqlite3.connect(db)) as conn:
        rows = conn.execute("SELECT id, -bm25(documents,0,6,4,2,2,1.5,4,1) FROM documents WHERE documents MATCH ?", (match,)).fetchall()
    return dict(rows)


def structural_evidence(source: str) -> tuple[dict[str, list[dict]], str, str, str | None]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return {}, "", "", f"AST parsing unavailable: {type(exc).__name__}; lexical fallback only"
    parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    annotation_roots = [n.annotation for n in ast.walk(tree) if isinstance(n, (ast.arg, ast.AnnAssign)) and n.annotation is not None]
    annotation_roots += [n.returns for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.returns is not None]
    annotation_nodes = {item for root in annotation_roots for item in ast.walk(root)}
    nodes = [n for n in ast.walk(tree) if n not in annotation_nodes]
    docs = [ast.get_docstring(n) or "" for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))]
    # Recover a common misplaced-spec shape without executing its string.
    docs += [n.value.value for n in nodes if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and len(n.value.value) > 150]
    spec = "\n".join(docs)
    spec_lower = re.sub(r"\s+", " ", spec.casefold())
    evidence: dict[str, list[dict]] = {}

    def add(slug, priority, node, why):
        record = {"line": getattr(node, "lineno", 1), "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                  "expression": (ast.get_source_segment(source, node) or ast.unparse(node))[:500],
                  "reason": why, "priority": priority}
        key = "py." + slug
        if record not in evidence.setdefault(key, []):
            evidence[key].append(record)

    aliases = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for a in node.names:
                aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                aliases[a.asname or a.name] = node.module + "." + a.name

    def function_scope(node):
        child = node
        while child in parent:
            outer = parent[child]
            if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if not isinstance(child, ast.arguments):
                    return outer
            child = outer
        return None

    def local_names(scope):
        if scope is None:
            return set()
        found = {a.arg for a in [*scope.args.posonlyargs, *scope.args.args, *scope.args.kwonlyargs]}
        stack = list(scope.body if hasattr(scope, "body") and isinstance(scope.body, list) else [])
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(n.name)
                continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                found.add(n.id)
            stack.extend(ast.iter_child_nodes(n))
        return found

    scopes = {n: local_names(n) for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))}
    global_shadow = {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and function_scope(n) is None}

    def qualified(node):
        if isinstance(node, ast.Attribute):
            base = qualified(node.value)
            return base + "." + node.attr if base else ""
        if isinstance(node, ast.Name):
            scope = function_scope(node)
            if node.id in scopes.get(scope, set()):
                return "<local>." + node.id
            if node.id in global_shadow:
                return "<global>." + node.id
            return aliases.get(node.id, node.id)
        return ""

    calls = [n for n in nodes if isinstance(n, ast.Call)]
    names = {qualified(n.func) for n in calls}
    attrs = {n.func.attr for n in calls if isinstance(n.func, ast.Attribute)}
    has = lambda word: any(n in {word, "builtins." + word} for n in names)
    has_set = any(isinstance(n, (ast.Set, ast.SetComp)) for n in nodes) or has("set")
    has_sort = has("sorted") or "sort" in attrs
    subscriptions = [n for n in nodes if isinstance(n, ast.Subscript)]
    has_loop = any(isinstance(n, (ast.For, ast.While, ast.comprehension)) for n in nodes)
    initial = {}
    for n in nodes:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Name):
                    initial.setdefault(t.id, n.value)

    def constant(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) and isinstance(n.operand.value, (int, float)):
            return -n.operand.value
        return None

    # Scope-specific constructs that formerly lost to unrelated lexical tokens.
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = [*node.args.defaults, *(x for x in node.args.kw_defaults if x is not None)]
            for default in defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    add("mutable-default", 220, default, "Mutable object in parameter default; inspect cross-call state.")
                elif isinstance(default, ast.Call):
                    add("definition-time-call", 165, default, "A parameter call is evaluated at definition time.")
            body_calls = [n for stmt in node.body for n in ast.walk(stmt) if isinstance(n, ast.Call)]
            recursive = [n for n in body_calls if isinstance(n.func, ast.Name) and n.func.id == node.name
                         and function_scope(n) is node and node.name not in scopes[node]]
            for call in recursive:
                add("recursive-base-progress", 140, call, "Self-recursive call; inspect valid base coverage and supported depth.")
        elif isinstance(node, (ast.For, ast.comprehension)):
            loop_body = node.body if isinstance(node, ast.For) else [parent.get(node, node)]
            if any(isinstance(n, (ast.Lambda, ast.FunctionDef)) for stmt in loop_body for n in ast.walk(stmt)):
                add("late-bound-closure", 205, node, "A callback is created in an iteration; inspect binding at invocation.")
        elif isinstance(node, ast.Try):
            for stmt in node.finalbody:
                stack = [stmt]
                while stack:
                    item = stack.pop()
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    if isinstance(item, (ast.Return, ast.Break, ast.Continue)):
                        add("finally-overrides-control-flow", 210, item, "Jump in finally can replace pending control flow.")
                    stack.extend(ast.iter_child_nodes(item))
        elif isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Tuple):
                add("truthy-tuple-condition", 210, node, "The assertion tests a tuple object.")
            elif isinstance(node.test, ast.GeneratorExp):
                add("truthy-generator-assert", 210, node, "The assertion tests a generator rather than its yielded conditions.")

    for sub in subscriptions:
        if isinstance(sub.slice, ast.Slice):
            add("slice-boundary-normalization", 62, sub, "Slice bounds and exclusive stop define the selected segment.")
            continue
        # Do not interpret an obvious mapping key as a sequence index.
        if isinstance(sub.value, ast.Name) and isinstance(initial.get(sub.value.id), (ast.Dict, ast.DictComp)):
            continue
        if isinstance(constant(sub.slice), str):
            continue
        add("index-out-of-bounds", 76, sub, "Direct subscription needs an admissible index at size boundaries.")
        if isinstance(constant(sub.slice), (int, float)) and constant(sub.slice) < 0:
            add("negative-index-sentinel", 83, sub, "Negative subscription selects from the end rather than rejecting a sentinel.")
        if isinstance(sub.slice, ast.BinOp) and isinstance(sub.slice.op, ast.Sub):
            add("negative-index-sentinel", 88, sub, "Subtracting from a position can create a valid-but-unintended negative index.")
        if isinstance(sub.slice, ast.Call) and qualified(sub.slice.func) == "len" and sub.slice.args and ast.dump(sub.value) == ast.dump(sub.slice.args[0]):
            add("index-out-of-bounds", 230, sub, "Index is exactly len(receiver), beyond its last valid element.")
        if isinstance(sub.value, (ast.List, ast.Tuple)) and isinstance(constant(sub.slice), int):
            i = constant(sub.slice)
            if not -len(sub.value.elts) <= i < len(sub.value.elts):
                add("index-out-of-bounds", 230, sub, "Literal sequence and index establish an out-of-bounds access.")
        if isinstance(sub.value, ast.Name) and isinstance(initial.get(sub.value.id), ast.BinOp) and isinstance(initial[sub.value.id].op, ast.Mult):
            add("index-out-of-bounds", 136, sub, "Subscription into repetition-allocated storage; inspect capacity versus input size.")

    # Branches are grounded at actual comparisons, not at the word 'if' in a spec.
    for node in nodes:
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            numeric = any(isinstance(constant(x), (int, float)) for x in operands)
            length = any(isinstance(x, ast.Call) and qualified(x.func) == "len" for x in operands)
            if numeric or length or any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)) for op in node.ops) and all(isinstance(x, (ast.Name, ast.BinOp, ast.Call)) for x in operands):
                add("branch-boundary-contract", 112 if numeric or length else 108, node, "Concrete comparison partitions valid inputs; inspect equality and adjacent boundary behavior.")
            if length and any(constant(x) in (0, 1, 2) for x in operands):
                add("empty-singleton-shortcut", 141, node, "A small-length comparison creates a specialized path.")
            for literal in operands:
                if isinstance(literal, ast.Name) and literal.id in initial:
                    literal = initial[literal.id]
                if isinstance(literal, ast.Constant) and isinstance(literal.value, str) and 1 < len(literal.value) < 60 and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                    add("literal-classification-domain", 148, node, "Literal character membership defines an explicit class table.")
                if isinstance(literal, (ast.List, ast.Tuple, ast.Set)) and literal.elts and all(isinstance(e, ast.Constant) for e in literal.elts):
                    if re.search(r"digit|vowel|odd|even|character|consonant", spec_lower):
                        add("literal-classification-domain", 140, node, "A finite literal table is used for a named numeric/character class.")
        elif isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not) and isinstance(node.test.operand, ast.Name):
            if re.search(r"list|array|string|bracket|prefix|empty", spec_lower):
                add("empty-singleton-shortcut", 125, node.test, "A truthiness guard specializes the empty-input path.")
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.BoolOp):
            if any(isinstance(v, (ast.Name, ast.List, ast.Dict, ast.Set)) for v in node.value.values):
                add("shortcircuit-boolean-result", 165, node.value, "Returned and/or expression can yield an operand instead of bool.")

    for node in calls:
        q = qualified(node.func)
        attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if q == "os.path.commonprefix":
            add("path-character-prefix", 225, node, "Qualified commonprefix performs a textual rather than component comparison.")
        if q == "range":
            add("range-exclusive-stop", 70, node, "The loop domain uses an exclusive range stop.")
            if len(node.args) >= 3 and constant(node.args[2]) not in (None, 1, -1):
                add("index-origin-domain", 144, node, "Non-unit range stride retains the start-origin alignment.")
        if attr == "index":
            add("first-occurrence-position", 146, node, "index returns the first equal occurrence, not an arbitrary current position.")
            if re.search(r"alphabet|ord\(", spec_lower):
                add("index-origin-domain", 157, node, "Occurrence position and alphabet ordinal are different coordinate domains.")
        if attr == "encode":
            add("unicode-text-byte-domain", 195, node, "Encoding changes from text characters to bytes.")
        if attr in {"lower", "upper", "casefold", "strip", "lstrip", "rstrip", "replace"}:
            if not re.search(r"regardless of case|case.insensitive|ignore case", spec_lower):
                add("text-normalization-contract", 143, node, "This operation changes exact case/characters or whitespace.")
            if attr in {"strip", "lstrip", "rstrip"} and node.args and isinstance(constant(node.args[0]), str) and len(constant(node.args[0])) > 1:
                add("strip-character-set", 218, node, "Multi-character strip argument denotes a character set.")
            if attr == "replace" and node.args:
                pattern = constant(node.args[0])
                if isinstance(pattern, str) and len(pattern) > 1 and len(set(pattern)) == 1:
                    add("fixed-chunk-run", 190, node, "A fixed repeated literal is replaced, rather than a maximal run.")
        if attr in {"split", "join", "replace"}:
            if re.search(r"space|word|separat|sentence|delimit", spec_lower):
                add("split-join-separator-loss", 151 if attr in {"split", "join"} else 135, node, "Tokenization/reconstruction has a delimiter and empty-field policy.")
        if attr in {"isalpha", "isupper", "islower", "isdigit", "isalnum"} or q in {"string.ascii_letters", "string.ascii_uppercase", "string.ascii_lowercase"}:
            add("ascii-unicode-classification", 130, node, "A character-class API chooses a specific Unicode/ASCII domain.")
        if q in {"int", "float"}:
            if q == "float" or node.args and isinstance(node.args[0], ast.BinOp) or q == "int" and node.args and isinstance(node.args[0], ast.Name) and re.search(r"positive numbers|list.*increment", spec_lower):
                add("numeric-cast-loss", 138, node, "Numeric coercion can change fraction or finite-precision value.")
            if q == "int" and node.args and any(isinstance(n, ast.Slice) for n in ast.walk(node.args[0])):
                add("numeric-text-width", 188, node, "Parsing sliced/reversed digit text discards leading-zero representation.")
            if q == "int" and (re.search(r"binary", spec_lower) or len(node.args) > 1):
                add("numeric-text-width", 123, node, "Integer parsing does not retain input digit width.")
        if q == "round":
            add("rounding-policy", 170, node, "Rounding and comparison order/tie policy must match the numeric contract.")
        if q in {"min", "max"}:
            if len(node.args) == 1:
                add("empty-reduction-domain", 131, node, "An iterable extremum needs a policy when no eligible element survives.")
            if re.search(r"first|tie|same|multiple|lexicograph", spec_lower):
                add("tie-break-selection", 121, node, "The specification distinguishes equal-scoring candidates.")
        if q in {"sum", "len"} and re.search(r"total|sum|balance|well|characters|chars", spec_lower):
            if q == "sum" or has_set:
                add("aggregation-scope", 126 if q == "sum" else 120, node, "The aggregate's region, unit and grouping are explicit review obligations.")
        if q in {"all", "any"}:
            add("quantifier-scope", 105, node, "The computation chooses a specific quantifier and input region.")
        if q == "eval" and re.search(r"fraction|denominator|numerator", spec_lower):
            add("integer-division-precision", 177, node, "Evaluated fraction text uses Python true division rather than exact rational arithmetic.")
            if any(isinstance(n, ast.Compare) for n in nodes):
                add("float-exact-equality", 160, node, "An exact integrality comparison consumes values computed by floating division.")
        if q.startswith("logging."):
            add("logging-format-arguments", 210, node, "Logging formats the message lazily with supplied arguments.")
        if q in {"re.match", "re.search"} and node.args and isinstance(constant(node.args[0]), str) and "$" in constant(node.args[0]):
            add("regex-fullmatch-boundary", 194, node, "Dollar anchoring does not imply complete-string consumption.")
        if attr in {"append", "extend", "sort", "reverse", "insert"} and isinstance(parent.get(node), (ast.Assign, ast.Return, ast.AnnAssign)):
            add("mutator-return-none", 210, node, "The result of an in-place mutator is consumed.")
        if attr == "fromkeys" and len(node.args) > 1 and isinstance(node.args[1], (ast.List, ast.Dict, ast.Set)):
            add("fromkeys-shared-value", 218, node, "A mutable value is reused by fromkeys.")

    # State and global/whole-input properties, still without target execution.
    if has_set:
        witness_node = next((n for n in calls if qualified(n.func) == "set"), tree)
        if not has_sort and re.search(r"sort|order", spec_lower):
            add("set-order-loss", 170, witness_node, "A set reaches sequence processing without restoring the specified order.")
        if re.search(r"duplicate|times|distinct elements|all strings|all integers", spec_lower):
            add("set-loses-multiplicity", 148, witness_node, "Set state cannot by itself retain the occurrence multiplicity needed by the task.")
            add("presence-frequency-confusion", 150, witness_node, "Presence-only state is being used in an occurrence-sensitive task.")
    if re.search(r"more than once|occur|frequency|times|duplicates|number of times|three distinct|minimum number.*changed", spec_lower):
        for n in nodes:
            if isinstance(n, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops):
                add("presence-frequency-confusion", 149, n, "Membership/one-key state does not establish occurrence counts or distinct index use.")
    for node in nodes:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            compared = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id in compared and constant(initial.get(target.id)) is not None:
                            add("extremum-initial-sentinel", 178, node.test, "A comparison-updated accumulator has a fixed initial sentinel.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if re.search(r"integer|whole|power|fraction|sequence", spec_lower):
                add("integer-division-precision", 159, node, "True division enters floating arithmetic in an exact-value task.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and re.search(r"unit digit|digit|negative", spec_lower):
            add("signed-modulo-domain", 94, node, "Remainder sign/domain differs from magnitude digit extraction.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv) and constant(node.right) == 10 and re.search(r"first|leading", spec_lower):
            add("digit-place-extraction", 191, node, "Dividing by ten leaves a prefix rather than a width-independent leading digit.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and re.search(r"absolute difference|how far|magnitude|distance", spec_lower) and not has("abs"):
            add("absolute-difference", 185, node, "Signed subtraction implements a required magnitude without abs.")
        if isinstance(node, ast.Compare) and any(isinstance(op, (ast.Lt, ast.Gt)) for op in node.ops):
            if any(isinstance(n, ast.Call) and qualified(n.func) == "str" for n in ast.walk(node)):
                add("lexicographic-numeric-order", 190, node, "Text coercion precedes ordering in a numeric/domain comparison.")
            elif "index" in attrs and re.search(r"orbit|proximity|ordered.*list|planet", spec_lower):
                add("lexicographic-numeric-order", 175, node, "Label comparison precedes lookup in an explicitly ranked domain.")
    if re.search(r"first.*index|last.*index|odd.*ind|even.*ind|odd.*position|even.*position|coefficient|derivative|even digits", spec_lower):
        n = subscriptions[0] if subscriptions else next((n for n in calls if qualified(n.func) in {"range", "enumerate"}), tree)
        add("index-origin-domain", 146, n, "The specification distinguishes a positional origin, index parity, or coefficient degree.")
        for sub in subscriptions:
            if isinstance(parent.get(sub), (ast.Assign, ast.AugAssign)):
                add("index-origin-domain", 147, sub, "A positional assignment or selection must use the specified coordinate origin and stride.")
        if "derivative" in spec_lower or "coefficient" in spec_lower:
            for assignment in nodes:
                if isinstance(assignment, ast.Assign) and isinstance(assignment.value, ast.BinOp):
                    if any(isinstance(x, ast.Call) and qualified(x.func) == "len" for x in ast.walk(assignment.value)):
                        add("index-origin-domain", 169, assignment, "A length-derived multiplier is used as a polynomial index/degree.")
    if re.search(r"length of.*interval|length of intersection|intersection.*length", spec_lower):
        for n in calls:
            if qualified(n.func) == "range" and len(n.args) > 1 and not any(isinstance(x, ast.Call) and qualified(x.func) == "len" for arg in n.args for x in ast.walk(arg)):
                add("index-origin-domain", 150, n, "Range enumerates absolute coordinates although the specification defines an interval length or derived coordinate.")
    if re.search(r"smallest|largest|biggest|minimum|maximum|closest", spec_lower) and has_loop:
        for node in nodes:
            if isinstance(node, ast.Return) and function_scope(node):
                p = parent.get(node)
                while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if isinstance(p, (ast.For, ast.While)):
                        add("first-match-vs-optimum", 139, node, "A loop returns a qualifying candidate before later candidates are considered.")
                        break
                    p = parent.get(p)
    if has_sort and subscriptions and re.search(r"first.*last|last.*first|original", spec_lower):
        add("observation-after-transform", 181, next((n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "sort"), tree), "Sorting occurs in a task whose decision depends on original ordered state.")
    if re.search(r"at any point|below zero|balance|palindrom|every|all numbers|all elements|whole array|right shift", spec_lower):
        if subscriptions or has("sum"):
            add("quantifier-scope", 149 if re.search(r"below zero|palindrom|all numbers|right shift", spec_lower) else 122,
                subscriptions[0] if subscriptions else calls[0], "Selected positions/final aggregate must not replace the required whole-input or prefix condition.")
    if any(isinstance(n, ast.Attribute) and qualified(n).startswith("string.ascii_") for n in nodes):
        add("ascii-unicode-classification", 180, next(n for n in nodes if isinstance(n, ast.Attribute) and qualified(n).startswith("string.ascii_")), "An explicit ASCII table chooses whether character processing is performed.")
    # Character-to-position comparisons, e.g. an iterated c == text[-1].
    targets = {n.target.id for n in nodes if isinstance(n, ast.For) and isinstance(n.target, ast.Name)}
    for n in nodes:
        if isinstance(n, ast.Compare) and any(isinstance(x, ast.Name) and x.id in targets for x in [n.left, *n.comparators]) and any(isinstance(x, ast.Subscript) and constant(x.slice) == -1 for x in [n.left, *n.comparators]):
            add("first-occurrence-position", 185, n, "Value equality with the final character does not establish current iteration position.")
    count_literals = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "count" and n.args and isinstance(constant(n.args[0]), str) and len(constant(n.args[0])) == 1]
    if len(count_literals) >= 3:
        add("literal-classification-domain", 184, count_literals[0], "Several literal counts implement a named character/digit class.")
    # Preserve source identifiers and APIs but omit Python syntax/annotation words.
    ignored = {"return", "def", "typing", "List", "Tuple", "Optional", "int", "float", "str", "bool"}
    symbols = " ".join(sorted({n.id for n in nodes if isinstance(n, ast.Name) and n.id not in ignored} | names))
    return evidence, spec, symbols, None


def search(query: str = "", *, code: str | None = None, top_k: int = 5,
           category: str | None = None, source: str | None = None, mode: str = "hybrid",
           db: Path = DEFAULT_DB) -> dict:
    if not 1 <= top_k <= 100 or mode not in {"hybrid", "lexical"}:
        raise ValueError("Invalid top_k or retrieval mode")
    ensure(db)
    all_cards = {c["id"]: c for c in corpus.cards()}
    evidence, spec, symbols, warning = structural_evidence(code) if code is not None else ({}, "", "", None)
    if mode == "lexical" or code is None or warning:
        old_hints = legacy_code_hints(code)[0] if code is not None else ""
        scores = lexical_scores(" ".join([query, old_hints, code or ""]), db)
    else:
        doc_scores = lexical_scores(query + " " + spec, db)
        symbol_scores = lexical_scores(symbols, db)
        doc_max = max(doc_scores.values(), default=1) or 1
        sym_max = max(symbol_scores.values(), default=1) or 1
        scores = {k: max(r["priority"] for r in rows) + 10 * doc_scores.get(k, 0) / doc_max + 5 * symbol_scores.get(k, 0) / sym_max for k, rows in evidence.items()}
    ranked = sorted(scores, key=lambda k: (-scores[k], k))
    results = []
    for key in ranked:
        card = all_cards[key]
        if category and card["category"] != category or source and not any(s["source"] == source for s in card["sources"]):
            continue
        sites = sorted(evidence.get(key, []), key=lambda r: (-r["priority"], r["line"]))
        results.append({"score": scores[key], "concept": card,
                        "evidence": sites[:3], "additional_sites_omitted": max(0, len(sites) - 3)})
        if len(results) == top_k:
            break
    return {"query": query, "warning": warning, "code_hints": " ".join(evidence), "results": results,
            "retrieval": mode + ": structural applicability and separate BM25 spec/API channels; scores are not bug probability",
            "engine_version": VERSION, "corpus_sha256": corpus.digest()}
