"""Authored source-only controls, not native bugs, paper reproduction or efficacy."""
import ast
import unittest

from .facts import Analysis
from .operation_binding import verdict
from .hybrid_engine import Retriever, source_sites, query_slices
from . import engine


def at_call(code,name):
    a=Analysis(code)
    n=next(n for n in a.nodes if isinstance(n,ast.Call) and
           ((isinstance(n.func,ast.Name) and n.func.id==name) or
            (isinstance(n.func,ast.Attribute) and n.func.attr==name)))
    return a,n


class OperationEvidenceTests(unittest.TestCase):
    def test_same_operation_different_requirement(self):
        for requirement,excluded in [
            ('Return the number of distinct values.',True),
            ('Count unique items.',True),
            ('Return the number of occurrences including repeated values.',False),
            ('Return the number of occurrences, not distinct values.',False),
            ('Return the number of occurrences of each distinct value.',False),
            ('Never return the number of distinct values.',False),
            ('Return a count. Values may be distinct.',False)]:
            a,n=at_call(f'def measure(values):\n """{requirement}"""\n return len(set(values))\n','set')
            row=verdict(a,'py.set-loses-multiplicity',n)
            self.assertEqual(row['status'].startswith('excluded_'),excluded)
            if not excluded:
                self.assertEqual(row['status'],'grounded_test_opportunity_contract_unknown')

    def test_irrelevant_calls_do_not_gain_grounding(self):
        a,n=at_call('def count(values):\n return len(values)\n','len')
        for cid in ['py.empty-reduction-domain','py.unicode-text-byte-domain',
                    'py.legacy-print-redirection','py.mutable-default',
                    'py.finally-overrides-control-flow','py.numeric-cast-loss']:
            self.assertEqual(verdict(a,cid,n)['status'],'unbound_operation_mismatch')

    def test_derived_reduction_and_defined_join_differ(self):
        a,n=at_call('def choose(xs):\n return min(x for x in xs if x>0)\n','min')
        self.assertTrue(verdict(a,'py.empty-reduction-domain',n)['operation_support'])
        a,n=at_call('def combine(xs):\n return "".join(str(x) for x in xs)\n','join')
        self.assertEqual(verdict(a,'py.empty-reduction-domain',n)['status'],'unbound_operation_mismatch')

    def test_builtin_shadowing_is_not_builtin_semantics(self):
        a,n=at_call('def choose(min, xs):\n return min(xs)\n','min')
        self.assertEqual(verdict(a,'py.empty-reduction-domain',n)['status'],'unbound_role_unknown')

    def test_qualified_and_imported_builtin_alias(self):
        for code,name in [('import builtins\ndef choose(xs):\n return builtins.min(xs)\n','min'),
                          ('from builtins import min as smallest\ndef choose(xs):\n return smallest(xs)\n','smallest')]:
            a,n=at_call(code,name)
            self.assertTrue(verdict(a,'py.empty-reduction-domain',n)['operation_support'])

    def test_unknown_callable_alias_abstains(self):
        for code in ['def choose(fn,xs):\n return fn(xs)\n',
                     'def choose(xs):\n fn = select_operation()\n return fn(xs)\n']:
            a,n=at_call(code,'fn')
            self.assertEqual(verdict(a,'py.empty-reduction-domain',n)['status'],'unbound_role_unknown')

    def test_nested_yield_does_not_make_outer_generator(self):
        a=Analysis('def outer():\n def inner():\n  yield 1\n return inner\n')
        functions={n.name:n for n in a.nodes if isinstance(n,ast.FunctionDef)}
        self.assertEqual(verdict(a,'py.generator-return-is-not-yield',functions['outer'])['operation_support'],False)
        self.assertEqual(verdict(a,'py.generator-return-is-not-yield',functions['inner'])['operation_support'],True)

    def test_mutable_default_requires_real_default(self):
        for default,grounded in [('None',False),('[]',True)]:
            a=Analysis(f'def collect(values={default}):\n return values\n')
            n=next(n for n in a.nodes if isinstance(n,ast.FunctionDef))
            self.assertEqual(verdict(a,'py.mutable-default',n)['operation_support'],grounded)

    def test_finally_requires_control_in_final_body(self):
        for code,wanted in [('def f():\n return 1\n',False),
                            ('def f():\n try:\n  return 1\n finally:\n  return 2\n',True)]:
            a=Analysis(code)
            n=[n for n in a.nodes if isinstance(n,ast.Return)][-1]
            self.assertEqual(verdict(a,'py.finally-overrides-control-flow',n)['operation_support'],wanted)

    def test_public_case_requirement_negation(self):
        for contract,excluded in [('Compare regardless of case.',True),
                                  ('Compare while ignoring irrelevant details; ignore case.',True),
                                  ('Preserve case and do not ignore case.',False),
                                  ('Never ignore case.',False),
                                  ('Comparison is not case-insensitive.',False),
                                  ('Compare regardless of case. Retain case.',False),
                                  ('Return a value. The word case-insensitive is mentioned.',False)]:
            a,n=at_call(f'def convert(text):\n """{contract}"""\n return text.lower()\n','lower')
            self.assertEqual(verdict(a,'py.text-normalization-contract',n)['status'].startswith('excluded_'),excluded)

    def test_true_division_precision_is_not_floor_division(self):
        for operator,grounded in [('/',True),('//',False)]:
            a=Analysis(f'def divide(x,y):\n return x {operator} y\n')
            n=next(n for n in a.nodes if isinstance(n,ast.BinOp))
            self.assertEqual(verdict(a,'py.integer-division-precision',n)['operation_support'],grounded)

    def test_unimplemented_dense_relation_abstains(self):
        a,n=at_call('def f(xs):\n return len(xs)\n','len')
        self.assertEqual(verdict(a,'py.observation-after-transform',n)['status'],'unbound_role_unknown')


