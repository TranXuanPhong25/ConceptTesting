"""One scheduled, two-call transport probe; frozen v25 files are read-only inputs."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit

import httpx
from jinja2.sandbox import SandboxedEnvironment

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v25_interface_gate import gate
from trickcatcher_linefacts.pipelines.v25_interface_gate.common import digest, immutable, strict_json, write_json
from trickcatcher_linefacts.pipelines.v25_interface_gate.interfaces import parse
from trickcatcher_linefacts.pipelines.v25_interface_gate.paths import CONFIG

ROOT = REPO / 'trickcatcher_linefacts/out/transport_probes/v25_20261017_140806'
DUE = '2026-10-17T14:08:06+00:00'
MAX_BODY = 1024 * 1024


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def verify_original():
    original = gate.ROOT
    protocol = read(original / 'protocol.json')
    assert gate.source_files() == protocol['sources'], 'source_drift'
    assert digest(read(original / 'prepared.json')) == protocol['prepared_hash'], 'prepared_drift'
    snapshot = read(original / 'run_frozen.json')
    assert all(hashlib.sha256((original / name).read_bytes()).hexdigest() == sha for name, sha in snapshot.items()), 'original_run_drift'
    return {'sources': protocol['sources'], 'original_snapshot_hash': digest(snapshot)}


def prepare(root=ROOT):
    request = read(gate.ROOT / 'requests/f02__meta.json')
    payload = {'model': CONFIG['model'], 'messages': request['messages'], 'temperature': 0,
               'top_p': 1, 'seed': request['seed'], 'max_tokens': 768}
    protocol = {'due_utc': DUE, 'source': verify_original(),
                'probe_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'plain': payload, 'guided': dict(payload, guided_json=request['guided_schema']),
                'physical_completion_cap': 2, 'attempts_per_slot': 1,
                'scope': 'transport only; plain first; skip guided if plain transport/protocol fails; no diagnostic5 chaining'}
    return immutable(root / 'protocol.json', protocol)


def endpoint():
    raw = os.environ.get('QWEN_BASE_URL', '').rstrip('/')
    parsed = urlsplit(raw); host = parsed.hostname or ''
    local = host in ('localhost', '127.0.0.1', '::1')
    tunnel = any(host.endswith('.' + x) for x in ('ngrok-free.dev', 'ngrok.dev', 'ngrok-free.app', 'ngrok.app', 'ngrok.io'))
    if (parsed.scheme not in ('https', 'http') or not (local or tunnel) or (not local and parsed.scheme != 'https')
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('missing_or_invalid_endpoint')
    return raw if raw.endswith('/v1') else raw + '/v1'


def redactor(base, key):
    def literal(text):
        for secret in (base, base[:-3], key):
            if secret:
                text = text.replace(secret, '<redacted>')
        pattern = r'https?://[^\s<>"\x27]*ngrok[^\s<>"\x27]*'
        text = re.sub(pattern, '<redacted>', text)
        # Scan escaped nested model content too; preserve text unless it encodes a secret.
        scan = text
        for _ in range(8):
            expanded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)),
                              scan.replace('\\\\', '\\').replace('\\/', '/'))
            if expanded == scan:
                break
            scan = expanded
        if scan != text and (any(secret and secret in scan for secret in (base, base[:-3], key))
                             or re.search(pattern, scan)):
            return '<redacted_encoded_secret>'
        return text
    def walk(value):
        if type(value) is str:
            return literal(value)
        if type(value) is list:
            return [walk(x) for x in value]
        if type(value) is dict:
            return {literal(k): walk(v) for k, v in value.items()}
        return value
    def clean(text):
        try:
            return json.dumps(walk(strict_json(text, max_bytes=MAX_BODY)), ensure_ascii=False)
        except ValueError:
            if '\\u' in text or '\\/' in text:
                return '<omitted_non_JSON_escaped_body>'
            return literal(text)
    return clean


def http_once(client, url, payload, path, redact, timeout):
    """Durably reserve before sending. Existing reservation is never retried."""
    if path.exists():
        return read(path)
    record = {'state': 'reserved_usage_unknown', 'started_at': now(), 'attempt': 1}
    immutable(path, record); started = time.monotonic(); body = bytearray()
    try:
        with client.stream('GET' if payload is None else 'POST', url, json=payload, timeout=timeout) as response:
            record['http_status'] = response.status_code
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BODY:
                    raise ValueError('body_limit')
        record.update(state='received' if 200 <= record['http_status'] < 300 else 'http_error_usage_unknown')
    except (httpx.HTTPError, ValueError) as exc:
        record.update(state='transport_error_usage_unknown', error_type=type(exc).__name__)
    finally:
        record.update(seconds=time.monotonic() - started, finished_at=now(), body_bytes=len(body),
                      body_sha256=hashlib.sha256(body).hexdigest(),
                      body_redacted=redact(bytes(body[:MAX_BODY]).decode(errors='replace')),
                      body_truncated=len(body) > MAX_BODY)
        write_json(path, record)
    return record


def decode(record):
    if record['state'] != 'received':
        raise ValueError('transport_unavailable')
    return strict_json(record['body_redacted'], max_bytes=MAX_BODY)


def probe(client, base, redact, protocol, root=ROOT):
    status = {'state': 'running', 'started_at': now(), 'scope': protocol['scope']}
    write_json(root / 'status.json', status)
    try:
        models = decode(http_once(client, base + '/models', None, root / 'models.json', redact, 15))
        assert type(models) is dict and type(models.get('data')) is list, 'model_metadata_shape'
        assert any(type(x) is dict and x.get('id') == CONFIG['model'] and x.get('max_model_len') == 16384 for x in models['data']), 'pinned_model_context'
        template = SandboxedEnvironment().from_string((gate.HERE / 'chat_template.jinja').read_text())
        rendered = template.render(messages=protocol['plain']['messages'], add_generation_prompt=True, tools=None)
        tokens = decode(http_once(client, base[:-3] + '/tokenize',
            {'model': CONFIG['model'], 'prompt': rendered, 'add_special_tokens': False}, root / 'tokenize.json', redact, 20))
        assert type(tokens) is dict and type(tokens.get('count')) is int and tokens['count'] >= 0 and tokens.get('max_model_len') == 16384, 'tokenizer_protocol'
        assert tokens['count'] + 768 <= 16384, 'context_budget'
        results = {}
        for mode in ('plain', 'guided'):
            wire = protocol[mode]; immutable(root / (mode + '_request.json'), wire)
            response = http_once(client, base + '/chat/completions', wire, root / (mode + '_attempt.json'), redact, 120)
            try:
                raw = decode(response); choice = raw['choices'][0]; usage = raw['usage']; text = choice['message']['content']
                assert type(text) is str and type(usage['prompt_tokens']) is int and usage['prompt_tokens'] == tokens['count'], 'prompt_usage'
                assert type(usage['completion_tokens']) is int and 0 <= usage['completion_tokens'] <= 768, 'completion_usage'
                result = {'state': 'received', 'origin': 'qwen_endpoint', 'text': text,
                          'finish_reason': choice.get('finish_reason'), 'input_tokens': usage['prompt_tokens'],
                          'output_tokens': usage['completion_tokens'], 'seconds': response['seconds']}
                try:
                    value, payload, framing = parse('meta', text, gate.task_for(gate.fixtures.cases()[0]))
                    result.update(interface_state='valid', parsed=value, decoded_payload=payload, envelope=framing)
                except ValueError as exc:
                    result.update(interface_state='failed', interface_error=str(exc))
                immutable(root / (mode + '_response.json'), result); results[mode] = result
            except (ValueError, AssertionError, KeyError, TypeError, IndexError) as exc:
                results[mode] = {'state': 'transport_or_protocol_failed', 'error_type': type(exc).__name__,
                                 'attempt_state': response['state'], 'http_status': response.get('http_status'), 'usage': None}
                results['guided' if mode == 'plain' else 'remaining'] = {'state': 'blocked_after_failure'}
                break
        immutable(root / 'results.json', results)
        status.update(state='finished', results={k: {x: v.get(x) for x in ('state', 'interface_state', 'http_status')} for k, v in results.items()})
    except (ValueError, AssertionError, KeyError, TypeError, IndexError) as exc:
        status.update(state='preflight_failed', error_type=type(exc).__name__)
    finally:
        status['finished_at'] = now(); write_json(root / 'status.json', status)
    return status


def notify(root=ROOT):
    if (root / 'notification.json').exists():
        return
    prompt = ('Owned user-authorized v25 transport probe finished/stopped at ' + str(root) +
              '. Read status, frozen protocol and actual plain/guided attempts/responses. Verify script/v25 source hashes and old run unchanged. '
              'At most2 single-attempt completions; plain failure blocks guided. No diagnostic5/full comparison/benchmark/paid/new calls. '
              'Report transport/protocol/schema evidence, latency, actual known vs unknown usage and sequential-order/server-log limits. '
              'No endpoint disclosure, repairs or resets. Update own analysis/RESULTS/memory, commit/push own changes main, reply Vietnamese.')
    try:
        done = subprocess.run(['/usr/bin/codex', 'queue', '--thread', os.environ['CODEX_THREAD_ID'],
                               '--message', prompt, '-C', str(REPO)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        queued = done.returncode == 0
    except Exception:
        queued = False
    write_json(root / 'notification.json', {'queued': queued, 'at': now()})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=('prepare', 'online')); args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    if args.command == 'prepare':
        prepare(); return
    with (ROOT / 'controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if (ROOT / 'status.json').exists() and read(ROOT / 'status.json')['state'] not in ('scheduled',):
            return  # No retries after started, interrupted or terminal run.
        protocol = prepare(); due = dt.datetime.fromisoformat(protocol['due_utc'])
        write_json(ROOT / 'status.json', {'state': 'scheduled', 'pid': os.getpid(), 'due_utc': protocol['due_utc'], 'scope': protocol['scope']})
        while True:
            remaining = (due - dt.datetime.now(dt.timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(30, remaining))
        try:
            assert prepare() == protocol, 'source_or_protocol_drift'
            base = endpoint(); key = os.environ.get('QWEN_API_KEY', ''); redact = redactor(base, key)
            headers = {'ngrok-skip-browser-warning': '1'}
            if key: headers['Authorization'] = 'Bearer ' + key
            with httpx.Client(headers=headers, trust_env=False, follow_redirects=False) as client:
                probe(client, base, redact, protocol)
        except Exception as exc:
            write_json(ROOT / 'status.json', {'state': 'incomplete', 'error_type': type(exc).__name__, 'finished_at': now()})
        finally:
            notify()


if __name__ == '__main__':
    main()
