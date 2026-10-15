"""Independently specified design fixtures, not benchmark oracle labels."""

def requirement(mode='preserve',eligibility='all',element_type='str'):
    text=f'Return a sequence with {mode} occurrence counts of each input element eligible under {eligibility}.'
    return dict(mode=mode,eligibility=eligibility,element_type=element_type,argument=0,
                review_status='fixture_spec',provenance='independently_authored_fixture',quote=text,spec=text,span=[0,len(text)])


def cases():
    return [
        dict(id='dedup',source='def f(xs):\n return sorted(set(xs))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=True,candidate_output_violation=True)),
        dict(id='sorting_preserves',source='def f(xs):\n return sorted(xs)\n',args=(['b','a','a'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='unique_spec',source='def f(xs):\n return sorted(set(xs))\n',args=(['aa','aa'],),requirement=requirement('unique'),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='unused_local',source='def f(xs):\n ys=set(xs)\n return xs\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='restored_count',source='def f(xs):\n return sorted(set(xs))*2\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='scalar_distinct_count',source='def f(xs):\n return len(set(xs))\n',args=(['aa','aa'],),requirement=requirement('unique'),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='untaken_operation',source='def f(xs, flag):\n return xs if flag else sorted(set(xs))\n',args=(['aa','aa'],True),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='taken_operation',source='def f(xs, flag):\n return xs if flag else sorted(set(xs))\n',args=(['aa','aa'],False),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='nested_sets',source='def f(xs):\n return sorted(set(set(xs)))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=True,candidate_output_violation=True)),
        dict(id='same_line_sets',source='def f(xs):\n return sorted(set(xs)-set([]))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=True,candidate_output_violation=True)),
        dict(id='eligibility_not_domain',source='def f(xs):\n return sorted(set(xs))\n',args=([-1,-1,2],),requirement=requirement(eligibility='positive',element_type='int'),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='eligible_loss',source='def f(xs):\n return sorted(set(xs))\n',args=([-1,2,2],),requirement=requirement(eligibility='positive',element_type='int'),expect=dict(supported=True,native_checked=True,complete_evidence=True,candidate_output_violation=True)),
        dict(id='unreviewed_candidate',source='def f(xs):\n return sorted(set(xs))\n',args=(['aa','aa'],),requirement=dict(requirement(),review_status='unreviewed'),expect=dict(supported=True,native_checked=True,complete_evidence=True,candidate_output_violation=True,grounded_reviewed=False)),
        dict(id='wrong_argument_binding',source='def f(xs, ys):\n return sorted(set(ys))\n',args=(['aa','aa'],['bb','bb']),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='exception_uncommitted',source='def f(xs):\n return sorted(set([[]]))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=False)),
        dict(id='shadowed_builtin',source='def f(xs, set):\n return list(set(xs))\n',args=(['a'],True),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='side_effect',source='def f(xs):\n xs.sort()\n return xs\n',args=(['b','a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='match_unsupported',source='def f(xs):\n match xs:\n  case []: return []\n  case _: return xs\n',args=(['a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='loop_unsupported',source='def f(xs):\n ys=[]\n for x in xs: ys.append(x)\n return ys\n',args=(['a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='top_level_execution',source='print("bad")\ndef f(xs):\n return xs\n',args=(['a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='default_execution',source='def f(xs=list()):\n return xs\n',args=(['a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='lambda_shadows_argument',source="def f(xs):\n return sorted(set(list(filter(lambda xs: xs, ['a','a']))))\n",args=(['bb','bb'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='lambda_shadows_other_argument',source='def f(xs, ys):\n return list(set(sorted(xs,key=lambda ys: len(ys))))\n',args=(['aa','aa'],['bb','bb']),requirement=dict(requirement(),argument=1),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='entry_shadows_builtin',entry='set',source='def set(xs):\n return list(set(xs))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='wrong_eligible_loss',source='def f(xs):\n return sorted(set(list(filter(lambda x: x < 0, xs))))\n',args=([-1,-1,2,2],),requirement=requirement(eligibility='positive',element_type='int'),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='literal_conditional_provenance',source="def f(xs):\n return sorted(set(xs if False else ['b','b']))\n",args=(['a','a'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='masked_by_zero',source='def f(xs):\n ys=set(xs)\n return list(ys)*0\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='unique_restored_duplicates',source='def f(xs):\n return sorted(set(xs))*2\n',args=(['aa','aa'],),requirement=requirement('unique'),expect=dict(supported=True,native_checked=True,complete_evidence=False,candidate_output_violation=True)),
        dict(id='argument_reassignment',source='def f(xs):\n xs=sorted(xs)\n return list(set(xs))\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='self_assignment',source='def f(xs):\n xs=xs\n return xs\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='unbound_self_definition',source='def f(xs):\n a=list(a)\n return a\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='local_reassignment',source='def f(xs):\n a=xs\n a=list(a)\n return a\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
        dict(id='oversize_ast',source='def f(xs):\n return '+' + '.join(['xs']*1200)+'\n',args=(['aa','aa'],),requirement=requirement(),expect=dict(supported=False,complete_evidence=False)),
    ]
