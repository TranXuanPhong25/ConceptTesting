"""Phase 0b gap extractor (PILOT_PLAN.md 'Phase 0b amendment', X0b). Reuses gaps.py unchanged (gap kinds, guard
categories, protection logic) and widens only its reach:
  X1 helper inlining depth 2 -> 4 (per-API size cap; capped APIs are counted, not gaps)
  X2 symbol index over TF core/{kernels,framework,util} and ATen native + ATen top level + c10/core
  X3 cross-file resolution: same stem -> #include closure (depth <= 3, header + .cc twin) -> unique definition
  X4 class definitions merged across same-stem / included files (out-of-line Foo::Compute)
  X5 registration/structured macros expanded at invocation sites; template aliases (using/typedef) resolved
Also records, per kind-3 gap, what V0b needs from the read site: literal index, index variable (-> attr), casts.
Outputs (never overwrites Phase 0): out/gap_raw_{tf,torch}_0b.json, out/gaps_0b.jsonl, out/gap_index_0b.json, and
out/gap_index_p0v0b.json (Phase 0 gaps + V0b vocabulary, for the vocabulary-vs-reach split).
usage (container, NOCREDS=1): /opt/pilot/bin/python run/gaps_ext.py [tf] [torch] [assemble]"""
import glob, json, os, re, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gaps as G
from cpp import calls, index_file, match_close, param_names, split_top, strip_comments

DEPTH = 4
CAP = 300_000  # chars of inlined text per API; ponytail: crude bound on exponential inlining, raise if many APIs cap
TFROOT = f"{HERE}/cache/tf"
OUT = G.OUT
STEM = re.compile(r"(_impl|_util|_utils|_common|_base|_op|_ops)?(_\d+[a-z]?)?\.(cc|h|cpp)$")
CAST = re.compile(r"(?:static_cast|reinterpret_cast|bit_cast|saturate_cast)\s*<\s*([\w:]+)\s*>\s*\(\s*$")


def stem(f):
    return STEM.sub("", f)


def macro_defs(src):
    """{name: (params, body)} for function-like #defines (comment-stripped text)."""
    out = {}
    for m in re.finditer(r"(?m)^[ \t]*#[ \t]*define[ \t]+(\w+)\(([^)]*)\)((?:[^\n]*\\\n)*[^\n]*)", src):
        out[m.group(1)] = ([p.strip() for p in m.group(2).split(",") if p.strip()], m.group(3).replace("\\\n", " "))
    return out


class Macros:
    """Expand function-like macros whose expansion reaches one of `roots` (REGISTER_KERNEL_BUILDER / TORCH_*_FUNC)."""

    def __init__(self, defs_by_file, roots, closure):
        self.defs, self.closure = defs_by_file, closure
        names = defaultdict(list)
        for f, ds in defs_by_file.items():
            for n, d in ds.items():
                names[n].append((f, d))
        reach = {n for n, ds in names.items() if any(re.search(roots, d[1]) for _, d in ds)}
        while True:  # fixpoint: macros that invoke a reaching macro reach too
            alt = re.compile(r"\b(?:" + "|".join(map(re.escape, reach)) + r")\s*\(") if reach else None
            new = {n for n, ds in names.items() if n not in reach and alt and any(alt.search(d[1]) for _, d in ds)}
            if not new:
                break
            reach |= new
        self.names, self.reach = names, reach
        self.re = r"|".join(map(re.escape, sorted(reach, key=len, reverse=True))) if reach else None

    def pick(self, name, f):
        ds = self.names.get(name, [])
        mine = [d for g, d in ds if g == f] or [d for g, d in ds if g in self.closure(f)]
        return (mine or ([ds[0][1]] if len(ds) == 1 else [None]))[0]

    def expand(self, text, f, depth=0):
        if depth >= 4 or not self.re:
            return text
        out, last = [], 0
        for start, name, args, end in calls(text, self.re):
            if start < last or re.search(r"#\s*define\s+$", text[max(0, start - 30):start]):
                continue
            d = self.pick(name, f)
            if d is None:
                continue
            params, body = d
            al = split_top(args) if args.strip() else []
            sub = dict(zip([p for p in params if p != "..."], al))
            if "..." in params:
                sub["__VA_ARGS__"] = ", ".join(al[len(params) - 1:])
            if sub:
                body = re.sub(r"(?<![\w#])#\s*(" + "|".join(map(re.escape, sub)) + r")\b", lambda m: f'"{sub[m.group(1)]}"', body)
                body = re.sub(r"(?<!\w)(" + "|".join(map(re.escape, sub)) + r")(?!\w)", lambda m: sub[m.group(1)], body)
            body = re.sub(r"\s*##\s*", "", body)
            out += [text[last:start], " ", self.expand(body, f, depth + 1), " "]
            last = end
        out.append(text[last:])
        return "".join(out)


