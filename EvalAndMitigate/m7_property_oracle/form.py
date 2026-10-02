"""Assertion-form classifier (offline, stdlib): LITERAL / RELATION / THROWS for every assertion of every @Test method.

LITERAL  = assertEquals/assertSame/assertArrayEquals (also `assertTrue(a == b)`, `assertTrue(a.equals(b))`,
           `assertThat(a, is(b) | equalTo(b))`) with one side a literal and the other side focal-derived; or
           assertNull/assertTrue/assertFalse applied directly to a focal call (or to a variable holding one).
  literal  = Java literals, ALL_CAPS constants (`Integer.MAX_VALUE`), `Double.NaN`, casts, operators, constant arrays
             (`new T[]{...}`, `{...}`), boxing wrappers of literals (`Integer.valueOf(1)`, `new BigDecimal("1.5")`,
             `Arrays.asList(...)`), and local variables whose every assignment is such a literal, unless the other side
             depends on that variable (`assertEquals(x, unescape(escape(x)))` is a round trip, not a literal oracle).
  focal-derived = contains a call `name(` of the focal method name, or a variable assigned from one, or the receiver
             / a mutable (array or non-value-typed) argument of a focal call (side effects: `w.value(1); sw.toString()`;
             also the objects such a receiver was constructed from: `new JsonWriter(sw)`).
THROWS   = assertThrows, fail(...), @Test(expected=...), ExpectedException `.expect(`.
RELATION = every other assertion.
A LITERAL is "marked" if `// from Javadoc` is on one of its lines or on the line just above it.

usage: python3 m7_property_oracle/form.py [FILE_POST_FIX ...]   (default: both m7 arms; prints compliance)
       python3 m7_property_oracle/form.py selftest
"""
import json, os, re, sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RQ1 = REPO + "/data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
SRC = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"
MARK = re.compile(r"//\s*from\s+javadoc", re.I)
VALUE_TYPES = {"String", "CharSequence", "Object", "Integer", "Long", "Short", "Byte", "Double", "Float", "Character", "Boolean",
               "int", "long", "short", "byte", "double", "float", "char", "boolean", "BigDecimal", "BigInteger", "Number",
               "Locale", "Class", "TimeZone", "Date", "Calendar", "Type", "var"}
WRAP = r"(?:new\s+)?(?:Integer|Long|Short|Byte|Double|Float|Character|Boolean|BigDecimal|BigInteger|String|Arrays|Collections|List)\s*(?:\.\s*(?:valueOf|asList|singletonList|emptyList|of))?\s*\("
KEYWORDS = {"new", "true", "false", "null", "int", "long", "short", "byte", "double", "float", "char", "boolean", "this", "class"}


def mask(code):
    """same-length copy with the contents of comments, string and char literals blanked (quotes kept)."""
    out, i, n = list(code), 0, len(code)
    while i < n:
        c = code[i]
        if code.startswith("//", i):
            j = code.find("\n", i); j = n if j < 0 else j
            out[i:j] = " " * (j - i); i = j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2); j = n if j < 0 else j + 2
            out[i:j] = [ch if ch == "\n" else " " for ch in code[i:j]]; i = j
        elif c in "\"'":
            j = i + 1
            while j < n and code[j] != c and code[j] != "\n":
                j += 2 if code[j] == "\\" else 1
            out[i + 1:j] = " " * (j - i - 1); i = j + 1
        else:
            i += 1
    return "".join(out)


def close(m, i, o="(", c=")"):
    """index of the bracket closing the one at m[i] (m is masked code)."""
    d = 0
    for j in range(i, len(m)):
        d += (m[j] == o) - (m[j] == c)
        if d == 0:
            return j
    return len(m) - 1


def split_args(m, a, b):
    """[(start, end)] of the depth-0 comma-separated arguments in m[a:b]."""
    out, d, s = [], 0, a
    for j in range(a, b):
        d += (m[j] in "([{") - (m[j] in ")]}")
        if m[j] == "," and d == 0:
            out.append((s, j)); s = j + 1
    if m[s:b].strip():
        out.append((s, b))
    return out


