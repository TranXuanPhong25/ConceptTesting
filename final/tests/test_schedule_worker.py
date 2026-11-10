"""A delayed worker cannot be released before its explicit deadline."""
import io
import json
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from final.src.orchestration import schedule_worker


def test_timer_resumes_only_at_deadline(tmp_path):
    receipt=tmp_path/'schedule.json'
    receipt.write_text(json.dumps({'state':'waiting_deadline','deadline_epoch':1200,
        'worker_pid':321,'flow_run_id':'fixture','progress_artifact_id':'fixture'}))
    clock=[0.0];signals=[]
    def sleep(seconds):
        assert 0<seconds<=30
        clock[0]+=seconds
    def resume(pid,kind):signals.append((pid,kind,clock[0]))
    with patch.object(schedule_worker,'validate_paused_worker'),patch.object(schedule_worker.time,'time',lambda:clock[0]),\
         patch.object(schedule_worker.time,'sleep',sleep),patch.object(schedule_worker.os,'kill',resume),\
         patch.object(schedule_worker.urllib.request,'urlopen',return_value=io.BytesIO(b'{"state_type":"RUNNING"}')),\
         patch.object(schedule_worker,'update_progress'):
        schedule_worker.run_timer(receipt)
    assert signals==[(321,signal.SIGCONT,1200)]
    assert json.loads(receipt.read_text())['state']=='worker_resumed'


def test_timer_never_resumes_a_cancelled_record(tmp_path):
    receipt=tmp_path/'schedule.json'
    receipt.write_text(json.dumps({'state':'waiting_deadline','deadline_epoch':0,
        'worker_pid':321,'flow_run_id':'fixture','progress_artifact_id':'fixture'}))
    with patch.object(schedule_worker,'validate_paused_worker'),\
         patch.object(schedule_worker.urllib.request,'urlopen',return_value=io.BytesIO(b'{"state_type":"CANCELLED"}')),\
         patch.object(schedule_worker.os,'kill') as resume:
        with pytest.raises(ValueError,match='no longer active'):schedule_worker.run_timer(receipt)
    resume.assert_not_called()
    assert json.loads(receipt.read_text())['state']=='schedule_error'


def test_schedule_is_not_repeatable_after_resume(tmp_path):
    receipt=tmp_path/'schedule.json';receipt.write_text(json.dumps({'state':'worker_resumed'}))
    with patch.object(schedule_worker.os,'kill') as resume:
        with pytest.raises(ValueError,match='duplicate'):schedule_worker.run_timer(receipt)
    resume.assert_not_called()
