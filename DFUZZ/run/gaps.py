"""Gap extractor (tool-only, no LLM) over TF v2.15 and torch v2.2 sources in run/cache/ (see HARNESS.md for the fetch).

A parameter role (op input / ATen argument) of an API is a gap when
  kind 1 shape_fn_only : TF only. Constrained in the op's shape function (rank / dim value / merge with another input),
                         but no kernel guard on it of a matching category (eager runs the kernel without shape
                         inference: run/out/eager_probe.jsonl).
  kind 2 sibling       : a sibling (TF: V2/V3, Resource*, Experimental* of the same op, input-name Jaccard >= 0.6;
                         torch: out=/inplace/functional overloads of the same base name, Jaccard >= 0.6) guards it in a
                         category the target's own code path does not.
  kind 3 read_before_guard : order-aware: an accessor with a precondition (TF dim_size(k), matrix/vec/tensor<T,N>,
                         scalar; torch sizes()[k], strides()[k], data_ptr) runs before any guard of a protecting
                         category on that input (helpers in the same file / class chain inlined 2 levels deep).
Kernel code is found via REGISTER_KERNEL_BUILDER (CPU) -> class -> Compute (bases followed); ATen code via
native_functions.yaml dispatch (CPU / Composite*) + structured meta/impl. Unresolved code => no gap (precision first).
Writes run/out/gaps.jsonl (one gap per line) and run/out/gap_index.json (per API: resolution status, gaps).
usage (container): /opt/pilot/bin/python run/gaps.py
"""
import glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cpp import calls, index_file, match_close, param_names, split_top, strip_comments

ROOT = os.path.dirname(HERE)
TFC = f"{HERE}/cache/tf/tensorflow/core"
ATEN = f"{HERE}/cache/torch/aten/src/ATen/native"
OUT = f"{HERE}/out"


def rel(path):
    return path.split("/cache/")[-1].split("/", 1)[-1]


def line_of(path, snippet, also=()):
    """'file:line' of the first occurrence of snippet (whitespace-insensitive; __inN = any ctx->input(..)) in path or
    in the fallback files, else None."""
    pat = r"\s*".join(r"\w+\s*(?:->|\.)\s*input\(\s*\w+\s*\)" if re.fullmatch(r"__in\w+", t) else re.escape(t)
                      for t in re.split(r"(__in\w+|\s+)", snippet) if t and not t.isspace())
    for f in (path, *also):
        try:
            src = open(f, errors="replace").read()
        except OSError:
            continue
        m = re.search(pat, src)
        if m:
            return f"{rel(f)}:{src.count(chr(10), 0, m.start()) + 1}"
    return None


# ----------------------------------------------------------------------------------------------- categories
def acc(v):
    return rf"(?<![\w.>]){re.escape(v)}\s*(?:\.|->)\s*"


def guard_cats(v, cond):
    """Categories in which guard condition `cond` constrains variable v."""
    if cond == "__ALL__":
        return {"any"}
    if v != "__inALL" and "__inALL" in cond:
        return guard_cats("__inALL", cond) | guard_cats(v, cond.replace("__inALL", "__in_all"))
    cats = set()
    if re.search(acc(v) + r"(?:dims\(\)|shape\(\)\s*\.\s*dims\(\))", cond) or \
            re.search(r"(?:TensorShapeUtils::)?Is(?:Scalar|Vector|Matrix|SquareMatrix|VectorOrHigher|MatrixOrHigher)\(\s*"
                      + re.escape(v) + r"\s*(?:\.|->)\s*shape\(\)", cond) or \
            re.search(acc(v) + r"(?:dim\(\)|ndimension\(\)|sizes\(\)\s*\.\s*size\(\))", cond):
        cats.add("rank")
    if re.search(acc(v) + r"(?:shape\(\)\s*\.\s*)?dim_size\(|" + acc(v) + r"size\(", cond):
        cats.add("dim")
    if re.search(acc(v) + r"(?:NumElements\(\)|numel\(\)|shape\(\)\s*\.\s*num_elements\(\))", cond):
        cats.add("numel")
    if re.search(acc(v) + r"(?:shape\(\)(?!\s*\.\s*(?:dims|dim_size|num_elements))|sizes\(\)(?!\s*\[)|IsSameSize\()", cond) or \
            re.search(r"IsSameSize\([^)]*\b" + re.escape(v) + r"\b", cond) or \
            re.search(r"\b(?:check_dim_size|checkSameSize|checkDim|checkSize|check_size_nonnegative)\([^;]*\b" + re.escape(v) + r"\b", cond):
        cats.add("shape")
    if re.search(acc(v) + r"(?:dtype\(\)|scalar_type\(\)|is_floating_point\(\)|is_complex\(\))", cond):
        cats.add("dtype")
    if re.search(acc(v) + r"(?:scalar|flat|vec|matrix)\s*<[^>]*>\s*\(\)\s*\(|" + acc(v) + r"(?:item|min|max)\b", cond):
        cats.add("value")
    if not cats and re.search(rf"(?<![\w.>]){re.escape(v)}\b", cond):
        cats.add("any")
    return cats


PROTECTS = {"rank": {"rank", "shape", "any"}, "numel": {"rank", "numel", "shape", "any"},
            "dim": {"dim", "numel", "shape", "any"}, "merge": {"dim", "numel", "shape", "any"}}


# ======================================================================================================== TF
def tf_ops():
    shape_fns = defaultdict(list)
    for f in sorted(glob.glob(f"{TFC}/ops/*.cc")) + [f"{TFC}/framework/common_shape_fns.cc"]:
        _, funcs, _ = index_file(f)
        for fn in funcs:
            shape_fns[fn["name"]].append(fn)
    ops = {}
    for f in sorted(glob.glob(f"{TFC}/ops/*.cc")):
        src = strip_comments(open(f, errors="replace").read())
        for m in re.finditer(r'REGISTER_OP\(\s*"(\w+)"\s*\)', src):
            i = m.end()
            while i < len(src) and src[i] != ";":
                i = match_close(src, i) if src[i] in "([{" else i + 1
            chain = src[m.end():i]
            inputs = [(a.partition(":")[0].strip(), a.partition(":")[2].strip())
                      for a in re.findall(r'\.Input\(\s*"([^"]*)"\s*\)', chain)]
            list_attrs = set(re.findall(r'\.Attr\(\s*"(\w+)\s*:\s*list\(type\)', chain))
            shape = ""
            k = chain.find(".SetShapeFn(")
            if k >= 0:
                o = chain.index("(", k)
                shape = expand_shape(chain[o + 1:match_close(chain, o) - 1], shape_fns, 0)
            ops[m.group(1)] = {"inputs": [n for n, _ in inputs],
                               "islist": ["*" in t or t in list_attrs for _, t in inputs],
                               "shape": shape, "file": f}
    return ops


