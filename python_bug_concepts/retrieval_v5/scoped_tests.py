import ast
import tempfile
import unittest
from pathlib import Path
from .facts import Analysis
from .engine import search

class ScopedFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/'index.sqlite3'
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def packet(self,source):return search(code=source,top_k=100,db=self.db)
    def ids(self,source):return {r['concept']['id'] for r in self.packet(source)['results']}

    def test_nonempty_guard_excludes_guarded_index(self):
        self.assertNotIn('py.index-out-of-bounds',self.ids('def f(s: str):\n if not s: return 0\n return s[0]'))
    def test_assigning_after_guard_invalidates_protection(self):
        self.assertIn('py.index-out-of-bounds',self.ids('def f(s: str):\n if not s: return 0\n s=""\n return s[0]'))
    def test_alias_mutation_invalidates_protection(self):
        source='def f(xs: list):\n if not xs: return 0\n alias=xs\n alias.clear()\n return xs[0]'
        self.assertIn('py.index-out-of-bounds',self.ids(source))
    def test_guard_in_other_scope_does_not_protect(self):
        source='def f(xs: list):\n if not xs: return 0\n def g(xs: list):\n  return xs[0]\n return g([])'
        packet=self.packet(source)
        self.assertTrue(any(h['concept']['id']=='py.index-out-of-bounds' and any(e['line']==4 for e in h['evidence']) for h in packet['results']))
    def test_branch_polarity_is_preserved(self):
        good='def f(s: str):\n if s:\n  return s[0]\n return 0'
        bad='def f(s: str):\n if not s:\n  return s[0]\n return 0'
        self.assertNotIn('py.index-out-of-bounds',self.ids(good))
        self.assertIn('py.index-out-of-bounds',self.ids(bad))
    def test_arbitrary_len_object_is_not_proven_builtin_sequence(self):
        self.assertIn('py.index-out-of-bounds',self.ids('def f(x):\n if len(x)==0:return 0\n return x[0]'))
    def test_nonempty_guard_does_not_protect_large_index(self):
        self.assertIn('py.index-out-of-bounds',self.ids('def f(x: list):\n if not x:return 0\n return x[100]'))
    def test_unknown_call_invalidates_guard(self):
        self.assertIn('py.index-out-of-bounds',self.ids('def f(x: list):\n if not x:return 0\n mutate_alias()\n return x[0]'))
    def test_resolved_builtin_length_guard(self):
        self.assertNotIn('py.index-out-of-bounds',self.ids('def f(x: list):\n if len(x)==0:return 0\n return x[-1]'))
    def test_shadowed_len_is_not_builtin_proof(self):
        self.assertIn('py.index-out-of-bounds',self.ids('def f(x: list, len):\n if len(x)==0:return 0\n return x[0]'))
    def test_guarded_reduction(self):
        self.assertNotIn('py.empty-reduction-domain',self.ids('def f(x: list):\n if not x:return None\n return min(x)'))
    def test_builtin_tie_rule_requires_public_tie_contract(self):
        good='def f(xs):\n """Return the first longest string in case of a tie."""\n return max(xs,key=len)'
        self.assertNotIn('py.tie-break-selection',self.ids(good))
        unknown=good.replace('key=len','key=score')
        self.assertIn('py.tie-break-selection',self.ids(unknown))
    def test_first_tie_semantics_does_not_hide_reversed_input(self):
        source='def f(xs):\n """Return the first longest string in case of a tie."""\n return max(reversed(xs),key=len)'
        self.assertIn('py.tie-break-selection',self.ids(source))
        reassigned=source.replace(' return max(reversed(xs),key=len)',' xs=list(reversed(xs))\n return max(xs,key=len)')
        self.assertIn('py.tie-break-selection',self.ids(reassigned))
    def test_first_tie_semantics_does_not_hide_inplace_reverse(self):
        source='def f(xs):\n """Return the first longest string in case of a tie."""\n xs.reverse()\n return max(xs,key=len)'
        self.assertIn('py.tie-break-selection',self.ids(source))
    def test_public_examples_refute_count_equality_claim(self):
        source='def f(a,b):\n """Return True for same characters, duplicates permitted.\n >>> f("aab", "ab")\n True\n """\n return set(a)==set(b)'
        result=self.packet(source)
        self.assertNotIn('py.set-loses-multiplicity',{h['concept']['id'] for h in result['results']})
        self.assertTrue(any(r['applicability']['contradictions'][0]['kind']=='public_count_equality_counterexample' for r in result['excluded_bindings']))
    def test_example_from_another_function_is_not_target_contract(self):
        source='def f(a,b):\n """Count duplicates.\n >>> other("aab", "ab")\n True\n """\n return set(a)==set(b)'
        self.assertIn('py.set-loses-multiplicity',self.ids(source))
    def test_source_span_uses_unicode_character_columns(self):
        source='def f(x):\n é = "é"; return len(x.encode())'
        analysis=Analysis(source)
        node=next(n for n in analysis.nodes if isinstance(n,ast.Call) and analysis.api(n)=='len')
        self.assertEqual(analysis.fact(node)['span']['column'],source.splitlines()[1].index('len'))
    def test_qualified_builtin_vs_shadowed_call(self):
        analysis=Analysis('def f(max,x):\n return max(x)')
        call=next(n for n in analysis.nodes if isinstance(n,ast.Call))
        self.assertNotEqual(analysis.api(call),'max')
    def test_origin_chain_retains_transformations(self):
        a=Analysis('def f(s):\n x=s.lower()\n y=x.encode()\n return len(set(y))')
        chain=next(iter(a.output_origins().values()))
        effects=[r['effect'] for r in chain]
        for effect in ['text_normalization','text_to_bytes','occurrences_to_membership','measure_length']:self.assertIn(effect,effects)
    def test_conditional_assignment_does_not_become_definite_origin(self):
        a=Analysis('def f(s,flag):\n x=s\n if flag:x=s.encode()\n return x')
        chain=next(iter(a.output_origins().values()))
        self.assertNotIn('text_to_bytes',[r['effect'] for r in chain])
        self.assertTrue(any(r.get('status')=='parameter_or_unresolved' for r in chain))
    def test_initializer_is_bound_to_own_definition(self):
        result=self.packet('def f(xs):\n best=0\n for x in xs:\n  if x>best:best=x\n return best')
        hit=next(h for h in result['results'] if h['concept']['id']=='py.extremum-initial-sentinel')
        self.assertEqual(hit['evidence'][0]['line'],2)
        self.assertEqual(hit['instantiated']['where']['expression'],'best=0')
    def test_origin_definition_never_crosses_function_scope(self):
        a=Analysis('def first():\n x="a".encode()\n return x\ndef second(x):\n return x')
        returns=[n for n in a.nodes if isinstance(n,ast.Return)]
        chain=a.origins(returns[-1].value)
        self.assertNotIn('text_to_bytes',[r['effect'] for r in chain])
    def test_aligned_loop_index_and_mutation(self):
        good='def f(xs: list):\n for i in range(len(xs)-1):\n  x=xs[i+1]\n return 0'
        self.assertNotIn('py.index-out-of-bounds',self.ids(good))
        bad=good.replace('  x=','  xs.clear()\n  x=')
        self.assertIn('py.index-out-of-bounds',self.ids(bad))
    def test_loop_index_reassignment_invalidates_bounds(self):
        bad='def f(xs: list):\n for i in range(len(xs)):\n  i=100\n  x=xs[i]\n return 0'
        self.assertIn('py.index-out-of-bounds',self.ids(bad))
    def test_slice_write_and_delete_invalidate_guard(self):
        for mutation in ['x[:]=[]','del x[:]']:
            source='def f(x: list):\n if not x:return 0\n '+mutation+'\n return x[0]'
            self.assertIn('py.index-out-of-bounds',self.ids(source))
    def test_rebinding_before_guard_overrides_annotation(self):
        source='def f(s: str):\n s=[]\n if s=="":return 0\n return s[0]'
        self.assertIn('py.index-out-of-bounds',self.ids(source))
    def test_conditional_rebinding_before_guard_is_unknown(self):
        source='def f(s: str, flag):\n if flag:s=[]\n if s=="":return 0\n return s[0]'
        self.assertIn('py.index-out-of-bounds',self.ids(source))
    def test_no_invented_expected_oracle_and_source_ids(self):
        result=self.packet('def f(s):\n """Count distinct characters."""\n return len(set(s.encode()))')
        for hit in result['results']:
            self.assertIsNone(hit['instantiated']['what']['expected_output'])
            fid=hit['instantiated']['where']['fact_id']
            if fid:self.assertIn(fid,{f['id'] for f in result['facts']['facts']})
    def test_expanding_assignment_graph_has_bounded_origins(self):
        source='def f(x):\n a0=x\n'+''.join(f' a{i}=a{i-1}+a{i-1}\n' for i in range(1,18))+' return a17'
        a=Analysis(source)
        chain=next(iter(a.output_origins().values()))
        self.assertLess(len(chain),600)
        self.assertTrue(any(r.get('reason')=='origin_node_budget' for r in chain))
    def test_public_api_explicit_v5_and_default_still_v2(self):
        from ..api import search as routed
        code='def f(x):\n return x[len(x)]'
        self.assertEqual(routed(code=code,retriever='v5',db=self.db)['engine_version'],'scoped-v5.1')
        self.assertEqual(routed(code=code)['engine_version'],'structure-v2.2')
    def test_cannot_execute_target_side_effect(self):
        marker=Path(self.tmp.name)/'must_not_exist'
        self.packet(f'from pathlib import Path\nPath({str(marker)!r}).touch()')
        self.assertFalse(marker.exists())
    def test_syntax_failure_retains_lexical_fallback(self):
        result=search('B006',code='def bad(',db=self.db)
        self.assertIsNone(result['facts'])
        self.assertTrue(result['warning'])

if __name__=='__main__':unittest.main()
