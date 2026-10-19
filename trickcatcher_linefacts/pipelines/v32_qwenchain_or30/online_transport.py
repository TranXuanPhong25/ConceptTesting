"""Bounded user-authorized Qwen transport; endpoints/credentials remain in environment."""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from jinja2.sandbox import SandboxedEnvironment
from .paths import CONFIG
from .source_view import digest
from .llm_client import atomic_json,NoRedirect
C=CONFIG['chain'];HERE=Path(__file__).resolve().parent


class TransportIncomplete(RuntimeError):pass
class ProtocolMismatch(RuntimeError):pass


def endpoint():
    value=os.environ.get('QWEN_BASE_URL','').rstrip('/');u=urllib.parse.urlsplit(value);host=u.hostname or ''
    local=host in ('127.0.0.1','localhost','::1')
    tunnel=any(host.endswith('.'+x) for x in ('ngrok-free.dev','ngrok.dev','ngrok-free.app','ngrok.app','ngrok.io'))
    if not value or u.scheme not in ('https','http') or not(local or tunnel) or (not local and u.scheme!='https') or u.username or u.password or u.query or u.fragment:raise ValueError('invalid_Qwen_endpoint')
    if not value.endswith('/v1'):value+='/v1'
    return value


class Connection:
    def __init__(self):
        self.base=endpoint();self.root=self.base[:-3];self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        self.headers={'Content-Type':'application/json','ngrok-skip-browser-warning':'1'}
        if os.environ.get('QWEN_API_KEY'):self.headers['Authorization']='Bearer '+os.environ['QWEN_API_KEY']
    def call(self,path,payload=None,timeout=120):
        url=(self.root if path=='/tokenize' else self.base)+path
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
        with self.opener.open(urllib.request.Request(url,data=data,headers=self.headers),timeout=timeout) as response:
            body=response.read(16*1024*1024)
        return json.loads(body)
    def redact(self,text):
        for value in (self.base,self.root,os.environ.get('QWEN_API_KEY','')):
            if value:text=text.replace(value,'<redacted>')
        return text


class Tokenizer:
    def __init__(self,connection,directory):
        self.connection=connection;self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((HERE/'tokenizer_manifest.json').read_text());template=(HERE/'chat_template.jinja').read_text()
        if hashlib.sha256(template.encode()).hexdigest()!=manifest['template_sha256']:raise ProtocolMismatch('chat_template_hash')
        self.template=SandboxedEnvironment().from_string(template);self.counter_id='server_raw_tokenize:'+manifest['template_sha256'];self.context=manifest['context_window']
    def __call__(self,messages):
        rendered=self.template.render(messages=messages,add_generation_prompt=True,tools=None)
        key=digest(rendered);file=self.directory/(key+'.json')
        if file.exists():return json.loads(file.read_text())['count']
        result=None
        for attempt in range(3):
            if attempt:time.sleep((2,8)[attempt-1])
            try:
                start=time.monotonic();result=self.connection.call('/tokenize',dict(model=C['model'],prompt=rendered,add_special_tokens=False),timeout=20)
                with (self.directory/'metadata_calls.jsonl').open('a') as f:f.write(json.dumps(dict(key=key,attempt=attempt+1,status='ok',seconds=time.monotonic()-start))+'\n')
                break
            except Exception as exc:
                with (self.directory/'metadata_calls.jsonl').open('a') as f:f.write(json.dumps(dict(key=key,attempt=attempt+1,status='error',error=type(exc).__name__))+'\n')
                if attempt==2:raise TransportIncomplete('tokenizer_unavailable:'+type(exc).__name__) from None
        if type(result.get('count')) is not int or result.get('max_model_len')!=self.context:raise ProtocolMismatch('tokenizer_context_metadata')
        atomic_json(file,dict(prompt_sha256=key,count=result['count'],context=self.context,counter_id=self.counter_id))
        return result['count']


