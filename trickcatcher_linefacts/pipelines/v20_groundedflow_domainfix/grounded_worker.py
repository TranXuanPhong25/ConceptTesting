"""Isolated CPU worker, no network/API environment."""
import ast
import json
from pathlib import Path
import resource
import sys
if not __package__:
    here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[2]))
    __package__='trickcatcher_linefacts.pipelines.'+here.name
from . import grounded as g,tracer,preconditions
from .llm_client import atomic_json


def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(4,4))
    job=json.loads(Path(sys.argv[1]).read_text())
    try:
        args=ast.literal_eval(job['input_repr']);g.checked_input(args)
        with tracer.alarm(2):
            if job.get('mined_valid_src'):
                valid=preconditions.load_predicate(job['mined_valid_src'],'valid')
                if valid(*args) is not True:
                    atomic_json(Path(sys.argv[2]),dict(complete_evidence=False,worker_status='filtered',domain_filter='mined_not_trusted_spec'));return
            result=g.evidence(job['source'],job['entry'],args,job['requirement'])
            if job.get('mined_valid_src'):result['domain_filter']='mined_passed_not_trusted_spec'
    except Exception as exc:result=dict(complete_evidence=False,worker_status='unresolved',reason=type(exc).__name__)
    atomic_json(Path(sys.argv[2]),result)


if __name__=='__main__':main()
