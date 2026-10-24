"""Read-only saved-data packet projection; no model/evaluator/native execution."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
V40=REPO/'trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021/prepared'
V43=REPO/'trickcatcher_linefacts/out/pipelines/v43_concept_identify/humaneval/binding8/prepared'
EPISODES=['E2','E3','E4','E6','E7','E8']
CONCEPT='''General concept vocabulary (not a per-task binding or oracle):
1. Occurrence conservation: distinguish an item value from each occurrence. Bind the required output content and multiplicity policy from the spec. Compare absence, one occurrence and repeated occurrences; ordering is a separate obligation.
2. Membership inclusion: identify which collection supplies required values and which must contain them. Distinguish inclusion from equality and set membership from multiplicity. Vary extras or missing required members while holding the other role fixed.
3. Quantified decision: identify the predicate and whether all, any or another quantifier is required. Consider no witnesses, one witness and mixed witnesses/counterexamples. Bind empty-domain behavior from the spec.
4. Eligible contribution: identify eligibility, each occurrence's weight, aggregation and any final comparison. Separate eligibility boundaries, repeated contributions and irrelevant elements; do not assume cardinality is the aggregate.
5. Order policy: identify the ordering relation, direction and any stated tie policy. Separate ordering from content conservation. Vary permutation or ties only when their meaning is specified.
6. Eligible selection: bind both eligibility and selection/rank rule, then any empty-case policy. First and minimum need not coincide; unspecified eligibility remains unspecified rather than being learned from code.
7. Defined outcome: distinguish normal values, declared sentinels, specified exceptions and unresolved execution. Bind allowed outcomes to the declared domain, including degenerate cases when specified.
Use only applicable concepts. Agreement with code does not validate a requirement; sampled agreement is not a universal proof.'''
GENERIC='''General reasoning checklist (not a per-task answer or oracle):
1. Read the complete specification before deciding what the implementation should do. Identify the function's arguments, stated input domain and required result. Distinguish explicit statements from assumptions that would need additional information.
2. Read the implementation in execution order. Explain the returned expression and how intermediate computations can affect it. Avoid inferring an output change merely because an operation appears somewhere in the code.
3. Inspect each recorded execution carefully. Keep the input, return value and exception category distinct. A recorded implementation output is evidence about that implementation, not automatically a required result.
4. Reassess the initial hypothesis as a fallible suggestion. Keep claims that are still supported, narrow overly broad claims and withdraw contradicted claims. A later observation may concern only part of the initial explanation.
5. Connect the final reasoning to specific specification clauses, source expressions or observation identifiers. Explain which facts support your conclusion and which questions remain unresolved. Avoid adding facts absent from the packet.
6. Propose small, valid inputs whose predicted observations would distinguish the competing explanations you describe. Explain what each test would resolve. If the supplied observations already decide the issue, identify that evidence rather than claim a new execution.
7. Keep the final judgment consistent with the reasoning. Distinguish demonstrated mismatch, no supported mismatch and missing specification information. Respect uncertainty without discarding clear evidence.
Use this checklist where helpful. Agreement with code does not validate a requirement; sampled agreement is not a universal proof.'''
INSTRUCTION='''Solve this one task using only the packet below. Do not use any tools, filesystem, execution, network, or other agents. Do not inspect the repository. Treat the initial hypothesis and reasoning guide as fallible. Return one final answer, preferably a JSON object, at most450words: requirement; implementation_hypothesis; initial_hypothesis_decision (keep/revise/withdraw/unknown) and reason; judgment (mismatch/no_mismatch/unknown) and reason; evidence IDs; up to2 inputs as full positional Python tuple literals, each naming two competing behavior predictions and its purpose. Predictions are hypothetical, not trusted expected values/assertions. Do not claim to have executed inputs. Unknown/abstention is allowed when justified.'''
def write(path,value):
 data=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
 if path.exists(): assert path.read_text()==data,'immutable packet drift'
 else: path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
def main():
 manifest={'requested_model':'gpt-6.1-sol','reasoning_override':None,'sources':{},'packets':{},'mapping':{}}
 for i,ep in enumerate(EPISODES,1):
  old=json.loads((V40/f'{ep}.json').read_text()); pool=json.loads((V43/f'{ep}.json').read_text())
  public=old['public']
  task={'task':f'T{i}','spec':public['spec'],'code':public['code'],'base_tests':public['base_tests'],'initial_hypothesis':public['initial_hypothesis'],'observations':pool['rows'],'evidence_ids':['original_spec','source_return']+[r['id'] for r in pool['rows']]}
  manifest['mapping'][f'T{i}']=ep
  for source in [V40/f'{ep}.json',V43/f'{ep}.json']:
   manifest['sources'][str(source.relative_to(REPO))]=hashlib.sha256(source.read_bytes()).hexdigest()
  for arm,guide in [('generic',GENERIC),('concept',CONCEPT)]:
   packet={'instruction':INSTRUCTION,'task_packet':task,'reasoning_guide':guide}
   path=ROOT/'packets'/f'T{i}_{arm}.json';write(path,packet)
   manifest['packets'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
 manifest['guide_words']={'generic':len(GENERIC.split()),'concept':len(CONCEPT.split())}
 write(ROOT/'manifest.json',manifest)
if __name__=='__main__':main()
