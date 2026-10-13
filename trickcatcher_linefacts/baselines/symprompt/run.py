"""SymPrompt (Ryan et al., FSE 2024) reimplemented from the paper for the TrickCatcher setting.

    python -m trickcatcher_linefacts.baselines.symprompt.run --tasks <bundle json> --out <dir> --k 3 [--online | --fake]

Offline cache replay is the default (a cache miss stops the run); --online enables the v7 Qwen client;
--fake uses a scripted local client (dry runs). Writes <out>/gen.jsonl in the pipelines/v7 row format,
<out>/tasks.json (the bundle, for v7 evaluate/oracle), <out>/manifest.json and per-sample artifacts.
No generated code is executed here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import pathcollect, prompts, tc

ARM = 'symprompt'
VERSION = 'symprompt-reimpl-v1'
SEED_OFFSET = 1_000_000_000
HERE = Path(__file__).resolve().parent


def plan(task, max_paths):
    """Static part, identical for all K samples: focal method, context, signature, selected paths."""
    fn, cls, wrapper, tree = pathcollect.focal(task['put'], task['entry'])
    every = pathcollect.collect(fn)
    chosen = pathcollect.select(every, max_paths)
    sig = prompts.signature(wrapper or fn, task['entry'])
    return dict(context=prompts.context(task['put'], fn, cls, wrapper, tree), signature=sig,
                focal=f'{cls.name}.{fn.name}' if cls is not None else fn.name,
                n_paths_collected=len(every), paths=[p.as_dict() for p in chosen])


def sample(task, k_index, plan_, client, directory, args, run_id):
    session = tc.Session(client, directory, args.llm_budget)
    base = tc.base_assertions(task)
    previous, groups, per_path = [], [], []
    for i, path in enumerate(plan_['paths'], start=1):
        if session.remaining <= 0:
            break
        msgs = prompts.messages(task, plan_['context'], plan_['signature'], path, i, previous)
        text = session.query(msgs, tc.seed(SEED_OFFSET, task['task'], k_index, 0, i - 1), f'path{i}',
                             temperature=0.7, top_p=0.95, max_tokens=args.max_tokens)
        code, parsed = prompts.parse_repair(tc.code_block(text))
        tests = prompts.test_functions(code) if code else []
        previous.extend(tests)
        found, rejected = tc.flatten(code, task['entry'], task['put'], helpers=tc.base_helpers(task)) if code else ([], [])
        new = [a for a in found if a not in base]
        groups.append(new)
        per_path.append(dict(path=i, parsed=parsed, repaired_code=code, assertions=new,
                             base_copies=len(found) - len(new), rejected=rejected))
    final = tc.round_robin(groups, args.max_tests)
    result = tc.row(task, ARM, k_index, run_id, client.model, final, session.calls, baseline=VERSION,
                    focal=plan_['focal'], n_paths_collected=plan_['n_paths_collected'],
                    n_paths_prompted=len(per_path), paths=plan_['paths'][:len(per_path)], per_path=per_path,
                    n_assertions_uncapped=len({a for g in groups for a in g}))
    tc.atomic_json(Path(directory) / 'result.json', result)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--tasks', type=Path, required=True, help='task bundle (e.g. out/pipelines/v7/humaneval/tasks_hybrid.json)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--k', type=int, default=3)
    p.add_argument('--task-ids', nargs='+')
    p.add_argument('--llm-budget', type=int, default=6, help='LLM calls per sample = max path prompts')
    p.add_argument('--max-paths', type=int, help='paths per task (default: --llm-budget)')
    p.add_argument('--max-tests', type=int, default=10, help='assertions kept per sample')
    p.add_argument('--max-tokens', type=int, default=1024)
    p.add_argument('--workers', type=int, default=4)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--online', action='store_true', help='call the Qwen endpoint through the v7 cached client')
    mode.add_argument('--fake', action='store_true', help='scripted local client (dry run)')
    args = p.parse_args(argv)
    args.max_paths = args.max_paths or args.llm_budget
    if not 1 <= args.k < 1000 or args.llm_budget < 1 or args.max_tests < 1 or args.max_paths < 1:
        p.error('need K in 1..999 and positive budgets')
    meta, tasks = tc.load_tasks(args.tasks, args.task_ids)
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    from .fake_client import FakeClient
    client = tc.make_client(out, online=args.online, fake=args.fake, workers=args.workers, fake_factory=FakeClient)
    plans = {str(t['task']): plan(tc.visible(t), args.max_paths) for t in tasks}
    manifest = dict(version=VERSION, arm=ARM, model=client.model, k=args.k, llm_budget=args.llm_budget,
                    max_paths=args.max_paths, max_tests=args.max_tests, max_tokens=args.max_tokens,
                    seed_offset=SEED_OFFSET, arms_seed=tc.ARMS_SEED, mode='online' if args.online else 'fake' if args.fake else 'offline',
                    tasks_sha256=tc.digest(tasks), plans_sha256=tc.digest(plans), sources=tc.source_hashes(HERE),
                    note='reimplementation from the paper, no official code')
    manifest.pop('mode')   # offline replay and online runs share one run id (same requests)
    tc.immutable(out / 'manifest.json', manifest)
    tc.immutable(out / 'tasks.json', dict(meta, tasks=tasks))
    tc.immutable(out / 'plans.json', plans)
    run_id = tc.digest(manifest)

    def one(task, k_index):
        directory = out / 'artifacts' / str(task['task']) / str(k_index)
        saved = directory / 'result.json'
        if saved.exists():
            result = json.loads(saved.read_text())
            if result['run_id'] == run_id:
                return result
        return sample(tc.visible(task) | {'facts_version': task.get('facts_version')}, k_index,
                      plans[str(task['task'])], client, directory, args, run_id)

    try:
        rows = tc.run_all(tasks, args.k, args.workers, one)
    except RuntimeError as exc:
        if type(exc).__name__ != 'CacheMiss':
            raise
        p.exit(2, f'{exc}\nOffline replay is the default; use --online to query the endpoint (or --fake).\n')
    path = tc.write_rows(out, rows)
    calls = sum(r['llm_calls'] for r in rows)
    print(f'{ARM}: {len(rows)} rows, {calls} LLM calls, {sum(r["n_assertions"] for r in rows)} assertions -> {path}')
    return rows


if __name__ == '__main__':
    sys.exit(0 if main() is not None else 1)
