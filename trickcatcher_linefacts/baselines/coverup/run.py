"""CoverUp (Pizzorno & Berger, FSE 2025) in the TrickCatcher setting: the authors' gpt-v2 prompts and
`improve_coverage` loop (compiled unmodified from CoverUp_concept/vendor/coverup), coverage measured with
coverage.py from the base tests, LLM via the shared Qwen client, every execution sandboxed.

  python -m trickcatcher_linefacts.baselines.coverup.run --tasks <bundle.json> --out <dir> --k 3 [--online]
"""
import argparse
import asyncio
import importlib
import json
import re
import subprocess
import sys
import types
from pathlib import Path

from ..common import REPO, base_test, cli, digest, extract_assertions, helper_functions, original_definitions, specification, worker

VENDOR = REPO/'CoverUp_concept/vendor/coverup'
PIN = 'd9ca25b9282621d2779560f2be397ab0683a6733'


def provenance():
    if not (VENDOR/'src/coverup/coverup.py').exists():
        raise FileNotFoundError('restore CoverUp_concept/vendor/coverup at '+PIN)
    return dict(paper='CoverUp (Pizzorno & Berger, FSE 2025)', commit=PIN,
                source=str(VENDOR.relative_to(REPO)),
                loop_sha256=digest((VENDOR/'src/coverup/coverup.py').read_text()),
                prompt_sha256=digest((VENDOR/'src/coverup/prompt/gpt_v2.py').read_text()),
                prompt='gpt-v2', max_attempts=3, repeat_tests=5, line_limit=50)


def load_original():
    # Bypass __init__, which imports the original LLM SDK. No source files are edited.
    if 'coverup' not in sys.modules:
        package = types.ModuleType('coverup'); package.__path__ = [str(VENDOR/'src/coverup')]
        sys.modules['coverup'] = package
    segment = importlib.import_module('coverup.segment')
    prompter = importlib.import_module('coverup.prompt.gpt_v2')
    utils = importlib.import_module('coverup.utils')
    ns = original_definitions(VENDOR/'src/coverup/coverup.py',
        ['improve_coverage','extract_python','clean_error','find_imports','missing_imports','new_test_file','test_file_path','State'],
        dict(Path=Path, re=re, json=json, subprocess=subprocess, module_available={}, test_seq=1,
             PROGRESS_COUNTERS=['G','F','U','R'], format_branches=utils.format_branches))
    return ns, segment, prompter.GptV2Prompter


def generate(task, session, config):
    ns, segment, Prompter = load_original()
    root = session.directory/'workspace'; root.mkdir()
    tests = root/'tests'; tests.mkdir()
    put = root/'put.py'; put.write_text(task['put'])
    base = tests/'test_base.py'; base.write_text(base_test(task))
    initial = worker('coverage', dict(root=str(root), tests=[str(base)]), session.directory/'coverage_base')
    if not initial['ok']:
        return dict(assertions=[], stop_reason='base_failed', diagnostics=initial)
    args = argparse.Namespace(src_base_dir=root, tests_dir=tests, max_attempts=3, dry_run=False,
                              install_missing_modules=False, repeat_tests=5, pytest_args='', isolate_tests=True,
                              branch_coverage=True, show_details=False, prefix='coverup', save_coverage_to=None)
    prompter = Prompter(args)
    original_initial = prompter.initial_prompt
    def initial_prompt(seg):
        # Text-only context instead of get_info tool calls: spec, whole module and base tests,
        # given once before the authors' unchanged prompt.
        context = (f"Specification:\n{specification(task)}\n\n"
                   f"Module put.py (import it as `from put import {task['entry']}`):\n```python\n{task['put']}\n```\n"
                   f"Existing tests (tests/test_base.py):\n```python\n{base_test(task)}\n```")
        return [dict(role='user', content=context)] + original_initial(seg)
    prompter.initial_prompt = initial_prompt
    events = []
    ns['log_write'] = lambda args, seg, message: events.append(dict(segment=str(seg), message=message))
    ns['state'] = ns['State'](initial['coverage'])
    measure_index = 0
    async def measure_test_coverage(*, test, **kwargs):
        nonlocal measure_index
        path = tests/'candidate.py'; path.write_text(test)
        # Repeat in separate processes to avoid retaining imported PUT/test state.
        measured = None
        for repeat in range(args.repeat_tests):
            measured = worker('coverage', dict(root=str(root), tests=[str(path)]),
                              session.directory/f'coverage_candidate_{measure_index}_{repeat}')
            if not measured['ok']: break
        measure_index += 1
        if not measured['ok']:
            raise subprocess.CalledProcessError(1, 'coverage.py/pytest', output=measured['error'].encode())
        return measured['coverage']
    ns['measure_test_coverage'] = measure_test_coverage
    exhausted = []
    class Chatter:
        async def chat(self, messages, ctx):
            if not session.remaining:
                exhausted.append(str(ctx))   # the original loop then logs "giving up" for this segment
                return None
            raw = session.query(messages, 'coverage')
            return dict(choices=[dict(message=dict(role='assistant',content=raw))])
    segments = sorted(segment.get_missing_coverage(initial['coverage'], line_limit=50), key=lambda s:s.missing_count(), reverse=True)
    attempted = []
    async def improve():
        # The authors schedule each initially missing segment once and stop at first gain.
        for seg in segments:
            if not session.remaining: break
            attempted.append(seg.identify())
            await ns['improve_coverage'](args, Chatter(), prompter, seg)
    # Original import availability check needs the task-local module to be discoverable.
    sys.path.insert(0, str(root))
    try: asyncio.run(improve())
    finally: sys.path.remove(str(root))
    accepted = sorted(tests.glob('test_coverup_*.py'), key=lambda p: int(p.stem.rsplit('_', 1)[1]))
    assertions, dropped, raw_tests = [], [], []
    for path in accepted:
        raw = path.read_text(); raw_tests.append(raw)
        found, rejected = extract_assertions(raw, task['entry'], task['put'], helper_functions(task['base']))
        assertions.extend(found)
        dropped.extend(rejected)
    assertions = list(dict.fromkeys(assertions))
    final = worker('coverage', dict(root=str(root), tests=[str(base), *map(str,accepted)]), session.directory/'coverage_final')
    def percent(cov):
        files = (cov or {}).get('files', {})
        return next(iter(files.values()))['summary']['percent_covered'] if files else None
    return dict(assertions=assertions, raw_tests=raw_tests, raw_assertions=assertions,
                extraction_rejected=dropped, events=events, initial_coverage=initial['coverage'],
                final_coverage=final, base_full_coverage=not segments, base_coverage_percent=percent(initial['coverage']),
                final_coverage_percent=percent(final.get('coverage')) if final.get('ok') else None,
                segments=len(segments), segments_attempted=attempted, accepted_tests=len(accepted),
                stop_reason='full_base_coverage' if not segments else
                ('llm_budget' if exhausted or len(attempted) < len(segments) else 'segments_completed'))


if __name__ == '__main__': cli('coverup', generate, provenance)
