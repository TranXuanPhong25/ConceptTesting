"""Opt-in dataset adapters, shared guidance and saved-input differential evaluation."""
from __future__ import annotations

import ast
import fcntl
import json
import math
from pathlib import Path

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.cohort import call_usage
from final.src.modular.call_builder import CallBuilder
from final.src.modular.response_json import load_response_json
from final.src.runtime.artifacts import digest, save
from .datasets import DatasetLoader
from .language_runtime import execute_program, serialize_call, equivalent


DEFAULTS = {'dataset':'mbpp', 'candidate_path':'', 'task_numbers':[],
    'arms':['plain','ep_bva_v2','decision_table_v2'], 'backend':'qwen',
    'model_name':'qwen3.5-27b-awq', 'inputs_per_task':20, 'completion_tokens':4096,
    'context_tokens':8192, 'temperature':.7, 'seed':314159, 'timeout_seconds':8}
ARM_NAMES = ('plain','ep_bva','decision_table','ep_bva_v2','decision_table_v2')


def normalize(values):
    if set(values) - DEFAULTS.keys():
        raise ValueError('Unknown adapter config field')
    config = {**DEFAULTS, **values}
    if config['dataset'] != 'mbpp':
        raise ValueError('Unknown adapter dataset')
    if config['backend'] not in ('qwen','vertex'):
        raise ValueError('Unknown adapter model backend')
    if not isinstance(config['model_name'], str) or not config['model_name'].strip() or len(config['model_name']) > 120:
        raise ValueError('Invalid model name')
    if not isinstance(config['candidate_path'], str):
        raise ValueError('candidate_path must be a file path string')
    arms = config['arms']
    if not isinstance(arms, list) or not arms or len(set(arms)) != len(arms) or set(arms) - set(ARM_NAMES):
        raise ValueError('Unknown or duplicate adapter arms')
    for field, low, high in (('inputs_per_task',1,200),('completion_tokens',128,32768),('context_tokens',512,131072),('seed',0,2147483483)):
        if type(config[field]) is not int or not low <= config[field] <= high:
            raise ValueError('Invalid ' + field)
    for field, low, high in (('temperature',0,2),('timeout_seconds',.1,60)):
        if type(config[field]) not in (int,float) or not math.isfinite(config[field]) or not low <= config[field] <= high:
            raise ValueError('Invalid ' + field)
    if config['completion_tokens']+128 >= config['context_tokens']:
        raise ValueError('Completion reserve leaves no prompt context')
    numbers = config['task_numbers']
    if not isinstance(numbers, list) or any(type(x) is not int for x in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError('Task numbers must be distinct integers')
    return config


def adapter_task(row):
    task = dict(row)
    if task['language'] == 'python':
        tree = ast.parse(task['canonical_solution'])
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == task['entry_point'])
        # Only interface metadata, never the reference implementation, is visible.
        stub = ast.FunctionDef(name=function.name, args=function.args, body=[ast.Pass()], decorator_list=[], returns=None)
        declaration = ast.unparse(ast.fix_missing_locations(stub))
        CallBuilder.for_source(declaration, task['entry_point'])
        task.update(declaration=declaration, reference_source=task['canonical_solution'], example_test=task['test'])
    else:
        task['reference_source'] = task['prompt'] + task['canonical_solution']
    return task


def tasks_for(config):
    rows = DatasetLoader('MBPP-py').load_tasks()
    available = {int(row['task_id'].split('/')[1]): row for row in rows}
    selected = config['task_numbers'] or sorted(available)
    if set(selected) - available.keys():
        raise ValueError('Selected task is absent from the dataset split')
    return [adapter_task(available[number]) for number in selected]


