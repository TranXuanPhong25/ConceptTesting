#!/usr/bin/env bash
set -euo pipefail
PIPE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TASK_REPO=$(cd -- "$PIPE_DIR/../../.." && pwd)
cd "$TASK_REPO"
source scripts/research_env.sh >/dev/null 2>&1
: "${QWEN_BASE_URL:?Privately export QWEN_BASE_URL before this run}"
export QWEN_MODEL=qwen2.5-coder-7b-instruct
export PYTHONPATH="$TASK_REPO"
export PYTHONDONTWRITEBYTECODE=1
VARIANT=$(basename -- "$PIPE_DIR")
MODULE="trickcatcher_linefacts.pipelines.$VARIANT.experiment"
RUN_PY="$TASK_REPO/CoverUp_concept/.venv/bin/python"

# Validate without printing endpoint/key or following authenticated redirects.
"$RUN_PY" -B - <<'PY'
import os, urllib.request, urllib.parse
# Match the pinned transport URL policy.
base=os.environ['QWEN_BASE_URL'].rstrip('/')
parsed=urllib.parse.urlsplit(base);host=parsed.hostname or ''
assert parsed.scheme in ('http','https') and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
assert host in ('localhost','127.0.0.1','::1') or (parsed.scheme=='https' and any(host.endswith('.'+s) for s in
    ('ngrok-free.app','ngrok.app','ngrok.io','ngrok-free.dev','ngrok.dev')))
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
url=base+('' if parsed.path.rstrip('/').endswith('/v1') else '/v1')+'/models'
headers={'ngrok-skip-browser-warning':'1'}
if os.environ.get('QWEN_API_KEY'):headers['Authorization']='Bearer '+os.environ['QWEN_API_KEY']
try:
    response=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(
        urllib.request.Request(url,headers=headers),timeout=30)
    with response:code=response.status
except Exception as exc:
    print('Qwen endpoint check failed:',type(exc).__name__)
    raise SystemExit(1)
if code!=200:raise SystemExit('Qwen endpoint check returned non-200')
print('Qwen endpoint ready')
PY

# One child process, owned by this script, receives credentials only via environment; logs contain no URL/key.
"$RUN_PY" -B - <<'PY' &
import os,time,urllib.request,urllib.parse
base=os.environ['QWEN_BASE_URL'].rstrip('/')
url=base+('' if urllib.parse.urlsplit(base).path.rstrip('/').endswith('/v1') else '/v1')+'/models'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
headers={'ngrok-skip-browser-warning':'1'}
if os.environ.get('QWEN_API_KEY'):headers['Authorization']='Bearer '+os.environ['QWEN_API_KEY']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
while True:
    try:
        with opener.open(urllib.request.Request(url,headers=headers),timeout=20):pass
    except Exception:pass
    time.sleep(600)
PY
KEEPALIVE_PID=$!
trap 'kill "$KEEPALIVE_PID" 2>/dev/null || true; wait "$KEEPALIVE_PID" 2>/dev/null || true' EXIT
"$RUN_PY" -B -m "$MODULE" all --online --workers "${LINEFACTS_EXPERIMENT_WORKERS:-4}"
