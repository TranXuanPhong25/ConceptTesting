import ast
import tempfile
import unittest
from pathlib import Path
from .engine import search
from .facts import Analysis


class SemanticRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "index.sqlite3"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def packet(self, code, policy="precise"):
        return search(code=code, top_k=3, db=self.db, policy=policy)

    def hit(self, code, cid):
        return next((r for r in self.packet(code)["results"] if r["concept"]["id"] == cid), None)

    def test_out_of_bounds_site_is_the_unsafe_offset(self):
        code = 'def f(xs: list):\n """Return whether a list is sorted."""\n for i in range(len(xs)-1):\n  if xs[i]>xs[i+1]:return False\n  if xs[i]==xs[i+2]:return False\n return True'
        h = self.hit(code, "py.index-out-of-bounds")
        self.assertIsNotNone(h)
        self.assertEqual(h["instantiated"]["where"]["expression"], "xs[i+2]")

    def test_mutation_invalidates_upper_bound_hypothesis(self):
        code = "def f(xs: list):\n for i in range(len(xs)-1):\n  xs.append(0)\n  x=xs[i+2]\n return True"
        h = self.hit(code, "py.index-out-of-bounds")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)

    def test_sentinel_offset_prefers_consuming_return(self):
        code = "def f(xs: list):\n pos=0\n for i in range(1,len(xs)):\n  if xs[i]<xs[pos]:pos=i\n return xs[pos-1]"
        h = self.hit(code, "py.negative-index-sentinel")
        self.assertIsNotNone(h)
        self.assertEqual(h["evidence"][0]["line"], 5)

    def test_ascii_literal_syntax_is_eligible(self):
        code = 'def f(s:str):\n """Flip lowercase and uppercase letters."""\n return "".join(c.lower() if "A"<=c<="Z" else c.upper() if "a"<=c<="z" else c for c in s)'
        self.assertIsNotNone(self.hit(code, "py.ascii-unicode-classification"))

    def test_requested_case_change_is_not_normalization_fault(self):
        code = 'def f(s:str):\n """Flip case."""\n return s.swapcase()'
        self.assertIsNone(self.hit(code, "py.text-normalization-contract"))

    def test_english_only_contract_is_not_strong_unicode_claim(self):
        code = 'def f(s:str):\n """Flip uppercase and lowercase English letters only."""\n return "".join(c.lower() if "A"<=c<="Z" else c for c in s)'
        h = self.hit(code, "py.ascii-unicode-classification")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] >= 2)

    def test_unique_membership_sort_retrieves_multiplicity(self):
        code = 'def f(xs):\n """Return the input numbers sorted."""\n domain={1:1,2:2,3:3}\n return [x for x in domain.keys() if domain[x] in xs]'
        self.assertIsNotNone(self.hit(code, "py.presence-frequency-confusion"))

    def test_sort_over_occurrences_is_not_unique_domain_loss(self):
        code = (
            'def f(xs):\n """Return the input numbers sorted."""\n return [x for x in sorted(xs)]'
        )
        self.assertIsNone(self.hit(code, "py.presence-frequency-confusion"))

    def test_unknown_keys_method_is_not_proven_unique(self):
        code = 'def f(xs,custom):\n """Return the input numbers sorted."""\n return [x for x in custom.keys() if x in xs]'
        h = self.hit(code, "py.presence-frequency-confusion")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)

    def test_optimum_early_return_outranks_correct_index_lookup(self):
        code = 'def f(xs):\n """Return the smallest even item and first index."""\n m=min(xs)\n if m%2==0:return [m,xs.index(m)]\n for i,x in enumerate(xs):\n  if x%2==0:return [x,i]\n return []'
        r = self.packet(code)["results"]
        self.assertEqual(r[0]["concept"]["id"], "py.first-match-vs-optimum")
        self.assertEqual(r[0]["evidence"][0]["line"], 6)
        self.assertNotIn("py.first-occurrence-position", {h["concept"]["id"] for h in r})

    def test_sorted_early_return_is_not_false_optimum_fault(self):
        code = 'def f(xs):\n """Return the smallest even element."""\n for x in sorted(xs):\n  if x%2==0:return x\n return None'
        self.assertIsNone(self.hit(code, "py.first-match-vs-optimum"))

    def test_global_min_inside_loop_is_not_first_qualifying_item(self):
        code = 'def f(xs):\n """Return the smallest element."""\n for x in xs:\n  return min(xs)\n return None'
        self.assertIsNone(self.hit(code, "py.first-match-vs-optimum"))

    def test_coefficient_value_role_not_sequence_allocation(self):
        code = 'def f(xs):\n """Return polynomial derivative coefficients."""\n out=[0]*(len(xs)-1)\n out[-1]=xs[-1]*len(xs)\n return out'
        h = self.hit(code, "py.index-origin-domain")
        self.assertIsNotNone(h)
        self.assertEqual(h["evidence"][0]["line"], 4)

    def test_ternary_direction_comparison_is_not_omitted(self):
        code = 'def f(xs):\n """Check monotonically increasing or decreasing input."""\n direction=1 if xs[0]<xs[1] else -1\n return direction'
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertIsNotNone(h)
        self.assertEqual(h["evidence"][0]["line"], 3)

    def test_empty_sum_identity_does_not_fill_top_slot(self):
        code = 'def f(xs: list):\n """Return the sum of entries."""\n if len(xs)==0:return 0\n return sum(xs)'
        self.assertIsNone(self.hit(code, "py.empty-singleton-shortcut"))

    def test_empty_balanced_sequence_rejection_is_supported(self):
        code = 'def f(s:str):\n """Check whether brackets are balanced."""\n if not s:return False\n return True'
        h = self.hit(code, "py.empty-singleton-shortcut")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_nonempty_contract_does_not_reject_its_own_guard(self):
        code = 'def f(xs:list):\n """Return sum for a non-empty list."""\n if len(xs)==0:raise ValueError()\n return sum(xs)'
        self.assertIsNone(self.hit(code, "py.empty-singleton-shortcut"))

    def test_plain_singleton_reduction_vs_transformed_reduction(self):
        benign = 'def f(xs:list):\n """Return minimum sum of any non-empty subarray."""\n if len(xs)==1:return xs[0]\n return 0'
        self.assertIsNone(self.hit(benign, "py.empty-singleton-shortcut"))
        bad = benign.replace("minimum sum of any non-empty subarray", "sum of squared entries")
        self.assertIsNotNone(self.hit(bad, "py.empty-singleton-shortcut"))

    def test_source_flow_crosses_comprehension_outer_binding(self):
        a = Analysis("def f(s):\n data=s.encode()\n return [x for x in data]")
        effects = [x["effect"] for chain in a.output_origins().values() for x in chain]
        self.assertIn("text_to_bytes", effects)

    def test_conditional_definition_remains_unknown_inside_comprehension(self):
        a = Analysis("def f(s,flag):\n data=s\n if flag:data=s.encode()\n return [x for x in data]")
        effects = [x["effect"] for chain in a.output_origins().values() for x in chain]
        self.assertNotIn("text_to_bytes", effects)

    def test_unstated_rejection_bound_is_visible(self):
        code = 'def f(year):\n """Validate a year integer."""\n if year<1980:return False\n return True'
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_stated_rejection_bound_is_not_contradicted(self):
        code = 'def f(year):\n """Validate a year integer, requires year >= 1980."""\n if year<1980:return False\n return True'
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)

    def test_literal_none_check_does_not_treat_unknown_return_as_none(self):
        code = 'def f(xs:list):\n """Return None for empty input."""\n if len(xs)==0:return xs[0]\n return 0'
        self.assertIsNotNone(self.hit(code, "py.empty-singleton-shortcut"))

    def test_semantic_tier_and_source_survive_renaming(self):
        for fn, var in [("compute", "items"), ("arbitrary", "zxy")]:
            code = f'def {fn}({var}):\n """Return smallest even element."""\n for x in {var}:\n  if x%2==0:return x\n return None'
            h = self.hit(code, "py.first-match-vs-optimum")
            self.assertIsNotNone(h)
            self.assertEqual(h["evidence"][0]["line"], 4)

    def test_unknown_candidate_is_not_a_confirmed_bug(self):
        r = self.packet("def f(xs):\n return xs[0]")["results"]
        self.assertTrue(all(h["status"] == "unverified_fault_hypothesis" for h in r))

    def test_whole_sum_does_not_replace_prefix_balance(self):
        code = 'def f(xs:list):\n """Return True if at any point the balance is below zero."""\n balance=sum(xs)\n return balance<0'
        h = self.hit(code, "py.quantifier-scope")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_internal_balance_is_not_rejected_input_count(self):
        code = 'def f(xs:list):\n """Check account balance at any point."""\n balance=sum(xs)\n if balance<0:return True\n return False'
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] >= 2)

    def test_zero_remainder_is_not_signed_modulo_bug(self):
        code = 'def f(n):\n """Count digits of integers divisible by 7."""\n return n%7==0'
        self.assertIsNone(self.hit(code, "py.signed-modulo-domain"))

    def test_placeholder_does_not_exclude_valid_zero_items(self):
        code = 'def f(xs:list,d):\n """Insert d between every two input elements."""\n xs.insert(0,0)\n out=[]\n for x in xs:\n  if x!=0:out.append(x)\n return out'
        # The relation is implemented for indexed sequence filters, not arbitrary
        # value loops: this unsupported spelling must not become a false proof.
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)
        code = 'def f(xs:list,d):\n """Insert d between every two input elements."""\n xs.insert(0,0)\n out=[]\n for i in range(len(xs)):\n  if xs[i]!=0:out.append(xs[i])\n return out'
        h = self.hit(code, "py.branch-boundary-contract")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_count_list_items_is_not_total_character_count(self):
        code = 'def f(words):\n """Return total chars of a list of strings."""\n return len(set(words))'
        h = self.hit(code, "py.aggregation-scope")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)
        correct = code.replace("len(set(words))", "sum(len(w) for w in words)")
        h = self.hit(correct, "py.aggregation-scope")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)

    def test_value_equal_to_last_character_is_not_current_position(self):
        code = 'def f(s):\n """Count letters a only at the end."""\n count=0\n for c in s:\n  if c==s[-1]:count+=1\n return count'
        h = self.hit(code, "py.first-occurrence-position")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_rightward_optimum_scan_is_not_first_match_fault(self):
        code = 'def f(s):\n """Find the closest vowel from the right side."""\n for i in range(len(s)-1,-1,-1):\n  if s[i] in "aeiou":return s[i]\n return ""'
        self.assertIsNone(self.hit(code, "py.first-match-vs-optimum"))

    def test_vowel_table_respects_uppercase_positive_example(self):
        code = 'def f(s):\n """Return the closest vowel.\n f("FULL") ==> "U"\n """\n for c in s:\n  if c in "aeiou":return c\n return ""'
        h = self.hit(code, "py.literal-classification-domain")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_uppercase_only_class_does_not_make_lowering_benign(self):
        code = 'def f(s):\n """Count uppercase vowels."""\n return sum(1 for c in s if c.lower() in "AEIOU")'
        self.assertIsNotNone(self.hit(code, "py.text-normalization-contract"))

    def test_filter_bucket_may_be_empty(self):
        code = 'def f(xs):\n """Return smallest positive integer or None if no positive exists."""\n positive=[]\n for x in xs:\n  if x>0:positive.append(x)\n return min(positive)'
        h = self.hit(code, "py.empty-reduction-domain")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)
        guarded = code.replace(
            " return min(positive)", " if not positive:return None\n return min(positive)"
        )
        self.assertIsNone(self.hit(guarded, "py.empty-reduction-domain"))

    def test_nonempty_literal_bucket_is_not_empty_risk(self):
        code = 'def f():\n """Return the minimum value."""\n values=[1,2]\n return min(values)'
        h = self.hit(code, "py.empty-reduction-domain")
        self.assertFalse(h and h["ranking"]["semantic_support"]["tier"] == 3)

    def test_int_square_root_loop_bound_is_intentional(self):
        code = 'def f(n):\n """Return whether n is prime."""\n for i in range(2,int(n**0.5)+1):\n  if n%i==0:return False\n return True'
        self.assertIsNone(self.hit(code, "py.numeric-cast-loss"))

    def test_variable_stride_two_origin_is_not_necessarily_even(self):
        code = 'def f(a,b):\n """Return the even digits between positive integers a and b."""\n return [x for x in range(a,b+1,2)]'
        h = self.hit(code, "py.index-origin-domain")
        self.assertIsNotNone(h)
        self.assertEqual(h["ranking"]["semantic_support"]["tier"], 3)

    def test_case_transform_does_not_authorize_space_deletion(self):
        code = 'def f(s):\n """Flip case of the input string."""\n s=s.replace(" ","")\n return s.swapcase()'
        self.assertIsNotNone(self.hit(code, "py.text-normalization-contract"))

    def test_regex_literals_have_no_accidental_control_characters(self):
        for path in Path(__file__).parent.glob("*.py"):
            self.assertFalse(
                any(ord(c) < 32 and c not in "\n\t\r" for c in path.read_text()), str(path)
            )

    def test_policy_is_explicit(self):
        with self.assertRaises(ValueError):
            self.packet("x=0", policy="invalid")


if __name__ == "__main__":
    unittest.main()
