"""Relation candidates for a focal method (no LLM, stdlib + regex).

Input: the dataset record's signature lists (`source:source_other_method_signature`, never the class code field, which
contains the focal body) and m6's blind evidence pack (`m6_agent_oracle/out/evidence.jsonl`: declaration, Javadoc,
same-name methods, caller snippets). Output: R1 inverse/round-trip candidates and R2 overload/variant candidates found
by name rules; R3-R5 are listed as generic families. Both m7 arms get the same block.

usage: python3 m7_property_oracle/relations.py [idx ...]   -> prints the blocks; `selftest` runs the checks
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
EVIDENCE = f"{REPO}/m6_agent_oracle/out/evidence.jsonl"
MAX_R1, MAX_R2 = 6, 8

# R1 verb pairs (either direction); the verb is the leading camelCase word of the method name
INVERSE = [("escape", "unescape"), ("encode", "decode"), ("serialize", "deserialize"), ("marshal", "unmarshal"),
           ("wrap", "unwrap"), ("compress", "decompress"), ("encrypt", "decrypt"), ("join", "split"), ("format", "parse"),
           ("add", "remove"), ("insert", "delete"), ("push", "pop"), ("to", "from"), ("to", "parse"), ("to", "valueOf"),
           ("write", "read")]
# R1 class-level pairs (focal class name token -> its inverse), listed only if the inverse class is named in the pack
INVERSE_CLASS = [("Unescaper", "Escaper"), ("Decoder", "Encoder"), ("Reader", "Writer"), ("InputStream", "OutputStream"),
                 ("Parser", "Printer"), ("Parser", "Formatter"), ("Deserializer", "Serializer")]
# R2 sibling tokens: (token a, token b, relation hint)
SIBLING = [("Any", "None", "complement: one should be the negation of the other on the same input"),
           ("Any", "Only", "related set predicates on the same input"),
           ("is", "isNot", "complement: one should be the negation of the other on the same input"),
           ("True", "False", "complement"), ("Left", "Right", "mirror: symmetric behaviour, e.g. equal result lengths"),
           ("Start", "End", "mirror"), ("First", "Last", "mirror"), ("Upper", "Lower", "mirror"),
           ("Date", "DateTime", "delegating variant: should agree on the shared part"),
           ("Time", "DateTime", "delegating variant: should agree on the shared part")]


def name_of(decl):
    m = re.search(r"([\w$]+)\s*\(", decl)
    return m.group(1) if m else None


def param_types(decl):
    """parameter types of a declaration, e.g. 'String', 'char[]', 'T...' (generics and 'final' dropped)."""
    inner = decl[decl.find("(") + 1:decl.rfind(")")]
    inner = re.sub(r"<[^<>]*>", "", re.sub(r"<[^<>]*>", "", inner))
    out = []
    for p in filter(None, (x.strip() for x in inner.split(","))):
        toks = [t for t in p.replace("...", "[] ").split() if t != "final" and not t.startswith("@")]
        out.append(" ".join(toks[:-1]) if len(toks) > 1 else toks[0])
    return tuple(re.sub(r"\s+(\[\])", r"\1", t) for t in out)


def norm_decl(d):
    return re.sub(r"\s+", " ", d).strip().rstrip(";").strip()


def public_methods(rec):
    """non-private method declarations of the focal class, deduplicated (the dataset lists most of them twice)."""
    seen = {}
    for s in rec.get("source:source_other_method_signature") or []:
        s = re.sub(r"@[\w.]+(\([^)]*\))?", "", re.sub(r"//[^\n]*|/\*.*?\*/", "", s, flags=re.S))  # annotations, comments
        if re.match(r"\s*private\b", s) or not name_of(s):
            continue
        seen.setdefault((name_of(s), param_types(s)), norm_decl(s))
    return seen


def has_verb(name, v):
    return name == v or name.startswith(v) and name[len(v)].isupper()


def r1(rec, ev, pack_text):
    name, focal = ev["name"], (ev["name"], param_types(ev["declaration"]))
    dist = lambda t: len(set(t) - set(focal[1])) + abs(len(t) - len(focal[1]))
    meths = {k: v for k, v in public_methods(rec).items() if k != focal}
    names = {k[0] for k in meths}
    # methods named elsewhere in the pack as Class.method( or {@link Class#method}: other classes' inverses
    for c, m in re.findall(r"\b([A-Z][\w$]*)\s*[.#]\s*([a-z][\w$]*)\s*[(\s}]", pack_text):
        names.add(f"{c}.{m}")
    out = []
    for a, b in INVERSE:
        for x, y in ((a, b), (b, a)):
            if not has_verb(name, x):
                continue
            target = y + name[len(x):]
            for n in sorted(names, key=len):
                short = n.split(".")[-1]
                if short == name or not has_verb(short, y):
                    continue
                if short == target or target.startswith(short) or short.startswith(target):
                    decls = [d for (k, t), d in sorted(meths.items(), key=lambda kd: dist(kd[0][1])) if k == n] or [n + "(...)"]
                    out += [(d, f"{x}/{y}: round trip, e.g. {short}({name}(x)) vs x") for d in decls]
    for a, b in INVERSE_CLASS:
        for x, y in ((a, b), (b, a)):
            cls = ev["class"]
            if cls.endswith(x) and not (x == "Escaper" and cls.endswith("Unescaper")):
                other = cls[:-len(x)] + y
                if re.search(r"\b" + re.escape(other) + r"\b", pack_text):
                    out.append((other, f"{x}/{y} classes: round trip through {other}"))
    return list(dict.fromkeys(out))[:MAX_R1]


def r2(rec, ev):
    name, ftypes = ev["name"], param_types(ev["declaration"])
    meths = public_methods(rec)
    for o in ev["overloads"]:  # same-name methods in the focal file (also of nested classes), from m6's pack
        meths.setdefault((name_of(o["declaration"]), param_types(o["declaration"])), norm_decl(o["declaration"]))
    dist = lambda t: len(set(t) - set(ftypes)) + abs(len(t) - len(ftypes))  # closest parameter list first
    over = sorted(((k, d) for k, d in meths.items() if k[0] == name and k[1] != ftypes), key=lambda kd: dist(kd[0][1]))
    out = [(d, "overload: should agree with the focal method where their inputs correspond") for _, d in over]
    for (n, _), d in sorted(meths.items(), key=lambda kd: kd[1]):
        if n == name:
            continue
        hint = None
        for a, b, h in SIBLING:
            for x, y in ((a, b), (b, a)):
                if x in name and name.replace(x, y, 1) == n:
                    hint = h
        if not hint and (n == name + "IgnoreCase" or name == n + "IgnoreCase"):
            hint = "case variant: case-sensitive true implies ignore-case true; they agree when case does not matter"
        if hint:
            out.append((d, hint))
    return out[:MAX_R2]


GENERIC = """- R3 documented invariants: properties the Javadoc states, e.g. result length/size bounds, value range, result type, null input -> null result. Use only what the Javadoc states.
- R4 metamorphic: transform the input in a way whose effect on the output is predictable (e.g. append/prepend text, swap arguments, change case, repeat the call, concatenate inputs) and relate the two outputs.
- R5 JDK equivalent: agreement with a JDK method, only where the Javadoc claims the method behaves like that JDK method."""


def block(rec, ev, pack_text):
    lines = ["// Relation candidates (found by name rules; a candidate may not hold, use it only if the documentation supports it):",
             "// R1 inverse / round-trip partners:"]
    lines += [f"//   {d}   -- {h}" for d, h in r1(rec, ev, pack_text)] or ["//   (none found)"]
    lines += ["// R2 overloads / variants of the same operation:"]
    lines += [f"//   {d}   -- {h}" for d, h in r2(rec, ev)] or ["//   (none found)"]
    lines += ["// Generic families:"] + [f"// {l}" for l in GENERIC.splitlines()]
    return "\n".join(lines)


def selftest():
    assert param_types("public static <T> T[] add(final T[] array, int index, T element);") == ("T[]", "int", "T")
    assert param_types("public static String join(Iterator<?> iterator, char separator)") == ("Iterator", "char")
    assert param_types("public static <T> String join(T... elements);") == ("T[]",)
    rec = {"source:source_other_method_signature": [
        "public static String escapeJava(String str);", "public static void escapeJava(Writer out, String str) throws IOException;",
        "public static String unescapeJava(String str);", "private static String escapeJavaStyleString(String str, boolean escapeSingleQuotes);",
        "public static boolean containsAny(CharSequence cs, char[] searchChars);", "public static boolean containsNone(CharSequence cs, char[] searchChars);",
        "public static boolean containsIgnoreCase(String str, String searchStr);", "public static boolean contains(String str, String searchStr);",
        '@SuppressWarnings("unchecked") // remove() always creates an array\npublic static <T> T[] remove(T[] array, int index);']}
    assert ("remove", ("T[]", "int")) in public_methods(rec)
    ev = {"name": "escapeJava", "declaration": "public static String escapeJava(String str);", "class": "StringEscapeUtils", "overloads": []}
    assert [d for d, _ in r1(rec, ev, "")] == ["public static String unescapeJava(String str)"]
    assert [d for d, _ in r2(rec, ev)] == ["public static void escapeJava(Writer out, String str) throws IOException"]
    ev = {**ev, "name": "containsNone", "declaration": "public static boolean containsNone(CharSequence cs, char[] searchChars);"}
    assert [h.split(":")[0] for _, h in r2(rec, ev)] == ["complement"]
    ev = {**ev, "name": "contains", "declaration": "public static boolean contains(String str, String searchStr);"}
    assert [h.split(":")[0] for _, h in r2(rec, ev)] == ["case variant"]
    ev = {"name": "translate", "declaration": "public int translate(CharSequence input, int index, Writer out) throws IOException;",
          "class": "NumericEntityUnescaper", "overloads": []}
    assert r1({}, ev, "see {@link NumericEntityEscaper}") == [("NumericEntityEscaper", "Unescaper/Escaper classes: round trip through NumericEntityEscaper")]
    assert r1({}, ev, "nothing") == []
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        sys.path.insert(0, f"{REPO}/m7_property_oracle")
        import gen
        recs, evs = gen.load()
        for i in [int(x) for x in sys.argv[1:]] or range(len(recs)):
            print(f"== {i} {recs[i]['extra:project_name']} {evs[i]['name']}\n{block(recs[i], evs[i], gen.pack(evs[i]))}\n")
