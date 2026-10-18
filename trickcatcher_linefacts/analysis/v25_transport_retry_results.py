"""Read-only evidence check for the one user-authorized 2026-10-18 retry."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v25_transport_retry as retry
old = retry.old
ROOT = old.REPO / 'trickcatcher_linefacts/out/transport_probes/v25_20261018_040624'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=old.read(ROOT/'protocol.json'); s=old.read(ROOT/'status.json'); a=old.read(ROOT/'models.json')
    assert sha(HERE/'v25_transport_retry.py') == p['wrapper_sha256']
    assert sha(Path(old.__file__)) == p['probe_script_sha256']
    assert old.verify_original() == p['source']
    prior=old.read(old.ROOT/'protocol.json')
    assert old.digest(prior) == p['previous_probe_protocol_hash']
    assert p['plain']==prior['plain'] and p['guided']==prior['guided']
    for name in ('v25_interface_gate_results.json','v25_transport_probe_results.json'):
        audit=old.read(HERE/name)
        root=old.gate.ROOT if name.startswith('v25_interface') else old.ROOT
        assert all(sha(root/k)==v for k,v in audit['analysis_time_evidence_hashes'].items())
    assert s['state']=='preflight_failed' and s['error_type']=='ValueError'
    assert a['http_status']==404 and a['attempt']==1 and a['state']=='http_error_usage_unknown'
    assert 'ERR_NGROK_3200' in a['body_redacted'] and 'is offline' in a['body_redacted']
    assert not re.search(r'\b[A-Za-z0-9-]+\.(?:ngrok-free|ngrok)\.(?:dev|app|io)\b',a['body_redacted'])
    for name in ('tokenize.json','plain_request.json','guided_request.json','plain_attempt.json','guided_attempt.json',
                 'plain_response.json','guided_response.json','results.json'):
        assert not (ROOT/name).exists()
    result={'run_id':ROOT.name,'callback_handled':True,'state':s['state'],'started_at':s['started_at'],
            'metadata_HTTP_attempts':1,'metadata_HTTP_status':404,'gateway_error':'ERR_NGROK_3200',
            'safe_message':'The endpoint <redacted-host> is offline.', 'models_seconds':a['seconds'],
            'wall_seconds':(dt.datetime.fromisoformat(s['finished_at'])-dt.datetime.fromisoformat(s['started_at'])).total_seconds(),
            'tokenizer_requests':0,'plain_completions':0,'guided_completions':0,'unknown_usage_completion_attempts':0,
            'completion_usage':'not_applicable_no_completion_sent','PUT_predicate_workers':0,
            'model_context_schema_semantics':'not_observed','body_recorded_original_sha256':a['body_sha256'],
            'verification':{'wrapper_and_frozen_script_hashes':True,'original_v25_sources_prepared_snapshot':True,
                            'old_diagnostic_and_probe_analysis_hashes':True,'identical_payload_pair':True,
                            'bare_hostname_guard_on_new_artifact':True,'single_attempt_no_expansion':True},
            'limits':'Gateway reports offline; no server logs or paired completions; cannot infer GPU/model/guided-decoder failure.',
            'no_new_calls_during_audit':True,'automatic_retry_or_diagnostic5':False,
            'analysis_time_evidence_hashes':{x.name:sha(x) for x in sorted(ROOT.glob('*.json'))}}
    output=Path(__file__).with_suffix('.json')
    if output.exists():
        assert old.read(output)==result
    else:
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='analysis_time_evidence_hashes'},indent=2))


if __name__=='__main__':
    main()