class IntegrationTests(unittest.TestCase):
    def test_legacy_control_keeps_parent_candidates_and_bindings(self):
        from ..retrieval_v7.hybrid_engine import Retriever as Parent
        code='def measure(values):\n """Return the number of occurrences including repeated values."""\n return len(set(values))\n'
        old,new=Parent(),Retriever(binder_policy='legacy')
        try:
            for arm in ['A','C']:
                before,after=old.search(code=code,arm=arm),new.search(code=code,arm=arm)
                self.assertEqual(before['candidates'],after['candidates'])
                signature=lambda p:[(h['concept']['id'],h['evidence'][0]['line']) for h in p['results']]
                self.assertEqual(signature(before),signature(after))
        finally:
            old.close();new.close()

    def test_no_fill_and_no_target_execution(self):
        code='def calculate(x):\n raise RuntimeError("THIS BODY MUST NEVER EXECUTE")\n'
        r=Retriever()
        try:
            p=r.search(code=code,arm='A')
            self.assertEqual(p['results'],[])
            self.assertTrue(p['screened_bindings'])
        finally:r.close()

    def test_coverage_reaches_late_local_operation(self):
        code='def transform(value):\n'+''.join(f' item_{i} = value + {i}\n' for i in range(80))+' return value.encode("utf8")\n'
        evidence,_,_,_,a,_=engine._candidates(code)
        sites,total=source_sites(a,evidence,spread=True)
        self.assertEqual(len(sites),64)
        self.assertGreater(total,64)
        q,_=query_slices(code,'',a,sites,'coverage')
        self.assertEqual(len(q['mechanism']),4)
        self.assertTrue(any('encode' in s for s in q['mechanism']))


