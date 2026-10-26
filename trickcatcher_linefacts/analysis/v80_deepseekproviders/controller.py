"""Run two explicitly authorized provider packages, never silently fall back."""
from pathlib import Path
import json,os,subprocess,hashlib
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PYTHON='/tmp/concepttester-v64-venv/bin/python'
BASE=REPO/'trickcatcher_linefacts/out/pipelines/v80_deepseekproviders'


def main():
    rows=[]
    for route,slug in [('reka','reka'),('deepinfra/fp8','deepinfra_fp8')]:
        out=BASE/slug
        env=dict(os.environ,V80_PROVIDER=route)
        command=[PYTHON,'-B','-u','-m','trickcatcher_linefacts.pipelines.v80_deepseekproviders.ds_probe','run','--out',str(out)]
        with (HERE/(slug+'.log')).open('xb') as log:
            result=subprocess.run(command,cwd=REPO,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode or not (out/'summary.json').exists() or not (out/'frozen.json').exists():
            rows.append({'route':route,'status':'controller_failure','returncode':result.returncode});break
        freeze=json.loads((out/'frozen.json').read_text())
        if any(hashlib.sha256((out/rel).read_bytes()).hexdigest()!=h for rel,h in freeze.items()):
            rows.append({'route':route,'status':'terminal_integrity_failure'});break
        for name in ('summary.json','frozen.json'):
            expected=json.loads((out/Path(name).with_suffix('.sha256.json')).read_text())
            if expected!={'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()}:
                raise ValueError('terminal_checkpoint_integrity_failure')
        summary=json.loads((out/'summary.json').read_text())
        rows.append({'route':route,**{k:v for k,v in summary.items() if k!='rows'}})
        if summary['unknown_cost_attempts']:
            # Only a raw provider-specific upstream rejection permits the other
            # already authorized provider. Network timeouts/unknown completions stop.
            permitted=False
            responses=[p.parent/'response.sse' for p in sorted(out.glob('*/*/attempt.json'))
                       if not (p.parent/'cost_receipt.json').exists()]
            if responses:
                try:
                    error=json.loads(responses[-1].read_text()).get('error',{})
                    meta=error.get('metadata',{})
                    permitted=(error.get('code')==429 and meta.get('limit_source')=='upstream_provider_shared_pool')
                except (ValueError,AttributeError):pass
            if not permitted:break
        if any(s in (summary.get('stop_reason') or '') for s in ('api_error:401','api_error:402','api_error:403')):break
    (HERE/'controller_terminal.json').write_text(json.dumps({'providers':rows,'finished_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')


if __name__=='__main__':main()
