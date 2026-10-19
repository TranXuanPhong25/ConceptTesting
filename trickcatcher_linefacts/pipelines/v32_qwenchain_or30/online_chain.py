"""Real five-stage execution over immutable candidate artifacts; no static alignment."""
import copy
from .chain import OfflineChain,sha
from . import schemas,chain_prompts,prompt_aliases
from .online_transport import ProtocolMismatch


class OnlineChain(OfflineChain):
    def run_stage(self,stage,tokenizer,transport):
        state=self.status(stage)
        if state in ('valid','failed'):return self.data['stages'][stage]
        if state!='ready':return dict(state=state)
        artifacts={s:r['artifact'] for s,r in self.data['stages'].items() if r['state']=='valid'}
        parents={s:sha(a) for s,a in artifacts.items() if s not in ('S1','S2') or stage not in ('S1','S2')}
        try:
            request=chain_prompts.request(stage,self.task,artifacts,self.data['feedback'] if stage=='S5' else [],count_tokens=tokenizer,context_window=tokenizer.context,counter_id=tokenizer.counter_id,seed_offset=int(self.task['task_hash'][:8],16)%1000000)
        except ValueError as exc:
            rec=dict(state='failed',reason=str(exc),origin='qwen_endpoint',parents=parents)
            self.data['stages'][stage]=rec;self.save();return rec
        _,back=prompt_aliases.maps(self.task,{} if stage in ('S1','S2') else artifacts)
        response=transport.completion(request,self.store)
        if response.get('n_in')!=request['input_tokens']:raise ProtocolMismatch('cached_prompt_usage_disagrees_with_tokenizer')
        rec=dict(state='failed',request_key=request['key'],origin='qwen_endpoint',parents=parents,raw=response['text'],reference_alias_map=back,input_tokens=response.get('n_in'),output_tokens=response.get('n_out'),finish_reason=response.get('finish_reason'),cache_hit=response.get('cache_hit',False))
        if stage=='S5':rec['feedback_hash']=sha(self.data['feedback'])
        try:
            obj,offsets=schemas.extract(response['text'],response.get('finish_reason','stop'))
            rec['parsed_alias_response']=copy.deepcopy(obj)
            obj=prompt_aliases.expand(stage,obj,back);rec['parsed_expanded_response']=copy.deepcopy(obj)
            schemas.validate(stage,obj,self.task,self.data['registry'],self.selected(),[r['id'] for r in self.data['feedback']])
            registry=copy.deepcopy(self.data['registry']);artifact=schemas.register(stage,obj,self.task['task_hash'],registry)
            rec.update(state='valid',artifact=artifact,extraction_character_offsets=offsets,reference_alias_map=back);self.data['registry']=registry
        except (schemas.ArtifactError,TypeError,ValueError,KeyError) as exc:rec['reason']=str(exc) or type(exc).__name__
        self.data['stages'][stage]=rec;self.save();return rec

    def report(self):
        import json
        records=[json.loads(p.read_text()) for p in (self.directory/'requests').glob('*.json')]
        responses=[r['response'] for r in records if r.get('response') is not None and r['response'].get('origin')=='qwen_endpoint']
        return dict(scope='controlled16_fixture_Qwen_pilot',states={s:self.status(s) for s in schemas.STAGES},scheduled_slots=5,stage_records=len(self.data['stages']),physical_attempts=sum(len(r['attempts']) for r in records),received_responses=len(responses),input_tokens=sum(r['n_in'] for r in responses if type(r.get('n_in')) is int),output_tokens=sum(r['n_out'] for r in responses if type(r.get('n_out')) is int),proposal_slots=self.data['proposal_slots'],unique_inputs=len(self.data['inputs']),semantic_accuracy=None,D_IO=None)
