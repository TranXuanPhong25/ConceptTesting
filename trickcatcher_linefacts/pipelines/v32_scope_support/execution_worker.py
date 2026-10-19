"""One ordinary OR traced execution in a clean isolated process. No semantic matcher."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import resource
import signal
import sys
if not __package__:
    here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[2]));__package__='trickcatcher_linefacts.pipelines.'+here.name
from .chain_inputs import check_topology,typed_value,parse_literal


class Deadline(Exception):pass
class TraceLimit(Exception):pass


def signature(value):
    try:
        check_topology(value,max_nodes=2048,max_items=512)
        text=repr(typed_value(value))
        return text if len(text.encode('utf-8'))<=4096 else None
    except (ValueError,RecursionError,TypeError):return None


def run(job):
    args=ast.literal_eval(job['input_repr']);check_topology(args);args=copy.deepcopy(args)
    if job.get('valid_code'):
        try:
            valid_namespace={'__name__':'__mined_filter__'}
            exec(compile(job['valid_code'],'<mined>','exec'),valid_namespace)
            accepted=valid_namespace['valid'](*copy.deepcopy(args)) is True
        except BaseException as exc:return dict(status='unresolved',reason='validity:'+type(exc).__name__,events=[],validity_checks=1,validity_provenance='mined_filter_not_spec_proof')
        if not accepted:return dict(status='filtered',reason='mined_filter_not_spec_proof',events=[],validity_checks=1,validity_provenance='mined_filter_not_spec_proof')
    before=signature(args);events=[];omitted=0;traced=job['mode']=='traced';filename='<chain-put>'
    def trace(frame,event,arg):
        if frame.f_code.co_filename==filename and event in ('line','return','exception'):
            if len(events)>=2048:raise TraceLimit()
            events.append(dict(line=frame.f_lineno,event=event,function=frame.f_code.co_name))
        return trace
    namespace={'__name__':'__chain_put__'}
    try:
        with contextlib.redirect_stdout(io.StringIO()):exec(compile(job['source'],filename,'exec'),namespace)
    except BaseException as exc:return dict(status='unresolved',reason='module_load:'+type(exc).__name__,events=[])
    value=None;put_calls=0
    try:
        if traced:sys.settrace(trace)
        put_calls=1
        with contextlib.redirect_stdout(io.StringIO()):value=namespace[job['entry']](*args)
        status='ok';exception=None;exception_module=None
    except (Deadline,TraceLimit):status='unresolved';exception=None;exception_module=None
    except BaseException as exc:status='exception';exception=type(exc).__name__;exception_module=type(exc).__module__
    finally:sys.settrace(None)
    output=None;capture='unavailable'
    if status=='ok':
        try:
            if signature(value) is None:raise ValueError('unsupported_output')
            output=repr(value)
            if len(output.encode('utf-8'))>4096:raise ValueError('oversize')
            parse_literal(output,output=True);capture='literal'
        except (ValueError,TypeError,RecursionError):output=None;capture='unsupported_or_oversize'
    return dict(status=status,put_calls=put_calls,exception_type=exception,output_capture=capture,output_repr=output,output_signature=signature(value) if status=='ok' and capture=='literal' else None,exception_module=exception_module,input_before=before,input_after=signature(args),
                output_aliases=[i for i,a in enumerate(args) if type(a) in (list,tuple,dict,set) and value is a] if status=='ok' else [],events=events,trace_complete=status!='unresolved',validity_checks=1 if job.get('valid_code') else 0,validity_provenance='mined_filter_not_spec_proof' if job.get('valid_code') else 'no_filter',trace_scope='function_calls_after_module_initialization')


def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(4,4))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(Deadline()));signal.alarm(2)
    try:result=run(json.loads(Path(sys.argv[1]).read_text()))
    except BaseException as exc:result=dict(status='unresolved',reason=type(exc).__name__,events=[])
    finally:signal.alarm(0)
    Path(sys.argv[2]).write_text(json.dumps(result,allow_nan=False)+'\n')


if __name__=='__main__':main()
