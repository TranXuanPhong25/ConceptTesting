"""Final reference grading, using the copied v11 native workers and comparator."""
import json
from collections import defaultdict
from .paths import HERE
from . import oracle_b01 as ob, v4_runtime
from .llm_client import atomic_json
from .prepare_comparison import verify, sha


def score(prepared):
    from .comparison import ROOT, run_pool, status
    freeze = json.loads((ROOT/'GENERATION_FREEZE.json').read_text())
    for name, expected in freeze['files'].items():
        assert sha(ROOT/name) == expected, name
    refs = {int(r['task_id'].split('/')[1]):r for r in json.loads((HERE/'assets/grading_references.json').read_text())}

    def one(pair):
        n, rows = pair['v11']['task'], []
        h = refs[n]
        for arm in ('v11','retrieval'):
            generated = [json.loads(line) for line in (ROOT/'generation'/arm/str(n)/'gen.jsonl').read_text().splitlines()]
            job = dict(task=pair[arm], rows=generated, canon=h['prompt']+h['canonical_solution'],
                       contract_src=h['prompt']+h['contract']+'\n    pass\n', atol=h.get('atol', 0))
            evaluated = v4_runtime.isolated('evaluate', job, ROOT/'grading'/str(n)/arm, timeout=1800)
            rows += [dict(r, arm=arm if r['arm']=='concept-hybrid' else arm+'_round1') for r in evaluated]
        task = pair['v11']
        calls, expected = set(), defaultdict(set)
        for row in rows:
            for assertion in row['asserts']:
                call, expr = ob.call_of(assertion['src'], task['entry']), ob.expected_of(assertion['src'])
                if call is not None:
                    calls.add(call)
                    if expr is not None:
                        expected[call].add(expr)
        programs = [ob.code_block(json.loads((ROOT/'oracles'/str(n)/f'{s}.json').read_text())['response']['text']) for s in range(10)]
        job = dict(entry=task['entry'], put=task['put'], canon=h['prompt']+h['canonical_solution'],
                   base=task['base'], contract=h['prompt']+h['contract']+'\n    pass\n',
                   spec=ob.preconditions.specification(task)[0], dpp=[], tc=[], ref=programs,
                   post=[], mutants=[], calls=sorted(calls), b1={}, o0={c:sorted(v) for c,v in expected.items()},
                   atol=h.get('atol', 0), shared_scorer=True)
        executed = v4_runtime.isolated('oracle', job, ROOT/'grading'/str(n)/'oracle', timeout=3000)
        atomic_json(ROOT/'scored'/f'{n}.json', dict(rows=rows, execution=executed))
        return dict(task=n, rows=rows, execution=executed)

    scored = run_pool('grading', prepared, one)
    tasks = {p['v11']['task']:p['v11'] for p in prepared}
    rows = [r for s in scored for r in s['rows']]
    executions = {str(s['task']):s['execution'] for s in scored}
    metrics = ob.fairness_metrics(tasks, rows, executions, {})
    results = {}
    for oracle in ('ref','o0'):
        arms = {}
        for arm in ('v11','retrieval','v11_round1','retrieval_round1'):
            confirmed, alarms, abstained = set(), set(), 0
            for row in (r for r in rows if r['arm']==arm):
                seen = set()
                for assertion in row['asserts']:
                    call = ob.call_of(assertion['src'], tasks[row['task']]['entry'])
                    if call is None or oracle=='ref' and call in seen:
                        continue
                    seen.add(call)
                    rec = executions[str(row['task'])]['calls'].get(call, {})
                    emit, correct, passes_put = ob.decide(oracle, rec, None, ob.expected_of(assertion['src']), assertion)
                    abstained += not emit
                    if emit and not passes_put:
                        (confirmed if rec.get('valid', False) and correct else alarms).add(row['task'])
            arms[arm] = dict(tasks=113, confirmed_tasks=sorted(confirmed), false_alarm_tasks=sorted(alarms), abstained_calls=abstained)
        wins = sorted(set(arms['retrieval']['confirmed_tasks']) - set(arms['v11']['confirmed_tasks']))
        losses = sorted(set(arms['v11']['confirmed_tasks']) - set(arms['retrieval']['confirmed_tasks']))
        results[oracle] = dict(arms=arms, wins=wins, losses=losses, sign_test_p=ob.sign_p(len(wins),len(losses)))
    responses = [json.loads(p.read_text()) for p in (ROOT/'transport/calls').glob('*/response.json')]
    attempts = [json.loads(line) for line in (ROOT/'transport/attempts.jsonl').read_text().splitlines()]
    assert len(attempts) == len({r['key'] for r in attempts}) <= 3503
    usage = {k:sum(r.get('usage',{}).get(k,0) for r in responses) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    verify()
    atomic_json(ROOT/'RESULTS.json', dict(results=results, metrics=metrics, usage=usage, completion_attempts=len(attempts),
                                        unknown_completion_usage=sum(bool(r.get('unknown_completion_usage')) for r in responses)))
    status('complete', 113, results={oracle:{arm:len(results[oracle]['arms'][arm]['confirmed_tasks']) for arm in ('v11','retrieval')} for oracle in results}, usage=usage)
    atomic_json(ROOT/'COMPLETE.json', json.loads((ROOT/'STATUS.json').read_text()))