def load_candidates(path, tasks):
    known_ids = {task['task_id'] for task in tasks}
    result, seen = {}, set()
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get('task_id'), str):
            raise ValueError('Invalid candidate task_id')
        task_id = row['task_id']
        if task_id not in known_ids:
            # Allow a full dataset's frozen file with a requested task subset.
            continue
        identifier = row.get('id')
        if type(identifier) not in (int,str) or not str(identifier) or not str(identifier).replace('_','').isalnum():
            raise ValueError('Invalid candidate id')
        identifier = str(identifier)
        if (task_id, identifier) in seen:
            raise ValueError('duplicate candidate id')
        seen.add((task_id, identifier))
        if not isinstance(row.get('code'), str) or not row['code'].strip() or len(row['code']) > 100000:
            raise ValueError('Invalid candidate source')
        if row.get('source_format','complete') != 'complete':
            raise ValueError('Candidates must contain complete source, including signature/class/imports')
        result.setdefault(task_id, []).append({'id':identifier, 'code':row['code']})
    if not result:
        raise ValueError('No candidates for the selected task set')
    return result


def preview(values):
    config = normalize(values)
    tasks = tasks_for(config)
    cohort = load_candidates(config['candidate_path'], tasks) if config['candidate_path'] else None
    call_cap = len(tasks) * len(config['arms'])
    return {'config':config, 'requested_task_count':len(tasks), 'task_ids':[task['task_id'] for task in tasks],
        'cohort_status':'supplied' if cohort is not None else 'pending',
        'candidate_count':sum(map(len, cohort.values())) if cohort is not None else None,
        'base_pass_put_count':None, 'logical_call_cap':call_cap,
        'transport_attempt_cap':3*call_cap,
        'completion_token_cap':call_cap*config['completion_tokens'],
        'input_budget_unit':'per task per arm', 'coverage':'pending', 'verified_bugs':'pending',
        'workload_calls':0}


def messages_for(task, programs, arm_name, budget):
    from final.src.modular.arms import selected_arms
    from final.src.modular.arms.classical import with_catalogue_output_contract
    arm = selected_arms([arm_name])[0]
    common = (f'Generate up to {budget} distinct new calls exposing specification violations. '
        'Inputs only; expected outputs come from a separate reference after freeze. '
        'Follow the specification and public examples. Never assume the implementations are correct. '
        'Return JSON: {"inputs":[{"arguments":{}}]}.\narguments maps exact parameter names to JSON values. '
        'No code or expressions in values. Respect language types and joint preconditions.\n'
        'Keep sequences/strings modest (normally <=30 items); generation caps are not specification boundaries.\n'
        f'LANGUAGE: {task["language"]}\nSPECIFICATION:\n{task["prompt"]}\nDECLARATION:\n{task["declaration"]}\n'
        f'PUBLIC EXAMPLES:\n{task["example_test"]}\nBASE-PASSING PUTS:\n' + json.dumps(programs, ensure_ascii=False))
    if getattr(arm, 'sections', ()):
        common = with_catalogue_output_contract(common, arm.sections)
    return [{'role':'system', 'content':f'Generate valid {task["language"]} function inputs as JSON.'},
            {'role':'user', 'content':common + '\n' + arm.build_guidance({'common':common})}]


def decode(task, response, budget):
    accepted, rejected, seen = [], [], set()
    try:
        document, _ = load_response_json(response.text)
        records = document['inputs']
        if not isinstance(records, list):
            raise ValueError('inputs must be a list')
    except (ValueError, TypeError, KeyError):
        return {'inputs':[], 'rejected':[{'reason':'invalid_response'}], 'catalogue':None}
    for index, row in enumerate(records[:budget]):
        try:
            arguments = row['arguments']
            if task['language']=='python':
                CallBuilder.for_source(task['declaration'], task['entry_point']).build(arguments)
            else:
                serialize_call(task['declaration'], arguments, task['language'])
            key = digest(arguments)
            if key in seen:
                raise ValueError('duplicate input')
            seen.add(key)
            accepted.append({'arguments':arguments, 'covers':row.get('covers')})
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            rejected.append({'index':index, 'reason':str(error)[:200]})
    return {'inputs':accepted, 'rejected':rejected, 'catalogue':document.get('catalogue'),
            'catalogue_semantics':'pending', 'membership':'pending'}