class Budget:
    def reset(self):
        self.size, self.capped = 0, False

    def take(self, n):
        self.size += n
        if self.size > CAP:
            self.capped = True
        return not self.capped


# ======================================================================================================== TF
class TFIndex0b(G.TFIndex):
    def __init__(self):
        self.ops = G.tf_ops()
        self._unique = self._umeth = None
        self._cl = {}
        self.reg, self.classes, self.funcs, self.consts, self.srcs = defaultdict(set), defaultdict(list), {}, {}, {}
        self.includes, self.alias, self.budget, self.capped, self.attrs, self.read_info = {}, {}, Budget(), set(), {}, {}
        kern = sorted(glob.glob(f"{G.TFC}/kernels/**/*.cc", recursive=True) + glob.glob(f"{G.TFC}/kernels/**/*.h", recursive=True))
        extra = sorted(f for d in ("framework", "util") for ext in ("cc", "h")
                       for f in glob.glob(f"{G.TFC}/{d}/**/*.{ext}", recursive=True))
        skip = re.compile(r"_test\.cc$|_benchmark|test_util|_gpu\.cu|_testlib|fuzz")
        kern, extra = [f for f in kern if not skip.search(G.rel(f))], [f for f in extra if not skip.search(G.rel(f))]
        mdefs = {}
        for f in kern + extra:
            raw = open(f, errors="replace").read()
            self.includes[f] = [p for p in (f"{TFROOT}/{i}" for i in re.findall(r'#include\s+"(tensorflow/core/[^"]+)"', raw))
                                if os.path.exists(p)]
            src, fs, cls = index_file(f)
            self.srcs[f] = src
            self.funcs[f] = defaultdict(list)
            for fn in fs:
                fn["file"] = f
                self.funcs[f][fn["name"]].append(fn)
            for c, info in cls.items():
                for ds in info["methods"].values():
                    for d in ds:
                        d["file"] = info["file"]
                self.classes[c].append(info)
            self.consts[f] = {m.group(1): int(m.group(2)) for m in re.finditer(
                r"\b(?:constexpr|const)\s+(?:static\s+)?(?:int|int32|int64|int32_t|int64_t|size_t)\s+(\w+)\s*=\s*(\d+)\s*;", src)}
            mdefs[f] = macro_defs(src)
            for m in re.finditer(r"\busing\s+(\w+)\s*=\s*(?:typename\s+)?([\w:]+)\s*[<;]", src):
                self.alias.setdefault(m.group(1), m.group(2).split("::")[-1])
            for m in re.finditer(r"\btypedef\s+(?:typename\s+)?([\w:]+)\s*(?:<[^;{}]*>)?\s+(\w+)\s*;", src):
                self.alias.setdefault(m.group(2), m.group(1).split("::")[-1])
        self.macros = Macros(mdefs, r"\bREGISTER_KERNEL_BUILDER\b", self.closure)
        for f in kern:
            text = self.macros.expand(self.srcs[f].replace("\\\n", "  "), f)
            for _, _, args, _ in calls(text, r"REGISTER_KERNEL_BUILDER"):
                parts = split_top(args)
                builder, cls_expr = parts[0], ",".join(parts[1:])
                if re.search(r"DEVICE_(?:GPU|TPU|DEFAULT)\b", builder) and "DEVICE_CPU" not in builder:
                    continue
                for op in re.findall(r'Name\(\s*"(\w+)"\s*\)', builder):
                    cname = re.sub(r"<.*", "", cls_expr.strip().lstrip("("), flags=re.S).split("::")[-1].strip(" ()")
                    if re.fullmatch(r"\w+", cname or ""):
                        self.reg[op].add((cname, f))

    def closure(self, f, depth=3):
        if f in self._cl:
            return self._cl[f]
        seen, frontier = set(), [f]
        for _ in range(depth):
            nxt = []
            for g in frontier:
                for h in self.includes.get(g, []):
                    for x in (h, re.sub(r"\.h$", ".cc", h)):
                        if x not in seen and x in self.includes:
                            seen.add(x)
                            nxt.append(x)
            frontier = nxt
        self._cl[f] = seen
        return seen

    def related_files(self, file):
        return super().related_files(file) + sorted(self.closure(file))

    def near_funcs(self, file, name, nargs=None):
        if not hasattr(self, "_by_stem"):
            self._by_stem = defaultdict(list)
            for f in self.funcs:
                self._by_stem[stem(f)].append(f)
        near = [d for f in self._by_stem[stem(file)] if f != file for d in self.funcs[f].get(name, [])]
        if not near:
            near = [d for f in sorted(self.closure(file)) for d in self.funcs.get(f, {}).get(name, [])]
        if not near:
            if self._unique is None:
                cnt = defaultdict(list)
                for fs in self.funcs.values():
                    for n, d in fs.items():
                        cnt[n] += d
                self._unique = {n: d for n, d in cnt.items() if len(d) == 1}
            near = self._unique.get(name) or []
        if nargs is not None and len(near) > 1:
            near = sorted(near, key=lambda d: abs(len(param_names(d["params"])) - nargs))
        return near or None

    def chain(self, cname, near, seen=None):
        seen = seen or set()
        if cname not in self.classes and cname in self.alias:
            cname = self.alias[cname]
        if cname in seen:
            return []
        seen.add(cname)
        infos = self.classes.get(cname, [])
        if not infos:
            return []
        cl = self.closure(near)
        infos = sorted(infos, key=lambda i: (i["file"] != near, i["file"] not in cl,
                                             os.path.dirname(i["file"]) != os.path.dirname(near)))
        first = infos[0]
        group = [first] + [i for i in infos[1:] if stem(i["file"]) == stem(first["file"]) or i["file"] in cl]
        merged = {"file": first["file"], "bases": [], "methods": defaultdict(list)}
        for i in group:
            merged["bases"] += [b for b in i["bases"] if b not in merged["bases"]]
            for m, ds in i["methods"].items():
                merged["methods"][m] += ds
        out = [merged]
        for b in merged["bases"]:
            out += self.chain(b, merged["file"], seen)
        return out

    def kernel(self, op):
        self.budget.reset()
        self.cur_op = op
        regs = sorted(self.reg.get(op, []))
        if not regs:
            return "no_cpu_kernel_registration"
        for cname, f in regs:
            ch = self.chain(cname, f)
            methods = defaultdict(list)
            for info in ch:
                for m, defs in info["methods"].items():
                    methods[m] += defs
            comp = methods.get("Compute") or methods.get("ComputeAsync")
            if not comp:
                continue
            file = ch[0]["file"]
            self.attrs[op] = {m.group(2): m.group(1) for ds in methods.values() for d in ds
                              for m in re.finditer(r'GetAttr\(\s*"(\w+)"\s*,\s*&\s*(\w+)\s*\)', d["body"])}
            text = self.expand(comp[0]["body"], comp[0].get("file", file), methods, 0, {"Compute", "ComputeAsync"})
            if self.budget.capped:
                self.capped.add(op)
            return text, file, cname
        return "kernel_class_or_compute_not_found"

    def expand(self, body, file, methods, depth, stack):
        if depth >= DEPTH:
            return body
        out, last = [], 0
        for start, name, args, end in calls(body, r"[A-Za-z_]\w*"):
            if start < last or name in stack or name in G.STOP:
                continue
            member = re.match(r"[.>]", body[max(0, start - 1):start]) and not body[:start].rstrip().endswith("this->")
            nargs = len(split_top(args)) if args.strip() else 0
            defs = (self.unique_methods().get(name) if G.HELPERISH.search(name) else None) if member else \
                (methods.get(name) or self.funcs.get(file, {}).get(name) or self.near_funcs(file, name, nargs))
            if not defs or len(defs[0]["body"]) > 30000 or not self.budget.take(len(defs[0]["body"])):
                continue
            fn = defs[0]
            sub = fn["body"]
            for p, a in zip(param_names(fn["params"]), split_top(args) if args.strip() else []):
                if p != a:
                    sub = re.sub(rf"(?<![\w.>]){re.escape(p)}\b",
                                 a if re.fullmatch(r"[\w\->().\[\]*&: ]+", a) else "__opaque__", sub)
            out.append(body[last:end])
            sub = sub.strip()
            sub = sub[1:-1] if sub.startswith("{") and sub.endswith("}") else sub
            out.append("; " + self.expand(sub, fn.get("file", file), methods, depth + 1, stack | {name}) + " ;")
            last = end
        out.append(body[last:])
        return "".join(out)


