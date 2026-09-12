#!/usr/bin/env python3
"""A — ConceptCoder lam BO CAP CONCEPT (learned). Nap checkpoint da train, du doan concept PER-LINE cho
moi ham target, xuat ra items voi `lines_concept` HOC-DUOC (cung format tree-sitter -> drop thang vao
prompt builder concept/concept_static hien co).

Chay TREN KAGGLE (can GPU + checkpoint tu student/run_short.sh + accelerate). VD:
  python student/predict_concepts.py \
     --ckpt data/saved_models/VD/concept/Qwen2.5-Coder-3B/checkpoint-best-f1/statement_level_sequential/Qwen2.5-Coder-3B \
     --base Qwen/Qwen2.5-Coder-3B --model_type qwen \
     --in magma/items/libpng.jsonl --out magma/items_learned/libpng.jsonl --func_key func_vuln

So sanh: chay gen/loop 2 lan — GOLD=items goc (concept tree-sitter) vs GOLD=items_learned (concept ConceptCoder).
"""
import os, sys, json, argparse, importlib.util, types

VD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ConceptCoder", "code", "concept_learning", "VD")
sys.path.insert(0, os.path.abspath(VD))
spec = importlib.util.spec_from_file_location("cc_vd", os.path.join(VD, "statement_level_sequential_multi_tasking.py"))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)   # DecoderClassifier, convert_examples_to_features, MODEL_CLASSES

import torch                                                              # noqa: E402
from transformers import AutoConfig, AutoModel, AutoTokenizer            # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="thu muc checkpoint accelerate (accelerator.save_state)")
    ap.add_argument("--base", required=True, help="base model HF, vd Qwen/Qwen2.5-Coder-3B")
    ap.add_argument("--model_type", default="qwen")
    ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--func_key", default="func_vuln")
    ap.add_argument("--block_size", type=int, default=512)
    ap.add_argument("--concepts", type=int, default=8)
    ap.add_argument("--max_statements", type=int, default=512)
    ap.add_argument("--thr", type=float, default=0.5)
    a = ap.parse_args()
    a.target_key = "target"

    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    config = AutoConfig.from_pretrained(a.base)
    if config.pad_token_id is None:
        config.pad_token_id = tok.pad_token_id
    encoder = AutoModel.from_pretrained(a.base, torch_dtype=torch.float16)
    model = cc.DecoderClassifier(encoder, config, tok, a)

    from accelerate import Accelerator                                    # noqa: E402
    acc = Accelerator()
    model = acc.prepare(model)
    acc.load_state(a.ckpt)                                                # nap cbl + classifier + encoder da train
    model.eval()

    items = [json.loads(l) for l in open(a.inp) if l.strip()]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    n_lines_changed = 0
    with open(a.out, "w") as fo:
        for it in items:
            func = it.get(a.func_key) or it.get("func") or ""
            lines = func.split("\n")
            js = {"func": func, "idx": 0, "target": 0,
                  "lines_concept": {str(i): [0] * a.concepts for i in range(len(lines))}}
            feat = cc.convert_examples_to_features(js, tok, a)
            ids = torch.tensor([feat.input_ids]); t2l = torch.tensor([feat.tok_to_line_map])
            ids = ids.to(acc.device); t2l = t2l.to(acc.device)
            with torch.no_grad():
                out = model(ids, tok_to_line_map=t2l)                     # [prob, cbl_output(per-line sigmoid)]
            cbl = out[1][0]                                               # [max_statements, concepts]
            learned = {str(i): [int(cbl[i][j].item() > a.thr) for j in range(a.concepts)]
                       for i in range(min(len(lines), a.max_statements))}
            it["lines_concept_treesitter"] = it.get("lines_concept")      # giu ban cu de doi chieu
            it["lines_concept"] = learned                                 # concept HOC-DUOC -> prompt dung cai nay
            it["concepts"] = [int(any(learned[k][j] for k in learned)) for j in range(a.concepts)]
            n_lines_changed += 1
            fo.write(json.dumps(it) + "\n")
    print("XONG: %d item -> %s (lines_concept = ConceptCoder learned; ban tree-sitter luu o lines_concept_treesitter)"
          % (n_lines_changed, a.out))


if __name__ == "__main__":
    main()
