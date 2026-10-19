"""Single-attempt CLI turn; execution host disabled, exposed schemas disclosed."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

MODEL = 'gpt-5.6-luna'
FLAGS = ('shell_tool', 'code_mode_host', 'code_mode', 'browser_use', 'computer_use', 'apps', 'multi_agent', 'multi_agent_v2', 'view_image', 'image_generation', 'plugins', 'remote_plugin',
         'skill_search', 'skill_mcp_dependency_install', 'goals', 'standalone_web_search')
ALLOWED_ITEMS = {'agent_message', 'reasoning'}
ALLOWED_EVENTS = {'thread.started', 'turn.started', 'turn.completed', 'item.started', 'item.updated', 'item.completed'}
CONFIG_WARNINGS = {
    'Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /home/phong/.codex/config.toml.',
    'Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.'}


class ProtocolViolation(RuntimeError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'); tmp.replace(path)


def immutable(path, data):
    path = Path(path)
    if path.exists():
        if read(path) != data:
            raise ProtocolViolation('immutable_drift:' + path.name)
    else:
        write(path, data)
    return data


def command(empty, last, prompt):
    return ['codex', '--strict-config', 'exec', '--skip-git-repo-check', '--ephemeral', '--ignore-rules',
            '--ignore-user-config', '-s', 'read-only', '-C', str(empty), '-m', MODEL,
            '-c', 'model_reasoning_effort="low"',
            '-c', 'web_search="disabled"',
            '-c', 'project_doc_max_bytes=0', '-c', 'mcp_servers={}', '--enable', 'skip_host_skill_discovery',
            *[arg for feature in FLAGS for arg in ('--disable', feature)],
            '--json', '-o', str(last), prompt]


def inspect_events(stdout):
    events = []; invalid_lines = 0
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if type(event) is not dict or type(event.get('type')) is not str:
                invalid_lines += 1
                continue
            if 'item' in event and (type(event['item']) is not dict
                                    or type(event['item'].get('type')) is not str):
                invalid_lines += 1
                continue
            events.append(event)
        except ValueError:
            invalid_lines += bool(line.strip())
    forbidden = []; configuration_warnings = []; turn_started = False
    for event in events:
        if event['type'] == 'turn.started':
            turn_started = True
        item = event.get('item', {})
        if item and item['type'] not in ALLOWED_ITEMS:
            if (not turn_started and event['type'] == 'item.completed' and item['type'] == 'error'
                    and item.get('message') in CONFIG_WARNINGS):
                configuration_warnings.append(item['message'])
            else:
                forbidden.append(item['type'])
    forbidden += [e['type'] for e in events if e['type'] not in ALLOWED_EVENTS]
    observed_models = [e[k] for e in events for k in ('model', 'model_slug') if type(e.get(k)) is str]
    forbidden += ['model_mismatch'] if any(x != MODEL for x in observed_models) else []
    completed = [e for e in events if e.get('type') == 'turn.completed']
    messages = [e['item'].get('text') for e in events
                if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'agent_message']
    invalid_lines += sum(type(x) is not str for x in messages)
    usage = completed[-1].get('usage') if completed else None
    known = (type(usage) is dict and all(type(usage.get(k)) is int and usage[k] >= 0
                                       for k in ('input_tokens', 'output_tokens')))
    return {'events': events, 'invalid_lines': invalid_lines, 'forbidden_items': forbidden,
            'completed_turns': len(completed), 'messages': messages, 'usage': usage,
            'usage_known': known, 'observed_models': observed_models, 'configuration_warnings': configuration_warnings,
            'thread_starts': sum(e['type']=='thread.started' for e in events),
            'turn_starts': sum(e['type']=='turn.started' for e in events),
            'started': any(e.get('type') in ('thread.started', 'turn.started') for e in events)}


class Client:
    def __init__(self, root, slot_failure, cap):
        self.root = Path(root); self.slot_failure = slot_failure; self.cap = cap
        self.root.mkdir(parents=True, exist_ok=True)
        immutable(self.root / 'server.json', {'requested_model': MODEL, 'reasoning_effort': 'low',
                  'client': 'fresh ephemeral Codex CLI', 'disabled_features': list(FLAGS),
                  'tools_disable_defaults': 'unsupported CLI field; documented feature flags used', 'web_search': 'disabled', 'ignore_user_config': True,
                  'tool_schemas_exposed': True, 'execution_host_disabled': True,
                  'role_mapping': 'original message content flattened into role-labeled user prompt',
                  'Qwen_sampling_output_token_caps': 'not enforced by CLI; unmatched harness'})

    def complete(self, request):
        folder = self.root / 'calls' / request['slot']
        immutable(folder / 'request.json', request)
        if (folder / 'response.json').exists():
            return read(folder / 'response.json')
        ledger = folder / 'attempts.json'
        if ledger.exists():
            raise self.slot_failure('single_attempt_already_consumed_no_retry')
        if len(list((self.root / 'calls').glob('*/attempts.json'))) >= self.cap:
            raise ProtocolViolation('model_slot_cap')
        prompt = '\n\n'.join('[' + m['role'].upper() + ']\n' + m['content'] for m in request['messages'])
        immutable(folder / 'prompt.json', {'text': prompt, 'sha256': hashlib.sha256(prompt.encode()).hexdigest()})
        attempt = {'state': 'reserved_usage_unknown', 'started_at': now(), 'usage_known': False}
        write(ledger, [attempt]); start = time.monotonic(); last = folder.resolve() / 'last.txt'
        proc = None
        env = {k:v for k,v in os.environ.items() if not k.upper().endswith(('_API_KEY', '_ACCESS_TOKEN'))
               and k not in ('QWEN_BASE_URL', 'OPENAI_BASE_URL', 'CODEX_THREAD_ID')}
        try:
            with tempfile.TemporaryDirectory(prefix='luna-empty-') as empty, (folder / 'stdout.jsonl').open('wb') as stdout, (folder / 'stderr.txt').open('wb') as stderr:
                cmd = command(empty, last, prompt)
                immutable(folder / 'invocation.json', {'argv': cmd[:-1] + ['<prompt in prompt.json>'],
                           'empty_cwd': empty, 'stdin': 'DEVNULL', 'subprocess_attempt_cap': 1})
                proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                        env=env, start_new_session=True)
                attempt['pid'] = proc.pid; write(ledger, [attempt])
                try:
                    code = proc.wait(timeout=180)
                    attempt.update(state='process_finished', returncode=code)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                    attempt.update(state='timeout_usage_unknown')
        except OSError as exc:
            attempt.update(state='spawn_error', error_type=type(exc).__name__)
        attempt.update(seconds=time.monotonic()-start, finished_at=now())
        event_data = inspect_events((folder / 'stdout.jsonl').read_text(errors='replace') if (folder / 'stdout.jsonl').exists() else '')
        stderr_text = (folder / 'stderr.txt').read_text(errors='replace') if (folder / 'stderr.txt').exists() else ''
        router_attempt = 'codex_core::tools::router' in stderr_text or 'error=code-mode host is disabled' in stderr_text
        attempt.update(usage=event_data['usage'], usage_known=event_data['usage_known'],
                       started=event_data['started'], completed_turns=event_data['completed_turns'],
                       forbidden_items=event_data['forbidden_items'], observed_models=event_data['observed_models'],
                       configuration_warnings=event_data['configuration_warnings'], denied_router_attempt=router_attempt)
        if event_data['usage_known']:
            attempt.update(input_tokens=event_data['usage']['input_tokens'], output_tokens=event_data['usage']['output_tokens'])
        write(ledger, [attempt])
        if event_data['forbidden_items'] or event_data['invalid_lines'] or router_attempt:
            attempt['state'] = 'protocol_violation'; write(ledger, [attempt])
            raise ProtocolViolation('unexpected_tool_or_event_output')
        if (attempt.get('returncode') != 0 or not last.exists() or event_data['completed_turns'] != 1
                or event_data['thread_starts'] != 1 or event_data['turn_starts'] != 1):
            attempt['failure_cause'] = attempt['state']; attempt['state'] = 'failed'; write(ledger, [attempt])
            raise self.slot_failure('CLI_failed_or_incomplete_single_attempt')
        text = last.read_text()
        if (not event_data['usage_known'] or not event_data['messages']
                or event_data['messages'][-1].rstrip('\n') != text.rstrip('\n')):
            attempt['state'] = 'protocol_violation'; write(ledger, [attempt])
            raise ProtocolViolation('CLI_usage_or_final_message_mismatch')
        result = {'text': text, 'origin': 'codex_cli_gpt-5.6-luna_low_host_disabled', 'model': MODEL,
                  'tool_schemas_exposed': True, 'execution_host_disabled': True,
                  'model_identity_authority': 'requested CLI -m and local catalog; server identity only if explicitly in events',
                  'event_reported_models': event_data['observed_models'],
                  'reasoning_effort': 'low', 'finish_reason': 'stop',
                  'finish_reason_authority': 'inferred successful CLI completed turn, not raw server field',
                  'input_tokens': event_data['usage']['input_tokens'], 'output_tokens': event_data['usage']['output_tokens'],
                  'raw_CLI_usage': event_data['usage'], 'tool_executions': 0}
        immutable(folder / 'response.json', result)
        attempt['state'] = 'received'; write(ledger, [attempt])
        return result


def costs(root):
    rows = [row for p in Path(root).glob('calls/*/attempts.json') for row in read(p)]
    return {'CLI_invocations': len(rows), 'received': sum(r['state']=='received' for r in rows),
            'known_usage_attempts': sum(r.get('usage_known',False) for r in rows),
            'unknown_usage_attempts': sum(not r.get('usage_known',False) for r in rows),
            'input_tokens_known': sum(r.get('input_tokens',0) for r in rows),
            'output_tokens_known': sum(r.get('output_tokens',0) for r in rows),
            'forbidden_item_count': sum(len(r.get('forbidden_items',[])) for r in rows),
            'denied_router_attempts': sum(r.get('denied_router_attempt',False) for r in rows),
            'request_count_scope': 'CLI invocations/turns, internal server HTTP retries unobserved'}
