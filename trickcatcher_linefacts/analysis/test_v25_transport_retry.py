"""Local privacy controls for the new wrapper only; no network."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v25_transport_retry import safe_redactor


def test_bare_and_nested_encoded_hostname_are_not_persisted():
    hostname = 'example.' + 'ngrok-free.dev'
    clean = safe_redactor('https://' + hostname + '/v1', '')
    assert hostname not in clean('The endpoint ' + hostname + ' is offline ERR_NGROK_3200')
    encoded = ''.join('\\u%04x' % ord(c) for c in hostname)
    nested = json.dumps({'relation': hostname}).replace(hostname, encoded)
    assert clean(json.dumps({'content': nested})) == '<omitted_encoded_hostname_body>'


def test_normal_json_and_secret_redaction_remain_usable():
    clean = safe_redactor('http://127.0.0.1/v1', 'secret-key')
    assert json.loads(clean('{"data":[],"value":16384}')) == {'data': [], 'value': 16384}
    assert 'secret-key' not in clean('{"message":"secret-key"}')
