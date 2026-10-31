"""Publish honest, ledger-derived audit counts; never infer read from download."""
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'
REPO = ROOT.parents[1]


def _find_rate_limits(value):
    if isinstance(value, dict):
        if isinstance(value.get('rate_limits'), dict):
            return value['rate_limits']
        for child in value.values():
            found = _find_rate_limits(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_rate_limits(child)
            if found is not None:
                return found
    return None


def latest_local_rate_limits():
    """Read quota fields only from the newest recent Codex session events."""
    session_root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'sessions'
    if not session_root.is_dir():
        return None
    files = sorted(session_root.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
    latest = None
    for path in files:
        try:
            with path.open(errors='replace') as stream:
                for line in stream:
                    if '"rate_limits"' not in line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    limits = _find_rate_limits(event)
                    timestamp = event.get('timestamp')
                    if limits is None or not timestamp:
                        continue
                    if latest is None or timestamp > latest[0]:
                        latest = (timestamp, limits, path.name)
        except OSError:
            continue
    return latest


def refresh_quota_checkpoint(path):
    """Prefer newer local live telemetry; retain an explicit user report if no newer event exists."""
    live = latest_local_rate_limits()
    if live is None:
        return
    timestamp, limits, filename = live
    current = json.loads(path.read_text()) if path.exists() else {}
    if timestamp <= current.get('telemetry_timestamp', ''):
        return
    primary = limits.get('primary') or {}
    weekly = limits.get('secondary') or {}
    def reset_iso(value):
        return datetime.fromtimestamp(value, ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds') if value else None
    try:
        event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
    except ValueError:
        event_time = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
    prior_user_note = current.get('user_reported_reset_at')
    current.pop('primary_used_percent', None)
    current.pop('weekly_used_percent', None)
    current.update({
        'checked_at': event_time.isoformat(timespec='seconds'),
        'telemetry_timestamp': timestamp,
        'telemetry_source': f'newest local rate_limits event in {filename}',
        'quota_status': 'live_verified',
        # Local rate_limits uses `used_percent` (consumed). Store both the raw
        # field and the complementary remaining quota shown to the user.
        'primary_used_percent': primary.get('used_percent'),
        'weekly_used_percent': weekly.get('used_percent'),
        'primary_remaining_percent': 100 - primary['used_percent'] if isinstance(primary.get('used_percent'), (int, float)) else None,
        'weekly_remaining_percent': 100 - weekly['used_percent'] if isinstance(weekly.get('used_percent'), (int, float)) else None,
        'telemetry_percent_field': 'rate_limits.*.used_percent; remaining_percent = 100 - used_percent',
        'primary_resets_at': reset_iso(primary.get('resets_at')),
        'weekly_resets_at': reset_iso(weekly.get('resets_at')),
        'quota_interpretation': (
            f'UI percentage is quota remaining per user clarification; raw telemetry used_percent is consumed. '
            f'Latest event: primary {primary.get("used_percent")}% used / '
            f'{100 - primary["used_percent"]}% remaining; weekly {weekly.get("used_percent")}% used / '
            f'{100 - weekly["used_percent"]}% remaining.'
            if isinstance(primary.get('used_percent'), (int, float)) and isinstance(weekly.get('used_percent'), (int, float))
            else 'UI percentage is quota remaining per user clarification; raw telemetry used_percent is consumed.'
        ),
    })
    if prior_user_note:
        current['user_reported_reset_at'] = prior_user_note
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')


def main():
    catalog = json.loads((ROOT / 'screened_500.json').read_text())
    reviewed = []
    reviews_dir = AUDIT / 'reviews'
    reviews_dir.mkdir(exist_ok=True)
    for path in sorted(reviews_dir.glob('*.json')):
        review = json.loads(path.read_text())
        if review.get('fulltext_read'):
            source = ROOT / review['read_path']
            assert source.is_file(), path
            assert hashlib.sha256(source.read_bytes()).hexdigest() == review['read_sha256'], path
        reviewed.append(review)
    assert len({r['rank'] for r in reviewed}) == len(reviewed)
    retrieved = [json.loads(f.read_text()) for f in ROOT.glob('papers/*/public_evidence/retrieval.json')]
    read_count = sum(r.get('fulltext_read') is True for r in reviewed)
    checked_count = sum(r.get('public_source_checked') is True for r in reviewed)
    complete_count = sum(r.get('review_complete') is True for r in reviewed)
    unread_access_blocked = sum(r.get('review_complete') is True and r.get('fulltext_read') is not True for r in reviewed)
    both = sum(r.get('fulltext_read') is True and r.get('public_source_checked') is True and r.get('review_complete') is True for r in reviewed)
    stamp = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat()
    stats = {'updated_at': stamp, 'total': 500, 'retrieval_attempted': len(retrieved),
             'retrieval_status': dict(Counter(r['retrieval_status'] for r in retrieved)),
             'fulltext_read': read_count, 'public_source_checked': checked_count,
             'review_complete': complete_count, 'read_and_verified': both,
             'unread_access_blocked': unread_access_blocked,
             'source_statuses': dict(Counter(r.get('source_status', 'unknown') for r in reviewed)),
             'locally_reproduced': sum(r.get('locally_reproduced') is True for r in reviewed),
             'remaining': 500 - complete_count, 'all_500_read_and_verified': both == 500}
    (AUDIT / 'progress.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    lines = ['# 500-paper full-text and public-source audit', '', f'Updated: {stamp}', '',
             f'**Đã đọc full text và verify public-source verdict: {both}/500 paper.**', '',
             f'- Full text đã đọc: {read_count}/500.',
             f'- Public-source checks đã ghi evidence: {checked_count}/500.',
             f'- Full text access-blocked/not read: {unread_access_blocked}.',
             f'- Review hoàn tất (kể cả access-blocked verdict): {complete_count}/500.',
             f'- Retrieval đã thử: {len(retrieved)}/500. Downloaded text không tính là đã đọc.',
             f'- Author-code/model reproduction đã chạy: {stats["locally_reproduced"]}.', '',
             'Yêu cầu người dùng: nếu xong trước 07:00 giờ Việt Nam, xuất report ở root xác nhận 500/500.',
             'Chỉ ghi hoàn tất 500/500 khi ledger có 500 full-text reviews và public-source verdicts đã kiểm chứng.', '',
             'Lịch tiếp tục: không có timer; tiếp tục thủ công theo yêu cầu người dùng, tối đa 50 paper bổ sung.',
             'Các timer audit systemd đã được disable theo yêu cầu ngày 2026-10-15.', '',
             'Hai lượt 02:20/07:20 ngày 15/10 đã fail vì thread writer conflict; không hoàn tất trước 07:00.',
             'Scheduler từng dùng codex queue sau lỗi writer conflict; hiện mọi timer đã disable và không có continuation tự động.', '',
             '## Reviewed papers', '',
             '| # | Paper | Full text read | Public source | Reproduction feasibility |',
             '|---:|---|---|---|---|']
    for r in sorted(reviewed, key=lambda r: r['rank']):
        lines.append(f'| {r["rank"]} | {r["title"]} | {r.get("fulltext_read", False)} | {r.get("source_status", "unknown")} | {r.get("reproduction_verdict", "unknown")} |')
    lines.extend(['', '## Reports and evidence', '',
                  '- [Original report](research/benchmark-papers-2025-2026/REPORT.md)',
                  '- [Audit recommendations](research/benchmark-papers-2025-2026/audit/RECOMMENDATIONS.md)',
                  '- [Provisional paper selection](research/benchmark-papers-2025-2026/audit/PAPER_SELECTION.md)',
                  '- [Per-paper review ledger](research/benchmark-papers-2025-2026/audit/reviews/)',
                  '- [Continuation instructions](research/benchmark-papers-2025-2026/audit/CONTINUE.md)', ''])
    checkpoint = AUDIT / 'quota_checkpoint.json'
    if checkpoint.exists():
        refresh_quota_checkpoint(checkpoint)
        quota = json.loads(checkpoint.read_text())
        quota.update({'fulltexts_read': read_count, 'source_checks': checked_count,
                      'unread_access_blocked': unread_access_blocked,
                      'next_continuation': f'Manual only; {max(0, quota.get("fresh_quota_read_cap", 50) - quota.get("fresh_quota_reads_completed", 0))} of 50 additional distinct full-text reads remain. Timers disabled.'})
        checkpoint.write_text(json.dumps(quota, ensure_ascii=False, indent=2) + '\n')
        lines.extend(['', '## Quota checkpoint', '',
                      f'Checked: {quota["checked_at"]} from {quota.get("telemetry_source", "recorded quota checkpoint")}.'])
        if quota.get('quota_status') == 'user_reported_reset':
            lines.append('Quota vừa được người dùng xác nhận đã reset; đây không phải số đo live. Phần trăm usage hiện chưa có telemetry mới để xác minh.')
        elif quota.get('primary_remaining_percent') is not None and quota.get('weekly_remaining_percent') is not None:
            lines.append(f'Quota còn lại (100% - used_percent): primary {quota["primary_remaining_percent"]}% (đã dùng {quota.get("primary_used_percent")}% ; reset {quota.get("primary_resets_at", "unknown")}); weekly {quota["weekly_remaining_percent"]}% (đã dùng {quota.get("weekly_used_percent")}% ; reset {quota.get("weekly_resets_at", "unknown")}).')
        else:
            lines.append('Live usage percentages and reset times are unavailable in this checkpoint.')
        if quota.get('user_reported_reset_at'):
            lines.append(f'Quota reset was user-reported at {quota["user_reported_reset_at"]}; the latest local telemetry event is recorded above. The UI percentage the user reported is remaining quota; raw local `used_percent` is converted to remaining as 100 minus usage.')
        if quota.get('user_reported_remaining_percent_primary') is not None:
            lines.append(f'Người dùng báo UI hiện còn {quota["user_reported_remaining_percent_primary"]}% quota primary (báo lúc {quota.get("user_reported_remaining_at", "time not recorded")}); đây là số remaining theo UI, tách riêng với snapshot local telemetry phía trên.')
        lines.extend([f'Continuation: {quota["next_continuation"]}', ''])
    (REPO / 'PAPER_AUDIT_500_REPORT.md').write_text('\n'.join(lines))
    (AUDIT / 'STATUS.md').write_text('\n'.join(lines[:21]) + '\n\nRead CONTINUE.md. Run summarize.py after each batch.\n')
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
