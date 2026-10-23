"""v49 definitional-concept oracle: program generation only (see PREREG.md). Usage (repo root, PYTHONPATH=.):
  source <env with QWEN_BASE_URL>; $V4_PYTHON .../v49_defn_oracle/gen.py generate [smoke]
One worker (the endpoint serves one request at a time). The URL comes from the environment only, never written/printed.
"""
import hashlib
import sys
from pathlib import Path

from trickcatcher_linefacts.analysis.v46_mutoracle_fixed.oracle import complete, digest
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v49_defn_oracle'
MODEL = 'qwen2.5-coder-32b-instruct'
ARMS = ('defn', 'brute', 'plain')
NPROG = 5
SYSTEM = 'You are an expert Python programmer. Reply with exactly one ```python code block and nothing else.'
INSTR = {
    'defn': ('First write the definition concept of the task as comments: `# ENUMERATE:` the candidate objects the '
             'statement quantifies over (all subsets, subarrays, pairs, splits, orders, values, ...), `# CHECK:` the '
             'condition the statement imposes on each candidate, `# AGGREGATE:` how the answer is formed from the '
             'candidates that pass. Then write a brute-force implementation that follows this definition literally. '
             'It only has to be correct on small inputs: do not optimise, no shortcuts or clever formulas.'),
    'brute': ('Write a brute-force implementation that follows the problem statement literally. It only has to be '
              'correct on small inputs: do not optimise, no shortcuts or clever formulas.'),
    'plain': 'Write a correct implementation of the function.',
}


def messages(task, arm):
    user = (f"Problem statement:\n{task['spec']}\n\nPublic tests (the function must pass them):\n{task['base']}\n\n"
            f"Write a module-level Python function with exactly this signature (plus any imports it needs):\n"
            f"def {task['signature']}:\n\n{INSTR[arm]}")
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}]


def jobs(run, root):
    out = []
    for case in run.cases:
        msgs = {arm: messages(run.task(case), arm) for arm in ARMS}
        for i in range(NPROG):
            for arm in ARMS:  # task-major, arms interleaved: a partial run stays balanced
                seed = int(hashlib.sha256(f"v49/{case['case_id']}/{arm}/{i}".encode()).hexdigest()[:8], 16)
                out.append((root / 'programs' / arm / case['case_id'] / f'{i}.json', msgs[arm],
                            dict(temperature=0.8, top_p=0.95, max_tokens=1024, seed=seed)))
    return out


def generate(smoke):
    import openai
    freeze_local_constants()
    run = ft_run.FTRun('vibepass_half')
    # 900 s > queue behind one other client's call + own 1024 tokens; tunnels drop idle connections silently
    client = openai.OpenAI(base_url=__import__('os').environ['QWEN_BASE_URL'], api_key='none', timeout=900,
                           max_retries=2, default_headers={'ngrok-skip-browser-warning': '1'})
    served = {m.id: getattr(m, 'max_model_len', None) for m in client.models.list().data}
    if served.get(MODEL, 0) != 8192:
        raise SystemExit(f'{MODEL} not served with max_model_len 8192: {served}')
    todo = jobs(run, OUT / 'smoke' if smoke else OUT)
    todo = todo[:2] if smoke else todo
    errors = 0
    for n, (path, msgs, params) in enumerate(todo, 1):
        try:
            complete(client, path, msgs, **params)
        except openai.BadRequestError as exc:  # prompt + max_tokens over the 8192 context: recorded once, no program
            if 'context' not in str(exc).lower():
                errors += 1
                print('BadRequestError', path.parent.name, str(exc)[:120], flush=True)
                continue
            immutable(path, dict(text='', finish_reason='context_overflow', input_tokens=None, output_tokens=0,
                                 digest=digest(msgs, params)))
        except Exception as exc:  # recorded; a rerun resumes from the cache
            errors += 1
            print(type(exc).__name__, path.parent.name, str(exc)[:120], flush=True)
        if n % 20 == 0:
            print(n, '/', len(todo), 'errors', errors, flush=True)
    print('done', len(todo), 'errors', errors, flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    if sys.argv[1] == 'generate':
        generate('smoke' in sys.argv[2:])
