"""Exact local Harmony counts; no tokenizer endpoint or model invocation."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import tiktoken
from tiktoken.load import load_tiktoken_bpe
from tiktoken_ext import openai_public
from jinja2.sandbox import SandboxedEnvironment

from .paths import CONFIG, REPO

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'assets'
TOKENIZER_SHA = '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'


@lru_cache(maxsize=1)
def encoding():
    path = ASSETS / 'o200k_base.tiktoken'
    if hashlib.sha256(path.read_bytes()).hexdigest() != TOKENIZER_SHA:
        raise ValueError('tokenizer_asset_drift')
    # Use tiktoken's official constructor, replacing only its network loader
    # with the SHA-verified local asset. No network/cache dependency.
    from unittest.mock import patch
    ranks = load_tiktoken_bpe(str(path), expected_hash=TOKENIZER_SHA)
    with patch.object(openai_public, 'load_tiktoken_bpe', return_value=ranks):
        kwargs = openai_public.o200k_harmony()
    return tiktoken.Encoding(**kwargs)


def token_count(messages, date='2026-10-26'):
    if CONFIG['model_choice'] == 'deepseek-v4-flash':
        if [m['role'] for m in messages] != ['system', 'user']:
            raise ValueError('registered_two_message_request_required')
        # Conservative byte envelope, not the unavailable provider tokenizer.
        # Two tokens per UTF-8 byte plus 4096 framing tokens; runtime gate too.
        return 4096 + 2 * sum(len(m['content'].encode('utf-8')) for m in messages)

    if len(messages)<2 or [m['role'] for m in messages[:2]] != ['system', 'user'] or any(m['role'] not in ('assistant','user') for m in messages[2:]):
        raise ValueError('registered_two_message_request_required')
    env = SandboxedEnvironment()
    template = env.from_string((ASSETS / 'gpt_oss_chat_template.jinja').read_text())
    rendered = template.render(messages=messages, tools=[], builtin_tools=[],
                               reasoning_effort='low', add_generation_prompt=True,
                               strftime_now=lambda _: date)
    return len(encoding().encode(rendered, allowed_special='all'))


def check_request(messages):
    count = token_count(messages)
    if count + CONFIG['openrouter']['max_tokens'] > CONFIG['openrouter']['context_length']:
        raise ValueError('request_exceeds_registered_context')
    return count


def preflight(prepared=None):
    """Exact initial payloads and explicit prospective envelopes, no inference.

    Full combined bundles are CPU-built only at launch/preparation. Unknown
    future strategy corrections receive an envelope here and an exact runtime
    gate at every dispatch; no historical future response is substituted.
    """
    from .datasets import cohort
    from . import prompts, gen_prompts, v4_prompts
    rows=[]
    for dataset in CONFIG['combined']['tasks']:
        for task in cohort(dataset):
            pair=next((p for p in (prepared or {}).get(dataset,[]) if p['baseline']['task']==task['task']),None)
            if pair:task=pair['baseline']
            for arm,kind in [('concept-hybrid','concept')]:
                messages=gen_prompts.messages(*prompts.build(kind,task))
                rows.append(dict(dataset=dataset,task=task['task'],arm=arm,scope='exact public baseline first request',input_tokens=check_request(messages)))
            # Envelope uses the actual entire PUT/spec/base and fixed-size public
            # concept descriptions, not hidden evaluator information.
            envelope=pair['combined'] if pair else dict(task,concept_facts=['Fault-type adequacy at a code line. '+('behaviour alternative '*300)]*3)
            messages=gen_prompts.messages(*prompts.build('concept',envelope))
            rows.append(dict(dataset=dataset,task=task['task'],arm='concept-hybrid-ft',scope='exact CPU combined first request' if pair else 'prospective concept text envelope',input_tokens=check_request(messages)))
            strategy_task=dict(task,strategy_src=task['strategy_src'])
            messages=v4_prompts.hybrid_messages(strategy_task,dict(text='Fault-type adequacy. '+('behaviour '*900)),['assert '+task['entry']+'(0) == 0']*20)
            rows.append(dict(dataset=dataset,task=task['task'],arm='round2',scope='prospective round2 envelope, retries checked at runtime',input_tokens=check_request(messages)))
    return dict(scope=('conservative UTF-8 byte bound for DeepSeek' if CONFIG['model_choice']=='deepseek-v4-flash' else 'local upstream Harmony')+'; public first requests + labelled envelopes; runtime exact gate mandatory',
                model=CONFIG['model_choice'],requests=len(rows),max_input_tokens=max(r['input_tokens'] for r in rows),
                context_length=CONFIG['openrouter']['context_length'],max_output_tokens=CONFIG['openrouter']['max_tokens'],rows=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=preflight()
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
