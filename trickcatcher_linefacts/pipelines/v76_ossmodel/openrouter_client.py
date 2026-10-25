"""OpenRouter SDK client with durable worst-case reservations and exact context gate.

Every physical dispatch is accounted for. No automatic SDK retries; unknown
charges retain their reservation and stop subsequent calls. No secrets in logs.
"""
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
import threading
import time
from pathlib import Path

import openai

from .context_preflight import check_request
from .flow_common import immutable
from .flow_client import write_json
from .paths import CONFIG

C = CONFIG['openrouter']


class BudgetExceeded(RuntimeError):
    pass


class WorkspacePaused(RuntimeError):
    pass


class AccountingUnknown(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        key = os.environ.get('OPENROUTER_API_KEY', '')
        if not key or key.startswith('PASTE_'):
            raise SystemExit('OPENROUTER_API_KEY missing: source scripts/openrouter_env.sh')
        base = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')
        if base != 'https://openrouter.ai/api/v1':
            raise ValueError('official_openrouter_endpoint_required')
        self.model = os.environ.get('OPENROUTER_MODEL', C['model'])
        if self.model != C['model']:
            raise ValueError('registered_model_mismatch')
        cap = Decimal(os.environ.get('OPENROUTER_MAX_USD', str(C['default_max_usd'])))
        if not cap.is_finite() or cap <= 0:
            raise ValueError('positive_finite_budget_required')
        self.max_usd = min(cap, Decimal(str(C['hard_max_usd'])))
        self.lock = threading.Lock()
        self.cost_path = self.root / 'cost.json'
        self.process_lock = (self.root / '.client.lock').open('a')
        try:
            fcntl.flock(self.process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.process_lock.close()
            raise RuntimeError('another_transport_process_is_active') from None
        self.halted = False
        immutable(self.root / 'server.json', dict(model=self.model, base=base, params=C['params'], provider=C['provider'],
                  reasoning=C['reasoning'], hard_max_usd=C['hard_max_usd'], client=f'openai-python {openai.__version__}'))
        self.sdk = openai.OpenAI(api_key=key, base_url=base, max_retries=0, timeout=C['timeout_seconds'],
                                 default_headers={'X-Title': 'ConceptTester v76'})

    def close(self):
        self.sdk.close()
        self.process_lock.close()

    def ledger(self):
        return json.loads(self.cost_path.read_text()) if self.cost_path.exists() else {'entries': {}}

    def spent(self):
        return float(sum((Decimal(e['cost_usd']) for e in self.ledger()['entries'].values()
                          if e.get('cost_usd') is not None), Decimal(0)))

    def _reserve(self, key, input_tokens):
        maximum = C['reservation_price_per_million']
        # Provider wrappers can add tokens: reserve the FULL context allowance
        # for the prompt, not just our exact local template count. Output cap
        # remains v34's 16384. Price ceilings use USD per million tokens.
        bound = (Decimal(C['context_length']) * Decimal(str(maximum['prompt'])) +
                 Decimal(C['max_tokens']) * Decimal(str(maximum['completion']))) / Decimal(1000000)
        with self.lock:
            ledger = self.ledger()
            if self.halted or any(e['state'] in ('sent', 'unknown') for e in ledger['entries'].values()):
                # 'sent' includes in-flight requests: serialize dispatches so
                # no new paid call can escape after unknown accounting.
                raise AccountingUnknown('pending_or_unknown_charge_stop')
            total = sum((Decimal(e['cost_usd'] if e.get('cost_usd') is not None else e['reserved_usd'])
                         for e in ledger['entries'].values()), Decimal(0))
            if total + bound > self.max_usd:
                self.halted = True
                raise BudgetExceeded('openrouter_hard_cap_before_dispatch')
            if key in ledger['entries']:
                raise AccountingUnknown('attempt_already_dispatched')
            ledger['entries'][key] = dict(state='sent', reserved_usd=str(bound), cost_usd=None,
                                          input_tokens_local=input_tokens, at=time.time())
            write_json(self.cost_path, ledger)
        return bound

    def _settle(self, key, state, cost=None, **fields):
        with self.lock:
            ledger = self.ledger()
            ledger['entries'][key].update(state=state, cost_usd=str(cost) if cost is not None else None, **fields)
            if state == 'unknown':
                self.halted = True
            write_json(self.cost_path, ledger)

    def complete(self, request):
        # Single dispatch lock covers accounting + network. Worker concurrency
        # still replays independently; no paid request is waiting unaccounted.
        with self.dispatch_lock:
            return self._complete(request)

    @property
    def dispatch_lock(self):
        # Created lazily for injected SDK tests too.
        with self.lock:
            if not hasattr(self, '_dispatch_lock'):
                self._dispatch_lock = threading.Lock()
            return self._dispatch_lock

    def _complete(self, request):
        slot = Path(request['slot'])
        if slot.is_absolute() or '..' in slot.parts:
            raise ValueError('invalid_slot')
        path = self.root / 'calls' / slot
        immutable(path / 'request.json', request)
        if (path / 'response.json').exists():
            return json.loads((path / 'response.json').read_text())
        input_tokens = check_request(request['messages'])
        if [m['role'] for m in request['messages']] != ['system','user']:
            raise ValueError('assistant_turns_forbidden')
        attempts_path = path / 'attempts.json'
        attempts = json.loads(attempts_path.read_text()) if attempts_path.exists() else []
        p = C['params']
        while len(attempts) < C['max_attempts']:
            key = request['slot'] + '/attempt-' + str(len(attempts) + 1)
            # Previously denied attempts stay in the global ledger; a fresh
            # per-slot counter after archival must never overwrite a receipt.
            while key in self.ledger()['entries'] and self.ledger()['entries'][key]['state'] == 'workspace_403':
                key += '-resume'
            bound = self._reserve(key, input_tokens)
            attempts.append(dict(state='sent', ledger_key=key, at=time.time()))
            write_json(attempts_path, attempts)
            try:
                r = self.sdk.chat.completions.create(
                    model=self.model, messages=request['messages'], **({'seed': request['seed']} if C['send_seed'] else {}), max_tokens=C['max_tokens'],
                    temperature=p['temperature'], top_p=p['top_p'], response_format=p['response_format'],
                    extra_body=dict(usage={'include': True}, provider=C['provider'], reasoning=C['reasoning']))
            except openai.APIStatusError as exc:
                code = exc.status_code
                # Explicit pre-generation HTTP rejections carry no completion.
                if code in (400, 401, 402, 403, 404, 422, 429):
                    state = 'workspace_403' if code == 403 else 'rejected'
                    self._settle(key, state, Decimal(0), http_status=code)
                    attempts[-1].update(state=state, http_status=code)
                    write_json(attempts_path, attempts)
                    self.halted = True
                    if code == 403:
                        raise WorkspacePaused(str(exc)) from None
                    raise RuntimeError(str(exc)) from None
                self._settle(key, 'unknown', http_status=code)
                raise AccountingUnknown('http_failure_cost_unknown') from None
            except Exception as exc:
                self._settle(key, 'unknown', error=type(exc).__name__)
                raise AccountingUnknown('transport_failure_cost_unknown') from None
            usage = (r.usage.model_dump() if r.usage else {}) or {}
            try:
                cost = Decimal(str(usage.get('cost')))
                if not cost.is_finite() or cost < 0 or isinstance(usage.get('cost'), bool):
                    raise ValueError()
                if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('prompt_tokens', 'completion_tokens')):
                    raise ValueError()
            except (ValueError, InvalidOperation):
                self._settle(key, 'unknown', error='missing_or_invalid_usage',
                             usage=usage, generation_id=r.id,
                             provider=getattr(r, 'provider', None) or (r.model_extra or {}).get('provider'))
                raise AccountingUnknown('missing_or_invalid_usage_stop') from None
            self._settle(key, 'received', cost, usage=usage, generation_id=r.id,
                         reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0,
                         finish_reason=r.choices[0].finish_reason if r.choices else None,
                         empty_answer_count=int(not (r.choices and (r.choices[0].message.content or '').strip())),
                         provider=getattr(r, 'provider', None) or (r.model_extra or {}).get('provider'))
            if cost > bound:
                self.halted = True
                raise AccountingUnknown('provider_exceeded_reserved_price_stop')
            details = usage.get('completion_tokens_details') or {}
            choice = r.choices[0] if r.choices else None
            content = (choice.message.content or '') if choice and choice.message else ''
            result = dict(text=content, origin='openrouter', model=r.model,
                          provider=getattr(r, 'provider', None) or (r.model_extra or {}).get('provider'),
                          finish_reason=choice.finish_reason if choice else None,
                          input_tokens=usage['prompt_tokens'], output_tokens=usage['completion_tokens'],
                          reasoning_output_tokens=details.get('reasoning_tokens', 0) or 0,
                          cost_usd=float(cost), attempts=len(attempts))
            complete = bool(content.strip()) and result['finish_reason'] == 'stop'
            attempts[-1].update(state='received' if complete else 'incomplete', response=result)
            write_json(attempts_path, attempts)
            if r.model != self.model:
                self.halted = True
                raise RuntimeError('served_model_mismatch')
            if complete or len(attempts) >= C['max_attempts']:
                immutable(path / 'response.json', result)
                return result
        raise RuntimeError('openrouter_attempts_exhausted')