_tf_reads0 = G.tf_reads


def tf_reads_recording(E, v):
    """gaps.tf_reads plus side info for V0b (literal index, index variable, reinterpreting cast); keyed per op/read."""
    out = _tf_reads0(E, v)
    ix = TF_IX
    for pos, need, text in out:
        info = {}
        m = re.search(r"dim_size\(\s*((?:[^()]|\([^()]*\))*)\)", text)
        if m:
            k = m.group(1).strip()
            if k.isdigit():
                info["read_index"] = int(k)
            elif re.fullmatch(r"\w+", k):
                info["index_var"] = k
                info["index_attr"] = ix.attrs.get(ix.cur_op, {}).get(k)
        c = CAST.search(E[max(0, pos - 60):pos])
        t = re.match(r"[\w>.\-\s]*?(?:scalar|vec|matrix|flat|tensor)\s*<\s*([\w:]+)", E[pos:pos + 120])
        if c and t:
            info["reinterpret"] = {"to": c.group(1), "from_T": t.group(1)}
        ix.read_info[(ix.cur_op, text.strip())] = info
    return out


# ===================================================================================================== torch
class TorchIndex0b(G.TorchIndex):
    def __init__(self):
        super().__init__()
        self.budget, self.capped_names = Budget(), set()
        extra = sorted(glob.glob(f"{HERE}/cache/torch/aten/src/ATen/*.cpp") + glob.glob(f"{HERE}/cache/torch/aten/src/ATen/*.h")
                       + glob.glob(f"{HERE}/cache/torch/c10/core/**/*.h", recursive=True)
                       + glob.glob(f"{HERE}/cache/torch/c10/core/**/*.cpp", recursive=True))
        for f in extra:
            _, fs, _ = index_file(f)
            for fn in fs:
                fn["file"] = f
                self.funcs[fn["name"].split("::")[-1]].append(fn)
        native = sorted(glob.glob(f"{G.ATEN}/**/*.cpp", recursive=True) + glob.glob(f"{G.ATEN}/**/*.h", recursive=True))
        native = [f for f in native if not re.search(r"/(cuda|mps|vulkan|metal|miopen|cudnn|nested|mkldnn|xnnpack|"
                                                     r"quantized/cuda|hip|sparse/cuda|transformers/cuda)/", f)]
        srcs = {f: strip_comments(open(f, errors="replace").read()) for f in native}
        mac = Macros({f: macro_defs(s) for f, s in srcs.items()}, r"\bTORCH_(?:META|IMPL|PRECOMPUTE_META)_FUNC2?\b",
                     lambda f: set())
        self.n_macro_structured = 0
        for f, s in srcs.items():
            if not mac.re or not re.search(r"\b(?:" + mac.re + r")\s*\(", s):
                continue
            src = mac.expand(s, f)
            for m in re.finditer(r"TORCH_(META|IMPL|PRECOMPUTE_META)_FUNC2?\s*\(\s*(\w+)(?:\s*,\s*(\w+))?\s*\)\s*\(", src):
                o = m.end() - 1
                e = match_close(src, o)
                b = src.find("{", e)
                if b < 0 or src[e:b].strip() not in ("", "const"):
                    continue
                key = m.group(2) + ("." + m.group(3) if m.group(3) else "")
                tbl = self.impl if m.group(1) == "IMPL" else self.meta
                if not tbl.get(key):
                    tbl[key].append({"params": src[o:e], "body": src[b:match_close(src, b)], "file": f})
                    self.n_macro_structured += 1

    def code(self, ov, depth=0, stack=frozenset()):
        if depth == 0:
            self.budget.reset()
        r = super().code(ov, depth, stack)
        if depth == 0 and self.budget.capped:
            self.capped_names.add(ov["name"])
        return r

    def expand(self, body, depth, stack):
        if depth >= DEPTH:
            return body
        out, last = [], 0
        for start, name, args, end in calls(body, r"[A-Za-z_]\w*"):
            if start < last or name in stack or name in G.TORCH_STOP or re.match(r"[.>]", body[max(0, start - 1):start]):
                continue
            defs = self.funcs.get(name)
            nargs = len(split_top(args)) if args.strip() else 0
            name = re.sub(r"_symint$", "", name)
            base_name, outv = re.sub(r"_outf?$", "", name), re.search(r"_(outf?)$", name)
            if (not defs or body[max(0, start - 4):start] == "at::") and (self.by_base.get(name) or
                                                                         (outv and self.by_base.get(base_name))):
                cands = self.by_base.get(name) or [o for o in self.by_base[base_name]
                                                   if any("!" in t for t in o["ptypes"].values())]
                if not cands or not self.budget.take(2000):
                    continue
                ov = sorted(cands, key=lambda o: (abs(len(o["params"]) - nargs), "dimname" in o["overload"].lower()))[0]
                outs = [x for x, t in ov["ptypes"].items() if "!" in t and x != "self"]
                ins = [x for x in ov["params"] if x not in outs] if outv else ov["params"]
                al = split_top(args) if args.strip() else []
                al = (al[len(outs):] if outv and outv.group(1) == "out" else al[:len(al) - len(outs)] if outv else al)
                if ov["name"] not in stack:
                    sub, _ = self.code(ov, depth + 1, stack | {name, ov["name"]})
                    for p, a in zip(ins, al):
                        if p != a:
                            sub = re.sub(rf"(?<![\w.>]){re.escape(p)}\b",
                                         a if re.fullmatch(r"[\w.()\-> ]+", a) else "__opaque__", sub)
                    out.append(body[last:end])
                    out.append("; " + sub + " ;")
                    last = end
                continue
            if not defs or len(defs) > 6:
                continue
            fn = sorted(defs, key=lambda d: abs(len(param_names(d["params"])) - nargs))[0]
            if len(fn["body"]) > 20000 or not self.budget.take(len(fn["body"])):
                continue
            sub = fn["body"]
            for p, a in zip(param_names(fn["params"]), split_top(args) if args.strip() else []):
                if p != a:
                    sub = re.sub(rf"(?<![\w.>]){re.escape(p)}\b", a if re.fullmatch(r"[\w.()\-> ]+", a) else "__opaque__", sub)
            sub = sub.strip()
            sub = sub[1:-1] if sub.startswith("{") and sub.endswith("}") else sub
            out.append(body[last:end])
            out.append("; " + self.expand(sub, depth + 1, stack | {name}) + " ;")
            last = end
        out.append(body[last:])
        return "".join(out)


