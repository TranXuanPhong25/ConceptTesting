"""Read-only terminal verification: no Client, endpoint access, workers or source edits."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v25_transport_probe as probe


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = probe.ROOT; protocol = read(root / 'protocol.json'); status = read(root / 'status.json')
    assert sha(HERE / 'v25_transport_probe.py') == protocol['probe_script_sha256']
    assert probe.verify_original() == protocol['source']
    old_root = probe.gate.ROOT
    old_audit = read(HERE / 'v25_interface_gate_results.json')
    assert all(sha(old_root / name) == expected for name, expected in old_audit['analysis_time_evidence_hashes'].items())
    original_request = read(old_root / 'transport/calls/f02__meta/wire_request.json')['payload']
    assert protocol['guided'] == original_request
    assert dict(protocol['plain'], guided_json=protocol['guided']['guided_json']) == protocol['guided']
    assert protocol['physical_completion_cap'] == 2 and protocol['attempts_per_slot'] == 1
    assert status['state'] == 'preflight_failed' and status['error_type'] == 'ValueError'
    record = read(root / 'models.json')
    assert record['state'] == 'http_error_usage_unknown' and record['http_status'] == 404 and record['attempt'] == 1
    assert record['body_truncated'] is False
    assert 'ERR_NGROK_3200' in record['body_redacted'] and 'is offline' in record['body_redacted']
    # Do not export HTML or hostname: the frozen utility missed bare hostname redaction.
    host_pattern = r'\b(?:[A-Za-z0-9-]+\.)*(?:ngrok-free|ngrok)\.(?:dev|app|io|com)\b'
    bare_hosts = re.findall(host_pattern, record['body_redacted'])
    assert bare_hosts, 'Expected documented artifact privacy gap'
    for name in ('tokenize.json', 'plain_attempt.json', 'guided_attempt.json', 'plain_response.json',
                 'guided_response.json', 'plain_request.json', 'guided_request.json', 'results.json'):
        assert not (root / name).exists()
    assert (root / 'controller.log').stat().st_size == 0
    notification = read(root / 'notification.json'); assert notification['queued']
    start = dt.datetime.fromisoformat(status['started_at']); due = dt.datetime.fromisoformat(protocol['due_utc'])
    delay = (start - due).total_seconds(); assert 0 <= delay < 1
    assert dt.datetime.fromisoformat(record['started_at']) >= due
    result = {
        'scope': 'single metadata GET preflight failed; no completion, semantic or paired transport result',
        'state': status['state'], 'due_utc': protocol['due_utc'], 'started_at': status['started_at'],
        'finished_at': status['finished_at'], 'start_delay_seconds': delay,
        'probe_wall_seconds': (dt.datetime.fromisoformat(status['finished_at']) - start).total_seconds(),
        'metadata': {'path': '/v1/models', 'attempts': 1, 'http_status': 404,
                     'seconds': record['seconds'], 'error_code': 'ERR_NGROK_3200',
                     'safe_body_excerpt': 'The endpoint <redacted-host> is offline. (ERR_NGROK_3200)',
                     'recorded_original_body_bytes': record['body_bytes'],
                     'recorded_original_body_sha256': record['body_sha256'],
                     'body_sha_independently_reconstructable': False,
                     'reason': 'only sanitized body retained; original body hash is recorded evidence'},
        'stages': {'models': 'HTTP404_ngrok_endpoint_offline', 'pinned_model_context': 'not_verified',
                   'tokenizer': 'blocked_preflight', 'plain': 'blocked_preflight', 'guided': 'blocked_preflight'},
        'costs': {'HTTP_requests': 1, 'metadata_HTTP_requests': 1, 'completion_HTTP_attempts': 0,
                  'completion_response_bodies': 0, 'known_model_usage_records': 0,
                  'unknown_completion_usage_attempts': 0, 'completion_usage': 'not_applicable_no_completion_request',
                  'model_token_consumption_from_sent_completion_requests': 0,
                  'predicate_workers': 0, 'PUT_workers': 0,
                  'metadata_generic_usage_unknown_label_is_not_unknown_model_completion_usage': True},
        'verification': {'script_hash': True, 'v25_source_files': len(protocol['source']['sources']),
                         'v25_original_frozen_artifacts': len(read(old_root / 'run_frozen.json')),
                         'v25_prepared_hash': True, 'old_run_transport_status_report_hashes_unchanged': True,
                         'exact_old_f02_payload_pair_only_guided_flag_differs': True,
                         'attempt_cap_preserved': True, 'no_network_before_due': True},
        'privacy': {'bare_hostname_present_in_original_error_body': True,
                    'original_artifact_preserved_per_instruction': True,
                    'no_hostname_or_full_body_copied_to_analysis': True,
                    'future_redactor_hardening_required': True,
                    'frozen_utility_and_originals_not_repaired': True},
        'limits': ['Gateway explicitly reports endpoint offline; no server logs to identify why tunnel or upstream stopped.',
                   'No response from pinned Qwen model; no protocol/schema/semantic judgment.',
                   'Neither plain nor guided ran, so no paired comparison; scheduled order would also confound causal claims.',
                   'Generic http_error_usage_unknown on a models GET is not a sent completion with unknown usage.',
                   'Old v25 eight unknown-usage completion attempts remain separate; not reset or counted as this probe.'],
        'callback_handled': True, 'new_calls_during_audit': 0, 'advance_to_diagnostic5': False,
        'analysis_time_evidence_hashes': {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()}}
    output = Path(__file__).with_suffix('.json')
    if output.exists():
        assert read(output) == result
    else:
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'analysis_time_evidence_hashes'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
