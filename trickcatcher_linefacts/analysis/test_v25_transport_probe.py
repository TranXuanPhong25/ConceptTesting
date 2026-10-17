"""Authored HTTP controls; never contacts live model or simulates a paper."""
import json
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v25_transport_probe as p


def protocol():
    req = p.read(p.gate.ROOT / 'requests/f02__meta.json')
    plain = {'model': p.CONFIG['model'], 'messages': req['messages'], 'temperature': 0,
             'top_p': 1, 'seed': req['seed'], 'max_tokens': 768}
    return {'plain': plain, 'guided': dict(plain, guided_json=req['guided_schema']), 'scope': 'authored CPU HTTP test only'}


def client(seen, fail_plain=False, bad_tokens=False):
    def handle(request):
        seen.append(request)
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': p.CONFIG['model'], 'max_model_len': 16384}]})
        if request.url.path.endswith('/tokenize'):
            return httpx.Response(200, json={'count': 384, 'max_model_len': 12 if bad_tokens else 16384})
        if fail_plain:
            return httpx.Response(503, text='Unavailable ' + 'https://' + 'secret.' + 'ngrok-free.dev/v1 key-secret')
        task = p.gate.task_for(p.gate.fixtures.cases()[0])
        text = json.dumps({'decision': 'proposed', 'spec_quote': task['spec'], 'input_domain': task['spec'],
                           'required_relation': 'Authored CPU relation fixture', 'uncertainty': ''})
        return httpx.Response(200, json={'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                                         'usage': {'prompt_tokens': 384, 'completion_tokens': 100}})
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_two_requests_only_guided_flag_differs(tmp_path):
    seen = []
    with client(seen) as http:
        status = p.probe(http, 'http://127.0.0.1/v1', p.redactor('http://127.0.0.1/v1', ''), protocol(), tmp_path)
    completions = [json.loads(x.content) for x in seen if x.url.path.endswith('/chat/completions')]
    assert len(completions) == 2
    assert dict(completions[0], guided_json=protocol()['guided']['guided_json']) == completions[1]
    assert all(p.read(tmp_path / (mode + '_response.json'))['interface_state'] == 'valid' for mode in ('plain', 'guided'))
    assert status['state'] == 'finished'


def test_plain_failure_blocks_guided_and_redacts_http_body(tmp_path):
    seen = []
    with client(seen, fail_plain=True) as http:
        p.probe(http, 'http://127.0.0.1/v1', p.redactor('http://127.0.0.1/v1', 'key-secret'), protocol(), tmp_path)
    assert sum(x.url.path.endswith('/chat/completions') for x in seen) == 1
    attempt = p.read(tmp_path / 'plain_attempt.json')
    assert attempt['http_status'] == 503 and attempt['state'] == 'http_error_usage_unknown'
    assert 'ngrok' not in attempt['body_redacted'] and 'key-secret' not in attempt['body_redacted']
    assert p.read(tmp_path / 'results.json')['guided']['state'] == 'blocked_after_failure'


def test_interrupted_reservation_is_never_retried(tmp_path):
    path = tmp_path / 'attempt.json'; p.immutable(path, {'state': 'reserved_usage_unknown'})
    def forbidden(request):
        raise AssertionError('No retry of an uncertain reservation')
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as http:
        result = p.http_once(http, 'http://127.0.0.1/v1/chat/completions', {}, path, lambda x: x, 1)
    assert result['state'] == 'reserved_usage_unknown'


def test_metadata_mismatch_stops_before_completion(tmp_path):
    seen = []
    with client(seen, bad_tokens=True) as http:
        result = p.probe(http, 'http://127.0.0.1/v1', lambda x: x, protocol(), tmp_path)
    assert result['state'] == 'preflight_failed'
    assert not any(x.url.path.endswith('/chat/completions') for x in seen)


def test_json_escaped_secrets_are_redacted_after_decoding():
    base = 'https://' + 'secret.' + 'ngrok-free.dev/v1'
    clean = p.redactor(base, 'key-secret')
    raw = json.dumps({'message': base + ' key-secret'}).replace('/', '\\/').replace('secret', '\\u0073ecret')
    decoded = json.loads(clean(raw))
    assert 'ngrok' not in decoded['message'] and 'key-secret' not in decoded['message']
    assert clean('not JSON \\u0068ttps:\\/\\/secret.ngrok-free.dev') == '<omitted_non_JSON_escaped_body>'
    nested = json.dumps({'required_relation': base + ' key-secret'}).replace('/', '\\/').replace('secret', '\\u0073ecret')
    decoded = json.loads(clean(json.dumps({'choices': [{'message': {'content': nested}}]})))
    assert decoded['choices'][0]['message']['content'] == '<redacted_encoded_secret>'
