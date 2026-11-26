"""Concept discovery and revision use the same small response contract."""
import json

INSTRUCTION = '''Discover testing CONCEPTS that help construct inputs for the supplied uncovered C1/C2 targets.
Return ONLY one JSON object with keys concepts and inputs; no expected outputs or assertions.
concepts (up to 6): [{id,target_id,name,input_relation,instruction,evidence_lines,predicate,strategies}].
Use EXACT target_id from targets. A concept is a meaningful input scenario, not just a line number:
explain the parameter relationship or operation behavior, the construction recipe, and the earlier
guards needed to reach it. Keep semantic claims as hypotheses; never infer an oracle from PUT output.
When the target suggests a plausible implementation mistake, prefer a valid input
that would expose an observable difference between that mistake and the specified behavior.
In instruction, name the suspected mistake and the observable behavior to check.

C1 means executing the target line. C2 means taking the exact target edge from one line to the next.

Consider this illustrative example.
    value = x - 1
    if increase:
        value = x + 1
    if square:
        return value * value
    return value
For C1 at `return value * value` or C2 into that branch, choose `square=True`. To also exercise the
earlier `value = x - 1` branch reaching that return, choose `increase=False` to skip the reassignment.
Use the actual PUT's parameters and source lines. A structural path is a hypothesis to check in the trace.

In an illustrative workshop booking example, the spec marks a session full when its seat count
after group approval reaches capacity. When approve_group is true, the PUT computes
booked_seats = confirmed_seats + group_size. Its guard tests confirmed_seats >= capacity
using the count before approval. For the false edge, use confirmed_seats=7, group_size=3,
approve_group=True, capacity=10. The original count of 7 is below capacity and the updated
count of 10 reaches it. In instruction, write "The guard may use the count from before
approval. Check the returned booking status when a newly approved group fills the session."

When a target involves a threshold, keep the earlier guards satisfied. Work backward from
how the guarded quantity is computed to choose arguments that put it just below, exactly at,
and just above the threshold when the trusted contract admits those cases. If the guard may
read a stale value, use the updated quantity required by the spec. In the workshop example,
hold confirmed_seats=7, approve_group=True, and capacity=10. Group sizes 2 and 3 give
9 and 10 booked seats. Both take the PUT's false edge while crossing the specified cutoff.
Try group_size=4 only if the contract admits over-capacity requests.

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
Dependent bounds may refer to an earlier parameter, e.g. max:"len(xs)".
Keep string lengths and list sizes at most 100.
Finite values/search limits are exploration budgets, never new spec/domain constraints.
Use sampled values for correlated constructions that independent descriptors cannot express.
inputs: [{arguments:{EXACT parameter name: JSON value},concept_id:string_or_null}], up to input_budget.
For each concept where you propose tool sampling, first try to solve the target relation and
earlier guards yourself. When you find a concrete valid input, return it in inputs with its
concept_id in the same response as the predicate and strategies. Keep the tool metadata even
when you can construct an input yourself. For example, for a + b == 1000, return a=250 and b=750
if the guards allow it, alongside the predicate and bounded strategies for exploring the relation.
Do not repeat base inputs. Inputs must satisfy the trusted contract. Keep direct input attempts even
when an abstraction is uncertain. In a feedback round revise concepts/strategies based on target hit,
domain failures or runtime status. Unknown or a timeout does not mean unreachable. All unmet targets,
including currently unsupported scenarios, remain eligible; never claim coverage from your own labels.'''


def messages(
    task,
    contract,
    programs,
    analyses,
    targets,
    input_budget,
    feedback=None,
    *,
    prior_stage_inputs=None,
    prior_stage_summary=None,
    max_prompt_prior_inputs=12,
    instruction=INSTRUCTION,
):
    payload = {'specification': task['prompt'], 'trusted_contract': contract,
               'parameter_names_from_signature': None, 'input_budget': input_budget,
               'programs': programs, 'analysis': analyses, 'targets': targets,
               'feedback': feedback}
    from ..call_builder import CallBuilder
    payload['parameter_names_from_signature'] = list(CallBuilder.for_source(task['prompt'], task['entry_point']).signature.parameters)
    if prior_stage_inputs is not None:
        summary = prior_stage_summary
        shown = prior_stage_inputs
        if len(prior_stage_inputs) > max_prompt_prior_inputs:
            from .tool_inputs import compact_prompt_prior_inputs
            shown, auto_summary = compact_prompt_prior_inputs(prior_stage_inputs, limit=max_prompt_prior_inputs)
            summary = summary or auto_summary
        has_prior = bool(shown) or (summary is None or summary.get('total_prior_inputs', 0) > 0)
        if has_prior:
            payload['prior_stage_inputs'] = shown
            if summary is not None:
                payload['prior_stage_summary'] = summary
            instruction += ('\nThe prior_stage_inputs extend the base suite. Use their source stages and '
                            'technique labels as context, and the supplied residual targets as measured evidence. '
                            'Do not repeat the prior calls or infer expected outputs from them.')
    return [{'role': 'system', 'content': instruction},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
