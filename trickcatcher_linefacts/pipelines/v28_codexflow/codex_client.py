"""Codex CLI as the oracle model: same request/response contract as flow_client, cached per prompt-digest slot.

Each call runs `codex exec` in an empty read-only directory with --ignore-rules/--ephemeral, so the model sees only
the prompt (no repo, no tools that could reach references). Token usage comes from the CLI's JSON events.
"""
import json
import subprocess
import tempfile
import time
from pathlib import Path

from .flow_common import immutable
from .paths import CONFIG

C = CONFIG['codex']


class CodexClient:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        immutable(self.root / 'server.json', dict(model=C['model'], reasoning_effort=C['reasoning_effort'], client='codex exec', disabled=C['disable_features']))

    def close(self):
        pass

    def complete(self, request):
        path = self.root / 'calls' / request['slot']
        immutable(path / 'request.json', request)
        if (path / 'response.json').exists():
            return json.loads((path / 'response.json').read_text())
        prompt = '\n\n'.join(f"[{m['role'].upper()}]\n{m['content']}" for m in request['messages'])
        attempts = json.loads((path / 'attempts.json').read_text()) if (path / 'attempts.json').exists() else []
        while len(attempts) < C['max_attempts']:
            attempts.append(dict(state='reserved'))
            (path / 'attempts.json').write_text(json.dumps(attempts))
            with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as out:
                last = Path(out) / 'last.txt'
                cmd = ['codex', 'exec', '--skip-git-repo-check', '--ephemeral', '--ignore-rules', '-s', 'read-only', '-C', empty,
                       '-m', C['model'], '-c', f"model_reasoning_effort=\"{C['reasoning_effort']}\"",
                       *[x for f in C['disable_features'] for x in ('--disable', f)], '--json', '-o', str(last), prompt]
                try:
                    proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=C['timeout_seconds'])
                except subprocess.TimeoutExpired:
                    attempts[-1].update(state='timeout')
                    continue
                usage, tool_events = {}, 0
                for line in proc.stdout.splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get('type') == 'turn.completed':
                        usage = event.get('usage', {})
                    if 'execution' in json.dumps(event.get('item', {}).get('type', '')):
                        tool_events += 1  # must stay 0: tools are disabled
                if proc.returncode != 0 or not last.exists():
                    attempts[-1].update(state='error', returncode=proc.returncode, stderr_tail=proc.stderr[-300:])
                    time.sleep(5)
                    continue
                result = dict(text=last.read_text(), origin='codex_cli', model=C['model'],
                              input_tokens=usage.get('input_tokens', 0), output_tokens=usage.get('output_tokens', 0),
                              reasoning_output_tokens=usage.get('reasoning_output_tokens', 0), tool_executions=tool_events)
            immutable(path / 'response.json', result)
            attempts[-1].update(state='received')
            (path / 'attempts.json').write_text(json.dumps(attempts))
            return result
        (path / 'attempts.json').write_text(json.dumps(attempts))
        raise RuntimeError('codex_attempts_exhausted')
