"""Execute restricted predicate; no PUT/spec/reference context or network/credentials."""
import builtins
from collections import Counter
import copy
import json
from pathlib import Path
import resource
import signal
import sys

if not __package__:
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parents[2]))
    __package__ = 'trickcatcher_linefacts.pipelines.' + here.name
from .predicates import PURE, validate_code
from .binding import check_json
COUNT = 0


class Deadline(Exception):
    pass


def run(job):
    global COUNT
    validate_code(job['source'], job['kind'])
    env = {'__builtins__': {}, 'Counter': Counter}
    env.update({name: getattr(builtins, name) for name in PURE if name != 'Counter'})
    exec(compile(job['source'], '<obligation>', 'exec'), env)
    rows = []
    for row in job['rows']:
        args = copy.deepcopy(check_json(row['arguments']))
        obs = copy.deepcopy(check_json(row.get('observation')))
        before = json.dumps([args, obs], sort_keys=True)
        try:
            COUNT += 1
            value = env[job['kind']](args, obs) if job['kind'] == 'obligation' else env[job['kind']](args)
            if json.dumps([args, obs], sort_keys=True) != before:
                raise ValueError('predicate_mutated_input')
            if type(value) is not bool:
                raise ValueError('predicate_non_boolean')
            rows.append({'state': 'evaluated', 'value': value})
        except Exception as exc:
            if isinstance(exc, Deadline):
                raise
            rows.append({'state': 'unknown', 'reason': type(exc).__name__})
    return {'rows': rows, 'evaluations_attempted': COUNT}


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Deadline()))
    signal.alarm(2)
    try:
        job = json.loads(Path(sys.argv[1]).read_text())
        result = run(job)
    except BaseException:
        # Whole batch remains unknown, never accepted after partial output.
        result = {'rows': [{'state': 'unknown', 'reason': 'predicate_batch_failed'}
                           for _ in job.get('rows', [])], 'evaluations_attempted': COUNT} if 'job' in locals() else {'rows': []}
    finally:
        signal.alarm(0)
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
