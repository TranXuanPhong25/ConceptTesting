"""Check hand-authored contrast examples, not an extractor or benchmark result."""
import json
from pathlib import Path

pack = json.loads(Path(__file__).with_name('CANDIDATE_CONCEPTS.json').read_text())
cards = {c['id']: c for c in pack['cards']}
assert len(cards) == len(pack['cards']) == 5
assert pack['runtime_default_changed'] is False
for c in cards.values():
    assert c['status'] == 'design_candidate_not_runtime'
    assert c['bindings'] and c['scope'] and 'unknown' in c['domain']
    assert c['requirement_sources'] == ['public_spec_quote', 'public_example']
    assert c['obligation'] and c['benign'] and c['guide']

x = cards['sem.text_normalization']['example']
assert (x['left'].lower() == x['right'].lower()) == x['projected_values_equal']
assert (x['left'] == x['right']) == x['required_values_equal']
# Same normalization is benign under a case-insensitive equality contract.
assert x['left'].casefold() == x['right'].casefold()

x = cards['sem.multiplicity_projection']['example']
assert (set(x['left']) == set(x['right'])) == x['projected_values_equal']
assert (len(x['left']) == len(x['right'])) == x['required_values_equal']
# Duplicate projection is benign for distinct-count rather than occurrence-count.
assert len(set(x['left'])) == len(set(x['right']))

x = cards['sem.comparison_order']['example']
assert (x['left'] < x['right']) == x['observed_left_less']
assert (int(x['left']) < int(x['right'])) == x['required_left_less']
# An ordinary line hit occurs for both agreeing and disagreeing ordering pairs.
assert ('1' < '2') == (int('1') < int('2'))
assert ('10' < '2') != (int('10') < int('2'))

x = cards['sem.classifier_membership']['example']
assert (x['symbol'] in x['observed_members']) == x['observed_member']
assert (x['symbol'] in x['required_members']) == x['required_member']
assert x['input'][1] == x['symbol']
assert all(c not in x['required_members'] for c in (x['input'][0], x['input'][-1]))
assert ('a' in x['observed_members']) == ('a' in x['required_members'])

x = cards['sem.recursive_work_structure']['example']
assert x['performance_violation_status'] == 'unknown'
print('5 draft definitions checked; 4 primitive contrasts and benign controls pass; no target execution.')