def expand_shape(arg, shape_fns, depth):
    arg = arg.strip()
    if arg.startswith("[") and "{" in arg:
        body = arg[arg.index("{"):]
    else:
        m = re.search(r"(\w+)\s*(?:\(\s*\))?\s*$", arg)
        body = "\n".join(fn["body"] for fn in shape_fns.get(m.group(1), [])[:1]) if m else ""
    return inline_shape(body, shape_fns, depth)


def inline_shape(body, shape_fns, depth):
    if depth >= 3:
        return body
    extra = []
    for _, name, args, _ in calls(body, r"[A-Za-z_]\w*"):
        if name in shape_fns and re.match(r"\s*c\s*(,|$)", args):
            fn = shape_fns[name][0]
            sub = fn["body"]
            for p, a in zip(param_names(fn["params"]), split_top(args)):
                if p != a and p != "c":
                    sub = re.sub(rf"\b{re.escape(p)}\b", a if re.fullmatch(r"[\w>()\-]+", a) else "__opaque__", sub)
            extra.append(inline_shape(sub, shape_fns, depth + 1))
    return body + "\n".join(extra)


def shape_constraints(S):
    alias = {}
    for m in re.finditer(r"(?:ShapeHandle\s+)?(\w+)\s*=\s*c->input\(\s*(\d+)\s*\)", S):
        alias[m.group(1)] = int(m.group(2))

    def res(e):
        e = e.strip().lstrip("&").strip()
        m = re.fullmatch(r"c->input\(\s*(\d+)\s*\)", e)
        return int(m.group(1)) if m else alias.get(e)

    for _ in range(2):
        for _, nm, args, _ in calls(S, r"WithRank(?:AtLeast|AtMost)?|Merge|WithValue"):
            a = split_top(args)
            if nm.startswith("WithRank") and len(a) >= 3 and res(a[0]) is not None:
                alias.setdefault(a[2].lstrip("&").strip(), res(a[0]))
    cons = []
    for _, nm, args, _ in calls(S, r"WithRank(?:AtLeast|AtMost)?"):
        a = split_top(args)
        if len(a) >= 2 and res(a[0]) is not None:
            r = int(a[1]) if a[1].isdigit() else None
            cons.append({"input": res(a[0]), "cat": "rank", "op": {"WithRank": "eq", "WithRankAtLeast": "ge",
                                                                   "WithRankAtMost": "le"}[nm], "r": r,
                         "text": f"{nm}({args.strip()[:80]})"})

    def dim_of(e):
        m = re.fullmatch(r"\s*c->Dim\((.*)\)\s*", e, re.S)
        if m:
            p = split_top(m.group(1))
            return res(p[0]), p[1] if len(p) > 1 else None
        return res(e), None

    for _, nm, args, _ in calls(S, r"WithValue"):
        a = split_top(args)
        if a:
            i, d = dim_of(a[0])
            if i is not None:
                cons.append({"input": i, "cat": "dim", "dim": d, "v": a[1] if len(a) > 1 else None,
                             "text": f"WithValue({args.strip()[:80]})"})
    for _, nm, args, _ in calls(S, r"Merge"):
        a = split_top(args)
        if len(a) >= 2:
            (i, _), (j, _) = dim_of(a[0]), dim_of(a[1])
            if i is not None and j is not None and i != j:
                for x, y in ((i, j), (j, i)):
                    cons.append({"input": x, "cat": "merge", "with": y, "text": f"Merge({args.strip()[:80]})"})
    return cons


def tf_kernels():
    reg, classes, funcs, consts, srcs = defaultdict(set), defaultdict(list), {}, {}, {}
    files = sorted(glob.glob(f"{TFC}/kernels/**/*.cc", recursive=True) + glob.glob(f"{TFC}/kernels/**/*.h", recursive=True))
    files = [f for f in files if not re.search(r"_test\.cc$|_benchmark|test_util|_gpu\.cu", f)]
    for f in files:
        src, fs, cls = index_file(f)
        srcs[f] = src
        funcs[f] = defaultdict(list)
        for fn in fs:
            funcs[f][fn["name"]].append(fn)
        for c, info in cls.items():
            classes[c].append(info)
        consts[f] = {m.group(1): int(m.group(2)) for m in re.finditer(
            r"\b(?:constexpr|const)\s+(?:static\s+)?(?:int|int32|int64|int32_t|int64_t|size_t)\s+(\w+)\s*=\s*(\d+)\s*;", src)}
        for _, _, args, _ in calls(src.replace("\\\n", "  "), r"REGISTER_KERNEL_BUILDER"):
            parts = split_top(args)
            builder, cls_expr = parts[0], ",".join(parts[1:])
            if re.search(r"DEVICE_(?:GPU|TPU|DEFAULT)\b", builder) and "DEVICE_CPU" not in builder:
                continue
            for op in re.findall(r'Name\(\s*"(\w+)"\s*\)', builder):
                cname = re.sub(r"<.*", "", cls_expr, flags=re.S).split("::")[-1].strip()
                if cname:
                    reg[op].add((cname, f))
    return reg, classes, funcs, consts, srcs


STOP = {"dims", "dim_size", "shape", "NumElements", "num_elements", "dtype", "flat", "vec", "matrix", "scalar", "tensor",
        "status", "ok", "size", "data", "begin", "end", "IsSameSize", "DebugString", "input", "output", "allocate_output",
        "allocate_temp", "eigen_device", "SetStatus", "CtxFailure", "set_output", "name", "type_string", "def"}
HELPERISH = re.compile(r"Valid|Check|Verify|Compute|Calculate|Init|Prepare|Setup|SetUp|Process|^Do[A-Z]|^Run")


