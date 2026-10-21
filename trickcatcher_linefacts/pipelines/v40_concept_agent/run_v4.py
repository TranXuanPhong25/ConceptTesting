"""V4 B5/domain mining, standard facts, and seven cached o0 arms."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import argparse
import ast
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import evaluate, gen_inputs, gen_prompts, generate, preconditions, prompts, run_gen, v4_prompts, v4_runtime, v4_strategies
from .llm_client import Client, atomic_json


def task_sources(ids):
    allowed = {int(n) for n in (HERE/'tasks.txt').read_text().split()} - run_gen.DESIGN
    if not ids or len(set(ids)) != len(ids) or not set(ids) <= allowed:
        raise ValueError('expected distinct non-design tasks')
    he = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, generate.HE.open())}
    pilot = json.loads(generate.TASKS.read_text())['pilot']
    tasks = [dict(task=n, entry=he[n]['entry_point'], base=he[n]['test'],
                  put=(generate.PUTS/f'HumanEval_{n}/put0.py').read_text(),
                  split='pilot' if n in pilot else 'dev') for n in ids]
    return tasks, he, pilot


def safe_path(path):
    from .paths import safe_output
    return safe_output(path)


def mined_task(task, precond_dir, strategy_dir):
    pd, sd = Path(precond_dir)/str(task['task']), Path(strategy_dir)/str(task['task'])
    p, s = json.loads((pd/'summary.json').read_text()), json.loads((sd/'summary.json').read_text())
    specification = pd/'specification.py'
    if specification.exists() and specification.read_text() != preconditions.specification(task)[0]+'\n':
        raise ValueError('reused mining belongs to a different specification')
    verifier_job = pd/'verifier_job.json'
    if verifier_job.exists():
        original_task = json.loads(verifier_job.read_text())['task']
        if any(original_task[key] != task[key] for key in ('entry','put','base')):
            raise ValueError('reused mining belongs to different PUT/base tests')
    valid, strategy = (pd/'valid.py').read_text(), (sd/'strategy.py').read_text()
    if p.get('seed') != CONFIG['seeds']['mining'] + task['task'] or p.get('model') != CONFIG['model']:
        raise ValueError('reused mining has different model/seed settings')
    if p.get('evidence_filter') is not False or p.get('preconditions_version') != 'B5':
        raise ValueError('v4 requires B5 preconditions')
    if preconditions.sha(valid) != p['valid_sha256'] or s['valid_sha256'] != p['valid_sha256'] or preconditions.sha(strategy) != s['strategy_sha256']:
        raise ValueError('domain/validator hash mismatch')
    return dict(task, mined_valid_src=valid, valid_sha256=p['valid_sha256'], strategy_src=strategy,
                strategy_sha256=s['strategy_sha256'], strategy_fallback=s['fallback'],
                mining_summary=p, facts_version='v4')


def mine(tasks, client, precond_dir, strategy_dir, python, workers):
    def work(task):
        preconditions.mine(task, client, precond_dir, evidence_filter=False, python=python)
        return v4_strategies.mine(task, client, precond_dir, strategy_dir, python)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(work, tasks))
    atomic_json(Path(strategy_dir)/'mining_summary.json', dict(tasks=results, tools=v4_runtime.VERSIONS,
                 fallback_tasks=[r['task'] for r in results if r['fallback']]))
    return results


def facts(tasks, he, pilot, precond_dir, strategy_dir, facts_dir, tasks_path, python, workers):
    facts_dir, tasks_path = safe_path(facts_dir), safe_path(tasks_path)
    facts_dir.mkdir(parents=True, exist_ok=True)
    def work(raw):
        task = mined_task(raw, precond_dir, strategy_dir)
        n = task['task']; output = facts_dir/f'{n}.json'; marker = output.with_suffix('.manifest.json')
        provenance = dict(task_sha256=run_gen._digest(task), sources=v4_runtime.source_hashes(), tools=v4_runtime.VERSIONS)
        if output.exists():
            if not marker.exists() or json.loads(marker.read_text()) != dict(provenance, facts_sha256=preconditions.sha(output.read_bytes())):
                raise ValueError('facts cache changed; use a fresh directory')
            fr = json.loads(output.read_text())
        else:
            fr = v4_runtime.isolated('facts', dict(task=task, he=he[n]), facts_dir/'jobs'/str(n), python, 3600)
            atomic_json(output, fr)
            atomic_json(marker, dict(provenance, facts_sha256=preconditions.sha(output.read_bytes())))
        top = [fr['facts'][i] for i in fr['top3']]
        return dict(task, concept_meta=top, concept_facts=[f['text'] for f in top],
                    placebo_meta=fr['placebo3'], placebo_facts=[f['text'] for f in fr['placebo3']],
                    tool_inputs=list(dict.fromkeys(f['witness_call'] for f in top if f['witness_call'])), doc_fail=fr['doc_fail'])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        bundles = sorted(pool.map(work, tasks), key=lambda t:t['task'])
    bundle = dict(facts_version='v4', tools=v4_runtime.VERSIONS, pilot=pilot,
                  design_excluded=sorted(run_gen.DESIGN), tasks=bundles)
    v4_runtime.immutable(tasks_path, bundle)
    return bundles


def classify(task, directory, python, *, candidates=None, assertions=None, shown=(), requested_draws=None):
    payload = dict(task=task, shown=list(shown))
    payload.update(assertions=assertions) if assertions is not None else payload.update(candidates=candidates or [])
    if requested_draws is not None: payload['requested_draws']=requested_draws
    try:
        return v4_runtime.isolated('classify', payload, directory, python)
    except RuntimeError as exc:
        # A classification sandbox that fails (e.g. total timeout) yields an empty, recorded result instead of aborting
        # the whole run (same rule as gen_inputs.classify in the v3m2 run).
        n = len(assertions if assertions is not None else candidates or [])
        return dict(records=[], summary=dict(candidates=n, valid=0, removed=n, raw_candidates=n, raw_valid=0,
                    oversize=0, trace_errors=0, shown_hit_counts=[0]*len(shown), concept_hit_counts=[0]*len(task.get('concept_meta', [])),
                    concept_hit_rates=[0.0]*len(task.get('concept_meta', [])), requested_draws=requested_draws or n,
                    raw_valid_rate=0.0, first_contract_message=f'classification failed: {exc}', classification_error=str(exc)))


def assertions(text):
    # Per completion cap stays 10; merging retains both rounds rather than silently truncating to 10.
    return evaluate.extract_asserts(text)


def merge(first, second):
    return list(dict.fromkeys(first + second))


def run(tasks, out_dir, python, generator_python=None, *, client=None, k=3, workers=16):
    out_dir = safe_path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    client = client or Client(out_dir/'cache', workers=workers)
    python = v4_runtime.interpreter(python)
    generator_python = Path(generator_python or python).absolute()
    if generator_python != python:
        raise ValueError('every v4 sandbox, including gen-plain, must use --python/V4_PYTHON')
    for t in tasks:
        if t.get('facts_version') != 'v4' or preconditions.sha(t['strategy_src']) != t['strategy_sha256'] or preconditions.sha(t['mined_valid_src']) != t['valid_sha256']:
            raise ValueError('v4 bundle hash/version mismatch')
        if any('mutant_src' not in f for key in ('concept_meta','placebo_meta') for f in t[key] if f['kind']=='MUTANT'):
            raise ValueError('shown mutants require full sources for post-hoc oracle_b01')
    manifest = dict(version='v4-o0', pipeline_version=CONFIG['VERSION'], facts_version='v4', model=client.model, k=k, arms=v4_prompts.ARMS,
                    tasks_sha256=run_gen._digest(tasks), sources=v4_runtime.source_hashes(), tools=v4_runtime.VERSIONS,
                    prereg_sha256=preconditions.sha((HERE/'PREREG.md').read_bytes()), python=str(python),
                    generator_python=str(generator_python), n_round2=100, per_fact=2, templates=gen_prompts.TEMPLATE_SHA256)
    v4_runtime.immutable(out_dir/'manifest.json', manifest)
    v4_runtime.immutable(out_dir/'tasks.json', dict(facts_version='v4', tasks=tasks))
    run_id = run_gen._digest(manifest)

    def work(pair):
        task, sample = pair
        root = out_dir/'artifacts'/str(task['task'])/str(sample); root.mkdir(parents=True, exist_ok=True)
        results = {}
        def one(arm):
            directory = root/arm; directory.mkdir(exist_ok=True)
            saved = directory/'result.json'
            if saved.exists():
                result = json.loads(saved.read_text())
                if result['run_id'] != run_id: raise ValueError('sample manifest mismatch')
                results[arm] = result; return result
            calls, selected, attempts, stage1_summaries = [], [], [], []
            round1 = []; count = 0
            def query(messages, stage, request=0, retry=0, label='response', strategy=False):
                atomic_json(directory/(label+'_prompt.json'), messages)
                response = client.chat(messages, v4_prompts.seed(task['task'],arm,sample,stage,request,retry),
                                       **(dict(temperature=0,top_p=1,max_tokens=4096) if strategy else {}))
                atomic_json(directory/(label+'.json'),response); calls.append(response)
                return response['text']
            if arm in ('plain','concept','placebo-hybrid'):
                kind = 'placebo' if arm=='placebo-hybrid' else arm
                round1 = assertions(query(gen_prompts.messages(*prompts.build(kind,task)),0,label='round1'))
            elif arm in ('concept-hybrid','plain-hybrid'):
                original = results['concept' if arm=='concept-hybrid' else 'plain']
                round1 = original['assertions'][:]
                # Attribute the same logical request/tokens to both arms; cache makes its physical request shared.
                calls += original['calls']
            if arm in ('toolinput','gen-plain'):
                if arm=='toolinput':
                    candidates = [dict(input_repr=repr(tuple(ast.literal_eval(x['input_repr']))))
                                  for x in gen_inputs.witness_candidates(task)]
                    flagged = classify(task,directory/'witnesses',python,candidates=candidates)
                    stage1_summaries.append(flagged['summary'])
                    selected = [r for r in flagged['records'] if r['valid']][:3]
                else:
                    messages = gen_prompts.generator_messages('gen-plain',task)
                    for retry in range(2):
                        d = directory/f'generator_{retry}'; d.mkdir(exist_ok=True)
                        raw = query(messages,1,retry=retry,label=f'generator_{retry}')
                        try:
                            code = gen_inputs.extract_generator(raw)
                            (d/'generator.py').write_text(code+'\n')
                            generated = gen_inputs.generate_candidates(code,task,generator_python,d,
                                v4_prompts.seed(task['task'],arm,sample,3,retry=retry))
                        except (SyntaxError,ValueError):
                            generated = dict(candidates=[],errors=['could not extract sample_one()'])
                        flagged = classify(task,d,python,candidates=generated['candidates'],requested_draws=100)
                        stage1_summaries.append(flagged['summary'])
                        correction = gen_inputs.feedback(generated,flagged,[])
                        attempts.append(dict(generated=generated,summary=flagged['summary'],feedback=correction))
                        if correction is None or retry==1: break
                        messages += [dict(role='assistant',content=raw),dict(role='user',content=correction)]
                    valid = [r for r in flagged['records'] if r['valid']]
                    selected = random.Random(v4_prompts.seed(task['task'],arm,sample,3)).sample(valid,min(3,len(valid)))
                final = assertions(query(gen_prompts.oracle_messages(task,selected),2,label='oracle'))
            elif arm.endswith('-hybrid'):
                shown = task['concept_meta'] if arm=='concept-hybrid' else task['placebo_meta'] if arm=='placebo-hybrid' else []
                r1 = classify(task,directory/'round1_inputs',python,assertions=round1,shown=shown)
                missed = [i for i,h in enumerate(r1['summary']['shown_hit_counts']) if not h]
                budget = results['concept-hybrid']['round2_strategy_requests'] if arm=='plain-hybrid' else len(missed)
                for request in range(budget):
                    fact = None if arm=='plain-hybrid' else shown[missed[request]]
                    messages = v4_prompts.hybrid_messages(task,fact,round1)
                    for retry in range(1 if arm=='plain-hybrid' else 2):
                        d = directory/f'request_{request}_{retry}'; d.mkdir(exist_ok=True)
                        raw = query(messages,1,request,retry,f'strategy_{request}_{retry}',True); count += 1
                        error = None; generated = None; flagged = None
                        try:
                            code = v4_strategies.checked(raw); (d/'strategy.py').write_text(code)
                            generated = v4_strategies.draws(code,task,d,python,
                                v4_prompts.seed(task['task'],arm,sample,3,request,retry))
                            flagged = classify(task,d,python,candidates=generated['candidates'],shown=[fact] if fact else [],requested_draws=100)
                            stage1_summaries.append(flagged['summary'])
                            good = [r for r in flagged['records'] if r['valid'] and (fact is None or r['shown_hits'][0])]
                            if not good: error = 'No valid input exercised the fact.' if fact else 'No valid inputs returned.'
                            if generated['nonliteral'] or generated['wrong_arity'] or generated['errors']:
                                error = json.dumps({key:generated[key] for key in ('nonliteral','wrong_arity','errors')})
                        except (SyntaxError,ValueError,RuntimeError) as exc:
                            good = []; error = f'{type(exc).__name__}: {exc}'
                        picked = random.Random(v4_prompts.seed(task['task'],arm,sample,3,request,retry)).sample(good,min(2,len(good))) if not error else []
                        attempts.append(dict(request=request,retry=retry,fact_index=missed[request] if fact else None,
                                             error=error,selected=picked,generated=generated,
                                             summary=flagged['summary'] if flagged else None))
                        selected += picked
                        if not error or retry==1 or arm=='plain-hybrid': break
                        messages += [dict(role='assistant',content=raw),dict(role='user',content=v4_prompts.RETRY.format(error=error))]
                selected = list({r['input_repr']:r for r in selected}.values())
                injected = assertions(query(gen_prompts.oracle_messages(task,selected),2,label='oracle')) if count else []
                final = merge(round1,injected)
            else:
                final = round1
            inputs = classify(task,directory/'final_inputs',python,assertions=final)
            result = dict(task=task['task'],split=task['split'],arm=arm,sample=sample,model=client.model,
                          facts_version='v4',run_id=run_id,text='```python\n'+'\n'.join(final)+'\n```',assertions=final,
                          n_assertions=len(final),n_inputs=len(inputs['records']),n_valid_inputs=inputs['summary']['valid'],
                          llm_calls=len(calls),n_in=sum(c['n_in'] for c in calls),n_out=sum(c['n_out'] for c in calls),
                          seconds=sum(c['seconds'] for c in calls),calls=calls,selected_inputs=selected,
                          input_summary=inputs['summary'],round1_assertions=round1,
                          round2_strategy_requests=count,generator_attempts=attempts,stage1_summaries=stage1_summaries)
            if arm.endswith('-hybrid'):
                result.update(round1_input_summary=r1['summary'],missed_fact_indices=missed)
            if arm=='plain-hybrid':
                result['matched_strategy_requests']=results['concept-hybrid']['round2_strategy_requests']
                assert count==result['matched_strategy_requests']
            if arm=='toolinput': result['toolinput_removed']=flagged['summary']['removed']
            atomic_json(saved,result); results[arm]=result
            return result
        for arm in v4_prompts.ARMS: one(arm)
        return [results[a] for a in v4_prompts.ARMS]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        grouped = list(pool.map(work,[(t,s) for t in tasks for s in range(k)]))
    temp = out_dir/'gen.pending.jsonl'
    temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for group in grouped for r in group))
    temp.replace(out_dir/'gen.jsonl')
    print(f'v4 o0 generation ready: {len(tasks)*k*len(v4_prompts.ARMS)} rows',flush=True)
    return out_dir/'gen.jsonl'


def main():
    raise SystemExit('v30 CPU-only: inherited generation CLI disabled')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cmd',choices=('mine','facts','arms'))
    p.add_argument('--python',type=Path,default=os.environ.get('V4_PYTHON'))
    p.add_argument('--generator-python',type=Path,help='optional alias; must equal the v4 --python interpreter')
    p.add_argument('--precond-dir',type=Path,default=DATA_OUT / 'precond_qwen7b_v4')
    p.add_argument('--strategy-dir',type=Path,default=DATA_OUT / 'strategy_qwen7b')
    p.add_argument('--facts-dir',type=Path,default=DATA_OUT / 'facts_v4')
    p.add_argument('--tasks',type=Path,default=DATA_OUT / 'tasks_v4_all.json')
    p.add_argument('--out-dir',type=Path,default=DATA_OUT / 'gen2_qwen7b_v4')
    p.add_argument('--task-ids',type=int,nargs='+')
    p.add_argument('--workers',type=int,default=16); p.add_argument('--k',type=int,default=3)
    a = p.parse_args()
    if a.workers<1 or not 1<=a.k<1000: p.error('positive workers and K=1..999 required')
    python=v4_runtime.interpreter(a.python)
    for path in (a.precond_dir,a.strategy_dir,a.facts_dir,a.tasks,a.out_dir): safe_path(path)
    if a.cmd=='arms':
        tasks=json.loads(a.tasks.read_text())['tasks']
        if a.task_ids: tasks=[t for t in tasks if t['task'] in a.task_ids]
        task_sources([t['task'] for t in tasks])
        if a.task_ids and {t['task'] for t in tasks}!=set(a.task_ids): p.error('requested task absent from bundle')
        run(tasks,a.out_dir,python,a.generator_python,k=a.k,workers=a.workers)
    else:
        ids=a.task_ids or [int(n) for n in (HERE/'tasks.txt').read_text().split() if int(n) not in run_gen.DESIGN]
        tasks,he,pilot=task_sources(ids)
        if a.cmd=='mine': mine(tasks,Client(a.strategy_dir/'cache',workers=a.workers),a.precond_dir,a.strategy_dir,python,a.workers)
        else: facts(tasks,he,pilot,a.precond_dir,a.strategy_dir,a.facts_dir,a.tasks,python,a.workers)


if __name__=='__main__': main()
