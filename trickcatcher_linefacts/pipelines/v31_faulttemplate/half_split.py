"""MVP half of VibePass (33/66 PUTs), stratified by question and difficulty; seeded hash order, outcome-blind.

Every question keeps floor(n/2) PUTs (seeded hash order); the remaining PUTs come from odd-sized questions, questions
with no PUT yet first, so every question stays represented; difficulty ratio is reported against the population.
Run once to write vibepass_half.json (frozen, hashed into protocol.json):
  python3 -m trickcatcher_linefacts.pipelines.v31_faulttemplate.half_split
"""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = '20261019'


def h(*parts):
    return hashlib.sha256('/'.join([SEED, *map(str, parts)]).encode()).hexdigest()


def split(manifest, heldout):
    puts = [p for p in manifest['puts'] if p['task'] in set(heldout)]
    byq = collections.defaultdict(list)
    for p in puts:
        byq[p['question_id']].append(p)
    chosen, odd = [], collections.defaultdict(list)
    for q, rows in sorted(byq.items()):
        rows = sorted(rows, key=lambda p: h('put', p['task']))
        chosen += rows[:len(rows) // 2]
        if len(rows) % 2:
            odd[rows[0]['difficulty']].append((q, rows[len(rows) // 2]))
    need = len(puts) // 2 - len(chosen)
    # Extras: questions with no PUT yet first (keeps every question), then seeded hash order.
    represented = {p['question_id'] for p in chosen}
    pool = sorted((qp for v in odd.values() for qp in v), key=lambda qp: (qp[0] in represented, h('question', qp[0])))
    chosen += [p for _, p in pool[:need]]
    return sorted(p['task'] for p in chosen)


def main():
    from .paths import CONFIG, REPO
    root = REPO / CONFIG['vibepass']['root']
    manifest = json.loads((root / 'manifest.json').read_text())
    heldout = json.loads((root / 'tasks.json').read_text())['heldout']
    tasks = split(manifest, heldout)
    meta = {p['task']: p for p in manifest['puts']}
    out = dict(seed=SEED, rule=__doc__.split('\n')[0], tasks=tasks, n=len(tasks),
               difficulty=dict(collections.Counter(meta[t]['difficulty'] for t in tasks)),
               questions=len({meta[t]['question_id'] for t in tasks}),
               population=dict(n=len(heldout), difficulty=dict(collections.Counter(meta[t]['difficulty'] for t in heldout)),
                               questions=len({meta[t]['question_id'] for t in heldout})))
    path = HERE / 'vibepass_half.json'
    if path.exists() and json.loads(path.read_text()) != out:
        raise SystemExit('vibepass_half.json differs')
    path.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'tasks'}))


if __name__ == '__main__':
    main()
