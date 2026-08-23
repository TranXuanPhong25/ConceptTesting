#!/usr/bin/env python3
"""05 - Export train/test sang dang SFT {"prompt","completion"} de train tren GCP.

Doc with_concept.jsonl + distill_cache_v3.jsonl -> voi moi ham CO DU 2 target,
xuat cap (prompt, completion) cho 2 nhanh:
  - concept : prompt = build_concept(d),   completion = teacher target (concept)
  - blind   : prompt = build_blind_adv(d), completion = teacher target (blind_adv)

Split theo PROJECT (linux luon nam train) -> khong ro ri chuc nang giua train/test.

--format:
  vertex         : schema Vertex AI managed tuning (Gemini): {"systemInstruction","contents":[user,model]}.
                   DUNG khi tune Gemini tren Vertex (Tuning ▸ Create a tuned model).
  chat           : prompt/completion theo template Qwen2.5 (<|im_start|>...). Cho trainer completion/raw tren Qwen.
  plain          : prompt = system + '\n\n' + user (KHONG token chat); completion = target.
                   Cho trainer TU AP chat template (tranh double-template).

Chay:
    python pipeline_v3/05_export_sft.py --format vertex          # <-- cho Vertex Gemini tuning
    python pipeline_v3/05_export_sft.py --format chat --with-meta
Ra: data/work/sft_{concept,blind}_{train,test}.jsonl  (vertex: schema strict, khong meta)
"""
import os, sys, json, argparse, random, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import build_blind_adv, build_concept, cache_key

IM_END = "<|im_end|>"
IN = "data/work/with_concept.jsonl"
OUTDIR = "data/work"
BUILD = {"concept": build_concept, "blind": build_blind_adv}
COND_KEY = {"concept": "concept", "blind": "blind_adv"}   # ten cond trong cache


def render_chat_prompt(msgs):
    s = "".join("<|im_start|>%s\n%s%s\n" % (m["role"], m["content"], IM_END) for m in msgs)
    return s + "<|im_start|>assistant\n"


def render_plain_prompt(msgs):
    return "\n\n".join(m["content"] for m in msgs)


def to_record(d, cond, fmt, with_meta):
    msgs = BUILD[cond](d); sys_txt = msgs[0]["content"]; user_txt = msgs[1]["content"]; tgt = d["_tgt"]
    if fmt == "vertex":   # schema Vertex Gemini SFT (strict, roles user/model)
        return {"systemInstruction": {"role": "system", "parts": [{"text": sys_txt}]},
                "contents": [{"role": "user",  "parts": [{"text": user_txt}]},
                             {"role": "model", "parts": [{"text": tgt}]}]}
    if fmt == "chat":
        rec = {"prompt": render_chat_prompt(msgs), "completion": "%s%s\n" % (tgt, IM_END)}
    else:  # plain
        rec = {"prompt": render_plain_prompt(msgs), "completion": tgt}
    if with_meta:
        rec.update(target=d.get("target"), family_pred=d.get("family_pred"),
                   project=d.get("project"), cond=cond)
    return rec


def split_projects(rows, test_frac, seed):
    byp = collections.defaultdict(list)
    for d in rows:
        byp[d.get("project", "?")].append(d)
    projs = [p for p in byp if p != "linux"]                 # linux -> luon train
    random.Random(seed).shuffle(projs)
    n_test = int(test_frac * len(rows)); test = []; test_projs = set()
    for p in projs:
        if len(test) >= n_test:
            break
        test.extend(byp[p]); test_projs.add(p)
    train = [d for d in rows if d.get("project", "?") not in test_projs]
    return train, test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["vertex", "chat", "plain"], default="vertex")
    ap.add_argument("--conds", default="concept,blind")
    ap.add_argument("--teacher_model", default=os.environ.get("TEACHER_MODEL", "gemini-2.5-flash"))
    ap.add_argument("--test_frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--with-meta", action="store_true", help="them target/family_pred/project vao moi dong")
    a = ap.parse_args()

    if not os.path.exists(IN):
        raise SystemExit("Thieu %s. Chay 01+02 truoc." % IN)
    cache = {}
    for cf in ["distill_cache_v3.jsonl"]:
        if os.path.exists(cf):
            for l in open(cf):
                try:
                    o = json.loads(l); cache[o["key"]] = o["target"]
                except Exception:
                    pass
    rows = [json.loads(l) for l in open(IN) if l.strip()]

    conds = a.conds.split(",")
    # chi giu ham CO DU target cho MOI cond duoc yeu cau (de train/test khop nhau)
    usable = []
    for d in rows:
        if all(cache.get(cache_key(a.teacher_model, COND_KEY[c], d["func"])) for c in conds):
            usable.append(d)
    print("format:", a.format, "| teacher:", a.teacher_model, "| conds:", conds)
    print("pool:", len(rows), "| dung duoc (du target moi cond):", len(usable),
          "| target:", dict(collections.Counter(d.get("target") for d in usable)))
    if not usable:
        raise SystemExit("0 ham dung duoc -> kiem TEACHER_MODEL khop cache va cache co du 2 cond.")

    train, test = split_projects(usable, a.test_frac, a.seed)
    print("split -> train:", len(train), "| test:", len(test))

    for cond in conds:
        for name, part in [("train", train), ("test", test)]:
            out = os.path.join(OUTDIR, "sft_%s_%s.jsonl" % (cond, name))
            n = 0
            with open(out, "w") as fo:
                for d in part:
                    d["_tgt"] = cache[cache_key(a.teacher_model, COND_KEY[cond], d["func"])]
                    rec = to_record(d, cond, a.format, a.with_meta and a.format != "vertex")
                    fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); n += 1
            print("  ghi %-28s %d dong" % (out, n))
    print("\nXong. Upload cac file sft_*_train.jsonl / sft_*_test.jsonl len GCP.")


if __name__ == "__main__":
    main()
