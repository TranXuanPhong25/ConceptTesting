"""One exact frozen v81 prompt each on Relace then Reka; no retry or v81 score."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.stream_wire import dispatch,parse_sse,known_cost

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PIPE=REPO/'trickcatcher_linefacts/pipelines/v81_deepinfra_quarter'
OLD=PIPE/'out/deepinfra_quarter_resume2_20261027'
CAP=Decimal('0.12')
MODEL='deepseek/deepseek-v4-flash-0731'
ENDPOINTS=HERE/'provider_trial_endpoints_20261027.json'
PROMPT_PATH=HERE/'provider_trial_prompt_final3.json'
PLAN_PATH=HERE/'provider_trial_plan_final3.json'
RESULT_PATH=HERE/'provider_trial_results_final3.json'
ROUTES=[
    {'tag':'relace/fp4','name':'Relace','input':Decimal('.05'),'output':Decimal('.18')},
    {'tag':'reka','name':'Reka','input':Decimal('.05'),'output':Decimal('.28')},
]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    return {'provider_trial.py':sha(Path(__file__)),
            'stream_wire.py':sha(PIPE/'stream_wire.py'),
            'paths.py':sha(PIPE/'paths.py'),
            'config.json':sha(PIPE/'config.json'),
            'PROVIDER_TRIAL_PREREG.md':sha(HERE/'PROVIDER_TRIAL_PREREG.md'),
            'PROVIDER_TRIAL_REVIEW.md':sha(HERE/'PROVIDER_TRIAL_REVIEW.md')}


def payload(messages,route):
    return {'model':MODEL,'stream':True,'messages':messages,'temperature':.6,'top_p':.95,
            'max_tokens':131072,'response_format':{'type':'text'},'reasoning':{'enabled':True},
            'provider':{'only':[route['tag']],'allow_fallbacks':False,'require_parameters':True,
                        'max_price':{'prompt':float(route['input']),'completion':float(route['output']),'request':0}}}


def prepare():
    if PLAN_PATH.exists() or RESULT_PATH.exists():raise ValueError('trial_already_prepared_or_terminal')
    metadata=json.loads(ENDPOINTS.read_text())['data']
    if metadata.get('id')!=MODEL:raise ValueError('model_metadata_drift')
    # Use the exact request messages already frozen for the canceled logical slot.
    key='chat/96421f0db5337313cb79041fbf5be21cbdf2823512f7e050ebe05f81e9b7d30d'
    request=json.loads((OLD/'transport/calls'/key/'request.json').read_text())
    messages=request['messages']
    if [m['role'] for m in messages]!=['system','user']:raise ValueError('prompt_role_drift')
    prompt_bound=2*len(json.dumps(messages,ensure_ascii=True).encode())+4096
    jobs=[]
    for route in ROUTES:
        e=next((x for x in metadata['endpoints'] if x.get('tag')==route['tag']),None)
        required={'reasoning','max_tokens','temperature','top_p','response_format'}
        if not e or e.get('status')!=0 or not required<=set(e.get('supported_parameters') or []):
            raise ValueError('provider_unavailable_or_parameter_mismatch:'+route['tag'])
        if e.get('max_completion_tokens',0)<131072 or prompt_bound+131072>e.get('context_length',0):
            raise ValueError('provider_context_limit:'+route['tag'])
        rates=e['pricing']
        if Decimal(rates['prompt'])*1000000>route['input'] or Decimal(rates['completion'])*1000000>route['output']:
            raise ValueError('provider_price_ceiling:'+route['tag'])
        wire=payload(messages,route)
        maximum=(Decimal(prompt_bound)*route['input']+Decimal(131072)*route['output'])/Decimal(1000000)
        jobs.append({'route':route['tag'],'name':route['name'],'wire':wire,'prompt_envelope':prompt_bound,
                     'context':e['context_length'],'max_completion':e['max_completion_tokens'],
                     'metadata_price':rates,'worstcase_usd':str(maximum),
                     'payload_sha256':hashlib.sha256(json.dumps(wire,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
    if sum(Decimal(j['worstcase_usd']) for j in jobs)>CAP:raise ValueError('trial_cap_insufficient')
    prompt_hash=hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()
    PROMPT_PATH.write_text(json.dumps({'origin':'frozen canceled v81 logical request; no prompt edits',
                                       'messages_sha256':prompt_hash,'messages':messages},indent=2)+'\n')
    plan={'model':MODEL,'routes':jobs,
          'prior_v81_slot':key,'prompt_sha256':prompt_hash,'combined_cap_usd':str(CAP),
          'sum_worstcase_usd':str(sum(Decimal(j['worstcase_usd']) for j in jobs)),
          'endpoint_metadata_sha256':sha(ENDPOINTS),
          'prior_v81_protocol_sha256':sha(OLD/'protocol.json'),
          'source_files':source_files(),
          'created_utc':datetime.now(timezone.utc).isoformat()}
    PLAN_PATH.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'prepared':True,'prompt_sha256':prompt_hash,'combined_worstcase_usd':plan['sum_worstcase_usd'],
                      'routes':[{'provider':x['route'],'reserve':x['worstcase_usd']} for x in jobs]}),flush=True)


def run():
    if RESULT_PATH.exists():raise ValueError('trial_already_terminal')
    plan=json.loads(PLAN_PATH.read_text())
    if sha(ENDPOINTS)!=plan['endpoint_metadata_sha256'] or sha(OLD/'protocol.json')!=plan['prior_v81_protocol_sha256']:
        raise ValueError('endpoint_metadata_drift')
    if source_files()!=plan['source_files']:raise ValueError('trial_source_or_review_drift')
    if hashlib.sha256((OLD/'protocol.json').read_bytes()).hexdigest()!=plan['prior_v81_protocol_sha256']:
        raise ValueError('v81_protocol_drift')
    messages=json.loads(PROMPT_PATH.read_text())['messages']
    if hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()!=plan['prompt_sha256']:
        raise ValueError('frozen_prompt_drift')
    results=[];spent=Decimal(0);reserve=Decimal(0);stop=None
    for job in plan['routes']:
        route=next(r for r in ROUTES if r['tag']==job['route'])
        wire=payload(messages,route)
        if hashlib.sha256(json.dumps(wire,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=job['payload_sha256']:
            raise ValueError('provider_payload_drift')
        bound=Decimal(job['worstcase_usd'])
        if spent+reserve+bound>CAP:stop='combined_cap_before_dispatch';break
        folder=HERE/'provider_trial_calls'/route['tag'].replace('/','_');folder.mkdir(parents=True,exist_ok=False)
        (folder/'wire.json').write_text(json.dumps(wire,indent=2)+'\n')
        attempt={'state':'dispatched_cost_unknown','provider':route['tag'],'reservation_usd':str(bound),
                 'payload_sha256':job['payload_sha256'],'time_utc':datetime.now(timezone.utc).isoformat()}
        (folder/'attempt.json').write_text(json.dumps(attempt,indent=2)+'\n')
        response,raw,stderr=dispatch(folder/'wire.json')
        (folder/'response.sse').write_text(raw);(folder/'stderr.txt').write_text(stderr)
        row={'provider':route['tag'],'response':response,'worstcase_reservation_usd':str(bound)}
        try:
            actual=known_cost(response);spent+=actual;row['known_cost_usd']=str(actual)
        except ValueError:
            actual=None;reserve+=bound;row['known_cost_usd']=None;row['billing']='unknown; full reservation retained'
        if actual is not None and actual>bound:
            row['status']='provider_cost_exceeded_reservation';results.append(row)
            (folder/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
            stop='actual_cost_exceeded_reserved_bound';break
        if response.get('stream_error'):
            row['status']='error_or_incomplete'
            try:
                err=json.loads(raw).get('error',{});meta=err.get('metadata') or {}
                row['http_error_code']=err.get('code');row['provider_error']=meta.get('provider_name')
                row['limit_source']=meta.get('limit_source')
            except (ValueError,AttributeError):pass
        else:
            row['status']='response_received'
            if response.get('model')!=MODEL or response.get('provider')!=route['name']:
                row['status']='served_package_mismatch';results.append(row)
                (folder/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
                stop='served_model_or_provider_mismatch';break
        (folder/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
        results.append(row)
        if response.get('stream_error') and any(f'api_error:{code}' in response['stream_error'] for code in (401,402,403)):
            stop='authentication_denied';break
        # Routes were separately and explicitly requested; continue to the next
        # route after provider-specific throttling while retaining its reserve.
    terminal={'model':MODEL,'results':results,'known_cost_usd':str(spent),
              'unresolved_reservation_usd':str(reserve),'combined_cap_usd':str(CAP),
              'worstcase_if_all_reserved_usd':str(spent+reserve),
              'stop_reason':stop,'efficacy_claim':None,'finished_utc':datetime.now(timezone.utc).isoformat()}
    RESULT_PATH.write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal),flush=True)


if __name__=='__main__':
    if sys.argv[1:]!=['--prepare'] and sys.argv[1:]!=['--run']:
        raise SystemExit('use --prepare or --run')
    prepare() if sys.argv[1]=='--prepare' else run()