class TFIndex:
    def __init__(self):
        self.ops = tf_ops()
        self.reg, self.classes, self.funcs, self.consts, self.srcs = tf_kernels()
        self._unique = None

    def related_files(self, file):
        stem = re.sub(r"(_impl|_util|_utils|_common|_base)?\.(cc|h)$", "", file)
        return [f for f in self.funcs if f != file and (f.startswith(stem) or os.path.dirname(f) == os.path.dirname(file))]

    def near_funcs(self, file, name):
        """Free function defined in a sibling file (same stem, e.g. foo.h/foo.cc/foo_impl.h), else defined exactly once
        across all kernel sources."""
        stem = re.sub(r"(_impl|_util|_utils|_common|_base)?\.(cc|h)$", "", file)
        near = [d for f, fs in self.funcs.items() if f != file and f.startswith(stem) for d in fs.get(name, [])]
        if near:
            return near
        if self._unique is None:
            cnt = defaultdict(list)
            for fs in self.funcs.values():
                for n, d in fs.items():
                    cnt[n] += d
            self._unique = {n: d for n, d in cnt.items() if len(d) == 1}
        return self._unique.get(name)

    def unique_methods(self):
        if getattr(self, "_umeth", None) is None:
            cnt = defaultdict(list)
            for infos in self.classes.values():
                for info in infos:
                    for m, d in info["methods"].items():
                        cnt[m] += d
            self._umeth = {m: d for m, d in cnt.items() if len(d) == 1}
        return self._umeth

    def class_info(self, cname, near):
        infos = self.classes.get(cname, [])
        return sorted(infos, key=lambda i: (i["file"] != near, os.path.dirname(i["file"]) != os.path.dirname(near)))

    def chain(self, cname, near, seen=None):
        """[(class info)] for cname and its bases, nearest file first."""
        seen = seen or set()
        if cname in seen:
            return []
        seen.add(cname)
        infos = self.class_info(cname, near)[:1]
        out = list(infos)
        for i in infos:
            for b in i["bases"]:
                out += self.chain(b, i["file"], seen)
        return out

    def kernel(self, op):
        """-> (expanded Compute text, file, class) or reason string."""
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
            file = ch[0]["file"] if ch else f
            text = self.expand(comp[0]["body"], file, methods, 0, {"Compute", "ComputeAsync"})
            return text, file, cname
        return "kernel_class_or_compute_not_found"

    def expand(self, body, file, methods, depth, stack):
        if depth >= 2:
            return body
        out, last = [], 0
        for start, name, args, end in calls(body, r"[A-Za-z_]\w*"):
            if start < last or name in stack:
                continue
            if name in STOP:
                continue
            member = re.match(r"[.>]", body[max(0, start - 1):start]) and not body[:start].rstrip().endswith("this->")
            defs = (self.unique_methods().get(name) if HELPERISH.search(name) else None) if member else \
                (methods.get(name) or self.funcs.get(file, {}).get(name) or self.near_funcs(file, name))
            if not defs or len(defs[0]["body"]) > 30000:
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
            out.append("; " + self.expand(sub, file, methods, depth + 1, stack | {name}) + " ;")
            last = end
        out.append(body[last:])
        return "".join(out)


def bind_inputs(E, op, consts):
    """Return (E with ctx->input(k) replaced by __in<k>, {var: input_name})."""
    inputs, islist = op["inputs"], op["islist"]

    def name_of(key):
        key = key.strip()
        if key.startswith('"'):
            n = key.strip('"')
            return n if n in inputs else None
        idx = int(key) if key.isdigit() else consts.get(key)
        if idx is None or idx >= len(inputs) or any(islist[:idx + 1]):
            return None
        return inputs[idx]

    var = {}
    E = re.sub(r"\b\w+\s*(?:->|\.)\s*input\(\s*(\w+)\s*\)",
               lambda m: f"__in{m.group(1)}" if name_of(m.group(1)) else
               "__inALL" if not m.group(1).isdigit() and m.group(1) not in consts else m.group(0), E)
    for m in re.finditer(r"__in(\w+)", E):
        var[f"__in{m.group(1)}"] = name_of(m.group(1))
    for m in re.finditer(r"(?:const\s+)?Tensor\s*[&*]?\s*(\w+)\s*(?:=|\()\s*&?\s*(__in\w+)", E):
        var[m.group(1)] = var[m.group(2)]
    for m in re.finditer(r"\b(\w+)\s*=\s*&?\s*(__in\w+)\s*;", E):
        var[m.group(1)] = var[m.group(2)]
    for m in re.finditer(r'\b\w+\s*(?:->|\.)\s*input\(\s*"(\w+)"\s*,\s*&\s*(\w+)\s*\)', E):
        if m.group(1) in inputs:
            var[m.group(2)] = m.group(1)
    var = {v: n for v, n in var.items() if n}
    for _ in range(3):  # chains: s = x.shape(); n = s.dims();
        E = derive_locals(E, list(var))
    return E, var


def derive_locals(E, vars_):
    """Substitute locals defined from an input's shape (n = x.dims(); s = x.shape(); d = x.dim_size(3)) by their
    definition, so later checks on n / s count as checks on x."""
    alt = "|".join(re.escape(v) for v in sorted(vars_, key=len, reverse=True))
    if not alt:
        return E
    pat = re.compile(r"(?:const\s+)?(?:TensorShape|auto|int|int32|int64|int64_t|int32_t|size_t|Eigen::Index)\s*&?\s*"
                     r"(\w+)\s*=\s*((?:" + alt + r")\s*(?:\.|->)\s*(?:shape\(\)|dims\(\)|NumElements\(\)|"
                     r"shape\(\)\s*\.\s*dims\(\)|dim_size\((?:[^()]|\([^()]*\))*\)))\s*;")
    for m in list(pat.finditer(E))[:40]:
        local, expr = m.group(1), m.group(2)
        if local in vars_:
            continue
        head, tail = E[:m.end()], E[m.end():]
        E = head + re.sub(rf"(?<![\w.>]){re.escape(local)}\b(?!\s*=[^=])", lambda _: expr, tail)
    return E


VALIDATING_CALL = re.compile(r"\b\w*(?:Valid|Check|Verify|Ensure|Require|SameShape|Compatible|MakeShape|BCast|"
                             r"IsSameSize|Matches)\w*\s*(?:<[^<>;(){}]*>)?\s*\(")


