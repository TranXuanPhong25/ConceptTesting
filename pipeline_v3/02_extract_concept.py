#!/usr/bin/env python3
"""02 - Chay STATIC concept annotator (TAI DUNG tool cua ConceptCoder) tren tung func.

Nho vay concept DERIVABLE cho ham bat ky (khong phu thuoc nhan precomputed).
Gan:
  - concepts[8], lines_concept        <- tree-sitter (design_and_annotate_VD_concepts.bfs)
  - family_pred                        <- heuristic tu tuong tac concept (KHONG leak)
  - family_gold                        <- tu cwe, CHI de do cascade-error (khong vao prompt)

Yeu cau: tree_sitter_languages (pip install tree_sitter_languages).
Chay:  python pipeline_v3/02_extract_concept.py
In:    data/work/filtered.jsonl -> data/work/with_concept.jsonl
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import PROPS, predict_family, family_from_cwe

IN = "data/work/filtered.jsonl"
OUT = "data/work/with_concept.jsonl"
ANN_DIR = "ConceptCoder/code/design_concept"


def load_annotator():
    """Import tool static cua ConceptCoder; tra ve annotate(func)->(concepts, lines_concept)."""
    if not os.path.isdir(ANN_DIR):
        raise SystemExit("Khong thay %s (thu muc code ConceptCoder)." % ANN_DIR)
    sys.path.insert(0, ANN_DIR)  # de 'from utils_VD import *' trong annotator hoat dong
    try:
        import design_and_annotate_VD_concepts as ann  # noqa: chay top-level: parser=get_parser('cpp')
    except Exception as e:
        raise SystemExit("Khong load duoc static tool: %s\n-> pip install tree_sitter_languages" % e)

    def annotate(func):
        props_ = ann.bfs(func, ann.parser)                 # dict 8 concept -> list span
        n_lines = len(func.split("\n"))
        lc = {i: [0] * len(PROPS) for i in range(n_lines)}
        for j, prop in enumerate(PROPS):
            for span in props_[prop]:
                for li in span["lines"]:
                    if li in lc:
                        lc[li][j] = 1
        concepts = [0] * len(PROPS)
        for i in range(n_lines):
            for j in range(len(PROPS)):
                concepts[j] = max(concepts[j], lc[i][j])
        return concepts, {str(k): v for k, v in lc.items()}  # key string cho khop schema
    return annotate


def main():
    if not os.path.exists(IN):
        raise SystemExit("Thieu %s. Chay 01_filter_data.py truoc." % IN)
    annotate = load_annotator()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n = err = 0
    with open(OUT, "w") as fo:
        for line in open(IN):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            try:
                d["concepts"], d["lines_concept"] = annotate(d["func"])
            except Exception:
                d["concepts"], d["lines_concept"] = [0] * len(PROPS), {}
                err += 1
            d["family_pred"] = predict_family(d)
            d["family_gold"] = family_from_cwe(d.get("cwe") or [])
            fo.write(json.dumps(d) + "\n"); n += 1

    fam_pred = collections.Counter(json.loads(l)["family_pred"] for l in open(OUT))
    # do cascade: bao nhieu mau family_pred KHONG khop family_gold (chi tren mau co gold)
    both = [json.loads(l) for l in open(OUT)]
    have_gold = [r for r in both if r["family_gold"]]
    agree = sum(1 for r in have_gold if r["family_pred"] == r["family_gold"])
    print("Ghi %d -> %s | loi annotate: %d" % (n, OUT, err))
    print("family_pred:", dict(fam_pred))
    if have_gold:
        print("family_pred KHOP family_gold: %d/%d (%.0f%%) [chi tren mau co CWE gold]"
              % (agree, len(have_gold), 100 * agree / len(have_gold)))


if __name__ == "__main__":
    main()