def tests(code):
    """[(name, annotation text, body start, body end)] of the @Test methods; code is the original text."""
    m = mask(code)
    out = []
    for t in re.finditer(r"@Test\b(\s*\([^)]*\))?", m):
        h = re.compile(r"\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public\s+|protected\s+|private\s+)?(?:static\s+)?void\s+(\w+)\s*\([^)]*\)\s*(?:throws[^{]*)?\{").match(m, t.end())
        if h:
            s = h.end() - 1
            out.append((h.group(1), code[t.start():t.end()], s, close(m, s, "{", "}")))
    return out


def strip_parens(e):
    e = e.strip()
    while e.startswith("(") and close(mask(e), 0) == len(e) - 1:
        e = e[1:-1].strip()
    return e


DECL = re.compile(r"(?:^|[;{}(]|\n)\s*(?:(?:final|private|protected|public|static)\s+)*([A-Za-z_$][\w$.]*(?:<[^;=(){}]*>)?(?:\[\])*)\s+([a-zA-Z_$][\w$]*)\s*(=|;|:)")
NOT_TYPES = {"return", "new", "throw", "else", "case", "assert"}


def decls(m):
    return {d.group(2): d.group(1) for d in DECL.finditer(m) if d.group(1) not in NOT_TYPES}


def chain_head(m, i):
    """receiver variable of the call starting at i: `a.b(x).focal(` -> a, `this.p.focal(` -> p, `Cls.focal(` -> Cls,
    `new X().focal(` / `focal(` -> None."""
    def back(j):
        while j > 0 and m[j - 1].isspace():
            j -= 1
        return j
    j, prev = back(i), None
    while j > 0 and m[j - 1] == ".":
        j, call = back(j - 1), False
        if m[j - 1:j] == ")":
            d, j = 0, j - 1
            while j > 0 and not (d == 1 and m[j] == "("):
                d += (m[j] == ")") - (m[j] == "(")
                j -= 1
            j, call = back(j), True
        k = j
        while k > 0 and (m[k - 1].isalnum() or m[k - 1] in "_$"):
            k -= 1
        if k == j:
            return None
        ident, j = m[k:j], back(k)
        if ident == "this":
            return prev
        prev = None if call else ident
        if m[j - 1:j] != ".":
            return prev
    return None


