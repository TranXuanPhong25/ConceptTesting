"""Post-freeze v11 ref/full and v34 VibePass silver+contract scoring."""
import ast
from collections import defaultdict
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from . import oracle_b01, evaluate, provenance
from .paths import REPO
from .llm_client import atomic_json
from .v4_runtime import immutable


def verify_freeze(root):
    protocol=root/'protocol.json'
    if protocol.exists() and json.loads(protocol.read_text())['sources']!=provenance.sources():
        raise ValueError('pipeline_source_drift')
    frozen=json.loads((root/'generation_frozen.json').read_text())
    for rel,h in frozen.items():
        if provenance.sha(root/rel)!=h: raise ValueError('generation_freeze_drift:'+rel)


def paired(rows,expected_tasks,k,*,partial=False):
    if len({r['task'] for r in rows})!=expected_tasks: raise ValueError('incomplete_scoring_tasks')
    arms=('plain','plain-hybrid','toolinput','placebo-hybrid','concept-hybrid','concept-hybrid-ft')
    keys={(r['task'],r['arm'],r['sample']) for r in rows}
    if len(keys)!=len(rows) or len(keys)!=expected_tasks*len(arms)*k:
        raise ValueError('incomplete_or_duplicate_scores')
    tasks=sorted({r['task'] for r in rows}); sums=defaultdict(int);fps=defaultdict(int)
    for r in rows:sums[r['task'],r['arm']]+=bool(r['detected']);fps[r['arm']]+=r['false_positive']
    pairs={}
    for control in ('placebo-hybrid','concept-hybrid','plain-hybrid','toolinput'):
        wins=sum(sums[t,'concept-hybrid-ft']>sums[t,control] for t in tasks)
        losses=sum(sums[t,'concept-hybrid-ft']<sums[t,control] for t in tasks)
        pairs[control]=dict(wins=wins,losses=losses,ties=len(tasks)-wins-losses,
                            false_positive_ft=fps['concept-hybrid-ft'],false_positive_control=fps[control],
                            rule_met=None if partial else wins>losses and fps['concept-hybrid-ft']<=fps[control])
    return dict(tasks=len(tasks),K=k,partial=partial,comparisons=pairs,primary=pairs['placebo-hybrid'],rows=rows)


def humaneval(run,root,*,client=None,k=3):
    """Invoke unchanged v11 native assertion evaluation and oracle routines."""
    verify_freeze(root)
    evaluate.evaluate(run/'tasks.json',run/'gen.jsonl',run/'eval.jsonl')
    out=run/'oracle';out.mkdir(exist_ok=True)
    old=REPO/'trickcatcher_linefacts/out/oracle_v7hyb'
    for name in ('ref_responses.json','post_responses.json'):
        source=provenance.verify_file(old/name)
        target=out/name
        if target.exists() and provenance.sha(target)!=provenance.sha(source):raise ValueError('oracle_response_drift')
        if not target.exists():shutil.copy2(source,target)
    oracle_b01.collect(run,out)
    ex=oracle_b01.execute(run,out,workers=1)
    tasks,rows=oracle_b01.load_run(run)
    reports={}
    def compute(oracle,jd):
        results=[]
        for row in rows:
            t=str(row['task']);det=False;fp=0;emitted=0;seen=set()
            if t not in ex:raise ValueError('missing_oracle_task:'+t)
            for a in row['asserts']:
                call=oracle_b01.call_of(a['src'],tasks[row['task']]['entry'])
                if call in seen or call is None:continue
                seen.add(call);rec=ex[t]['calls'].get(call,{})
                emit,cok,pok=oracle_b01.decide(oracle,rec,jd.get((t,call)),oracle_b01.expected_of(a['src']),a)
                valid=rec.get('valid',True)
                emitted+=bool(emit);fp+=bool(emit and (not cok or not valid));det|=bool(emit and cok and not pok and valid)
            results.append(dict(task=row['task'],arm=row['arm'],sample=row['sample'],detected=det,false_positive=fp,
                                emitted=emitted,abstentions=len(seen)-emitted))
        return paired(results,len(tasks),k,partial=(root/'partial_status.json').exists())
    reports['ref']=compute('ref',{})
    atomic_json(run/'score_ref.json',reports['ref'])
    if client is not None:
        with patch.object(oracle_b01,'Client',return_value=client):jd=oracle_b01.judges(ex,run,out,workers=1)
    else:jd=oracle_b01.judges(ex,run,out,use_llm=False)
    reports['full']=compute('full',jd)
    atomic_json(run/'score.json',reports)
    return reports


def vibepass(run,root,*,k=3):
    verify_freeze(root)
    # Use the frozen v29/v34 reference executor and exact typed comparison.
    # Imported only after generation freeze; it writes under run/reference.
    from ..v34_ftplacebo.flow_run import Reference,parse_expected,same
    from .datasets import VP_ROOT
    from types import SimpleNamespace
    reference=Reference(SimpleNamespace(root=run))
    data=provenance.verify_file(VP_ROOT/'humaneval_mbpp_plus.jsonl')
    plus={int(r['task_id'].split('/')[1]):r for r in map(json.loads,data.read_text().splitlines())}
    bundles={t['task']:t for t in json.loads((run/'tasks.json').read_text())['tasks']}
    results=[]
    for row in map(json.loads,(run/'gen.jsonl').read_text().splitlines()):
        n=row['task'];h=plus[n];t=bundles[n]
        case=dict(reference=dict(kind='canonical',source=h['prompt']+h['canonical_solution'],entry=h['entry_point'],
                                 contract=h['prompt']+h['contract']+'\n    pass\n'))
        det=False;fp=0;unknown=0;invalid=0
        for assertion in row['assertions']:
            try:
                call=ast.parse(assertion).body[0].test
                fn=call.left
                if not isinstance(call,ast.Compare) or len(call.ops)!=1 or not isinstance(call.ops[0],ast.Eq) or not isinstance(fn,ast.Call) or not isinstance(fn.func,ast.Name) or fn.func.id!=t['entry'] or fn.keywords:
                    raise ValueError('unsupported_assertion')
                literal=repr(tuple(ast.literal_eval(a) for a in fn.args))
                expected=parse_expected(ast.unparse(call.comparators[0]))
                if expected is None:raise ValueError('unparsed_expected')
            except (ValueError,SyntaxError,AttributeError):unknown+=1;continue
            r=reference._run(t['put'],t['entry'],literal)
            if r.get('status')=='ok':actual=parse_expected(r.get('output_repr',''))
            elif r.get('status')=='exception':actual=parse_expected('exception:'+r['exception_type'])
            else:unknown+=1;continue
            if actual is None:unknown+=1;continue
            if not reference.contract_valid(case,literal):
                invalid+=1;fp+=not same(expected,actual);continue
            truth=reference(case,literal)
            if truth is None:unknown+=1;continue
            disc=not same(actual,truth)
            det|=disc and same(expected,truth)
            # Exact v34 convention: discrepancy with wrong expected is separate,
            # not a false alarm when the PUT is already wrong on this input.
            if not disc and not same(expected,actual):fp+=1
        results.append(dict(task=n,arm=row['arm'],sample=row['sample'],detected=bool(det),false_positive=fp,
                            contract_invalid=invalid,unscored=unknown))
    report=paired(results,len(bundles),k,partial=(root/'partial_status.json').exists());atomic_json(run/'score.json',report);return report
