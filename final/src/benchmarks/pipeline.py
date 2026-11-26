"""Opt-in dataset adapters, shared guidance and saved-input differential evaluation."""
from __future__ import annotations

import ast
import fcntl
import json
import math
from pathlib import Path

from final.src.models import OPENROUTER_DEFAULT_MODEL
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.black_box import DecisionTableArm, EpBvaArm
from final.src.modular.cohort import call_usage
from final.src.modular.call_builder import CallBuilder
from final.src.modular.context import DEFAULT_CONTEXT_TOKENS, DEFAULT_INPUT_TOKENS
from final.src.modular.response_json import load_response_json
from final.src.runtime.artifacts import digest, save
from final.src.runtime.contracts import bound_call_key
from .datasets import DatasetLoader
from .language_runtime import execute_program, equivalent


DEFAULTS = {'dataset':'mbpp', 'candidate_path':'', 'task_numbers':[],
    'arms':['plain','ep_bva_single','decision_table_single'], 'backend':'qwen',
    'model_name':'qwen3.5-27b-awq', 'inputs_per_task':20, 'completion_tokens':DEFAULT_INPUT_TOKENS,
    'context_tokens':DEFAULT_CONTEXT_TOKENS, 'temperature':.7, 'seed':314159, 'timeout_seconds':8,
    'tool_runs_dir':''}
ARM_NAMES = ('plain','ep_bva_single','decision_table_single','control_flow','control_flow_4tool')
CONTROL_FLOW_ARMS = ('control_flow','control_flow_4tool')


def normalize(values):
    if set(values) - DEFAULTS.keys():
        raise ValueError('Unknown adapter config field')
    config = {**DEFAULTS, **values}
    if config['dataset'] != 'mbpp':
        raise ValueError('Unknown adapter dataset')
    if config['backend'] not in ('qwen','vertex','openrouter'):
        raise ValueError('Unknown adapter model backend')
    if config['backend'] == 'openrouter' and 'model_name' not in values:
        config['model_name'] = OPENROUTER_DEFAULT_MODEL
    if not isinstance(config['model_name'], str) or not config['model_name'].strip() or len(config['model_name']) > 120:
        raise ValueError('Invalid model name')
    if not isinstance(config['candidate_path'], str):
        raise ValueError('candidate_path must be a file path string')
    if not isinstance(config['tool_runs_dir'], str):
        raise ValueError('tool_runs_dir must be a directory path string')
    arms = config['arms']
    if not isinstance(arms, list) or not arms or len(set(arms)) != len(arms) or set(arms) - set(ARM_NAMES):
        raise ValueError('Unknown or duplicate adapter arms')
    if config['tool_runs_dir'].strip() and 'control_flow_4tool' not in arms:
        raise ValueError('tool_runs_dir requires control_flow_4tool arm')
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
    tree = ast.parse(task['canonical_solution'])
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == task['entry_point'])
    # Only interface metadata, never the reference implementation, is visible.
    stub = ast.FunctionDef(name=function.name, args=function.args, body=[ast.Pass()], decorator_list=[], returns=None)
    declaration = ast.unparse(ast.fix_missing_locations(stub))
    CallBuilder.for_source(declaration, task['entry_point'])
    task.update(declaration=declaration, reference_source=task['canonical_solution'], example_test=task['test'])
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
    has_dynamic_cf = any(arm in CONTROL_FLOW_ARMS for arm in config['arms'])
    call_cap = 'pending' if has_dynamic_cf else len(tasks) * len(config['arms'])
    return {'config':config, 'requested_task_count':len(tasks), 'task_ids':[task['task_id'] for task in tasks],
        'cohort_status':'supplied' if cohort is not None else 'pending',
        'candidate_count':sum(map(len, cohort.values())) if cohort is not None else None,
        'base_pass_put_count':None, 'logical_call_cap':call_cap,
        'transport_attempt_cap':'pending' if has_dynamic_cf else 3*call_cap,
        'completion_token_cap':'pending' if has_dynamic_cf else call_cap*config['completion_tokens'],
        'input_budget_unit':'per task per arm', 'coverage':'pending', 'verified_bugs':'pending',
        'workload_calls':0}


