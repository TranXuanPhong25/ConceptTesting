"""Authored regressions, never synthetic benchmark outcomes."""
import copy
import time

import pytest

from . import pipeline
from .evidence_gate import check_public_examples, select_evidence, assess_context
from .joint_constructor import construct_case
from .semantic_contract import admit
from .test_contractfix import REQ, proposal
from .test_pipeline import Client

CONFIG = {'repeat_seeds': [1, 2], 'repeats_per_program_seed': 2, 'max_case_seconds': 10}


def accepted(**changes):
    good, bad = admit(REQ, [dict(proposal(), **changes)])
    assert good and not bad
    return good[0]


@pytest.mark.parametrize('changes,reason', [
    ({'event_predicate': {'op': 'literal', 'value': False}}, 'constant_false_event'),
    ({'trigger': {'op': 'and', 'items': [{'op': 'literal', 'value': False},
                                        {'op': 'eq', 'left': {'op': 'input', 'arg': 0},
                                         'right': {'op': 'literal', 'value': 2}}]}}, 'constant_false_trigger'),
    ({'trigger': {'op': 'literal', 'value': 1}}, 'nonboolean_constant_predicate'),
    ({'required_relation': ' SUBTRACT   ONE '}, 'no_claimed_mismatch'),
    ({'alternative': 'None'}, 'none_expression_not_abstention'),
    ({'alternative': 'x - 1'}, 'no_op_alternative'),
    ({'alternative_rationale': ''}, 'alternative_rationale_required'),
])
def test_admission_rejects_known_failure_modes(changes, reason):
    good, bad = admit(REQ, [dict(proposal(), **changes)])
    assert not good and bad[0]['reason'] == 'ValueError:' + reason


def test_null_is_abstention_not_a_sensitive_alternative():
    h = accepted(alternative=None, alternative_rationale='')
    report = construct_case(REQ, [h], CONFIG)
    assert report['native_executions'] == 0
    assert report['records'][0]['public_consistency']['status'] == 'no_alternative'
    assert not assess_context(REQ, pipeline.contexts(REQ, report)['concept'])['passed']


def test_public_check_accepts_consistency_but_never_asserts_semantic_truth():
    check = check_public_examples(REQ, accepted(), CONFIG, time.monotonic()+10, 32)
    assert check['status'] == 'passed' and check['native_executions'] == 8
    assert check['semantic_truth'] == 'unverified'


def test_public_check_blocks_a_regressing_alternative():
    # Site executes on the public example; this plausible-looking replacement is wrong.
    req = dict(REQ, source='def f(x):\n    return x+1\n')
    from .semantic_contract import writer_packet
    p = proposal(req)
    p.update(alternative='x+2', required_relation='add two', observed_relation='add one')
    good, bad = admit(req, [p])
    assert good and not bad
    check = check_public_examples(req, good[0], CONFIG, time.monotonic()+10, 32)
    assert check['status'] == 'public_regression'
    assert check['rows'][-1]['program'] == 'alternative'


def test_public_check_rejects_boolean_integer_equivalence():
    req = dict(REQ, public_examples=[{'arguments': '(1,)', 'expected': True}])
    check = check_public_examples(req, accepted(), CONFIG, time.monotonic()+10, 32)
    assert check['status'] == 'public_regression'


def test_unknown_and_budget_never_pass(monkeypatch):
    from . import evidence_gate
    monkeypatch.setattr(evidence_gate, 'replay', lambda *a, **kw: {'status': 'worker_timeout'})
    check = check_public_examples(REQ, accepted(), CONFIG, time.monotonic()+10, 32)
    assert check['status'] == 'public_check_unknown' and check['native_executions'] == 1
    check = check_public_examples(REQ, accepted(), CONFIG, time.monotonic()+10, 0)
    assert check['status'] == 'public_check_budget' and check['native_executions'] == 0


def run(arguments, sensitive=False, **changes):
    return dict(arguments=arguments, stable=True, normal=True, site_realized=True,
                predicate_realized=True, event_realized=True, event_unknown=False,
                output_sensitivity=sensitive,
                observations=[{'put': {'output': {'type': 'int', 'repr': '1'}},
                               'alternative': {'output': {'type': 'int', 'repr': '0' if sensitive else '1'}}}],
                **changes)


def construction(runs, status='passed'):
    return {'records': [{'hypothesis': accepted(), 'construction': {'status': 'authored_fixture'},
                         'public_consistency': {'status': status, 'semantic_truth': 'unverified'},
                         'runs': runs}], 'candidates_tested': len(runs)}


