"""Fresh authorized transport retry using the frozen probe; old namespaces stay read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v25_transport_probe as old


def safe_redactor(base, key):
    legacy = old.redactor(base, key)
    host = r'\b(?:[A-Za-z0-9-]+\.)*(?:ngrok-free|ngrok)\.(?:dev|app|io|com)\b'
    def clean(text):
        result = re.sub(host, '<redacted-host>', legacy(text), flags=re.IGNORECASE)
        scan = result
        for _ in range(8):
            decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)),
                             scan.replace('\\\\', '\\').replace('\\/', '/'))
            if decoded == scan:
                break
            scan = decoded
        return '<omitted_encoded_hostname_body>' if re.search(host, scan, re.IGNORECASE) else result
    return clean


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True); args = parser.parse_args()
    if not re.fullmatch(r'v25_\d{8}_\d{6}', args.run_id):
        raise SystemExit('invalid_run_id')
    root = old.REPO / 'trickcatcher_linefacts/out/transport_probes' / args.run_id
    root.mkdir(parents=True, exist_ok=False)  # Never reuse any existing run, terminal or interrupted.
    prior = old.read(old.ROOT / 'protocol.json')
    assert hashlib.sha256(Path(old.__file__).read_bytes()).hexdigest() == prior['probe_script_sha256']
    assert old.verify_original() == prior['source']
    protocol = dict(prior, due_utc=old.now(), authorization='user explicit fresh retry 2026-10-18',
                    wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    previous_probe_protocol_hash=old.digest(prior),
                    privacy_adapter='mask bare/encoded tunnel hostname before persistence; no prompt/schema change')
    old.immutable(root / 'protocol.json', protocol)
    try:
        base = old.endpoint(); key = os.environ.get('QWEN_API_KEY', '')
        headers = {'ngrok-skip-browser-warning': '1'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        with httpx.Client(headers=headers, trust_env=False, follow_redirects=False) as client:
            old.probe(client, base, safe_redactor(base, key), protocol, root)
    except Exception as exc:
        old.write_json(root / 'status.json', {'state': 'incomplete', 'error_type': type(exc).__name__, 'finished_at': old.now()})
    finally:
        old.notify(root)


if __name__ == '__main__':
    main()