class Test:
    def __init__(self, code, m, body, end, name, cls_m, helpers):
        """code/m: original and masked class text; [body, end]: the test's braces; cls_m: masked text outside @Test
        bodies; helpers: {name: masked body} of the test class's other methods. A helper that calls the focal method
        (directly or through another helper) counts as a focal call; other helpers with literal arguments as literals."""
        self.code, self.m, self.s, self.e, self.name = code, m, body, end, name
        fn = {name}
        for _ in range(5):
            fn |= {h for h, b in helpers.items() if re.search(r"(?<![\w$])(?:" + "|".join(map(re.escape, fn)) + r")\s*\(", b)}
        self.fnames, self.helpers = fn, set(helpers) - fn
        self.focal = re.compile(r"(?<![\w$])(?:" + "|".join(map(re.escape, sorted(fn))) + r")\s*\(")
        bm = m[body:end]
        local = decls(bm)
        self.decl = {**decls(cls_m), **local}  # test-class fields (and helper locals), then the test's own locals
        self.rhs = {}
        for v in self.decl:
            texts = [bm] + ([] if v in local else [cls_m])
            self.rhs[v] = [r for t in texts for r in self._assigned(t, v)]
            if not self.rhs[v]:
                del self.rhs[v]
        recv = set()
        for c in self.focal.finditer(bm):  # receivers and mutable arguments of focal calls (side effects)
            h = chain_head(bm, c.start())
            if h in self.decl:
                recv.add(h)
            p = c.end() - 1
            for x, y in split_args(bm, p + 1, close(bm, p)):
                v = bm[x:y].strip()
                if v in self.decl and self._mutable(v):
                    recv.add(v)
        for v in list(recv):  # what a mutated object was built from (jsonWriter = new JsonWriter(stringWriter))
            recv |= {h for r in self.rhs.get(v, []) for h in self.heads(r) if self._mutable(h)}
        self.recv = recv
        self.derived = self._derived()
        self.caught = set(re.findall(r"catch\s*\(\s*(?:final\s+)?[\w$.|\s]+?\s+([\w$]+)\s*\)", bm))

    def _mutable(self, v):
        t = self.decl[v]
        return t.endswith("]") or t.split("<")[0] not in VALUE_TYPES

    def _assigned(self, t, v):
        """right-hand sides of `v = ...;` in masked text t, plus the arguments of statement-level calls `v.m(args);`
        on v (other than the focal method): `expected.put("a", 0);` keeps `expected` a literal value."""
        out = []
        for a in re.finditer(r"(?<![\w$.])" + re.escape(v) + r"\s*=(?!=)", t):
            k = a.end()
            while k < len(t) and not (t[k] == ";" and self._depth_t(t, a.end(), k) == 0):
                k += 1
            out.append(t[a.end():k])
        for c in re.finditer(r"(?:^|[;{}])\s*" + re.escape(v) + r"\s*\.\s*([\w$]+)\s*\(", t):
            p = c.end() - 1; q = close(t, p)
            if c.group(1) not in self.fnames and t[q + 1:].lstrip().startswith(";"):
                out.append(t[p + 1:q] or "L")
        return out

    @staticmethod
    def _depth_t(t, a, b):
        s = t[a:b]
        return sum(s.count(x) for x in "([{") - sum(s.count(x) for x in ")]}")

    def _depth(self, a, b):
        s = self.m[a:b]
        return sum(s.count(x) for x in "([{") - sum(s.count(x) for x in ")]}")

    def heads(self, e):
        """identifiers used as values in masked expression e (not after '.', not called, not keywords/types)."""
        return {h for h in re.findall(r"(?<![\w$.])([a-zA-Z_$][\w$]*)(?!\s*\()", e) if h in self.decl}

    def lit_var(self, v, seen=()):
        return v in self.rhs and v not in seen and v not in self.recv and all(self.is_lit(r, seen + (v,)) for r in self.rhs[v])

    def is_lit(self, e, seen=()):
        e = e.strip()
        if not e or self.focal.search(e):
            return False
        for _ in range(6):  # wrappers and array initialisers of literals -> L
            e2 = re.sub(r"\"\s*\"|'\s*'", "L", e)
            e2 = re.sub(r"(?:" + WRAP + r"|new\s+[\w$.]+\s*(?:<[^<>()]*>)?\s*\()([^()]*)\)", lambda x: "L" if self.is_lit(x.group(1) or "L", seen) or not x.group(1).strip() else x.group(0), e2)
            if self.helpers:
                e2 = re.sub(r"(?<![\w$.])(?:" + "|".join(map(re.escape, sorted(self.helpers))) + r")\s*\(([^()]*)\)",
                            lambda x: "L" if not x.group(1).strip() or self.is_lit(x.group(1), seen) else x.group(0), e2)
            e2 = re.sub(r"System\s*\.\s*(?:lineSeparator\s*\(\s*\)|getProperty\s*\(\s*\"\s*\"\s*\))", "L", e2)
            e2 = re.sub(r"\bL\s*\.\s*(?:getBytes|toCharArray|length|toString|intValue|longValue|doubleValue)\s*\(([^()]*)\)",
                        lambda x: "L" if not x.group(1).strip() or self.is_lit(x.group(1), seen) else x.group(0), e2)
            e2 = re.sub(r"new\s+[\w$.<>]+\s*(?:\[\s*\]\s*)+\{([^{}]*)\}|\{([^{}]*)\}", lambda x: "L" if all(
                self.is_lit(p, seen) for p in (x.group(1) if x.group(1) is not None else x.group(2) or "L").split(",") if p.strip()) else "X", e2)
            if e2 == e:
                break
            e = e2
        for v in self.heads(e):
            if not self.lit_var(v, seen):
                return False
            e = re.sub(r"(?<![\w$.])" + re.escape(v) + r"(?![\w$])", "L", e)
        e = re.sub(r"\(\s*(?:int|long|short|byte|char|double|float|boolean|[A-Z][a-z][\w$.]*(?:\[\])*)\s*\)", " ", e)  # casts
        e = re.sub(r"\b[\w$.]+(?:\[\])*\s*\.\s*class\b", "L", e)  # class literals
        e = re.sub(r"\b[A-Z][\w$]*(?:\.[A-Z][\w$]*)*\.(?:[A-Z][A-Z0-9_]*|NaN)\b|\b[A-Z][A-Z0-9_]+\b", "L", e)  # constants
        e = re.sub(r"\b0[xX][0-9a-fA-F_]+[lL]?\b|\b\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?[lLfFdD]?\b|\.\d+[fFdD]?\b|\btrue\b|\bfalse\b|\bnull\b", "L", e)
        return re.fullmatch(r"[\sL+\-*/%()!~^&|<>?:,]*", e) is not None and "L" in e

    def _derived(self):
        der = set(self.recv) | {v for v, rs in self.rhs.items() if any(self.focal.search(r) for r in rs)}
        for _ in range(10):
            new = {v for v, rs in self.rhs.items() if v not in der and any(self.heads(r) & der for r in rs)}
            if not new:
                break
            der |= new
        return der

    def is_derived(self, e):
        return bool(self.focal.search(e)) or bool(self.heads(e) & self.derived)

    def deps(self, e, seen=()):
        out = set()
        for h in self.heads(e) - set(seen):
            out |= {h} | {d for r in self.rhs.get(h, []) for d in self.deps(r, seen + (h,))}
        return out

    def eq(self, a, b):
        """equality oracle between masked expressions a and b."""
        for x, y in ((a, b), (b, a)):
            if self.is_lit(x) and self.is_derived(y):
                if not (self.heads(x) & self.deps(y)):  # literal var feeding the other side = round trip / identity
                    return "LITERAL"
        return "RELATION"

    def direct(self, e):
        e = strip_parens(e.strip().lstrip("!").strip())
        me = mask(e)
        if re.fullmatch(r"[a-zA-Z_$][\w$]*", e):
            return e in self.rhs and len(self.rhs[e]) == 1 and self.direct(self.rhs[e][0])
        last = [c for c in self.focal.finditer(me)]
        return bool(last) and close(me, last[-1].end() - 1) == len(me) - 1 and not re.search(r"[&|?=<>+]", me[:last[-1].start()])

    def assertions(self):
        """[(kind, marked, start, end)] in order."""
        out, m, code = [], self.m, self.code
        for a in re.finditer(r"(?:(?<=Assert\.)|(?<![\w$.]))(assert\w*|fail)\s*\(|\.\s*expect\s*\(", m[self.s:self.e]):
            st = self.s + a.start(); p = self.s + a.end() - 1; q = close(m, p)
            fn = (a.group(1) or "expect")
            args = [m[x:y] for x, y in split_args(m, p + 1, q)]
            if fn in ("fail", "assertThrows", "expect") or any(re.search(r"(?<![\w$.])" + re.escape(c) + r"\b", " ".join(args)) for c in self.caught):
                kind = "THROWS"  # also assertions on a caught exception (its message)
            elif fn in ("assertEquals", "assertSame", "assertArrayEquals") and len(args) >= 2:
                if len(args) == 4 or len(args) == 3 and args[0].strip().startswith('"'):
                    args = args[1:]
                kind = self.eq(args[0], args[1])
            elif fn in ("assertTrue", "assertFalse", "assertNull") and args:
                e = strip_parens(args[-1]); me = mask(e)
                eqm = re.fullmatch(r"(.*?)\s*(==|!=)\s*(.*)", me) if me.count("==") + me.count("!=") == 1 and not re.search(r"&&|\|\|", me) else None
                dot = re.fullmatch(r"(.*)\.equals\s*\((.*)\)", me, re.S)
                if eqm:
                    kind = self.eq(eqm.group(1), eqm.group(3))
                elif dot and self.name != "equals" and fn != "assertNull" and len(split_args(dot.group(2), 0, len(dot.group(2)))) == 1 \
                        and close(me, me.rfind(".equals") + me[me.rfind(".equals"):].find("(")) == len(me) - 1:
                    kind = self.eq(dot.group(1), dot.group(2))
                else:
                    kind = "LITERAL" if self.direct(e) else "RELATION"
            elif fn == "assertThat" and len(args) >= 2:
                mt = re.fullmatch(r"\s*(?:is|equalTo|sameInstance)\s*\((.*)\)\s*", args[-1], re.S)
                kind = self.eq(args[-2], mt.group(1)) if mt else "RELATION"
            else:
                kind = "RELATION"
            end = m.find(";", q); end = q if end < 0 else end
            l0 = code.rfind("\n", 0, st) + 1; lp = code.rfind("\n", 0, max(0, l0 - 1)) + 1
            l1 = code.find("\n", end); l1 = len(code) if l1 < 0 else l1
            above = code[lp:l0].strip()  # a comment-only line just above the assertion
            marked = bool(MARK.search(code[l0:l1])) or above.startswith("//") and bool(MARK.search(above))
            out.append((kind, marked, st, end))
        return out


