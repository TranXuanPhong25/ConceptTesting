"""Registered metadata-only context envelopes; never issue a completion or PUT call."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v43_concept_identify import identify as app


class MetadataClient(app.Client):
    def request(self, method, path, payload=None, raw_folder=None):
        if path=='/chat/completions':
            raise RuntimeError('readiness_cannot_generate')
        if path=='/models':
            raw_folder=self.root/'models_response'
        return super().request(method,path,payload,raw_folder)


def messages(packet):
    return [{'role':'system','content':'Return exactly one JSON object. No external tools. Bind concepts from spec; observed behavior is not normative truth.'},
            {'role':'user','content':json.dumps(packet,ensure_ascii=False)}]


def envelope(row):
    ids=['B_readiness_0001','B_readiness_0002','B_readiness_0003']
    proposal={'bindings':[{'id':bid,'concept':'eligible_contribution','relation':'sum_distinct_gt_one',
                          'arguments':row['parameters'][:2],'spec_quote':'界'*300} for bid in ids],
              'tools':app.TOOLS}
    table={'columns':['observation','binding','status','candidate_value','candidate_exception','holds_on_observation','reason'],
           'rows':[[obs['id'],bid,'computed','9'*64,'ValueError',False,'binding_arguments_or_observation_unsupported']
                   for obs in row['rows'] for bid in ids]}
    measurement={'length':999999,'distinct':999999,'sum':-999999,'positive':999999,'ones':999999,'max_multiplicity':999999}
    feedback={'notice':'READINESS ONLY: synthetic size envelope, not actual tool facts or candidates.',
              'candidate_relations_on_observations':table,
              'contrasts':{'scope':'4 small observed pairs, prefer one changed argument; possibly multiple dimensions changed',
                           'pairs':[{'rows':[row['rows'][0]['id'],row['rows'][-1]['id']],
                                     'changed_candidates':ids,'only_changed_argument':1,
                                     'measurements':[[measurement,measurement],[measurement,measurement]],'cost':999999}
                                    for _ in range(4)],'found':999999,'no_pair_means':'none in this finite pool, not infeasibility'},
              'return_dependencies':{'scope':'partial return-expression/top-level-assignment read inventory; omits guards, aliases, side effects and nested scopes; NOT sound dataflow or causality proof',
                                     'return_reads':[['hypothetical_variable_name'*2]*5],
                                     'top_level_assignments_read':{'hypothetical_assignment_name':['hypothetical_variable_name']*5},
                                     'transitive_names':['hypothetical_variable_name']*5,
                                     'unreferenced_top_level_targets':['hypothetical_assignment_name']*2,
                                     'control_or_nested_scope_present':True},
              'input_pool_hash':app.digest(row['rows'])}
    return proposal,feedback


def main():
    folder=app.ROOT/'readiness'
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (folder/'status.json').exists():
            raise SystemExit('readiness_already_consumed_no_retry')
        app.verify();app.quota()
        status={'state':'running','started_utc':datetime.now(timezone.utc).isoformat(),
                'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'freeze_sha256':hashlib.sha256((app.ROOT/'freeze.json').read_bytes()).hexdigest(),
                'task_completion_calls':0,'PUT_calls':0,'sizes':[],
                'scope':'hypothetical envelope estimate; not a universal Unicode upper bound; actual-call tokenizer guard authoritative'}
        app.write_json(folder/'status.json',status)
        client=None
        try:
            client=MetadataClient(folder/'transport')
            for path in sorted((app.ROOT/'prepared').glob('*.json')):
                row=app.read(path);proposal,feedback=envelope(row);app.quota()
                packets={'initial':app.initial_packet(row),
                         'raw':app.final_packet(row,proposal,feedback,'raw'),
                         'tool':app.final_packet(row,proposal,feedback,'tool')}
                for phase,packet in packets.items():
                    request=messages(packet)
                    app.immutable(folder/'requests'/f"{row['episode']}__{phase}.json",request)
                    count=client.token_count(request)
                    status['sizes'].append({'episode':row['episode'],'phase':phase,'input_tokens':count})
                    app.write_json(folder/'status.json',status)
                    if count>6144:
                        raise app.TransportStop('readiness_input_cap')
            app.verify();status['state']='ready'
        except Exception as exc:
            status.update(state='stopped',error_type=type(exc).__name__,
                          reason=str(exc) if isinstance(exc,app.TransportStop) else 'readiness_controller_failure')
        finally:
            if client:client.close()
            status['ended_utc']=datetime.now(timezone.utc).isoformat()
            app.write_json(folder/'status.json',status)
            print(json.dumps({'state':status['state'],'reason':status.get('reason'),
                              'tokenizations':len(status['sizes']),
                              'maximum_tokens':max((x['input_tokens'] for x in status['sizes']),default=None)}),flush=True)


if __name__=='__main__':
    main()
