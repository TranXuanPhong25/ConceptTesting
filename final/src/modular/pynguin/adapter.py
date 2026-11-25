"""InputGenerator adapter over real upstream Pynguin, without oracle feedback."""
import ast
import csv
from dataclasses import asdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import textwrap

from .config import PynguinSettings
from . import runner
from .extraction import extract, target_source
from ..generators.base import InputGenerator
from ..input_preparation import load_or_prepare_packet
from ..call_builder import CallBuilder, input_identity
from final.src.runtime.artifacts import digest, read_sandbox_file
from final.src.runtime.execution import execute, ExecutionError


def source_hash(source):
    return hashlib.sha256(source.encode()).hexdigest()


def child_directory_names(work, name=''):
    descriptors=[]
    try:
        root=os.open(work,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        descriptors.append(root)
        if name:
            try:
                root=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
            except FileNotFoundError:
                return []
            descriptors.append(root)
        names=[]
        with os.scandir(root) as entries:
            for entry in entries:
                if len(names)>=64:
                    raise ValueError('unsafe_child_artifact:directory_entry_limit')
                names.append(entry.name)
        return names
    except OSError:
        raise ValueError('unsafe_child_artifact') from None
    finally:
        for descriptor in reversed(descriptors): os.close(descriptor)


def read_export_sources(work):
    names=sorted(name for name in child_directory_names(work,'export')
                 if name.startswith('test_') and name.endswith('.py'))
    if len(names)>16:
        raise ValueError('unsafe_child_artifact:export_file_limit')
    exports={};remaining=8*1024*1024
    for name in names:
        if remaining==0:
            raise ValueError('unsafe_child_artifact:export_total_size_limit')
        content=read_sandbox_file(work,'export/'+name,max_bytes=remaining)
        remaining-=len(content)
        exports[name]=content.decode()
    return exports


def read_statistics(text):
    try:
        rows=list(csv.DictReader(io.StringIO(text)))
        if len(rows)!=1 or not {'Coverage','Executed','TotalTime'} <= set(rows[0]): raise ValueError()
        row=rows[0]
        if not 0 <= float(row['Coverage']) <= 1: raise ValueError()
        if int(row['Executed']) < 0 or not math.isfinite(float(row['TotalTime'])): raise ValueError()
        return {'status':'measured','values':row}
    except (ValueError,TypeError,csv.Error):
        return {'status':'pending','reason':'invalid_statistics'}


class PynguinInputGenerator(InputGenerator):
    name='pynguin'
    uses_model=False
    requires_model=False
    uses_shared_prompt=False

    def __init__(self, settings, *, allow_missing_contract=False):
        self.settings=settings
        self.allow_missing_contract = allow_missing_contract
        self.methods=(self,)

    def configuration(self):
        config = self.settings.configuration()
        if self.allow_missing_contract:
            config['missing_contract_policy'] = 'signature_only'
        return config

    def reporter(self):
        from ..catalogue_reporting import CatalogueReporter
        return CatalogueReporter()

    def prepare_context(self, context):
        load_or_prepare_packet(context, ())

    def owners(self,context):
        programs={program['id']:program for program in (context.cohort_task or {}).get('programs',[])}
        visible=(context.packet or {}).get('visible_put_ids',[])
        return [programs[identifier] for identifier in dict.fromkeys(visible)
                if identifier in programs and programs[identifier]['base']['status']=='pass'][:self.settings.owner_limit]

    def provenance(self,context):
        return {'task_id':context.task['task_id'],'entry':context.task['entry_point'],
                'prompt_sha256':source_hash(context.task['prompt']),
                'contract_sha256':source_hash(context.metadata.get('contract','')),
                'input_types':context.metadata.get('input_types',{}),
                'settings':self.configuration(),'runtime_identity':self.settings.runtime_identity(),'input_budget':context.settings.input_budget,
                'implementation':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))},
                'owners':[{'id':p['id'],'source_sha256':source_hash(p['code'])} for p in self.owners(context)]}

    def validate_generation(self,contexts):
        for context in contexts:
            if not context.inputs or context.inputs.get('skip'): continue
            batch=context.inputs['arms']['pynguin']
            if batch['status'] not in ('complete','partial','empty'):
                raise ValueError('Pynguin generation unavailable: '+batch['status'])

    def generate(self,context):
        if (context.packet or {}).get('skip'):
            return {'task_id':context.task['task_id'],'skip':context.packet['skip']}
        return {'task_id':context.task['task_id'],'arms':{'pynguin':self.run_task(context)}}

    def run_task(self,context):
        prefix=context.task_directory+'/pynguin/'
        provenance=self.provenance(context)
        artifacts=context.artifacts
        if artifacts.exists(prefix+'intent.json'):
            if artifacts.read(prefix+'intent.json') != provenance: raise ValueError('Pynguin provenance mismatch')
            if artifacts.exists(prefix+'batch.json'):
                saved=artifacts.read(prefix+'batch.json')
                if saved['provenance']!=provenance or saved['batch_sha256']!=digest(saved['batch']):
                    raise ValueError('Pynguin saved batch provenance mismatch')
                for owner in saved['batch']['pynguin']['owners']:
                    for exported in owner.get('exports',[]):
                        artifact=artifacts.read(exported['path'])
                        if source_hash(artifact['source'])!=exported['sha256']:
                            raise ValueError('Pynguin exported test provenance mismatch')
                return saved['batch']
            return {'status':'failed','reason':'interrupted_unknown','inputs':[],'rejected':[],
                    'pynguin':{'owners':[],'provenance':provenance}}
        # Exclusive create makes concurrent callers share one dispatch budget.
        intent=artifacts.path(prefix+'intent.json')
        if artifacts.read_only: raise FileNotFoundError('Read-only replay requires Pynguin batch')
        intent.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=intent.parent,delete=False) as handle:
            temporary=Path(handle.name)
            json.dump(provenance,handle,sort_keys=True)
            handle.flush(); os.fsync(handle.fileno())
        try:
            os.link(temporary,intent)
        except FileExistsError:
            return self.run_task(context)
        finally:
            temporary.unlink()
        batch=self.construct(context,prefix,provenance)
        artifacts.write(prefix+'batch.json',{'provenance':provenance,'batch':batch,'batch_sha256':digest(batch)})
        return batch

    def construct(self,context,prefix,provenance):
        batch={'status':'empty','inputs':[],'rejected':[],
               'pynguin':{'owners':[],'provenance':provenance,'candidate_ledger':[],
                          'common_observer_coverage':'pending'}}
        if not Path(self.settings.python).is_file() or not shutil.which('bwrap'):
            return {**batch,'status':'unsupported_environment','reason':'missing_python_or_bwrap'}
        if (context.packet or {}).get('skip'):
            return {**batch,'status':'empty','reason':context.packet['skip']}
        contract=context.metadata.get('contract')
        if not isinstance(contract, str) or (not contract.strip() and not self.allow_missing_contract):
            return {**batch,'status':'unsupported_input','reason':'missing_trusted_contract'}
        if not contract.strip():
            batch['pynguin']['domain_admission'] = 'not_measured'
        try:
            builder=CallBuilder.for_source(context.task['prompt'],context.task['entry_point'],
                input_types=context.metadata.get('input_types'))
        except (SyntaxError,ValueError,TypeError) as error:
            return {**batch,'status':'unsupported_input','reason':str(error)}
        identities={}
        for index,owner in enumerate(self.owners(context)):
            receipt=self.search_owner(context,prefix,index,owner)
            batch['pynguin']['owners'].append(receipt)
            for rejection in receipt.get('rejected',[]): batch['rejected'].append({**rejection,'owner':owner['id']})
            candidates=receipt.get('calls',[])
            try:
                if contract.strip():
                    validation=execute({'mode':'validate','context':context.task['prompt'], 'source':'',
                        'entry':context.task['entry_point'],
                        'contract':textwrap.indent(textwrap.dedent(contract), '    '),
                        'tests':candidates,'timeout':context.settings.timeout_seconds})['tests'] if candidates else []
                else:
                    validation = [{'status': 'not_measured'} for _ in candidates]
                if (len(validation)!=len(candidates) or any(not isinstance(row,dict) or
                        row.get('status') not in (('valid','invalid_domain','error','timeout') if contract.strip()
                                                  else ('not_measured',)) for row in validation)):
                    raise ExecutionError('invalid_domain_validation_result')
            except (ExecutionError,KeyError,TypeError) as error:
                receipt['status_before_domain_validation']=receipt['status']
                receipt.update(status='failed',reason='domain_validation_failed',
                    domain_validation={'status':'failed','detail':str(error)})
                for candidate in candidates:
                    row={'owner':owner['id'],'test':candidate['test'],'candidate':candidate,
                         'selection':'rejected','reason':'domain_validation_failed'}
                    batch['rejected'].append(row)
                    batch['pynguin']['candidate_ledger'].append(row.copy())
                continue
            receipt['domain_validation']={'mode':'validate','tests':validation}
            for candidate,domain in zip(candidates,validation):
                row={'owner':owner['id'],'test':candidate['test'],'candidate':candidate}
                try:
                    bound=builder.signature.bind(*ast.literal_eval(candidate['args']),**ast.literal_eval(candidate['kwargs']))
                    bound.apply_defaults()
                    record=builder.build_values(bound.arguments)
                    if domain['status']=='invalid_domain': raise ValueError('outside_trusted_domain')
                    if domain['status'] not in ('valid', 'not_measured'):
                        raise ValueError('domain_validation_error:'+domain['status'])
                    identity=input_identity(builder.signature,record)
                    if identity in identities:
                        row['selection']='duplicate'
                        identities[identity]['provenance'].append({'owner':owner['id'],'test':candidate['test']})
                    elif len(batch['inputs'])>=min(20,context.settings.input_budget):
                        row['selection']='input_budget'
                    else:
                        record.update(id='pynguin_'+str(len(batch['inputs'])),
                                      provenance=[{'owner':owner['id'],'test':candidate['test']}])
                        batch['inputs'].append(record); identities[identity]=record
                        row['selection']='selected_stable_owner_test_order'
                except (ValueError,TypeError,SyntaxError,RecursionError) as error:
                    row.update(selection='rejected',reason=str(error))
                    batch['rejected'].append(row.copy())
                batch['pynguin']['candidate_ledger'].append(row)
        statuses=[owner['status'] for owner in batch['pynguin']['owners']]
        failures=[{'owner':owner['owner'],'status':owner['status'],'reason':owner.get('reason','unknown')}
                  for owner in batch['pynguin']['owners'] if owner['status'] not in ('complete','empty','unsupported_input')]
        batch['pynguin'].update(partial=bool(failures and batch['inputs']),owner_failures=failures)
        if any(status not in ('complete','empty','unsupported_input') for status in statuses):
            batch['status']='partial' if batch['inputs'] else 'timeout' if 'timeout' in statuses else 'failed'
        elif batch['inputs']: batch['status']='complete'
        elif 'unsupported_input' in statuses: batch['status']='unsupported_input'
        return batch

    def extend_summary(self,contexts,summary,reporting):
        tasks=[]
        executions=[]
        for context in contexts:
            batch=(context.inputs or {}).get('arms',{}).get('pynguin')
            if batch is None: continue
            owners=batch['pynguin']['owners']
            row={'task_id':context.task['task_id'],'status':batch['status'],
                 'owner_searches':len(owners),'inputs':len(batch['inputs']),
                 'search_seconds_requested':len(owners)*self.settings.search_seconds,
                 'execution_limit_requested':len(owners)*self.settings.maximum_test_executions,
                 'elapsed_seconds':sum(owner.get('elapsed_seconds',0) +
                     owner.get('extraction_receipt',{}).get('elapsed_seconds',0) for owner in owners)}
            for owner in owners:
                statistics=owner.get('native_statistics',{})
                executions.append(int(statistics['values']['Executed'])
                    if isinstance(statistics,dict) and statistics.get('status')=='measured' else None)
            tasks.append(row)
        summary['pynguin']={'tasks':tasks,'model_calls':0,'model_tokens':0,
            'configuration':self.configuration(),'actual_test_executions':
            sum(executions) if executions and all(value is not None for value in executions) else 'pending',
            'execution_limit_is_hard':False,'common_observer_coverage':'pending'}

    def search_owner(self,context,prefix,index,owner):
        source=owner['code']
        packaged_source,offset=target_source(source,context.task['prompt'])
        receipt={'owner':owner['id'],'source_sha256':source_hash(source),'seed':self.settings.seed,
                 'source_mapping':{'original_line_offset':offset,'wrapper_origin':'public_context_then_exact_put',
                                   'context_sha256':source_hash(context.task['prompt']),
                                   'packaged_source_sha256':source_hash(packaged_source)},
                 'exports':[],'native_statistics':'pending','calls':[],'rejected':[]}
        with tempfile.TemporaryDirectory(prefix='pynguin-') as temporary:
            work=Path(temporary)
            source_path=prefix+f'owners/{index}/source.json'
            context.artifacts.write(source_path,{'source':source})
            receipt['source_path']=source_path
            (work/'target.py').write_text(packaged_source)
            (work/'settings.json').write_text(json.dumps(asdict(self.settings)))
            shutil.copyfile(runner.__file__,work/'runner.py')
            search=runner.sandbox(self.settings.python,work,'runner.py',self.settings.wall_seconds)
            receipt.update(search)
            receipt['logs']=[]
            try:
                root_names=child_directory_names(work)
                for name in ('stdout.log','stderr.log'):
                    path=prefix+f'owners/{index}/'+name+'.json'
                    text=read_sandbox_file(work,name).decode(errors='replace')[:16000]
                    context.artifacts.write(path,{'text':text})
                    receipt['logs'].append({'path':path,'sha256':source_hash(text)})
                if 'actual_config.json' in root_names:
                    actual=read_sandbox_file(work,'actual_config.json')
                    try: receipt['actual_config']=json.loads(actual)
                    except ValueError: receipt.update(status='failed',reason='invalid_actual_config')
                exports=read_export_sources(work)
                for name,text in exports.items():
                    path=prefix+f'owners/{index}/'+name+'.json'
                    context.artifacts.write(path,{'source':text})
                    receipt['exports'].append({'path':path,'sha256':source_hash(text)})
                if 'statistics.csv' in child_directory_names(work,'statistics'):
                    receipt['native_statistics']=read_statistics(read_sandbox_file(work,'statistics/statistics.csv').decode())
            except (OSError,ValueError,UnicodeError):
                return {**receipt,'status':'failed','reason':'unsafe_child_artifact'}
            if receipt['status']!='complete': return receipt
            if not exports: return {**receipt,'status':'empty','reason':'missing_or_empty_export'}
            extraction=work/'extraction'
            try: extraction.mkdir()
            except OSError: return {**receipt,'status':'failed','reason':'unsafe_child_artifact'}
            shutil.copyfile(runner.__file__,extraction/'runner.py')
            from .. import call_builder
            shutil.copyfile(call_builder.__file__,extraction/'call_builder.py')
            remaining=max(.01,self.settings.wall_seconds-search['elapsed_seconds'])
            extracted=extract(self.settings.python,extraction,source,context.task['entry_point'],exports,
                              self.settings.max_extract_calls,remaining,context_source=context.task['prompt'])
            receipt.update(status=extracted['status'],calls=extracted['calls'],rejected=extracted['rejected'],
                           extraction_receipt={k:v for k,v in extracted.items() if k not in ('calls','rejected')})
        return receipt
