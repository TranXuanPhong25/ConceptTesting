"""Context and observation regressions on authored sources; no model or benchmark calls."""
from copy import deepcopy
import json

from final.src.modular.control_flow.feedback_prompts import messages
from final.src.modular.control_flow.schema import parse_response
from final.src.modular.spec_obligation.evidence import Evidence






















def test_complete_miss_does_not_hide_another_partial_trace():
    from final.src.modular.control_flow.analysis import measure_targets
    target = {'id': 't', 'program_id': 'p0', 'criterion': 'C1', 'line': 3}
    rows = [{'program_id': 'p0', 'domain': 'valid', 'status': 'executed',
             'coverage': {'lines': [2], 'arcs': []}},
            {'program_id': 'p0', 'domain': 'valid', 'status': 'timeout',
             'coverage': {'lines': [2], 'arcs': []}}]
    measured = measure_targets([target], rows, [])[0]
    assert measured['status'] == 'unknown' and measured['complete_observations'] == 1
    assert measured['unknown_observations'] == 1
    rows[1]['coverage']['lines'].append(3)
    assert measure_targets([target], rows, [])[0]['status'] == 'hit'




def test_diagnostic_uses_all_observations_and_names_unobserved_target():
    from final.src.modular.control_flow.feedback import target_diagnostics
    targets = [{'id': 'a', 'program_id': 'p0', 'criterion': 'C1', 'line': 3},
               {'id': 'b', 'program_id': 'p1', 'criterion': 'C1', 'line': 3}]
    rows = [{'program_id': 'p0', 'call': {'args': '(i,)', 'kwargs': '{}'}, 'domain': 'valid',
             'status': 'executed', 'coverage': {'lines': [2], 'arcs': []}} for _ in range(20)]
    rows.append({**rows[0], 'call': {'args': '(9,)', 'kwargs': '{}'}, 'coverage': {'lines': [2, 3], 'arcs': []}})
    a, b = target_diagnostics(targets, rows)
    assert a['target_hit'] and a['call']['args'] == '(9,)'
    assert b['status'] == 'unknown' and b['reason'] == 'no_native_observation'


