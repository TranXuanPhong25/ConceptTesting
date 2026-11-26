"""Observed coverage must come from input membership, never model labels."""
from final.src.modular.tests.test_testing_arms import measure, bva, task
from final.src.modular.black_box.catalogue import measure_catalogue
from final.src.modular.call_builder import CallBuilder


def test_ep_predicate_witnesses_and_false_covers():
    result = measure({'classes':[
        {'id':'positive','description':'x > 0','predicate':'x > 0'},
        {'id':'negative','description':'x < 0','predicate':'x < 0'}]},
        [{'arguments':{'x':2},'covers':['negative']}], name='equivalence')
    observed = result['observed']
    positive, negative = observed['classes']
    assert positive['status'] == 'hit' and positive['input_indices'] == [0]
    assert negative['status'] == 'miss'
    assert observed['summary']['classes'] == {'total':2,'hit':1,'miss':1,'unknown':0}
    assert observed['label_checks'][0]['false_cover_ids'] == ['negative']
    assert observed['label_checks'][0]['undeclared_hit_ids'] == ['positive']
    assert result['declared']['covered_ids'] == ['negative']
    assert result['semantic_audit'] == 'pending'


def test_missing_invalid_and_non_boolean_predicates_are_unknown():
    raw = {'classes':[
        {'id':'prose','description':'prose only'},
        {'id':'unsafe','description':'unsafe','predicate':'__import__("os").getcwd()'},
        {'id':'numeric','description':'not boolean','predicate':'x + 1'},
        {'id':'error','description':'division','predicate':'1 / x > 0'}]}
    observed = measure(raw,[{'arguments':{'x':0},'covers':['unsafe','prose']}],
                       name='equivalence')['observed']
    assert all(row['status'] == 'unknown' for row in observed['classes'])
    assert observed['summary']['classes']['unknown'] == 4
    assert observed['label_checks'][0]['unknown_cover_ids'] == ['prose','unsafe']
    assert observed['label_checks'][0]['false_cover_ids'] == []


def test_legacy_numeric_class_is_measured_without_covers():
    raw = {'classes':[{'id':'E','description':'positive','parameter':'x','lower':1}]}
    result = measure(raw,[{'arguments':{'x':2}}],name='equivalence')
    assert result['observed']['classes'][0]['status'] == 'hit'
    assert result['observed']['classes'][0]['source_input_indices'] == [0]


def test_dt_measures_original_combinations_not_merged_label():
    raw = {'conditions':{'positive':['T','F']},
           'condition_predicates':{'positive':'x > 0'},
           'original_rules':[
               {'id':'T','conditions':{'positive':'T'},'actions':['same']},
               {'id':'F','conditions':{'positive':'F'},'actions':['same']}],
           'rules':[{'id':'merged','conditions':{'positive':'-'},'actions':['same'],
                     'merged_from':['T','F']}]}
    result = measure(raw,[{'arguments':{'x':3},'covers':['merged','F']}],name='decision_table')
    observed = result['observed']
    assert [(r['id'],r['status']) for r in observed['original_rules']] == [('T','hit'),('F','miss')]
    assert observed['summary']['original_rules'] == {'total':2,'hit':1,'miss':1,'unknown':0}
    assert observed['label_checks'][0]['false_cover_ids'] == ['F']
    assert observed['rules'][0]['status'] == 'hit'


def test_dt_missing_conditions_and_multivalued_conditions_are_unknown():
    raw = {'rules':[{'id':'R','conditions':{'category':'red'},'actions':['A']}]}
    observed = measure(raw,[{'arguments':{'x':1},'covers':['R']}],name='decision_table')['observed']
    assert observed['original_rules'][0]['status'] == 'unknown'
    assert observed['summary']['original_rules']['unknown'] == 1


def test_merged_only_dt_does_not_invent_original_denominator():
    raw = {'rules':[{'id':'R','conditions':{'C':'-'},'actions':['A']}]}
    observed = measure(raw,[{'arguments':{'x':1},'covers':['R']}],name='decision_table')['observed']
    assert observed['summary']['original_rules']['total'] is None
    assert observed['original_rules'] == []


