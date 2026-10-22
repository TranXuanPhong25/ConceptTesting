"""Saved-ledger/mechanical analysis only; no tool re-evaluation, model or PUT calls."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v43_concept_identify import identify as app


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    app.verify();root=app.ROOT
    assert app.read(root/'status.json')['state']=='complete'
    inventory=app.read(root/'terminal_inventory.json')
    assert inventory=={str(p.relative_to(root)):sha(p) for p in root.rglob('*')
                       if p.is_file() and p.name!='terminal_inventory.json'}
    for name,expected in app.read(root/'generation_frozen.json').items():
        assert sha(root/name)==expected
    rows=[];slots=Counter();mechanical=Counter();tool_counts=Counter();matrix_counts=Counter()
    for i in range(1,9):
        episode=f'E{i}';prepared=app.read(root/'prepared'/f'{episode}.json')
        initial=app.read(root/'artifacts'/f'{episode}__initial.json')
        raw=app.strict_json(initial['raw']['text'])  # Read rejected RAW, never repair or execute it.
        bindings=[]
        for binding in raw.get('bindings',[]):
            relation=binding.get('relation')
            checks={'concept_in_vocabulary':binding.get('concept') in app.t.CONCEPTS,
                    'relation_in_vocabulary':relation in app.t.RELATIONS,
                    'argument_names_known':all(x in prepared['parameters'] for x in binding.get('arguments',[])),
                    'arity_matches':relation=='unknown' or len(binding.get('arguments',[]))==app.t.arity(relation),
                    'quote_exact_nonempty':bool(binding.get('spec_quote')) and binding.get('spec_quote') in prepared['spec'],
                    'concept_relation_compatible':binding.get('concept') in app.t.RELATION_CONCEPTS.get(relation,[])}
            for key,value in checks.items():mechanical[key+'_true' if value else key+'_false']+=1
            bindings.append({'raw':binding,'mechanical_checks_only':checks,
                             'semantic_validity':'independent manual review, not inferred from these flags'})
        row={'episode':episode,'pool_rows':len(prepared['rows']),
             'initial_state':initial['state'],'initial_error':initial.get('error_code'),
             'initial_error_path':initial.get('schema_path'),'raw_bindings':bindings,
             'raw_requested_tools':raw.get('tools',[]),'finals':{}}
        slots['initial_'+initial['state']]+=1
        if initial['state']=='valid':
            result=app.read(root/'tool_results'/f'{episode}.json')
            row['actual_tool_result_path']=str((root/'tool_results'/f'{episode}.json').relative_to(REPO))
            for name in raw['tools']:tool_counts[name]+=1
            table=result.get('candidate_relations_on_observations',{})
            for values in table.get('rows',[]):
                cell=dict(zip(table['columns'],values));matrix_counts[cell['status']]+=1
                if cell['status']=='computed':matrix_counts['holds_'+str(cell['holds_on_observation'])]+=1
                if cell.get('reason'):matrix_counts[cell['reason']]+=1
            row['actual_contrasts']=len(result.get('contrasts',{}).get('pairs',[]))
            for name in ('contrasts','return_dependencies'):
                if result.get(name,{}).get('status')=='error':tool_counts['component_error']+=1
            if 'matrix_error' in result:tool_counts['component_error']+=1
            raw_packet=json.loads(app.read(root/'requests'/f'{episode}__final_raw.json')[1]['content'])
            tool_packet=json.loads(app.read(root/'requests'/f'{episode}__final_tool.json')[1]['content'])
            assert raw_packet.pop('tool_feedback') is None
            actual_feedback=tool_packet.pop('tool_feedback');assert actual_feedback==result
            assert raw_packet==tool_packet
            assert raw_packet['observations']==prepared['rows']
            row['paired_common_packet_equal']=True
        for arm in ('raw','tool'):
            path=root/'artifacts'/f'{episode}__final_{arm}.json'
            if path.exists():
                artifact=app.read(path)
                value=app.strict_json(artifact['raw']['text'])
                row['finals'][arm]={'state':artifact['state'],'error':artifact.get('error_code'),
                                    'error_path':artifact.get('schema_path'),'raw_output':value}
                slots['final_'+arm+'_'+artifact['state']]+=1
            else:
                blocked=app.read(root/'blocked'/f'{episode}.json')
                assert blocked['final_'+arm]=='initial_invalid'
                row['finals'][arm]={'state':'blocked','reason':'initial_invalid'}
                slots['final_'+arm+'_blocked']+=1
        rows.append(row)
    attempts=[app.read(p) for p in (root/'transport/calls').glob('*/attempt.json')]
    metadata={}
    for name,transport in [('readiness1',root/'readiness/transport'),('readiness2',root/'readiness2/transport'),('actual_run',root/'transport')]:
        values=[json.loads(x) for x in (transport/'metadata.jsonl').read_text().splitlines()]
        metadata[name]={'requests':len(values),'by_path_state':dict(Counter(x['path']+':'+x['state'] for x in values))}
    costs={'completion_attempts':len(attempts),'responses':sum(x['state']=='received' for x in attempts),
           'known_usage_attempts':sum(x.get('usage_known') is True for x in attempts),
           'unknown_usage_attempts':sum(x.get('usage_known') is not True for x in attempts),
           'input_tokens_known':sum(x.get('input_tokens') or 0 for x in attempts),
           'output_tokens_known':sum(x.get('output_tokens') or 0 for x in attempts),
           'metadata':metadata,'new_PUT_workers':0,
           'original_v40_unknown_completion':'historical separate; never reset or included in v43 known total'}
    times=[x['seconds'] for x in attempts]
    costs['client_completion_latency_seconds']={'min':min(times),'median':statistics.median(times),'max':max(times),'sum':sum(times)}
    result={'scope':'all8initial+16pairedfinal slots retained; RAW-invalid read but never repaired/executed',
            'status':app.read(root/'status.json'),'slots':dict(slots),'rows':rows,
            'raw_candidate_count':sum(len(x['raw_bindings']) for x in rows),
            'raw_candidate_mechanical_flags':dict(mechanical),'actual_tool_invocations':dict(tool_counts),
            'saved_comparison_matrix_counts':dict(matrix_counts),'costs':costs,
            'integrity':{'source_files':len(app.sources()),'prepared_pools':8,'prepared_rows':sum(x['pool_rows'] for x in rows),
                         'terminal_entries':len(inventory),'terminal_inventory_sha256':sha(root/'terminal_inventory.json'),
                         'generation_entries':len(app.read(root/'generation_frozen.json'))},
            'semantic_review':'separate manual independent review; does not follow from schema or observed holds',
            'no_input_discovery_assertion_or_reference_free_proof_claim':True}
    app.write_json(HERE/'results.json',result)
    print(json.dumps({'slots':result['slots'],'costs':costs,'matrix':dict(matrix_counts),'mechanical':dict(mechanical)},indent=2))


if __name__=='__main__':
    main()
