"""Archive completed native B4 results; require the full frozen cohort."""
import collections
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pipelines/v13_hyp/out/humaneval'


def main():
    generation = OUT / 'generation'
    tasks = json.loads((generation / 'tasks.json').read_text())['tasks']
    manifest = json.loads((generation / 'manifest.json').read_text())
    metrics_path = OUT / 'oracle/ref_metrics.json'
    metrics = json.loads(metrics_path.read_text())
    expected = {(t['task'], s, a) for t in tasks for s in range(manifest['k']) for a in manifest['arms']}
    costs = collections.defaultdict(lambda: dict(samples=0, llm_calls=0, n_in=0, n_out=0, n_inputs=0))
    keys = set()
    rows = 0
    for line in (generation / 'gen.jsonl').open():
        row = json.loads(line)
        rows += 1
        keys.add((row['task'], row['sample'], row['arm']))
        c = costs[row['split'], row['arm']]
        c['samples'] += 1
        for key in ('llm_calls', 'n_in', 'n_out', 'n_inputs'):
            c[key] += row[key]
    assert rows == len(expected) and keys == expected, 'Incomplete B4 generation cohort'
    assert sum(1 for _ in (generation / 'eval.jsonl').open()) == rows, 'Incomplete evaluation'
    assert all((OUT / 'oracle/exec' / f"{t['task']}.json").exists() for t in tasks), 'Missing execution'
    result = copy.deepcopy(metrics)
    for cohort in result['cohorts'].values():
        for pair in cohort['comparisons']:
            pair.pop('budgets', None)
    result.update(version='v13_hyp', generation_rows=rows, completed_execution_tasks=len(tasks),
                  costs={split: {arm: c for (s, arm), c in costs.items() if s == split}
                         for split in metrics['cohorts']},
                  provenance={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (metrics_path, generation / 'manifest.json', generation / 'tasks.json',
                                        generation / 'gen.jsonl', generation / 'eval.jsonl')})
    attribution_path = OUT / 'oracle/hyp_attribution.json'
    if attribution_path.exists():
        result['native_attribution_all_133_tasks'] = json.loads(attribution_path.read_text())
        result['provenance'][str(attribution_path.relative_to(ROOT))] = hashlib.sha256(attribution_path.read_bytes()).hexdigest()
    retry_path = ROOT / 'out/runlogs_resume_b3_b4/b4_task44_retry.json'
    if retry_path.exists():
        result['task44_retry'] = json.loads(retry_path.read_text())
    result['mechanism'] = {}
    for split in metrics['cohorts']:
        group = [t for t in tasks if t['split'] == split]
        cards = [h for t in group for h in t['hypothesis_meta']['shown']]
        result['mechanism'][split] = dict(tasks=len(group), tasks_with_shown=sum(bool(t['hypothesis_meta']['shown']) for t in group),
            shown=len(cards), witnessed=sum(bool(h.get('witnessed')) for h in cards),
            mutant_difference=sum(bool(h.get('mutant_diff')) for h in cards),
            proposal_calls=sum(t['hypothesis_meta']['proposal_calls'] for t in group))
    lines = ['# B4 v13_hyp completed comparison', '',
             'Frozen 133-task cohort: 113 dev + 20 pilot, seven exported arms, K=3; common spec-only ref oracle.',
             f'{rows:,} generation/evaluation rows; all {len(tasks)} execution records present.',
             'One task-level hypothesis proposal is shared across K/arms and accounted separately.', '']
    for split, cohort in result['cohorts'].items():
        mechanism = result['mechanism'][split]
        lines += [f'## {split}', '',
                  f"{mechanism['shown']} shown hypotheses on {mechanism['tasks_with_shown']}/{mechanism['tasks']} tasks; "
                  f"{mechanism['witnessed']} witnessed; {mechanism['mutant_difference']} with surviving-mutant differences.", '',
                  '| Arm | D_IO tasks/run | Precision | False alarms | Generation calls/sample |',
                  '|---|---:|---:|---:|---:|']
        for arm, m in cohort['arms'].items():
            c = result['costs'][split][arm]
            precision = 'n/a' if m['precision'] is None else f"{m['precision']:.3f}"
            lines.append(f"| {arm} | {m['D_IO_samples']/cohort['k']:.2f} | {precision} | "
                         f"{m['false_alarms']} | {c['llm_calls']/c['samples']:.2f} |")
        lines += ['', '| Hypothesis contrast | Matched inputs | Wins/losses | Nominal p | Detection tasks/run |',
                  '|---|---|---:|---:|---:|']
        for q in cohort['comparisons']:
            if q['first'] not in ('hyp-hybrid', 'hyp-witness-only'):
                continue
            scores = '/'.join(f"{v/cohort['k']:.2f}" for v in q['detecting_samples'])
            lines.append(f"| {q['first']} vs {q['second']} | {q['matched']} | "
                         f"{q['wins']}/{q['losses']} | {q['sign_p']:.4f} | {scores} |")
        lines += ['']
    lines += ['## Finding', '',
              'On dev, hyp-hybrid detects 46.33 tasks/run vs flat-hybrid 62.67 and toolinput 63.00.',
              'Primary raw paired wins/losses are 14/43 (p=.000154) and 14/35 (p=.003802).',
              'Equal-input random-subset comparisons also favor flat and toolinput.',
              'This registered hypothesis pipeline does not meet its promotion gate.', '',
              'Generation calls/sample differ: hyp-hybrid 1.83 vs flat-hybrid 3.27. Matching input',
              'counts does not match LLM requests. The result compares complete methods and does not',
              'isolate hypothesis wording alone; proposal coverage and witness-pool quality also differ.', '',
              '## Scope and limits', '',
              'Primary registered contrasts are hyp-hybrid vs flat-hybrid and vs toolinput; pilot stays separate.',
              'P-values are nominal across several exploratory contrasts. No held-out promotion follows automatically.',
              'The frozen seven-arm B4 manifest does not export placebo; hypothesis and original witness controls are present.',
              'Hint budgets use whitespace/punctuation proxy normalization, not equal actual tokenizer counts.',
              'A hypothesis witness or mutant difference is not proof of a specification violation.',
              'Task-44 missing execution was retried with the exact original saved worker/job/timers; other results retained.',
              'Raw assertions with witness-only None are placeholders; report uses ref-replaced outcomes.', '']
    stem = ROOT / 'analysis/b4_v13_hyp_results'
    stem.with_suffix('.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    stem.with_suffix('.md').write_text('\n'.join(lines))
    for split, cohort in metrics['cohorts'].items():
        print(split, {a: round(m['D_IO_samples']/cohort['k'], 3) for a, m in cohort['arms'].items()})
        for q in cohort['comparisons']:
            if q['first'] == 'hyp-hybrid':
                print({k: v for k, v in q.items() if k != 'budgets'})


if __name__ == '__main__':
    main()
