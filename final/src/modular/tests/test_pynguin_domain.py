"""Pynguin admission shares the pipeline's isolated trusted-contract validator."""
import pytest

from final.src.modular.pynguin import adapter
from final.src.modular.pynguin import PynguinInputGenerator, PynguinSettings
from final.src.modular.tests.test_pynguin_adapter import context, PYTHON
from final.src.runtime.execution import ExecutionError


def generated_batch(tmp_path, monkeypatch, contract):
    ctx = context(tmp_path)
    ctx.metadata['contract'] = contract
    generator = PynguinInputGenerator(PynguinSettings(python=PYTHON))
    calls = [{'test': f'test_{index}', 'args': repr((value,)), 'kwargs': '{}'}
             for index, value in enumerate([2, -1, 2, 4])]
    monkeypatch.setattr(generator, 'search_owner', lambda *args: {
        'owner': 'p1', 'status': 'complete', 'calls': calls, 'rejected': []})
    return generator.construct(ctx, 'unused/', {})


def test_full_trusted_contract_runs_in_shared_validator(tmp_path, monkeypatch):
    # Assignment and helper calls cannot be represented by compile_domain.
    contract = '''\n    def permitted(value):\n        return value % 2 == 0\n    minimum = 0\n    assert isinstance(x, int) and x >= minimum and permitted(x)\n'''
    batch = generated_batch(tmp_path, monkeypatch, contract)
    assert batch['status'] == 'complete'
    assert [row['args'] for row in batch['inputs']] == ['(2,)', '(4,)']
    assert [row['selection'] for row in batch['pynguin']['candidate_ledger']] == [
        'selected_stable_owner_test_order', 'rejected', 'duplicate', 'selected_stable_owner_test_order']
    assert batch['rejected'][0]['reason'] == 'outside_trusted_domain'


def test_validator_infrastructure_failure_cannot_admit(tmp_path, monkeypatch):
    def failed(job):
        raise ExecutionError('sandbox unavailable')
    monkeypatch.setattr(adapter, 'execute', failed)
    batch = generated_batch(tmp_path, monkeypatch, 'assert x >= 0')
    assert batch['status'] == 'failed'
    assert batch['pynguin']['owner_failures'][0]['reason'] == 'domain_validation_failed'
    assert not batch['inputs']


@pytest.mark.parametrize('contract,reason', [
    ('assert x < 0', None),
    ('raise RuntimeError("broken contract")', 'domain_validation_error:error'),
    ('while True:\n    pass', 'domain_validation_error:timeout'),
])
def test_rejected_or_unresolved_domain_is_never_admitted(tmp_path, monkeypatch, contract, reason):
    # Exercise the real validator without dispatching an upstream search.
    if 'while' in contract:
        original = adapter.execute
        monkeypatch.setattr(adapter, 'execute', lambda job: original({**job, 'timeout': .02}))
    batch = generated_batch(tmp_path, monkeypatch, contract)
    if reason:
        assert not batch['inputs']
        assert {row['reason'] for row in batch['rejected']} == {reason}
    else:
        assert [row['args'] for row in batch['inputs']] == ['(-1,)']


def test_domain_infrastructure_failure_preserves_other_owner_inputs(tmp_path,monkeypatch):
    ctx=context(tmp_path)
    ctx.cohort_task['programs'].append({'id':'p2','code':ctx.cohort_task['programs'][0]['code'],'base':{'status':'pass'}})
    ctx.packet['visible_put_ids'].append('p2')
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    monkeypatch.setattr(generator,'search_owner',lambda context,prefix,index,owner: {
        'owner':owner['id'],'status':'complete','calls':[{'test':'test_0','args':repr((index+1,)),'kwargs':'{}'}]})
    original=adapter.execute
    def validate(job):
        if job['tests'][0]['args']=='(2,)': raise ExecutionError('sandbox unavailable')
        return original(job)
    monkeypatch.setattr(adapter,'execute',validate)
    batch=generator.construct(ctx,'unused/',{})
    assert batch['status']=='partial'
    assert [row['args'] for row in batch['inputs']]==['(1,)']
    assert batch['pynguin']['owner_failures']==[{'owner':'p2','status':'failed','reason':'domain_validation_failed'}]
    assert batch['pynguin']['owners'][1]['domain_validation']['status']=='failed'
    assert batch['rejected'][0]['reason']=='domain_validation_failed'


@pytest.mark.parametrize('contract',[None,'',' \n '])
def test_missing_trusted_contract_fails_closed_before_search(tmp_path,monkeypatch,contract):
    ctx=context(tmp_path)
    if contract is None: ctx.metadata.pop('contract')
    else: ctx.metadata['contract']=contract
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    monkeypatch.setattr(generator,'search_owner',lambda *args: pytest.fail('must not search without contract'))
    batch=generator.construct(ctx,'unused/',{})
    assert batch['status']=='unsupported_input' and batch['reason']=='missing_trusted_contract'
    assert not batch['inputs']
