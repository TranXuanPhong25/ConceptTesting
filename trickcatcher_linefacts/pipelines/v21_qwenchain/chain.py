"""Offline-only five-stage dependency adapter. No semantic selector or network calls."""
import copy
import hashlib
import json
from pathlib import Path
from . import schemas,chain_prompts
from .chain_inputs import parse_arguments,literal_for_transport
from .chain_store import Store
from .evidence import project_feedback,compare_prediction
from .llm_client import atomic_json
from .paths import CONFIG
from .chain_protocol import fingerprint


def sha(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


class OfflineChain:
    def __init__(self,task,directory):
        self.task=copy.deepcopy(task);self.directory=Path(directory).resolve();self.directory.mkdir(parents=True,exist_ok=True)
        self.store=Store(self.directory/'requests');self.path=self.directory/'state.json'
        context=dict(task=task,config=CONFIG['chain'],adapter_protocol=fingerprint())
        context_path=self.directory/'context.json'
        if context_path.exists() and json.loads(context_path.read_text())!=context:raise ValueError('context_drift')
        if not context_path.exists():atomic_json(context_path,context)
        self.data=json.loads(self.path.read_text()) if self.path.exists() else dict(stages={},registry={},feedback=[],feedback_ready=False,inputs={},proposal_slots={'S4':0,'S5':0})
    def save(self):atomic_json(self.path,self.data)
    def status(self,stage):
        stages=self.data['stages']
        if stage in stages:return stages[stage]['state']
        required={'S1':[],'S2':[],'S3':['S1','S2'],'S4':['S3'],'S5':['S4']}[stage]
        if any(self.status(s) in ('failed','blocked') for s in required):return 'blocked'
        if any(self.status(s)=='not_applicable' for s in required):return 'not_applicable'
        if any(self.status(s)!='valid' for s in required):return 'waiting'
        if stage in ('S4','S5'):
            alignment=stages.get('S3',{}).get('artifact',{})
            if not alignment.get('selected_ids'):return 'not_applicable'
        if stage=='S5' and not self.data['feedback_ready']:return 'waiting_feedback'
        return 'ready'
    def selected(self):return self.data['stages'].get('S3',{}).get('artifact',{}).get('selected_ids',[])
    def ingest_fixture(self,stage,raw,*,count_tokens,context_window,counter_id='offline_fixture_counter',finish_reason='stop'):
        """Explicitly hand-authored responses, never evidence of Qwen performance."""
        state=self.status(stage)
        if state not in ('ready','valid','failed'):return dict(state=state)
        if state in ('valid','failed'):return self.data['stages'][stage]
        artifacts={s:r['artifact'] for s,r in self.data['stages'].items() if r['state']=='valid'}
        parents={s:sha(a) for s,a in artifacts.items() if s not in ('S1','S2') or stage not in ('S1','S2')}
        try:
            req=chain_prompts.request(stage,self.task,artifacts,self.data['feedback'] if stage=='S5' else [],count_tokens=count_tokens,context_window=context_window,counter_id=counter_id)
        except ValueError as exc:
            record=dict(state='failed',reason=str(exc),origin='offline_fixture',parents=parents)
            self.data['stages'][stage]=record;self.save();return record
        reservation=self.store.reserve(req)
        if reservation['state']=='reserved':
            response=dict(text=raw,finish_reason=finish_reason,origin='offline_fixture')
            self.store.finish(req['key'],reservation['attempt'],response=response)
        elif reservation['state']=='cache_hit':response=reservation['response']
        else:return dict(state=reservation['state'])
        record=dict(state='failed',request_key=req['key'],origin='offline_fixture',parents=parents,raw=response['text'])
        if stage=='S5':record['feedback_hash']=sha(self.data['feedback'])
        try:
            obj,offsets=schemas.extract(response['text'],response.get('finish_reason','stop'))
            schemas.validate(stage,obj,self.task,self.data['registry'],self.selected(),[r['id'] for r in self.data['feedback']])
            staged=copy.deepcopy(self.data['registry'])
            artifact=schemas.register(stage,obj,self.task['task_hash'],staged)
            record.update(state='valid',artifact=artifact,extraction_character_offsets=offsets)
            self.data['registry']=staged
        except (schemas.ArtifactError,TypeError,ValueError,KeyError) as exc:record['reason']=str(exc) or type(exc).__name__
        self.data['stages'][stage]=record;self.save();return record
    def input_slots(self,stage):
        if stage not in ('S4','S5') or self.status(stage)!='valid':raise ValueError('valid_probe_stage_required')
        rows=[]
        # Idempotent parse: budget uses actual artifact rows, not invocation count.
        artifact=self.data['stages'][stage]['artifact'];self.data['proposal_slots'][stage]=len(artifact['items'])
        for probe in artifact['items']:
            row=dict(proposal_id=probe['id'],input_repr=probe['input_repr'],prediction=probe['prediction'],observe=probe['observe'])
            try:
                args=parse_arguments(probe['input_repr'],self.task['arity']);literal=literal_for_transport(args)
                key=sha(dict(source_hash=self.task['source_hash'],input_repr=literal))
                if key not in self.data['inputs']:
                    if len(self.data['inputs'])>=CONFIG['chain']['max_unique_inputs']:raise ValueError('input_budget')
                    self.data['inputs'][key]=dict(input_repr=literal,result=None)
                row.update(status='parsed',input_key=key,input_repr=literal)
                if self.data['inputs'][key]['result'] is not None:row.update(status='cached',execution=self.data['inputs'][key]['result'])
            except (ValueError,TypeError,RecursionError) as exc:row.update(status='rejected',reason=str(exc))
            rows.append(row)
        self.save();return rows
    def attach_feedback(self,attempts):
        if self.status('S4')!='valid':raise ValueError('S4_required')
        probes=self.data['stages']['S4']['artifact']['items']
        if len(attempts)!=len(probes) or [x.get('proposal_id') for x in attempts]!=[x['id'] for x in probes]:raise ValueError('all_proposal_statuses_required')
        for a,probe in zip(attempts,probes):
            if a.get('input_repr')!=probe['input_repr']:
                # Canonical normalized representation is also accepted for the same literal.
                try:equal=literal_for_transport(parse_arguments(a['input_repr'],self.task['arity']))==literal_for_transport(parse_arguments(probe['input_repr'],self.task['arity']))
                except (ValueError,KeyError):equal=False
                if not equal:raise ValueError('feedback_input_mismatch')
            if 'execution' in a:a['prediction_check']=compare_prediction(probe['prediction'],a['execution'])
        feedback=project_feedback(attempts)
        if self.data['feedback_ready'] and feedback!=self.data['feedback']:raise ValueError('feedback_immutable')
        self.data['feedback']=feedback;self.data['feedback_ready']=True;self.save();return feedback
    def execute_fixture_slots(self,stage,directory=None):
        """Local execution of explicitly offline fixture inputs, no model/network."""
        from .execution_adapter import execute
        cache_root=self.directory/'native_executions'
        if directory is not None and Path(directory).resolve()!=cache_root:raise ValueError('execution_directory_drift')
        attempts=self.input_slots(stage)
        for row in attempts:
            if row['status'] in ('parsed','cached'):
                # The adapter reuses immutable ordinary/traced records and only reprojects observations.
                result=execute(self.task,row['input_repr'],row['observe'],cache_root)
                self.record_input_result(row['input_key'],result);row['execution']=result;row['status']=result['status']
            if 'execution' in row:row['prediction_check']=compare_prediction(row['prediction'],row['execution'])
        if stage=='S4':self.attach_feedback(attempts)
        return attempts
    def record_input_result(self,key,result):
        if key not in self.data['inputs']:raise ValueError('unknown_input')
        previous=self.data['inputs'][key]['result']
        if previous is not None:
            core=lambda r:{k:v for k,v in r.items() if k!='observations'}
            if core(previous)!=core(result):raise ValueError('input_result_immutable')
            return
        self.data['inputs'][key]['result']=result;self.save()
    def report(self):
        return dict(scope='offline_adapter_only_no_Qwen_semantics',states={s:self.status(s) for s in schemas.STAGES},scheduled_slots=5,received_artifacts=len(self.data['stages']),proposal_slots=self.data['proposal_slots'],unique_inputs=len(self.data['inputs']),put_execution_upper_bound=2*len(self.data['inputs']),semantic_accuracy=None,D_IO=None,model_calls=0)
