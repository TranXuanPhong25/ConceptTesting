"""The combined technique is one model completion, not an input-set union."""
import json

from final.src.core_model import ModelResponse
from final.src.modular.arms.classical import EpDtBvaArm
from final.src.modular.input_prompts import structured_input_prompt
from final.src.modular.generators.methods import MethodInputGenerator
from final.src.modular.tests.test_testing_arms import context
from final.src.orchestration.config import preview


def test_three_techniques_share_one_completion_catalogue_and_input_list(tmp_path):
    calls=[]
    class Calls:
        def complete(self,*args,**kwargs):
            calls.append((args,kwargs))
            return ModelResponse(json.dumps({'catalogue':{
                'classes':[{'id':'E','description':'class selected by a specification rule'}],
                'boundaries':[{'id':'B','dimension':'x','values':[1,2]}],
                'rules':[{'id':'R','conditions':{'C1':'T'},'actions':['A1'],'merged_from':[]}]},
                'inputs':[{'arguments':{'x':1},'covers':['E','B','R']}]}),finish_reason='stop')
    ctx=context(tmp_path);ctx.calls=Calls()
    ctx.packet={'common':structured_input_prompt(ctx.task,[],ctx.metadata['contract'],20)}
    result=EpDtBvaArm().run(ctx)
    assert len(calls)==1 and calls[0][0][1]=='ep_dt_bva'
    assert calls[0][1]['max_tokens']==4096
    assert result['catalogue_status']=='applicable'
    assert len(result['inputs'])==1 and result['inputs'][0]['covers']==['E','B','R']
    assert set(result['catalogue'])>={'classes','boundaries','rules'}
    assert 'expected' not in result['inputs'][0]
    generator=MethodInputGenerator((EpDtBvaArm(),))
    assert len(generator.methods)==1 and generator.post_reference_stages()[0].names==('ep_dt_bva',)


def test_single_combined_full_run_has_single_arm_budget():
    budget=preview({'cohort':'humaneval164','arms':['ep_dt_bva'],'completion_tokens':4096,
                    'inputs_per_task':20,'timeout_seconds':8})
    assert budget['logical_calls_by_arm']=={'ep_dt_bva':157}
    assert budget['logical_call_cap']==157 and budget['max_input_slots_per_arm']==3140
    assert budget['evaluated_base_pass_put_count']==1454