def input_union(batches):
    union, indices, keys = [], {}, []
    for arm, batch in batches.items():
        indices[arm] = []
        for record in batch['inputs']:
            key = digest(record['arguments'])
            if key not in keys:
                union.append(record['arguments'])
                keys.append(key)
            indices[arm].append(keys.index(key))
    return union, indices


def run_benchmark(tasks, cohort, store, values, *, calls=None, executor=None):
    from final.src.modular.calls import CachedModelCalls
    config = normalize(values)
    executor = executor or execute_program
    if store.read_only and calls is not None:
        raise ValueError('Replay cannot accept live calls')
    calls = calls or CachedModelCalls(store)
    manifest = {'protocol':'dataset-adapters-v1', 'tasks_sha256':digest(tasks), 'cohort_sha256':digest(cohort),
                'config':config, 'oracle':'stable reference disagreement; specification admission pending', 'coverage':'pending'}
    store.write('adapter_manifest.json', manifest)
    prepared = []
    for task in tasks:
        number = int(task['task_id'].split('/')[1]); prefix = f'tasks/{number}'
        programs = cohort.get(task['task_id'], [])
        passing = []
        for program in programs:
            baseline = store.load_or_compute(f'{prefix}/base/{program["id"]}.json',
                lambda program=program: executor(task, program['code'], [], timeout=config['timeout_seconds'], base=True))
            if baseline['status'] in ('unsupported_environment','infrastructure_error'):
                raise RuntimeError(baseline['status'] + ': ' + task['task_id'])
            if baseline['status']=='ok' and baseline['tests']==[{'status':'ok'}]:
                passing.append(program)
        if not passing:
            prepared.append((task, [], None))
            continue
        if store.exists(prefix+'/inputs.json'):
            batches = store.read(prefix+'/inputs.json')
        else:
            if store.read_only:
                raise FileNotFoundError(prefix+'/inputs.json')
            packets = {arm:messages_for(task, passing, arm, config['inputs_per_task']) for arm in config['arms']}
            if max((calls.token_count(messages) for messages in packets.values()), default=0) + config['completion_tokens'] + 128 >= config['context_tokens']:
                batches = {'skip':'prompt_too_large'}
            else:
                batches = {}
                for arm in config['arms']:
                    response = calls.complete(number, arm, packets[arm], temperature=config['temperature'],
                        max_tokens=config['completion_tokens'], seed=config['seed']+number)
                    batches[arm] = decode(task, response, config['inputs_per_task'])
            store.write(prefix+'/inputs.json', batches)
        prepared.append((task, passing, batches))
        if not store.read_only:
            save(store.path('progress.json'), {'phase':'generation', 'task_id':task['task_id'], 'prepared_tasks':len(prepared), 'total_tasks':len(tasks)})
    store.write('generation_frozen.json', {'cohort_sha256':digest(cohort),
        'inputs':{task['task_id']:digest(batches) for task, _, batches in prepared},
        'model_artifacts':artifact_hashes(store, ('tasks/*/calls/*/*.json',))})
    results = []
    for task, programs, batches in prepared:
        number = int(task['task_id'].split('/')[1]); prefix = f'tasks/{number}'
        if not programs or batches.get('skip'):
            result = {'task_id':task['task_id'], 'skip':'no_base_pass' if not programs else batches['skip']}
        elif task['task_id'] == 'CPP/32':
            result = {'task_id':task['task_id'], 'skip':'non_unique_root_oracle_not_supported'}
        else:
            union, indices = input_union(batches)
            def reference_execution():
                return executor(task, task['reference_source'], union, timeout=config['timeout_seconds']) if union else {'status': 'ok', 'tests': []}
            reference = [store.load_or_compute(f'{prefix}/reference_{repeat}.json',
                reference_execution) for repeat in range(2)]
            if any(r['status'] != 'ok' for r in reference):
                raise RuntimeError('Reference compilation failed for ' + task['task_id'])
            valid = [i for i in range(len(union)) if all(r['tests'][i]['status']=='ok' for r in reference)
                and digest(reference[0]['tests'][i]['value']) == digest(reference[1]['tests'][i]['value'])]
            outcomes = {}
            retained = [union[i] for i in valid]
            for program in programs:
                repeats = [store.load_or_compute(f'{prefix}/evaluation/{program["id"]}_{repeat}.json',
                    lambda: executor(task, program['code'], retained, timeout=config['timeout_seconds'])
                        if retained else {'status': 'ok', 'tests': []}) for repeat in range(2)]
                if any(r['status'] != 'ok' for r in repeats):
                    raise RuntimeError('PUT compilation/infrastructure changed after base pass')
                failures = []
                for local, index in enumerate(valid):
                    expected = reference[0]['tests'][index]['value']
                    if all(r['tests'][local]['status'] != 'ok' or not equivalent(r['tests'][local]['value'], expected) for r in repeats):
                        failures.append(index)
                outcomes[program['id']] = failures
            arms = {arm:{'valid_inputs':len(set(selected)&set(valid)),
                'detected':sum(bool(set(selected)&set(failing)) for failing in outcomes.values())} for arm, selected in indices.items()}
            result = {'task_id':task['task_id'], 'base_pass':len(programs), 'arms':arms,
                'reference_rejected':len(union)-len(valid), 'outcomes':outcomes, 'arm_indices':indices,
                'validity':'reference-executable-only; specification admission pending', 'base_duplicate_filter':'pending'}
        store.write(prefix+'/result.json', result); results.append(result)
        if not store.read_only:
            save(store.path('progress.json'), {'phase':'evaluation','evaluated_or_skipped_tasks':len(results),'total_tasks':len(tasks)})
    totals = {arm:{'valid_inputs':0,'detected':0,'tasks_detected':0} for arm in config['arms']}
    for result in results:
        for arm, metrics in result.get('arms', {}).items():
            for key in ('valid_inputs','detected'):
                totals[arm][key] += metrics[key]
            totals[arm]['tasks_detected'] += metrics['detected'] > 0
    summary = {'dataset':config['dataset'], 'arms':totals, 'tasks':len(tasks), 'config':config,
        'evaluated_base_pass':sum(r.get('base_pass',0) for r in results), 'skips':[r for r in results if 'skip' in r],
        'tester_calls':call_usage(store.directory), 'coverage':'pending', 'verified_bugs':'pending',
        'metric_scope':'confirmed reference disagreement; specification validity unverified'}
    store.write('result_digest.json', summary)
    store.write('execution_frozen.json', artifact_hashes(store, ('tasks/*/base/*.json','tasks/*/reference_*.json',
        'tasks/*/evaluation/*.json','tasks/*/result.json')))
    if not store.read_only:
        store.path('REPORT.md').write_text(render(summary))
    return summary


def artifact_hashes(store, patterns):
    from .datasets import dataset_sha256
    return {str(p.relative_to(store.directory)):dataset_sha256(p)
            for pattern in patterns for p in sorted(store.directory.glob(pattern))}


def render(summary):
    return ('# MBPP\n\nKết quả là số PUT có sai khác với reference qua hai lần execution; '
        ''
        'Full natural-language spec completeness, coverage, semantic grounding và lọc base duplicates còn pending.\n\n'
        f"Dataset: {summary['dataset']}; {summary['tasks']} task; {summary['evaluated_base_pass']} base-pass PUT.\n\n"
        'Mỗi arm có input budget theo task; valid_inputs đếm input memberships, detected đếm PUT. '
        'Không suy gain từ tổng input khác nhau.\n\n```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n')
