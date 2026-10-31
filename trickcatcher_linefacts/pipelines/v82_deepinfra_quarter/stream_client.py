"""Reserved streaming transport; retry only explicit shared-pool429 rejections."""
from pathlib import Path
from decimal import Decimal
import json,time
from .openrouter_client import OpenRouterClient as LedgerClient,AccountingUnknown,BudgetExceeded
from .stream_wire import payload,dispatch,known_cost
from .context_preflight import check_request
from .paths import CONFIG
from .llm_client import atomic_json
from .v4_runtime import immutable
from .openrouter_client import write_json

C=CONFIG['openrouter']


def _bound_reserve(self,key,input_tokens):
    maximum=C['reservation_price_per_million']
    bound=(Decimal(input_tokens)*Decimal(str(maximum['prompt']))+
           Decimal(C['max_tokens'])*Decimal(str(maximum['completion'])))/Decimal(1000000)
    with self.lock:
        ledger=self.ledger()
        if self.halted or any(e['state'] in ('sent','unknown') for e in ledger['entries'].values()):
            raise AccountingUnknown('pending_or_unknown_charge_stop')
        total=sum((Decimal(e['cost_usd'] if e.get('cost_usd') is not None else e['reserved_usd'])
                   for e in ledger['entries'].values()),Decimal(0))
        if total+bound>self.max_usd:
            self.halted=True;raise BudgetExceeded('openrouter_hard_cap_before_dispatch')
        if key in ledger['entries']:raise AccountingUnknown('attempt_already_dispatched')
        ledger['entries'][key]=dict(state='sent',reserved_usd=str(bound),cost_usd=None,
                                    input_tokens_local=input_tokens,at=time.time())
        write_json(self.cost_path,ledger)
    return bound


class OpenRouterClient(LedgerClient):
    def _reserve(self,key,input_tokens):
        return _bound_reserve(self,key,input_tokens)

    def _complete(self,request):
        slot=Path(request['slot'])
        if slot.is_absolute() or '..' in slot.parts:raise ValueError('invalid_slot')
        folder=self.root/'calls'/slot
        immutable(folder/'request.json',request)
        if (folder/'response.json').exists():return json.loads((folder/'response.json').read_text())
        n_in=check_request(request['messages'])
        attempts_path=folder/'attempts.json'
        attempts=json.loads(attempts_path.read_text()) if attempts_path.exists() else []
        if attempts:raise AccountingUnknown('existing_attempt_without_response_stop')
        wire=payload(request['messages']);immutable(folder/'wire.json',wire)
        for number in range(1,C['max_attempts']+1):
            key=request['slot']+'/attempt-'+str(number)
            bound=self._reserve(key,n_in)
            attempts.append(dict(state='sent',ledger_key=key,at=time.time()))
            atomic_json(attempts_path,attempts)
            result,raw,stderr=dispatch(folder/'wire.json')
            (folder/f'attempt{number}.sse').write_text(raw)
            (folder/f'attempt{number}.stderr').write_text(stderr)
            atomic_json(folder/f'attempt{number}.result.json',result)
            if result['stream_error'] is not None:
                try:
                    error=json.loads(raw).get('error',{});meta=error.get('metadata') or {}
                    rejected=(error.get('code')==429 and meta.get('limit_source')=='upstream_provider_shared_pool'
                              and not result.get('generation_id') and result.get('usage') is None)
                except (ValueError,AttributeError):rejected=False
                if rejected:
                    self._settle(key,'upstream_rejected_unbilled',http_status=429)
                    attempts[-1].update(state='upstream_rejected_unbilled',http_status=429)
                    atomic_json(attempts_path,attempts)
                    if number<C['max_attempts']:
                        time.sleep(30*number);continue
                    self.halted=True;raise RuntimeError('upstream429_after_three_attempts')
                self._settle(key,'unknown',error=result['stream_error'],generation_id=result.get('generation_id'))
                attempts[-1].update(state='unknown',error=result['stream_error'])
                atomic_json(attempts_path,attempts)
                raise AccountingUnknown(result['stream_error']+';reserved_charge_retained')
            try:cost=known_cost(result)
            except ValueError:
                self._settle(key,'unknown',error='missing_cost_or_usage',generation_id=result.get('generation_id'))
                raise AccountingUnknown('missing_cost_or_usage_stop') from None
            usage=result['usage'];content=result['content']
            self._settle(key,'received',cost,usage=usage,generation_id=result['generation_id'],
                         provider=result['provider'],finish_reason=result['finish_reason'],
                         reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0)
            if cost>bound or result['model']!=self.model or result['provider']!=C['expected_provider']:
                self.halted=True;raise RuntimeError('provider_model_or_price_mismatch_stop')
            if result['finish_reason']!='stop':content=''
            response=dict(text=content,origin='openrouter_stream',model=result['model'],provider=result['provider'],
                          finish_reason=result['finish_reason'],input_tokens=usage['prompt_tokens'],
                          output_tokens=usage['completion_tokens'],
                          reasoning_output_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0,
                          cost_usd=float(cost),attempts=number)
            attempts[-1].update(state='received' if content.strip() else 'incomplete',response=response)
            atomic_json(attempts_path,attempts);immutable(folder/'response.json',response)
            return response
        raise RuntimeError('attempt_cap')