class CompletenessTests(unittest.TestCase):
    def test_fixed_literal_and_constant_repeat_are_grounded(self):
        for pattern in ['"   "','" " * 3','3 * "x"']:
            a,n=at_call(f'def squash(text):\n return text.replace({pattern},"_")\n','replace')
            g=verdict(a,'py.fixed-chunk-run',n)
            self.assertTrue(g['operation_support'])
            self.assertEqual(g['status'],'grounded_test_opportunity_contract_unknown')

    def test_fixed_chunk_contract_is_not_automatically_a_bug(self):
        code='def chunks(text):\n """Replace every non-overlapping pair of spaces with one marker."""\n return text.replace("  ","_")\n'
        a,n=at_call(code,'replace')
        self.assertEqual(verdict(a,'py.fixed-chunk-run',n)['status'],'grounded_test_opportunity_contract_unknown')

    def test_dynamic_pattern_is_unknown(self):
        a,n=at_call('def squash(text,pattern):\n return text.replace(pattern,"_")\n','replace')
        self.assertEqual(verdict(a,'py.fixed-chunk-run',n)['status'],'unbound_role_unknown')

    def test_non_run_and_slices_are_unrelated(self):
        for pattern in ['"x"','"xy"','""']:
            a,n=at_call(f'def change(text):\n return text.replace({pattern},"_")\n','replace')
            self.assertEqual(verdict(a,'py.fixed-chunk-run',n)['status'],'unbound_operation_mismatch')
        a=Analysis('def chunk(text):\n return text[::2]\n')
        n=next(n for n in a.nodes if isinstance(n,ast.Subscript))
        self.assertEqual(verdict(a,'py.fixed-chunk-run',n)['status'],'unbound_operation_mismatch')

    def test_unqualified_shadowed_replace_is_not_string_method(self):
        a,n=at_call('def change(replace,text):\n return replace(text,"  ","_")\n','replace')
        self.assertEqual(verdict(a,'py.fixed-chunk-run',n)['status'],'unbound_operation_mismatch')

    def test_nested_replace_grounded_only_at_actual_call(self):
        a,n=at_call('def outer(text):\n def helper(x):\n  return x.replace("  ","_")\n return helper(text)\n','replace')
        self.assertTrue(verdict(a,'py.fixed-chunk-run',n)['operation_support'])
        helper=next(n for n in a.nodes if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='helper')
        self.assertEqual(verdict(a,'py.fixed-chunk-run',helper)['status'],'unbound_operation_mismatch')

    def test_self_recursion_and_benign_termination_are_opportunities(self):
        for body in ['return recur(n)', 'return 0 if n<=0 else recur(n-1)']:
            a,n=at_call(f'def recur(n):\n {body}\n','recur')
            g=verdict(a,'py.recursive-base-progress',n)
            self.assertTrue(g['operation_support'])
            self.assertEqual(g['status'],'grounded_test_opportunity_contract_unknown')

    def test_existing_recursive_support_is_preserved_as_conditional(self):
        a,n=at_call('def recur(n):\n return recur(n-1)\n','recur')
        row=verdict(a,'py.recursive-base-progress',n,existing={'semantic_support':{'tier':2}})
        self.assertEqual(row['status'],'source_supported_conditional_hypothesis')

    def test_nested_callee_and_nested_outer_call_not_self_recursion(self):
        code='def recur(n):\n def helper(x):\n  return recur(x)\n return helper(n)\n'
        a=Analysis(code)
        for n in a.nodes:
            if isinstance(n,ast.Call):
                self.assertEqual(verdict(a,'py.recursive-base-progress',n)['status'],'unbound_operation_mismatch')

    def test_nested_self_recursive_function_is_local_positive(self):
        a=Analysis('def outer(n):\n def inner(x):\n  return inner(x-1)\n return inner(n)\n')
        for n in a.nodes:
            if isinstance(n,ast.Call):
                supported=isinstance(a.owner(n),ast.FunctionDef) and a.owner(n).name=='inner'
                self.assertEqual(verdict(a,'py.recursive-base-progress',n)['operation_support'],supported)

    def test_recursive_name_shadowing_is_not_self_binding(self):
        for code in ['def recur(recur,n):\n return recur(n)\n',
                     'def recur(n):\n recur = lambda x:x\n return recur(n)\n']:
            a,n=at_call(code,'recur')
            self.assertEqual(verdict(a,'py.recursive-base-progress',n)['status'],'unbound_operation_mismatch')


if __name__=='__main__':unittest.main()