def test_third_sensitive_witness_is_delivered_with_exact_control_parity():
    # Regression for v63 selection: sensitive witness at index 3, beyond [:2].
    report = construction([run('(7,)'), run('(9,)'), run('(8,)'), run('(6,)', True)])
    before = copy.deepcopy(report)
    selection = select_evidence(REQ, report)
    context = pipeline.contexts(REQ, report)
    assert context['concept']['evidence'] == context['equal_evidence_raw']['evidence']
    assert context['inputs_only']['inputs'] == ['(6,)', '(7,)']
    gate = assess_context(REQ, context['concept'])
    assert gate['passed'] and gate['delivered_sensitive'][0]['arguments'] == '(6,)'
    assert gate['evidence_sha256'] == selection['evidence_sha256']
    assert selection['receipts'][0]['omitted'] == 2
    assert report == before


def test_selection_deduplicates_and_excludes_public_only_sensitivity():
    report = construction([run('(1,)', True), run('(7,)'), run('(7,)')])
    selection = select_evidence(REQ, report)
    assert len(selection['inputs']) == 2
    assert not assess_context(REQ, pipeline.contexts(REQ, report)['concept'])['passed']


def test_unknown_realization_and_unchecked_alternatives_cannot_supply_evidence():
    r = run('(6,)', True)
    r['event_unknown'] = True
    for report in (construction([r]), construction([run('(6,)', True)], 'public_check_unknown')):
        assert not select_evidence(REQ, report)['evidence']
        assert not assess_context(REQ, pipeline.contexts(REQ, report)['concept'])['passed']


def test_gate_requires_every_case_and_cannot_count_undelivered_runs(monkeypatch, tmp_path):
    reports = {'0': construction([run('(6,)', True)]), '1': construction([run('(7,)')])}
    def prepare(client, req, out):
        return [accepted()], [], reports[req['case_id']]
    monkeypatch.setattr(pipeline, 'prepare_case', prepare)
    requests = [dict(REQ, case_id=str(i)) for i in range(2)]
    gate = pipeline.admission_gate(None, requests, tmp_path)
    assert not gate['passed']
    assert [row['passed'] for row in gate['rows']] == [True, False]


def test_direct_generation_cannot_bypass_failed_gate_or_spend_arm_calls(tmp_path):
    client = Client()
    for _ in range(2):
        with pytest.raises(ValueError, match='case_evidence_gate_failed'):
            pipeline.generate_case(client, REQ, tmp_path)
    assert client.calls == 1  # Writer only, reused on resume.
    assert not (tmp_path/'plain').exists() and not (tmp_path/'result.json').exists()


def test_case_budget_includes_public_checks_and_search():
    report = construct_case(REQ, [accepted()], CONFIG)
    record = report['records'][0]
    assert record['public_consistency']['status'] == 'passed'
    total = record['public_consistency']['native_executions'] + sum(r['native_executions'] for r in record['runs'])
    assert report['native_executions'] == total <= 256
    assert report['candidates_tested'] <= 64
    assert assess_context(REQ, pipeline.contexts(REQ, report)['concept'])['passed']


def test_first_unproductive_hypothesis_cannot_starve_later_one(monkeypatch):
    from . import joint_constructor
    first = accepted()
    second = accepted(trigger={'op': 'eq', 'left': {'op': 'input', 'arg': 0},
                               'right': {'op': 'literal', 'value': 3}})
    visited = []
    def solve(*args, **kwargs):
        return {'inputs': [(i,) for i in range(kwargs['max_candidates'])],
                'status': 'authored_budget_fixture'}
    def verify(request, hypothesis, args, config, deadline):
        visited.append(hypothesis['id'])
        return dict(native_executions=8, output_sensitivity=False)
    monkeypatch.setattr(joint_constructor, 'solve_inputs', solve)
    monkeypatch.setattr(joint_constructor, 'verify_input', verify)
    report = construct_case(REQ, [first, second], CONFIG)
    assert first['id'] in visited and second['id'] in visited
    assert report['native_executions'] <= 256 and report['candidates_tested'] <= 64
    assert all(record['public_consistency']['status'] == 'passed' for record in report['records'])


def test_old_cli_routes_to_integrated_gate(monkeypatch):
    from . import ngrok_run
    entered = []
    monkeypatch.setattr(pipeline, 'main', lambda: entered.append('integrated'))
    ngrok_run.main()
    assert entered == ['integrated']
