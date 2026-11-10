"""Evaluate a materialized union using the exact already-executed native pool.

ReferenceOracleStage and PutEvaluationStage replay read-only checkpoints. There is
no model backend and missing checkpoints are fatal; this module cannot run a PUT.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil

from final.src.runtime.artifacts import digest, save
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.dataset import load_tasks
from final.src.modular.cohort import load_cohort
from final.src.modular.input_contract import validate_generated_inputs
from final.src.modular.references import HumanEvalPlusReferencePrograms
from final.src.modular.stages.reference_oracle import ReferenceOracleStage
from final.src.modular.stages.put_evaluation import PutEvaluationStage
from final.src.modular.stages.reporting import ReportingStage
from final.src.audits.detection_kinds import observation_kind, strongest_kind
from final.src.audits.run_bva_precision import evaluation_observations
from final.src.audits.run_bva_full import SourceGuard
from final.src.audits.resume_bva_batch import inventory

SOURCE_ARMS = ('plain', 'ep_bva', 'decision_table')
UNION_ARM = 'union'


def read(path):
    return json.loads(Path(path).read_text())


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_union_pool(oracle, source_arms):
    """Only an exact, deduplicated full pool may reuse these native checkpoints."""
    keys = [test['input_key'] for test in oracle['tests']]
    if len(keys) != len(set(keys)):
        raise ValueError('Source oracle pool has duplicate input keys')
    covered = set()
    for name in source_arms:
        indices = oracle['arm_indices'][name]
        if any(type(index) is not int or not 0 <= index < len(keys) for index in indices):
            raise ValueError('Invalid source arm input index')
        covered.update(indices)
    if covered != set(range(len(keys))):
        raise ValueError('Source arms do not cover the exact native evaluation pool')
    return list(range(len(keys)))


def validate_native_evidence(task_directory, source_result, input_count):
    """Reconfirm every saved failing index from the actual two observations."""
    for put_id, outcome in source_result['outcomes'].items():
        observations = evaluation_observations(task_directory, put_id, outcome)
        if len(observations) != input_count:
            raise ValueError('Native checkpoint length differs from union input count')
        confirmed = [index for index, values in enumerate(observations)
                     if len(values) == 2 and all(value['status'] in ('fail', 'error', 'timeout') for value in values)]
        if confirmed != outcome['failing']:
            raise ValueError('Saved confirmed failures differ from native checkpoint evidence')


def validate_source(source):
    """Require a complete, verified three-arm full run with frozen generation."""
    SourceGuard(source).verify()
    result = read(source/'result_digest.json')
    if read(source/'status.json')['state'] != 'complete':
        raise ValueError('Union source must be completed')
    if not result.get('read_only_replay_matches') or not result.get('source_hashes_verified'):
        raise ValueError('Union source requires verified source and replay')
    manifest = read(source/'modular_manifest.json')
    if tuple(arm['name'] for arm in manifest['arms']) != SOURCE_ARMS:
        raise ValueError('Expected same-run Plain, EP+BVA and Decision Table inputs')
    freeze = read(source/'generation_frozen.json')
    if freeze['inputs_sha256'] != digest(freeze['inputs']) or set(freeze['inputs']) != set(manifest['tasks']):
        raise ValueError('Invalid source generation freeze')
    if freeze['cohort_sha256'] != manifest['cohort_sha256']:
        raise ValueError('Source cohort/freeze mismatch')
    return manifest, freeze


def source_material(source, manifest):
    """Pin task/domain/reference data and the exact shared replay-stage code."""
    plan = read(source/'launch_plan.json'); runtime = Path(plan['runtime'])
    cohort = load_cohort(Path(plan['cohort']))
    if cohort['cohort_sha256'] != manifest['cohort_sha256']:
        raise ValueError('Source cohort checksum differs')
    tasks_by_id = {task['task_id']:task for task in load_tasks()}
    tasks = [tasks_by_id[task_id] for task_id in manifest['tasks']]
    metadata = read(runtime/'final/data/contracts.json')
    selected_metadata = {task['task_id']:metadata[task['task_id']] for task in tasks}
    if digest(tasks) != manifest['task_data_sha256'] or digest(selected_metadata) != manifest['metadata_sha256']:
        raise ValueError('Task/spec/domain differs from source run')
    from final.src.modular.stages import reference_oracle, put_evaluation
    from final.src.modular import execution_cache
    for module in (reference_oracle, put_evaluation, execution_cache):
        relative = Path(module.__file__).resolve().relative_to(Path(__file__).resolve().parents[3])
        if checksum(Path(module.__file__)) != checksum(runtime/relative):
            raise ValueError('Replay stage code differs from source runtime: '+str(relative))
    references = HumanEvalPlusReferencePrograms(runtime/'final/data/humanevalplus_v0.1.10_references.json')
    return tasks, metadata, {task['task_id']:task for task in cohort['tasks']}, references


def evaluate(source, output, *, replay=False):
    source = Path(source).resolve(); output = Path(output).resolve()
    if source == output:
        raise ValueError('Union needs a separate output directory')
    manifest, freeze = validate_source(source)
    original_inventory = inventory(source)
    tasks, metadata, cohort, references = source_material(source, manifest)
    settings = PipelineSettings(**manifest['settings'])
    output_store = ArtifactStore(output, read_only=replay)
    source_store = ArtifactStore(source, read_only=True)
    if not replay:
        output.mkdir(parents=True, exist_ok=False)
    source_root = Path(__file__).resolve().parents[1]
    implementation_files = [path for path in source_root.rglob('*.py')
                            if 'tests' not in path.parts and '__pycache__' not in path.parts]
    implementation_hashes = {str(path.resolve()):checksum(path) for path in implementation_files}
    if not replay:
        for path in implementation_files:
            target = output/'implementation'/path.relative_to(source_root)
            target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(path,target)
            if checksum(target) != implementation_hashes[str(path.resolve())]:
                raise ValueError('Union evaluator changed while freezing implementation')
    output_store.write('evaluation_manifest.json', {
        'schema':'saved-union-replay-manifest-v1', 'source_directory':str(source),
        'source_inventory_sha256':digest(original_inventory),
        'implementation':implementation_hashes,
        'packages':{name:importlib.metadata.version(name) for name in ('numpy','scipy','pydantic','evalplus')},
        'new_model_calls':0, 'new_native_calls':0,
    })
    generation_hashes = {}; rows = []; kind_counts = Counter(); total_inputs = 0; duplicated_memberships = 0
    source_indices = {}; detection_kind_rows = []; checkpoint_copies = []
    for ordinal, task in enumerate(tasks, 1):
        number = task['task_id'].split('/')[-1]; directory = f'tasks/{number}'
        batch = source_store.read(directory+'/inputs.json')
        if digest(batch) != freeze['inputs'][task['task_id']]:
            raise ValueError('Source generated input batch changed')
        context = TaskContext(task, metadata[task['task_id']], source_store, settings)
        context.cohort_task = cohort[task['task_id']]; context.inputs = batch; context.inputs_frozen = True
        # Read-only stores make every cache miss fatal, before any executor call.
        ReferenceOracleStage(reference_programs=references).run(context)
        PutEvaluationStage().run(context)
        original_result = context.result
        if batch.get('skip'):
            union_batch = batch; union_result = original_result
        else:
            union_indices = validate_union_pool(context.oracle, SOURCE_ARMS)
            validate_native_evidence(source/directory, original_result, len(union_indices))
            union_inputs = [{'args':test['args'], 'kwargs':test['kwargs']}
                            for test in context.oracle['tests']]
            union_batch = {'task_id':task['task_id'], 'arms':{
                **batch['arms'], UNION_ARM:{'inputs':union_inputs, 'rejected':[], 'status':'saved_union_replay'}}}
            validate_generated_inputs(union_batch, task_id=task['task_id'], input_budget=3*settings.input_budget)
            context.inputs = union_batch
            context.oracle = {**context.oracle, 'arm_indices':{**context.oracle['arm_indices'],UNION_ARM:union_indices}}
            # Same test list and same native indices: only add union attribution.
            union_result = PutEvaluationStage().evaluate_programs(context)
            if union_result['outcomes'] != original_result['outcomes']:
                raise ValueError('Union replay changed source outcomes')
            total_inputs += len(union_indices)
            duplicated_memberships += sum(len(context.oracle['arm_indices'][name]) for name in SOURCE_ARMS)-len(union_indices)
            source_indices[task['task_id']] = {name:context.oracle['arm_indices'][name] for name in SOURCE_ARMS}
            output_store.write(directory+'/oracle_valid.json', context.oracle)
            for put_id in union_result['arms'][UNION_ARM]['detected_put_ids']:
                outcome = union_result['outcomes'][put_id]
                observations = evaluation_observations(source/directory, put_id, outcome)
                kind = strongest_kind({observation_kind(observations[index]) for index in outcome['failing']})
                kind_counts[kind] += 1
                detection_kind_rows.append({'task_id':task['task_id'],'put_id':put_id,'kind':kind})
            if not replay:
                for native_path in (source/directory/'evaluation').glob('*.json'):
                    target = output/directory/'evaluation'/native_path.name
                    target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(native_path,target)
                    expected_hash = original_inventory[str(native_path)]
                    if checksum(target) != expected_hash:
                        raise ValueError('Copied native evidence differs from source checkpoint')
                    checkpoint_copies.append({'target':str(target.relative_to(output)),
                                              'source':str(native_path), 'sha256':expected_hash})
        output_store.write(directory+'/inputs.json', union_batch)
        output_store.write(directory+'/result.json', union_result)
        generation_hashes[task['task_id']] = digest(union_batch); rows.append(union_result)
        if not replay:
            save(output/'progress.json',{'state':'replaying_saved_evaluation','evaluated_tasks':ordinal,
                'total_tasks':len(tasks),'new_model_calls':0,'new_native_calls':0})
    output_store.write('generation_frozen.json',{'cohort_sha256':manifest['cohort_sha256'],
        'inputs':generation_hashes,'inputs_sha256':digest(generation_hashes)})
    totals = {}; evaluated_puts = 0; eligible_tasks = 0
    for row in rows:
        if row.get('skip'):continue
        eligible_tasks += 1; evaluated_puts += row['base_pass']
        for arm, values in row['arms'].items():
            target = totals.setdefault(arm,{'valid_inputs':0,'detected':0,'tasks_detected':0})
            target['valid_inputs'] += values['valid_inputs'];target['detected'] += values['detected']
            target['tasks_detected'] += values['detected']>0
    comparisons = [ReportingStage().compare(rows,name,UNION_ARM) for name in SOURCE_ARMS]
    summary = {'schema':'saved-input-union-evaluation-v1','source_directory':str(source),
        'source_generation_sha256':freeze['inputs_sha256'],'source_cohort_sha256':manifest['cohort_sha256'],
        'settings':{**manifest['settings'],'input_budget':3*settings.input_budget},'source_settings':manifest['settings'],
        'task_records':len(tasks),'eligible_tasks':eligible_tasks,'evaluated_base_pass':evaluated_puts,
        'arms':totals,'union_valid_inputs':total_inputs,'duplicate_valid_memberships_removed':duplicated_memberships,
        'union_detection_kinds':dict(kind_counts),'union_detections':detection_kind_rows,'comparisons':comparisons,
        'upstream_generation_usage':read(source/'result_digest.json')['writer_usage'],
        'new_model_calls':0,'new_native_calls':0,'source_hashes_verified':True,'source_unchanged':True,
        'scope':'exact existing native pool replay; larger input budget; matched analysis post-hoc descriptive'}
    if inventory(source) != original_inventory:
        raise ValueError('Source files changed during union evaluation replay')
    if any(checksum(Path(name)) != expected for name,expected in implementation_hashes.items()):
        raise ValueError('Executing union evaluator source changed during replay')
    output_store.write('union_summary.json',summary)
    if not replay:
        save(output/'source_inventory.json',original_inventory)
        save(output/'checkpoint_copy_receipts.json',checkpoint_copies)
        save(output/'union_input_provenance.json',{'source_arm_indices':source_indices})
        copied = {str(path.relative_to(output)):checksum(path) for path in output.rglob('*')
                  if path.is_file() and path.name not in ('progress.json','replay_files.json')}
        save(output/'replay_files.json',copied)
    else:
        for receipt in read(output/'checkpoint_copy_receipts.json'):
            if (checksum(output/receipt['target']) != receipt['sha256'] or
                    original_inventory[receipt['source']] != receipt['sha256']):
                raise ValueError('Materialized native evidence no longer matches source')
        for name,expected in read(output/'replay_files.json').items():
            if checksum(output/name)!=expected:raise ValueError('Materialized union artifact changed: '+name)
    return summary


def render(summary):
    union = summary['arms'][UNION_ARM]
    lines=['# Union inputs: Plain + EP+BVA + Decision Table','',
        f"Union phát hiện **{union['detected']}/{summary['evaluated_base_pass']} eligible PUTs**, trên "
        f"{union['tasks_detected']}/{summary['eligible_tasks']} eligible tasks, bằng {union['valid_inputs']} unique novel-valid inputs. "
        'Đây là gộp input đã sinh, không phải một generator mới. Union có budget lớn hơn từng arm; không suy ra gain ở cùng budget.', '',
        '| Arm | Novel valid inputs | Detected PUTs | Task có detection |','|---|---:|---:|---:|']
    for name,values in summary['arms'].items():
        lines.append(f"| {name} | {values['valid_inputs']} | {values['detected']} | {values['tasks_detected']} |")
    lines += ['',f"Union kinds: {summary['union_detection_kinds']}; mỗi PUT lấy strongest kind wrong-value→exception→resource. "
        f"Loại {summary['duplicate_valid_memberships_removed']} duplicate memberships giữa các arms.", '',
        'Source đã chạy reference và PUT trên đúng union pool, nên evaluation này replay lại toàn bộ shared reference/scorer '
        'từ checkpoint read-only. Thiếu checkpoint hoặc mismatched freeze/evidence sẽ fail; không chạy lại cùng native workload. '
        'Đã kiểm các first-failure confirmations trên từng PUT và pool identity. '
        '0 model calls mới, 0 native calls mới; giữ nguyên mọi source outputs/checkpoints.', '',
        f"Config thực tế: {summary['task_records']} task records/{summary['eligible_tasks']} eligible tasks;timeout "
        f"{summary['settings']['timeout_seconds']} giây/input;input cap union{summary['settings']['input_budget']}/task "
        f"so với{summary['source_settings']['input_budget']}/task/arm;corrected reference/scorer/seeds giữ nguồn.", '',
        'Chi phí upstream generation không phải miễn phí: ```'+json.dumps(summary['upstream_generation_usage'],ensure_ascii=False)+'```', '',
        'Matched-valid-budget (post-hoc descriptive, seeded random subsets; không lấy prefix):']
    for row in summary['comparisons']:
        lines.append(f"- {row['left']} vs union:macro detected PUT fraction {row['left_macro_fraction']:.6f} vs "
                     f"{row['right_macro_fraction']:.6f};p={row['paired_permutation_pvalue']:.5g};"
                     f"zero-budget tasks{row['zero_valid_budget_tasks']}/{row['task_count']}.")
    lines += ['', 'Source checks, source inventory trước/sau và materialized union replay PASS. '
              'Catalogue semantics của các generator nguồn chưa được xác nhận chỉ từ union detection.', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args();output=args.artifacts.resolve()
    result=evaluate(args.source,output)
    if evaluate(args.source,output,replay=True)!=result:raise ValueError('Union immutable replay differs')
    result={**result,'read_only_replay_matches':True}
    save(output/'result_digest.json',result);(output/'REPORT.md').write_text(render(result))
    save(output/'progress.json',{'state':'complete','evaluated_tasks':result['task_records'],'total_tasks':result['task_records']})
    save(output/'status.json',{'state':'complete','new_model_calls':0,'new_native_calls':0})
    print(json.dumps({'union':result['arms'][UNION_ARM],'kinds':result['union_detection_kinds'],
        'new_model_calls':0,'new_native_calls':0,'read_only_replay_matches':True}))


if __name__=='__main__':main()
