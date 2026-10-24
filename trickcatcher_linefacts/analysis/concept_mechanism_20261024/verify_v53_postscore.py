"""Independent v53 arithmetic and checker-cache review; no program execution."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = REPO / 'trickcatcher_linefacts/out/analysis'
RUN = OUT / 'v53_validity_smallscope'
ARMS = ('concept', 'lines', 'open')


def ordered(inputs):
    return sorted(set(inputs), key=lambda lit: (hashlib.sha256(lit.encode()).hexdigest(), lit))


def main():
    hashes = {}

    def read(path):
        hashes[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())

    score = read(RUN / 'score.json')
    protocol = read(HERE / 'V53_PROTOCOL_INVENTORY.json')
    # Independently sum every registered scalar metric from per-task records.
    totals = {}
    for arm in (*ARMS, 'tool'):
        t = Counter()
        for row in score['tasks'].values():
            a = row['arms'][arm]
            for key in ('invalid', 'valid', 'exposing'):
                t[key] += row[key]
            for key in ('invalid_caught', 'valid_rejected', 'exposing_rejected'):
                t[key] += a[key]
            for oracle, values in a['oracles'].items():
                for key, value in values.items():
                    t[f'{oracle}_{key}'] += int(value)
        totals[arm] = dict(t)
        totals[arm]['recall'] = t['invalid_caught'] / t['invalid'] if t['invalid'] else None
        totals[arm]['valid_rejected_rate'] = t['valid_rejected'] / t['valid'] if t['valid'] else None
        assert totals[arm] == score['totals'][arm], f'aggregate mismatch: {arm}'

    def safety(arm, ref):
        a, r = totals[arm], totals[ref]
        checks = dict(valid_rejected_le_1pct=(a['valid_rejected_rate'] or 0) <= .01,
                      exposing_le_ref=a['exposing_rejected'] <= r['exposing_rejected'])
        for oracle in ('qwen_defn', 'sonnet_defn'):
            checks[f'{oracle}_no_task_lost'] = a.get(f'{oracle}_task_lost', 0) == 0
            checks[f'{oracle}_lost_le_ref'] = a.get(f'{oracle}_confirmed_lost', 0) <= r.get(f'{oracle}_confirmed_lost', 0)
        return checks

    margin = (totals['concept']['recall'] or 0) - (totals['open']['recall'] or 0)
    checks = dict(recall=(totals['concept']['recall'] or 0) >= (totals['open']['recall'] or 0) + .10,
                  **safety('concept', 'open'))
    primary = dict(recall_margin=margin, checks=checks,
                   verdict='promising' if all(checks.values()) else 'not promising')
    taxonomy = dict(recall_margin=(totals['concept']['recall'] or 0) - (totals['lines']['recall'] or 0),
                    report_only=True, safety=safety('concept', 'lines'))
    assert dict(primary=primary, taxonomy_vs_lines=taxonomy) == score['decision'], 'gate mismatch'

    cache_stats = {arm: Counter() for arm in ARMS}
    masks, tasks = {}, {}
    for cid, row in score['tasks'].items():
        rec = read(OUT / 'v49_defn_oracle/tasks' / f'{cid}.json')
        inputs = ordered(rec['inputs'])
        # Rebuild hidden contract statuses from the already verified cache mapping.
        truth = {}
        dirs = [OUT / 'v41_iorel/cases' / cid / 'ref']
        dirs += sorted((OUT / 'v49_defn_oracle/references' / cid).glob('generated*'))
        for directory in dirs:
            job, result = read(directory / 'job.json'), read(directory / 'result.json')
            truth.update({lit: value[0] == 'ok' for lit, value in zip(job['inputs'], result['contract']) if lit in rec['inputs']})
        assert set(truth) == set(inputs), f'incomplete truth: {cid}'
        by_arm = {}
        for arm in ARMS:
            key = f"{row['problem']}_{arm}"
            answer = (RUN / 'answers' / (key + '.txt')).read_text()
            code = re.search(r'```(?:python|py)?\s*\n(.*?)```', answer, re.S).group(1).strip()
            tree = ast.parse(code)
            names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and re.fullmatch(r'check_\d+', n.name)]
            assert len(names) == row['arms'][arm]['checks']
            mask = {lit: True for lit in inputs}
            kept = 0
            for index, name in enumerate(names):
                program, source = f'p{index}', None

                def cached(tag, order):
                    nonlocal source
                    values = []
                    for offset in range(0, len(order), 200):
                        directory = RUN / 'exec' / cid / ('chk_' + arm) / tag / program / f'c{offset}'
                        job, result = read(directory / 'job.json'), read(directory / 'result.json')
                        assert job['inputs'] == order[offset:offset + 200], f'checker cache input mismatch: {directory}'
                        assert job['order'] == [program] and len(result[program]) == len(job['inputs'])
                        if source is None:
                            source = job['sources'][program]
                            assert code in source, f'checker source differs from answer: {directory}'
                            assert f'r = {name}(*a, **k)' in source
                        else:
                            assert source == job['sources'][program], f'checker source differs by chunk: {directory}'
                        values += result[program]
                    return values

                base = cached('base', rec['base_inputs'])
                values = cached('inputs', inputs)
                accepted = lambda outcome: bool(outcome) and outcome[0] == 'ok' and outcome[1] == 'True'
                dropped = not all(map(accepted, base))
                stats = cache_stats[arm]
                stats['check_instances'] += 1
                stats['dropped_public'] += dropped
                stats['raised_public'] += sum(bool(v) and v[0] != 'ok' for v in base)
                if not dropped:
                    kept += 1
                    rejected = sum(not accepted(v) for v in values)
                    stats['kept'] += 1
                    stats['zero_rejection_checks'] += rejected == 0
                    stats['raised_universe'] += sum(bool(v) and v[0] != 'ok' for v in values)
                    for lit, outcome in zip(inputs, values):
                        mask[lit] &= accepted(outcome)
            assert kept == row['arms'][arm]['kept']
            assert sum(not mask[l] for l in inputs if not truth[l]) == row['arms'][arm]['invalid_caught']
            assert sum(not mask[l] for l in inputs if truth[l]) == row['arms'][arm]['valid_rejected']
            by_arm[arm] = mask
        assert all(by_arm[ARMS[0]] == by_arm[arm] for arm in ARMS[1:]), f'acceptance masks differ: {cid}'
        assert by_arm[ARMS[0]] == truth, f'acceptance differs from contract on universe: {cid}'
        masks[cid] = hashlib.sha256(json.dumps(by_arm[ARMS[0]], sort_keys=True).encode()).hexdigest()
        tasks[cid] = dict(inputs=len(inputs), invalid=row['invalid'], valid=row['valid'],
                          identical_three_arm_masks=True, matches_hidden_contract=True)
    result = dict(scope='independent arithmetic and cached checker output replay; no program execution',
                  primary=primary, taxonomy=taxonomy, totals=totals, tasks=tasks,
                  mask_sha256=masks, per_check_cache_statistics={a: dict(c) for a, c in cache_stats.items()},
                  tasks_with_invalid=sum(r['invalid'] > 0 for r in tasks.values()),
                  tasks_without_invalid=sum(r['invalid'] == 0 for r in tasks.values()),
                  cache_sha256=hashes, score_source_sha256=protocol['source_sha256'])
    path = HERE / 'V53_POSTSCORE_VERIFICATION.json'
    with path.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['primary', 'per_check_cache_statistics', 'tasks_with_invalid', 'tasks_without_invalid']}, indent=2))


if __name__ == '__main__':
    main()
