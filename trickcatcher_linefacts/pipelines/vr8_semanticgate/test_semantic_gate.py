import ast
import unittest
from .semantic_gate import bind,Probe


def fixture(source,card,expression,entry='f'):
    tree=ast.parse(source);want=ast.dump(ast.parse(expression,mode='eval').body)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.expr) and ast.dump(n)==want)
    return dict(put=source,entry=entry),dict(card_id=card,retrieval_evidence=dict(line=node.lineno,end_line=node.end_lineno,expression=expression))


class SemanticGateTests(unittest.TestCase):
    def probe(self,source,card,expression):
        task,fact=fixture(source,card,expression);b=bind(task,fact)
        self.assertEqual(b['status'],'supported',b)
        return Probe(source,'f',[b]),b

    def test_normalization_distinguishes_value_change_and_preserves_result(self):
        p,b=self.probe('def f(s):\n return s.lower()','py.text-normalization-contract','s.lower()')
        for s,hit in [('abc',False),('Abc',True)]:
            states,out=p.run((s,));self.assertIs(states[0]['state'],hit);self.assertEqual(out,('ok',s.lower()))
        self.assertEqual(b['requirement_status'],'unknown')

    def test_replace_and_same_line_other_call_do_not_cross_bind(self):
        p,_=self.probe('def f(a,b):\n return a.lower(),b.lower()','py.text-normalization-contract','a.lower()')
        states,out=p.run(('abc','UPPER'));self.assertIs(states[0]['state'],False);self.assertEqual(out,('ok',('abc','upper')))
        q,_=self.probe("def f(s):\n return s.replace(' ', '')",'py.text-normalization-contract',"s.replace(' ', '')")
        self.assertIs(q.run(('a b',))[0][0]['state'],True)

    def test_unreached_and_wrong_runtime_type_are_unknown(self):
        p,_=self.probe('def f(s):\n return s.lower() if s else s','py.text-normalization-contract','s.lower()')
        self.assertIsNone(p.run(('',))[0][0]['state'])
        self.assertIsNone(p.run((2,))[0][0]['state'])

    def test_finite_class_missing_member_and_benign_complete_class(self):
        src='def f(s):\n """Count uppercase vowels."""\n return s in "AEOU"'
        p,b=self.probe(src,'py.literal-classification-domain','s in "AEOU"')
        self.assertEqual(b['expected_members'],'AEIOU')
        self.assertIs(p.run(('I',))[0][0]['state'],True)
        self.assertIs(p.run(('A',))[0][0]['state'],False)
        self.assertIs(p.run(('x',))[0][0]['state'],False)
        q,_=self.probe(src.replace('AEOU','AEIOU'),'py.literal-classification-domain','s in "AEIOU"')
        self.assertIs(q.run(('I',))[0][0]['state'],False)
        self.assertIsNone(p.run(('II',))[0][0]['state'])

    def test_membership_without_public_class_cue_is_unsupported(self):
        t,f=fixture('def f(s):\n return s in "ABC"','py.literal-classification-domain','s in "ABC"')
        self.assertEqual(bind(t,f)['status'],'unsupported')

    def test_numeric_order_inversion_and_agreement(self):
        p,_=self.probe('def f(a,b):\n return str(a)<str(b)','py.lexicographic-numeric-order','str(a)<str(b)')
        self.assertIs(p.run((10,2))[0][0]['state'],True)
        self.assertIs(p.run((1,2))[0][0]['state'],False)
        self.assertIsNone(p.run(('NaN','2'))[0][0]['state'])

    def test_literal_domain_order_and_unknown_value(self):
        src='def f(a,b):\n ranks=["z","a","m"]\n if a<b:\n  return ranks.index(a)-ranks.index(b)\n return None'
        p,b=self.probe(src,'py.lexicographic-numeric-order','a<b')
        self.assertEqual(b['alternative'],'literal_rank')
        self.assertIs(p.run(('z','a'))[0][0]['state'],True)
        self.assertIsNone(p.run(('absent','z'))[0][0]['state'])

    def test_expression_evaluated_once_and_method_lookup_order_preserved(self):
        src='def f(s):\n seen=[]\n def value():\n  seen.append(1)\n  return s\n result=value().lower()\n return result,len(seen)'
        p,_=self.probe(src,'py.text-normalization-contract','value().lower()')
        self.assertEqual(p.run(('X',))[1],('ok',('x',1)))

    def test_bound_source_change_and_ambiguity_are_rejected(self):
        src='def f(s):\n return s.lower()'
        t,f=fixture(src,'py.text-normalization-contract','s.lower()');b=bind(t,f)
        with self.assertRaisesRegex(ValueError,'source_changed'):
            Probe(src.replace('lower','upper'),'f',[b])
        t['put']='def f(s):\n return s.lower(),s.lower()'
        self.assertEqual(bind(t,f)['reason'],'ambiguous_or_missing_expression')


if __name__=='__main__':unittest.main()