def _mbpp_prompt(task):
    tree = ast.parse(task['declaration'])
    function = tree.body[0]
    function.body = [ast.Expr(value=ast.Constant(task['prompt']))]
    return ast.unparse(ast.fix_missing_locations(tree)) + '\n'


def _encode_argument_value(value, depth=0):
    if depth > 8:
        raise ValueError('argument_nesting_limit')
    if type(value) is bool or value is None or type(value) in (int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('nonfinite_float')
        return value
    if type(value) is list:
        return [_encode_argument_value(item, depth + 1) for item in value]
    if type(value) is tuple:
        return {'__python_type__':'tuple', 'items':[_encode_argument_value(item, depth + 1) for item in value]}
    if type(value) is set:
        ordered = sorted(value, key=lambda item: (type(item).__name__, repr(item)))
        return {'__python_type__':'set', 'items':[_encode_argument_value(item, depth + 1) for item in ordered]}
    if type(value) is dict:
        if '__python_type__' in value or any(type(key) is not str for key in value):
            raise ValueError('unsupported_dict_key')
        return {key:_encode_argument_value(item, depth + 1) for key, item in value.items()}
    raise ValueError('unsupported_argument_value')


def _call_to_arguments(builder, call):
    args = ast.literal_eval(call['args'])
    kwargs = ast.literal_eval(call['kwargs'])
    bound = builder.signature.bind(*args, **kwargs)
    bound.apply_defaults()
    arguments = {name:_encode_argument_value(value) for name, value in bound.arguments.items()}
    builder.build(arguments)
    return arguments


def _trace_mbpp_base(task, program, *, timeout, seed):
    from .PUT_generation import run_base_tests
    return run_base_tests(task, program, timeout=timeout, seed=seed)


def _generate_control_flow_arms(
    task,
    passing,
    store,
    config,
    cf_arms,
    *,
    calls,
    base_tracer=None,
    arm_factories=None,
    default_tool_runs_dir=None,
):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowFourToolArm
    from final.src.modular.context import PipelineSettings, TaskContext

    number = int(task['task_id'].split('/')[1])
    prefix = f'tasks/{number}'
    tracer = base_tracer or _trace_mbpp_base
    traced_programs = []
    for program in passing:
        traced = store.load_or_compute(
            f'{prefix}/base_trace/{program["id"]}.json',
            lambda program=program: tracer(task, program, timeout=config['timeout_seconds'], seed=config['seed']),
        )
        base_entry = {
            'status': 'pass',
            'calls': traced.get('calls', []),
            'input_keys': traced.get('input_keys', []),
        }
        if traced.get('status') == 'pass' and isinstance(traced.get('coverage'), dict):
            base_entry['coverage'] = traced['coverage']
        traced_programs.append({'id': program['id'], 'code': program['code'], 'base': base_entry})

    public_task = {
        'task_id': task['task_id'],
        'entry_point': task['entry_point'],
        'prompt': _mbpp_prompt(task),
        'test': task['example_test'],
    }
    cf_settings = PipelineSettings(
        input_budget=config['inputs_per_task'],
        input_tokens=config['completion_tokens'],
        input_temperature=config['temperature'],
        input_seed=config['seed'],
        reference_seed=config['seed'],
        context_tokens=config['context_tokens'],
        timeout_seconds=config['timeout_seconds'],
    )
    cf_context = TaskContext(
        public_task,
        {'contract': ''},
        store,
        cf_settings,
        calls=calls,
        cohort_task={'programs': traced_programs},
        packet={'visible_put_ids': [p['id'] for p in traced_programs], 'common': ''},
    )
    tool_dir = config.get('tool_runs_dir') or default_tool_runs_dir or None
    default_factories = {
        'control_flow': ControlFlowArm,
        'control_flow_4tool': lambda: ControlFlowFourToolArm(tool_runs_dir=tool_dir),
    }
    factories = {**default_factories, **(arm_factories or {})}
    builder = CallBuilder.for_source(task['declaration'], task['entry_point'])
    batches = {}
    for arm_name in cf_arms:
        raw_batch = factories[arm_name]().run(cf_context)
        accepted, rejected, seen = [], [], set()
        for index, row in enumerate(raw_batch.get('inputs', [])):
            try:
                arguments = _call_to_arguments(builder, row)
                key = bound_call_key(arguments)
                if key in seen:
                    continue
                seen.add(key)
                item = {
                    'arguments': arguments,
                    'call': {'args': row['args'], 'kwargs': row['kwargs']},
                }
                if 'sources' in row:
                    item['sources'] = row['sources']
                accepted.append(item)
            except (ValueError, KeyError, TypeError, SyntaxError, RecursionError) as error:
                rejected.append({'index': index, 'reason': str(error)[:200]})
        batch_record = {
            'inputs': accepted,
            'rejected': rejected,
            'status': raw_batch.get('status', 'generated'),
            'concepts': len(raw_batch.get('concepts', [])),
            'rounds': len(raw_batch.get('rounds', [])),
            'target_coverage': raw_batch.get('target_coverage', {}),
            'suite_input_budget': raw_batch.get('suite_input_budget'),
            'errors': raw_batch.get('errors', []),
        }
        if 'tool4_prior_summary' in raw_batch:
            batch_record['tool4_prior_summary'] = raw_batch['tool4_prior_summary']
        batches[arm_name] = batch_record
    return batches


def _summarize_control_flow_batches(prepared, arm_name):
    batches = [
        batches[arm_name]
        for _, programs, batches in prepared
        if programs and batches and not batches.get('skip') and arm_name in batches
    ]
    coverage = [batch.get('target_coverage', {}) for batch in batches]
    result = {
        'concepts': sum(batch.get('concepts', 0) for batch in batches),
        'model_calls': sum(batch.get('rounds', 0) for batch in batches),
        'observed_targets': sum(row.get('covered') or 0 for row in coverage),
        'selected_targets': sum(row.get('total') or 0 for row in coverage),
        'coverage_pending_tasks': sum(row.get('total') is None for row in coverage),
    }
    if arm_name == 'control_flow_4tool':
        prior_rows = [batch.get('tool4_prior_summary', {}) for batch in batches]
        before_values = [row.get('base_targets_before_4tool') for row in prior_rows]
        residual_values = [row.get('residual_targets_after_4tool') for row in prior_rows]
        known_before = bool(before_values) and all(type(v) is int for v in before_values)
        known_residual = bool(residual_values) and all(type(v) is int for v in residual_values)
        result.update(
            prior_inputs_loaded=sum(row.get('prior_inputs_traced', 0) for row in prior_rows),
            base_targets_before_4tool=sum(before_values) if known_before else None,
            residual_targets_after_4tool=sum(residual_values) if known_residual else None,
            targets_eliminated_by_4tool=(
                sum(row.get('targets_eliminated_by_4tool') or 0 for row in prior_rows)
                if known_before and known_residual else None
            ),
            tasks_closed_by_4tool=sum(bool(row.get('closed_by_4tool')) for row in prior_rows),
            tasks_with_residual_gaps=sum(
                type(row.get('residual_targets_after_4tool')) is int
                and row['residual_targets_after_4tool'] > 0
                for row in prior_rows
            ),
        )
    return result


def messages_for(task, programs, arm_name, budget):
    guidance = {
        'plain': '',
        'ep_bva_single': EpBvaArm.guidance,
        'decision_table_single': DecisionTableArm.guidance,
    }[arm_name]
    output = 'Return JSON with an inputs array of objects with named arguments.'
    if guidance:
        output += ' Include a compact catalogue of the classes, boundaries, or rules you used.'
    return [
        {'role': 'system', 'content': f'Generate valid {task["language"]} function inputs as JSON.'},
        {'role': 'user', 'content': (
            f'Generate up to {budget} distinct new calls exposing specification violations. '
            'Follow the specification and public examples. Never assume the implementations are correct. '
            f'{output} Do not include expected outputs.\n'
            'The arguments object maps exact parameter names to JSON values. '
            'No code or expressions in values. Respect language types and joint preconditions.\n'
            'Keep sequences/strings modest (normally <=30 items); generation caps are not specification boundaries.\n'
            f'LANGUAGE: {task["language"]}\nSPECIFICATION:\n{task["prompt"]}\nDECLARATION:\n{task["declaration"]}\n'
            f'PUBLIC EXAMPLES:\n{task["example_test"]}\nBASE-PASSING PUTS:\n' + json.dumps(programs, ensure_ascii=False)
            + '\n' + guidance
        )},
    ]


def decode(task, response, budget):
    accepted, rejected, seen = [], [], set()
    try:
        document, _ = load_response_json(response.text)
        records = document['inputs']
        if not isinstance(records, list):
            raise ValueError('inputs must be a list')
    except (ValueError, TypeError, KeyError):
        return {'inputs':[], 'rejected':[{'reason':'invalid_response'}], 'catalogue':None}
    # Validate calls against the task signature before deduplicating within the response.
    builder = CallBuilder.for_source(task['declaration'], task['entry_point'])
    for index, row in enumerate(records[:budget]):
        try:
            arguments = row['arguments']
            builder.build(arguments)
            key = bound_call_key(arguments)
            if key in seen:
                raise ValueError('duplicate input')
            seen.add(key)
            accepted.append({'arguments':arguments, 'covers':row.get('covers')})
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            rejected.append({'index':index, 'reason':str(error)[:200]})
    return {'inputs':accepted, 'rejected':rejected, 'catalogue':document.get('catalogue'),
            'catalogue_semantics':'pending', 'membership':'pending'}


def input_union(batches, *, input_field="arguments"):
    union, indices, keys = [], {}, {}
    for arm, batch in batches.items():
        indices[arm] = []
        for record in batch['inputs']:
            key = bound_call_key(record[input_field])
            if key not in keys:
                keys[key] = len(union)
                union.append(record[input_field])
            indices[arm].append(keys[key])
    return union, indices


def evaluate_task(
    task,
    programs,
    batches,
    store,
    *,
    timeout,
    executor=execute_program,
    input_field='arguments',
):
    """Score frozen inputs using the two-repeat MBPP reference and PUT receipts."""
    number = int(task['task_id'].split('/')[1])
    prefix = f'tasks/{number}'
    # Run each distinct input once per repeat and keep its arm memberships for attribution.
    union, indices = input_union(batches, input_field=input_field)
    def reference_execution():
        return executor(task, task['reference_source'], union, timeout=timeout) if union else {'status': 'ok', 'tests': []}
    reference = [store.load_or_compute(f'{prefix}/reference_{repeat}.json',
        reference_execution) for repeat in range(2)]
    if any(r['status'] != 'ok' for r in reference):
        raise RuntimeError('Reference compilation failed for ' + task['task_id'])
    # An input needs two successful reference runs with the same value to supply an oracle.
    valid = [i for i in range(len(union)) if all(r['tests'][i]['status']=='ok' for r in reference)
        and digest(reference[0]['tests'][i]['value']) == digest(reference[1]['tests'][i]['value'])]
    outcomes = {}
    retained = [union[i] for i in valid]
    # Count a PUT failure only when both repeats fail or disagree with the oracle.
    for program in programs:
        repeats = [store.load_or_compute(f'{prefix}/evaluation/{program["id"]}_{repeat}.json',
            lambda: executor(task, program['code'], retained, timeout=timeout)
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
    return {'task_id':task['task_id'], 'base_pass':len(programs), 'arms':arms,
        'reference_rejected':len(union)-len(valid), 'outcomes':outcomes, 'arm_indices':indices,
        'validity':'reference-executable-only; specification admission pending', 'base_duplicate_filter':'pending'}


def run_benchmark(
    tasks,
    cohort,
    store,
    values,
    *,
    calls=None,
    executor=None,
    base_tracer=None,
    arm_factories=None,
    default_tool_runs_dir=None,
):
    if store.read_only:
        if calls is not None:
            raise ValueError('Replay cannot accept live calls')
        return store.read('result_digest.json')
    config = normalize(values)
    executor = executor or execute_program
    manifest = {
        'protocol': 'dataset-adapters-v1',
        'config': config,
        'oracle': 'stable reference disagreement; specification admission pending',
    }
    store.write('adapter_manifest.json', manifest)
    standard_arms = [arm for arm in config['arms'] if arm not in CONTROL_FLOW_ARMS]
    cf_arms = [arm for arm in config['arms'] if arm in CONTROL_FLOW_ARMS]
    prepared = []
    for task in tasks:
        number = int(task['task_id'].split('/')[1]); prefix = f'tasks/{number}'
        programs = cohort.get(task['task_id'], [])
        passing = []
        # Limit input generation and evaluation to PUTs that pass the original tests.
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
        # Reuse saved inputs on resume and replay. Generate only when there is no saved batch.
        if store.exists(prefix+'/inputs.json'):
            batches = store.read(prefix+'/inputs.json')
        else:
            if calls is None:
                raise RuntimeError('MBPP generation needs model calls or saved inputs')
            batches = {}
            if standard_arms:
                budget = config['inputs_per_task']
                packets = {arm: messages_for(task, passing, arm, budget) for arm in standard_arms}
                # Reserve completion space for every standard arm before making any calls for the task.
                if max((calls.token_count(messages) for messages in packets.values()), default=0) + config['completion_tokens'] + 128 >= config['context_tokens']:
                    if not cf_arms:
                        batches = {'skip':'prompt_too_large'}
                    else:
                        for arm in standard_arms:
                            batches[arm] = {'inputs':[], 'rejected':[], 'status':'prompt_too_large'}
                else:
                    for arm in standard_arms:
                        response = calls.complete(
                            number,
                            arm,
                            packets[arm],
                            temperature=config['temperature'],
                            max_tokens=config['completion_tokens'],
                            seed=config['seed'] + number,
                        )
                        batches[arm] = decode(task, response, budget)
            if cf_arms and not batches.get('skip'):
                cf_batches = _generate_control_flow_arms(
                    task,
                    passing,
                    store,
                    config,
                    cf_arms,
                    calls=calls,
                    base_tracer=base_tracer,
                    arm_factories=arm_factories,
                    default_tool_runs_dir=default_tool_runs_dir,
                )
                batches.update(cf_batches)
            if not batches.get('skip'):
                batches = {arm: batches[arm] for arm in config['arms']}
            store.write(prefix+'/inputs.json', batches)
        prepared.append((task, passing, batches))
        save(store.path('progress.json'), {
            'phase': 'generation', 'task_id': task['task_id'], 'prepared_tasks': len(prepared), 'total_tasks': len(tasks),
        })
    # The evaluation loop only starts after all input batches are saved.
    results = []
    for task, programs, batches in prepared:
        number = int(task['task_id'].split('/')[1]); prefix = f'tasks/{number}'
        if not programs or batches.get('skip'):
            result = {'task_id':task['task_id'], 'skip':'no_base_pass' if not programs else batches['skip']}
        else:
            result = evaluate_task(
                task,
                programs,
                batches,
                store,
                timeout=config['timeout_seconds'],
                executor=executor,
            )
        store.write(prefix+'/result.json', result); results.append(result)
        save(store.path('progress.json'), {
            'phase': 'evaluation', 'evaluated_or_skipped_tasks': len(results), 'total_tasks': len(tasks),
        })
    # Aggregate input memberships and detected PUTs per arm across tasks.
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
    for cf_arm in cf_arms:
        summary[cf_arm] = _summarize_control_flow_batches(prepared, cf_arm)
    store.write('result_digest.json', summary)
    store.path('REPORT.md').write_text(render(summary))
    return summary


def render(summary):
    return ('# MBPP\n\nKết quả là số PUT có sai khác với reference qua hai lần execution; '
        ''
        'Full natural-language spec completeness, coverage, semantic grounding và lọc base duplicates còn pending.\n\n'
        f"Dataset: {summary['dataset']}; {summary['tasks']} task; {summary['evaluated_base_pass']} base-pass PUT.\n\n"
        'Mỗi arm có input budget theo task; valid_inputs đếm input memberships, detected đếm PUT. '
        'Không suy gain từ tổng input khác nhau.\n\n```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n')
