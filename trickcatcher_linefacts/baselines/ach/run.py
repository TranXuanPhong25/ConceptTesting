"""ACH (Foster, Harman et al., FSE 2025 industry) reimplemented from the paper for the TrickCatcher setting.

    python -m trickcatcher_linefacts.baselines.ach.run --tasks <bundle json> --out <dir> --k 3 [--online | --fake]

Per sample: repeat [Make a fault -> builds? -> passes the existing tests? -> not syntactically identical
(comments stripped)? -> LLM equivalence detector says 'no' -> Make a test to catch the fault -> keep the test
cases that build, run on the PUT and kill the mutant] while the per-sample LLM-call budget allows a full
cycle (3 calls). All model-written code runs in `unshare -rn` sandboxes with timeouts.
Offline cache replay is the default; --online enables the v7 Qwen client; --fake uses a scripted client.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import mutants, prompts, tc

ARM = 'ach'
VERSION = 'ach-reimpl-v1'
SEED_OFFSET = 1_500_000_000
HERE = Path(__file__).resolve().parent
CYCLE = 3   # LLM calls of one full mutant cycle: fault, equivalence, test


def sandbox(job, directory, python, timeout):
    """Run sandbox_worker.py in a user+network namespace with a minimal environment (no credentials)."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / 'job.json', directory / 'result.json'
    tc.atomic_json(jp, job)
    op.unlink(missing_ok=True)
    env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'HOME': str(directory)}
    cmd = ['timeout', '-k', '5', str(int(timeout)), 'unshare', '-rn', str(python), '-I', '-B',
           str(HERE / 'sandbox_worker.py'), str(jp), str(op)]
    proc = subprocess.run(cmd, cwd=directory, env=env, capture_output=True, text=True)
    if proc.returncode or not op.exists():
        return None, f'sandbox failed (exit {proc.returncode}): {proc.stderr[-500:]}'
    return json.loads(op.read_text()), None


def keep(result, mode):
    """Test filter (paper Figure 1, TestGen-LLM part), per assertion = per test case.
    paper: passes on the PUT in every repetition and does not pass on the mutant.
    run  : runs on the PUT (consistently, every call returns) and the PUT and the mutant return different
           results for its inputs (the input kills the mutant regardless of the written expected value)."""
    outs = result['put_outcomes']
    consistent = len(set(outs)) == 1
    if mode == 'paper':
        return consistent and outs[0] == 'pass' and result['mutant_outcome'] != 'pass'
    return consistent and outs[0] in ('pass', 'fail') and result['put_calls_ok'] and result['outputs_differ']


