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
from . import fair_generation as fair
from .run_v4 import classify, assertions, merge
from .transport import user_feedback


def run(tasks, out_dir, python, generator_python=None, *, client, k=3, workers=1):
    out_dir = Path(out_dir).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    from .provenance import sources
    all_tasks=tasks
    tasks=[t['baseline'] for t in all_tasks]
    variants={t['baseline']['task']:t['combined'] for t in all_tasks}
    ARMS=('concept-hybrid','concept-hybrid-ft')
    exported=tuple(CONFIG['combined']['arms'])
    python = v4_runtime.interpreter(python)
    generator_python = Path(generator_python or python).absolute()
    if generator_python != python:
        raise ValueError('every v4 sandbox, including gen-plain, must use --python/V4_PYTHON')
    for t in tasks:
        if t.get('facts_version') != 'v4' or preconditions.sha(t['strategy_src']) != t['strategy_sha256'] or preconditions.sha(t['mined_valid_src']) != t['valid_sha256']:
            raise ValueError('v4 bundle hash/version mismatch')
        if any('mutant_src' not in f for key in ('concept_meta','placebo_meta') for f in t[key] if f['kind']=='MUTANT'):
            raise ValueError('shown mutants require full sources for post-hoc oracle_b01')
    manifest = dict(version='v4-o0', pipeline_version=CONFIG['VERSION'], facts_version='v4', model=client.model, k=k, arms=exported,
                    tasks_sha256=run_gen._digest(all_tasks), sources=sources(), tools=v4_runtime.VERSIONS,
                    prereg_sha256=preconditions.sha((HERE/'PREREG_V83.md').read_bytes()), python=str(python),
                    generator_python=str(generator_python), n_round2=100, per_fact=2, templates=gen_prompts.TEMPLATE_SHA256)
    if any(CONFIG.get(key) for key in ('strict_round2','placebo_matched','caps','shared_scorer')):
        manifest['fair_flags']={key:CONFIG.get(key,False) for key in ('strict_round2','placebo_matched','caps','shared_scorer')}
    v4_runtime.immutable(out_dir/'manifest.json', manifest)
    v4_runtime.immutable(out_dir/'tasks.json', dict(facts_version='v4', tasks=tasks, combined_tasks=list(variants.values())))
    run_id = run_gen._digest(manifest)

    def work(pair):
        baseline, sample = pair
        task=baseline
        root = out_dir/'artifacts'/str(task['task'])/str(sample); root.mkdir(parents=True, exist_ok=True)
        results = {}
        def one(arm):
            task=variants[baseline['task']] if arm in ('concept-hybrid-ft','toolinput') else baseline
            is_hybrid=arm.endswith('-hybrid') or arm=='concept-hybrid-ft'
            def seed(stage=0,request=0,retry=0):
                if arm=='concept-hybrid' and stage==0:
                    return v4_prompts.seed(task['task'],'concept',sample,stage,request,retry)
                if arm=='concept-hybrid-ft':
                    return v4_prompts.seed(task['task'],'concept-hybrid',sample,stage,request,retry)+100000000
                return v4_prompts.seed(task['task'],arm,sample,stage,request,retry)
            directory = root/arm; directory.mkdir(exist_ok=True)
            saved = directory/'result.json'
            if saved.exists():
                result = json.loads(saved.read_text())
                if result['run_id'] != run_id: raise ValueError('sample manifest mismatch')
                results[arm] = result; return result
            calls, selected, attempts, stage1_summaries = [], [], [], []
            round1 = []; count = 0; inherited_dropped = 0; strict_missing = 0; dropped_round2_inputs = 0
            def query(messages, stage, request=0, retry=0, label='response', strategy=False):
                if CONFIG.get('caps') and len(calls) >= fair.MAX_CALLS:
                    raise RuntimeError('sample LLM call budget exhausted')
                messages=user_feedback(messages)
                atomic_json(directory/(label+'_prompt.json'), messages)
                response = client.chat(messages, seed(stage,request,retry),
                                       **(dict(temperature=0,top_p=1,max_tokens=4096) if strategy else {}))
                atomic_json(directory/(label+'.json'),response); calls.append(response)
                return response['text']
            if arm in ('plain','concept','placebo-hybrid','concept-hybrid','concept-hybrid-ft'):
                kind = 'placebo' if arm=='placebo-hybrid' else 'concept' if arm in ('concept-hybrid','concept-hybrid-ft') else arm
                round1 = assertions(query(gen_prompts.messages(*prompts.build(kind,task)),0,label='round1'))
            elif arm in ('concept-hybrid','plain-hybrid'):
                original = results['concept' if arm=='concept-hybrid' else 'plain']
                round1 = original['assertions'][:]
                # Attribute the same logical request/tokens to both arms; cache makes its physical request shared.
                calls += original['calls']
                inherited_dropped = original.get('dropped_assertions', 0)
            if CONFIG.get('caps'):
                round1, round1_dropped = fair.cap_assertions(round1)
                inherited_dropped += round1_dropped
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
            elif is_hybrid:
                shown = task['concept_meta'] if arm in ('concept-hybrid','concept-hybrid-ft') else task['placebo_meta'] if arm=='placebo-hybrid' else []
                r1 = classify(task,directory/'round1_inputs',python,assertions=round1,shown=shown)
                missed = [i for i,h in enumerate(r1['summary']['shown_hit_counts']) if not h]
                matched = arm=='plain-hybrid' or (arm=='placebo-hybrid' and CONFIG.get('placebo_matched'))
                budget = results['concept-hybrid-ft']['round2_strategy_requests'] if matched else len(missed)
                if CONFIG.get('caps'):
                    budget = min(budget, max(0, fair.MAX_CALLS-len(calls)-1))
                for request in range(budget):
                    if matched and count >= budget: break
                    if CONFIG.get('caps') and len(calls) >= fair.MAX_CALLS-1: break
                    fact_index = ((missed or list(range(len(shown))))[request % len(missed or shown)]
                                  if arm=='placebo-hybrid' and CONFIG.get('placebo_matched') and shown
                                  else None if arm=='placebo-hybrid' and CONFIG.get('placebo_matched')
                                  else missed[request] if arm!='plain-hybrid' else None)
                    fact = shown[fact_index] if fact_index is not None else None
                    messages = v4_prompts.hybrid_messages(task,fact,round1)
                    for retry in range(1 if arm=='plain-hybrid' else 2):
                        if matched and count >= budget: break
                        if CONFIG.get('caps') and len(calls) >= fair.MAX_CALLS-1: break
                        d = directory/f'request_{request}_{retry}'; d.mkdir(exist_ok=True)
                        raw = query(messages,1,request,retry,f'strategy_{request}_{retry}',True); count += 1
                        error = None; generated = None; flagged = None
                        try:
                            code = v4_strategies.checked(raw); (d/'strategy.py').write_text(code)
                            generated = v4_strategies.draws(code,task,d,python,
                                seed(3,request,retry))
                            flagged = classify(task,d,python,candidates=generated['candidates'],shown=[fact] if fact else [],requested_draws=100)
                            stage1_summaries.append(flagged['summary'])
                            good = [r for r in flagged['records'] if r['valid'] and (fact is None or r['shown_hits'][0])]
                            if not good: error = 'No valid input exercised the fact.' if fact else 'No valid inputs returned.'
                            if generated['nonliteral'] or generated['wrong_arity'] or generated['errors']:
                                error = json.dumps({key:generated[key] for key in ('nonliteral','wrong_arity','errors')})
                        except (SyntaxError,ValueError,RuntimeError) as exc:
                            good = []; error = f'{type(exc).__name__}: {exc}'
                        picked = random.Random(seed(3,request,retry)).sample(good,min(2,len(good))) if not error else []
                        attempts.append(dict(request=request,retry=retry,fact_index=fact_index,
                                             error=error,selected=picked,generated=generated,
                                             summary=flagged['summary'] if flagged else None))
                        selected += picked
                        if not raw.strip() or not error or retry==1 or arm=='plain-hybrid': break
                        messages += [dict(role='assistant',content=raw),dict(role='user',content=v4_prompts.RETRY.format(error=error))]
                selected = list({r['input_repr']:r for r in selected}.values())
                if CONFIG.get('strict_round2'):
                    selected = fair.unseen_inputs(selected, round1, task['entry'])
                    if CONFIG.get('caps'):
                        capacity = max(0, fair.MAX_ASSERTIONS-len(round1))
                        dropped_round2_inputs = max(0,len(selected)-capacity)
                        selected = selected[:capacity]
                    injected = assertions(query(gen_prompts.strict_oracle_messages(task,selected),2,label='oracle')) if selected else []
                    final, strict_missing = fair.strict_assertions(round1, selected, injected, task['entry'])
                else:
                    injected = assertions(query(gen_prompts.oracle_messages(task,selected),2,label='oracle')) if count else []
                    final = merge(round1,injected)
            else:
                final = round1
            empty_answers=sum(not c['text'].strip() for c in calls)
            if empty_answers: final=[]
            dropped = 0
            if CONFIG.get('caps'):
                final, dropped = fair.cap_assertions(final)
            inputs = classify(task,directory/'final_inputs',python,assertions=final)
            result = dict(task=task['task'],split=task['split'],arm=arm,sample=sample,model=client.model,
                          facts_version='v4',run_id=run_id,empty_answer_count=empty_answers,arm_failed=bool(empty_answers),text='```python\n'+'\n'.join(final)+'\n```',assertions=final,
                          n_assertions=len(final),n_inputs=len(inputs['records']),n_valid_inputs=inputs['summary']['valid'],
                          llm_calls=len(calls),n_in=sum(c['n_in'] for c in calls),n_out=sum(c['n_out'] for c in calls),
                          seconds=sum(c['seconds'] for c in calls),calls=calls,selected_inputs=selected,
                          input_summary=inputs['summary'],round1_assertions=round1,
                          round2_strategy_requests=count,generator_attempts=attempts,stage1_summaries=stage1_summaries)
            if CONFIG.get('caps'):
                result.update(dropped_assertions=dropped+inherited_dropped, call_cap=fair.MAX_CALLS, assertion_cap=fair.MAX_ASSERTIONS)
            if CONFIG.get('strict_round2') and is_hybrid:
                result.update(strict_round2=True, strict_missing_expected=strict_missing,
                              dropped_round2_inputs=dropped_round2_inputs)
            if is_hybrid:
                result.update(round1_input_summary=r1['summary'],missed_fact_indices=missed)
            if arm=='plain-hybrid' or (arm=='placebo-hybrid' and CONFIG.get('placebo_matched')):
                result['matched_strategy_requests']=results['concept-hybrid-ft']['round2_strategy_requests']
                assert count==result['matched_strategy_requests']
            if arm=='toolinput': result['toolinput_removed']=flagged['summary']['removed']
            atomic_json(saved,result); results[arm]=result
            return result
        for arm in ARMS: one(arm)
        return [results[a] for a in exported]
    if workers != 1: raise ValueError('task_major_serial_dispatch_required')
    grouped=[]
    for t in tasks:
        for sample in range(k):
            grouped.append(work((t,sample)))
        atomic_json(out_dir/'completed_tasks.json', [x['task'] for x in tasks[:tasks.index(t)+1]])
    temp = out_dir/'gen.pending.jsonl'
    temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for group in grouped for r in group))
    temp.replace(out_dir/'gen.jsonl')
    print(f'v4 o0 generation ready: {len(tasks)*k*len(exported)} rows',flush=True)
    return out_dir/'gen.jsonl'