# ================================================================================================== mapping
def torch_family(api):
    p = api.split(".")
    if api.startswith("torch.Tensor.") or api.startswith("torch.nn.functional."):
        b = p[-1]
    elif len(p) == 3 and p[1] in ("fft", "linalg", "special"):
        b = f"{p[1]}_{p[2]}"
    else:
        b = p[-1]
    return b.rstrip("_")


def excluded(api, ex, bug_fams, torch_bug_fams):
    """known-bug API or alias (gaps.excluded_apis) or sibling family (TF tf_family, torch base name)."""
    if api in ex:
        return "known_bug_or_alias"
    if api.startswith("tf.raw_ops.") and G.tf_family(api.split(".")[-1]) in bug_fams:
        return "sibling_family"
    if api.startswith("torch") and torch_family(api) in torch_bug_fams:
        return "sibling_family"
    return None


def assemble(raw_tf, raw_torch, suffix, write_gaps=True):
    """Map gaps to DFUZZ roles with released (Phase 0) and V0b candidates; write gap_index{suffix}.json (+ gaps)."""
    from edgecases import best_released
    from edgecases_ext import axis_candidate, candidates
    tres, tfsa = raw_tf["tf"], raw_tf["tfsa"]
    pres = raw_torch["torch"]
    ex = G.excluded_apis()
    bug_fams = {G.tf_family(a.split(".")[-1]) for a in ex if a.startswith("tf.raw_ops.")}
    torch_bug_fams = {torch_family(a) for a in G.KNOWN_BUG_APIS if a.startswith("torch")}
    renames = json.load(open(f"{OUT}/tf_arg_renames.json"))
    index, lines = {}, []
    for lib, short in (("tensorflow", "tf"), ("torch", "torch")):
        info = json.load(open(f"{G.ROOT}/get_api_reference/results/{lib}/apis_info.json"))
        progs = json.load(open(f"{G.ROOT}/gen_program/results/{short}/api_programs.json"))
        for api in sorted(progs):
            if short == "tf":
                if not api.startswith("tf.raw_ops."):
                    continue
                r = tres.get(api.split(".")[-1], {"status": "no_REGISTER_OP", "gaps": []})
            else:
                r = pres.get(api, {"status": "no_native_function", "gaps": []})
            params = info.get(api) or {}
            ren = renames.get(api.split(".")[-1], {}) if short == "tf" else {}
            gl = []
            for g in r["gaps"]:
                role = ren.get(g["param"], g["param"])
                if role not in params and role == "self" and "input" in params:
                    role = "input"
                ptype = params.get(role)
                g = {**g, "role": role}
                if "read_index" not in g and g.get("read"):  # Phase 0 records: literal index from the read text
                    m = re.search(r"(?:dim_size\(|sizes\(\)\s*\[|strides\(\)\s*\[)\s*(\d+)\s*[)\]]", g["read"])
                    if m:
                        g["read_index"] = int(m.group(1))
                if short == "torch" and g.get("read") and "index_var" not in g:
                    m = re.search(r"(?:sizes|strides)\(\)\s*\[\s*(\w+)\s*\]", g["read"])
                    if m and not m.group(1).isdigit():
                        g["index_var"] = g["index_attr"] = m.group(1)
                rel = best_released(ptype or "Tensor", g.get("need"), g["cat"])
                other = None
                if g["cat"] == "merge" and g.get("need") and len(g["need"]) > 1 and g["need"][1]:
                    o = ren.get(g["need"][1], g["need"][1])
                    other = o if o in params else None
                cands = candidates(g, ptype or "Tensor", other, rel)
                ir = g.get("index_attr") or (g.get("index_var") or "").rstrip("_") or None
                ir = ren.get(ir, ir) if ir else None
                if ir in params:
                    ax = axis_candidate(g, ir, params[ir])
                    if ax:
                        cands.insert(sum(c["tier"] == 0 for c in cands), ax)
                rec = {"api": api, "lib": short, **g, "dfuzz_type": ptype, "role_in_dfuzz": role in params,
                       "edge_case": rel, "candidates": cands}
                gl.append(rec)
                lines.append(rec)
            exc = excluded(api, ex, bug_fams, torch_bug_fams)
            index[api] = {"lib": short, "status": r["status"], "seeded": progs[api] != "none", "n_gaps": len(gl),
                          "n_gaps_mapped_released": sum(1 for g in gl if g["role_in_dfuzz"] and g["edge_case"]),
                          "n_gaps_mapped": sum(1 for g in gl if g["role_in_dfuzz"] and g["candidates"]),
                          "kinds": sorted({g["kind"] for g in gl}), "excluded": exc,
                          "known_bug_or_alias": exc == "known_bug_or_alias",
                          "tfsa": tfsa.get(api.split(".")[-1], []) if short == "tf" else [], "capped": r.get("capped", False)}
    if write_gaps:
        with open(f"{OUT}/gaps{suffix}.jsonl", "w") as f:
            for rec in lines:
                f.write(json.dumps(rec) + "\n")
    json.dump(index, open(f"{OUT}/gap_index{suffix}.json", "w"), indent=0)
    report(index, suffix)
    return index


