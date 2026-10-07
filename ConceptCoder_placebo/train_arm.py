#!/usr/bin/env python3
"""One arm of the ConceptCoder placebo study (LoRA, 1x T4). Derived from student/kaggle_train.py.

Arms differ ONLY as listed in ARMS; model, LoRA config, tokenisation (the authors' per-line
convert_examples_to_features), data order, seed and hyper-parameters are identical.
Models come unmodified from the authors' files (ConceptCoder_org/.../VD/*.py); we call their
forward WITHOUT labels and compute the loss here, because (a) their in-forward BCE casts targets to
bf16 (patched in the old student copy) and (b) their released regular forward appends an undefined
`loss` (NameError). Loss = their formula: CE(vuln, class-weighted) + concept_weight * BCE(per-line).

  python train_arm.py --arm placebo --cc_vd <dir with authors' VD .py> --data_dir <data/VD> --out out/placebo
"""
import os, sys, json, time, random, hashlib, argparse, importlib.util
sys.dont_write_bytecode = True                          # never drop __pycache__ into the authors' dir
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from transformers import AutoConfig, AutoModel, AutoTokenizer

#            head          train file                     concept_weight
ARMS = {"conceptcoder":      ("bottleneck", "train_concept.jsonl",         0.2),
        "placebo":           ("bottleneck", "train_concept_placebo.jsonl", 0.2),
        "regular":           ("bottleneck", "train_concept.jsonl",         0.0),
        "regular_paperhead": ("lasttoken",  "train_concept.jsonl",         0.0)}


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--arm", required=True, choices=list(ARMS))
    p.add_argument("--cc_vd", required=True, help="dir with the authors' VD python files")
    p.add_argument("--data_dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B")
    p.add_argument("--model_type", default="qwen")
    p.add_argument("--seed", type=int, default=123456)          # authors' seed
    p.add_argument("--epoch", type=int, default=1)
    p.add_argument("--bs", type=int, default=2)
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--block_size", type=int, default=512)
    p.add_argument("--max_statements", type=int, default=100)
    p.add_argument("--concepts", type=int, default=8)
    p.add_argument("--eval_bs", type=int, default=8)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--fit_n", type=int, default=1000, help="train functions used to measure label fit")
    p.add_argument("--max_train", type=int, default=0, help="smoke only")
    p.add_argument("--max_eval", type=int, default=0, help="smoke only")
    return p.parse_args()


