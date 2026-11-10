"""Resume one explicitly delayed worker, retaining its existing Prefect record."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import time
import urllib.request


def save_receipt(path, record):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)


def validate_paused_worker(record):
    """A PID alone is insufficient: require the original process and zero requests."""
    pid=record['worker_pid'];folder=Path('/proc')/str(pid)
    fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
    if fields[19]!=record['worker_start_token']:
        raise ValueError('Worker PID identity changed; refuse resume')
    if fields[0] not in ('T','t'):
        raise ValueError('Scheduled worker is not stopped; refuse duplicate resume')
    output=Path(record['output_directory'])
    if str(output).encode() not in (folder/'cmdline').read_bytes():
        raise ValueError('Worker command belongs to a different output')
    if list(output.glob('tasks/*/calls/*/attempt.json')):
        raise ValueError('Generation already started before the scheduled deadline')
    status=json.loads((output/'status.json').read_text())
    if status.get('state')!='waiting_endpoint' or status.get('pid')!=pid:
        raise ValueError('Scheduled worker no longer waits for its endpoint')


def update_progress(record, message):
    api='http://127.0.0.1:4200/api'
    request=urllib.request.Request(api+'/artifacts/'+record['progress_artifact_id'],
        data=json.dumps({'data':message}).encode(),headers={'Content-Type':'application/json'},method='PATCH')
    with urllib.request.urlopen(request,timeout=10) as response:response.read()


def run_timer(receipt_path):
    with receipt_path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        record=json.loads(receipt_path.read_text())
        if record['state']!='waiting_deadline':
            raise ValueError('Schedule is no longer waiting; refuse duplicate action')
        validate_paused_worker(record)
        record['timer_pid']=os.getpid();save_receipt(receipt_path,record)
        while time.time()<record['deadline_epoch']:
            time.sleep(min(30,max(.01,record['deadline_epoch']-time.time())))
        try:
            validate_paused_worker(record)
            with urllib.request.urlopen('http://127.0.0.1:4200/api/flow_runs/'+record['flow_run_id'],timeout=10) as response:
                flow=json.load(response)
            if flow['state_type']!='RUNNING':
                raise ValueError('Prefect record is no longer active; do not restart it')
            # Same worker, same budgets and history; only release its user-requested pause.
            os.kill(record['worker_pid'],signal.SIGCONT)
            record.update(state='worker_resumed',resumed_epoch=time.time());save_receipt(receipt_path,record)
            update_progress(record,'Đã đến mốc user hẹn và resume cùng worker. Run ep_dt_bva kiểm endpoint/model rồi generation; '
                'không gọi trước deadline,không tạo run mới. Metrics detection/inputs/tokens:pending.')
        except BaseException as error:
            record.update(state='schedule_error',error_type=type(error).__name__);save_receipt(receipt_path,record)
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args();run_timer(args.receipt.resolve())


if __name__=='__main__':main()