def report(index, suffix):
    print(f"--- gap_index{suffix}.json")
    for lib in ("tf", "torch"):
        seeded = [a for a, v in index.items() if v["lib"] == lib and v["seeded"]]
        st = defaultdict(int)
        for a in seeded:
            st[index[a]["status"]] += 1
        g = sum(1 for a in seeded if index[a]["n_gaps"])
        mr = sum(1 for a in seeded if index[a]["n_gaps_mapped_released"])
        mv = sum(1 for a in seeded if index[a]["n_gaps_mapped"])
        mvx = sum(1 for a in seeded if index[a]["n_gaps_mapped"] and not index[a]["excluded"])
        print(f"{lib}: seeded={len(seeded)} status={dict(st)} with_gap={g} ({g / len(seeded):.1%}) "
              f"mapped_released={mr} mapped_v0b={mv} mapped_v0b_not_excluded={mvx} capped={sum(index[a]['capped'] for a in seeded)}")
    seeded = [a for a, v in index.items() if v["seeded"]]
    g = sum(1 for a in seeded if index[a]["n_gaps"])
    print(f"pooled: with_gap {g}/{len(seeded)} = {g / len(seeded):.1%}; mapped(v0b) not excluded: "
          f"{sum(1 for a in seeded if index[a]['n_gaps_mapped'] and not index[a]['excluded'])}", flush=True)


