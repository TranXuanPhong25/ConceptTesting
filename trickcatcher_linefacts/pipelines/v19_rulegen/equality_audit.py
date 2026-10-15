"""Score every cached generation assertion twice on identical CPU observations.

This avoids attributing hash ordering or deadline changes to float tolerance.
Generated code executes only in the existing network-isolated sandbox.
"""
import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
    __package__='trickcatcher_linefacts.pipelines.'+Path(__file__).resolve().parent.name
import contextlib
import copy
import io
import json
import resource
from . import scorer


def worker(job_path, output_path):
    from .v4_evaluation import guard_alarm
    guard_alarm()
    from .tracer import alarm, load_module, Timeout
    resource.setrlimit(resource.RLIMIT_AS,(1<<30,1<<30))
    job=json.loads(Path(job_path).read_text())
    entry=job['entry']; atol=job['atol']
    modules={kind:load_module(job[kind]) for kind in ('put','canon')}
    functions={kind:ns[entry] for kind,ns in modules.items()}
    # Each literal input is executed once per function, so both verdicts see
    # exactly the same result, exception type or timeout.
    observations={kind:{} for kind in modules}
    results={}; changes=[]; assertions=0
    for row in job['rows']:
        for index,source in enumerate(row['assertions']):
            assertions+=1
            if source not in results:
                scores={}; float_changes=[]
                for kind in modules:
                    def wrapped(*args,**kwargs):
                        key=repr((args,kwargs)); memo=observations[kind]
                        if key not in memo:
                            try:
                                with alarm(5): value=functions[kind](*copy.deepcopy(args),**copy.deepcopy(kwargs))
                                memo[key]=(True,copy.deepcopy(value))
                            except BaseException as exc: memo[key]=(False,exc)
                        ok,value=memo[key]
                        if not ok: raise value
                        return copy.deepcopy(value)
                    def equal(a,b):
                        old=bool(a==b); new=scorer.output_equal(a,b,atol)
                        if old != new:
                            assert scorer.contains_float(a) or scorer.contains_float(b), 'non-float comparison changed'
                            float_changes.append(dict(function=kind,left=repr(a)[:1000],right=repr(b)[:1000],atol=atol))
                        return new
                    def run(shared):
                        ns=dict(modules[kind]); ns[entry]=wrapped; ns['__fair_equal__']=equal
                        try:
                            with contextlib.redirect_stdout(io.StringIO()),alarm(5):
                                exec('import math',ns)
                                exec(scorer.assertion_code(source) if shared else source,ns)
                            return 'ok'
                        except AssertionError: return 'fail'
                        except Timeout: return 'Timeout'
                        except BaseException as exc: return type(exc).__name__
                    old,new=run(False),run(True)
                    scores[kind]=(old,new)
                changed=any(a!=b for a,b in scores.values())
                if changed: assert float_changes, 'verdict changed without a float comparison'
                results[source]=(scores,float_changes,changed)
            scores,evidence,changed=results[source]
            if changed:
                changes.append(dict(task=job['task'],arm=row['arm'],sample=row['sample'],index=index,
                                    assertion=source,verdicts=scores,float_comparisons=evidence))
    Path(output_path).write_text(json.dumps(dict(assertions=assertions,unique_assertions=len(results),changes=changes)))


if __name__=='__main__': worker(*sys.argv[1:])
