"""V4 o0 assertion scoring, diagnostic false alarms, and paired assertion budgets."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast
import collections
import contextlib
import io
import json
import math
from pathlib import Path
from . import gen_inputs, preconditions, v4_prompts, v4_runtime
from .llm_client import atomic_json

COMPARISONS = [('concept','plain')] + [('concept-hybrid',a) for a in
              ('plain-hybrid','placebo-hybrid','concept','toolinput','gen-plain')]
CLASSES = ('contract-invalid','mined-invalid','canonical-raises','copied-the-bug',
           'type-format-mismatch','float-tolerance','other-wrong-oracle')



def _short(text, cap=2000):
    # v7 amendment: stored reprs of very large inputs are truncated (8 MB sandbox output limit); scoring is unaffected
    return text if len(text) <= cap else text[:cap] + f'...[{len(text)} chars]'

def validity(fn, args, boolean=False):
    from .tracer import alarm, dcopy
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(1):
            value = fn(*dcopy(args[0]),**dcopy(args[1]))
        return value is True if boolean else True
    except BaseException:
        return False


def expected_value(src, entry):
    node = ast.parse(src).body[0].test
    if not isinstance(node,ast.Compare) or len(node.ops)!=1 or not isinstance(node.ops[0],ast.Eq):
        raise ValueError('non-equality assertion')
    left,right = node.left,node.comparators[0]
    if isinstance(right,ast.Call) and isinstance(right.func,ast.Name) and right.func.id==entry:
        left,right=right,left
    if not isinstance(left,ast.Call) or not isinstance(left.func,ast.Name) or left.func.id!=entry:
        raise ValueError('nonliteral oracle assertion')
    return ast.literal_eval(right)


def false_alarm(src, entry, calls, mined, contract, put, canon, unordered=False):
    from .tracer import call, same
    diagnostics = []
    for args in calls:
        m,c = validity(mined,args,True),validity(contract,args)
        pout,cout = call(put,args),call(canon,args)
        diagnostics.append(dict(input_repr=_short(repr(args)),mined_valid=m,contract_valid=c,
                                canonical_status=cout[0],put_status=pout[0]))
    if any(not r['contract_valid'] for r in diagnostics): return 'contract-invalid',diagnostics
    if any(not r['mined_valid'] for r in diagnostics): return 'mined-invalid',diagnostics
    if any(r['canonical_status']!='ok' for r in diagnostics): return 'canonical-raises',diagnostics
    if not calls: return 'other-wrong-oracle',diagnostics
    try: expected=expected_value(src,entry)
    except (SyntaxError,ValueError,TypeError): return 'other-wrong-oracle',diagnostics
    pout,cout = call(put,calls[0]),call(canon,calls[0])
    if pout[0]=='ok' and same(expected,pout[1]): return 'copied-the-bug',diagnostics
    actual=cout[1]
    if type(expected) is not type(actual): return 'type-format-mismatch',diagnostics
    if isinstance(expected,str) and expected.strip(' \'"')==str(actual).strip(' \'"'):
        return 'type-format-mismatch',diagnostics
    if unordered and isinstance(expected,(list,tuple)) and isinstance(actual,(list,tuple)):
        if collections.Counter(map(repr,expected))==collections.Counter(map(repr,actual)):
            return 'type-format-mismatch',diagnostics
    def close(a,b):
        if isinstance(a,(int,float)) and isinstance(b,(int,float)) and (isinstance(a,float) or isinstance(b,float)):
            return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-6)
        return isinstance(a,(list,tuple)) and isinstance(b,type(a)) and len(a)==len(b) and all(close(x,y) or x==y for x,y in zip(a,b))
    if close(expected,actual): return 'float-tolerance',diagnostics
    return 'other-wrong-oracle',diagnostics


def guard_alarm():
    # A SIGALRM delivered just after its timer was cancelled used to raise inside coverage.py's locked bookkeeping and
    # leave the process waiting on that lock forever (v4c evaluation, task 41). Late signals are now ignored.
    import signal; from . import tracer
    armed = [False]
    @contextlib.contextmanager
    def alarm(t):
        armed[0] = True; signal.setitimer(signal.ITIMER_REAL, t)
        try:
            yield
        finally:
            armed[0] = False; signal.setitimer(signal.ITIMER_REAL, 0)
    def handler(sig, frame):
        if armed[0]: raise tracer.Timeout()
    signal.signal(signal.SIGALRM, handler)
    tracer.alarm = alarm


def worker(job, directory):
    guard_alarm()
    from .tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module, same
    from . import spec_facts
    from .v4_tools import Coverage
    task=job['task']; entry=task['entry']; facts=task['concept_meta']
    pg=load_module(task['put']); cg=load_module(job['canon']); put,canon=pg[entry],cg[entry]
    mined=preconditions.load_predicate(task['mined_valid_src'],'valid')
    contract=load_module(job['contract_src'])[entry]
    code,_=instrument(task['put']); iput=load_module(code,HOOKS)[entry]
    coverage=Coverage(task['put'],entry,directory)
    mutants={i:load_module(f['mutant_src'])[entry] for i,f in enumerate(facts) if f['kind']=='MUTANT'}
    doc=preconditions.specification(task)[1].lower()
    unordered=any(s in doc for s in ('any order','order does not matter','unordered','ignore order'))
    def run_assert(src,fn,g):
        calls=[]
        def wrapped(*a,**k):
            calls.append((dcopy(a),dcopy(k))); return fn(*a,**k)
        ns=dict(g); ns[entry]=wrapped
        try:
            with contextlib.redirect_stdout(io.StringIO()),alarm(5): exec('import math\n'+src,ns)
            return 'ok',calls
        except AssertionError: return 'fail',calls
        except BaseException as exc: return type(exc).__name__,calls
    rows=[]
    # Inputs whose assertion already timed out on the PUT (5 s) are not traced again: tracing them only repeats the
    # same timeout many times (task 41, n = 12345 with an n^2 PUT). Detection uses the assertion statuses, unchanged.
    slow=set(); memo={}
    def observe(args):
        # Each distinct input is traced once per task (the same inputs recur across arms and samples).
        key=repr(args)
        if key not in memo:
            pout=call(put,args)
            # v7 spec facts: hit = input-class membership of the argument (no trace needed, also for timed-out inputs)
            spec=lambda f: spec_facts.in_class(f['input_class']['cls'],args[0][f['input_class']['param']])
            if pout[0]=='timeout':   # over the step budget: not traced (no hits), see amendment 5
                memo[key]=(pout,[spec(f) if 'input_class' in f else False for f in facts])
            else:
                tr=coverage.trace(iput,args)
                memo[key]=(pout,[spec(f) if 'input_class' in f else fact_hit(f,tr,pout,call(mutants[i],args) if i in mutants else None) for i,f in enumerate(facts)])
        return memo[key]
    for row in job['rows']:
        scored=[]; unique={}
        for src in row['assertions']:
          try:
            cst,ccalls=run_assert(src,canon,cg); pst,pcalls=run_assert(src,put,pg)
            calls=list({repr(a):a for a in pcalls+ccalls}.values())
            if pst=='Timeout': slow.update(repr(a) for a in pcalls)
            hits=[False]*len(facts)
            for args in calls[:20]:
                unique[repr(args)]=args
                if not validity(mined,args,True) or repr(args) in slow: continue
                hits=[h or x for h,x in zip(hits,observe(args)[1])]
            result=dict(src=src,canon=cst,put=pst,hits=hits)
            if cst!='ok':
                cls,diagnostics=false_alarm(src,entry,calls,mined,contract,put,canon,unordered)
                result.update(false_alarm_class=cls,false_alarm_inputs=diagnostics)
            scored.append(result)
          except MemoryError:
            # mutref amendment: an assertion whose input is too large to copy/repr/trace (e.g. task 87,
            # [[1]*1000 for _ in range(1000)]*1000) is scored as crashing on both programs (a false alarm, no hits)
            # instead of killing the whole task's scoring sandbox.
            scored.append(dict(src=src,canon='MemoryError',put='MemoryError',hits=[False]*len(facts)))
        inputs=[]
        for args in unique.values():
          try:
            valid=validity(mined,args,True); contract_valid=validity(contract,args)
            r=dict(input_repr=_short(repr(args[0])),kwargs_repr=_short(repr(args[1])),valid=valid,contract_valid=contract_valid,
                   hits=[False]*len(facts),bug_revealing=None,canonical_scored=False)
            if valid and repr(args) in slow:
                cout=call(canon,args)
                r.update(put_status='Timeout',canon_status=cout[0],canonical_scored=cout[0]=='ok',
                         bug_revealing=True if cout[0]=='ok' else None,trace_skipped=True)
            elif valid:
                (pout,hits),cout=observe(args),call(canon,args)
                r.update(put_status=pout[0],canon_status=cout[0],canonical_scored=cout[0]=='ok',
                         bug_revealing=(pout[0]!='ok' or not same(pout[1],cout[1])) if cout[0]=='ok' else None,
                         hits=hits)
            inputs.append(r)
          except MemoryError:   # mutref amendment (see above): unscorable oversized input
            inputs.append(dict(input_repr='<oversized>',kwargs_repr='{}',valid=False,contract_valid=False,hits=[False]*len(facts),
                               bug_revealing=None,canonical_scored=False,put_status='MemoryError'))
        rows.append({key:value for key,value in row.items() if key not in ('text','assertions','asserts')} |
                    dict(asserts=scored,input_metrics=inputs,n_assertions=len(scored),n_inputs=len(inputs)))
    return rows


def evaluate(tasks_path,gen_path,eval_path,python=None):
    from .evaluate import HEP, extract_asserts
    tasks={t['task']:t for t in json.loads(Path(tasks_path).read_text())['tasks']}
    rows=[json.loads(line) for line in Path(gen_path).read_text().splitlines()]
    he={int(r['task_id'].split('/')[1]):r for r in map(json.loads,HEP.open())}
    contracts=gen_inputs.load_contracts()
    if set(r['task'] for r in rows)-set(tasks): raise ValueError('generation tasks absent from bundle')
    results=[]; eval_path=Path(eval_path)
    for n,t in sorted(tasks.items()):
        if preconditions.sha(t['mined_valid_src'])!=t['valid_sha256']: raise ValueError('validator hash mismatch')
        # Raw generator candidates (up to 24 MB for task 68) stay in gen.jsonl; scoring needs only their count.
        drop=lambda g:{k:v for k,v in g.items() if k!='candidates'}|dict(n_candidates=len(g.get('candidates',[])))
        slim=lambda r:dict(r,generator_attempts=[{k:(drop(v) if k=='generated' and isinstance(v,dict) else v)
                                                   for k,v in a.items()} for a in r.get('generator_attempts',[])])
        group=[dict(slim(r),assertions=r.get('assertions',extract_asserts(r['text']))) for r in rows if r['task']==n]
        if not group: continue
        h=he[n]
        job=dict(task=t,rows=group,canon=h['prompt']+h['canonical_solution'],contract_src=contracts[n]['contract_src'])
        for attempt in range(3):   # a stuck sandbox is retried (amendment 5); scoring itself is deterministic
            try:
                results += v4_runtime.isolated('evaluate',job,eval_path.parent/(eval_path.stem+'_jobs')/str(n),python,600); break
            except RuntimeError:
                if attempt==2: raise
                print(f'evaluate task {n}: sandbox failed (attempt {attempt+1}), retrying',flush=True)
    eval_path.parent.mkdir(parents=True,exist_ok=True)
    eval_path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results))


def detects(assertions):
    return any(a['canon']=='ok' and a['put']!='ok' for a in assertions)


def comparison(rows,first,second,matched=False):
    from .evaluate import sign_p
    indexed={(r['task'],r['sample'],r['arm']):r for r in rows}; scores=collections.defaultdict(lambda:[0,0]); budgets=[]
    for task,sample in sorted({(r['task'],r['sample']) for r in rows}):
        a,b=indexed[task,sample,first]['asserts'],indexed[task,sample,second]['asserts']
        m=min(len(a),len(b)); budgets.append(dict(task=task,sample=sample,m=m))
        if matched: a,b=a[:m],b[:m]
        scores[task][0]+=detects(a); scores[task][1]+=detects(b)
    win=sum(a>b for a,b in scores.values()); loss=sum(a<b for a,b in scores.values())
    return dict(first=first,second=second,matched=matched,wins=win,losses=loss,sign_p=sign_p(win,loss),
                detecting_samples=[sum(s[i] for s in scores.values()) for i in (0,1)],budgets=budgets)


def report(tasks_path,eval_path):
    tasks={t['task']:t for t in json.loads(Path(tasks_path).read_text())['tasks']}
    rows=[json.loads(line) for line in Path(eval_path).read_text().splitlines()]
    if not rows: print('No evaluated rows.'); return
    k=max(r['sample'] for r in rows)+1
    keys=[(r['task'],r['arm'],r['sample']) for r in rows]
    expected={(n,a,s) for n in tasks for a in v4_prompts.ARMS for s in range(k)}
    if len(set(keys))!=len(keys) or set(keys)!=expected: raise ValueError('v4 report requires complete task x seven-arm x K cohort')
    output={}
    for split in ('dev','pilot','heldout'):
        for cohort in ('all','without doc_fail','doc_fail only'):
            ids={n for n,t in tasks.items() if t['split']==split and
                 (cohort=='all' or bool(t['doc_fail'])==(cohort=='doc_fail only'))}
            selected=[r for r in rows if r['task'] in ids]
            if not selected: continue
            print(f'\n{split} / {cohort}: {len(ids)} tasks, K={k}'+(' (primary)' if split=='dev' and cohort=='all' else ''))
            print('arm detect/sample any-of-K asserts/sample detects/assert false-alarm delivery valid-input bug-input calls tokens-in tokens-out')
            arms={}
            for arm in v4_prompts.ARMS:
                rs=[r for r in selected if r['arm']==arm]; asserts=[a for r in rs for a in r['asserts']]
                inputs=[i for r in rs for i in r['input_metrics']]; valid=[i for i in inputs if i['valid']]
                scored=[i for i in valid if i.get('canonical_scored')]
                nf=sum(len(tasks[r['task']]['concept_meta']) for r in rs)
                reached=sum(any(a['hits'][i] for a in r['asserts']) for r in rs for i in range(len(tasks[r['task']]['concept_meta'])))
                kinds=collections.defaultdict(lambda:[0,0])
                for r in rs:
                    good=[i for i in r['input_metrics'] if i['valid']]
                    for i,f in enumerate(tasks[r['task']]['concept_meta']):
                        kind='MUTANT-X' if f.get('extended') else f['kind']
                        kinds[kind][0]+=sum(x['hits'][i] for x in good); kinds[kind][1]+=len(good)
                m=dict(detect_sample=sum(detects(r['asserts']) for r in rs)/k,
                       any_of_k=sum(any(detects(r['asserts']) for r in rs if r['task']==n) for n in ids),
                       assertions_per_sample=len(asserts)/len(rs),
                       detection_per_assertion=sum(a['canon']=='ok' and a['put']!='ok' for a in asserts)/max(1,len(asserts)),
                       false_alarm=sum(a['canon']!='ok' for a in asserts)/max(1,len(asserts)),delivery=reached/max(1,nf),
                       inputs=len(inputs),valid_inputs=len(valid),bug_inputs=sum(bool(i['bug_revealing']) for i in scored),
                       scored_inputs=len(scored),unscored_inputs=len(valid)-len(scored),calls=sum(r['llm_calls'] for r in rs),
                       n_in=sum(r['n_in'] for r in rs),n_out=sum(r['n_out'] for r in rs),seconds=sum(r['seconds'] for r in rs),
                       false_alarm_classes={c:sum(a.get('false_alarm_class')==c for a in asserts) for c in CLASSES},hits_by_kind=dict(kinds),
                       strategy_requests=sum(r.get('round2_strategy_requests',0) for r in rs),
                       toolinput_removed=sum(r.get('toolinput_removed',0) for r in rs),
                       raw_stage1_valid=sum(s['raw_valid'] for r in rs for s in r.get('stage1_summaries',[])),
                       raw_stage1_candidates=sum(s['raw_candidates'] for r in rs for s in r.get('stage1_summaries',[])),
                       requested_stage1_draws=sum(s['requested_draws'] for r in rs for s in r.get('stage1_summaries',[])),
                       retries=sum(bool(a.get('retry')) for r in rs for a in r.get('generator_attempts',[])))
                arms[arm]=m
                print(f"{arm:16s} {m['detect_sample']:.2f} {m['any_of_k']} {m['assertions_per_sample']:.2f} {m['detection_per_assertion']:.3f} {m['false_alarm']:.3f} {m['delivery']:.3f} {len(valid)}/{len(inputs)} {m['bug_inputs']}/{len(scored)} {m['calls']} {m['n_in']} {m['n_out']}")
                print('  false-alarm classes: '+json.dumps(m['false_alarm_classes'])+'; valid-input hits by kind: '+json.dumps(dict(kinds)))
                print(f"  raw stage-1 valid/candidates/requested={m['raw_stage1_valid']}/{m['raw_stage1_candidates']}/{m['requested_stage1_draws']}; requests={m['strategy_requests']}; retries={m['retries']}; invalid witnesses={m['toolinput_removed']}; unscored inputs={m['unscored_inputs']}; seconds={m['seconds']:.3f}")
            comparisons=[comparison(selected,a,b,matched) for a,b in COMPARISONS for matched in (False,True)]
            for c in comparisons:
                print(f"  {'matched' if c['matched'] else 'raw'} {c['first']} vs {c['second']}: {c['wins']}/{c['losses']}, sign p={c['sign_p']:.6g}")
            output[split+'/'+cohort]=dict(arms=arms,comparisons=comparisons)
    atomic_json(Path(eval_path).with_suffix('.metrics.json'),output)
    return output