def java_of(completion):
    return "\n".join(re.findall(r"```java(.*?)```", completion or "", re.DOTALL))


def classify(completion, name):
    """{test name: {"kinds": [(kind, marked)], "src": text}} for one completion."""
    code = java_of(completion); m = mask(code)
    ts = tests(code)
    cls_m = list(m)
    for _, _, s, e in ts:
        cls_m[s:e + 1] = " " * (e + 1 - s)
    cls_m = "".join(cls_m)
    helpers = {}
    for h in re.finditer(r"(?:^|[;{}]|\n)\s*(?:(?:public|private|protected|static|final|synchronized)\s+)*[\w$<>\[\],.?]+(?:\s*\[\])*\s+([\w$]+)\s*\([^()]*\)\s*(?:throws[^{;]*)?\{", cls_m):
        if h.group(1) not in ("if", "for", "while", "switch", "catch", "synchronized"):
            helpers[h.group(1)] = cls_m[h.end() - 1:close(cls_m, h.end() - 1, "{", "}") + 1]
    res = {}
    for t, ann, s, e in ts:
        T = Test(code, m, s, e, name, cls_m, helpers)
        asserts = T.assertions()
        kinds = [(k, mk) for k, mk, _, _ in asserts]
        if "expected" in ann:
            kinds.append(("THROWS", False))
        res[t] = {"kinds": kinds, "src": code[s:e + 1], "marked_text": [code[a:b + 1] for k, mk, a, b in asserts if k == "LITERAL" and mk]}
    return res


