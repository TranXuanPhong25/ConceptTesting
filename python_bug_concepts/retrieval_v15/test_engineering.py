import ast
import unittest
from .instances import extract
from .retriever import bind,query_text
import json
from pathlib import Path


class ConceptTests(unittest.TestCase):
    def kinds(self,src):return {r['kind'] for r in extract(src)['instances']}

    def test_correct_filter_has_concept_without_fault(self):
        p=extract('def f(xs):\n return [v for v in xs if v > 0]')
        r=next(r for r in p['instances'] if r['kind']=='selective_filter')
        self.assertEqual(r['slots']['predicate']['evidence']['expression'],'v > 0')
        self.assertEqual(r['bug_verdict'],'not_inferred')
        self.assertEqual(p['requirement']['status'],'unknown')

    def test_transform_flows_to_filter_through_alias(self):
        src='def f(s: str):\n t=s.replace(" ", "")\n return "".join(c for c in t if c not in "aeiou")'
        p=extract(src);r=next(r for r in p['instances'] if r['kind']=='selective_filter')
        self.assertEqual(r['relations'][0]['predicate'],'feeds_selection_source')
        self.assertEqual(len(r['source_chain']),1)

    def test_alias_search_to_index_and_direct_are_distinct(self):
        p=extract('def f(s: str, q):\n i=s.find(q)\n j=i\n return s[j]')
        r=next(r for r in p['instances'] if r['kind']=='search_position_indexing')
        self.assertEqual(r['slots']['position']['evidence']['expression'],'j')
        self.assertEqual(r['relations'][0]['predicate'],'position_flows_to_index')
        self.assertNotIn('search_position_indexing',self.kinds('def f(s, i):\n return s[i]'))

    def test_shadowed_builtin_is_not_deduplication(self):
        self.assertNotIn('deduplication',self.kinds('def f(set, xs):\n return set(xs)'))
        self.assertIn('deduplication',self.kinds('def f(xs):\n return set(xs)'))

    def test_branch_rebinding_does_not_invent_search_flow(self):
        src='def f(s: str,q,b):\n i=s.find(q)\n if b:\n  i=0\n return s[i]'
        p=extract(src)
        self.assertNotIn('search_position_indexing',{r['kind'] for r in p['instances']})
        self.assertTrue(p['unknown'])

    def test_unsupported_method_receiver_is_explicit_unknown(self):
        p=extract('def f(x,q):\n return x.find(q)')
        self.assertFalse(p['instances']);self.assertTrue(p['unknown'])

    def test_effectful_predicate_does_not_claim_identity_preservation(self):
        p=extract('def f(xs):\n return [x for x in xs if mutate(x)]')
        self.assertFalse(p['instances']);self.assertTrue(p['unknown'])

    def test_spec_negation_is_not_positive_requirement(self):
        p=extract('def f(xs):\n """Do not preserve order."""\n return set(xs)')
        self.assertEqual(p['requirement']['status'],'unknown')
        p=extract('def f(xs):\n """Keep duplicates."""\n return list(xs)')
        self.assertEqual(p['requirement']['cues'][0]['value'],'preserved')

    def test_parameter_renaming_does_not_change_normalized_query(self):
        a='def f(xs):\n return [v for v in xs if v > 0]'
        b='def renamed(values):\n return [item for item in values if item > 0]'
        self.assertEqual(query_text(a,extract(a),'relations'),query_text(b,extract(b),'relations'))

    def test_evidence_spans_match_original_source(self):
        source='def f(s: str, needle):\n index=s.find(needle)\n return s[index]'
        p=extract(source);spans={tuple([n.lineno,n.col_offset,n.end_lineno,n.end_col_offset]):ast.get_source_segment(source,n) for n in ast.walk(ast.parse(source)) if hasattr(n,'lineno')}
        for r in p['instances']:
            for slot in r['slots'].values():
                e=slot['evidence'];self.assertEqual(spans[tuple(e['span'])],e['expression'])

    def test_partition_binding_does_not_set_observed_or_expected_value(self):
        p=extract('def f(xs):\n return set(xs)');r=p['instances'][0]
        template=next(t for t in json.loads(Path(__file__).with_name('templates.json').read_text()) if t['kind']=='deduplication')
        b=bind(template,r)
        self.assertTrue(b['partitions']);self.assertTrue(all(x['realized'] is None for x in b['partitions']))
        self.assertEqual(b['bug_verdict'],'not_inferred')

    def test_multiple_functions_require_explicit_entry(self):
        with self.assertRaises(ValueError):extract('def a(): return 1\ndef b(): return 2')

    def test_public_type_enables_self_assignment_composition(self):
        src='def clean(text):\n """clean is a function that takes string and returns string without vowels."""\n text=text.replace(" ", "")\n return [c for c in text if c not in "aeiou"]'
        p=extract(src);r=next(x for x in p['instances'] if x['kind']=='transform_then_filter')
        self.assertEqual(r['slots']['input_source']['evidence']['expression'],'text')
        self.assertTrue(any(e.get('rule')=='explicit_public_parameter_type' for e in r['domain_evidence']['input_source']['evidence']))
        self.assertEqual(r['relations'][0]['predicate'],'transform_flows_to_filter')

    def test_type_doc_negation_and_wrong_parameter_do_not_bind(self):
        for doc in ['x is not a string.', ':type y: str', 'f may take string and returns string.', 'Do not assume x (str): text']:
            p=extract('def f(x):\n '+repr(doc)+'\n return x.replace("a","b")')
            self.assertFalse(p['instances'])

    def test_non_name_binding_invalidates_parameter_domain(self):
        for body in ['def s(): pass','class s: pass','try:\n  pass\n except Exception as s:\n  pass',
                     'match value:\n  case s:\n   pass']:
            p=extract('def f(s: str,value):\n '+body+'\n return s.find("x")')
            self.assertNotIn('position_lookup',{r['kind'] for r in p['instances']})

    def test_rhs_walrus_does_not_reuse_old_search_position(self):
        p=extract('def f(s: str,q):\n i=s.find(q)\n x=((i := 0),s[i])\n return x')
        self.assertNotIn('search_position_indexing',{r['kind'] for r in p['instances']})
        p=extract('def f(s: str):\n s=((s := []), s.find("x"))\n return s')
        self.assertNotIn('position_lookup',{r['kind'] for r in p['instances']})

    def test_conflicting_annotation_and_type_doc_abstains(self):
        for annotation in ['list','dict','int','Unknown']:
            p=extract('def f(x: '+annotation+'):\n """:type x: str"""\n return x.replace("a","b")')
            self.assertFalse(p['instances'])

    def test_query_term_truncation_and_unused_direct_query(self):
        from .retriever import search
        source='def f(x):\n # '+' '.join('word'+str(i) for i in range(150))+'\n return x'
        raw=search(source,arm='raw');direct=search(source,arm='direct')
        self.assertGreater(raw['omitted_query_terms'],0)
        self.assertEqual(raw['omitted_query_characters'],0)
        self.assertFalse(direct['query_used_for_ranking'])
        self.assertEqual(direct['omitted_query_terms'],0)

    def test_constructor_slice_and_string_result_domains(self):
        src='def f(x,q):\n s=str(x).lower()\n t=s[1:]\n i=t.find(q)\n return t[i]'
        p=extract(src)
        self.assertIn('search_position_indexing',{r['kind'] for r in p['instances']})
        self.assertTrue(all(r['domain_evidence'] for r in p['instances']))

    def test_shadowed_constructor_does_not_infer_domain(self):
        p=extract('def f(str,x,q):\n s=str(x)\n return s.find(q)')
        self.assertFalse(p['instances'])

    def test_unpacked_search_arguments_have_no_element_binding(self):
        p=extract('def f(s: str,args):\n i=s.find(*args)\n return s[i]')
        self.assertNotIn('position_lookup',{r['kind'] for r in p['instances']})
        self.assertNotIn('search_position_indexing',{r['kind'] for r in p['instances']})
        self.assertIn('unpacked_search_arguments',{u['reason'] for u in p['unknown']})

    def test_generic_sequence_annotation_supports_index(self):
        p=extract('from typing import List\ndef f(xs: List[int],i):\n return xs[i]')
        self.assertEqual([x['kind'] for x in p['instances']],['direct_indexing'])

    def test_composite_requires_stable_source(self):
        p=extract('def f(s: str,b):\n t=s.replace("a", "")\n if b:\n  t=[]\n return [c for c in t if c != "x"]')
        self.assertNotIn('transform_then_filter',{r['kind'] for r in p['instances']})

    def test_distinct_count_is_inline_not_mutated_alias(self):
        self.assertIn('distinct_cardinality',self.kinds('def f(xs):\n return len(set(xs))'))
        self.assertNotIn('distinct_cardinality',self.kinds('def f(xs):\n s=set(xs)\n s.add(42)\n return len(s)'))

    def test_direct_control_caps_candidates_and_prefers_composite(self):
        from .retriever import search
        p=search('def f(xs):\n return len(set(xs))',arm='direct')
        self.assertLessEqual(len(p['candidates']),3)
        self.assertEqual(p['candidates'][0]['template_id'],'concept.distinct_cardinality')
        self.assertTrue(all(x['bm25_score'] is None for x in p['candidates']))

    def test_loop_carried_index_abstains(self):
        p=extract('def f(s: str,q):\n p=s.find(q)\n for k in range(2):\n  value=s[p]\n  p=0\n return value')
        self.assertNotIn('search_position_indexing',{r['kind'] for r in p['instances']})
        self.assertTrue(p['unknown'])

    def test_exception_group_definition_is_not_dominating(self):
        p=extract('def f(s: str):\n p=0\n try:\n  fail()\n except* ValueError:\n  p=s.find("x")\n return s[p]')
        self.assertNotIn('search_position_indexing',{r['kind'] for r in p['instances']})
        self.assertTrue(p['unknown'])

    def test_comprehension_shadow_does_not_inherit_parameter_type(self):
        p=extract('def f(s: str,q):\n return [s.find(q) for s in [1,2]]')
        self.assertNotIn('position_lookup',{r['kind'] for r in p['instances']})
        self.assertTrue(p['unknown'])

    def test_subscript_write_is_not_read(self):
        self.assertFalse(extract('def f(a: list,i):\n a[i]=0')['instances'])

    def test_unknown_mapping_domain_is_not_sequence_indexing(self):
        p=extract('def f(d,k):\n return d[k]')
        self.assertFalse(p['instances']);self.assertTrue(p['unknown'])

    def test_replace_requires_string_domain(self):
        for src in ['def f(x):\n return x.replace("a","b")','def f():\n return [].replace("a","b")']:
            p=extract(src);self.assertFalse(p['instances']);self.assertTrue(p['unknown'])

    def test_counter_mapping_is_not_occurrence_counting(self):
        for arg in ["{'a': -2}", 'xs']:
            p=extract('from collections import Counter\ndef f(xs):\n return Counter('+arg+')')
            self.assertFalse(p['instances']);self.assertTrue(p['unknown'])
        self.assertIn('frequency_aggregation',self.kinds('from collections import Counter\ndef f(xs: list):\n return Counter(xs)'))

    def test_relation_labels_check_endpoints_and_evidence(self):
        from .diagnostic import relation_labels
        import copy
        p=extract('def f(s: str,q):\n i=s.find(q)\n return s[i]')
        r=next(x for x in p['instances'] if x['kind']=='search_position_indexing')
        expected=[dict(subject_kind='position_lookup',subject_expression='s.find(q)',
                       predicate='position_flows_to_index',object_kind='search_position_indexing',
                       object_expression='s[i]',evidence=['s.find(q)','i','s[i]'])]
        self.assertEqual(relation_labels(r['relations'],p['instances']),expected)
        wrong=copy.deepcopy(r['relations']);wrong[0]['subject']=r['id']
        self.assertNotEqual(relation_labels(wrong,p['instances']),expected)
        wrong=copy.deepcopy(r['relations']);wrong[0]['evidence']=[]
        self.assertNotEqual(relation_labels(wrong,p['instances']),expected)


if __name__=='__main__':unittest.main()
