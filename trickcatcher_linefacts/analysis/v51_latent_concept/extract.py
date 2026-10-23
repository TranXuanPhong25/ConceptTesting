"""v51 step 2: hidden states of a frozen Qwen2.5-Coder-1.5B-Instruct on each example (see PREREG.md). CPU.

    ~/.local/state/concepttester_v51/venv/bin/python trickcatcher_linefacts/analysis/v51_latent_concept/extract.py check
    ~/.local/state/concepttester_v51/venv/bin/python trickcatcher_linefacts/analysis/v51_latent_concept/extract.py {train,eval}

Per task, the token prefix shared by all its prompts (chat template + spec) is run once and cached; each example runs
only its own suffix, then the cache is cropped back. `check` verifies cached == uncached on 3 prompts. Output per task:
out/analysis/v51_latent_concept/feats/<split>/<task>.npz with h [n, layers, d] (float16), verbal, intrinsic, index.
Resumable: finished tasks are skipped.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache

HOME = Path(__file__).resolve().parents[2]
OUT = HOME / 'out' / 'analysis' / 'v51_latent_concept'
MODEL = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'
LAYERS = (4, 8, 12, 16, 20, 24, 28)
QUESTION = 'Does the observed result satisfy the specification? Answer Yes or No.'


def prompt(ex):
    return (f"Specification:\n{ex['spec']}\n\nCall: {ex['entry']}{ex['call']}\nObserved result: {ex['observed']}"
            f"\n\n{QUESTION}")


class Extractor:
    def __init__(self):
        torch.set_num_threads(os.cpu_count())
        self.tok = AutoTokenizer.from_pretrained(MODEL)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()
        self.yes, self.no = self.tok.encode('Yes')[0], self.tok.encode('No')[0]

    def encode(self, ex):
        text = self.tok.apply_chat_template([{'role': 'user', 'content': prompt(ex)}], tokenize=False,
                                            add_generation_prompt=True)
        enc = self.tok(text, return_offsets_mapping=True)
        start = text.index('Observed result: ') + len('Observed result: ')
        end = start + len(ex['observed'])
        start += len(ex['observed'].split(' ', 1)[0]) + 1  # the literal only, not the word 'returned'/'raised'
        span = [i for i, (a, b) in enumerate(enc['offset_mapping']) if b > start and a < end]  # overlapping tokens
        return enc['input_ids'], span

    @torch.no_grad()
    def run(self, ids, span, cache=None, offset=0):
        """Forward ids[offset:] on top of a cache holding ids[:offset]; features at the last position."""
        x = torch.tensor([ids[offset:]])
        out = self.model(input_ids=x, past_key_values=cache, use_cache=cache is not None, output_hidden_states=True)
        h = torch.stack([out.hidden_states[k][0, -1] for k in LAYERS]).numpy()
        logits = out.logits[0, -1]
        verbal = float(logits[self.no] - logits[self.yes])
        logp = torch.log_softmax(out.logits[0], -1)  # row j predicts token offset + j + 1
        lp = [float(logp[j - offset - 1, ids[j]]) for j in span if j - offset - 1 >= 0]
        intrinsic = -sum(lp) / len(lp) if lp else float('nan')
        return h, verbal, intrinsic

    @torch.no_grad()
    def task(self, examples):
        encoded = [self.encode(ex) for ex in examples]
        first = encoded[0][0]
        common = min(next((i for i, (a, b) in enumerate(zip(first, ids)) if a != b), min(len(first), len(ids)))
                     for ids, _ in encoded)
        common = min(common, min(span[0] if span else len(ids) for ids, span in encoded)) - 1
        cache = DynamicCache()
        self.model(input_ids=torch.tensor([first[:common]]), past_key_values=cache, use_cache=True)
        rows = []
        for ids, span in encoded:
            rows.append(self.run(ids, span, cache, common))
            cache.crop(common)
        return rows


def load(split):
    rows = [json.loads(line) for line in (OUT / f'{split}.jsonl').read_text().splitlines()]
    by_task = defaultdict(list)
    for i, r in enumerate(rows):
        by_task[r['task']].append((i, r))
    return by_task


def check():
    ex = Extractor()
    tasks = load('eval')
    items = next(iter(tasks.values()))[:3]
    cached = ex.task([r for _, r in items])
    worst = 0.0
    for (_, r), (h, verbal, intrinsic) in zip(items, cached):
        ids, span = ex.encode(r)
        h0, v0, i0 = ex.run(ids, span)
        worst = max(worst, float(np.abs(h0 - h).max() / (np.abs(h0).max() + 1e-9)), abs(v0 - verbal), abs(i0 - intrinsic))
    print(f'cached vs uncached: max relative diff {worst:.2e}')
    if worst >= 1e-3:
        raise SystemExit('cache check FAILED')


def extract(split):
    ex = Extractor()
    directory = OUT / 'feats' / split
    directory.mkdir(parents=True, exist_ok=True)
    tasks = load(split)
    for n, (task, items) in enumerate(sorted(tasks.items())):
        path = directory / f"{task.replace('/', '_')}.npz"
        if path.exists():
            continue
        rows = ex.task([r for _, r in items])
        np.savez(path, index=np.array([i for i, _ in items]), h=np.stack([r[0] for r in rows]).astype(np.float16),
                 verbal=np.array([r[1] for r in rows]), intrinsic=np.array([r[2] for r in rows]))
        print(f'{split} {n + 1}/{len(tasks)} {task} n={len(items)}', flush=True)


if __name__ == '__main__':
    check() if sys.argv[1] == 'check' else extract(sys.argv[1])
