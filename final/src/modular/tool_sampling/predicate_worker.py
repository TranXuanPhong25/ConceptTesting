"""Persistent expression worker, launched only inside the membership bwrap sandbox."""
import ast
import builtins
import json
import resource
import signal
import sys

class PredicateTimeout(BaseException):pass


def expired(*unused):raise PredicateTimeout()


def main():
    from support.input_buckets.predicates import FUNCTIONS

    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    SAFE={name:getattr(builtins,name) for name in (
        'all','any','isinstance','type','str','bool','list','tuple','set','dict','sorted',
        'reversed','enumerate','zip','range','round','pow','divmod')}


    signal.signal(signal.SIGALRM,expired)
    for line in sys.stdin:
        try:
            signal.setitimer(signal.ITIMER_REAL,.1)
            request=json.loads(line)
            arguments=ast.literal_eval(request['arguments'])
            environment={'__builtins__':{},**FUNCTIONS,**SAFE,**arguments}
            value=eval(compile(request['expression'],'<membership>','eval'),environment,environment)
            if type(value) is not bool:raise ValueError('predicate_must_return_bool')
            response={'result':value}
        except PredicateTimeout:response={'error':'predicate_timeout'}
        except BaseException as exc:
            response={'error':'predicate_must_return_bool' if str(exc)=='predicate_must_return_bool' else 'predicate_execution_error:'+type(exc).__name__}
        finally:signal.setitimer(signal.ITIMER_REAL,0)
        sys.stdout.write(json.dumps(response)+'\n');sys.stdout.flush()


if __name__=='__main__':main()
