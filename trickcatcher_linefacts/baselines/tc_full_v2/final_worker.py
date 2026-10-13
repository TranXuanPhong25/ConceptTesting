"""Final-budget TrickCatcher vote worker: PUT/base/variants only, no reference data."""
import ast
import copy
import json
import resource
import signal
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from trickcatcher_linefacts.baselines.tc_full_v2 import tc_full_worker as native
from trickcatcher_linefacts.pipelines.v11_fair_vp import scorer


def vote(job):
    entry=job['entry']; seconds=job['call_timeout']; atol=job['atol']
    status,put=native.load(job['put'],entry,job['load_timeout'])
    variants=[(v['index'],*native.load(v['src'],entry,job['load_timeout'])) for v in job['variants']]
    rows=[]
    for c in job['pool']:
        args=ast.literal_eval(c['input_repr'])
        run=lambda fn:native.timed(lambda:fn(*copy.deepcopy(args)),seconds)
        pout=run(put) if status=='ok' else (status,None)
        groups=[]; outcomes=[]
        for i,st,fn in variants:
            out=run(fn) if st=='ok' else (st,None)
            outcomes.append(dict(index=i,status=out[0]))
            if out[0]!='ok' or scorer.outcome_equal(pout,out,atol):continue
            group=next((g for g in groups if scorer.output_equal(g['value'],out[1],atol)),None)
            if group is None:
                group=dict(value=out[1],members=[]); groups.append(group)
            group['members'].append(i)
        row=dict(input_repr=c['input_repr'],put_status=pout[0],variant_outcomes=outcomes)
        if groups:
            best=max(groups,key=lambda g:len(g['members']))
            try:
                literal=repr(best['value']); ast.literal_eval(literal)
                row['assertion']=f"assert {entry}({', '.join(repr(a) for a in args)}) == {literal}"
            except (ValueError,SyntaxError):row['emit_error']='nonliteral output'
        rows.append(row)
    return dict(records=rows)


def main():
    resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20))
    resource.setrlimit(resource.RLIMIT_FSIZE,(8<<20,8<<20))
    signal.signal(signal.SIGALRM,native.expired)
    job=json.loads(Path(sys.argv[1]).read_text())
    # Base filtering uses the shared comparison, including embedded public helper assertions.
    if job['mode']=='filter':
        kept=[]; records=[]
        for variant in job['variants']:
            status,fn=native.load(variant['src'],job['entry'],job['load_timeout'])
            if status=='ok':
                def check():
                    ns={'__name__':'__tc_base__', '__fair_equal__':lambda a,b:scorer.output_equal(a,b,job['atol'])}
                    exec(scorer.assertion_code(job['base']),ns)
                    ns['check'](fn)
                status,_=native.timed(check,job['base_timeout'])
            records.append(dict(index=variant['index'],status=status))
            if status=='ok':kept.append(variant)
        result=dict(survivors=kept,base_results=records)
    else:result=vote(job)
    Path(sys.argv[2]).write_text(json.dumps(result,allow_nan=False))

if __name__=='__main__':main()
