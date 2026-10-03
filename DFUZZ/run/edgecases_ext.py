"""Phase 0b edge-case vocabulary V0b (PILOT_PLAN.md 'Phase 0b amendment'). Tool-derived from one gap record, no LLM.
Texts follow DFUZZ's individual-mutator style and go unchanged into Fig. 7's requirement slot. DFUZZ data files are
never edited. `candidates(gap, ptype, other_role)` -> ordered list of {id, src, text, var, tier}; tier 0 = primary
violation, 1 = secondary probe. Released best (Phase 0 mapping, `edgecases.best_released`) comes first when present.
Self-check: python run/edgecases_ext.py"""
import re

FLOAT_T = re.compile(r"float|double|half|bfloat16|Eigen::half")


def R(k):
    return ("A tensor with 0 dimensions (a scalar)" if k == 0 else "A 1-dimensional tensor (vector)" if k == 1
            else f"A tensor with {k} dimensions")


def placeholder(ptype):
    t = (ptype or "").lower()
    return next((x for x in ("int", "scalar", "float", "bool", "list") if x in t), "scalar")


def _merge_dims(shape_fn):
    """'Merge(c->Dim(input, 0), c->Dim(offsets, 0), &d)' -> ('0', '0'); non-literal dims -> None."""
    m = re.findall(r"c->Dim\(\s*\w+\s*,\s*(-?\d+)\s*\)", shape_fn or "")
    return (m[0], m[1]) if len(m) >= 2 else (None, None)


def candidates(g, ptype, other_role=None, released=None):
    """g: gap record (gaps_0b.jsonl, before mapping). ptype: DFUZZ type of g's role. other_role: DFUZZ name of the
    merge partner (kind-1 merge), None if it is not a DFUZZ parameter. released: Phase 0 best_released() or None."""
    need, kind, role = g.get("need") or [g["cat"]], g["kind"], g["role"]
    op, n = need[0], (need[1] if len(need) > 1 else None)
    tensor = "tensor" in (ptype or "Tensor").lower()
    out = []
    add = lambda cid, text, tier=0, var=None: out.append({"id": cid, "src": "v0b", "text": text, "tier": tier,
                                                          "var": var or role})
    if released:
        out.append({"id": f"rel:{released['pattern']}#{released['idx']}", "src": "released", "text": released["text"],
                    "tier": 0, "var": role})
    if tensor:
        if op == "rank_ge" and isinstance(n, int) and n >= 1:
            add("T-rm", R(n - 1))
            if n >= 2:
                add("T-r0", R(0), 1)
        elif op == "rank_eq" and isinstance(n, int):
            add("T-req", R(n + 1))
            if n >= 1:
                add("T-req", R(n - 1))
        elif op == "rank_le" and isinstance(n, int):
            add("T-rle", R(n + 1))
        elif op == "numel_eq":
            add("T-n1", "A 1-dimensional tensor with 2 elements")
        elif op == "dim" and len(need) >= 3 and str(need[1]).lstrip("-").isdigit() and str(need[2]).isdigit():
            add("T-dv", f"A tensor where dimension {need[1]} has size {int(need[2]) + 1}")
        elif op == "merge" and other_role:
            dx, dy = _merge_dims(g.get("shape_fn"))
            if dx is not None:
                txt = (f"tensor_1 and tensor_2 have the same number of dimensions, but dimension {dx} of tensor_1 has "
                       f"size 3 while dimension {dy} of tensor_2 has size 4")
            else:
                txt = ("tensor_1 and tensor_2 have the same number of dimensions, but the dimension that must match has "
                       "size 3 in tensor_1 and size 4 in tensor_2")
            add("T-mm", txt.replace("tensor_1", role).replace("tensor_2", other_role), var=[role, other_role])
        k = g.get("read_index")
        if kind == 3 and isinstance(k, int):
            add("T-e0", f"A tensor with {k + 1} dimensions where dimension {k} has size 0", 1)
        cast = g.get("reinterpret")
        if kind == 3 and cast:
            add("T-dx", "A tensor containing the largest value its dtype can represent (e.g. 2147483647 for int32)", 1)
            if FLOAT_T.search(cast.get("from_T", "")):
                add("T-dx", "A tensor containing NaN and infinity values", 1)
    else:
        ph = placeholder(ptype)
        if op in ("numel_eq",) or (op == "rank_eq" and n == 0):
            add("S-t1", f"{ph}_1 is a 1-dimensional tensor with 2 elements instead of a single value")
        elif op == "rank_le" and isinstance(n, int):
            add("S-tn", f"{ph}_1 is a {n + 1}-dimensional tensor of integers, such as [[0]], instead of a single value")
        elif op in ("rank_ge", "rank_eq") and isinstance(n, int) and n >= 1:
            add("S-s0", f"{ph}_1 is a single number (a 0-dimensional tensor) instead of a list")
            if op == "rank_eq":
                add("S-sn", f"{ph}_1 is a nested list with {n + 1} levels, such as [[1, 2]], instead of a "
                            f"{n}-dimensional list")
    return out


def axis_candidate(g, index_role, index_type):
    """S-ax: a kind-3 read x.dim_size(i) / x.sizes()[i] whose index is the Int role index_role."""
    if g["kind"] != 3 or "int" not in (index_type or "").lower():
        return None
    return {"id": "S-ax", "src": "v0b", "tier": 0, "var": index_role,
            "text": f"int_1 is equal to the number of dimensions of `{g['role']}` (an axis that does not exist)"}


if __name__ == "__main__":
    g = {"kind": 3, "need": ["rank_ge", 4], "cat": "rank", "role": "images", "read_index": 3}
    ids = [c["id"] for c in candidates(g, "Tensor")]
    assert ids == ["T-rm", "T-r0", "T-e0"], ids
    assert candidates(g, "Tensor")[0]["text"] == "A tensor with 3 dimensions"
    a = candidates({"kind": 1, "need": ["rank_le", 1], "cat": "rank", "role": "axis"}, "Int")
    assert a[0]["id"] == "S-tn" and a[0]["text"].startswith("int_1 is a 2-dimensional tensor"), a
    m = candidates({"kind": 1, "need": ["merge", "offsets"], "cat": "merge", "role": "input",
                    "shape_fn": "Merge(c->Dim(input, 0), c->Dim(offsets, 0), &b)"}, "Tensor", "offsets")
    assert m[0]["var"] == ["input", "offsets"] and "dimension 0 of input has size 3" in m[0]["text"], m
    s = candidates({"kind": 3, "need": ["numel_eq", 1], "cat": "numel", "role": "x",
                    "reinterpret": {"to": "int", "from_T": "float"}}, "Tensor")
    assert [c["id"] for c in s] == ["T-n1", "T-dx", "T-dx"], s
    assert candidates({"kind": 1, "need": ["rank_eq", 0], "cat": "rank", "role": "p"}, "Scalar")[0]["id"] == "S-t1"
    print("ok")
