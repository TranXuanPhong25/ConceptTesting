"""Format-only repair of historical naive inputs on top of the packaging-repaired view.

No model call. Starts from the authenticated original naive responses and keeps
every packaging-repaired or originally admitted input. Raw slots that were still
lost only because of output format are recovered when exactly one reading exists:

- response level: strict JSON, then the shared Python-literal fallback, then
  per-record salvage of a response whose JSON is broken in some records;
- record level: a raw newline/tab/CR inside a string literal (JSON-decoded escape),
  the kwargs field copied into the args literal (``('x', 'kwargs': '{}')``), one
  stray trailing quote, garbled key quoting ``{"args':'...','kwargs":"{}"``,
  and argument wrapping: when the args literal does not bind as positional
  arguments but binds as one single argument, it is wrapped (``'a'`` -> ``('a',)``),
  unless static type evidence (annotation/contract) contradicts the wrapped value.

Not format, so still rejected: expressions (``2 * 3``, ``float('inf')``,
``'a' * 1000``), non-finite values, garbled quoting with no single reading, and
truncated responses (``finish_reason=length``, the same rule as Direct/Soft).
Values are never changed or chosen by looking at oracle outcomes.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
import re
from pathlib import Path
import shutil

from final.src.modular.call_builder import CallBuilder
from final.src.benchmarks.datasets import load_tasks, load_metadata
from final.src.modular.response_json import load_response_json
from final.src.runtime.contracts import parse_json
from .continue_bva_evaluation import read, save, digest, checksum, prepare, launch
from .repair_cached_plain import repair_record, static_evidence, compatible

ROOT = Path(__file__).resolve().parents[3]
SOURCE_AUDIT = ROOT / 'final/out/naive_packaging_audit_20261108_0200'
ORIGINAL_RESPONSES = ROOT / 'final/out/v11_concept_inputs'
INPUT_BUDGET = 20
CONTROL_ESCAPES = {'\n': '\\n', '\r': '\\r', '\t': '\\t'}


RECORD_BOUNDARY = re.compile(r'\}\s*,\s*(?=\{\s*"args)')
# A record whose key quoting is garbled but whose args payload has one reading:
# {"args':'"xyzyx", "z"','kwargs":"{}",...}
GARBLED_ARGS_KEY = re.compile(r'^\{"args\':\'(?P<args>.*)\',\'kwargs":"(?P<kwargs>\{\})"')
# The model copied the kwargs field into the args literal: "('x', 'kwargs': '{}')"
EMBEDDED_KWARGS = re.compile(r", 'kwargs': '\{\}'\)$")


def split_records(text):
    """Split the "inputs" list body at record boundaries that start a new {"args record."""
    start = text.find('[', text.find('"inputs"'))
    end = text.rfind(']')
    if start < 0 or end <= start:
        return []
    pieces = RECORD_BOUNDARY.split(text[start + 1:end].strip())
    records = []
    for index, piece in enumerate(pieces):
        records.append(piece if index == len(pieces) - 1 else piece + '}')
    return [record for record in records if record]


def decode_record(record_text):
    """Return (row, rule) for one record text, or (None, 'undecodable_record')."""
    try:
        row = load_response_json(record_text)[0]
        if isinstance(row, dict):
            return row, None
    except (TypeError, ValueError, RecursionError):
        pass
    match = GARBLED_ARGS_KEY.match(record_text)
    if match:
        return {'args': match.group('args'), 'kwargs': match.group('kwargs'), 'concept_id': None}, 'garbled_key_quotes'
    return None, 'undecodable_record'


def decode_rows(response):
    """Return (rows, record_rules, response_rule). Undecodable rows become None."""
    text = response['text']
    try:
        rows = parse_json(text)['inputs']
        return rows, [None] * len(rows), 'strict_json'
    except (KeyError, IndexError, TypeError, ValueError, RecursionError):
        pass
    try:
        rows = load_response_json(text)[0]['inputs']
        return rows, [None] * len(rows), 'python_literal_fallback'
    except (KeyError, IndexError, TypeError, ValueError, RecursionError):
        pass
    rows, rules = [], []
    for record_text in split_records(text):
        row, rule = decode_record(record_text)
        rows.append(row)
        rules.append(rule)
    return rows, rules, 'per_record_salvage'


def literal(text):
    """Python literal of a JSON-decoded field, with single-reading format fixes.

    Returns (value, fix) where fix names the format fix used, or None.
    """
    try:
        return ast.literal_eval(text), None
    except SyntaxError:
        pass
    candidates = []
    if any(character in text for character in CONTROL_ESCAPES):
        candidates.append((''.join(CONTROL_ESCAPES.get(character, character) for character in text),
                           'control_character_escape'))
    if EMBEDDED_KWARGS.search(text):
        candidates.append((EMBEDDED_KWARGS.sub(')', text), 'embedded_kwargs_removed'))
    if text.endswith("'"):
        candidates.append((text[:-1], 'stray_trailing_quote_removed'))
    for candidate, fix in candidates:
        try:
            return ast.literal_eval(candidate), fix
        except SyntaxError:
            continue
    raise SyntaxError('not a literal')


def format_record(row, builder, evidence):
    """Return (record, rule) for one raw slot, or (None, reason)."""
    if not isinstance(row, dict) or not isinstance(row.get('args'), str) or not isinstance(row.get('kwargs', '{}'), str):
        return None, 'invalid_record_fields'
    try:
        value, args_fix = literal(row['args'])
        keywords, kwargs_fix = literal(row.get('kwargs', '{}'))
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
        return None, 'not_a_literal'
    if not isinstance(keywords, dict) or not all(isinstance(name, str) for name in keywords):
        return None, 'invalid_kwargs'
    bound = None
    rule = None
    if isinstance(value, (list, tuple)):
        try:
            bound = builder.signature.bind(*value, **keywords)
            rule = args_fix or kwargs_fix or 'already_valid'
        except TypeError:
            bound = None
    if bound is None:
        if evidence and not compatible(value, evidence):
            # Static type evidence contradicts the wrapped value, e.g. '()' for a list.
            return None, 'does_not_bind'
        try:
            bound = builder.signature.bind(value, **keywords)
            rule = 'wrap_single_argument' + ('+' + args_fix if args_fix else '')
        except TypeError:
            return None, 'does_not_bind'
    if rule == 'already_valid':
        return {'args': row['args'], 'kwargs': row.get('kwargs', '{}'), 'concept_id': row.get('concept_id')}, rule
    try:
        encoded = builder.build_values(dict(bound.arguments))
    except (ValueError, TypeError):
        return None, 'unsupported_or_nonfinite_value'
    return {'args': encoded['args'], 'kwargs': encoded['kwargs'], 'concept_id': row.get('concept_id')}, rule


def admitted_form(row):
    """The original admission rule: args list/tuple literal, kwargs dict literal."""
    try:
        positional, keywords = ast.literal_eval(row['args']), ast.literal_eval(row['kwargs'])
    except (KeyError, TypeError, SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    if isinstance(positional, (list, tuple)) and isinstance(keywords, dict):
        return {'args': row['args'], 'kwargs': row['kwargs'], 'concept_id': row.get('concept_id')}
    return None


def task_inputs(task, contract, response, previous_arm):
    builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
    evidence = []
    if len(builder.signature.parameters) == 1:
        evidence = static_evidence(task, contract, next(iter(builder.signature.parameters)))
    if response.get('finish_reason') == 'length':
        return previous_arm, {'response_rule': 'truncated_not_reparsed', 'slots': []}
    rows, record_rules, response_rule = decode_rows(response)
    inputs, slots = [], []
    for index, row in enumerate(rows[:INPUT_BUDGET]):
        record_rule = record_rules[index]
        packaged, _ = repair_record(row, builder, evidence) if isinstance(row, dict) else (None, None)
        if packaged is not None:
            inputs.append(packaged)
            slots.append({'raw_index': index, 'rule': 'packaging_repair'})
            continue
        record, rule = format_record(row, builder, evidence) if row is not None else (None, 'undecodable_record')
        if rule == 'does_not_bind' and isinstance(row, dict) and admitted_form(row) is not None:
            record, rule = admitted_form(row), 'admitted_unbound_kept'
        if record_rule and record is not None:
            rule = record_rule + '+' + rule
        if record is not None:
            inputs.append(record)
        slots.append({'raw_index': index, 'rule': rule, 'raw_args': row.get('args') if isinstance(row, dict) else None})
    unchanged_rules = ('already_valid', 'packaging_repair', 'admitted_unbound_kept')
    repaired = [slot for slot in slots if slot['rule'] not in unchanged_rules and slot['rule'] in FIXED_RULES(slot['rule'])]
    return ({**previous_arm, 'inputs': inputs, 'format_repair_slots': len(repaired)},
            {'response_rule': response_rule, 'slots': slots})


def FIXED_RULES(rule):
    """A slot counts as format-repaired when its rule names an applied fix."""
    return (rule,) if any(name in rule for name in ('wrap_single_argument', 'control_character_escape',
            'embedded_kwargs_removed', 'stray_trailing_quote_removed', 'garbled_key_quotes')) else ()


def build_view(directory):
    source_view = SOURCE_AUDIT / 'repaired_view'
    view = directory / 'format_view'
    shutil.copytree(source_view, view)
    tasks = {task['task_id']: task for task in load_tasks()}
    metadata = load_metadata()
    ledger, receipts, totals = {}, [], Counter()
    for task_id in read(view / 'modular_manifest.json')['tasks']:
        number = task_id.split('/')[-1]
        batch = read(view / 'tasks' / number / 'inputs.json')
        response_path = ORIGINAL_RESPONSES / 'tasks' / number / 'calls/plain/response.json'
        receipt = {'task_id': task_id, 'changed': False}
        if not batch.get('skip') and response_path.exists():
            previous = batch['arms']['plain']
            arm, details = task_inputs(tasks[task_id], metadata[task_id]['contract'], read(response_path), previous)
            kept = [row for row in arm['inputs'] if row in previous['inputs']]
            if kept != previous['inputs']:
                raise ValueError('Format repair lost or reordered a packaging-repaired input: ' + task_id)
            receipt.update(details, valid_before=len(previous['inputs']), valid_after=len(arm['inputs']),
                           changed=arm['inputs'] != previous['inputs'],
                           source_response_sha256=checksum(response_path))
            for slot in details['slots']:
                totals[slot['rule']] += 1
            batch = {**batch, 'arms': {'plain': arm}}
            save(view / 'tasks' / number / 'inputs.json', batch)
        ledger[task_id] = digest(batch)
        receipts.append(receipt)
    freeze = read(view / 'generation_frozen.json')
    save(view / 'generation_frozen.json', {**freeze, 'inputs': ledger, 'inputs_sha256': digest(ledger)})
    manifest = read(view / 'modular_manifest.json')
    save(view / 'modular_manifest.json', {**manifest, 'protocol': 'frozen-naive-packaging-repair-1+format-repair-1'})
    summary = {'slot_rules': dict(totals), 'changed_tasks': [row['task_id'] for row in receipts if row['changed']],
               'recovered_inputs': sum(row.get('valid_after', 0) - row.get('valid_before', 0) for row in receipts),
               'new_model_calls': 0}
    save(view / 'format_receipts.json', {'summary': summary, 'tasks': receipts})
    archived = view / 'format_repair_controller.py'
    shutil.copyfile(__file__, archived)
    archived.chmod(0o444)
    snapshot = read(view / 'source_snapshot.json')
    for path in view.rglob('*'):
        if path.is_file() and path.name not in ('source_snapshot.json', 'status.json', '.worker.lock'):
            snapshot['sources'][str(path)] = checksum(path)
    for path_text in list(snapshot['sources']):
        if path_text.startswith(str(source_view) + '/'):
            del snapshot['sources'][path_text]
    save(view / 'source_snapshot.json', snapshot)
    save(view / 'status.json', {'state': 'frozen_export', 'new_model_calls': 0})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--view-only', action='store_true', help='Build the repaired input view without evaluation')
    options = parser.parse_args()
    directory = options.artifacts.resolve()
    if directory.exists():
        raise ValueError('Use a new output directory')
    directory.mkdir(parents=True)
    summary = build_view(directory)
    receipt = {'artifacts': str(directory), **summary}
    if not options.view_only:
        prepare(directory / 'format_view', directory / 'evaluation',
                native_lock=(ROOT / 'final/out/.boundary_native.lock').resolve())
        receipt['pid'] = launch(directory / 'evaluation')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
