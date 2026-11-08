from final.src.audits.format_repair_naive import decode_rows, format_record
from final.src.modular.call_builder import CallBuilder


def builder(source, entry='f'):
    return CallBuilder.for_source(source, entry)


def test_single_argument_wrapping_and_format_fixes_keep_values():
    one = builder('def f(s: str):\n    pass\n')
    assert format_record({'args': "'a'", 'kwargs': '{}'}, one, [])[0]['args'] == "('a',)"
    assert format_record({'args': "(')()(', 'kwargs': '{}')", 'kwargs': '{}'}, one, [])[0]['args'] == "(')()(',)"
    assert format_record({'args': "('Hello\nWorld',)", 'kwargs': '{}'}, one, [])[0]['args'] == "('Hello\\nWorld',)"
    pair = builder('def f(a, b):\n    pass\n')
    assert format_record({'args': "['x', 'y']'", 'kwargs': '{}'}, pair, [])[0]['args'] == "('x', 'y')"


def test_expressions_nonfinite_and_ambiguous_records_stay_rejected():
    one = builder('def f(n):\n    pass\n')
    for raw in ('(2 * 3,)', "(float('inf'),)", "('a' * 10,)", "('())"):
        assert format_record({'args': raw, 'kwargs': '{}'}, one, [])[0] is None
    # Static evidence says list, so '()' is not rewrapped as a tuple value.
    evidence = [('list', 'instance', 'parameter annotation')]
    assert format_record({'args': '()', 'kwargs': '{}'}, one, evidence) == (None, 'does_not_bind')


def test_per_record_salvage_and_truncation_policy():
    text = ('{"inputs":[{"args":"(1,)","kwargs":"{}","concept_id":null},{"args":"\' \', "kwargs":"{}"},'
            '{"args\':\'"ab", "b"\',\'kwargs":"{}","concept_id":null},{"args":"(2,)","kwargs":"{}","concept_id":null}]}')
    rows, rules, rule = decode_rows({'text': text})
    assert rule == 'per_record_salvage'
    assert rows[0]['args'] == '(1,)' and rows[1] is None and rows[3]['args'] == '(2,)'
    assert rows[2]['args'] == '"ab", "b"' and rules[2] == 'garbled_key_quotes'
