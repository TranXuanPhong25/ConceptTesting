"""Post-freeze read-only scoring/transport verification; no model calls or repairs."""
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[2])]
import runner
from client import costs, inspect_events, read, MODEL


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protocol=runner.verify();root=runner.ROOT;results={};threads=[];evidence={}
    for version in runner.VERSIONS:
        path=root/version;status=read(path/'luna_status.json')
        assert status['state'] in ('complete','incomplete'), 'still_running'
        report=read(path/'report.json') if (path/'report.json').exists() else None
        m=runner.module(version)
        if version=='v23' and (path/'generation_frozen.json').exists():m.verify_generation(path)
        elif version=='v24' and (path/'generation_frozen.json').exists():
            m.verify_snapshot(path,'preparation_frozen.json');m.verify_snapshot(path,'generation_frozen.json')
        elif version=='v25' and (path/'run_frozen.json').exists():m.verify_snapshot(path)
        attempts=[];stage_stats={};cached=reasoning=cache_write=0;reported_cache=reported_reasoning=0
        latencies=[];responses=[];request_provenance=[]
        for p in sorted((path/'transport/calls').glob('*/attempts.json')):
            rows=read(p);assert len(rows)==1;record=rows[0];attempts.append(record)
            request=read(p.parent/'request.json')
            assert request==read(path/'requests'/(p.parent.name+'.json'))
            event=inspect_events((p.parent/'stdout.jsonl').read_text(errors='replace'))
            threads.extend(e['thread_id'] for e in event['events'] if e['type']=='thread.started' and 'thread_id'in e)
            use=record.get('usage') or {}
            if type(use.get('cached_input_tokens')) is int:cached+=use['cached_input_tokens'];reported_cache+=1
            if type(use.get('reasoning_output_tokens')) is int:reasoning+=use['reasoning_output_tokens'];reported_reasoning+=1
            if type(use.get('cache_write_input_tokens')) is int:cache_write+=use['cache_write_input_tokens']
            latencies.append(record.get('seconds',0))
            artpath=path/'artifacts'/(p.parent.name+'.json')
            if artpath.exists():
                art=read(artpath);assert art['request_hash']==m.digest(request)
                stage_stats.setdefault(request['stage'],Counter())[art.get('reason',art['state'])]+=1
            else:art=None
            if record['state']=='received':
                assert event['completed_turns']==1 and not event['forbidden_items'] and not event['invalid_lines']
                assert 'codex_core::tools::router' not in (p.parent/'stderr.txt').read_text(errors='replace')
                raw=read(p.parent/'response.json')
                assert raw['origin']=='codex_cli_gpt-5.6-luna_low_host_disabled' and raw['model']==MODEL
                assert raw['tool_schemas_exposed'] and raw['execution_host_disabled'] and raw['tool_executions']==0
                assert art and art['response']==raw
                assert raw['text']==(p.parent/'last.txt').read_text()
                assert raw['raw_CLI_usage']==event['usage']==record['usage']
                responses.append({'slot':request['slot'],'request_hash':m.digest(request),
                    'state':art['state'],'reason':art.get('reason'),'origin':raw['origin'],
                    'raw_text':raw['text'],'raw_CLI_usage':raw['raw_CLI_usage']})
            request_provenance.append({'slot':request['slot'],'attempt_state':record['state'],
                                       'usage_known':record.get('usage_known',False),
                                       'request_hash':m.digest(request),'response_received':record['state']=='received'})
        assert len(attempts)<=runner.VERSIONS[version][1]
        cs=costs(path/'transport')
        cs.update(cached_input_tokens_reported=cached,cached_token_reporting_attempts=reported_cache,
                  reasoning_output_tokens_reported=reasoning,reasoning_reporting_attempts=reported_reasoning,
                  cache_write_input_tokens_reported=cache_write,
                  CLI_seconds_sum=sum(latencies),wall_seconds=(dt.datetime.fromisoformat(status['finished_at'])-dt.datetime.fromisoformat(status['started_at'])).total_seconds())
        common={'f02','f04','f06','f13','f14'}
        if report:
            report_rows=report.get('rows',[])
            overlap=[x for x in report_rows if x['case'] in common]
        else:overlap=[]
        workers={}
        for group in ('executions','native_executions','predicate_executions'):
            reservations=[read(p) for p in (path/group).rglob('attempt.json')]
            data=[read(p) for p in (path/group).rglob('result.json')]
            workers[group]={'recorded_launches':sum(x.get('launched') is True for x in reservations),
                            'reserved_attempts':len(reservations), 'unresolved_launches':sum(x.get('launched') is None for x in reservations),
                            'failed_workers':sum(x.get('state')=='failed' for x in reservations),
                            'reported_PUT_calls':sum(x.get('put_calls',0) for x in data),
                            'reported_predicate_evaluations':sum(x.get('evaluations_attempted',0) for x in data),
                            'scope':'durable ledger only; v23 legacy execution has no such ledger, not zero actual work'}
        results[version]={'case_denominator':protocol['versions'][version]['case_count'],
                          'status':status,'native_report':report,'adapter_costs_authoritative':cs,
                          'stage_stats':stage_stats,'overlapping5_native_rows':overlap,
                          'worker_costs_recorded':workers,'requests':request_provenance,'raw_model_responses':responses}
        for p in path.rglob('*'):
            if p.is_file() and p.suffix in ('.json','.jsonl','.txt'):
                evidence[str(p.relative_to(root))]=sha(p)
    assert len(threads)==len(set(threads)), 'context_reused'
    prior=read(root/'protocol_v3.json')
    for name,wanted in prior['suite_sources'].items():
        assert sha(root/'configuration_epochs/epoch3_sources'/name)==wanted
    canary=read(root/'readiness_v4.json')
    assert canary['exposure_gate_passed'] is False and canary['actual_canary_model_turns']==1
    canary_record=read(root/'canary_v3/transport/calls/tools_availability/attempts.json')[0]
    assert canary_record['usage_known'] and canary_record['usage']['input_tokens']==13565
    config_rejections=[]
    for directory,key in [('canary','tools.disable_defaults'),('canary_v2','tools.view_image')]:
        p=root/directory/'transport/calls/tools_availability'
        r=read(p/'attempts.json')[0]
        assert not r['started'] and r['completed_turns']==0 and ('unknown configuration field `'+key+'`')in(p/'stderr.txt').read_text()
        config_rejections.append({'namespace':directory,'CLI_invocations':1,'actual_model_turns':0,'reason':'unsupported_configuration_'+key})
    result={'scope':'same seen native16/9/5 diagnostics, requestedLuna low, different CLI harness; no causal equal-budget superiority',
            'model_requested':MODEL,'server_identity':'not independently reported; explicit mismatches rejected',
            'model_task_CLI_invocations':sum(v['adapter_costs_authoritative']['CLI_invocations'] for v in results.values()),
            'fresh_task_thread_ids':len(threads),'readiness':canary,'configuration_only_rejections':config_rejections,
            'canary_raw_usage':canary_record['usage'],'results':results,
            'sampling_role_limits':'flattened role content and Codex base instructions; Qwen numeric seed/temp/output budgets not enforced',
            'schema_exposure_gate_failed':True,'target_model_execution_host_disabled':True,
            'historical_Qwen_and_Luna_outputs_unmodified_unpooled':True,'no_output_repairs':True,
            'advance_to_benchmark':False,'advance_to_new_comparison':False,'analysis_time_evidence_hashes':evidence}
    output=HERE/'results.json'
    if output.exists():assert read(output)==result
    else:output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({v:{'status':r['status']['state'],'costs':r['adapter_costs_authoritative'],
                        'totals':r['native_report'].get('totals') if r['native_report'] else None,
                        'gates':r['native_report'].get('gates') if r['native_report'] else None,
                        'stages':r['stage_stats']} for v,r in results.items()},indent=2))


if __name__=='__main__':main()
