#!/usr/bin/env python3
"""ConceptCoder VD training cho KAGGLE (T4) — tai dung MODEL + DATA code GOC cua ho, doi co che fit GPU.

Vi sao KHONG dung nguyen run_conceptcoder_fine_tuning.sh:
  full-FT 3B = params fp32(12G) + grads(6G) + Adam m,v(24G) ~ 42GB -> can ZeRO-3 + CPU offload,
  ma Kaggle chi ~29GB RAM CPU -> OOM. => dung LoRA tren encoder (base fp16 6GB, fit 1xT4),
  van train ca `cbl` (concept bottleneck) + `classifier` => giu NGUYEN phuong phap multitask:
     loss = CE(vuln) * vul_weight + BCE(concept per-line) * concept_weight
Khac paper: LoRA thay full-FT -> so TUYET DOI se lech, nhung Delta concept-vs-baseline va `cbl`
(dung cho huong A: cap concept hoc-duoc) van do duoc.

Chay:  python student/kaggle_train.py --variant conceptcoder --epoch 3 --model Qwen/Qwen2.5-Coder-3B
       python student/kaggle_train.py --variant regular      --epoch 3   (baseline: concept_weight=0)
"""
import os, sys, json, time, argparse, importlib.util
from types import SimpleNamespace

import torch, numpy as np
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VD = os.path.join(ROOT, "ConceptCoder", "code", "concept_learning", "VD")
sys.path.insert(0, VD)

# SHIM: code cua ho viet cho transformers~4.48; ban moi da GO `AdamW` va `WEIGHTS_NAME`.
import transformers                                                    # noqa: E402
if not hasattr(transformers, "AdamW"):
    from torch.optim import AdamW as _AdamW
    transformers.AdamW = _AdamW
if not hasattr(transformers, "WEIGHTS_NAME"):
    transformers.WEIGHTS_NAME = "pytorch_model.bin"

_s = importlib.util.spec_from_file_location("cc_vd", os.path.join(VD, "statement_level_sequential_multi_tasking.py"))
cc = importlib.util.module_from_spec(_s); _s.loader.exec_module(cc)     # DecoderClassifier, TextDataset

from transformers import AutoConfig, AutoModel, AutoTokenizer          # noqa: E402


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B")
    p.add_argument("--model_type", default="qwen")
    p.add_argument("--variant", default="conceptcoder", choices=["conceptcoder", "regular"])
    p.add_argument("--data_dir", default=os.path.join(ROOT, "data", "VD"))
    p.add_argument("--dataset", default="concept")
    p.add_argument("--epoch", type=int, default=3)
    p.add_argument("--block_size", type=int, default=512)
    p.add_argument("--max_statements", type=int, default=100)
    p.add_argument("--concepts", type=int, default=8)
    p.add_argument("--bs", type=int, default=2)
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-4)                   # LoRA -> lr cao hon full-FT(2e-5)
    p.add_argument("--vul_weight", type=float, default=1.0)
    p.add_argument("--concept_weight", type=float, default=0.20)       # =0 neu variant=regular
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--max_train", type=int, default=0, help="0=het; >0 = cat bot de chay nhanh")
    p.add_argument("--out", default=os.path.join(ROOT, "ckpt"))
    return p.parse_args()


