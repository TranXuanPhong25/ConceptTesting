from concurrent.futures import ThreadPoolExecutor
from threading import Event


def test_overlap_submits_only_saved_receipts_and_does_not_wait_for_consumer():
    from final.src.orchestration.tool_overlap import overlap
    consumer_started=Event();second_saved=Event();seen=[]
    def produce(item):
        if item==2:
            assert consumer_started.wait(3)
            second_saved.set()
        return {'task':item,'response_persisted':True}
    def consume(receipt):
        assert receipt['response_persisted']
        if receipt['task']==1:
            consumer_started.set()
            assert second_saved.wait(3), 'Producer was blocked by CPU consumer'
        seen.append(receipt['task'])
        return receipt['task']
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=overlap([1,2],produce,consume,pool)
        assert [future.result() for future in pending]==[1,2]
    assert seen==[1,2]


def test_skipped_production_never_submits_consumer():
    from final.src.orchestration.tool_overlap import overlap
    def forbidden(receipt):raise AssertionError('Skipped slot reached consumer')
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert overlap([1,2],lambda item:None,forbidden,pool)==[]


def test_duplicate_producer_cannot_overwrite_owner_status(tmp_path,monkeypatch):
    import fcntl,json
    from final.src.orchestration import tool_overlap
    status=tmp_path/'status.json';status.write_text(json.dumps({'state':'running','owner':'first'}))
    with (tmp_path/'.producer.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        import pytest
        with pytest.raises(BlockingIOError):tool_overlap.produce_run(tmp_path)
    assert json.loads(status.read_text())=={'state':'running','owner':'first'}


def test_observer_cannot_mark_terminal_from_a_report_built_before_last_receipt(tmp_path,monkeypatch):
    import json
    from final.src.orchestration import tool_overlap
    status=tmp_path/'status.json';status.write_text(json.dumps({'state':'running','phase':'generation'}))
    def report(directory):
        status.write_text(json.dumps({'state':'complete','phase':'terminal'}))
        return {'task_states':{'complete':1}}
    monkeypatch.setattr(tool_overlap,'report',report)
    state,result=tool_overlap.report_snapshot(tmp_path)
    assert state['phase']!='terminal'
    state,result=tool_overlap.report_snapshot(tmp_path)
    assert state['phase']=='terminal'
