"""Concept discovery and revision use the same small response contract."""
import json

INSTRUCTION = '''Discover testing CONCEPTS that help construct inputs for the supplied uncovered C1/C2 targets.
Return ONLY one JSON object with keys concepts and inputs; no expected outputs or assertions.
concepts (up to 6): [{id,target_id,name,input_relation,instruction,evidence_lines,predicate,strategies}].
Use EXACT target_id from targets. A concept is a meaningful input scenario, not just a line number:
explain the parameter relationship or operation behavior, the construction recipe, and the earlier
guards needed to reach it. Use source assignments and static def-use; a structural path is only an
approximation, never proof. Keep semantic claims as hypotheses; never infer an oracle from PUT output.
Examples of concept families: cardinality after dedup, first/later occurrence, equality after aggregation,
later loop update, alternative after an early return. Derive the actual binding from this source.
evidence_lines is a nonempty integer list of ORIGINAL source lines supporting the concept.
predicate is an optional safe boolean expression over INPUT PARAMETERS, or "" if not representable.
Every predicate clause must depend on an actual parameter: sum([1,2]) == 3 is a constant example,
not a predicate about xs. If a relation such as sum of positive xs cannot be expressed with the
allowed helpers, use predicate="" and retain the concept/instruction for native target checking.
Allowed expressions: comparisons, and/or/not, +/-, indexing, len/sum/min/max/abs, distinct_count(sequence).
No local branch variables, attributes, imports, comprehensions, arbitrary calls or executable code.
strategies is {} or an object keyed by EVERY signature parameter; descriptors reuse Hypothesis:
{kind:int,min:integer,max:integer}, {kind:bool}, {kind:sampled,values:[JSON values]},
{kind:str,min_size:integer,max_size:integer,alphabet:string},
{kind:list,elements:descriptor,min_size:integer,max_size:integer}.
Dependent bounds may refer to an earlier parameter, e.g. max:"len(xs)". Keep search sizes <=30.
Finite values/search limits are exploration budgets, never new spec/domain constraints.
Use sampled values for correlated constructions that independent descriptors cannot express.
inputs: [{arguments:{EXACT parameter name: JSON value},concept_id:string_or_null}], up to input_budget.
Do not repeat base inputs. Inputs must satisfy the trusted contract. Keep direct input attempts even
when an abstraction is uncertain. In a feedback round revise concepts/strategies based on target hit,
domain failures or runtime status. Unknown or a timeout does not mean unreachable. All unmet targets,
including currently unsupported scenarios, remain eligible; never claim coverage from your own labels.'''


def messages(task, contract, programs, analyses, targets, input_budget, feedback=None):
    payload = {'specification': task['prompt'], 'trusted_contract': contract,
               'parameter_names_from_signature': None, 'input_budget': input_budget,
               'programs': programs, 'analysis': analyses, 'targets': targets,
               'feedback': feedback}
    from ..call_builder import CallBuilder
    payload['parameter_names_from_signature'] = list(CallBuilder.for_source(task['prompt'], task['entry_point']).signature.parameters)
    return [{'role': 'system', 'content': INSTRUCTION},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
