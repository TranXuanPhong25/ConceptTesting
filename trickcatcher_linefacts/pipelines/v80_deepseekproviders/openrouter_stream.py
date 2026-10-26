"""Bounded curl-N SSE transport; credentials exist only in environment/stdin."""
from decimal import Decimal,InvalidOperation
import json
import os
from pathlib import Path
import subprocess
import tempfile

MODEL='deepseek/deepseek-v4-flash-0731'
URL='https://openrouter.ai/api/v1/chat/completions'
ROUTES={
    'reka':{'name':'Reka','cap':'0.17','prompt':0.05,'completion':0.28},
    'deepinfra/fp8':{'name':'DeepInfra','cap':'0.12','prompt':0.06,'completion':0.18},
}
ROUTE=os.environ.get('V80_PROVIDER','reka')
if ROUTE not in ROUTES:raise ValueError('provider_must_be_reka_or_deepinfra_fp8')
SETTINGS=ROUTES[ROUTE]
PROVIDER={'only':[ROUTE],'allow_fallbacks':False,'require_parameters':True,
          'max_price':{'prompt':SETTINGS['prompt'],'completion':SETTINGS['completion'],'request':0}}
MAX_TOKENS=131072


def payload(messages):
    return {'model':MODEL,'stream':True,'messages':messages,'temperature':0.2,'top_p':0.95,
            'max_tokens':MAX_TOKENS,'response_format':{'type':'json_object'},
            'reasoning':{'enabled':True},'provider':PROVIDER}


def prompt_envelope(request):
    return 2*len(json.dumps(request['messages'],ensure_ascii=True).encode())+4096


def reservation(request):
    # Token count cannot exceed serialized UTF8 byte count plus a deliberately
    # loose chat-template overhead for these two-message text-only requests.
    prompt_bound=prompt_envelope(request)
    maximum=request['provider']['max_price']
    return (Decimal(prompt_bound)*Decimal(str(maximum['prompt']))+
            Decimal(request['max_tokens'])*Decimal(str(maximum['completion'])))/Decimal(1000000)


def parse_sse(text):
    events=[];data=[];malformed=False
    for line in text.splitlines()+['']:
        if line.startswith(':'):continue
        if line.startswith('data:'):data.append(line[5:].lstrip(' '))
        elif not line and data:
            value='\n'.join(data);data=[]
            if value=='[DONE]':events.append('[DONE]')
            else:
                try:events.append(json.loads(value))
                except (ValueError,TypeError):malformed=True
    result={'content':'','finish_reason':None,'usage':None,'provider':None,'model':None,
            'generation_id':None,'done':False,'stream_error':None,'event_count':len(events)}
    if not events:
        try:
            plain=json.loads(text);error=plain.get('error')
            result['stream_error']='api_error:'+str(error.get('code','unknown'))if isinstance(error,dict)else 'non_sse_response'
        except (ValueError,TypeError,AttributeError):result['stream_error']='non_sse_response'
        return result
    contents=[]
    for event in events:
        if event=='[DONE]':result['done']=True;continue
        if result['done']:
            result['stream_error']='data_after_done';continue
        if not isinstance(event,dict):malformed=True;continue
        if 'error'in event:
            error=event['error'];code=error.get('code','unknown')if isinstance(error,dict)else 'unknown'
            result['stream_error']='api_error:'+str(code)[:80]
        for src,dest in (('provider','provider'),('model','model'),('id','generation_id')):
            if event.get(src)is not None:
                if result[dest]is not None and result[dest]!=event[src]:
                    result['stream_error']='conflicting_stream_'+dest
                result[dest]=event[src]
        if isinstance(event.get('usage'),dict):result['usage']=event['usage']
        for choice in event.get('choices',[]):
            if choice.get('index',0)!=0:continue
            content=(choice.get('delta')or{}).get('content')
            if isinstance(content,str):contents.append(content)
            elif content is not None:malformed=True
            finish=choice.get('finish_reason')
            if finish is not None:
                if result['finish_reason']is not None and result['finish_reason']!=finish:
                    result['stream_error']='conflicting_finish_reason'
                result['finish_reason']=finish
    result['content']=''.join(contents)
    if malformed:result['stream_error']='invalid_sse_frame'
    elif not result['done']and result['stream_error']is None:result['stream_error']='missing_done'
    elif result['finish_reason']is None and result['stream_error']is None:result['stream_error']='missing_finish_reason'
    return result


def known_cost(result):
    usage=result.get('usage')
    if not isinstance(usage,dict):raise ValueError('missing_usage_stop_paid_calls')
    if type(usage.get('prompt_tokens'))is not int or type(usage.get('completion_tokens'))is not int:
        raise ValueError('missing_token_usage_stop_paid_calls')
    if isinstance(usage.get('cost'),bool):raise ValueError('invalid_cost_stop_paid_calls')
    try:cost=Decimal(str(usage.get('cost')))
    except InvalidOperation:raise ValueError('missing_cost_stop_paid_calls')from None
    if not cost.is_finite()or cost<0:raise ValueError('invalid_cost_stop_paid_calls')
    return cost


def curl_command(request_path):
    return ['curl','-N','--silent','--show-error','--fail-with-body','--connect-timeout','20',
            '--max-time','360','--max-filesize','16777216','--config','-',
            '--data-binary','@'+str(request_path)]


def dispatch(request_path):
    key=os.environ.get('OPENROUTER_API_KEY','')
    if not key:raise ValueError('missing_openrouter_key')
    if any(c in key for c in ('\n','\r','"','\\')):raise ValueError('invalid_key_configuration')
    if os.environ.get('OPENROUTER_BASE_URL','https://openrouter.ai/api/v1').rstrip('/')!='https://openrouter.ai/api/v1':
        raise ValueError('official_openrouter_endpoint_required')
    config=f'url = "{URL}"\nheader = "Content-Type: application/json"\nheader = "Authorization: Bearer {key}"\n'
    # Secret is not in command arguments, payload, filesystem, stderr or logs.
    with tempfile.TemporaryFile()as raw,tempfile.TemporaryFile()as errors:
        process=subprocess.Popen(curl_command(request_path),stdin=subprocess.PIPE,stdout=raw,stderr=errors)
        try:process.communicate(config.encode(),timeout=380)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
        raw.seek(0);body=raw.read(16777217)
        errors.seek(0);stderr=errors.read(16000)
    if len(body)>16777216:raise ValueError('sse_response_size_limit')
    text=body.decode('utf-8',errors='replace').replace(key,'<redacted>')
    stderr=stderr.decode('utf-8',errors='replace').replace(key,'<redacted>')
    result=parse_sse(text)
    result['curl_exit_code']=process.returncode
    if process.returncode and result['stream_error']is None:result['stream_error']='curl_transport_failure'
    return result,text,stderr
