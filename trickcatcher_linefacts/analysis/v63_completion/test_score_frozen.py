import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("v57_score", Path(__file__).with_name("score_frozen.py"))
score = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(score)


def test_comparator_matches_historical_dataset_numeric_policy():
    assert score._same(1.0, 1.0000001, 1e-5)
    assert score._same(True, 1, 0.0)
    assert score._same(1,1.00000001,1e-5)
    assert not score._same([1],(1,),0.0)


def test_decode_unresolved_when_output_literal_is_bad():
    assert score._decode({"status": "ok", "output_repr": "not a literal"}) == ("unresolved", None)
    assert score._decode({"status": "exception", "exception_type": "ValueError"}) == ("exception", "ValueError")


def test_worker_separates_checker_failure_dut_exception_and_serialization(tmp_path):
    cases=[('def f(x):\n    return x\n','contract','exception'),
           ('def is_valid_test(x):\n    return False\ndef f(x):\n    pass\n','contract','invalid'),
           ('def f(x):\n    assert False\n','put','exception'),
           ('def f(x):\n    return object()\n','put','unresolved'),
           ('raise ValueError()\ndef f(x):\n    return 0\n','put','unresolved')]
    for source,kind,status in cases:
        result=score._run_worker(source,'f',(1,),tmp_path,kind,'fixture')
        assert result['status']==status,result


def test_worker_cache_detects_modified_result(tmp_path):
    import pytest
    source='def f(x):\n    return x+1\n'
    score._run_worker(source,'f',(1,),tmp_path,'put','fixture')
    result=next(tmp_path.rglob('result.json'));result.write_text('{"status":"ok","output_repr":"999"}')
    with pytest.raises(ValueError,match='integrity'):score._run_worker(source,'f',(1,),tmp_path,'put','fixture')
