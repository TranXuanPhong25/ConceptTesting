"""Hand annotation of DFUZZ's released edge cases (edge_case_extraction/results/unique_mutators.json, 146 / 21 type
patterns) with the property each states about each placeholder, so a gap's need (e.g. rank >= 4) can be matched to
edge cases that violate it. Only properties a gap can use are annotated: rank, empty, dtype, neg, mismatch (shape
differs from the other placeholder). Unannotated = says nothing usable (device, layout, sparse, quantized, ...)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = json.load(open(os.path.join(ROOT, "edge_case_extraction/results/unique_mutators.json")))

T1 = "['tensor_1']"
PAIR = "['tensor_1', 'tensor_2']"
R = lambda r, **k: {"rank": r, **k}
PROPS = {
    T1: {0: {"tensor_1": R(3)}, 1: {"tensor_1": R(0)}, 5: {"tensor_1": {"dtype": "string"}}, 6: {"tensor_1": R(0)},
         7: {"tensor_1": R(0)}, 8: {"tensor_1": R(1)}, 9: {"tensor_1": {"empty": True}}, 10: {"tensor_1": {"neg": True}},
         12: {"tensor_1": {"empty": True}}, 13: {"tensor_1": R(2)}, 14: {"tensor_1": {"empty": True}},
         15: {"tensor_1": R(3)}, 16: {"tensor_1": R(1)}, 18: {"tensor_1": {"dtype": "complex"}}, 22: {"tensor_1": R(0)},
         29: {"tensor_1": R(1, empty=True)}, 30: {"tensor_1": R(1)}, 33: {"tensor_1": {"empty": True}},
         34: {"tensor_1": R(1)}, 35: {"tensor_1": R(2)}, 36: {"tensor_1": R(1)}, 37: {"tensor_1": R(5)},
         38: {"tensor_1": R(5)}, 39: {"tensor_1": R(0)}, 40: {"tensor_1": R(3)}, 43: {"tensor_1": R(2)},
         45: {"tensor_1": {"dtype": "float"}}, 46: {"tensor_1": R(2)}, 49: {"tensor_1": R(3)},
         51: {"tensor_1": {"dtype": "float"}}},
    "['tensor_2']": {0: {"tensor_2": R(2)}},
    PAIR: {1: {"tensor_1": {"dtype": "float32"}, "tensor_2": {"dtype": "int32"}},
           2: {"tensor_1": {"dtype": "int"}, "tensor_2": {"dtype": "float"}},
           4: {"tensor_1": R(2, mismatch=True), "tensor_2": R(1, mismatch=True)},
           5: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           6: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           7: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           8: {"tensor_1": R(0, mismatch=True), "tensor_2": R(2, mismatch=True)},
           9: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           10: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           12: {"tensor_1": R(3, mismatch=True), "tensor_2": R(2, mismatch=True)},
           13: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           16: {"tensor_1": R(2), "tensor_2": R(2)},
           17: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           18: {"tensor_1": {"dtype": "complex"}, "tensor_2": {"dtype": "float"}},
           22: {"tensor_1": {"dtype": "complex64"}, "tensor_2": {"dtype": "float32"}},
           24: {"tensor_1": R(1, mismatch=True), "tensor_2": R(0, mismatch=True)},
           25: {"tensor_1": {"mismatch": True}, "tensor_2": {"mismatch": True}},
           26: {"tensor_1": R(3, mismatch=True), "tensor_2": R(3, mismatch=True)},
           27: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)},
           28: {"tensor_1": R(1, mismatch=True), "tensor_2": R(2, mismatch=True)},
           29: {"tensor_1": R(5), "tensor_2": R(5)},
           30: {"tensor_1": {"mismatch": True}, "tensor_2": {"mismatch": True}},
           31: {"tensor_1": {"mismatch": True}, "tensor_2": {"mismatch": True}}},
    "['tensor_1', 'tensor_2', 'tensor_3']": {0: {"tensor_1": R(1), "tensor_2": R(2), "tensor_3": R(3)},
                                             1: {"tensor_1": R(1), "tensor_2": R(2), "tensor_3": R(3)},
                                             2: {"tensor_1": R(2), "tensor_2": R(1), "tensor_3": R(2)},
                                             3: {"tensor_1": R(3), "tensor_2": R(3), "tensor_3": R(1)},
                                             5: {"tensor_1": {"dtype": "int32"}, "tensor_2": {"dtype": "float64"},
                                                 "tensor_3": {"dtype": "int64"}}},
    "['int_1', 'tensor_1']": {0: {"int_1": {"neg": True}, "tensor_1": R(2)}, 1: {"tensor_1": R(3)},
                              5: {"tensor_1": R(3)}},
    "['bool_1', 'tensor_1']": {0: {"tensor_1": {"empty": True}}, 1: {"tensor_1": R(2)},
                               2: {"tensor_1": R(4, empty=True)}, 3: {"tensor_1": R(2)}},
    "['list_1', 'tensor_1']": {0: {"tensor_1": R(2)}, 1: {"tensor_1": R(4)}, 2: {"tensor_1": R(3)}},
    "['int_1', 'tensor_1', 'tensor_2']": {0: {"tensor_1": R(2, mismatch=True), "tensor_2": R(2, mismatch=True)}},
    "['int_1', 'int_2', 'tensor_1']": {0: {"int_1": {"neg": True}}},
    "['int_1']": {1: {"int_1": {"neg": True}}, 3: {"int_1": {"neg": True}}},
    "['float_1']": {0: {"float_1": {"neg": True}}, 2: {"float_1": {"neg": True}}},
    "['scalar_1']": {1: {"scalar_1": {"neg": True}}},
    "['int_1', 'int_2']": {0: {"int_1": {"neg": True}, "int_2": {"neg": True}}, 1: {"int_2": {"neg": True}}},
    "['int_1', 'int_2', 'int_3']": {0: {"int_1": {"neg": True}, "int_2": {"neg": True}, "int_3": {"neg": True}}},
}


def violates(need, cat, props, other_props=None):
    """Score (higher = better) how well a placeholder's props violate a gap's need; 0 = does not violate."""
    if not props:
        return 0
    r = props.get("rank")
    kind = need[0] if need else cat
    if kind == "rank_ge" and r is not None and need[1] is not None:
        return 10 - (need[1] - 1 - r) if r < need[1] else 0  # prefer the highest rank still too small
    if kind == "rank_eq" and r is not None and need[1] is not None:
        return 10 - abs(r - need[1]) if r != need[1] else 0
    if kind == "rank_le" and r is not None and need[1] is not None:
        return 10 - (r - need[1]) if r > need[1] else 0
    if kind in ("rank_ge", "rank_eq", "rank_le", "rank") and (r is not None or props.get("empty")):
        return 5 if r in (0, 1) or props.get("empty") else 3
    if kind == "numel_eq":
        return 9 if (r is not None and r >= 1) or props.get("empty") else 0
    if kind in ("merge", "dim", "shape", "numel"):
        return 8 if props.get("mismatch") else 4 if props.get("empty") else 2 if r is not None else 0
    if kind == "dtype":
        return 8 if props.get("dtype") else 0
    if kind == "value":
        return 8 if props.get("neg") else 0
    return 0


def best_released(param_type, need, cat):
    """Best released edge case for a gap on a parameter whose DFUZZ type is param_type (individual patterns)."""
    t = (param_type or "").lower()
    keys = [T1, "['tensor_2']"] if "tensor" in t else [f"['{x}_1']" for x in ("int", "float", "scalar", "list", "bool")
                                                         if x in t]
    best = None
    for key in keys:
        for idx, pr in PROPS.get(key, {}).items():
            ph = key.strip("[]'").split("', '")[0]
            sc = violates(need, cat, pr.get(ph))
            if sc and (best is None or sc > best[0]):
                best = (sc, key, idx, EDGE[key][idx])
    return {"pattern": best[1], "idx": best[2], "text": best[3], "score": best[0]} if best else None


if __name__ == "__main__":
    assert best_released("Tensor", ["rank_ge", 4], "rank")["text"] == "A tensor with 3 dimensions, each dimension of size greater than 1"
    assert best_released("Tensor", ["numel_eq", 1], "numel") is not None
    assert all(idx < len(EDGE[k]) for k, d in PROPS.items() for idx in d)
    print("ok", sum(len(d) for d in PROPS.values()), "annotated edge cases")