TF_IX = None

if __name__ == "__main__":
    t = time.time()
    which = sys.argv[1:] or ["tf", "torch", "assemble"]
    if "tf" in which:
        TF_IX = TFIndex0b()
        G.tf_reads = tf_reads_recording
        print(f"TF: {len(TF_IX.ops)} ops, {len(TF_IX.reg)} ops with CPU kernels, {len(TF_IX.macros.reach)} registering "
              f"macros, {len(TF_IX.alias)} aliases ({time.time() - t:.0f}s)", flush=True)
        tres = G.tf_analyse(TF_IX)
        for op, r in tres.items():
            r["capped"] = op in TF_IX.capped
            for g in r["gaps"]:
                if g["kind"] == 3:
                    g.update(TF_IX.read_info.get((op, g["read"]), {}))
        tfsa = G.tfsa_ops(set(TF_IX.ops))
        json.dump({"tf": tres, "tfsa": tfsa}, open(f"{OUT}/gap_raw_tf_0b.json", "w"))
        st = defaultdict(int)
        for r in tres.values():
            st[r["status"]] += 1
        print(dict(st), "ops with gaps:", sum(bool(r["gaps"]) for r in tres.values()),
              "by kind:", {k: sum(g["kind"] == k for r in tres.values() for g in r["gaps"]) for k in (1, 2, 3)},
              f"capped: {len(TF_IX.capped)} ({time.time() - t:.0f}s)", flush=True)
    if "torch" in which:
        tx = TorchIndex0b()
        apis = sorted(json.load(open(f"{G.ROOT}/gen_program/results/torch/api_programs.json")))
        print(f"torch: {len(tx.entries)} native functions, {sum(map(len, tx.funcs.values()))} C++ defs, "
              f"{tx.n_macro_structured} macro-generated structured defs ({time.time() - t:.0f}s)", flush=True)
        pres = G.torch_analyse(tx, apis)
        for api, r in pres.items():
            r["capped"] = any(o in tx.capped_names for o in r.get("overloads", []))
        json.dump({"torch": pres}, open(f"{OUT}/gap_raw_torch_0b.json", "w"))
        st = defaultdict(int)
        for r in pres.values():
            st[r["status"]] += 1
        print(dict(st), "APIs with gaps:", sum(bool(r["gaps"]) for r in pres.values()),
              "by kind:", {k: sum(g["kind"] == k for r in pres.values() for g in r["gaps"]) for k in (2, 3)},
              f"capped overloads: {len(tx.capped_names)} ({time.time() - t:.0f}s)", flush=True)
    if "assemble" in which:
        p0 = (json.load(open(f"{OUT}/gap_raw_tf.json")), json.load(open(f"{OUT}/gap_raw_torch.json")))
        assemble(*p0, "_p0v0b", write_gaps=True)
        assemble(json.load(open(f"{OUT}/gap_raw_tf_0b.json")), json.load(open(f"{OUT}/gap_raw_torch_0b.json")), "_0b")
