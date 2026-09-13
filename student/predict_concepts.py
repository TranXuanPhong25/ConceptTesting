#!/usr/bin/env python3
"""A — ConceptCoder lam BO CAP CONCEPT (learned). Nap checkpoint da train (LoRA + heads), du doan
concept PER-LINE cho moi ham target, xuat items voi `lines_concept` HOC-DUOC (cung format tree-sitter
-> drop thang vao prompt builder concept/concept_static hien co).

Checkpoint = output cua student/kaggle_train.py:  <ckpt>/lora/ (adapters)  +  <ckpt>/heads.pt (cbl+classifier)

Chay (can GPU; Kaggle):
  python student/predict_concepts.py --ckpt /kaggle/input/cc-ckpt/ckpt \
     --base Qwen/Qwen2.5-Coder-3B --model_type qwen \
     --in "magma/items/*.jsonl" --outdir magma/items_learned --func_key func_vuln

So sanh sau do: chay magma/loop.py 2 lan — GOLD=items goc (tree-sitter) vs GOLD=items_learned (learned).
"""
import os, sys, glob, json, argparse, importlib.util
from types import SimpleNamespace

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VD = os.path.join(ROOT, "ConceptCoder", "code", "concept_learning", "VD")
sys.path.insert(0, VD)

import transformers                                                    # noqa: E402
if not hasattr(transformers, "AdamW"):                                 # SHIM (transformers moi da go)
    from torch.optim import AdamW as _A
    transformers.AdamW = _A
if not hasattr(transformers, "WEIGHTS_NAME"):
    transformers.WEIGHTS_NAME = "pytorch_model.bin"

_s = importlib.util.spec_from_file_location("cc_vd", os.path.join(VD, "statement_level_sequential_multi_tasking.py"))
cc = importlib.util.module_from_spec(_s); _s.loader.exec_module(cc)
from transformers import AutoConfig, AutoModel, AutoTokenizer          # noqa: E402


def load_model(a):
    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    cfg = AutoConfig.from_pretrained(a.base)
    if cfg.pad_token_id is None:
        cfg.pad_token_id = tok.pad_token_id
    enc = AutoModel.from_pretrained(a.base, torch_dtype=torch.float16)
    from peft import PeftModel                                         # noqa: E402
    enc = PeftModel.from_pretrained(enc, os.path.join(a.ckpt, "lora"))
    args = SimpleNamespace(block_size=a.block_size, max_statements=a.max_statements,
                           concepts=a.concepts, model_type=a.model_type, target_key="target")
    model = cc.DecoderClassifier(enc, cfg, tok, args)
    sd = torch.load(os.path.join(a.ckpt, "heads.pt"), map_location="cpu")
    model.cbl.load_state_dict(sd["cbl"]); model.classifier.load_state_dict(sd["classifier"])
    model.cbl.float(); model.classifier.float()
    return model, tok, args


@torch.no_grad()
def predict(model, tok, args, func, dev, thr):
    """-> (lines_concept hoc-duoc, prob_vuln). Chi phu cac dong LOT vao block_size/max_statements."""
    lines = func.split("\n")
    js = {"func": func, "idx": 0, "target": 0,
          "lines_concept": {str(i): [0] * args.concepts for i in range(max(1, len(lines)))}}
    f = cc.convert_examples_to_features(js, tok, args)
    ids = torch.tensor([f.input_ids]).to(dev); t2l = torch.tensor([f.tok_to_line_map]).to(dev)
    n_cov = len({i for i in f.tok_to_line_map if i >= 0})               # so dong THUC SU duoc model nhin
    with torch.autocast("cuda", dtype=torch.float16, enabled=(dev == "cuda")):
        out = model(ids, tok_to_line_map=t2l)
    prob, cbl = out[0][0], out[1][0]                                    # cbl: [max_statements, concepts]
    lc = {str(i): [int(cbl[i][j].item() > thr) for j in range(args.concepts)]
          for i in range(min(len(lines), args.max_statements, cbl.shape[0]))}
    return lc, float(prob[1].item()), n_cov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True); ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-3B")
    ap.add_argument("--model_type", default="qwen")
    ap.add_argument("--in", dest="inp", required=True, help="glob, vd 'magma/items/*.jsonl'")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--func_key", default="func_vuln")
    ap.add_argument("--block_size", type=int, default=512)
    ap.add_argument("--max_statements", type=int, default=100)
    ap.add_argument("--concepts", type=int, default=8)
    ap.add_argument("--thr", type=float, default=0.5)
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, tok, args = load_model(a); model.to(dev).eval()
    os.makedirs(a.outdir, exist_ok=True)
    files = sorted(glob.glob(a.inp))
    print("files:", len(files), "| device:", dev)
    tot = 0
    for fp in files:
        items = [json.loads(l) for l in open(fp) if l.strip()]
        out = os.path.join(a.outdir, os.path.basename(fp))
        with open(out, "w") as fo:
            for it in items:
                func = it.get(a.func_key) or it.get("func") or ""
                if not func.strip():
                    fo.write(json.dumps(it) + "\n"); continue
                lc, pv, n_cov = predict(model, tok, args, func, dev, a.thr)
                it["lines_concept_treesitter"] = it.get("lines_concept")   # giu ban cu doi chieu
                it["lines_concept"] = lc                                   # <- prompt se dung cai nay
                it["concepts"] = [int(any(v[j] for v in lc.values())) for j in range(a.concepts)]
                it["cc_prob_vuln"] = pv; it["cc_lines_covered"] = n_cov
                fo.write(json.dumps(it) + "\n"); tot += 1
        print("  %-28s -> %s (%d item)" % (os.path.basename(fp), out, len(items)), flush=True)
    print("XONG: %d item. lines_concept = ConceptCoder learned (ban tree-sitter o lines_concept_treesitter)" % tot)


if __name__ == "__main__":
    main()
