"""v51 step 3: probes on frozen hidden states (see PREREG.md). CPU, scikit-learn.

    ~/.local/state/concepttester_v51/venv/bin/python trickcatcher_linefacts/analysis/v51_latent_concept/probe.py fit
    ~/.local/state/concepttester_v51/venv/bin/python trickcatcher_linefacts/analysis/v51_latent_concept/probe.py score

`fit` uses MBPP+ only: 80/20 task split, layer chosen by the direct probe's validation AUC (shared by arms A/B/C), L2
strength chosen per arm, then refit on all MBPP+ tasks. `score` applies the frozen models to the VibePass pool once.
"""
import ast
import json
import pickle
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
HOME = HERE.parents[1]
OUT = HOME / 'out' / 'analysis' / 'v51_latent_concept'
SEED = 20261023
LAYERS = (4, 8, 12, 16, 20, 24, 28)
CS = (0.001, 0.01, 0.1)
CONCEPTS = ('TYPE', 'BOOL_FLIP', 'ORDER', 'SIZE', 'NUM_NEAR', 'NUM_FAR', 'CONTENT')
TYPES = ('int', 'float', 'bool', 'str', 'list', 'tuple', 'dict', 'set', 'NoneType')


def load(split):
    rows = [json.loads(line) for line in (OUT / f'{split}.jsonl').read_text().splitlines()]
    parts = {}
    for path in sorted((OUT / 'feats' / split).glob('*.npz')):
        z = np.load(path)
        for i, k in enumerate(z['index']):
            parts[int(k)] = (z['h'][i], z['verbal'][i], z['intrinsic'][i])
    if len(parts) != len(rows):
        raise SystemExit(f'{split}: features for {len(parts)}/{len(rows)} examples; run extract.py first')
    h = np.stack([parts[i][0] for i in range(len(rows))])
    verbal = np.array([parts[i][1] for i in range(len(rows))])
    intrinsic = np.array([parts[i][2] for i in range(len(rows))])
    return rows, h, verbal, intrinsic


def kind(text):
    """Type name of the returned literal, or None."""
    if not text.startswith('returned '):
        return None
    try:
        return type(ast.literal_eval(text[len('returned '):])).__name__
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


def surface(rows):
    """Output-only features: literal length and returned type (amendment 1: no exception flag)."""
    return np.array([[np.log1p(len(r['observed']))] + [float(kind(r['observed']) == t) for t in TYPES] for r in rows])


def logistic(c):
    return LogisticRegression(C=c, max_iter=3000, tol=1e-3)


def macro_auc(y, s, groups):
    by = defaultdict(list)
    for g, a, b in zip(groups, y, s):
        by[g].append((a, b))
    aucs = [roc_auc_score([a for a, _ in v], [b for _, b in v]) for v in by.values() if len({a for a, _ in v}) == 2]
    return float(np.mean(aucs)) if aucs else float('nan')


