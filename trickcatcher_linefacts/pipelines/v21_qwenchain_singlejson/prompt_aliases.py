"""Exact task/request-bound ID aliases; no semantic matching, fuzzy edits or prose rewriting."""
import copy


def maps(task,artifacts):
    forward={n['id']:'N'+str(i+1) for i,n in enumerate(task['nodes'])}
    for stage,artifact in artifacts.items():
        for row in artifact['items']:
            local=row['local_id'];forward[row['id']]=local if stage in ('S1','S2','S3') else stage+'.'+local
    if len(set(forward.values()))!=len(forward):raise ValueError('alias_collision')
    return forward,{short:full for full,short in forward.items()}


def view(task,artifacts,feedback):
    forward,back=maps(task,artifacts)
    reference_fields={'id','source_id','source_ids','source','target','entry_source_id','obligation_ids','behavior_ids','hypothesis_ids','selected_ids','supersedes','proposal_id','evidence_ids'}
    def walk(x,key=''):
        if isinstance(x,str):return forward.get(x,x) if key in reference_fields else x
        if isinstance(x,list):return [walk(v,key) for v in x]
        if isinstance(x,dict):return {k:walk(v,k) for k,v in x.items()}
        return x
    return walk(task),walk(artifacts),walk(feedback),back


def expand(stage,obj,back):
    out=copy.deepcopy(obj)
    def ref(value):
        if type(value) is not str:raise ValueError('reference_alias_shape')
        if value in back:return back[value]
        if value in back.values():return value
        raise ValueError('unknown_reference_alias')
    if type(out.get('items')) is not list:raise ValueError('alias_item_shape')
    for row in out['items']:
        if type(row) is not dict:raise ValueError('alias_item_shape')
        for field in ('source_ids','obligation_ids','behavior_ids','hypothesis_ids','observe'):
            if field in row and type(row[field]) is not list:raise ValueError('alias_reference_shape')
        if stage in ('S2','S3'):row['source_ids']=[ref(x) for x in row.get('source_ids',[])]
        if stage=='S3':
            for field in ('obligation_ids','behavior_ids'):row[field]=[ref(x) for x in row.get(field,[])]
        if stage in ('S4','S5'):
            row['hypothesis_ids']=[ref(x) for x in row.get('hypothesis_ids',[])]
            for observation in row.get('observe',[]):
                if type(observation) is not dict:raise ValueError('alias_observation_shape')
                observation['source_id']=ref(observation.get('source_id'))
    if stage=='S5':
        if type(out.get('decisions')) is not list:raise ValueError('alias_decision_shape')
        for row in out['decisions']:
            if type(row) is not dict:raise ValueError('alias_decision_shape')
            row['supersedes']=ref(row.get('supersedes'))
    # Local item IDs, selected_ids, feedback IDs and semantic prose are never expanded.
    return out
