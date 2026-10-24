"""Read saved reference caches for the v53/v49 decisive universe; no execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = REPO / 'trickcatcher_linefacts/out/analysis'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, hashes):
    hashes[str(path.relative_to(REPO))] = sha(path)
    return json.loads(path.read_text())


def unresolved(value):
    if not value or value[0] not in ('ok', 'exception'):
        return True
    return value[0] == 'exception' and (
        str(value[1]).startswith('load:') or value[1] in ('MemoryError', 'RecursionError'))


def main():
    hashes, tasks = {}, {}
    problems = read(OUT / 'v53_validity_smallscope/problems.json', hashes)
    for cid in sorted({cid for cids in problems.values() for cid in cids}, key=int):
        record = read(OUT / 'v49_defn_oracle/tasks' / f'{cid}.json', hashes)
        wanted = set(record['inputs'])
        values, conflicts = {}, set()
        directories = [OUT / 'v41_iorel/cases' / cid / 'ref']
        refs = OUT / 'v49_defn_oracle/references' / cid
        # Bounded to the generated-reference directories named by original scorer.
        directories += [p for p in sorted(refs.glob('generated*')) if p.is_dir()]
        for directory in directories:
            jp, rp = directory / 'job.json', directory / 'result.json'
            if not jp.exists() or not rp.exists():
                continue
            job, result = read(jp, hashes), read(rp, hashes)
            if len(job['inputs']) != len(result['contract']) or len(job['inputs']) != len(result['ref']):
                raise ValueError(f'cache lengths differ: {directory}')
            for lit, contract, ref in zip(job['inputs'], result['contract'], result['ref']):
                if lit not in wanted:
                    continue
                pair = [contract, ref]
                if lit in values and values[lit] != pair:
                    conflicts.add(lit)
                values[lit] = pair
        missing = wanted - values.keys()
        bad_contract = [lit for lit, (contract, ref) in values.items() if unresolved(contract)]
        bad_valid_ref = [lit for lit, (contract, ref) in values.items()
                         if contract[0] == 'ok' and unresolved(ref)]
        tasks[cid] = dict(
            inputs=len(wanted), cached=len(values), missing=len(missing), conflicting=len(conflicts),
            contract_status=dict(Counter(v[0][0] for v in values.values())),
            contract_exceptions=dict(Counter(str(v[0][1]) for v in values.values() if v[0][0] == 'exception')),
            valid_ref_status=dict(Counter(v[1][0] for v in values.values() if v[0][0] == 'ok')),
            unresolved_contract=len(bad_contract), unresolved_valid_ref=len(bad_valid_ref),
        )
    totals = {k: sum(t[k] for t in tasks.values()) for k in
              ('inputs', 'cached', 'missing', 'conflicting', 'unresolved_contract', 'unresolved_valid_ref')}
    result = dict(scope='saved reference cache integrity only; no program execution', tasks=tasks,
                  totals=totals, source_sha256=hashes,
                  ready=not any(totals[k] for k in ('missing', 'conflicting', 'unresolved_contract', 'unresolved_valid_ref')))
    target = HERE / 'REFERENCE_INTEGRITY.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(ready=result['ready'], totals=totals), indent=2))


if __name__ == '__main__':
    main()