class CBM:
    """Sequential concept bottleneck: concept probes h -> p_k, aggregator on out-of-fold p -> wrong."""

    def __init__(self, c):
        self.c = c

    def fit(self, x, concepts, y, groups):
        targets = np.array([[float(k == name) for name in CONCEPTS] for k in concepts])
        oof = np.zeros_like(targets)
        for tr, te in GroupKFold(5).split(x, y, groups):
            for j in range(len(CONCEPTS)):
                probe = self._probe(x[tr], targets[tr, j])
                oof[te, j] = probe.predict_proba(x[te])[:, 1] if probe is not None else 0.0
        self.probes = [self._probe(x, targets[:, j]) for j in range(len(CONCEPTS))]
        self.agg = LogisticRegression(max_iter=3000).fit(self._logit(oof), y)
        return self

    def _probe(self, x, t):
        return logistic(self.c).fit(x, t) if 0 < t.sum() < len(t) else None

    def concepts(self, x):
        return np.stack([p.predict_proba(x)[:, 1] if p is not None else np.zeros(len(x)) for p in self.probes], 1)

    @staticmethod
    def _logit(p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return np.log(p / (1 - p))

    def score(self, x):
        return self.agg.predict_proba(self._logit(self.concepts(x)))[:, 1]


PLACEBO_SEEDS = (0, 1, 2)


def placebo(concepts, y, kinds, seed):
    """Amendment 1: concept labels permuted among wrong examples with the same returned type, so the placebo keeps the
    routing by output type and differs from the real bottleneck only in discrepancy semantics."""
    out = list(concepts)
    for k in sorted(set(kinds), key=str):
        ix = [i for i, (t, kk) in enumerate(zip(y, kinds)) if t and kk == k]
        labels = [concepts[i] for i in ix]
        random.Random(f'{SEED}-{seed}-{k}').shuffle(labels)
        for i, label in zip(ix, labels):
            out[i] = label
    return out


def fit():
    rows, h, verbal, intrinsic = load('train')
    y = np.array([r['wrong'] for r in rows])
    groups = np.array([r['task'] for r in rows])
    concepts = [r['concept'] for r in rows]
    tasks = sorted(set(groups))
    random.Random(SEED).shuffle(tasks)
    val_tasks = set(tasks[:len(tasks) // 5])
    va = np.array([g in val_tasks for g in groups])
    tr = ~va
    report = dict(train_examples=int(tr.sum()), val_examples=int(va.sum()), val_tasks=len(val_tasks))

    def xs(layer):
        x = h[:, LAYERS.index(layer)].astype(np.float32)
        scaler = StandardScaler().fit(x[tr])
        return scaler.transform(x)

    direct = {}
    for layer in LAYERS:
        x = xs(layer)
        for c in CS:
            direct[layer, c] = macro_auc(y[va], logistic(c).fit(x[tr], y[tr]).predict_proba(x[va])[:, 1], groups[va])
    layer, c_direct = max(direct, key=direct.get)
    report['direct_val'] = {f'L{k[0]}_C{k[1]}': v for k, v in direct.items()}
    report['layer'] = layer
    x = xs(layer)
    kinds = [kind(r['observed']) for r in rows]
    pls = {seed: placebo(concepts, y, kinds, seed) for seed in PLACEBO_SEEDS}
    arms, fitted = {}, {}
    for name, labels in (('cbm', concepts), ('placebo', pls[0])):  # placebo C chosen on seed 0, used for all seeds
        scores = {}
        for c in CS:
            sub = [labels[i] for i in np.flatnonzero(tr)]
            fitted[name, c] = CBM(c).fit(x[tr], sub, y[tr], groups[tr])
            scores[c] = macro_auc(y[va], fitted[name, c].score(x[va]), groups[va])
        arms[name] = max(scores, key=scores.get)
        report[f'{name}_val'] = {str(k): v for k, v in scores.items()}
    s = surface(rows)
    s_scaler = StandardScaler().fit(s[tr])
    report['surface_val'] = macro_auc(y[va], logistic(1.0).fit(s_scaler.transform(s[tr]), y[tr])
                                      .predict_proba(s_scaler.transform(s[va]))[:, 1], groups[va])
    report['verbal_val'] = macro_auc(y[va], verbal[va], groups[va])
    report['intrinsic_val'] = macro_auc(y[va], intrinsic[va], groups[va])
    # per-concept probe quality on validation (one-vs-rest over all validation examples)
    pv = fitted['cbm', arms['cbm']].concepts(x[va])
    report['concept_val_auc'] = {k: float(roc_auc_score([concepts[i] == k for i in np.flatnonzero(va)], pv[:, j]))
                                 for j, k in enumerate(CONCEPTS)
                                 if 0 < sum(concepts[i] == k for i in np.flatnonzero(va)) < va.sum()}
    # refit everything on all MBPP+ tasks with the chosen settings
    x_all = h[:, LAYERS.index(layer)].astype(np.float32)
    scaler = StandardScaler().fit(x_all)
    xa = scaler.transform(x_all)
    models = dict(layer=layer, scaler=scaler, direct=logistic(c_direct).fit(xa, y),
                  cbm=CBM(arms['cbm']).fit(xa, concepts, y, groups),
                  **{f'placebo{seed}': CBM(arms['placebo']).fit(xa, pls[seed], y, groups) for seed in PLACEBO_SEEDS},
                  surface_scaler=StandardScaler().fit(s))
    models['surface'] = logistic(1.0).fit(models['surface_scaler'].transform(s), y)
    report['chosen'] = dict(layer=layer, c_direct=c_direct, c_cbm=arms['cbm'], c_placebo=arms['placebo'])
    (OUT / 'models.pkl').write_bytes(pickle.dumps(models))
    (HERE / 'fit_report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1))


def sign(w, l):
    from math import comb
    n = w + l
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n) if n else 1.0


def score():
    models = pickle.loads((OUT / 'models.pkl').read_bytes())
    rows, h, verbal, intrinsic = load('eval')
    y = np.array([r['wrong'] for r in rows])
    x = models['scaler'].transform(h[:, LAYERS.index(models['layer'])].astype(np.float32))
    scores = dict(direct=models['direct'].predict_proba(x)[:, 1], cbm=models['cbm'].score(x),
                  **{f'placebo{seed}': models[f'placebo{seed}'].score(x) for seed in PLACEBO_SEEDS},
                  verbal=verbal, intrinsic=intrinsic,
                  surface=models['surface'].predict_proba(models['surface_scaler'].transform(surface(rows)))[:, 1])
    cases = defaultdict(list)
    for i, r in enumerate(rows):
        cases[r['task']].append(i)
    evaluable = {c: ix for c, ix in cases.items() if len({y[i] for i in ix}) == 2}
    problem = {c: rows[ix[0]]['problem'] for c, ix in evaluable.items()}
    per_case = {arm: {c: float(roc_auc_score(y[ix], s[ix])) for c, ix in evaluable.items()} for arm, s in scores.items()}
    problems = sorted(set(problem.values()))
    per_problem = {arm: [float(np.mean([v for c, v in per_case[arm].items() if problem[c] == p])) for p in problems]
                   for arm in scores}
    per_problem['placebo'] = [float(np.mean(v)) for v in zip(*(per_problem[f'placebo{s}'] for s in PLACEBO_SEEDS))]
    macro = {arm: float(np.mean(v)) for arm, v in per_problem.items()}
    top3 = {arm: sum(any(y[i] for i in sorted(ix, key=lambda i: -s[i])[:3]) for ix in evaluable.values())
            for arm, s in scores.items()}

    def vs(a, b):
        w = sum(x > z + 1e-9 for x, z in zip(per_problem[a], per_problem[b]))
        l = sum(z > x + 1e-9 for x, z in zip(per_problem[a], per_problem[b]))
        return dict(first=a, second=b, macro_diff=macro[a] - macro[b], wins=w, losses=l, p_two_sided=sign(w, l))

    baselines = ('verbal', 'intrinsic', 'surface')
    best_d = max(baselines, key=macro.get)
    comps = [vs('cbm', 'direct'), vs('cbm', 'placebo'), vs('cbm', best_d), vs('direct', best_d)]

    def beats_d(arm):  # one predicate for GO and SIGNAL ONLY (amendment 1)
        c = vs(arm, best_d)
        return all(macro[arm] > macro[d] for d in baselines) and c['wins'] > c['losses']

    go = (macro['cbm'] >= 0.60 and beats_d('cbm') and macro['cbm'] >= macro['direct'] - 0.02
          and comps[1]['macro_diff'] >= 0.02 and comps[1]['wins'] > comps[1]['losses'])
    signal = any(macro[a] >= 0.60 and beats_d(a) for a in ('direct', 'cbm'))
    decision = 'GO' if go else 'SIGNAL ONLY' if signal else 'NO-GO'
    # mechanism: does the concept head name the tool-computed concept of VibePass wrong outputs?
    pc = models['cbm'].concepts(x)
    wrong_ix = [i for i in range(len(rows)) if y[i] and rows[i]['concept']]
    concept_acc = dict(n=len(wrong_ix), top1=sum(CONCEPTS[int(np.argmax(pc[i]))] == rows[i]['concept'] for i in wrong_ix),
                       true_distribution={k: sum(rows[i]['concept'] == k for i in wrong_ix) for k in CONCEPTS})
    result = dict(decision=decision, evaluable_cases=len(evaluable), problems=len(problems), macro_auc=macro,
                  pooled_auc={a: float(roc_auc_score(y, s)) for a, s in scores.items()}, top3_hit_cases=top3,
                  best_d=best_d, comparisons=comps, per_case_auc=per_case, concept_accuracy_on_wrong=concept_acc)
    (HERE / 'results.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({k: result[k] for k in ('decision', 'macro_auc', 'comparisons', 'top3_hit_cases')}, indent=1))


if __name__ == '__main__':
    fit() if sys.argv[1] == 'fit' else score()
