"""v75: v47 concept selection replayed with deepseek/deepseek-v4-flash-0731 (provider relace/fp4 only) on OpenRouter (see PREREG.md). Usage (repo root, PYTHONPATH=.):
  $V4_PYTHON .../v75_deepseek_select/ds_select.py prepare    # copy frozen v47 menus (sha256 checked)
  source scripts/openrouter_env.sh; $V4_PYTHON .../ds_select.py generate
  $V4_PYTHON .../ds_select.py score                     # unchanged v47 scorer, v74 calls
The key comes from the environment only and is never written or printed.
"""
import hashlib
import json
import os
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from trickcatcher_linefacts.analysis.v47_concept_select import select_run as S
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run

V47_OUT = S.OUT
OUT = V47_OUT.parent / 'v75_deepseek_select'
MODEL = 'deepseek/deepseek-v4-flash-0731'
MAX_USD = 0.40
MAX_TOKENS = 65536
S.OUT, S.MODEL = OUT, MODEL  # the v47 scorer reads these module globals at call time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cmd = sys.argv[1]
    if cmd == 'prepare':
        OUT.mkdir(parents=True, exist_ok=True)
        dst = OUT / 'prepared.json'
        if not dst.exists():
            shutil.copyfile(V47_OUT / 'prepared.json', dst)
        assert sha(dst) == sha(V47_OUT / 'prepared.json')
        print('prepared', sha(dst))
        return
    freeze_local_constants()
    run = ft_run.FTRun('vibepass_half')
    cases = run.cases
    prepared = json.loads((OUT / 'prepared.json').read_text())
    assert sha(OUT / 'prepared.json') == sha(V47_OUT / 'prepared.json')
    if cmd != 'generate':
        S.score(run, cases, prepared)
        return
    import openai
    client = openai.OpenAI(base_url=os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                           api_key=os.environ['OPENROUTER_API_KEY'], timeout=3600, max_retries=2)
    lock, spent = threading.Lock(), [sum(json.loads(p.read_text())['cost_usd'] or 0 for p in (OUT / 'calls').rglob('*.json'))]

    def call(job):
        case, arm = job
        p = prepared[case['case_id']]
        path = OUT / 'calls' / case['case_id'] / f'{arm}.json'
        if 'error' in p or not p['menus'][arm]['items']:
            return case['case_id'], arm, 'skipped'
        if path.exists():
            return case['case_id'], arm, 'cached'
        with lock:
            if spent[0] >= MAX_USD:
                return case['case_id'], arm, 'budget_stop'
        msgs = S.prompt(run.task(case), case, p['menus'][arm]['items'], arm)
        r = client.chat.completions.create(
            model=MODEL, messages=msgs, temperature=0, max_tokens=MAX_TOKENS, seed=20261022,
            extra_body=dict(provider=dict(only=['relace/fp4'], allow_fallbacks=False), reasoning=dict(max_tokens=4096), usage=dict(include=True)))
        u = r.usage.model_dump() if r.usage else {}
        cost = u.get('cost')
        with lock:
            spent[0] += cost or 0
        immutable(path, dict(text=r.choices[0].message.content or '', finish_reason=r.choices[0].finish_reason,
                             input_tokens=u.get('prompt_tokens'), output_tokens=u.get('completion_tokens'),
                             reasoning_tokens=(u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                             cost_usd=cost, max_tokens=MAX_TOKENS, provider=getattr(r, 'provider', None), model=r.model,
                             prompt_sha256=hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()))
        return case['case_id'], arm, r.choices[0].finish_reason, getattr(r, 'provider', None), cost
    with ThreadPoolExecutor(4) as pool:
        for res in pool.map(call, [(c, a) for c in cases for a in S.ARMS]):
            print(*res, flush=True)
    print('spent_usd', round(spent[0], 6))


if __name__ == '__main__':
    main()