def summary(per_test):
    """counts over tests: ≥1 LITERAL, ≥1 unmarked LITERAL, ≥1 marked, only THROWS, no assertion; assertion kinds."""
    t = list(per_test)
    lit = [x for x in t if any(k == "LITERAL" for k, _ in x["kinds"])]
    unm = [x for x in t if any(k == "LITERAL" and not mk for k, mk in x["kinds"])]
    mk = [x for x in t if any(k == "LITERAL" and mk for k, mk in x["kinds"])]
    kinds = Counter(k for x in t for k, _ in x["kinds"])
    return {"tests": len(t), "lit": len(lit), "unmarked": len(unm), "marked": len(mk),
            "throws_only": sum(bool(x["kinds"]) and all(k == "THROWS" for k, _ in x["kinds"]) for x in t),
            "no_assert": sum(not x["kinds"] for x in t), "kinds": dict(kinds)}


def label(x):
    """per-test form label: LITERAL (unmarked), LITERAL-marked, RELATION, THROWS, NONE."""
    ks = x["kinds"]
    if any(k == "LITERAL" and not mk for k, mk in ks):
        return "LITERAL"
    if any(k == "LITERAL" for k, _ in ks):
        return "LITERAL-marked"
    if any(k == "RELATION" for k, _ in ks):
        return "RELATION"
    return "THROWS" if ks else "NONE"


def report(fpf):
    names = {r["source:source_method_signature"]: r["source:source_method_name"] for r in map(json.loads, open(SRC))}
    recs = [json.loads(l) for l in open(RQ1.format(fpf))]
    allt = [x for r in recs for x in classify(r["completion"], names[r["method_signature"]]).values()]
    s = summary(allt)
    pct = lambda k: f"{s[k]} ({100 * s[k] / max(1, s['tests']):.1f}%)"
    print(f"{fpf}: {len(recs)} completions, {s['tests']} @Test methods; tests with ≥1 LITERAL {pct('lit')}, ≥1 unmarked LITERAL "
          f"{pct('unmarked')}, ≥1 marked LITERAL {pct('marked')}, THROWS only {pct('throws_only')}, no assertion {pct('no_assert')}; "
          f"assertions {s['kinds']}; per-test labels {dict(Counter(label(x) for x in allt))}")
    return s