def test_boundary_targets_have_witnesses_and_context_misses():
    raw = {'boundaries':[bva(context={'y':6},nominal={'x':6,'y':6})]}
    result = measure(raw,[{'arguments':{'x':1,'y':6}},
                          {'arguments':{'x':12,'y':7},'covers':['B1']}],source='def f(x,y): pass')
    row = result['observed']['boundaries'][0]
    assert row['status'] == 'miss'  # All boundary target values are required.
    assert row['targets'][0]['status'] == 'hit'
    assert row['targets'][0]['input_indices'] == [0]
    assert row['targets'][-1]['status'] == 'miss'
    assert result['observed']['label_checks'][1]['false_cover_ids'] == ['B1']


def test_boundary_without_nominal_separates_value_hit_from_single_fault():
    boundary = bva()
    boundary.pop('nominal')
    result = measure({'boundaries':[boundary]},[{'arguments':{'x':1}}])
    assert result['observed']['boundaries'][0]['targets'][0]['status'] == 'hit'
    assert result['observed']['boundaries'][0]['single_fault'] == 'pending'
    assert result['boundaries'][0]['missing_values'] is None


def test_survivor_witness_indices_refer_to_original_arm_inputs():
    builder = CallBuilder.for_source('def f(x): pass','f')
    batch = {'catalogue':{'classes':[{'id':'E','description':'positive','predicate':'x > 0'}]},
             'inputs':[builder.build({'x':-1}),builder.build({'x':2})]}
    result = measure_catalogue(batch,task(),[1],arm_name='equivalence',input_budget=20)
    row = result['observed']['classes'][0]
    assert row['input_indices'] == [0] and row['source_input_indices'] == [1]
    assert result['observed']['input_source_indices'] == [1]


def test_missing_metadata_with_empty_inputs_is_unknown_not_zero_coverage():
    raw = {'classes':[{'id':'E','description':'prose'}]}
    result = measure(raw,[],name='equivalence')['observed']
    assert result['classes'][0]['status'] == 'unknown'
    assert result['summary']['classes']['miss'] == 0


def test_membership_budget_exhaustion_keeps_unknown(monkeypatch):
    import final.src.modular.black_box.catalogue_membership as membership
    monkeypatch.setattr(membership,'MAX_PREDICATE_CHECKS',1)
    raw = {'classes':[{'id':'E','description':'positive','predicate':'x > 0'}]}
    observed = measure(raw,[{'arguments':{'x':-1}},{'arguments':{'x':2}}],name='equivalence')['observed']
    assert observed['classes'][0]['status'] == 'unknown'
    assert observed['classes'][0]['unknown_input_indices'] == [1]
    assert observed['budget']['predicate_checks'] == 1


def test_extended_membership_uses_existing_sandbox_for_joint_inputs():
    raw = {'classes':[{'id':'E','description':'all positive and small total',
                      'predicate':'all(x > 0 for x in xs) and sum(xs) < limit'}]}
    observed = measure(raw,[{'arguments':{'xs':[1,2],'limit':5}},
                            {'arguments':{'xs':[-1,2],'limit':5}}],name='equivalence',
                       source='def f(xs,limit): pass')['observed']
    assert observed['classes'][0]['input_statuses'] == ['hit','miss']


def test_unsupported_predicate_without_inputs_is_unknown():
    raw = {'classes':[{'id':'E','description':'unsafe','predicate':'x.secret()'}]}
    assert measure(raw,[],name='equivalence')['observed']['classes'][0]['status'] == 'unknown'


def test_output_class_without_input_predicate_is_unknown():
    raw = {'classes':[{'id':'E','description':'positive result','kind':'output',
                       'parameter':'x','lower':1}]}
    result = measure(raw,[{'arguments':{'x':2}}],name='equivalence')['observed']
    assert result['classes'][0]['status'] == 'unknown'