def tf_guards(E):
    """[(start, end, cond, msg)] for OP_REQUIRES*, validating OP_REQUIRES_OK/TF_RETURN_IF_ERROR, if(...) error returns."""
    g = []
    for start, nm, args, end in calls(E, r"TF_REQUIRES"):
        a = split_top(args)
        g.append((start, end, a[0], ",".join(a[1:])[:300]))
    for start, nm, args, end in calls(E, r"OP_REQUIRES(?:_ASYNC)?"):
        a = split_top(args)
        if len(a) >= 2:
            g.append((start, end, a[1], ",".join(a[2:])[:300]))
    for start, nm, args, end in calls(E, r"OP_REQUIRES_OK(?:_ASYNC)?|TF_RETURN_IF_ERROR"):
        a = split_top(args)
        expr = a[1] if nm.startswith("OP_") and len(a) >= 2 else a[0]
        if VALIDATING_CALL.search(expr):
            g.append((start, end, expr, ""))
    for start, nm, args, end in calls(E, r"\w*(?:Valid|Check|Verify)\w*"):
        if re.match(r"\s*(?:ctx|context|c|op_ctx|context_)\s*(?:,|$)", args) or re.search(r"\b(?:ctx|context)\b", args):
            g.append((start, end, "__ALL__", nm))
    for m in re.finditer(r"\b[A-Z]\w*(?:<[^<>;]*>)?\s+\w+\s*([({])\s*(?:context|ctx|c|op_ctx)\s*[,)}]", E):
        o = m.start(1)
        e = match_close(E, o)
        if re.search(r"status\(\)\s*\.\s*ok\(\)|IsValid\(\)", E[e:e + 400]):
            g.append((m.start(), e, E[o + 1:e - 1], "constructor validation"))
    built = {}
    for m in re.finditer(r"\b[A-Z][\w:]*(?:<[^<>;]*>)?\s+(\w+)\s*([({])", E):
        o = m.start(2)
        built[m.group(1)] = E[o + 1:match_close(E, o) - 1]
    g = [(gs, ge, cond + "".join(f" /*built from*/ {built[n]}" for n in re.findall(r"\b(\w+)\s*\.\s*(?:IsValid|ok)\(\)", cond)
                                 if n in built), msg) for gs, ge, cond, msg in g]
    for m in re.finditer(r"\bif\s*\(", E):
        o = m.end() - 1
        e = match_close(E, o)
        if re.match(r"\s*\{?\s*(?:[^;{}]*;\s*){0,2}?[^;{}]*(?:SetStatus|CtxFailure|return\s+errors::|return\s+absl::|"
                    r"errors::InvalidArgument|return\s+(?:tsl::)?errors|OP_REQUIRES)", E[e:e + 400]):
            g.append((m.start(), e, E[o + 1:e - 1], E[e:e + 160]))
    return sorted(g)


def tf_reads(E, v):
    """[(pos, need, text)] precondition reads of v. need: ('rank_ge', m) | ('rank_eq', n) | ('numel_eq', 1)."""
    out = []
    for m in re.finditer(acc(v) + r"(?:shape\(\)\s*\.\s*)?dim_size\(\s*((?:[^()]|\([^()]*\))*)\)", E):
        k = m.group(1).strip()
        out.append((m.start(), ("rank_ge", int(k) + 1 if k.isdigit() else 1), m.group(0)))
    for m in re.finditer(acc(v) + r"(matrix|vec|tensor)\s*<([^>]*)>", E):
        kind, targs = m.group(1), m.group(2)
        n = 2 if kind == "matrix" else 1 if kind == "vec" else (int(targs.split(",")[-1]) if targs.split(",")[-1].strip().isdigit() else None)
        if n is not None:
            out.append((m.start(), ("rank_eq", n), m.group(0)))
    for m in re.finditer(acc(v) + r"scalar\s*<", E):
        out.append((m.start(), ("numel_eq", 1), m.group(0)))
    return sorted(out)


