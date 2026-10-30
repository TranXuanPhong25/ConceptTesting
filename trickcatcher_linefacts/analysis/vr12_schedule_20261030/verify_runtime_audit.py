"""Audit saved scores under both Python runtimes; never execute task code."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker():
    from trickcatcher_linefacts.pipelines.vr12_expanded import diagnostic as d, oracle_b01 as ob
    d.verify()
    tasks = {r['task']['task']: r['task'] for r in load(d.HERE / 'assets/prepared.json')}
    saved = {int(p.stem): load(p) for p in (d.ROOT / 'scored').glob('*.json')}
    original = load(d.ROOT / 'RESULTS.json')['results']
    summary, missing = {}, []
    for oracle in ('ref', 'o0'):
        summary[oracle] = {}
        for mode in (*d.MODES, *(m + '_round1' for m in d.MODES)):
            bugs, alarms, abstained = set(), set(), 0
            for n, pack in saved.items():
                for row in pack['rows']:
                    if row['arm'] != mode:
                        continue
                    seen = set()
                    for assertion in row['asserts']:
                        call = ob.call_of(assertion['src'], tasks[n]['entry'])
                        if call is None or oracle == 'ref' and call in seen:
                            continue
                        seen.add(call)
                        calls = pack['execution']['calls']
                        if call not in calls:
                            missing.append(dict(oracle=oracle, arm=mode, task=n,
                                assertion_sha256=hashlib.sha256(assertion['src'].encode()).hexdigest(),
                                parsed_call=call))
                        rec = calls.get(call, {})
                        emit, correct, passes = ob.decide(oracle, rec, None,
                            ob.expected_of(assertion['src']), assertion)
                        abstained += not emit
                        if emit and not passes:
                            (bugs if rec.get('valid', False) and correct else alarms).add(n)
            summary[oracle][mode] = dict(tasks=len(tasks), confirmed_tasks=sorted(bugs),
                                        false_alarm_tasks=sorted(alarms), abstained_calls=abstained)
    differences = {o: {m: dict(recomputed=r, original=original[o]['arms'][m])
        for m, r in arms.items() if r != original[o]['arms'][m]}
        for o, arms in summary.items()}
    print(json.dumps(dict(python=sys.version, unicode=unicodedata.unidata_version,
                          results=summary, differences=differences, missing_call_keys=missing)))


def main():
    pinned = REPO / 'trickcatcher_linefacts/handoffs/v85_20261029/.venv/bin/python'
    runtimes = {}
    for name, python in [('pinned', str(pinned)), ('system', '/usr/bin/python3')]:
        result = subprocess.run([python, str(Path(__file__).resolve()), '--worker'],
            cwd=REPO, text=True, capture_output=True, check=True)
        runtimes[name] = json.loads(result.stdout)
    from trickcatcher_linefacts.pipelines.vr12_expanded import diagnostic as d
    generation = load(d.ROOT / 'GENERATION_FREEZE.json')
    generation_mismatches = [name for name, digest in generation['files'].items()
                             if sha(d.ROOT / name) != digest]
    ledger = d.ledger()
    received = [load(p) for p in (d.ROOT / 'transport/calls').glob('*/response.json')]
    assert len(ledger) == len(received) == 39
    assert {r['key'] for r in ledger} == {r['key'] for r in received}
    assert all(r['status'] == 'received' for r in received)
    lock_free = False
    with (d.ROOT / 'RUN.lock').open('r') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_free = True
        except BlockingIOError:
            pass
    active = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if b'trickcatcher_linefacts.pipelines.vr12_expanded.diagnostic' in args and b'run' in args:
            active.append(int(proc.name))
    original_audit = load(HERE / 'AUDIT_CHECKS.json')
    system_matches_old_audit = runtimes['system']['results'] == original_audit['score_recomputed']
    pinned_matches_original = all(not x for x in runtimes['pinned']['differences'].values())
    result = dict(runtimes=runtimes, pinned_matches_original_RESULTS=pinned_matches_original,
                  system_matches_prior_audit=system_matches_old_audit,
                  generation_files=len(generation['files']), generation_mismatches=generation_mismatches,
                  completion_attempts=len(ledger), received=len(received), run_lock_free=lock_free,
                  active_controllers=active, complete=load(d.ROOT / 'COMPLETE.json'),
                  audit_script_sha256=sha(Path(__file__)),
                  artifact_sha256={str(p.relative_to(REPO)): sha(p) for p in
                    [d.ROOT / 'RESULTS.json', d.ROOT / 'GENERATION_FREEZE.json',
                     HERE / 'AUDIT_CHECKS.json', HERE / 'AUDIT_RESULT.md']},
                  no_task_or_reference_execution=True, no_network_calls=True)
    with (HERE / 'RUNTIME_AUDIT.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=True, indent=2)
        handle.write('\n')
    print(json.dumps(dict(pinned_matches_original=pinned_matches_original,
                         system_matches_prior_audit=system_matches_old_audit,
                         versions={k: (v['python'], v['unicode']) for k, v in runtimes.items()},
                         missing_keys={k: len(v['missing_call_keys']) for k, v in runtimes.items()},
                         generation_mismatches=generation_mismatches, active_controllers=active)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    worker() if args.worker else main()
