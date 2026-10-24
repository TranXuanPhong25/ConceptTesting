"""v55 preparation, isolated Codex writer, and gated v53/v49 scorer.

Run from repo root with PYTHONPATH=. and the registered interpreter.
No generation or scoring is performed by `prepare`.
"""
import argparse
import ast
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from trickcatcher_linefacts.analysis.v53_validity_smallscope import smallscope as S

O, V, E = S.O, S.V, S.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / HERE.name
ARMS = ('defn', 'interpretation', 'placebo')
MODEL = 'gpt-6.1-sol'
COMMENT = 'Use 80–120 words for this introductory comment block. '
EXTRA = {
    'defn': '',
    'interpretation': COMMENT + 'Before writing code, list ambiguous points of the statement as comments, '
        'including candidate interpretations. Select the interpretation consistent with every public test. '
        'Write `# INTERPRETATION: ...` explicitly stating your chosen semantics immediately above the '
        'ENUMERATE/CHECK/AGGREGATE definition. Do not invent constraints or rules. ',
    'placebo': COMMENT + 'Before writing code, write a comment about Python formatting: indentation, '
        'blank lines, descriptive local names and readable line breaks. Keep this comment unrelated to '
        'the meaning or interpretation of the problem. ',
}


def digest(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def save(path, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != text:
        raise RuntimeError('immutable file differs: ' + str(path))
    path.write_text(text)


def latest_primary(root):
    latest = None
    for path in root.rglob('*.jsonl'):
        try:
            for line in path.open():
                if 'rate_limits' not in line:
                    continue
                d = json.loads(line)
                limits = d.get('payload', {}).get('rate_limits')
                if limits and limits.get('primary') and (latest is None or d['timestamp'] > latest[0]):
                    latest = d['timestamp'], limits['primary']
        except (OSError, ValueError):
            continue
    return None if latest is None else dict(timestamp=latest[0], remaining_percent=100-latest[1]['used_percent'],
                                            resets_at=latest[1]['resets_at'])


def quota():
    candidates = [latest_primary(Path.home()/'.codex/sessions')]
    candidates += [json.loads(p.read_text()) for p in (OUT/'quota_observations').glob('*.json')]
    candidates = [c for c in candidates if c is not None]
    if not candidates:
        raise RuntimeError('no quota evidence; cannot start a batch')
    return max(candidates, key=lambda q: q['timestamp'])


def prepare():
    _, probs = V.problems()
    manifest = []
    problem_list = list(sorted(probs))
    for kind in (*ARMS, 'open', 'plain'):
        for sample in range(3 if kind in ARMS else 1):
            for start in range(0, len(problem_list), 8):
                ids = problem_list[start:start+8]
                parts = []
                for pid in ids:
                    task = E.task_view(probs[pid][0])
                    if kind in ARMS:
                        msg = S.gen.messages(task, 'defn')[1]['content']
                        # Interpretation/placebo precede the same literal defn instruction.
                        msg = msg.replace(S.gen.INSTR['defn'], EXTRA[kind]+S.gen.INSTR['defn'])
                        msg += '\nUse at most 1024 output tokens for this answer.'
                    else:
                        msg = V.message(task, 'open') if kind == 'open' else S.message(task, 'plain')
                    parts.append(dict(id=pid, prompt=msg))
                prompt = ('Answer each problem independently using only the supplied prompt. Do not use tools, '
                          'search, files or external information. Return exactly a JSON object mapping each id '
                          'to a string containing one fenced Python code block, with no other text.\n\n'
                          + json.dumps(parts, ensure_ascii=False))
                name = f'{kind}_{sample}_{start//8}'
                path = OUT / 'prompts' / (name+'.txt')
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and path.read_text() != prompt:
                    raise RuntimeError('prompt changed')
                path.write_text(prompt)
                manifest.append(dict(call=name, kind=kind, sample=sample, problems=ids,
                                     entrypoints={pid: ('inputs' if kind == 'plain' else
                                         ast.parse('def '+E.task_view(probs[pid][0])['signature']+':\n pass').body[0].name)
                                         for pid in ids} if kind != 'open' else {},
                                     prompt_sha256=digest(prompt)))
    save(OUT/'manifest.json', manifest)
    save(HERE/'MANIFEST.json', manifest)
    save(OUT/'problems.json', {p: [c['case_id'] for c in cs] for p, cs in probs.items()})
    save(HERE/'DEPENDENCIES.json', {p: sha for p, sha in O.Inventory().finish().items()
                                  if not p.startswith(str(HERE.relative_to(E.REPO))+'/')})
    print(json.dumps(dict(problems=len(probs), calls=len(manifest), oracle_answers=len(probs)*9,
                          shared_answers=len(probs)*2)))


def isolated(prompt, call_root):
    """Mount only auth read-only; hide repo, all user home and host /tmp.

    New PID namespace prevents /proc/<hostpid>/root from exposing the host repo.
    No model artifacts are written by this parent process.
    """
    call_root.mkdir(parents=True, exist_ok=False)
    save(call_root/'attempt.json', dict(prompt_sha256=digest(prompt),
         started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='unresolved'))
    auth = Path.home()/'.codex/auth.json'
    with tempfile.TemporaryDirectory(prefix='v55-writer-') as directory:
        root = Path(directory)
        for name in ('home', 'work', 'codex'):
            (root/name).mkdir()
        (root/'codex/auth.json').touch()
        args = ['bwrap', '--ro-bind', '/', '/', '--tmpfs', '/home', '--tmpfs', '/tmp',
                '--bind', str(root), '/tmp/isolate', '--ro-bind', str(auth), '/tmp/isolate/codex/auth.json',
                '--unshare-pid', '--proc', '/proc', '--dev', '/dev', '--chdir', '/tmp/isolate/work',
                '--setenv', 'HOME', '/tmp/isolate/home', '--setenv', 'CODEX_HOME', '/tmp/isolate/codex',
                '--', '/usr/bin/codex', 'exec', '--ignore-user-config', '--ignore-rules',
                '--skip-git-repo-check', '-s', 'read-only', '-c', 'features.shell_tool=false',
                '-c', 'features.apps=false', '-m', MODEL, '-c', 'model_reasoning_effort="medium"',
                '--json', '-']
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if k in os.environ}
        try:
            run = subprocess.run(args, input=prompt, text=True, capture_output=True, env=env, timeout=900)
        except (subprocess.TimeoutExpired, OSError, KeyboardInterrupt) as exc:
            save(call_root/'failure.json', dict(error_type=type(exc).__name__, status='unresolved',
                                               retry_allowed=False))
            raise
        finally:
            observation = latest_primary(root/'codex/sessions')
            if observation is not None:
                save(OUT/'quota_observations'/(call_root.name+'.json'), observation)
    (call_root/'events.jsonl').write_text(run.stdout)
    # stderr can contain transport diagnostics; never print endpoint bodies.
    errors = [line for line in run.stderr.splitlines() if 'ngrok' not in line.lower()]
    (call_root/'stderr.txt').write_text('\n'.join(errors)+'\n')
    events = []
    for line in run.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    items = [e.get('item', {}) for e in events if e.get('type') == 'item.completed']
    tools = [e.get('item', {}) for e in events if e.get('type') in
             ('item.started', 'item.updated', 'item.completed') and
             e.get('item', {}).get('type') not in ('agent_message', 'reasoning', 'error')]
    answers = [i.get('text', '') for i in items if i.get('type') == 'agent_message']
    audit = dict(exit_code=run.returncode, prompt_sha256=digest(prompt), model=MODEL,
                 writer_saw_only_prompt=True, repository_hidden=True, tool_items=len(tools),
                 usage=[e for e in events if e.get('type') == 'turn.completed'])
    save(call_root/'audit.json', audit)
    if run.returncode or tools or len(answers) != 1:
        raise RuntimeError('isolated Codex call incomplete or tool audit failed; no automatic retry')
    return answers[0]


def review_gate():
    path = HERE/'REVIEW_APPROVED.json'
    if not path.exists():
        raise RuntimeError('independent review gate pending')
    approved = json.loads(path.read_text())
    for filename in ('experiment.py', 'PREREG.md', 'MANIFEST.json', 'DEPENDENCIES.json'):
        if approved['sha256'][filename] != digest((HERE/filename).read_bytes()):
            raise RuntimeError('reviewed file changed: '+filename)
    for filename, sha in json.loads((HERE/'DEPENDENCIES.json').read_text()).items():
        if digest((E.REPO/filename).read_bytes()) != sha:
            raise RuntimeError('registered dependency changed: '+filename)


def validate_answer(text, kind, entrypoint=None):
    code = O.code_block(text)
    if not code:
        raise ValueError('missing Python code block')
    tree = ast.parse(code)
    if kind == 'open':
        if V.checks(text)[2] != 'ok':
            raise ValueError('malformed open checker')
    elif not any(isinstance(node, ast.FunctionDef) and node.name == entrypoint for node in tree.body):
        raise ValueError('missing module-level entrypoint')


def generate():
    review_gate()
    for job in json.loads((HERE/'MANIFEST.json').read_text()):
        directory = OUT/'calls'/job['call']
        if (directory/'accepted.json').exists():
            continue
        if directory.exists():
            raise RuntimeError('previous attempt unresolved: '+job['call'])
        q = quota()
        # A successful writer without a rate event requires a fresh host event
        # before another call, including after restarting this controller.
        for accepted in (OUT/'calls').glob('*/accepted.json'):
            if not (OUT/'quota_observations'/(accepted.parent.name+'.json')).exists():
                started = json.loads((accepted.parent/'attempt.json').read_text())['started_at']
                if q['timestamp'] <= started:
                    raise RuntimeError('fresh host quota required after writer with no rate event')
        if q['remaining_percent'] < 15:
            with (HERE/'CHANGELOG.md').open('a') as f:
                f.write('\nQuota stop: '+json.dumps(q)+'; next call '+job['call']+'.\n')
            raise RuntimeError('quota stop; checkpoint must be committed before exit')
        prompt = (OUT/'prompts'/(job['call']+'.txt')).read_text()
        assert digest(prompt) == job['prompt_sha256']
        answer = isolated(prompt, directory)
        (directory/'answer.txt').write_text(answer)
        parsed = json.loads(answer)
        if set(parsed) != set(job['problems']):
            raise RuntimeError('incomplete/malformed batch; no repair or scoring')
        for pid, text in parsed.items():
            validate_answer(text, job['kind'], job['entrypoints'].get(pid))
        for pid, text in parsed.items():
            kind = job['kind']
            path = OUT/'answers'/kind/(f'{pid}_{job["sample"]}.txt' if kind in ARMS else pid+'.txt')
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise RuntimeError('answer already exists')
            path.write_text(text)
        save(directory/'accepted.json', dict(job=job, quota=q, answer_sha256=digest(answer)))
        print('accepted', job['call'], flush=True)
        if not (OUT/'quota_observations'/(directory.name+'.json')).exists():
            raise RuntimeError('answer saved but writer quota unavailable; obtain fresh host quota before next batch')


def accepted_inputs(case, rec, pid, inputs):
    code, checks, status = V.checks((OUT/'answers/open'/f'{pid}.txt').read_text())
    if status != 'ok':
        raise RuntimeError('malformed open checks')
    srcs = [V.wrap(code, case['entry'], c['name']) for c in checks]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'codex_open', srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'codex_open', srcs, inputs, 'all')
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = [j for j in range(len(checks)) if all(ok(o) for o in base[f'p{j}'])]
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}, dict(
        total=len(checks), kept=len(kept), dropped=len(checks)-len(kept))