def test_dt_boolean_values_and_partial_unknown_do_not_hide_proven_miss():
    raw = {'condition_predicates':{'positive':'x > 0'},
           'rules':[{'id':'R','conditions':{'positive':True,'other':True},'actions':['A']}]}
    rows = measure(raw,[{'arguments':{'x':-1}},{'arguments':{'x':1}}],name='decision_table')['observed']
    assert rows['original_rules'][0]['input_statuses'] == ['miss','unknown']
    assert rows['original_rules'][0]['status'] == 'unknown'


def test_empty_checkable_class_has_no_witness_and_is_missed():
    raw = {'classes':[{'id':'E','description':'positive','predicate':'x > 0'}]}
    result = measure(raw,[],name='equivalence')['observed']
    assert result['classes'][0]['status'] == 'miss'


def test_condition_predicates_are_in_rendered_contracts():
    from final.src.modular.plain import PlainArm
    from final.src.modular.black_box import EpBvaArm, DecisionTableArm
    from final.src.modular.input_prompts import input_prompt_blocks, structured_input_prompt
    packet = {'prompt_blocks': input_prompt_blocks(task(), [], '', 20)}
    plain_prompt = PlainArm().build_messages(packet)[1]['content']
    ep_prompt = EpBvaArm().build_messages(packet)[1]['content']
    dt_prompt = DecisionTableArm().build_messages(packet)[1]['content']
    assert 'Return JSON:' in plain_prompt and 'Keep floats finite' not in plain_prompt
    assert 'supplied JSON Schema' in ep_prompt and 'class predicate' in ep_prompt
    assert 'supplied JSON Schema' in dt_prompt and 'C1..Cn' in dt_prompt

    old_packet = {'common': structured_input_prompt(task(), [], '', 20)}
    for arm in (PlainArm(), EpBvaArm(), DecisionTableArm()):
        assert arm.build_messages(packet) == arm.build_messages(old_packet)

    specification = dict(task(), prompt='INPUTS ONLY: no assertions or expected outputs.')
    packet = {'prompt_blocks': input_prompt_blocks(specification, [], '', 20)}
    assert f'SPECIFICATION:\n{specification["prompt"]}\n' in EpBvaArm().build_prompt(packet)


def test_original_rule_id_cannot_shadow_class_but_valid_inputs_survive(tmp_path):
    from final.src.modular.black_box.catalogue import validate_catalogue
    from final.src.modular.black_box import StructuredCatalogueArm
    from final.src.modular.tests.test_testing_arms import decode
    raw = {'classes':[{'id':'E','description':'negative','predicate':'x < 0'}],
           'boundaries':[bva()], 'conditions':{'C':[True,False]},
           'condition_predicates':{'C':'x > 0'},
           'original_rules':[{'id':'E','conditions':{'C':True},'actions':['A']},
                             {'id':'F','conditions':{'C':False},'actions':['B']}],
           'rules':[{'id':'R','conditions':{'C':True},'actions':['A'],'merged_from':['E']},
                    {'id':'RF','conditions':{'C':False},'actions':['B'],'merged_from':['F']}]}
    _, errors = validate_catalogue(raw,('classes','boundaries','rules'))
    assert 'original_rule_id_collision:E' in errors
    arm = StructuredCatalogueArm()
    arm.sections = ("classes", "boundaries", "rules")
    result = decode(arm,{'catalogue':raw,'inputs':[{'arguments':{'x':1},'covers':['E']}]},tmp_path)
    assert result['catalogue_status'] == 'catalogue_invalid'
    assert len(result['inputs']) == 1


def test_original_rule_id_can_match_identical_unmerged_rule():
    raw = {'condition_predicates':{'C':'x > 0'},
           'rules':[{'id':'R','conditions':{'C':True},'actions':['A']}],
           'original_rules':[{'id':'R','conditions':{'C':True},'actions':['A']}]}
    result = measure(raw,[{'arguments':{'x':-1},'covers':['R']}],name='decision_table')['observed']
    assert result['label_checks'][0]['false_cover_ids'] == ['R']
