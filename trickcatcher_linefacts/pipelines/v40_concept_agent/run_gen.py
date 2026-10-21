"""Six-arm Qwen generator experiment; no paid client and no canonical stage-1 use."""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import gen_inputs, gen_prompts, generate, prompts, preconditions
from .llm_client import Client, atomic_json

TASKS = DATA_OUT / 'tasks_v3c_all.json'
FACTS = DATA_OUT / 'facts_v3c'
FACTS_VERSION = "v3c"
DESIGN = {22, 33, 111, 122, 123, 139}
SMOKE = (2, 3, 4)


def bundle_all(output=TASKS):
    he = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, generate.HE.open())}
    pilot = json.loads(generate.TASKS.read_text())["pilot"]
    ids = [int(n) for n in (HERE / "tasks.txt").read_text().split() if int(n) not in DESIGN]
    if len(ids) != 133 or len(set(ids)) != 133:
        raise ValueError("expected 133 unique non-design tasks")
    tasks = []
    for n in ids:
        task = generate.bundle(n, he[n], FACTS)
        facts = json.loads((FACTS / f"{n}.json").read_text())
        task.update(placebo_meta=facts["placebo3"], split="pilot" if n in pilot else "dev", facts_version=FACTS_VERSION)
        tasks.append(task)
    atomic_json(output, dict(facts_version=FACTS_VERSION, pilot=pilot, design_excluded=sorted(DESIGN), tasks=tasks))
    return tasks


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run(tasks, contracts, out_dir, generator_python, *, k=3, workers=16, client=None, facts_version=FACTS_VERSION, job_slots=None,
        arms=gen_prompts.DEFAULT_ARMS):
    if not arms or len(set(arms)) != len(arms) or not set(arms) <= set(gen_prompts.ARMS):
        raise ValueError("expected distinct supported arms")
    arms = tuple(a for a in gen_prompts.ARMS if a in arms)
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    client = client or Client(out_dir / "cache", workers=workers)
    gen_prompts.read_original_templates()
    if any(a.startswith("gen-") for a in arms):
        generator_python = Path(generator_python).absolute()
        if not generator_python.is_file():
            raise ValueError("Set QWEN_GENERATOR_PYTHON or --generator-python to the dedicated cyaron venv interpreter")
        if not (generator_python.parent.parent / "pyvenv.cfg").is_file():
            raise ValueError("Generator interpreter must belong to a dedicated cyaron venv")
    source_hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in
                     ("run_gen.py", "gen_inputs.py", "generator_worker.py", "gen_prompts.py", "llm_client.py", "prompts.py", "facts.py", "tracer.py", "preconditions.py", "precond_prompts.py", "fuzz_validity.py")}
    if any(t.get("facts_version", facts_version) != facts_version for t in tasks):
        raise ValueError("task facts version mismatch")
    manifest = dict(version="gen2-v1", facts_version=facts_version, model=client.model, k=k, arms=arms,
                    tasks_sha256=_digest(tasks), contracts_sha256=_digest({t["task"]: contracts[t["task"]] for t in tasks}),
                    source_sha256=source_hashes, templates=gen_prompts.TEMPLATE_SHA256,
                    prereg_sha256=hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest(), n=gen_inputs.N)
    if facts_version == "v3m":
        if any("mined_src" not in contracts[t["task"]] or "contract_src" in contracts[t["task"]] for t in tasks):
            raise ValueError("v3m requires exclusively mined validators")
        hashes = {str(t["task"]): preconditions.sha(contracts[t["task"]]["mined_src"]) for t in tasks}
        if any(t.get("valid_sha256") != hashes[str(t["task"])] for t in tasks):
            raise ValueError("mined validator hash mismatch")
        manifest["valid_sha256"] = hashes
    manifest = json.loads(json.dumps(manifest))
    mp = out_dir / "manifest.json"
    if mp.exists() and json.loads(mp.read_text()) != manifest:
        raise ValueError("Run manifest changed; use a new output directory rather than mixing experiments")
    atomic_json(mp, manifest)
    atomic_json(out_dir / "tasks.json", dict(facts_version=facts_version, tasks=tasks))
    run_id = _digest(manifest)
    gen_path = out_dir / "gen.jsonl"
    done = set()
    if gen_path.exists():
        for line in gen_path.read_text().splitlines():
            row = json.loads(line)
            if row.get("run_id") != run_id:
                raise ValueError("Existing output does not match this run manifest")
            key = row["task"], row["arm"], row["sample"]
            if key in done:
                raise ValueError("Duplicate output key")
            done.add(key)
    jobs = [(t, arm, sample) for sample in range(k) for t in tasks for arm in arms
            if (t["task"], arm, sample) not in done]
    print(f"{len(tasks)} tasks; K={k}; {len(done)} completed; {len(jobs)} pending", flush=True)
    lock = threading.Lock()

    def work(job):
        task, arm, sample = job
        directory = out_dir / "artifacts" / str(task["task"]) / arm / str(sample)
        directory.mkdir(parents=True, exist_ok=True)
        calls, attempts, selected, classified = [], [], [], None

        def query(messages, stage, retry, path):
            response = client.chat(messages, gen_prompts.seed(task["task"], arm, sample, stage, retry))
            atomic_json(path, response)
            calls.append(response)
            return response["text"]

        if arm in ("plain", "concept"):
            text = query(gen_prompts.messages(*prompts.build(arm, task)), 0, 0, directory / "direct_response.json")
        else:
            shown = task["concept_meta"] if arm == "gen-concept" else task["placebo_meta"] if arm == "gen-placebo" else []
            if arm in ("toolinput", "concept-toolinput"):
                classified = gen_inputs.classify(task, contracts[task["task"]], gen_inputs.witness_candidates(task), [], directory)
            else:
                messages = gen_prompts.generator_messages(arm, task)
                for retry in range(2):
                    attempt_dir = directory / f"attempt_{retry}"
                    attempt_dir.mkdir(exist_ok=True)
                    raw = query(messages, 1, retry, attempt_dir / "stage1_response.json")
                    try:
                        code = gen_inputs.extract_generator(raw)
                        (attempt_dir / "generator.py").write_text(code + "\n")
                        generated = gen_inputs.generate_candidates(code, task, generator_python, attempt_dir,
                            gen_prompts.seed(task["task"], arm, sample, 3, retry))
                    except (SyntaxError, ValueError) as exc:
                        generated = dict(attempted=0, returned=0, duplicates=0, rejected=0, candidates=[],
                                         errors=[f"{type(exc).__name__}: could not extract sample_one()"])
                    classified = gen_inputs.classify(task, contracts[task["task"]], generated["candidates"], shown, attempt_dir,
                                                     requested_draws=gen_inputs.N)
                    correction = gen_inputs.feedback(generated, classified, shown)
                    attempt = dict(retry=retry, generated=generated, summary=classified["summary"], feedback=correction)
                    atomic_json(attempt_dir / "summary.json", attempt)
                    attempts.append(attempt)
                    if correction is None or retry == 1:
                        break
                    messages += [{"role": "assistant", "content": raw}, {"role": "user", "content": correction}]
            selected = gen_inputs.select("toolinput" if arm == "concept-toolinput" else arm, classified,
                                         gen_prompts.seed(task["task"], arm, sample, 3, 0))
            atomic_json(directory / "selected.json", selected)
            if arm == "concept-toolinput":
                text = query(gen_prompts.concept_toolinput_messages(task, selected), 0, 0, directory / "direct_response.json")
            else:
                text = query(gen_prompts.oracle_messages(task, selected), 2, 0, directory / "stage2_response.json")
        result = dict(task=task["task"], split=task["split"], arm=arm, sample=sample, model=client.model,
                      text=text, run_id=run_id, facts_version=facts_version, llm_calls=len(calls), n_in=sum(c["n_in"] for c in calls),
                      n_out=sum(c["n_out"] for c in calls), seconds=sum(c["seconds"] for c in calls),
                      calls=[{key: c[key] for key in ("key", "params", "n_in", "n_out", "seconds", "cache_hit", "transport_attempts")} for c in calls])
        if classified is not None:
            result.update(selected_inputs=selected, input_summary=classified["summary"], generator_attempts=attempts,
                          empty_inputs=not selected,
                          toolinput_removed=classified["summary"]["removed"] if arm in ("toolinput", "concept-toolinput") else 0)
        atomic_json(directory / "result.json", result)
        with lock, gen_path.open("a") as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
        return task["task"], arm, sample

    def bounded_work(job):
        if job_slots is None:
            return work(job)
        with job_slots:
            return work(job)

    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(bounded_work, job): job for job in jobs}
        for future in as_completed(pending):
            task, arm, sample = pending[future]
            try:
                future.result()
            except Exception as exc:
                failures.append((task["task"], arm, sample, type(exc).__name__))
                print(f"failed task={task['task']} arm={arm} sample={sample}: {type(exc).__name__}", flush=True)
    if failures:
        atomic_json(out_dir / "failures.json", failures)
        raise RuntimeError(f"{len(failures)} jobs failed; rerun to resume; no evaluation was run")
    print(f"generation ready: {gen_path}", flush=True)
    return gen_path


