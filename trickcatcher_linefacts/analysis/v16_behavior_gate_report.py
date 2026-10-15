"""Summarize frozen v16 proposal gate and actual request ledger; never calls a model."""
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
PIPE=REPO/'trickcatcher_linefacts/pipelines/v16_behavior_ready'
ROOT=PIPE/'out/humaneval/behavior_smoke'
OUT=Path(__file__).with_name('v16_behavior_gate_results')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    gate=json.loads((ROOT/'concept_gate.json').read_text())
    protocol=json.loads((ROOT/'protocol.json').read_text())
    for name,expected in protocol['sources'].items():
        if digest(PIPE/name)!=expected:raise ValueError('Frozen source changed: '+name)
    ids=protocol['config']['task_ids'];rows=gate['rows']
    if len(rows)!=len(ids) or {r['task'] for r in rows}!=set(ids):raise ValueError('incomplete proposal cohort')
    ledger=[json.loads(s) for s in (ROOT/'model_cache/calls.jsonl').read_text().splitlines()]
    successes=[r for r in ledger if not r.get('cache_hit') and not r.get('error')]
    from trickcatcher_linefacts.pipelines.v16_behavior_ready import semantic,behavior_experiment
    behavior_experiment.verify()
    unknown_ops=collections.Counter()
    for response in (ROOT/'proposals').glob('*/*_response.json'):
        raw=json.loads(response.read_text())['text']
        for op in re.findall(r'"op"\s*:\s*"([^"\n]+)"',raw):
            if op not in semantic.ARITIES:unknown_ops[op]+=1
    by_task=[];reasons=collections.Counter()
    for r in rows:
        counts=collections.Counter(x['reason'] for x in r['rejections']);reasons.update(counts)
        by_task.append(dict(task=r['task'],obligations=len(r['obligations']),checked_cards=len(r['cards']),
                            shown=len(r['shown']),qualified=r['qualified'],rejections=dict(counts),
                            input_tokens=r['input_tokens'],output_tokens=r['output_tokens']))
    gen=ROOT/'generation/gen.jsonl';report=ROOT/'report.json'
    result=dict(version='v16_behavior_ready',scope='20-task design dev proposal smoke; not efficacy evaluation',
                representation=json.loads((ROOT/'representation_gate.json').read_text())['usable'],
                gate=dict(qualified=gate['qualified'],denominator=gate['tasks'],required=gate['required'],passed=gate['passed']),
                totals=dict(obligations=sum(r['obligations'] for r in by_task),cards=sum(r['checked_cards'] for r in by_task),shown=sum(r['shown'] for r in by_task)),
                costs=dict(logical_proposal_requests=gate['proposal_calls'],successful_new_requests=len(successes),
                           unique_success_keys=len({r['key'] for r in successes}),cache_hits=sum(bool(r.get('cache_hit')) for r in ledger),
                           failed_attempts=sum(bool(r.get('error')) for r in ledger),
                           actual_input_tokens=sum(r.get('n_in',0) for r in successes),
                           actual_output_tokens=sum(r.get('n_out',0) for r in successes),
                           request_seconds_sum=sum(r.get('seconds',0) for r in successes)),
                rejection_counts=dict(reasons),unknown_operator_mentions=dict(unknown_ops),rows=by_task,
                generation_rows=sum(bool(x) for x in gen.read_text().splitlines()) if gen.exists() else 0,
                scored=report.exists(),D_IO=None if not report.exists() else 'see native report',
                provenance=dict(gate_sha256=digest(ROOT/'concept_gate.json'),protocol_sha256=digest(ROOT/'protocol.json'),
                                import_resume='analysis/resume_v16_frozen.py preloads behavior/tracer on main thread',frozen_sources_verified=True))
    if not gate['passed'] and result['generation_rows']:raise ValueError('unexpected generation after failed gate')
    OUT.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# v16_behavior_ready — proposal gate','',result['scope'],'',
           f"Representation gate {result['representation']}/20; concept gate **{gate['qualified']}/{gate['tasks']}**, required {gate['required']}: **{'passed' if gate['passed'] else 'failed'}**.",
           '',f"Accepted obligations: {result['totals']['obligations']}; checked cards: {result['totals']['cards']}; shown: {result['totals']['shown']}.",
           f"Generation rows: {result['generation_rows']}; scored: {result['scored']}. D_IO is unmeasured when no score exists.",
           '', '| Task | Obligations | Checked cards | Shown | Rejections |','|---|---:|---:|---:|---|']
    lines += [f"| {r['task']} | {r['obligations']} | {r['checked_cards']} | {r['shown']} | {json.dumps(r['rejections'])} |" for r in by_task]
    lines+=['','Actual request ledger: '+json.dumps(result['costs'])+'.','',
            'Rejection counts: '+json.dumps(result['rejection_counts'])+'.','',
            'Unsupported operator mentions in raw response text (occurrences, not card counts): '+json.dumps(result['unknown_operator_mentions'])+'.','',
            'First attempt stopped when binding prompt construction lazily imported tracer in a thread; SIGALRM registration needs the main thread. Three exact spec responses were cached. The external resume preloaded behavior/tracer on main thread, verified original source hashes and reused exact caches. No pipeline source, prompts, validators, seeds or budgets changed.',
            '',
            'A gate failure measures proposal/mechanism feasibility, not whether semantic concepts improve detection. No canonical/reference scores feed this proposal stage. Schema/quotation/binding/predicate rejections need a separately registered future revision; do not relax this run or start generation to obtain a result.','']
    OUT.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps({k:result[k] for k in ('gate','totals','costs','generation_rows','scored')},indent=2))
if __name__=='__main__':main()
