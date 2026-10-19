"""OpenRouter client (openai SDK) with the flow_client contract: complete(request) -> dict(text, tokens, ...).

Key, base URL, model and a USD hard cap come from the environment (source scripts/openrouter_env.sh, gitignored);
the key is never written to disk or logs. Transport retries (429 / 5xx / connection, honoring Retry-After) are the SDK's
`max_retries`; other 4xx fail fast. A completion with empty content or finish_reason != 'stop' is retried up to
`max_attempts` times and is cached only on the last attempt (then it is a model failure, recorded with its reason).
Each slot is cached (request.json / response.json); reported cost is summed in cost.json; new calls stop at the cap.
"""
import json
import os
import threading
import time
from pathlib import Path

import openai

from .flow_common import immutable
from .paths import CONFIG

C = CONFIG['openrouter']


class BudgetExceeded(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        key = os.environ.get('OPENROUTER_API_KEY', '')
        if not key or key.startswith('PASTE_'):
            raise SystemExit('OPENROUTER_API_KEY missing: fill scripts/openrouter_env.sh and source it')
        base = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')
        self.model = os.environ.get('OPENROUTER_MODEL', C['model'])
        if self.model != C['model']:
            raise SystemExit(f'OPENROUTER_MODEL={self.model} differs from the registered model {C["model"]}')
        self.max_usd = float(os.environ.get('OPENROUTER_MAX_USD', C['default_max_usd']))
        self.lock = threading.Lock()
        self.cost_path = self.root / 'cost.json'
        immutable(self.root / 'server.json', dict(model=self.model, base=base, params=C['params'], provider=C['provider'],
                                                  client=f'openai-python {openai.__version__}'))
        self.sdk = openai.OpenAI(api_key=key, base_url=base, max_retries=C['sdk_max_retries'], timeout=C['timeout_seconds'],
                                 default_headers={'X-Title': 'ConceptTester v31'})

    def close(self):
        self.sdk.close()

    def spent(self):
        return json.loads(self.cost_path.read_text())['usd'] if self.cost_path.exists() else 0.0

    def _reserve(self):
        with self.lock:
            if self.spent() >= self.max_usd:
                raise BudgetExceeded(f'openrouter budget {self.max_usd} USD reached')

    def _charge(self, usd):
        with self.lock:
            self.cost_path.write_text(json.dumps(dict(usd=self.spent() + usd)) + '\n')

    def complete(self, request):
        path = self.root / 'calls' / request['slot']
        immutable(path / 'request.json', request)
        if (path / 'response.json').exists():
            return json.loads((path / 'response.json').read_text())
        attempts = json.loads((path / 'attempts.json').read_text()) if (path / 'attempts.json').exists() else []
        p = C['params']
        while len(attempts) < C['max_attempts']:
            self._reserve()
            attempts.append(dict(state='sent', at=time.time()))
            (path / 'attempts.json').write_text(json.dumps(attempts))
            try:
                r = self.sdk.chat.completions.create(
                    model=self.model, messages=request['messages'], seed=request['seed'], max_tokens=C['max_tokens'],
                    temperature=p['temperature'], top_p=p['top_p'], response_format=p['response_format'],
                    extra_body=dict(usage={'include': True}, provider=C['provider']))
            except openai.BadRequestError as exc:  # deterministic (e.g. context length): no retry
                attempts[-1].update(state='bad_request', body=str(exc)[:300])
                (path / 'attempts.json').write_text(json.dumps(attempts))
                raise RuntimeError('openrouter_attempts_exhausted') from None
            except openai.APIError as exc:  # SDK retries already spent on 429/5xx/connection
                attempts[-1].update(state='api_error', error=type(exc).__name__, body=str(exc)[:300])
                (path / 'attempts.json').write_text(json.dumps(attempts))
                continue
            usage = (r.usage.model_dump() if r.usage else {}) or {}
            details = usage.get('completion_tokens_details') or {}
            choice = r.choices[0] if r.choices else None
            text = (choice.message.content or '') if choice and choice.message else ''
            result = dict(text=text, origin='openrouter', model=r.model, provider=getattr(r, 'provider', None) or (r.model_extra or {}).get('provider'),
                          finish_reason=choice.finish_reason if choice else None,
                          input_tokens=usage.get('prompt_tokens', 0), output_tokens=usage.get('completion_tokens', 0),
                          reasoning_output_tokens=details.get('reasoning_tokens', 0) or 0, cost_usd=float(usage.get('cost') or 0.0),
                          attempts=len(attempts))
            self._charge(result['cost_usd'])
            complete = bool(text.strip()) and result['finish_reason'] == 'stop'
            attempts[-1].update(state='received' if complete else 'incomplete', finish_reason=result['finish_reason'],
                                empty=not text.strip(), cost_usd=result['cost_usd'])
            (path / 'attempts.json').write_text(json.dumps(attempts))
            if complete or len(attempts) >= C['max_attempts']:
                immutable(path / 'response.json', result)
                return result
        raise RuntimeError('openrouter_attempts_exhausted')
