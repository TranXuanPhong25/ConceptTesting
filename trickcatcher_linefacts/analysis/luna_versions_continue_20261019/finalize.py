"""Verify the resumed trajectory and score only native frozen complete outputs."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('resume',HERE/'continue.py');resume=importlib.util.module_from_spec(spec);spec.loader.exec_module(resume)
from client import costs,inspect_events,read


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def ledger_usage(folder):
    result=costs(folder);cache=reason=0;cache_reports=reason_reports=0
    for path in Path(folder).glob('calls/*/attempts.json'):
        rows=read(path);assert len(rows)==1
        usage=rows[0].get('usage')or{}
        if type(usage.get('cached_input_tokens')) is int:cache+=usage['cached_input_tokens'];cache_reports+=1
        if type(usage.get('reasoning_output_tokens')) is int:reason+=usage['reasoning_output_tokens'];reason_reports+=1
    return dict(result,cached_input_tokens_reported=cache,cached_reporting_records=cache_reports,
                reasoning_output_tokens_reported=reason,reasoning_reporting_records=reason_reports)


def worker_counts(root):
    result={}
    for name in ('native_executions','predicate_executions','cpu_native','cpu_predicates','cpu_evaluator_only'):
        group=root/name;attempts=[read(p)for p in group.rglob('attempt.json')];data=[read(p)for p in group.rglob('result.json')]
        result[name]={'reserved_attempts':len(attempts),'recorded_launches':sum(x.get('launched')is True for x in attempts),
                      'unresolved_launches':sum(x.get('launched')is None for x in attempts),
                      'failed_workers':sum(x.get('state')=='failed' for x in attempts),
                      'reported_PUT_calls':sum(x.get('put_calls',0)for x in data),
                      'reported_predicate_evaluations':sum(x.get('evaluations_attempted',0)for x in data)}
    legacy=list((root/'executions').glob('*/*_result.json'))
    result['v23_legacy']={'worker_results':len(legacy),'result_states':dict(Counter(read(p).get('status')for p in legacy)),
                          'launches_and_exact_PUT_calls':None,'reason':'legacy results have no durable launch/put_calls counter; not zero work'}
    return result


def main():
    protocol=resume.verify();summaries={};all_threads=[];hashes={};raw=[]
    for version in ('v23','v24','v25'):
        root=resume.ROOT/version if version!='v25' else resume.old.ROOT/'v25'
        module=resume.old.module(version);status=read(root/'luna_status.json')
        assert status['state']=='complete', 'incomplete_or_running_'+version
        if version!='v25':
            assert all(sha(root/k)==v for k,v in protocol['versions'][version]['imported_inventory'].items()),'imported_bytes_changed'
        if version=='v23':module.verify_generation(root)
        elif version=='v24':
            module.verify_snapshot(root,'preparation_frozen.json');module.verify_snapshot(root,'generation_frozen.json')
        else:module.verify_snapshot(root)
        report=read(root/'report.json');base=ledger_usage(resume.old.ROOT/version/'transport')
        fresh=ledger_usage(root/'continuation_transport') if version!='v25' else None
        attempts=base['CLI_invocations']+(fresh['CLI_invocations']if fresh else 0)
        received=base['received']+(fresh['received']if fresh else 0)
        unknown=base['unknown_usage_attempts']+(fresh['unknown_usage_attempts']if fresh else 0)
        total={'CLI_invocations':attempts,'received':received,'unknown_usage_attempts':unknown,
               'input_tokens_known':base['input_tokens_known']+(fresh['input_tokens_known']if fresh else 0),
               'output_tokens_known':base['output_tokens_known']+(fresh['output_tokens_known']if fresh else 0),
               'cached_input_tokens_reported':base['cached_input_tokens_reported']+(fresh['cached_input_tokens_reported']if fresh else 0),
               'reasoning_output_tokens_reported':base['reasoning_output_tokens_reported']+(fresh['reasoning_output_tokens_reported']if fresh else 0),
               'native_cost_report_authority':('v25 completed original probe; namespace cost consistent' if version=='v25'
                   else 'not total: imported old transport only in resumed native report')}
        if fresh:assert fresh['CLI_invocations']<=protocol['versions'][version]['new_call_cap']
        stages={};requests=list((root/'requests').glob('*.json'));imported=fresh_count=0
        for path in sorted(requests):
            req=read(path);slot=req['slot'];old=resume.old.ROOT/version/'transport/calls'/slot
            new=root/'continuation_transport/calls'/slot
            old_response=old/'response.json';new_response=new/'response.json'
            assert not(old_response.exists()and new_response.exists()),'accepted_response_regenerated'
            transport=new if new_response.exists()else old
            response=read(transport/'response.json');record=read(transport/'attempts.json')[0];artifact=read(root/'artifacts'/path.name)
            assert read(transport/'request.json')==req
            assert artifact['request_hash']==module.digest(req)and artifact['response']==response
            assert record['state']=='received'and record['usage_known']and not record.get('denied_router_attempt',False)
            events=inspect_events((transport/'stdout.jsonl').read_text())
            assert not events['forbidden_items']and not events['invalid_lines']and events['completed_turns']==1
            assert 'codex_core::tools::router'not in(transport/'stderr.txt').read_text()
            assert response['raw_CLI_usage']==events['usage']and response['text']==(transport/'last.txt').read_text()
            assert response['origin']=='codex_cli_gpt-5.6-luna_low_host_disabled'
            assert response['execution_host_disabled']and response['tool_schemas_exposed']and response['tool_executions']==0
            all_threads += [e['thread_id']for e in events['events']if e['type']=='thread.started']
            imported+=transport==old;fresh_count+=transport==new
            stages.setdefault(req['stage'],Counter())[artifact.get('reason',artifact['state'])]+=1
            raw.append({'version':version,'slot':slot,'epoch':'continuation'if transport==new else'initial',
                        'request_hash':module.digest(req),'state':artifact['state'],'reason':artifact.get('reason'),
                        'origin':response['origin'],'raw_text':response['text'],'raw_usage':response['raw_CLI_usage']})
        assert len(requests)==received==imported+fresh_count
        native_rows=report['rows'];overlap=[r for r in native_rows if r['case']in{'f02','f04','f06','f13','f14'}]
        summaries[version]={'case_denominator':16 if version=='v23' else 9 if version=='v24' else 5,
                            'status':status,'native_report':report,'authoritative_cumulative_costs':total,
                            'epoch1_costs':base,'continuation_costs':fresh,'imported_responses_reused':imported,
                            'fresh_responses':fresh_count,'stage_stats':stages,'overlapping5_rows':overlap,
                            'recorded_workers':worker_counts(root)}
        for p in sorted(root.rglob('*')):
            if p.is_file()and p.suffix in('.json','.jsonl','.txt'):
                hashes[version+'/'+str(p.relative_to(root))]=sha(p)
    assert len(all_threads)==len(set(all_threads)),'target_context_reused'
    known_in=sum(x['authoritative_cumulative_costs']['input_tokens_known']for x in summaries.values())
    known_out=sum(x['authoritative_cumulative_costs']['output_tokens_known']for x in summaries.values())
    result={'scope':'one native paused diagnostic trajectory, same requestedLuna low; no matched sampling/harness causal comparison',
            'model_requested':'gpt-5.6-luna','effort':'low','server_model_identity':'not independently reported',
            'continuation_protocol_sha256':sha(resume.ROOT/'resume_protocol.json'),
            'initial_suite_protocol_v4_sha256':sha(resume.old.ROOT/'protocol_v4.json'),
            'imported_bytes_reverified_after_completion':True,
            'results':summaries,'raw_model_responses':raw,'fresh_unique_target_threads':len(all_threads),
            'cumulative_target_CLI_invocations':sum(x['authoritative_cumulative_costs']['CLI_invocations']for x in summaries.values()),
            'cumulative_received_target_responses':len(raw),
            'cumulative_known_target_input_tokens':known_in,'cumulative_known_target_output_tokens':known_out,
            'cumulative_unknown_usage_target_attempts':sum(x['authoritative_cumulative_costs']['unknown_usage_attempts']for x in summaries.values()),
            'canary_separate':read(resume.old.ROOT/'readiness_v4.json'),
            'old_failed_attempts_and_all_originals_preserved':True,'accepted_responses_not_regenerated':True,
            'model_tool_schemas_exposed':True,'execution_host_disabled':True,'recorded_target_tool_attempts':0,
            'v25_rejected_predicates_not_executed_repaired_or_rescored':True,
            'v23_new_input_baseline':'public bases only','v24_v25_novelty_baseline':'ENTIRE frozen24+base pool',
            'no_automatic_wider_comparison_benchmark_or_v25_repair':True,'analysis_time_evidence_hashes':hashes}
    out=HERE/'results.json'
    if out.exists():assert read(out)==result
    else:out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({v:{'costs':r['authoritative_cumulative_costs'],'totals':r['native_report'].get('totals'),
                        'gates':r['native_report'].get('gates'),'stages':r['stage_stats']}for v,r in summaries.items()},indent=2))


if __name__=='__main__':main()