def build(a):
    args = SimpleNamespace(block_size=a.block_size, max_statements=a.max_statements,
                           concepts=a.concepts, model_type=a.model_type, target_key="target")
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    cfg = AutoConfig.from_pretrained(a.model)
    if cfg.pad_token_id is None:
        cfg.pad_token_id = tok.pad_token_id
    enc = AutoModel.from_pretrained(a.model, torch_dtype=torch.float16)
    enc.gradient_checkpointing_enable()

    from peft import LoraConfig, get_peft_model                        # noqa: E402
    enc = get_peft_model(enc, LoraConfig(
        r=a.lora_r, lora_alpha=2 * a.lora_r, lora_dropout=0.05, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    model = cc.DecoderClassifier(enc, cfg, tok, args)
    model.cbl.float(); model.classifier.float()                        # head fp32 cho on dinh
    return model, tok, args


@torch.no_grad()
def evaluate(model, loader, dev):
    model.eval(); P, L = [], []
    for ids, lab, cl, t2l, _ in loader:
        with torch.autocast("cuda", dtype=torch.float16):
            out = model(ids.to(dev), tok_to_line_map=t2l.to(dev))
        P += out[0].float().argmax(-1).cpu().tolist(); L += lab.tolist()
    model.train()
    return dict(acc=accuracy_score(L, P) * 100, prec=precision_score(L, P, zero_division=0) * 100,
                rec=recall_score(L, P, zero_division=0) * 100, f1=f1_score(L, P, zero_division=0) * 100)


def main():
    a = get_args()
    if a.variant == "regular":
        a.concept_weight = 0.0                                          # baseline: KHONG hoc concept
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, tok, args = build(a)
    model.to(dev)

    d = a.data_dir
    tr = cc.TextDataset(tok, args, os.path.join(d, "train_%s.jsonl" % a.dataset))
    te = cc.TextDataset(tok, args, os.path.join(d, "test_%s.jsonl" % a.dataset))
    if a.max_train:
        tr.examples = tr.examples[:a.max_train]
    print("train=%d test=%d | variant=%s concept_weight=%s" % (len(tr), len(te), a.variant, a.concept_weight))

    tl = DataLoader(tr, batch_size=a.bs, shuffle=True, num_workers=2, drop_last=True)
    el = DataLoader(te, batch_size=a.bs, num_workers=2)

    lab = np.array([f.label for f in tr.examples])                      # class weight (data mat can bang)
    w = torch.tensor([len(lab) / (2 * max(1, (lab == i).sum())) for i in (0, 1)], dtype=torch.float32, device=dev)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr)
    scaler = torch.amp.GradScaler("cuda")
    steps = a.epoch * (len(tl) // a.accum)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=max(1, steps), pct_start=0.05)
    print("optimizable params: %.2fM | steps=%d" % (
        sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6, steps))

    t0 = time.time(); best = 0.0
    for ep in range(a.epoch):
        run = 0.0
        for i, (ids, y, cl, t2l, _) in enumerate(tl):
            with torch.autocast("cuda", dtype=torch.float16):
                out = model(ids.to(dev), y.to(dev), cl.to(dev), t2l.to(dev), weight=w,
                            vul_weight=a.vul_weight, concept_weight=a.concept_weight)
            loss = out[0] / a.accum
            scaler.scale(loss).backward(); run += loss.item() * a.accum
            if (i + 1) % a.accum == 0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0)
                scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
                if sch.last_epoch < steps - 1:
                    sch.step()
            if (i + 1) % (a.accum * 50) == 0:
                print("  ep%d %d/%d loss=%.4f (%.0f min)" % (ep, i + 1, len(tl), run / (i + 1), (time.time() - t0) / 60), flush=True)
        m = evaluate(model, el, dev)
        print("EPOCH %d | acc=%.2f prec=%.2f rec=%.2f F1=%.2f | %.0f min"
              % (ep, m["acc"], m["prec"], m["rec"], m["f1"], (time.time() - t0) / 60), flush=True)
        if m["f1"] >= best:
            best = m["f1"]
            os.makedirs(a.out, exist_ok=True)
            model.encoder.save_pretrained(os.path.join(a.out, "lora"))   # LoRA adapters
            torch.save({"cbl": model.cbl.state_dict(), "classifier": model.classifier.state_dict()},
                       os.path.join(a.out, "heads.pt"))
            json.dump({"variant": a.variant, "epoch": ep, **m}, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
            print("  saved (best F1=%.2f) -> %s" % (best, a.out), flush=True)
    print("DONE variant=%s BEST_F1=%.2f" % (a.variant, best))


if __name__ == "__main__":
    main()