def prepare_task(task, client, precond_dir, facts_dir):
    summary = preconditions.mine(task, client, precond_dir)
    facts_dir = Path(facts_dir).resolve()
    facts_dir.mkdir(parents=True, exist_ok=True)
    output = facts_dir / f"{task['task']}.json"
    provenance = dict(valid_sha256=summary['valid_sha256'], mining_key=summary['cache_key'],
                      source_sha256={p: preconditions.sha((HERE/p).read_bytes()) for p in
                                     ('facts.py', 'tracer.py', 'fuzz_validity.py')})
    marker = output.with_suffix('.manifest.json')
    if output.exists():
        if not marker.exists() or json.loads(marker.read_text()) != dict(provenance, facts_sha256=preconditions.sha(output.read_bytes())):
            raise ValueError('facts cache changed; choose a fresh facts directory')
    else:
        temp = output.with_suffix('.pending.json')
        cmd = ['unshare', '-rn', sys.executable, '-I', '-B', str(HERE/'facts.py'), str(task['task']),
               str(generate.PUTS/f"HumanEval_{task['task']}/put0.py"), str(generate.HE), str(temp),
               '--validity', 'mined', '--precond-dir', str(Path(precond_dir).resolve())]
        env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
        with output.with_suffix('.log').open('w') as log:
            subprocess.run(cmd, env=env, stdout=log, stderr=log, check=True, timeout=3600)
        temp.replace(output)
        atomic_json(marker, dict(provenance, facts_sha256=preconditions.sha(output.read_bytes())))
    facts = json.loads(output.read_text())
    if facts.get('facts_version') != 'v3m' or facts.get('valid_sha256') != summary['valid_sha256']:
        raise ValueError('facts/validator mismatch')
    bundled = generate.bundle(task['task'], dict(entry_point=task['entry'], test=task['base']), facts_dir)
    bundled.update(placebo_meta=facts['placebo3'], split=task['split'], facts_version='v3m',
                   valid_sha256=summary['valid_sha256'],
                   mined_valid_src=(Path(precond_dir)/str(task['task'])/'valid.py').read_text())
    return bundled


