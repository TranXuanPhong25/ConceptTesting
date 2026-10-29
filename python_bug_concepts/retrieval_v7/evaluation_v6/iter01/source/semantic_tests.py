import ast
import tempfile
import unittest
from pathlib import Path
from .engine import search
from .facts import Analysis

class SemanticRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.db=Path(cls.tmp.name)/'index.sqlite3'
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def packet(self,code,policy='precise'):
        return search(code=code,top_k=3,db=self.db,policy=policy)
    def hit(self,code,cid):
        return next((r for r in self.packet(code)['results'] if r['concept']['id']==cid),None)

    def test_out_of_bounds_site_is_the_unsafe_offset(self):
        code='def f(xs: list):\n """Return whether a list is sorted."""\n for i in range(len(xs)-1):\n  if xs[i]>xs[i+1]:return False\n  if xs[i]==xs[i+2]:return False\n return True'
        h=self.hit(code,'py.index-out-of-bounds')
        self.assertIsNotNone(h);self.assertEqual(h['instantiated']['where']['expression'],'xs[i+2]')
    def test_mutation_invalidates_upper_bound_hypothesis(self):
        code='def f(xs: list):\n for i in range(len(xs)-1):\n  xs.append(0)\n  x=xs[i+2]\n return True'
        h=self.hit(code,'py.index-out-of-bounds')
        self.assertFalse(h and h['ranking']['semantic_support']['tier']==3)
    def test_sentinel_offset_prefers_consuming_return(self):
        code='def f(xs: list):\n pos=0\n for i in range(1,len(xs)):\n  if xs[i]<xs[pos]:pos=i\n return xs[pos-1]'
        h=self.hit(code,'py.negative-index-sentinel');self.assertIsNotNone(h)
        self.assertEqual(h['evidence'][0]['line'],5)
    def test_ascii_literal_syntax_is_eligible(self):
        code='def f(s:str):\n """Flip lowercase and uppercase letters."""\n return "".join(c.lower() if "A"<=c<="Z" else c.upper() if "a"<=c<="z" else c for c in s)'
        self.assertIsNotNone(self.hit(code,'py.ascii-unicode-classification'))
    def test_requested_case_change_is_not_normalization_fault(self):
        code='def f(s:str):\n """Flip case."""\n return s.swapcase()'
        self.assertIsNone(self.hit(code,'py.text-normalization-contract'))
    def test_english_only_contract_is_not_strong_unicode_claim(self):
        code='def f(s:str):\n """Flip uppercase and lowercase English letters only."""\n return "".join(c.lower() if "A"<=c<="Z" else c for c in s)'
        h=self.hit(code,'py.ascii-unicode-classification')
        self.assertFalse(h and h['ranking']['semantic_support']['tier']>=2)
    def test_unique_membership_sort_retrieves_multiplicity(self):
        code='def f(xs):\n """Return the input numbers sorted."""\n domain={1:1,2:2,3:3}\n return [x for x in domain.keys() if domain[x] in xs]'
        self.assertIsNotNone(self.hit(code,'py.presence-frequency-confusion'))
    def test_sort_over_occurrences_is_not_unique_domain_loss(self):
        code='def f(xs):\n """Return the input numbers sorted."""\n return [x for x in sorted(xs)]'
        self.assertIsNone(self.hit(code,'py.presence-frequency-confusion'))
    def test_unknown_keys_method_is_not_proven_unique(self):
        code='def f(xs,custom):\n """Return the input numbers sorted."""\n return [x for x in custom.keys() if x in xs]'
        h=self.hit(code,'py.presence-frequency-confusion')
        self.assertFalse(h and h['ranking']['semantic_support']['tier']==3)
    def test_optimum_early_return_outranks_correct_index_lookup(self):
        code='def f(xs):\n """Return the smallest even item and first index."""\n m=min(xs)\n if m%2==0:return [m,xs.index(m)]\n for i,x in enumerate(xs):\n  if x%2==0:return [x,i]\n return []'
        r=self.packet(code)['results']
        self.assertEqual(r[0]['concept']['id'],'py.first-match-vs-optimum')
        self.assertEqual(r[0]['evidence'][0]['line'],6)
        self.assertNotIn('py.first-occurrence-position',{h['concept']['id'] for h in r})
    def test_sorted_early_return_is_not_false_optimum_fault(self):
        code='def f(xs):\n """Return the smallest even element."""\n for x in sorted(xs):\n  if x%2==0:return x\n return None'
        self.assertIsNone(self.hit(code,'py.first-match-vs-optimum'))
    def test_global_min_inside_loop_is_not_first_qualifying_item(self):
        code='def f(xs):\n """Return the smallest element."""\n for x in xs:\n  return min(xs)\n return None'
        self.assertIsNone(self.hit(code,'py.first-match-vs-optimum'))
    def test_coefficient_value_role_not_sequence_allocation(self):
        code='def f(xs):\n """Return polynomial derivative coefficients."""\n out=[0]*(len(xs)-1)\n out[-1]=xs[-1]*len(xs)\n return out'
        h=self.hit(code,'py.index-origin-domain');self.assertIsNotNone(h)
        self.assertEqual(h['evidence'][0]['line'],4)
    def test_ternary_direction_comparison_is_not_omitted(self):
        code='def f(xs):\n """Check monotonically increasing or decreasing input."""\n direction=1 if xs[0]<xs[1] else -1\n return direction'
        h=self.hit(code,'py.branch-boundary-contract');self.assertIsNotNone(h)
        self.assertEqual(h['evidence'][0]['line'],3)
    def test_empty_sum_identity_does_not_fill_top_slot(self):
        code='def f(xs: list):\n """Return the sum of entries."""\n if len(xs)==0:return 0\n return sum(xs)'
        self.assertIsNone(self.hit(code,'py.empty-singleton-shortcut'))
    def test_empty_balanced_sequence_rejection_is_supported(self):
        code='def f(s:str):\n """Check whether brackets are balanced."""\n if not s:return False\n return True'
        h=self.hit(code,'py.empty-singleton-shortcut');self.assertIsNotNone(h)
        self.assertEqual(h['ranking']['semantic_support']['tier'],3)
    def test_nonempty_contract_does_not_reject_its_own_guard(self):
        code='def f(xs:list):\n """Return sum for a non-empty list."""\n if len(xs)==0:raise ValueError()\n return sum(xs)'
        self.assertIsNone(self.hit(code,'py.empty-singleton-shortcut'))
    def test_plain_singleton_reduction_vs_transformed_reduction(self):
        benign='def f(xs:list):\n """Return minimum sum of any non-empty subarray."""\n if len(xs)==1:return xs[0]\n return 0'
        self.assertIsNone(self.hit(benign,'py.empty-singleton-shortcut'))
        bad=benign.replace('minimum sum of any non-empty subarray','sum of squared entries')
        self.assertIsNotNone(self.hit(bad,'py.empty-singleton-shortcut'))
    def test_source_flow_crosses_comprehension_outer_binding(self):
        a=Analysis('def f(s):\n data=s.encode()\n return [x for x in data]')
        effects=[x['effect'] for chain in a.output_origins().values() for x in chain]
        self.assertIn('text_to_bytes',effects)
    def test_conditional_definition_remains_unknown_inside_comprehension(self):
        a=Analysis('def f(s,flag):\n data=s\n if flag:data=s.encode()\n return [x for x in data]')
        effects=[x['effect'] for chain in a.output_origins().values() for x in chain]
        self.assertNotIn('text_to_bytes',effects)
    def test_unstated_rejection_bound_is_visible(self):
        code='def f(year):\n """Validate a year integer."""\n if year<1980:return False\n return True'
        h=self.hit(code,'py.branch-boundary-contract');self.assertIsNotNone(h)
        self.assertEqual(h['ranking']['semantic_support']['tier'],3)
    def test_stated_rejection_bound_is_not_contradicted(self):
        code='def f(year):\n """Validate a year integer, requires year >= 1980."""\n if year<1980:return False\n return True'
        h=self.hit(code,'py.branch-boundary-contract')
        self.assertFalse(h and h['ranking']['semantic_support']['tier']==3)
    def test_literal_none_check_does_not_treat_unknown_return_as_none(self):
        code='def f(xs:list):\n """Return None for empty input."""\n if len(xs)==0:return xs[0]\n return 0'
        self.assertIsNotNone(self.hit(code,'py.empty-singleton-shortcut'))
    def test_semantic_tier_and_source_survive_renaming(self):
        for fn,var in [('compute','items'),('arbitrary','zxy')]:
            code=f'def {fn}({var}):\n """Return smallest even element."""\n for x in {var}:\n  if x%2==0:return x\n return None'
            h=self.hit(code,'py.first-match-vs-optimum')
            self.assertIsNotNone(h);self.assertEqual(h['evidence'][0]['line'],4)
    def test_unknown_candidate_is_not_a_confirmed_bug(self):
        r=self.packet('def f(xs):\n return xs[0]')['results']
        self.assertTrue(all(h['status']=='unverified_fault_hypothesis' for h in r))
    def test_policy_is_explicit(self):
        with self.assertRaises(ValueError):self.packet('x=0',policy='invalid')

if __name__=='__main__':unittest.main()