def sample(task, k_index, client, directory, args, run_id):
    directory = Path(directory)
    session = tc.Session(client, directory, args.llm_budget)
    base = tc.base_assertions(task)
    original_nf = mutants.normal_form(task['put'])
    seen_nf, groups, records, attempt = {original_nf}, [], [], 0
    while attempt < args.mutants and session.remaining >= CYCLE:
        attempt += 1
        rec = dict(attempt=attempt)
        records.append(rec)
        text = session.query(prompts.make_fault(task), tc.seed(SEED_OFFSET, task['task'], k_index, 0, attempt),
                             f'fault{attempt}', temperature=0.7, top_p=0.95, max_tokens=args.max_tokens)
        try:
            mutant = mutants.assemble(task['put'], tc.code_block(text), task['entry'])
        except (SyntaxError, ValueError) as exc:
            rec.update(status='does-not-build', error=f'{type(exc).__name__}: {exc}'); continue
        rec['mutant'] = mutant
        (directory / f'mutant{attempt}.py').write_text(mutant)
        built, error = sandbox(dict(mode='mutant', entry=task['entry'], put=task['put'], mutant=mutant,
                                    base=task['base'], timeout=args.call_timeout),
                               directory / f'mutant{attempt}_build', args.python, args.sandbox_timeout)
        if built is None:
            rec.update(status='does-not-build', error=error); continue
        rec['build'] = built
        if not built['mutant']['builds']:
            rec.update(status='does-not-build'); continue
        if not built['mutant']['passes']:
            rec.update(status='killed-by-existing-tests'); continue
        nf = mutants.normal_form(mutants.strip_comments(mutant))
        if nf in seen_nf:
            rec.update(status='syntactically-identical' if nf == original_nf else 'duplicate'); continue
        seen_nf.add(nf)
        answer = session.query(prompts.equivalence(mutants.strip_comments(task['put']), mutants.strip_comments(mutant)),
                               tc.seed(SEED_OFFSET, task['task'], k_index, 1, attempt), f'equivalence{attempt}',
                               temperature=0.0, top_p=1.0, max_tokens=512)
        verdict = mutants.judge(answer)
        rec['equivalence'] = verdict
        if verdict != 'non-equivalent':
            rec.update(status=verdict); continue
        text = session.query(prompts.make_test(task, mutant), tc.seed(SEED_OFFSET, task['task'], k_index, 2, attempt),
                             f'test{attempt}', temperature=0.7, top_p=0.95, max_tokens=args.max_tokens)
        try:
            found, rejected = tc.flatten(tc.code_block(text), task['entry'], task['put'], helpers=tc.base_helpers(task))
        except SyntaxError as exc:
            rec.update(status='tests-do-not-build', error=str(exc)); continue
        candidates = [a for a in found if a not in base]
        rec.update(rejected=rejected, base_copies=len(found) - len(candidates), candidates=candidates)
        if not candidates:
            rec.update(status='no-new-tests'); continue
        checked, error = sandbox(dict(mode='tests', entry=task['entry'], put=task['put'], mutant=mutant,
                                      assertions=candidates, repeats=args.repeats, timeout=args.call_timeout),
                                 directory / f'tests{attempt}', args.python,
                                 min(1800, 30 + len(candidates) * (args.repeats + 3) * args.call_timeout))
        if checked is None:
            rec.update(status='test-run-failed', error=error); continue
        kept = [r['source'] for r in checked if keep(r, args.filter)]
        rec.update(checks=checked, kept=kept, status='killed' if kept else 'not-killed')
        groups.append(kept)
    final = tc.round_robin(groups, args.max_tests)
    statuses = [r['status'] for r in records]
    result = tc.row(task, ARM, k_index, run_id, client.model, final, session.calls, baseline=VERSION,
                    filter=args.filter, mutant_attempts=records, mutant_statuses=statuses,
                    n_mutants_killed=statuses.count('killed'),
                    n_assertions_uncapped=len({a for g in groups for a in g}))
    tc.atomic_json(directory / 'result.json', result)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--tasks', type=Path, required=True, help='task bundle (e.g. out/pipelines/v7/humaneval/tasks_hybrid.json)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--k', type=int, default=3)
    p.add_argument('--task-ids', nargs='+')
    p.add_argument('--llm-budget', type=int, default=6, help='LLM calls per sample (a cycle needs 3)')
    p.add_argument('--mutants', type=int, default=3, help='max Make-a-fault attempts per sample')
    p.add_argument('--max-tests', type=int, default=10, help='assertions kept per sample')
    p.add_argument('--max-tokens', type=int, default=2048)
    p.add_argument('--filter', choices=('run', 'paper'), default='run',
                   help="run: test runs on the PUT and its input separates PUT/mutant; paper: passes on PUT, fails on mutant")
    p.add_argument('--repeats', type=int, default=5, help='runs on the PUT (flakiness check, TestGen-LLM)')
    p.add_argument('--call-timeout', type=float, default=5.0)
    p.add_argument('--sandbox-timeout', type=int, default=120)
    p.add_argument('--python', type=Path, default=Path(sys.executable))
    p.add_argument('--workers', type=int, default=4)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--online', action='store_true', help='call the Qwen endpoint through the v7 cached client')
    mode.add_argument('--fake', action='store_true', help='scripted local client (dry run)')
    args = p.parse_args(argv)
    if not 1 <= args.k < 1000 or args.llm_budget < CYCLE or args.mutants < 1 or args.max_tests < 1 or args.repeats < 1:
        p.error(f'need K in 1..999, --llm-budget >= {CYCLE} and positive limits')
    meta, tasks = tc.load_tasks(args.tasks, args.task_ids)
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    from .fake_client import FakeClient
    client = tc.make_client(out, online=args.online, fake=args.fake, workers=args.workers, fake_factory=FakeClient)
    manifest = dict(version=VERSION, arm=ARM, model=client.model, k=args.k, llm_budget=args.llm_budget,
                    mutants=args.mutants, max_tests=args.max_tests, max_tokens=args.max_tokens, filter=args.filter,
                    repeats=args.repeats, call_timeout=args.call_timeout, seed_offset=SEED_OFFSET,
                    arms_seed=tc.ARMS_SEED, tasks_sha256=tc.digest(tasks), sources=tc.source_hashes(HERE),
                    note='reimplementation from the paper, no official code')
    tc.immutable(out / 'manifest.json', manifest)
    tc.immutable(out / 'tasks.json', dict(meta, tasks=tasks))
    run_id = tc.digest(manifest)

    def one(task, k_index):
        directory = out / 'artifacts' / str(task['task']) / str(k_index)
        saved = directory / 'result.json'
        if saved.exists():
            result = json.loads(saved.read_text())
            if result['run_id'] == run_id:
                return result
        return sample(tc.visible(task) | {'facts_version': task.get('facts_version')}, k_index, client, directory, args, run_id)

    try:
        rows = tc.run_all(tasks, args.k, args.workers, one)
    except RuntimeError as exc:
        if type(exc).__name__ != 'CacheMiss':
            raise
        p.exit(2, f'{exc}\nOffline replay is the default; use --online to query the endpoint (or --fake).\n')
    path = tc.write_rows(out, rows)
    print(f'{ARM}: {len(rows)} rows, {sum(r["llm_calls"] for r in rows)} LLM calls, '
          f'{sum(r["n_assertions"] for r in rows)} assertions -> {path}')
    return rows


if __name__ == '__main__':
    sys.exit(0 if main() is not None else 1)