def selftest():
    code = """
    @Test public void a() {
        assertEquals("a\\\\tb", StringEscapeUtils.escapeJava("a\\tb"));
        String in = "x\\ty"; String out = StringEscapeUtils.escapeJava(in);
        assertEquals(in, StringEscapeUtils.unescapeJava(out));
        assertEquals(StringEscapeUtils.escapeJava(in), out);
        assertTrue(out.length() >= in.length());
        String exp = "q";
        assertEquals(exp, out); // from Javadoc
        assertNull(StringEscapeUtils.escapeJava(null));
        assertNotNull(StringEscapeUtils.escapeJava(""));
        assertEquals("msg", Integer.valueOf(3), out.length());
    }
    @Test(expected = IllegalArgumentException.class)
    public void b() throws Exception { StringEscapeUtils.escapeJava(null); }
    @Test public void c() {
        StringWriter sw = new StringWriter(); JsonWriter w = new JsonWriter(sw);
        w.beginArray(); w.escapeJava(1L); w.endArray();
        assertEquals("[1]", sw.toString());
        try { StringEscapeUtils.escapeJava(null); fail("x"); } catch (Exception e) { }
        assertArrayEquals(new String[]{"a", "b"}, new String[]{StringEscapeUtils.escapeJava("a"), "b"});
        assertTrue(StringEscapeUtils.escapeJava("a") == "a");
        assertTrue(!StringEscapeUtils.escapeJava("a").isEmpty());
        StrBuilder sb = new StrBuilder(); sb.append("x").escapeJava("y", 3);
        assertEquals("xy", sb.toString());
        Assert.assertEquals((Object) ("x"), StringEscapeUtils.escapeJava("x"));
    }
    """
    r = classify(f"```java{code}```", "escapeJava")
    assert [k for k, _ in r["a"]["kinds"]] == ["LITERAL", "RELATION", "RELATION", "RELATION", "LITERAL", "LITERAL", "RELATION", "LITERAL"], r["a"]["kinds"]
    assert [mk for _, mk in r["a"]["kinds"]] == [False, False, False, False, True, False, False, False]
    assert r["b"]["kinds"] == [("THROWS", False)]
    assert [k for k, _ in r["c"]["kinds"]] == ["LITERAL", "THROWS", "LITERAL", "LITERAL", "RELATION", "LITERAL", "LITERAL"], r["c"]["kinds"]
    m = mask("x = a.b(c, d(e)).f( ; y = new X().f( ; z = Cls.f( ; w = f( ; v = this.p.f(")
    assert [chain_head(m, k.start()) for k in re.finditer(r"f\(", m)] == ["a", None, "Cls", None, "p"]
    code = """
    private StringWriter sw = new StringWriter(); private JsonWriter jw;
    @Before public void setUp() { jw = new JsonWriter(sw); }
    @Test public void d() { jw.name("k").escapeJava(1); assertEquals("{1", sw.toString());
        Map<String, Integer> exp = new LinkedHashMap<>(); exp.put("a", 0);
        assertEquals(exp, StringUtils.escapeJava("a"));
        assertTrue(StringUtils.equals("a", "a")); }
    """
    assert [k for k, _ in classify(f"```java{code}```", "escapeJava")["d"]["kinds"]] == ["LITERAL", "LITERAL", "RELATION"]
    assert [k for k, _ in classify(f"```java{code}```", "equals")["d"]["kinds"]] == ["RELATION", "RELATION", "LITERAL"]
    code = """
    private static final String SEP = System.getProperty("line.separator"); private String nl = System.lineSeparator();
    private Fraction frac(int a, int b) { return Fraction.getFraction(a, b); }
    private String roundTrip(String s) { return StringEscapeUtils.unescapeJava(StringEscapeUtils.escapeJava(s)); }
    @Test public void e() { assertEquals(frac(1, 2), frac(2, 4).reduce()); assertEquals("ab", roundTrip("ab"));
        assertEquals("a" + nl + "b", StringEscapeUtils.escapeJava("x")); assertEquals("ab".length(), StringEscapeUtils.escapeJava("ab").length());
        assertEquals(String.class, StringEscapeUtils.escapeJava("a").getClass());
        try { StringEscapeUtils.escapeJava(null); } catch (IllegalArgumentException ex) { assertEquals("m", ex.getMessage()); } }
    """
    r2 = classify(f"```java{code}```", "reduce")["e"]["kinds"]
    assert [k for k, _ in r2][:1] == ["LITERAL"], r2
    r2 = classify(f"```java{code}```", "escapeJava")["e"]["kinds"]
    assert [k for k, _ in r2] == ["RELATION", "LITERAL", "LITERAL", "LITERAL", "LITERAL", "THROWS"], r2
    assert label(r["a"]) == "LITERAL" and label(r["b"]) == "THROWS"
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        for f in sys.argv[1:] or ["m7_prop", "m7_example"]:
            report(f)
