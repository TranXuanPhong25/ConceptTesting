"""Single-author review of a fixed 20-row sample, with native examples."""
import hashlib,json,math
from pathlib import Path
from ..client import atomic
from ..grade_utility import equal
from ...retrieval_v2.grade_witnesses import isolated
HERE=Path(__file__).resolve().parent
# grade; where/how/what; proposed example; diagnostic alternative; reviewer reasoning
REVIEWS=[
 (3,[1,1,1],[[-5,-2]],None,'Fixed zero sentinel suppresses valid negative rolling maxima.'),
 (3,[1,1,1],['C',['a','b']],None,'Strength -1 never replaces sentinel -1, leaving an empty extension.'),
 (2,[0,0,0],[[4,2,6,7]],[[4,2,6]],'Length-derived parity is a real fault on odd-length lists. Cited even-length example returns 2 correctly, not 7. Strictly cited while condition is not the faulty initialization; causal parity statement is reversed.'),
 (3,[1,1,1],[[1.5]],None,'int truncates a valid fractional increment; official contract only requires list.'),
 (3,[1,1,1],[[1.0]],None,'Singleton valid under official contract, yet the guard raises instead of returning zero MAD.'),
 (2,[1,1,0],[[2,1,2]],[[2,1,1]],'First-occurrence index is the actual fault. Supplied identical expected/actual example is not diagnostic; alternative creates IndexError.'),
 (1,[0,0,0],[5,0],None,'Supplied input violates positive-integer contract and also returns 5 correctly. Else swaps arguments to (0,5); no claimed infinite recursion.'),
 (1,[0,0,0],[7],None,'Excluding n as its own trial divisor is correct. The real invalid-prime result at n<=0 is unrelated to the range stop.'),
 (1,[0,0,1],[-120],None,'Counterexample identifies zero loss, but numeric branch boundary is correct. The fault is int conversion after reversal, not negative/nonnegative partition.'),
 (2,[1,1,0],[[1,2,1]],[[2,1,1]],'Position/value-domain mismatch is real. Example has both copies at even indices and does not fail, contrary to the claim.'),
 (0,[0,0,0],[[3,3]],None,'Strict update leaves equal maxima unchanged correctly. Response explicitly admits no fault.'),
 (3,[1,1,1],[[-5,-2]],None,'Zero sentinel returns zero rather than maximum of a negative list.'),
 (3,[1,1,1],['Hello.'],None,'Trailing period creates an empty words list, indexed without a guard.'),
 (0,[0,0,0],[['abc'],''],None,'Every string starts with the empty prefix, so shortcut matches reference.'),
 (3,[1,1,1],[[10],5],None,'Singleton early return bypasses the weight constraint.'),
 (3,[1,1,1],['AaB'],None,'Lowercasing merges A and a, turning a case-distinct happy triple into a repeated triple.'),
 (1,[0,0,0],['1.5'],None,'Binary halves such as 1.5 are exactly representable; the proposed precision failure is unsupported and reference uses the same float half comparison.'),
 (3,[1,1,1],['FULL'],None,'Lowercase-only vowel table misses the explicit uppercase-vowel example.'),
 (0,[0,0,0],[[1,3,5]],None,'All-odd path returns [] correctly; no empty reduction or alleged odd-value return.'),
 (2,[1,0,0],['bc'],['b'],'Index-versus-alphabet domain is real, but explanation says actual iteration index is required, which is wrong. bc returns 1 correctly; b exposes the actual domain mismatch.'),
]

def wilson(successes,n):
    z=1.96;p=successes/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d
    width=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [center-width,center+width]

def main():
    plan=json.loads((HERE/'MANUAL_SAMPLE_PLAN.json').read_text())
    packet=json.loads((HERE/'MANUAL_REVIEW_PACKET.json').read_text())
    refs={r['task_id']:{k:r[k] for k in ['entry_point','prompt','canonical_solution','contract','atol']} for r in map(json.loads,(Path.home()/'.cache/evalplus/HumanEvalPlus-v0.1.10.jsonl').read_text().splitlines())}
    results=[]
    for row,review in zip(packet,REVIEWS,strict=True):
        grade,binding,args,alternative,reason=review
        ref=refs[row['task_id']];code=ref['prompt']+ref['canonical_solution']
        def replay(args):
            job={'entry':ref['entry_point'],'args':args}
            validity=isolated({**job,'source':code,'contract':ref['contract'],'mode':'validity'})
            expected=isolated({**job,'source':code,'mode':'value'})
            actual=isolated({**job,'source':row['source'],'mode':'value'})
            differs=expected.get('status')=='ok' and (actual.get('status')=='error' or actual.get('status')=='ok' and not equal(expected['value'],actual['value'],ref['atol']))
            return {'args':args,'validity':validity,'reference':expected,'put':actual,'confirmed_bug_input':validity.get('value') is True and differs}
        results.append({**{k:v for k,v in row.items() if k not in ['source','reference']},'manual_grade':grade,'manual_binding':dict(zip(['where','how','what'],binding)),'reason':reason,'proposed_example':replay(args),'alternative_diagnostic':replay(alternative) if alternative is not None else None})
    good=sum(r['manual_grade']>=2 for r in results)
    complete=sum(all(r['manual_binding'].values()) for r in results)
    summary={'population':167,'sample':len(results),'actual_bug_concepts':good,'actual_bug_concept_rate':good/len(results),'nominal_wilson_95_interval':wilson(good,len(results)),'all_where_how_what_correct':complete,'binding_complete_rate':complete/len(results),'where_correct':sum(r['manual_binding']['where'] for r in results),'how_correct':sum(r['manual_binding']['how'] for r in results),'what_correct':sum(r['manual_binding']['what'] for r in results)}
    atomic(HERE/'MANUAL_SAMPLE_REVIEW.json',{'summary':summary,'limits':['Post-hoc deterministic sample, not an independent new experiment.','Same project author; manual causal grades remain subjective. Native replay confirms validity/outcomes, not causal attribution.','Sample can include multiple concepts per task; nominal row-level interval ignores task clustering and finite-population correction.','Strict binding: an explicitly incorrect concrete example fails what even if the broader family is correct.'],'plan_sha256':hashlib.sha256((HERE/'MANUAL_SAMPLE_PLAN.json').read_bytes()).hexdigest(),'hidden_tests_used':False,'results':results})
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
