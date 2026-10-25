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

    if [m['role'] for m in messages] != ['system', 'user']:
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


def preflight():
    """Count 297 frozen historical message payloads; first rounds must match v76.

    Later rounds depend on new outputs and cannot exist before a run. They
    are counted again at dispatch. These are exact local-template counts,
    not provider-billed token claims (provider wrappers may differ).
    """
    from . import ft_run
    from .flow_common import digest
    from .flow_run import original_context, message, INSTR
    run = ft_run.FTRun('vibepass_half')
    old = REPO / 'trickcatcher_linefacts/out/pipelines/v34_ftplacebo/humaneval/faulttemplate/openrouter/vibepass_half'
    rows = []
    for case in run.cases:
        cid = case['case_id']
        tool = json.loads((old / 'cases' / cid / 'tool.json').read_text())
        for arm in ft_run.LLM_ARMS:
            record = json.loads((old / 'cases' / cid / 'arms' / arm / 'result.json').read_text())
            ctx = original_context(run.task(case))
            if arm == 'fault-template':
                ctx['guidance'] = ft_run.guidance(tool)
            elif arm == 'template-placebo':
                ctx['guidance'] = ft_run.placebo_guidance(tool)
            history = []
            for index, stage in enumerate(('probe', 'probe', 'final')):
                messages = message(INSTR[stage], dict(ctx, earlier_feedback=history), stage)
                historical = old if arm == 'template-placebo' else old.parents[4] / 'v31_faulttemplate/humaneval/faulttemplate/openrouter/vibepass_half'
                label = 'final' if stage == 'final' else f'round{index + 1}'
                slot = f'vibepass_half/{cid}/{arm}/{label}-{digest(messages)[:16]}'
                saved = json.loads((historical / 'transport/calls' / slot / 'request.json').read_text())
                if saved['messages'] != messages:
                    raise ValueError('historical_prompt_reconstruction_drift')
                rows.append(dict(case_id=cid, arm=arm, call=index + 1, stage=stage,
                                 messages_sha256=digest(messages), input_tokens=check_request(messages)))
                if stage == 'probe':
                    r = record['rounds'][index]
                    history.append(dict(round=index + 1, feedback=r['feedback']))
                    if len(json.dumps(history, ensure_ascii=False)) > 12000:
                        history = [dict(round=h['round'], feedback=h['feedback'][:3],
                                        omitted=max(0, len(h['feedback']) - 3)) for h in history]
    assert len(rows) == 297
    return dict(scope=('DeepSeek conservative UTF-8 envelope' if CONFIG['model_choice']=='deepseek-v4-flash' else 'exact local upstream Harmony template')+'; historical feedback only; runtime gate on new requests',
                model=CONFIG['model_choice'],tokenizer_sha256=TOKENIZER_SHA if CONFIG['model_choice']=='gpt-oss-120b' else None, context_length=CONFIG['openrouter']['context_length'],
                max_completion_tokens=CONFIG['openrouter']['max_tokens'], requests=len(rows),
                max_input_tokens=max(r['input_tokens'] for r in rows),
                total_historical_input_tokens=sum(r['input_tokens'] for r in rows), rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = preflight()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