def load_module(name, path):
    t = sys.modules["transformers"]      # SHIM: authors' code targets transformers ~4.48. Re-applied per load:
    for k, v in (("AdamW", torch.optim.AdamW), ("WEIGHTS_NAME", "pytorch_model.bin")):  # newer transformers
        if not hasattr(t, k):                                                          # swaps the lazy module
            setattr(t, k, v)
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def seed_all(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def dataset(cc, tok, args, path, limit=0):
    ds = cc.TextDataset.__new__(cc.TextDataset)
    ds.examples = []
    with open(path) as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            js = json.loads(line)
            if "robustness" in path:     # released file keeps the ORIGINAL function's line labels (2887/2892 rows
                lc = js["lines_concept"]  # have more lines than labels -> authors' loader KeyErrors); VD-only use, zero-fill
                js["lines_concept"] = {str(k): lc.get(str(k), [0] * args.concepts) for k in range(len(js["func"].split("\n")))}
            ds.examples.append(cc.convert_examples_to_features(js, tok, args))
    return ds


def macro(y, p):
    return dict(macro_f1=100 * f1_score(y, p, average="macro", zero_division=0),
                per_concept_f1=[round(100 * x, 2) for x in f1_score(y, p, average=None, zero_division=0)],
                pred_pos_rate=p.mean(0).round(4).tolist(), true_pos_rate=y.mean(0).round(4).tolist())


@torch.no_grad()
def run_eval(model, head, ds, a, dev, store, cc):
    """-> per-example rows, per-line pooled reps, per-line true labels, per-line concept-head preds, n_lines."""
    model.eval()
    rows, reps, labs, cpred, nl = [], [], [], [], []
    for ids, y, cl, t2l, idx in DataLoader(ds, batch_size=a.eval_bs, shuffle=False, num_workers=a.workers):
        ids, t2l = ids.to(dev), t2l.to(dev)
        with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
            prob = model(ids, tok_to_line_map=t2l)[0] if head == "bottleneck" else model(ids)[0]
            pooled, _, lengths = cc.average_pool_by_segments_optimized(store["h"], t2l, max_segments=a.max_statements)
        p1 = prob[:, 1].float().cpu()
        for i in range(len(y)):
            rows.append({"idx": int(idx[i]), "label": int(y[i]), "p1": round(float(p1[i]), 6), "pred": int(p1[i] > 0.5)})
            k = min(int(lengths[i]), int((~(cl[i] == -1).all(-1)).sum()))
            nl.append(k)
            reps.append(pooled[i, :k].half().cpu()); labs.append(cl[i, :k].numpy())
            if head == "bottleneck":
                cpred.append((store["lc"][i, :k] > 0).int().cpu().numpy())
    model.train()
    return rows, torch.cat(reps), np.concatenate(labs), (np.concatenate(cpred) if cpred else None), nl


def vd_metrics(rows):
    y = [r["label"] for r in rows]; p = [r["pred"] for r in rows]
    return dict(n=len(y), pos_rate=100 * np.mean(y), acc=100 * accuracy_score(y, p),
                prec=100 * precision_score(y, p, zero_division=0), rec=100 * recall_score(y, p, zero_division=0),
                f1=100 * f1_score(y, p, zero_division=0), pred_pos_rate=100 * np.mean(p))


def linear_probe(Xtr, Ytr, Xte, Yte, dev, seed, epochs=20, bs=64, lr=1e-3):
    """Authors' probe (Linear + BCEWithLogits, Adam 1e-3, bs 64); fixed epochs instead of valid selection."""
    torch.manual_seed(seed)
    Xtr, Ytr = Xtr.float().to(dev), torch.tensor(Ytr, dtype=torch.float32, device=dev)
    lin = torch.nn.Linear(Xtr.shape[1], Ytr.shape[1]).to(dev)
    opt = torch.optim.Adam(lin.parameters(), lr=lr)
    for _ in range(epochs):
        perm = torch.randperm(len(Xtr), device=dev)
        for s in range(0, len(Xtr), bs):
            b = perm[s:s + bs]
            loss = F.binary_cross_entropy_with_logits(lin(Xtr[b]), Ytr[b])
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        P = torch.cat([(lin(Xte[s:s + 4096].float().to(dev)) > 0).int().cpu() for s in range(0, len(Xte), 4096)])
    return macro(Yte.astype(int), P.numpy())


def main():
    a = get_args()
    head, train_file, cw = ARMS[a.arm]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(a.out, exist_ok=True)
    cc = load_module("cc_vd", os.path.join(a.cc_vd, "statement_level_sequential_multi_tasking.py"))
    reg = load_module("cc_reg", os.path.join(a.cc_vd, "vulnerability_detection_regular_finetune.py"))
    args = SimpleNamespace(block_size=a.block_size, max_statements=a.max_statements, concepts=a.concepts,
                           model_type=a.model_type, target_key="target")
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    cfg = AutoConfig.from_pretrained(a.model)
    if cfg.pad_token_id is None:
        cfg.pad_token_id = tok.pad_token_id

    seed_all(a.seed)
    enc = AutoModel.from_pretrained(a.model, torch_dtype=torch.float16 if dev == "cuda" else torch.float32)
    enc.gradient_checkpointing_enable()
    from peft import LoraConfig, get_peft_model
    enc = get_peft_model(enc, LoraConfig(r=a.lora_r, lora_alpha=2 * a.lora_r, lora_dropout=0.05, bias="none",
                                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    seed_all(a.seed)
    model = (cc if head == "bottleneck" else reg).DecoderClassifier(enc, cfg, tok, args)
    for m in (getattr(model, "cbl", None), model.classifier):
        if m is not None:
            m.float()
    model.to(dev)
    store = {}
    model.encoder.register_forward_hook(lambda m, i, o: store.__setitem__("h", o[0]))
    if head == "bottleneck":
        model.cbl.register_forward_hook(lambda m, i, o: store.__setitem__("lc", o))

    d = a.data_dir
    if train_file != "train_concept.jsonl":                      # placebo: same functions, same order
        key = lambda fn: [(r["idx"], r["target"], hash(r["func"])) for r in map(json.loads, open(os.path.join(d, fn)))]
        assert key(train_file) == key("train_concept.jsonl")
    tr = dataset(cc, tok, args, os.path.join(d, train_file), a.max_train)
    print("arm=%s head=%s train=%s (%d) concept_weight=%s sha=%s" % (
        a.arm, head, train_file, len(tr), cw, sha(os.path.join(d, train_file))[:16]), flush=True)

    tl = DataLoader(tr, batch_size=a.bs, shuffle=True, num_workers=a.workers, drop_last=True,
                    generator=torch.Generator().manual_seed(a.seed))
    lab = np.array([f.label for f in tr.examples])
    w = torch.tensor([len(lab) / (2 * max(1, (lab == i).sum())) for i in (0, 1)], dtype=torch.float32, device=dev)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr)
    scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")
    steps = max(1, a.epoch * (len(tl) // a.accum))
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.05)
    print("trainable %.2fM | opt steps %d" % (sum(p.numel() for p in params) / 1e6, steps), flush=True)

    t0 = time.time(); grad_check = None; model.train()
    for ep in range(a.epoch):
        run = ce_run = bce_run = 0.0
        for i, (ids, y, cl, t2l, _) in enumerate(tl):
            ids, y, t2l = ids.to(dev), y.to(dev), t2l.to(dev)
            with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
                prob = model(ids, tok_to_line_map=t2l)[0] if head == "bottleneck" else model(ids)[0]
            ce = F.nll_loss(torch.log(prob.float().clamp_min(1e-12)), y, weight=w)
            loss = ce
            if head == "bottleneck":                              # logged for every bottleneck arm
                lc = store["lc"].float().reshape(-1, a.concepts)
                clf = cl.to(dev).float().reshape(-1, a.concepts)
                m = ~(clf == -1).all(1)
                bce = F.binary_cross_entropy_with_logits(lc[m], clf[m])
                bce_run += bce.item()
                if cw > 0:
                    loss = ce + cw * bce
            ce_run += ce.item(); run += loss.item()
            scaler.scale(loss / a.accum).backward()
            if grad_check is None:                                # LoRA must receive gradient
                grad_check = sum(float(p.grad.norm()) for n, p in model.named_parameters()
                                 if "lora_" in n and p.grad is not None)
                print("lora grad-norm sum after 1st backward: %.4g" % grad_check, flush=True)
                assert grad_check > 0, "no gradient reaches LoRA"
            if (i + 1) % a.accum == 0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(params, 1.0)
                scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
                if sch.last_epoch < steps - 1:
                    sch.step()
            if (i + 1) % (a.accum * 50) == 0:
                print("  ep%d %d/%d loss=%.4f ce=%.4f bce=%.4f (%.0f min)" % (
                    ep, i + 1, len(tl), run / (i + 1), ce_run / (i + 1), bce_run / (i + 1), (time.time() - t0) / 60), flush=True)
    train_min = (time.time() - t0) / 60
    model.encoder.save_pretrained(os.path.join(a.out, "lora"))
    torch.save({k: v for k, v in model.state_dict().items() if not k.startswith("encoder.")}, os.path.join(a.out, "heads.pt"))
    print("trained %.0f min; evaluating final model (no checkpoint selection)" % train_min, flush=True)

    res = dict(arm=a.arm, head=head, train_file=train_file, train_sha256=sha(os.path.join(d, train_file)),
               concept_weight=cw, seed=a.seed, epoch=a.epoch, lr=a.lr, bs=a.bs, accum=a.accum, lora_r=a.lora_r,
               n_train=len(tr), train_min=round(train_min, 1), lora_grad_check=grad_check,
               final_train_loss=run / max(1, len(tl)), final_ce=ce_run / max(1, len(tl)), final_bce=bce_run / max(1, len(tl)))
    sets = {"test": "test_concept.jsonl", "robust": "test_concept_robustness.jsonl",
            "probe_train": "train_concept_probing.jsonl", "probe_test": "test_concept_probing.jsonl"}
    keep = {}
    for name, fn in sets.items():
        t1 = time.time()
        rows, X, Y, CP, _ = run_eval(model, head, dataset(cc, tok, args, os.path.join(d, fn), a.max_eval), a, dev, store, cc)
        if not name.startswith("probe"):
            with open(os.path.join(a.out, "preds_%s.jsonl" % name), "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
            res[name] = vd_metrics(rows)
            print("%s: %s (%.0f min)" % (name, {k: round(v, 2) for k, v in res[name].items()}, (time.time() - t1) / 60), flush=True)
        if CP is not None and name in ("test", "probe_test"):
            res["concept_head_" + name] = macro(Y.astype(int), CP)
        if name.startswith("probe"):
            keep[name] = (X, Y)
    # authors' probing files: probe trained on train_concept_probing, tested on test_concept_probing
    res["linear_probe"] = linear_probe(*keep["probe_train"], *keep["probe_test"], dev, a.seed)
    del keep
    if head == "bottleneck":                                     # does the head fit the labels it was trained on?
        n_fit = a.fit_n if not a.max_eval else min(a.fit_n, a.max_eval)
        ds_true = dataset(cc, tok, args, os.path.join(d, "train_concept.jsonl"), n_fit)
        ds_plc = dataset(cc, tok, args, os.path.join(d, "train_concept_placebo.jsonl"), n_fit)
        _, _, Y, CP, nl = run_eval(model, head, ds_true, a, dev, store, cc)
        Yp = np.concatenate([np.array(ex.concept_label)[:k] for ex, k in zip(ds_plc.examples, nl)])
        res["fit_train_true_labels"] = macro(Y.astype(int), CP)
        res["fit_train_placebo_labels"] = macro(Yp.astype(int), CP)
    json.dump(res, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
    print("DONE arm=%s test F1=%.2f probe macroF1=%.2f" % (a.arm, res["test"]["f1"], res["linear_probe"]["macro_f1"]), flush=True)


if __name__ == "__main__":
    main()