def block_ends(E):
    """For every '{' at i: matching close. Used to scope guards: a guard inside a block that closes before a read
    (other if/else branch, loop body, lambda) does not protect that read."""
    ends, stack, i, n = {}, [], 0, len(E)
    while i < n:
        c = E[i]
        if c in "\"'":
            j = i + 1
            while j < n and E[j] != c:
                j += 2 if E[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            stack.append(i)
        elif c == "}" and stack:
            ends[stack.pop()] = i
        i += 1
    return ends


def scope_end(blocks, pos, E=None):
    """End of the innermost block containing pos; a for-loop body is transparent (a check run for every element,
    e.g. over all inputs, still guards what follows the loop)."""
    inner = sorted(((s, e) for s, e in blocks.items() if s < pos < e), reverse=True)
    for s, e in inner:
        head = E[max(0, s - 300):s].rstrip() if E else ""
        if head.endswith(")") and re.search(r"\bfor\s*\([^{};]*;[^{}]*\)$", head):
            continue
        return e
    return 10 ** 9


def protected(E, guards, vars_, pos, need_cat, blocks):
    """Is a read at pos protected by an earlier, in-scope check on any alias of the input?"""
    for gs, ge, cond, _ in guards:
        if gs >= pos:
            break
        if scope_end(blocks, gs, E) < pos:
            continue
        cats = set().union(*(guard_cats(v, cond) for v in vars_))
        if not cats & PROTECTS[need_cat]:
            continue
        if ge <= pos:
            return True
        # read inside this guard's own condition: protected only by a check textually before it (short-circuit)
        if set().union(*(guard_cats(v, E[gs:pos]) for v in vars_)) & PROTECTS[need_cat]:
            return True
    for m in re.finditer(r"\b(?:if|while|for)\s*\(", E[:pos]):  # read inside a branch/loop whose header checks it
        o = m.end() - 1
        e = match_close(E, o)
        if e <= pos:
            k = e + len(E[e:]) - len(E[e:].lstrip())
            body_end = blocks.get(k, k) if E[k:k + 1] == "{" else E.find(";", k)
            if pos > body_end:
                continue
        cond = E[o + 1:min(e - 1, pos)]
        if set().union(*(guard_cats(v, cond) for v in vars_)) & PROTECTS[need_cat]:
            return True
    return False


def tf_analyse(ix):
    """-> {op: {"status": .., "gaps": [..], "guards": {input: cats}}}"""
    res = {}
    for opname, op in ix.ops.items():
        k = ix.kernel(opname)
        if isinstance(k, str):
            res[opname] = {"status": k, "gaps": [], "guard_cats": {}}
            continue
        E, file, cname = k
        E, var = bind_inputs(E, op, ix.consts.get(file, {}))
        guards = tf_guards(E)
        blocks = block_ends(E)
        by_input = defaultdict(set)
        for v, n in var.items():
            by_input[n].add(v)
        gcats = {n: sorted(set().union(*(guard_cats(v, g[2]) for v in vs for g in guards))) for n, vs in by_input.items()}
        gaps = []
        # kind 3: read before guard
        for n, vs in by_input.items():
            reads = sorted(r for v in vs for r in tf_reads(E, v))
            for pos, need, text in reads:
                cat = "numel" if need[0] == "numel_eq" else "rank"
                if not protected(E, guards, vs, pos, cat, blocks):
                    later = [g for g in guards if g[0] > pos and set().union(*(guard_cats(v, g[2]) for v in vs)) & PROTECTS[cat]]
                    gaps.append({"kind": 3, "param": n, "cat": cat, "need": list(need), "read": text.strip(),
                                 "read_at": line_of(file, text.strip(), ix.related_files(file)),
                                 "later_guard": later[0][2].strip()[:160] if later else None,
                                 "guard_msg": later[0][3].strip()[:200] if later else None})
                    break
        # kind 1: shape-function-only
        for c in shape_constraints(op["shape"]):
            i = c["input"]
            if i >= len(op["inputs"]) or any(op["islist"][:i + 1]):
                continue
            n = op["inputs"][i]
            vs = by_input.get(n)
            if not vs:
                continue  # input never read in the kernel code we can see: unknown, no gap
            if any(VALIDATING_CALL.search(g[2]) and re.search(rf"\b{re.escape(v)}\b", g[2]) for v in vs for g in guards):
                continue
            if set(gcats.get(n, [])) & PROTECTS[c["cat"]]:
                continue
            need = (["rank_eq", c["r"]] if c["cat"] == "rank" and c.get("op") == "eq" else
                    ["rank_ge", c["r"]] if c["cat"] == "rank" and c.get("op") == "ge" else
                    ["rank_le", c["r"]] if c["cat"] == "rank" else
                    ["merge", op["inputs"][c["with"]] if c["with"] < len(op["inputs"]) else None] if c["cat"] == "merge"
                    else ["dim", c.get("dim"), c.get("v")])
            g = {"kind": 1, "param": n, "cat": c["cat"], "need": need, "shape_fn": c["text"],
                 "shape_fn_file": rel(op["file"])}
            if not any(x["kind"] == 1 and x["param"] == n and x["cat"] == c["cat"] for x in gaps):
                gaps.append(g)
        for g in gaps:
            g.update(kernel_file=rel(file), kernel_class=cname)
        res[opname] = {"status": "ok", "gaps": gaps, "guard_cats": gcats, "kernel_file": rel(file),
                       "kernel_class": cname, "bound_inputs": sorted(by_input)}
    # kind 2: siblings
    norm = lambda s: re.sub(r"V\d+$", "", re.sub(r"^(?:Resource|Experimental)", "", s))
    fam = defaultdict(list)
    for opname in res:
        fam[norm(opname)].append(opname)
    for opname, r in res.items():
        if r["status"] != "ok":
            continue
        mine = set(ix.ops[opname]["inputs"])
        for sib in fam[norm(opname)]:
            s = res.get(sib)
            if sib == opname or not s or s["status"] != "ok" or s.get("kernel_class") == r["kernel_class"]:
                continue
            theirs = set(ix.ops[sib]["inputs"])
            jac = len(mine & theirs) / max(1, len(mine | theirs))
            if jac < 0.6:
                continue
            for n in sorted(mine & theirs):
                if n not in r["guard_cats"] or "any" in r["guard_cats"][n]:
                    continue
                for cat in sorted(set(s["guard_cats"].get(n, [])) - set(r["guard_cats"][n]) - {"any"}):
                    if cat in ("value",):
                        continue
                    if any(x["kind"] == 2 and x["param"] == n and x["cat"] == cat for x in r["gaps"]):
                        continue
                    r["gaps"].append({"kind": 2, "param": n, "cat": cat, "need": [cat], "sibling": sib,
                                      "jaccard": round(jac, 2), "sibling_kernel": s["kernel_file"],
                                      "kernel_file": r["kernel_file"], "kernel_class": r["kernel_class"]})
    return res


def tfsa_ops(known_ops):
    out = defaultdict(list)
    for f in sorted(glob.glob(f"{HERE}/cache/tf/tensorflow/security/advisory/tfsa-*.md")):
        t = open(f, errors="replace").read()
        title = t.splitlines()[0] if t else ""
        names = set(re.findall(r"tf\.raw_ops\.(\w+)", t)) | {w for w in re.findall(r"\b([A-Z][A-Za-z0-9]+)\b", title)
                                                           if w in known_ops}
        for n in names:
            out[n].append(os.path.basename(f)[:-3])
    return out


# ===================================================================================================== torch
TORCH_GUARD = r"TORCH_CHECK(?:_VALUE|_INDEX|_TYPE|_LINALG|_NOT_IMPLEMENTED)?"
TORCH_VALIDATOR = re.compile(r"\b(?:check\w*|_check\w*|\w+_check\w*|squareCheckInputs|linearSolveCheckInputs|checkIsMatrix|"
                             r"checkFloatingOrComplex|checkInputsSolver|checkSameDevice|checkAllSameDim|"
                             r"check_dim_size|checkDim|checkSize)\s*\(")
TORCH_STOP = {"dim", "size", "sizes", "strides", "stride", "numel", "scalar_type", "dtype", "options", "device", "data_ptr",
              "const_data_ptr", "mutable_data_ptr", "item", "defined", "is_contiguous", "contiguous", "empty", "zeros",
              "empty_like", "zeros_like", "resize_", "copy_", "to", "view", "reshape", "expand", "squeeze", "unsqueeze",
              "select", "narrow", "slice", "clone", "fill_", "zero_", "set_", "as_strided", "TensorIterator",
              "TensorIteratorConfig", "build", "add_output", "add_input", "add_const_input"}


class TorchIndex:
    def __init__(self):
        import yaml
        self.entries = yaml.safe_load(open(f"{ATEN}/native_functions.yaml"))
        self.funcs, self.meta, self.impl = defaultdict(list), defaultdict(list), defaultdict(list)
        files = sorted(glob.glob(f"{ATEN}/**/*.cpp", recursive=True) + glob.glob(f"{ATEN}/**/*.h", recursive=True))
        files = [f for f in files if not re.search(r"/(cuda|mps|vulkan|metal|miopen|cudnn|nested|mkldnn|xnnpack|"
                                                   r"quantized/cuda|hip|sparse/cuda|transformers/cuda)/", f)]
        self.macros = {}
        for f in files:
            raw = open(f, errors="replace").read()
            for m in re.finditer(r"#define\s+(\w+)\(\)\s*\\\n((?:.*\\\n)*.*)", raw):
                self.macros[m.group(1)] = m.group(2).replace("\\\n", "\n")
            src, fs, cls = index_file(f)
            for fn in fs:
                fn["file"] = f
                self.funcs[fn["name"].split("::")[-1]].append(fn)
            for m in re.finditer(r"TORCH_(META|IMPL|PRECOMPUTE_META)_FUNC2?\s*\(\s*(\w+)(?:\s*,\s*(\w+))?\s*\)\s*\(", src):
                o = m.end() - 1
                e = match_close(src, o)
                b = src.find("{", e)
                if b < 0 or src[e:b].strip() not in ("", "const"):
                    continue
                d = {"params": src[o:e], "body": src[b:match_close(src, b)], "file": f}
                key = m.group(2) + ("." + m.group(3) if m.group(3) else "")
                (self.impl if m.group(1) == "IMPL" else self.meta)[key].append(d)
        self.by_base = defaultdict(list)
        for e in self.entries:
            if "func" not in e:
                continue
            sig = e["func"]
            name = sig.split("(")[0]
            base, _, overload = name.partition(".")
            args = [a.strip() for a in split_top(sig[sig.index("(") + 1:sig.rindex(") ->")]) if a.strip() not in ("", "*")]
            pnames = [re.split(r"\s+", a.split("=")[0].strip())[-1] for a in args]
            ptypes = {re.split(r"\s+", a.split("=")[0].strip())[-1]: a.split("=")[0].strip().rsplit(" ", 1)[0] for a in args}
            self.by_base[base].append({"name": name, "base": base, "overload": overload, "params": pnames,
                                       "ptypes": ptypes, "entry": e})

    def ops_for(self, api):
        """DFUZZ API name -> overloads of the base name, plus its inplace twin (foo_)."""
        ovs = self._ops_for(api)
        if ovs and not ovs[0]["base"].endswith("_"):
            ovs = ovs + self.by_base.get(ovs[0]["base"] + "_", [])
        return ovs

    def _ops_for(self, api):
        """DFUZZ API name -> native_functions overloads (all overloads of the base name)."""
        p = api.split(".")
        if api.startswith("torch.Tensor."):
            base = p[2]
        elif api.startswith("torch.nn.functional."):
            base = p[3]
        elif len(p) == 3 and p[1] in ("fft", "linalg", "special"):
            base = f"{p[1]}_{p[2]}"
        elif len(p) == 2:
            base = p[1]
        else:
            return []
        return self.by_base.get(base, [])

    def bodies(self, ov):
        """[(kind, body)] meta first, then impls, for CPU / composite dispatch of one overload."""
        e = ov["entry"]
        out = []
        tgt = ov
        if e.get("structured_delegate"):
            dn = e["structured_delegate"]
            tgt = next((o for o in self.by_base.get(dn.split(".")[0], []) if o["name"] == dn), None)
            if tgt is None:
                return out
            for key in (ov["base"] + ("." + ov["overload"] if ov["overload"] and ov["overload"] != "out" else ""), ov["base"],
                        ov["base"].rstrip("_")):
                if self.meta.get(key):
                    out.append(("meta", self.meta[key][0]))
                    break
        disp = tgt["entry"].get("dispatch") or {}
        names = []
        for k, v in disp.items():
            keys = {x.strip() for x in str(k).split(",")}
            if keys & {"CPU", "CompositeExplicitAutograd", "CompositeImplicitAutograd", "CompositeExplicitAutogradNonFunctional",
                       "Math", "DefaultBackend"}:
                names.append(v)
        if not names:  # quantized-only ops: QuantizedCPU is still a CPU kernel
            names += [v for k, v in disp.items() if "QuantizedCPU" in {x.strip() for x in str(k).split(",")}]
        if not disp:
            names.append(tgt["base"])
        if tgt["entry"].get("structured"):
            for key in (tgt["base"] + ("." + tgt["overload"] if tgt["overload"] and tgt["overload"] != "out" else ""),
                        tgt["base"], tgt["base"].rstrip("_")):
                if self.meta.get(key) and not any(k == "meta" for k, _ in out):
                    out.append(("meta", self.meta[key][0]))
                    break
        for n in names:
            d = (self.impl.get(n) or [None])[0] or self.pick(n, len(tgt["params"]))
            if d:
                out.append(("impl", d))
        return out

    def pick(self, name, nparams):
        defs = self.funcs.get(name, [])
        if not defs:
            return None
        return sorted(defs, key=lambda d: abs(len(param_names(d["params"])) - nparams))[0]

    def expand(self, body, depth, stack):
        if depth >= 2:
            return body
        out, last = [], 0
        for start, name, args, end in calls(body, r"[A-Za-z_]\w*"):
            if start < last or name in stack or name in TORCH_STOP or re.match(r"[.>]", body[max(0, start - 1):start]):
                continue
            defs = self.funcs.get(name)
            nargs = len(split_top(args)) if args.strip() else 0
            name = re.sub(r"_symint$", "", name)
            base_name, outv = re.sub(r"_outf?$", "", name), re.search(r"_(outf?)$", name)
            if (not defs or body[max(0, start - 4):start] == "at::") and (self.by_base.get(name) or
                                                                         (outv and self.by_base.get(base_name))):
                # at::foo(...) dispatches to the native function foo (at::foo_out/_outf to its out= overload):
                # inline its CPU/composite code, schema parameter names mapped to the call's arguments
                cands = self.by_base.get(name) or [o for o in self.by_base[base_name]
                                                   if any("!" in t for t in o["ptypes"].values())]
                if not cands:
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
            if len(fn["body"]) > 20000:
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

    def code(self, ov, depth=0, stack=frozenset()):
        parts = []
        for kind, d in self.bodies(ov):
            sub = d["body"]
            # rename the implementation's own parameter names to the schema's (positional)
            for p, a in zip(param_names(d["params"]), [x for x in ov["params"] if x != "out"] + ["out"]):
                if p != a:
                    sub = re.sub(rf"(?<![\w.>]){re.escape(p)}\b", a, sub)
            sub = re.sub(r"\b(\w+)\(\)\s*;", lambda m: self.macros.get(m.group(1), m.group(0)), sub)
            parts.append(self.expand(sub.strip()[1:-1], depth, set(stack)))
        return "\n;\n".join(parts), [d["file"] for _, d in self.bodies(ov)]


def torch_guards(E):
    g = []
    for start, nm, args, end in calls(E, TORCH_GUARD):
        a = split_top(args)
        g.append((start, end, a[0] if a else "", ",".join(a[1:])[:300]))
    for m in TORCH_VALIDATOR.finditer(E):
        o = m.end() - 1
        e = match_close(E, o)
        g.append((m.start(), e, E[o + 1:e - 1] + " /*validator*/", m.group(0)))
    return sorted(g)


def torch_reads(E, v):
    out = []
    for m in re.finditer(acc(v) + r"(?:sizes|strides)\(\)\s*\[\s*([^\]]*)\]", E):
        k = m.group(1).strip()
        out.append((m.start(), ("rank_ge", int(k) + 1 if k.isdigit() else 1), m.group(0)))
    return out


def torch_analyse(tx, apis):
    res = {}
    cache = {}
    for api in apis:
        ovs = tx.ops_for(api)
        if not ovs:
            res[api] = {"status": "no_native_function", "gaps": []}
            continue
        info = []
        ovs = [o for o in ovs if not any("Dimname" in t for t in o["ptypes"].values())]  # named-tensor NYI paths
        for ov in ovs:
            if ov["name"] not in cache:
                E, files = tx.code(ov)
                tparams = [p for p, t in ov["ptypes"].items() if "Tensor" in t]
                guards = torch_guards(E) if E else []
                blocks = block_ends(E) if E else {}
                gcats = {p: sorted(set().union(*(guard_cats(p, g[2]) for g in guards))) for p in ov["params"]}
                gaps = []
                for p in tparams:
                    for pos, need, text in sorted(torch_reads(E, p)):
                        if not protected(E, guards, [p], pos, "rank", blocks):
                            gaps.append({"kind": 3, "param": p, "cat": "rank", "need": list(need), "read": text.strip(),
                                         "read_at": line_of(files[-1], text.strip(), files[:-1]) if files else None})
                            break
                cache[ov["name"]] = {"name": ov["name"], "resolved": bool(E.strip()), "gcats": gcats, "gaps": gaps,
                                     "outs": [x for x, t in ov["ptypes"].items() if "!" in t and x != "self"],
                                     "params": ov["params"], "tensor_params": tparams,
                                     "files": sorted({rel(f) for f in files})}
            info.append(cache[ov["name"]])
        resolved = [i for i in info if i["resolved"]]
        if not resolved:
            res[api] = {"status": "no_cpu_impl_found", "gaps": [], "overloads": [i["name"] for i in info]}
            continue
        gaps = []
        # functional overloads of the API are the targets; out=/inplace overloads are siblings
        inplace_api = api.split(".")[-1].endswith("_")
        targets = [i for i in resolved if not i["outs"] and "out" not in i["params"]
                   and i["name"].split(".")[0].endswith("_") == inplace_api] or resolved
        for t in targets:
            gaps += [{**g, "overload": t["name"]} for g in t["gaps"]]
            for s in resolved:
                if s is t:
                    continue
                # siblings = the out= / inplace variants of the same overload (same inputs, plus mutable outputs);
                # other overloads (max vs max.dim) are different operations
                mine, theirs = set(t["params"]) - {"out"}, set(s["params"]) - set(s.get("outs", [])) - {"out"}
                jac = len(mine & theirs) / max(1, len(mine | theirs))
                if jac < 0.6 or not (s.get("outs") or s["name"].split(".")[0].endswith("_")) or \
                        mine - {"self"} != theirs - {"self"}:
                    continue
                for p in sorted(mine & theirs):
                    if p not in t["tensor_params"] or "any" in t["gcats"].get(p, []):
                        continue
                    for cat in sorted(set(s["gcats"].get(p, [])) - set(t["gcats"].get(p, [])) - {"any", "value"}):
                        if not any(x["kind"] == 2 and x["param"] == p and x["cat"] == cat for x in gaps):
                            gaps.append({"kind": 2, "param": p, "cat": cat, "need": [cat], "overload": t["name"],
                                         "sibling": s["name"], "jaccard": round(jac, 2), "files": t["files"],
                                         "sibling_files": s["files"]})
        res[api] = {"status": "ok", "gaps": gaps, "overloads": [i["name"] for i in resolved],
                    "guard_cats": {i["name"]: i["gcats"] for i in resolved}}
    return res


KNOWN_BUG_APIS = [l.split("\t")[2] for l in open(f"{HERE}/expected.tsv").read().splitlines()[1:]]
KNOWN_BUG_ALIASES = {  # public API -> raw op(s) / torch method twins; their families are dropped in sensitivity analyses
    "tf.audio.decode_wav": ["DecodeWav"], "tf.experimental.numpy.cos": ["Cos"],
    "tf.image.draw_bounding_boxes": ["DrawBoundingBoxes", "DrawBoundingBoxesV2"], "tf.linalg.solve": ["MatrixSolve"],
    "tf.quantization.fake_quant_with_min_max_vars_per_channel": ["FakeQuantWithMinMaxVarsPerChannel"],
    "tf.tensor_scatter_nd_add": ["TensorScatterAdd"], "tf.tensor_scatter_nd_update": ["TensorScatterUpdate"],
    "tf.io.TFRecordOptions": [],
}


def excluded_apis():
    ex = set(KNOWN_BUG_APIS)
    for api in KNOWN_BUG_APIS:
        if api.startswith("tf.raw_ops."):
            continue
        if api.startswith("tf."):
            ex |= {f"tf.raw_ops.{o}" for o in KNOWN_BUG_ALIASES.get(api, [])}
        elif api.startswith("torch.Tensor."):
            ex.add("torch." + api.split(".")[-1])
        elif api.startswith("torch.") and api.count(".") == 1:
            ex.add("torch.Tensor." + api.split(".")[-1])
    return ex


def tf_family(op):
    return re.sub(r"V\d+$", "", re.sub(r"^(?:Resource|Experimental)", "", op))


def assemble():
    """gaps.jsonl (one gap per line, mapped to DFUZZ's parameter role + a released edge case) and gap_index.json."""
    from edgecases import best_released
    raw_tf = json.load(open(f"{OUT}/gap_raw_tf.json"))
    tres, tfsa = raw_tf["tf"], raw_tf["tfsa"]
    pres = json.load(open(f"{OUT}/gap_raw_torch.json"))["torch"]
    ex = excluded_apis()
    bug_fams = {tf_family(a.split(".")[-1]) for a in ex if a.startswith("tf.raw_ops.")}
    index, lines = {}, []
    for lib, short, res in (("tensorflow", "tf", None), ("torch", "torch", pres)):
        info = json.load(open(f"{ROOT}/get_api_reference/results/{lib}/apis_info.json"))
        progs = json.load(open(f"{ROOT}/gen_program/results/{short}/api_programs.json"))
        for api in sorted(progs):
            if short == "tf":
                if not api.startswith("tf.raw_ops."):
                    continue
                op = api.split(".")[-1]
                r = tres.get(op, {"status": "no_REGISTER_OP", "gaps": []})
            else:
                r = pres.get(api, {"status": "no_native_function", "gaps": []})
            params = info.get(api) or {}
            gl = []
            renames = json.load(open(f"{OUT}/tf_arg_renames.json")) if short == "tf" else {}
            for g in r["gaps"]:
                role = renames.get(api.split(".")[-1], {}).get(g["param"], g["param"])  # api_def renames (axis)
                if role not in params and role == "self" and "input" in params:
                    role = "input"
                ptype = params.get(role)
                ec = best_released(ptype or "Tensor", g.get("need"), g["cat"])
                rec = {"api": api, "lib": short, **g, "role": role, "dfuzz_type": ptype, "role_in_dfuzz": role in params,
                       "edge_case": ec}
                gl.append(rec)
                lines.append(rec)
            index[api] = {"lib": short, "status": r["status"], "seeded": progs[api] != "none",
                          "n_gaps": len(gl), "n_gaps_mapped": sum(1 for g in gl if g["role_in_dfuzz"] and g["edge_case"]),
                          "kinds": sorted({g["kind"] for g in gl}), "known_bug_or_alias": api in ex,
                          "tfsa": tfsa.get(api.split(".")[-1], []) if short == "tf" else [],
                          "bug_family": short == "tf" and tf_family(api.split(".")[-1]) in bug_fams}
    with open(f"{OUT}/gaps.jsonl", "w") as f:
        for rec in lines:
            f.write(json.dumps(rec) + "\n")
    json.dump(index, open(f"{OUT}/gap_index.json", "w"), indent=0)
    for lib in ("tf", "torch"):
        seeded = [a for a, v in index.items() if v["lib"] == lib and v["seeded"]]
        st = defaultdict(int)
        for a in seeded:
            st[index[a]["status"]] += 1
        g = [a for a in seeded if index[a]["n_gaps"]]
        gm = [a for a in seeded if index[a]["n_gaps_mapped"]]
        print(f"{lib}: seeded={len(seeded)} status={dict(st)} with_gap={len(g)} ({len(g) / len(seeded):.1%}) "
              f"with_mapped_gap={len(gm)}; upper bound if every unresolved API had a gap: "
              f"{(len(g) + sum(v for k, v in st.items() if k != 'ok')) / len(seeded):.1%}")
    seeded = [a for a, v in index.items() if v["seeded"]]
    g = [a for a in seeded if index[a]["n_gaps"]]
    print(f"pooled: {len(g)}/{len(seeded)} = {len(g) / len(seeded):.1%} seeded APIs have >=1 gap "
          f"(stop rule: < 50% -> stop); gaps total {len(lines)}")


if __name__ == "__main__":
    import time
    t = time.time()
    which = sys.argv[1:] or ["tf", "torch"]
    if "tf" in which:
        tf = TFIndex()
        print(f"TF: {len(tf.ops)} ops, {len(tf.reg)} ops with CPU kernels ({time.time() - t:.0f}s)", flush=True)
        tres = tf_analyse(tf)
        tfsa = tfsa_ops(set(tf.ops))
        json.dump({"tf": tres, "tfsa": tfsa}, open(f"{OUT}/gap_raw_tf.json", "w"))
        st = defaultdict(int)
        for r in tres.values():
            st[r["status"]] += 1
        print(dict(st), "ops with gaps:", sum(bool(r["gaps"]) for r in tres.values()),
              "by kind:", {k: sum(g["kind"] == k for r in tres.values() for g in r["gaps"]) for k in (1, 2, 3)},
              f"TFSA ops: {len(tfsa)} ({time.time() - t:.0f}s)", flush=True)
    if "torch" in which:
        tx = TorchIndex()
        apis = sorted(json.load(open(f"{ROOT}/gen_program/results/torch/api_programs.json")))
        print(f"torch: {len(tx.entries)} native functions, {sum(map(len, tx.funcs.values()))} C++ defs "
              f"({time.time() - t:.0f}s)", flush=True)
        pres = torch_analyse(tx, apis)
        json.dump({"torch": pres}, open(f"{OUT}/gap_raw_torch.json", "w"))
        st = defaultdict(int)
        for r in pres.values():
            st[r["status"]] += 1
        print(dict(st), "APIs with gaps:", sum(bool(r["gaps"]) for r in pres.values()),
              "by kind:", {k: sum(g["kind"] == k for r in pres.values() for g in r["gaps"]) for k in (2, 3)},
              f"({time.time() - t:.0f}s)")
    assemble()