def run_mined(ids, *, precond_only=False, precond_dir=preconditions.ROOT, facts_dir=DATA_OUT / 'facts_v3m',
              tasks_path=DATA_OUT / 'tasks_v3m_all.json', out_dir=DATA_OUT / 'gen2_qwen7b_v3m',
              generator_python=None, workers=16, k=3, client=None, arms=gen_prompts.DEFAULT_ARMS):
    """Each task completes mine -> facts -> bundle -> arms in the same bounded pool."""
    allowed = {int(n) for n in (HERE/'tasks.txt').read_text().split()} - DESIGN
    if not ids or len(set(ids)) != len(ids) or not set(ids) <= allowed:
        raise ValueError('expected distinct non-design task ids')
    # v3m must never overwrite a historical output directory, even through CLI overrides.
    for path in (precond_dir, facts_dir, tasks_path, out_dir):
        path = Path(path).resolve()
        old = [DATA_OUT/n for n in ('facts', 'facts_v2', 'facts_v3', 'facts_v3f', 'facts_v3c',
                                       'gen2_qwen7b', 'offline', 'offline_v2', 'offline_v3', 'offline_v3f', 'offline_v3c')]
        if any(path == p or p in path.parents for p in old) or path.name in ('tasks_v3_all.json', 'tasks_v3c_all.json', 'pilot_tasks.json', 'pilot_tasks_v3.json'):
            raise ValueError('v3m path points to protected output')
    client = client or Client(Path(precond_dir)/'cache', workers=workers)
    job_slots = threading.BoundedSemaphore(workers)
    if not precond_only:
        config = dict(ids=sorted(ids), k=k, model=client.model, facts_version='v3m',
                      precond_dir=str(Path(precond_dir).resolve()), facts_dir=str(Path(facts_dir).resolve()),
                      sources={p: preconditions.sha((HERE/p).read_bytes()) for p in
                               ('run_gen.py', 'preconditions.py', 'precond_prompts.py', 'llm_client.py',
                                'facts.py', 'tracer.py', 'gen_inputs.py', 'gen_prompts.py', 'prompts.py',
                                'generator_worker.py', 'fuzz_validity.py', 'PREREG.md')})
        config_path = Path(out_dir)/'run_config.json'
        if config_path.exists() and json.loads(config_path.read_text()) != config:
            raise ValueError('run configuration changed; choose a fresh output directory')
        atomic_json(config_path, config)
    he = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, generate.HE.open())}
    pilot = json.loads(generate.TASKS.read_text())['pilot']

    def work(n):
        task = dict(task=n, entry=he[n]['entry_point'], base=he[n]['test'],
                    put=(generate.PUTS/f'HumanEval_{n}/put0.py').read_text(), split='pilot' if n in pilot else 'dev')
        task = prepare_task(task, client, precond_dir, facts_dir)
        if not precond_only:
            code = (Path(precond_dir)/str(n)/'valid.py').read_text()
            run([task], {n: dict(mined_src=code)}, Path(out_dir)/'task_runs'/str(n), generator_python,
                k=k, workers=workers, client=client, facts_version='v3m', job_slots=job_slots, arms=arms)
        return task

    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = sorted(pool.map(work, ids), key=lambda t: t['task'])
    bundle = dict(facts_version='v3m', pilot=pilot, design_excluded=sorted(DESIGN), tasks=tasks)
    atomic_json(tasks_path, bundle)
    manifest = dict(facts_version='v3m', tasks_sha256=_digest(tasks), model=client.model,
                    valid_sha256={str(t['task']): t['valid_sha256'] for t in tasks},
                    eval_plan_sha256=preconditions.sha((HERE/'eval_plan_v3m.json').read_bytes()))
    atomic_json(Path(tasks_path).with_suffix('.manifest.json'), manifest)
    if not precond_only:
        out_dir = Path(out_dir)
        parts = [out_dir/'task_runs'/str(t['task']) for t in tasks]
        manifest.update(k=k, arms=tuple(a for a in gen_prompts.ARMS if a in arms),
                        task_manifests={str(t['task']): json.loads((p/'manifest.json').read_text()) for t,p in zip(tasks,parts)})
        manifest = json.loads(json.dumps(manifest))
        target = out_dir/'manifest.json'
        if target.exists() and json.loads(target.read_text()) != manifest:
            raise ValueError('run manifest changed; choose a fresh output directory')
        atomic_json(target, manifest)
        atomic_json(out_dir/'tasks.json', bundle)
        temp = out_dir/'gen.pending.jsonl'
        temp.write_text(''.join((p/'gen.jsonl').read_text() for p in parts))
        temp.replace(out_dir/'gen.jsonl')
    print(f"v3m {'preconditions/facts ready' if precond_only else 'generation ready'}: {len(tasks)} tasks", flush=True)
    return tasks


