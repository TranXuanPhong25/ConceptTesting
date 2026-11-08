"""Start/stop the local Prefect UI, preset listener and read-only history index."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

from .config import ROOT

STATE=ROOT/'final/out/run_console'


def environment(port):
    env=dict(os.environ)
    env.pop('PREFECT_API_KEY',None)
    env.update(PREFECT_HOME=str(STATE/'prefect_home'),PREFECT_API_URL=f'http://127.0.0.1:{port}/api',
        PREFECT_SERVER_UI_API_URL=f'http://127.0.0.1:{port}/api',PREFECT_SERVER_ANALYTICS_ENABLED='false',
        PYTHONPATH=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
    return env


def process_token(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return None


def alive(record):
    if not record or process_token(record['pid'])!=record['start_token']:return False
    try:return Path(f"/proc/{record['pid']}/status").read_text().split('State:\t',1)[1].split()[0]!='Z'
    except (OSError,IndexError):return False


def load():
    try:return json.loads((STATE/'services.json').read_text())
    except (OSError,ValueError):return {'processes':{}}


def healthy(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=2) as response:return response.status==200
    except (OSError,ValueError):return False


def start(port=4200,server_only=False):
    STATE.mkdir(parents=True,exist_ok=True);STATE.chmod(0o700)
    info=load()
    if alive(info['processes'].get('server')) and info.get('port',4200)!=port:
        raise ValueError('Stop the existing console before changing its port')
    info['port']=port
    commands={'server':[str(Path(sys.executable).parent/'prefect'),'server','start','--host','127.0.0.1','--port',str(port),'--analytics-off']}
    if not server_only:
        commands.update(presets=[sys.executable,'-m','final.src.orchestration.serve'],
                        history=[sys.executable,'-m','final.src.orchestration.history','--watch'])
    if not alive(info['processes'].get('server')):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('Port is already occupied by another server')
    for name,command in commands.items():
        if alive(info['processes'].get(name)):continue
        if name!='server' and not healthy(port):raise RuntimeError('Prefect server did not become healthy; inspect server.log')
        with (STATE/(name+'.log')).open('ab') as log:
            process=subprocess.Popen(command,cwd=ROOT,env=environment(port),stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        info['processes'][name]={'pid':process.pid,'start_token':process_token(process.pid),'command':command}
        (STATE/'services.json').write_text(json.dumps(info,indent=2)+'\n')
        if name=='server':
            for _ in range(90):
                if healthy(port):break
                if process.poll() is not None:raise RuntimeError('Prefect server exited; inspect server.log')
                time.sleep(1)
    print(json.dumps({'url':f'http://127.0.0.1:{port}','services':{name:record['pid'] for name,record in info['processes'].items() if alive(record)}}))


def stop():
    info=load()
    for name in ('presets','history','server'):
        record=info['processes'].get(name)
        if alive(record):
            try:os.killpg(record['pid'],signal.SIGTERM)
            except ProcessLookupError:pass
    print(json.dumps({'stop_requested':True,'benchmark_checkpoints':'preserved'}))


def active_managed_flow_count(port):
    """Do not reload deployments while a run owned by the console is queued/running."""
    import asyncio
    from prefect.client.orchestration import get_client
    async def list_runs():
        async with get_client() as client:return await client.read_flow_runs(limit=200)
    old={key:os.environ.get(key) for key in ('PREFECT_HOME','PREFECT_API_URL','PREFECT_SERVER_UI_API_URL')}
    try:
        os.environ.update(environment(port))
        runs=asyncio.run(list_runs())
        states={'Pending','Running','Scheduled','Cancelling','Retrying'}
        return sum(run.deployment_id is not None and run.state_name in states for run in runs)
    finally:
        for key,value in old.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


def reload_presets():
    info=load();port=info.get('port',4200);record=info['processes'].get('presets')
    if not healthy(port) or not alive(record):raise RuntimeError('Run the local console first')
    if not alive(info['processes'].get('server')):raise RuntimeError('Prefect server is not owned by this console')
    running=active_managed_flow_count(port)
    if running:raise RuntimeError(f'{running} managed run(s) are active; reload presets after they finish')
    os.killpg(record['pid'],signal.SIGTERM)
    for _ in range(100):
        if not alive(record):break
        time.sleep(.1)
    if alive(record):raise RuntimeError('Preset listener did not stop; other services remain running')
    info['processes'].pop('presets',None)
    (STATE/'services.json').write_text(json.dumps(info,indent=2)+'\n')
    start(port,server_only=False)


def cleanup_stale_history():
    info=load();port=info.get('port',4200)
    if not healthy(port):raise RuntimeError('Start the local console first')
    command=[str(Path(sys.executable).parent/'python'),'-m','final.src.orchestration.history','--clean-stale-historical-rows']
    result=subprocess.run(command,cwd=ROOT,env=environment(port),stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
    print(result.stdout.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('start','stop','status','reload-presets','clean-stale-history'),nargs='?',default='start')
    parser.add_argument('--port',type=int,default=4200);parser.add_argument('--server-only',action='store_true')
    args=parser.parse_args()
    if args.action=='start':start(args.port,args.server_only)
    elif args.action=='stop':stop()
    elif args.action=='reload-presets':reload_presets()
    elif args.action=='clean-stale-history':cleanup_stale_history()
    else:
        info=load();print(json.dumps({'url':f"http://127.0.0.1:{info.get('port',4200)}",'healthy':healthy(info.get('port',4200)),
            'services':{name:{'pid':record['pid'],'alive':alive(record)} for name,record in info['processes'].items()}}))


if __name__=='__main__':main()