def score():
    review_gate()
    jobs = json.loads((HERE/'MANIFEST.json').read_text())
    if any(not (OUT/'calls'/j['call']/'accepted.json').exists() for j in jobs):
        raise RuntimeError('all writer calls must be complete before computing outcomes')
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, _ = ready
    run, probs = V.problems()
    cases = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    official = E.Reference(run)
    official.root = OUT/'references/official'
    # All generator executions and new reference caches remain under v55.
    S.OUT = OUT
    tasks = {}
    for cid in cohort:
        case, rec, pid = cases[cid], records[cid], pid_of[cid]
        universe = E.ordered(rec['inputs'])
        generated, gen_info = S.generated(case, pid, 'plain')
        if gen_info['status'] != 'ok':
            raise RuntimeError('generator execution failed; run incomplete, no automatic repair')
        everything = list(dict.fromkeys(universe+generated))
        acc, filter_info = accepted_inputs(case, rec, pid, everything)
        pools = dict(universe=[l for l in universe if acc[l]], plain=[l for l in generated if acc[l]])
        used = list(dict.fromkeys(pools['universe']+pools['plain']))
        pools['union'] = used
        new = [l for l in used if l not in rec['inputs']]
        with E.execution_root(OUT):
            newput = O.run_programs(case, 'put', [case['source']], new, 'new')['p0'] if new else []
        puts = {l: rec['inputs'][l]['put'] for l in used if l in rec['inputs']} | dict(zip(new, newput))
        truth = S.truth_for(inv, case, {l: dict(put=puts[l]) for l in used}, official)
        arms = {}
        for arm in ARMS:
            srcs = [O.code_block((OUT/'answers'/arm/f'{pid}_{i}.txt').read_text()) for i in range(3)]
            with E.execution_root(OUT):
                base = O.run_programs(case, arm, srcs, rec['base_inputs'], 'base', 2)
                reasons = {j: O.rejection(rec['base_put'], base[f'p{j}']) for j in range(3)}
                strict = [j for j in range(3) if srcs[j] and not reasons[j]]
                tolerant = [j for j in range(3) if srcs[j] and (not reasons[j] or (
                    O.resource_only(reasons[j], base[f'p{j}']) and 'mismatch' not in reasons[j]
                    and any(o and o[0] == 'ok' for o in base[f'p{j}'])))]
                ran = O.run_programs(case, arm+'_valid', [srcs[j] for j in tolerant], used, 'used')
            rows = {}
            for name, ids in (('tolerant', tolerant), ('strict', strict)):
                rows[name] = {}
                for n, lit in enumerate(used):
                    outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
                    rows[name][lit] = dict(put=puts[lit], programs=outs, **O.votes(puts[lit], outs))
            metrics = {name: S.arm_metrics(inputs, rows, truth, len(tolerant), len(strict))
                       for name, inputs in pools.items()}
            emitted = E.emitted(used, rows['tolerant'], 'primary', 20)
            labels = O.labels_for(rows['tolerant'], truth)
            split = collections.Counter()
            for lit in emitted:
                if labels[lit]['primary'] == 'confirmed':
                    continue
                t = truth[lit]
                value = E.iorel.value(rows['tolerant'][lit]['primary'])
                split['invalid' if not t['valid'] else 'unknown_reference' if t['ref'] is None else
                      'wrong_value' if not E.same(value, t['ref']) else 'unconfirmed'] += 1
            common = collections.Counter()
            abstentions = collections.Counter()
            for lit in used:
                row = rows['tolerant'][lit]
                abstentions['program_input_calls'] += len(row['programs'])
                abstentions['nonfinishing_program_inputs'] += sum(not o or o[0] != 'ok' for o in row['programs'])
                abstentions['no_primary_vote_inputs'] += row['primary'] is None
                t = truth[lit]
                if not t['valid'] or t['ref'] is None or not t['exposes']():
                    continue
                abstentions['exposing_inputs'] += 1
                abstentions['exposing_no_primary_vote'] += row['primary'] is None
                vals = [E.iorel.value(o) for o in rows['tolerant'][lit]['programs'] if o and o[0] == 'ok']
                if len(vals) >= 2 and all(v is not None and E.same(v, vals[0]) for v in vals) and not E.same(vals[0], t['ref']):
                    common['with_put' if E.same(vals[0], E.iorel.value(puts[lit])) else 'away_from_put'] += 1
            arms[arm] = dict(pools=metrics, fa_split=dict(split), common_mode=dict(common),
                             abstentions=dict(abstentions), strict=strict, tolerant=tolerant, rejection=reasons)
        tasks[cid] = dict(problem=pid, arms=arms, generator=gen_info, validity=filter_info)
        print('scored', cid, flush=True)
    totals = {}
    for arm in ARMS:
        sums = collections.Counter()
        for task in tasks.values():
            m = task['arms'][arm]
            sums.update({k: m['pools']['union'][k] for k in ('confirmed_tasks', 'confirmed_tests', 'tests', 'fa_tests')})
        totals[arm] = dict(sums, precision=sums['confirmed_tests']/sums['tests'] if sums['tests'] else None,
                          common_mode_problems=len({t['problem'] for t in tasks.values() if any(
                              t['arms'][arm]['common_mode'].values())}))
    pairs = {}
    for control in ('defn', 'placebo'):
        wins = [c for c, t in tasks.items() if t['arms']['interpretation']['pools']['union']['confirmed_tasks']
                and not t['arms'][control]['pools']['union']['confirmed_tasks']]
        losses = [c for c, t in tasks.items() if t['arms'][control]['pools']['union']['confirmed_tasks']
                  and not t['arms']['interpretation']['pools']['union']['confirmed_tasks']]
        a, b = totals['interpretation'], totals[control]
        pairs[control] = dict(wins=wins, losses=losses, promising=(len(wins)-len(losses) >= 2 and
            len({tasks[c]['problem'] for c in wins}) >= 2 and a['fa_tests'] <= b['fa_tests'] and
            (a['precision'] or 0) >= .95 and a['common_mode_problems'] < b['common_mode_problems']))
    save(OUT/'score.json', dict(tasks=tasks, totals=totals, paired=pairs,
         decision='promising' if all(p['promising'] for p in pairs.values()) else 'not promising'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'generate', 'score', 'quota'))
    args = parser.parse_args()
    if args.action == 'quota':
        print(json.dumps(quota()))
    else:
        globals()[args.action]()
