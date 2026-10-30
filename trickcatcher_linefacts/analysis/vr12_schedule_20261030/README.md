# One-shot local schedule, 2026-10-30 Vietnam time

User authorized scheduling after expected ngrok availability and supplied quota
reset screenshot. Use local user-systemd timers because no app scheduling tool
is exposed in this session. This is not a Scheduled-tab task or a promise of an
automatic follow-up message in the original chat.

- 00:45 Asia/Ho_Chi_Minh (2026-10-29 17:45UTC): launch unchanged frozen VR12 once,
  with exactmodel/contextpreflight and duplicate/ledger/hash guards. No Codex call.
- 03:15 Asia/Ho_Chi_Minh (2026-10-29 20:15UTC): one ChatGPT-authenticated Codex CLI
  audit, after screenshot's2h54reset plus buffer. No new model experiment calls,
  no API-key fallback and no retry if quota remains exhausted.

Both are one-shot, not recurring. Machine and user service manager must remain
on; timers cannot survive a reboot unless re-created. Late service wake checks
completion/locks/ledger before any inference. Endpoint is passed through transient
service environment only, never repo files or reports. Prior failed-preflight
receipts are copied into run history before the controller updates its status.
The original freeze/PREREG/scorer and cap132 remain unchanged. No larger run.

Units: `concepttester-vr12-launch-20261030.timer` and
`concepttester-vr12-audit-20261030.timer`. Inspect with `systemctl --user list-timers`.
Cancel before firing via `systemctl --user stop <unit>.timer` for either timer;
do not stop an active inference controller without checking saved requests.
Audit outputs go in this folder. Systemd services log safe status to the user
journal, and run generation logs remain under the ignored experiment out folder.

Verification before handoff: both timerunits active with the exact next deadlines;
frozenVR12 check PASS; shellsyntax/Pythoncompile PASS; six mocked automationguard
tests PASS with zero actual workers or network calls. User-manager Linger=no:
keep the machine on and the login session alive until both timers have fired.
