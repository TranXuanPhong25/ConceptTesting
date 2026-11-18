"""Audit packaging-only repairs of authenticated historical naive responses."""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque, Counter
import inspect
import json
import os
from pathlib import Path
import shutil
import textwrap
import time

from final.src.modular.call_builder import CallBuilder, entry_function
from final.src.benchmarks.datasets import load_tasks, load_metadata
from final.src.runtime.contracts import parse_json
from .continue_bva_evaluation import read, save, digest, checksum, prepare, launch
from .export_cached_plain import export
from .compare_bva_naive import collect, partition


TYPES = {'str': str, 'int': int, 'float': float, 'bool': bool, 'list': list,
         'tuple': tuple, 'dict': dict, 'set': set}
ALIASES = {'List': 'list', 'Tuple': 'tuple', 'Dict': 'dict', 'Set': 'set'}


def type_name(node):
    if isinstance(node, ast.Subscript):
        node = node.value
    name = node.id if isinstance(node, ast.Name) else None
    name = ALIASES.get(name, name)
    return name if name in TYPES else None


def static_evidence(task, contract, parameter):
    """Only explicit annotations and unconditional contract requirements count."""
    function = entry_function(task['prompt'], task['entry_point'])
    annotation = next((arg.annotation for arg in function.args.posonlyargs + function.args.args
                      if arg.arg == parameter), None)
    evidence = []
    if type_name(annotation):
        evidence.append((type_name(annotation), 'instance', 'parameter annotation'))
    tree = ast.parse(textwrap.dedent(contract))
    if any(isinstance(node, ast.Name) and node.id == parameter and isinstance(node.ctx, ast.Store)
           for node in ast.walk(tree)):
        return []
    for statement in tree.body:
        if isinstance(statement, (ast.Return, ast.Raise)):
            break
        if isinstance(statement, ast.For) and isinstance(statement.iter, ast.Name) and statement.iter.id == parameter:
            evidence.append(('iterable', 'iterable', 'unconditional contract iteration'))
        if not isinstance(statement, ast.Assert):
            continue
        test = statement.test
        # Only the first conjunct is guaranteed to execute.
        while isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            test = test.values[0]
        if (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                and isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Name)
                and test.left.func.id == 'type' and len(test.left.args) == 1
                and isinstance(test.left.args[0], ast.Name) and test.left.args[0].id == parameter
                and type_name(test.comparators[0])):
            evidence.append((type_name(test.comparators[0]), 'exact', 'contract type equality'))
        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name):
            if (test.func.id == 'isinstance' and len(test.args) == 2
                    and isinstance(test.args[0], ast.Name) and test.args[0].id == parameter
                    and type_name(test.args[1])):
                evidence.append((type_name(test.args[1]), 'instance', 'contract isinstance'))
            if test.func.id == 'all' and len(test.args) == 1:
                argument = test.args[0]
                if isinstance(argument, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
                    iterator = argument.generators[0].iter
                    if isinstance(iterator, ast.Name) and iterator.id == parameter:
                        evidence.append(('iterable', 'iterable', 'unconditional contract all iteration'))
    return evidence


def compatible(value, evidence):
    if not evidence:
        return False
    for kind, mode, _ in evidence:
        if kind == 'iterable':
            if type(value) not in (list, tuple, dict, set, str):
                return False
        elif mode == 'exact':
            if type(value) is not TYPES[kind]:
                return False
        elif not isinstance(value, TYPES[kind]):
            return False
    return True


def repair_record(record, builder, evidence):
    parameters = list(builder.signature.parameters.values())
    if (len(parameters) != 1 or parameters[0].kind not in
            (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            or parameters[0].default is not inspect.Parameter.empty):
        return None, 'unsupported_or_ambiguous_signature'
    if not isinstance(record, dict) or not evidence:
        return None, 'no_static_type_proof'
    try:
        if any(not isinstance(record.get(key), str) or len(record[key]) > 16000 for key in ('args', 'kwargs')):
            return None, 'invalid_literal_fields'
        value, keywords = ast.literal_eval(record['args']), ast.literal_eval(record['kwargs'])
        if keywords != {}:
            return None, 'nonempty_or_invalid_kwargs'
        if isinstance(value, (tuple, list)):
            try:
                original = builder.signature.bind(*value)
            except TypeError:
                original = None
            if original is not None and compatible(original.arguments[parameters[0].name], evidence):
                return None, 'existing_binding_preserved'
        if not compatible(value, evidence):
            return None, 'candidate_not_proven_compatible'
        encoded = builder.build_values({parameters[0].name: value})
        assert ast.literal_eval(encoded['args'])[0] == value
        return {'args': encoded['args'], 'kwargs': encoded['kwargs'], 'concept_id': record.get('concept_id')}, 'rewrap_single_argument'
    except (SyntaxError, TypeError, ValueError, RecursionError, OverflowError):
        return None, 'unsupported_literal'


def repaired_batch(original_arm, response, builder, evidence):
    """One encoding per original raw slot; never append extra value slots."""
    if response.get('finish_reason') == 'length':
        return original_arm, [], {'truncated_response_not_reparsed': 1}
    try:
        rows = parse_json(response['text'])['inputs']
        if not isinstance(rows, list) or len(rows) > 20:
            raise ValueError('invalid input list')
    except (KeyError, IndexError, TypeError, ValueError, RecursionError):
        return original_arm, [], {'unparseable_response': 1}
    admitted = defaultdict(deque)
    for record in original_arm['inputs']:
        admitted[(record['args'], record['kwargs'])].append(record)
    result, changes, decisions = [], [], Counter()
    for index, row in enumerate(rows):
        key = (row.get('args'), row.get('kwargs')) if isinstance(row, dict) else (None, None)
        previous = admitted[key].popleft() if all(isinstance(value, str) for value in key) and admitted[key] else None
        repaired, reason = repair_record(row, builder, evidence)
        decisions[reason] += 1
        if repaired is not None:
            result.append(repaired)
            changes.append({'raw_index': index, 'original_raw_record': row, 'original_admitted_record': previous,
                            'repaired_record': repaired, 'static_proof': evidence, 'rule': reason})
        elif previous is not None:
            result.append(previous)
    if any(queue for queue in admitted.values()):
        raise ValueError('Raw slots do not account for the original admitted records')
    if len(result) > 20:
        raise ValueError('Repair exceeded original raw slot budget')
    return {**original_arm, 'inputs': result, 'packaging_repair_count': len(changes)}, changes, dict(decisions)


def build_export(directory):
    original_source = Path('final/out/v11_concept_inputs').resolve()
    authenticated = Path('final/out/naive_vs_soft_bva_full164_20261108_000951/plain_inputs/source_snapshot.json')
    authenticated_hashes = read(authenticated)['sources']
    baseline = directory / 'original_view'
    export(original_source, Path('final/out/boundary_soft_humaneval164_resume_20261107_195417').resolve(),
           Path('final/out/boundary_soft_humaneval164_evaluation_20261107_224720').resolve(), baseline)
    repaired = directory / 'repaired_view'
    shutil.copytree(baseline, repaired)
    sources = read(baseline / 'source_snapshot.json')
    ledger, receipts, decisions = {}, [], Counter()
    metadata = load_metadata()
    tasks = {task['task_id']: task for task in load_tasks()}
    for task_id in read(baseline / 'modular_manifest.json')['tasks']:
        number = task_id.split('/')[-1]
        batch = read(baseline / 'tasks' / number / 'inputs.json')
        changes = []
        raw_path = original_source / 'tasks' / number / 'calls/plain/response.json'
        if not batch.get('skip') and raw_path.exists():
            if authenticated_hashes.get(str(raw_path)) != checksum(raw_path):
                raise ValueError('Historical response authentication failed: ' + task_id)
            task = tasks[task_id]
            builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
            evidence = []
            if len(builder.signature.parameters) == 1:
                evidence = static_evidence(task, metadata[task_id]['contract'], next(iter(builder.signature.parameters)))
            arm, changes, counts = repaired_batch(batch['arms']['plain'], read(raw_path), builder, evidence)
            batch = {**batch, 'arms': {'plain': arm}}
            decisions.update(counts)
        destination = repaired / 'tasks' / number / 'inputs.json'
        save(destination, batch)
        ledger[task_id] = digest(batch)
        receipts.append({'task_id': task_id, 'changes': changes, 'source_response': str(raw_path) if raw_path.exists() else None,
                         'source_response_sha256': checksum(raw_path) if raw_path.exists() else None})
    freeze = read(repaired / 'generation_frozen.json')
    save(repaired / 'generation_frozen.json', {**freeze, 'inputs': ledger, 'inputs_sha256': digest(ledger)})
    manifest = read(repaired / 'modular_manifest.json')
    save(repaired / 'modular_manifest.json', {**manifest, 'protocol': 'frozen-naive-packaging-repair-1',
         'packaging_policy': 'one corrected encoding per original raw slot; no value changes or oracle-guided repair'})
    summary = {'changed_raw_slots': sum(len(row['changes']) for row in receipts),
               'changed_tasks': sum(bool(row['changes']) for row in receipts), 'decisions': dict(decisions), 'new_model_calls': 0}
    save(repaired / 'packaging_receipts.json', {'summary': summary, 'tasks': receipts})
    usage = read(repaired / 'export_receipts.json')
    batch_receipts = []
    for receipt in usage['batches']:
        task_id = receipt['task_id']
        number = task_id.split('/')[-1]
        before = read(baseline / 'tasks' / number / 'inputs.json')
        after = read(repaired / 'tasks' / number / 'inputs.json')
        batch_receipts.append({**receipt, 'original_projected_batch_sha256': receipt['exported_batch_sha256'],
            'exported_batch_sha256': ledger[task_id],
            'plain_inputs_unchanged': before.get('arms', {}).get('plain', {}).get('inputs') ==
                                      after.get('arms', {}).get('plain', {}).get('inputs')})
    save(repaired / 'export_receipts.json', {**usage, 'policy': manifest.get('packaging_policy', 'packaging-only repaired view'),
         'batches': batch_receipts, 'packaging_receipts': str(repaired / 'packaging_receipts.json')})
    archived = repaired / 'repair_controller.py'
    shutil.copyfile(__file__, archived)
    archived.chmod(0o444)
    for path in repaired.rglob('*'):
        if path.is_file() and path.name not in ('source_snapshot.json', 'status.json', '.worker.lock'):
            sources['sources'][str(path)] = checksum(path)
    sources['sources'][str(authenticated.resolve())] = checksum(authenticated)
    save(repaired / 'source_snapshot.json', sources)
    save(repaired / 'status.json', {'state': 'frozen_export', 'new_model_calls': 0})
    prepare(repaired, directory / 'evaluation', native_lock=Path('final/out/.boundary_native.lock').resolve())
    save(directory / 'repair_summary.json', summary)
    return summary


def finalize(directory):
    evaluation = directory / 'evaluation'
    while True:
        status = read(evaluation / 'status.json')
        if status['state'] == 'complete':
            break
        if status['state'] == 'interrupted':
            raise RuntimeError('Packaging evaluation interrupted; checkpoints preserved')
        if status.get('pid'):
            os.kill(status['pid'], 0)
        time.sleep(30)
    digest_record = read(evaluation / 'result_digest.json')
    if not digest_record['read_only_replay_matches'] or not digest_record['source_and_input_hashes_verified']:
        raise ValueError('Packaging evaluation integrity/replay failed')
    bva = collect(Path('final/out/boundary_soft_humaneval164_evaluation_20261107_224720').resolve(), 'boundary')
    old = collect(Path('final/out/naive_vs_soft_bva_full164_20261108_000951/evaluation').resolve(), 'plain')
    repaired = collect(evaluation, 'plain')
    if bva['targets'] != old['targets'] or old['targets'] != repaired['targets']:
        raise ValueError('Packaging diagnostic evaluated target sets differ')
    for key in ('settings', 'task_data_sha256', 'metadata_sha256', 'python', 'packages'):
        if bva['manifest'][key] != repaired['manifest'][key]:
            raise ValueError('Packaging scoring identity differs: ' + key)
    for name in ('reference_oracle', 'put_evaluation'):
        left = next(row for row in bva['manifest']['stages'] if row['name'] == name)
        right = next(row for row in repaired['manifest']['stages'] if row['name'] == name)
        if left != right:
            raise ValueError('Packaging scorer stage differs')
    targets = bva['targets']
    original_bva_only = bva['detected'] - old['detected']
    recovered = original_bva_only & repaired['detected']
    def identifiers(values):
        return [{'task_id': task, 'put_id': put} for task, put in sorted(values)]
    report = {'scope': 'Packaging-only diagnostic; generated values unchanged, encodings may be repaired',
        'repair_summary': read(directory / 'repair_summary.json'),
        'original_naive': old['summary'], 'repaired_naive': repaired['summary'], 'bva': bva['summary'],
        'bva_vs_repaired': partition(bva['detected'], repaired['detected'], targets),
        'original_bva_only_recovered': identifiers(recovered),
        'original_bva_only_remaining': identifiers(original_bva_only - repaired['detected']),
        'new_naive_detections': identifiers(repaired['detected'] - old['detected']),
        'old_naive_detections_lost': identifiers(old['detected'] - repaired['detected']),
        'stable_wrong_values': {'original_naive': len(old['value']), 'repaired_naive': len(repaired['value']), 'bva': len(bva['value'])},
        'new_model_calls': 0, 'read_only_replay_matches': True, 'source_hashes_verified': True,
        'evaluation': str(evaluation)}
    save(directory / 'comparison.json', report)
    counts = report['bva_vs_repaired']
    lines = ['# Historical naive packaging diagnostic', '',
        'Packaging-repaired baseline: generated literal values remain unchanged; only statically proven argument wrapping is corrected. This is separate from the original admitted-input baseline and the fresh matched batch trial.', '',
        '| Metric | Original naive | Packaging-repaired naive | Historical BVA |', '|---|---:|---:|---:|',
        f"| Detected PUTs | {old['summary']['detected']} | {repaired['summary']['detected']} | {bva['summary']['detected']} |",
        f"| Novel valid inputs | {old['summary']['valid_inputs']} | {repaired['summary']['valid_inputs']} | {bva['summary']['valid_inputs']} |",
        f"| Tasks with detection | {old['summary']['tasks_detected']} | {repaired['summary']['tasks_detected']} | {bva['summary']['tasks_detected']} |", '',
        f"Of the original {len(original_bva_only)} BVA-only PUTs, {len(recovered)} are now detected by the repaired naive inputs; {len(original_bva_only-repaired['detected'])} remain BVA-only relative to the repaired set.",
        f"BVA versus repaired naive: shared {counts['shared']}, BVA-only {counts['bva_only']}, naive-only {counts['naive_only']}, net BVA {counts['net_bva_minus_naive']:+d}.", '',
        f"Repair summary: {report['repair_summary']}.",
        f"Old naive detections lost: {len(report['old_naive_detections_lost'])}. Stable wrong-value witnesses: {report['stable_wrong_values']}.", '',
        'All 1,454 base-passing PUTs use the same historical full-two-repeat frozen scorer, corrected reference and 3 s timeout. No model calls, semantic value edits or oracle-guided repair selection. Raw-slot/proof receipts, authenticated original responses and the original baseline are preserved. Input/source hash checks and immutable replay passed.', '',
        'This diagnostic does not isolate boundary guidance, writer visibility or call budget. Exact recovered/remaining/new/lost identities are in comparison.json.']
    (directory / 'REPORT.md').write_text('\n'.join(lines)+'\n')
    prefix = Path('final/review/naive_packaging_audit_2026-11-08')
    save(prefix.with_suffix('.json'), report)
    prefix.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'report': str(prefix.with_suffix('.md')), 'recovered_original_bva_only': len(recovered),
                      'bva_vs_repaired': counts}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--watch', action='store_true', help='Only wait for existing CPU evaluation and write report')
    options = parser.parse_args()
    directory = options.artifacts.resolve()
    if options.watch:
        finalize(directory)
        return
    if directory.exists():
        raise ValueError('Use a new audit output directory')
    directory.mkdir(parents=True)
    summary = build_export(directory)
    if not options.prepare_only:
        summary['pid'] = launch(directory / 'evaluation')
    print(json.dumps({'artifacts': str(directory), **summary}), flush=True)


if __name__ == '__main__':
    main()