class OnlineTransport:
    def __init__(self,connection,log):self.abort=None;self.connection=connection;self.log=Path(log);self.log.parent.mkdir(parents=True,exist_ok=True)
    def record(self,rec):
        with self.log.open('a') as f:f.write(json.dumps(rec,allow_nan=False)+'\n')
    def verify(self,response,request,store):
        reason=None
        if response.get('origin')!='qwen_endpoint':reason='non_Qwen_response_origin'
        elif type(response.get('n_in')) is not int or response['n_in']!=request['input_tokens']:reason='completion_prompt_usage_disagrees_with_tokenizer'
        elif type(response.get('n_out')) is not int or not 0<=response['n_out']<=request['payload']['max_tokens']:reason='completion_token_usage_missing_or_over_budget'
        if reason:
            store.quarantine(request['key'],reason)
            if self.abort is not None:self.abort.set()
            raise ProtocolMismatch(reason)
        return response
    def completion(self,request,store):
        while True:
            if self.abort is not None and self.abort.is_set():raise TransportIncomplete('run_aborted')
            reservation=store.reserve(request)
            if reservation['state']=='cache_hit':return self.verify(dict(reservation['response'],cache_hit=True),request,store)
            if reservation['state']!='reserved':raise TransportIncomplete(reservation['state'])
            number=reservation['attempt'];time.sleep(reservation['backoff_seconds']);start=time.monotonic()
            try:raw=self.connection.call('/chat/completions',request['payload'],timeout=reservation['timeout_seconds'])
            except urllib.error.HTTPError as exc:
                if exc.code not in (408,429,500,502,503,504):
                    response=dict(text='',finish_reason='protocol_error',origin='qwen_endpoint',protocol_error='HTTP_'+str(exc.code),n_in=None,n_out=None)
                    store.finish(request['key'],number,response=response);self.record(dict(key=request['key'],stage=request['stage'],task_hash=request['task_hash'],attempt=number,status='protocol_error',http_status=exc.code,seconds=time.monotonic()-start));return self.verify(response,request,store)
                store.finish(request['key'],number,transport_error=True);self.record(dict(key=request['key'],stage=request['stage'],task_hash=request['task_hash'],attempt=number,status='transport_error',http_status=exc.code,seconds=time.monotonic()-start,usage='unknown'));continue
            except (urllib.error.URLError,TimeoutError,ConnectionError,OSError) as exc:
                store.finish(request['key'],number,transport_error=True);self.record(dict(key=request['key'],stage=request['stage'],task_hash=request['task_hash'],attempt=number,status='transport_error',error=type(exc).__name__,seconds=time.monotonic()-start,usage='unknown'));continue
            except (ValueError,KeyError,TypeError) as exc:
                response=dict(text='',finish_reason='protocol_error',origin='qwen_endpoint',protocol_error=type(exc).__name__,n_in=None,n_out=None)
                store.finish(request['key'],number,response=response);self.record(dict(key=request['key'],stage=request['stage'],task_hash=request['task_hash'],attempt=number,status='protocol_error',seconds=time.monotonic()-start));return self.verify(response,request,store)
            try:
                choice=raw['choices'][0];text=choice['message']['content'];usage=raw.get('usage',{})
                if type(text) is not str:raise ValueError('content_type')
                response=dict(text=self.connection.redact(text),finish_reason=choice.get('finish_reason'),origin='qwen_endpoint',n_in=usage.get('prompt_tokens'),n_out=usage.get('completion_tokens'),cache_hit=False)
            except (ValueError,KeyError,TypeError,IndexError) as exc:response=dict(text='',finish_reason='protocol_error',origin='qwen_endpoint',protocol_error='malformed_completion',n_in=None,n_out=None)
            store.finish(request['key'],number,response=response)
            self.record(dict(key=request['key'],stage=request['stage'],task_hash=request['task_hash'],attempt=number,status='response_received',n_in=response['n_in'],n_out=response['n_out'],finish_reason=response['finish_reason'],seconds=time.monotonic()-start))
            return self.verify(response,request,store)
