"""Single-attempt OpenRouter transport; environment-only key, durable spend reservations."""
import hashlib
import json
import math
import os
import threading
import time
from pathlib import Path
import httpx
from .paths import CONFIG
from .llm_client import atomic_json
C=CONFIG['openrouter']
class StopRun(RuntimeError):pass

def input_bound(messages):return len(json.dumps(messages,ensure_ascii=False).encode())+4096

class Router:
    def __init__(self,root,http=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();self.stop=threading.Event()
        limit=float(os.environ.get('OPENROUTER_MAX_USD',1))
        if not math.isfinite(limit) or limit<=0:raise StopRun('invalid_budget')
        self.cap=min(limit,C['usd_cap']);self.ledger_path=self.root/'ledger.json'
        self.ledger=json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {}
        if any(x['status'] not in ('received',) for x in self.ledger.values()):self.stop.set()
        key=os.environ.get('OPENROUTER_API_KEY','')
        if not key or key.startswith('PASTE_'):raise StopRun('missing_key')
        if os.environ.get('OPENROUTER_MODEL',C['model'])!=C['model']:raise StopRun('model_mismatch')
        self.base=os.environ.get('OPENROUTER_BASE_URL','https://openrouter.ai/api/v1').rstrip('/')
        if self.base!='https://openrouter.ai/api/v1':raise StopRun('unexpected_endpoint')
        self.http=http or httpx.Client(timeout=C['timeout_seconds'],headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    def total(self):return sum(x.get('cost_usd',x['reserved_usd']) for x in self.ledger.values())
    def complete(self,stage,messages,seed):
        cap=CONFIG['chain']['max_tokens'][stage];bound=input_bound(messages)
        if bound+cap>CONFIG['chain']['context_window_tokens']:raise ValueError('context_bound_exceeded')
        body=dict(model=C['model'],messages=messages,max_tokens=cap,temperature=0,top_p=1,seed=seed,reasoning=C['reasoning'],usage={'include':True},provider={'max_price':C['max_price_per_million'],'sort':'price','require_parameters':True})
        ident=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest();directory=self.root/'calls'/ident;directory.mkdir(parents=True,exist_ok=True)
        reservation=(bound*.30+cap*1.5)/1e6
        with self.lock:
            if ident in self.ledger:
                if self.ledger[ident]['status']=='received':return json.loads((directory/'response.json').read_text())
                raise StopRun('ambiguous_attempt_no_retry')
            if self.stop.is_set():raise StopRun('run_stopped')
            if self.total()+reservation>self.cap:self.stop.set();raise StopRun('budget_limit')
            atomic_json(directory/'request.json',body)
            self.ledger[ident]=dict(stage=stage,status='pending',reserved_usd=reservation,at=time.time());atomic_json(self.ledger_path,self.ledger)
        try:
            response=self.http.post(self.base+'/chat/completions',json=body)
            if response.status_code!=200:raise StopRun('http_'+str(response.status_code))
            data=response.json();choice=data['choices'][0];usage=data['usage'];cost=usage.get('cost')
            if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:raise StopRun('missing_or_invalid_cost')
            counts=[usage.get('prompt_tokens'),usage.get('completion_tokens')]
            if any(type(x) is not int or x<0 for x in counts):raise StopRun('missing_usage')
            text=choice['message'].get('content')
            if text is None:text=''
            if type(text) is not str:raise StopRun('unsupported_content')
            result=dict(text=text,finish_reason=choice.get('finish_reason'),model=data.get('model'),provider=data.get('provider'),input_tokens=counts[0],output_tokens=counts[1],reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0),cost_usd=cost,origin='openrouter',id=data.get('id'))
            # Record actual paid usage even if a later protocol check fails.
            with self.lock:
                atomic_json(directory/'response.json',result);self.ledger[ident].update(status='received',cost_usd=cost,input_tokens=counts[0],output_tokens=counts[1],reasoning_tokens=result['reasoning_tokens'],provider=result['provider'],finish_reason=result['finish_reason']);atomic_json(self.ledger_path,self.ledger)
            if counts[0]>bound or counts[1]>cap or cost>reservation+1e-8 or result['model']!=C['model']:raise StopRun('response_protocol_mismatch')
            return result
        except BaseException as exc:
            self.stop.set()
            with self.lock:
                self.ledger[ident].update(status='stopped_after_response' if 'cost_usd' in self.ledger[ident] else 'unknown',error_type=type(exc).__name__)
                atomic_json(self.ledger_path,self.ledger)
            raise StopRun(str(exc) if isinstance(exc,StopRun) else type(exc).__name__) from None