def main():
    raise SystemExit('v30 CPU-only: inherited generation CLI disabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', type=Path)
    parser.add_argument('--from-bundle', action='store_true', help='use --tasks unchanged, including its mined validators')
    parser.add_argument('--arms', nargs='+', choices=gen_prompts.ARMS, default=gen_prompts.DEFAULT_ARMS)
    parser.add_argument('--validity', choices=('mined', 'evalplus'), default='mined')
    parser.add_argument('--precond-only', action='store_true')
    parser.add_argument('--precond-dir', type=Path, default=preconditions.ROOT)
    parser.add_argument('--facts-dir', type=Path, default=DATA_OUT / 'facts_v3m')
    parser.add_argument('--bundle-only', action='store_true')
    parser.add_argument('--smoke', action='store_true', help='exactly three dev tasks (2,3,4), K=1')
    parser.add_argument('--task-ids', type=int, nargs='+')
    parser.add_argument('--out-dir', type=Path)
    parser.add_argument('--generator-python', type=Path, default=os.environ.get('QWEN_GENERATOR_PYTHON'))
    parser.add_argument('--contract-data', type=Path, default=gen_inputs.CONTRACTS)
    parser.add_argument('--k', type=int, default=3)
    parser.add_argument('--workers', type=int, default=16)
    args = parser.parse_args()
    if len(set(args.arms)) != len(args.arms):
        parser.error('--arms must be distinct')
    if args.from_bundle and (args.tasks is None or args.precond_only or args.bundle_only):
        parser.error('--from-bundle requires --tasks and cannot prepare facts/bundles')
    needs_generator = any(a.startswith('gen-') for a in args.arms)
    if args.k not in range(1,1000) or args.workers < 1:
        parser.error('k must be 1..999 and workers must be positive')
    if args.smoke and args.task_ids:
        parser.error('--smoke and --task-ids cannot be combined')
    ids = list(SMOKE) if args.smoke else args.task_ids
    if args.validity == 'mined' and not args.from_bundle:
        if args.bundle_only:
            parser.error('use --precond-only for the inline mined bundle')
        if not args.precond_only and needs_generator and args.generator_python is None:
            parser.error('--generator-python or QWEN_GENERATOR_PYTHON is required for arms')
        ids = ids or [int(n) for n in (HERE/'tasks.txt').read_text().split() if int(n) not in DESIGN]
        tasks_path = args.tasks or DATA_OUT/('tasks_v3m_all.json' if len(ids)==133 else 'tasks_v3m_subset.json')
        output = args.out_dir or DATA_OUT/('gen2_qwen7b_v3m/smoke' if args.smoke else 'gen2_qwen7b_v3m')
        run_mined(ids, precond_only=args.precond_only, precond_dir=args.precond_dir, facts_dir=args.facts_dir,
                  tasks_path=tasks_path, out_dir=output, generator_python=args.generator_python,
                  workers=args.workers, k=1 if args.smoke else args.k, arms=args.arms)
        return
    if args.precond_only:
        parser.error('--precond-only requires --validity mined')
    tasks_path = args.tasks or TASKS
    if args.bundle_only:
        tasks = bundle_all(tasks_path)
        print(f'bundled {len(tasks)} tasks')
        return
    if needs_generator and args.generator_python is None:
        parser.error('--generator-python or QWEN_GENERATOR_PYTHON is required')
    if not tasks_path.exists():
        if args.from_bundle:
            parser.error('--from-bundle requires an existing bundle')
        bundle_all(tasks_path)
    bundle = json.loads(tasks_path.read_text())
    tasks = bundle['tasks']
    if ids:
        tasks = [t for t in tasks if t['task'] in ids]
        if {t['task'] for t in tasks} != set(ids):
            parser.error('requested tasks are absent from the non-design bundle')
    output = args.out_dir or DATA_OUT/('gen2_qwen7b/smoke' if args.smoke else 'gen2_qwen7b')
    contracts = ({t['task']: dict(mined_src=t['mined_valid_src']) for t in tasks}
                 if args.from_bundle and bundle['facts_version'] == 'v3m' else gen_inputs.load_contracts(args.contract_data))
    run(tasks, contracts, output, args.generator_python,
        k=1 if args.smoke else args.k, workers=args.workers, facts_version=bundle['facts_version'], arms=args.arms)


if __name__ == '__main__':
    main()
