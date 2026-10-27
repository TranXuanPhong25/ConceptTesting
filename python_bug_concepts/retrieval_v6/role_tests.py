import ast
import tempfile
import unittest
from pathlib import Path
from .engine import search
from .facts import Analysis


class RoleAndSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "index.sqlite3"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def result(self, code, policy="precise"):
        return search(code=code, top_k=3, policy=policy, db=self.db)

    def candidates(self, code):
        return {h["concept"]["id"] for h in self.result(code)["results"]}

    def test_weak_candidate_goes_to_review_instead_of_primary(self):
        r = self.result("def f(xs):\n return xs[0]")
        self.assertEqual(r["results"], [])
        self.assertTrue(r["abstained"])
        self.assertTrue(
            any(x["concept_id"] == "py.index-out-of-bounds" for x in r["review_candidates"])
        )

    def test_balanced_fallback_is_explicit(self):
        self.assertTrue(self.result("def f(xs):\n return xs[0]", policy="balanced")["results"])

    def test_encoding_for_digest_is_not_character_count_loss(self):
        code = 'def f(s:str):\n """Return md5 hash string."""\n import hashlib\n return hashlib.md5(s.encode()).hexdigest()'
        self.assertNotIn("py.unicode-text-byte-domain", self.candidates(code))

    def test_byte_count_still_exposes_character_domain_mismatch(self):
        code = 'def f(s:str):\n """Count distinct characters."""\n return len(set(s.encode()))'
        self.assertIn("py.unicode-text-byte-domain", self.candidates(code))

    def test_set_length_does_not_observe_order(self):
        code = 'def f(xs):\n """Return how many unique items, sorted order is irrelevant."""\n return len(set(xs))'
        self.assertNotIn("py.set-order-loss", self.candidates(code))

    def test_lambda_without_captured_loop_symbol_is_not_late_binding(self):
        code = 'def f(xs):\n out=[]\n for x in xs:\n  out.append(list(filter(lambda c:c=="a",str(x))))\n return out'
        self.assertNotIn("py.late-bound-closure", self.candidates(code))

    def test_captured_comprehension_lambda_retains_correct_source(self):
        code = "def f(xs):\n return [lambda:x for x in xs]"
        r = self.result(code)
        h = next(h for h in r["results"] if h["concept"]["id"] == "py.late-bound-closure")
        self.assertEqual(h["evidence"][0]["line"], 2)
        self.assertIn(h["instantiated"]["where"]["fact_id"], {x["id"] for x in r["facts"]["facts"]})

    def test_captured_lambda_not_confused_with_shadowed_argument(self):
        code = "def f(xs):\n return [lambda x:x for x in xs]"
        self.assertNotIn("py.late-bound-closure", self.candidates(code))

    def test_immediate_lambda_does_not_escape_iteration(self):
        code = "def f(xs):\n return [(lambda:x)() for x in xs]"
        self.assertNotIn("py.late-bound-closure", self.candidates(code))

    def test_shortcircuit_on_boolean_state_returns_boolean(self):
        code = "def f(xs):\n inc,dec=True,True\n for x in xs:\n  if x>0:inc=False\n  if x<0:dec=False\n return inc or dec"
        self.assertNotIn("py.shortcircuit-boolean-result", self.candidates(code))

    def test_nonboolean_shortcircuit_is_not_excluded(self):
        self.assertIn(
            "py.shortcircuit-boolean-result",
            self.candidates('def f(a,b):\n """Return a boolean."""\n return a or b'),
        )

    def test_tuple_definitions_preserve_numeric_positions(self):
        code = 'def f(a,b):\n """Order planet labels by their orbit proximity."""\n planets=["Mars","Earth"]\n i,j=planets.index(a),planets.index(b)\n if i>j:i,j=j,i\n return i,j'
        self.assertNotIn("py.lexicographic-numeric-order", self.candidates(code))

    def test_conditional_definition_is_known_within_same_branch(self):
        a = Analysis(
            "def f(s,flag):\n if flag:\n  data=s.encode()\n  return [x for x in data]\n return []"
        )
        effects = [r["effect"] for chain in a.output_origins().values() for r in chain]
        self.assertIn("text_to_bytes", effects)

    def test_definition_is_unknown_after_branch_join(self):
        a = Analysis("def f(s,flag):\n if flag:data=s.encode()\n return data")
        effects = [r["effect"] for chain in a.output_origins().values() for r in chain]
        self.assertNotIn("text_to_bytes", effects)

    def test_shadowed_builtin_annotation_does_not_prove_sequence(self):
        code = "class list:pass\ndef f(xs:list):\n if not xs:return 0\n return xs[0]"
        a = Analysis(code)
        sub = next(n for n in a.nodes if isinstance(n, ast.Subscript))
        self.assertIsNone(a.sequence_domain("xs", sub))

    def test_output_nonempty_clause_is_not_input_precondition(self):
        code = 'def f(xs:list):\n """Return all non-empty subsets of the input list."""\n if len(xs)==0:return None\n return []'
        r = self.result(code, policy="coverage")
        self.assertFalse(
            any(
                c["kind"] == "public_nonempty_domain"
                for e in r["excluded_bindings"]
                for c in e["applicability"]["contradictions"]
            )
        )

    def test_correct_sign_parity_is_not_fixed_sign_shortcut(self):
        code = 'def f(xs):\n """Return sum of magnitudes times product of all signs."""\n if all(x<0 for x in xs):return (-1)**len(xs)*sum(-x for x in xs)\n return 0'
        self.assertFalse(
            any(
                h["concept"]["id"] == "py.branch-boundary-contract"
                and h["ranking"]["semantic_support"]["tier"] == 3
                for h in self.result(code, policy="coverage")["results"]
            )
        )

    def test_fixed_sign_negative_sum_does_ignore_parity(self):
        code = 'def f(xs):\n """Return sum of magnitudes times product of all signs."""\n if all(x<0 for x in xs):return -sum(xs)\n return 0'
        self.assertIn("py.branch-boundary-contract", self.candidates(code))

    def test_ordinary_input_bound_is_not_an_output_bound(self):
        code = 'def f(x:float):\n """Given input smaller than 1, return 1."""\n if x==0:return 1\n return 1'
        self.assertFalse(
            any(
                h["concept"]["id"] == "py.branch-boundary-contract"
                and h["ranking"]["semantic_support"]["tier"] == 3
                for h in self.result(code, policy="coverage")["results"]
            )
        )

    def test_round_half_policy_has_positive_and_correct_control(self):
        bad = (
            'def f(x):\n """Return nearest integer, round ties away from zero."""\n return round(x)'
        )
        self.assertIn("py.rounding-policy", self.candidates(bad))
        good = 'def f(x):\n """Return nearest integer, round ties away from zero."""\n if x%1!=0.5:return round(x)\n return int(x+1) if x>0 else int(x-1)'
        self.assertNotIn("py.rounding-policy", self.candidates(good))

    def test_integer_cast_inside_loop_body_is_not_loop_bound(self):
        code = 'def f(xs):\n """Increment each element by one."""\n while xs:\n  return [int(x+1) for x in xs]\n return []'
        self.assertIn("py.numeric-cast-loss", self.candidates(code))

    def test_nested_helper_uses_enclosing_purpose_but_not_input_type(self):
        a = Analysis(
            'def f(xs:list):\n """Return nearest integer, ties away from zero."""\n def helper(v):\n  return round(v)\n return helper(xs[0])'
        )
        call = next(n for n in a.nodes if isinstance(n, ast.Call) and a.api(n) == "round")
        self.assertIn("away from zero", a.spec(call))
        self.assertIsNone(a.sequence_domain("v", call))

    def test_helper_does_not_borrow_unrelated_function_contract(self):
        a = Analysis(
            'def f(s):\n """Count characters."""\n return len(s)\ndef g(v):\n return round(v)'
        )
        call = next(n for n in a.nodes if isinstance(n, ast.Call) and a.api(n) == "round")
        self.assertEqual(a.spec(call), "")

    def test_declared_sentence_delimiters_can_be_normalized(self):
        code = 'def f(s):\n """Count sentences delimited by ? or ."""\n return len(s.replace("?",".").split("."))'
        self.assertNotIn("py.text-normalization-contract", self.candidates(code))

    def test_module_fragments_do_not_require_a_function_wrapper(self):
        cases = [
            '"""Test palindromic input."""\nresult=xs[0]==xs[-1]',
            '"""Count tokens delimited by ? or ."""\nresult=s.replace("?",".").split(".")',
        ]
        for code in cases:
            r = self.result(code, policy="coverage")
            self.assertIsNone(r["warning"])
            self.assertIsNotNone(r["facts"])

    def test_supplemental_compound_decision_fact_is_exported(self):
        code = 'def f(freq):\n """Select greatest integer whose frequency is at least its value."""\n for i in range(len(freq)-1,0,-1):\n  if freq[i]>=i and freq[i]>freq[i-1]:return i\n return -1'
        r = self.result(code)
        known = {f["id"] for f in r["facts"]["facts"]}
        for h in r["results"]:
            self.assertIn(h["instantiated"]["where"]["fact_id"], known)

    def test_float_infinity_is_identity_not_precision_loss(self):
        self.assertNotIn("py.numeric-cast-loss", self.candidates('def f():\n return float("INF")'))


if __name__ == "__main__":
    unittest.main()
