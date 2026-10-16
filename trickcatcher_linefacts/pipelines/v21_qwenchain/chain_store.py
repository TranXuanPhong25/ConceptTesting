"""Durable exact-request/cache ledger. No HTTP implementation in P1."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
from .llm_client import atomic_json
from .paths import CONFIG
C=CONFIG['chain']


class Store:
    def __init__(self,directory):self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
    @contextmanager
    def locked(self,key):
        if re.fullmatch('[a-f0-9]{64}',key) is None:raise ValueError('cache_key')
        with (self.directory/(key+'.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield self.directory/(key+'.json')
    def load(self,key):
        with self.locked(key) as path:return json.loads(path.read_text()) if path.exists() else None
    def reserve(self,request):
        key=request['key'];payload=request['payload'];stage=request.get('stage')
        if stage not in C['stages'] or payload.get('max_tokens')!=C['max_tokens'][stage] or payload.get('model')!=C['model'] or payload.get('temperature')!=C['temperature'] or payload.get('top_p')!=C['top_p']:raise ValueError('request_budget_or_model_drift')
        encoded=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        if hashlib.sha256(encoded.encode()).hexdigest()!=key:raise ValueError('request_key_mismatch')
        with self.locked(key) as path:
            rec=json.loads(path.read_text()) if path.exists() else dict(request=request,attempts=[],response=None)
            if rec['request']!=request:raise ValueError('cache_metadata_drift')
            if rec['response'] is not None:return dict(state='cache_hit',response=rec['response'])
            attempts=rec['attempts']
            if attempts and attempts[-1]['state']=='pending':return dict(state='pending_unknown_usage',attempt=attempts[-1]['number'])
            if len(attempts)>=C['max_attempts']:return dict(state='exhausted')
            number=len(attempts)+1;attempts.append(dict(number=number,state='pending',usage='unknown'))
            atomic_json(path,rec)
            return dict(state='reserved',attempt=number,timeout_seconds=C['timeout_seconds'],backoff_seconds=0 if number==1 else C['retry_backoff_seconds'][number-2])
    def finish(self,key,attempt,*,response=None,transport_error=False):
        with self.locked(key) as path:
            rec=json.loads(path.read_text());last=rec['attempts'][-1]
            if last['number']!=attempt or last['state']!='pending':raise ValueError('attempt_state')
            if transport_error:
                if response is not None:raise ValueError('error_with_response')
                last['state']='transport_error'
            else:
                if type(response) is not dict or type(response.get('text')) is not str:raise ValueError('response_shape')
                if response.get('origin')!='offline_fixture':raise ValueError('P1_accepts_offline_fixture_only')
                last['state']='response_received';last['usage']='fixture_not_model_usage';rec['response']=response
            atomic_json(path,rec)
    def abandon_pending(self,key,attempt):
        # A documented interrupted attempt still consumes its cumulative reservation.
        self.finish(key,attempt,transport_error=True)
