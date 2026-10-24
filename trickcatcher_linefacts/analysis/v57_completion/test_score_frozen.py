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
