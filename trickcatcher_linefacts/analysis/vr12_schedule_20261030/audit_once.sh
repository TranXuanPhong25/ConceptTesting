#!/usr/bin/env bash
set -euo pipefail
cd /home/phong/dev/ConceptTester
vr12_audit_dir=/home/phong/dev/ConceptTester/trickcatcher_linefacts/analysis/vr12_schedule_20261030
exec 9>"$vr12_audit_dir/audit.lock"
flock -n 9 || exit 0
if [[ -e "$vr12_audit_dir/AUDIT_ATTEMPTED" ]]; then exit 0; fi
touch "$vr12_audit_dir/AUDIT_ATTEMPTED"
# OAuth login was checked before scheduling. Never allow an API-key fallback.
unset OPENAI_API_KEY OPENAI_BASE_URL OPENAI_ORG_ID OPENAI_PROJECT_ID
exec /usr/bin/codex exec --ignore-user-config -s workspace-write \
  -c 'approval_policy="never"' -c 'model_reasoning_effort="low"' \
  -C /home/phong/dev/ConceptTester --color never \
  -o "$vr12_audit_dir/CLI_FINAL.md" - < "$vr12_audit_dir/audit_prompt.md"
