"""Offline v57 preparation: explicit hypotheses -> construction -> replay -> prompt controls.

No model backend or private evaluator is imported. Accepts only method-visible requests.
"""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
import sys
import time
import z3

from . import hypotheses
from .construction import replay
from .crosshair_construct import construct
from .symbolic import Unsupported

HERE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def validate_request(request):
    if set(request) - {'case_id', 'source', 'entry', 'public_examples', 'proposals', 'spec'}:
        raise ValueError('request_contains_unknown_or_evaluator_fields')
    for key in ('case_id', 'source', 'entry', 'public_examples'):
        if key not in request: raise ValueError('missing:' + key)
    if not isinstance(request['source'], str) or len(request['source']) > 65536: raise ValueError('source_limit')
    tree = ast.parse(request['source'])
    if sum(1 for _ in ast.walk(tree)) > 4096: raise ValueError('source_ast_limit')
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == request['entry']), None)
    if fn is None: raise ValueError('entry')
    if any(isinstance(n, ast.Name) and n.id.startswith('_v57_') for n in ast.walk(tree)):
        raise ValueError('reserved_identifier')
    examples = request['public_examples']
    if not isinstance(examples, list) or not 1 <= len(examples) <= 6: raise ValueError('public_example_count')
    seeds = []
    for row in examples:
        if set(row) != {'arguments', 'expected'}: raise ValueError('public_example_fields')
        if not isinstance(row['arguments'], str) or len(row['arguments']) > 4000: raise ValueError('public_example_size')
        args = ast.literal_eval(row['arguments'])
        if type(args) is not tuple: raise ValueError('arguments_must_be_positional_tuple')
        ast.literal_eval(row['expected'])
        seeds.append(args)
    if len(request.get('proposals', [])) > 48: raise ValueError('proposal_count')
    if 'spec' in request and (not isinstance(request['spec'], str) or len(request['spec']) > 20000): raise ValueError('spec_size')
    return fn, seeds


def proposal_request(request):
    fn, _ = validate_request(request)
    return dict(instruction=(
        'Identify explicit fault hypotheses from specification and code. A hypothesis is not a confirmed bug. '
        'For each, give the exact source AST span and before/after expression (or accumulator assignment), '
        'a verbatim docstring quote, and rationale separating required semantics from observed behavior. '
        'Separate required_relation, observed_relation, and trigger_reason (reach conditions, local failure condition '
        'and expected propagation). Return a JSON list of '
        '{span:[line,col,end_line,end_col],before,after,family,rationale,spec_quote,required_relation,observed_relation,trigger_reason}. '
        'Do not propose arbitrary code; replacements must be supported pure expressions. '
        'Do not infer domain constraints merely from example signs or lengths. Abstain with [] when ungrounded.'),
        families=hypotheses.FAMILIES, source=request['source'], entry=request['entry'],
        spec=request.get('spec', ast.get_docstring(fn, clean=False) or ''), public_examples=request['public_examples'])


def base_status(source, entry, seeds, h, deadline=None):
    rows = []
    for args in seeds:
        observed = replay(source, entry, args, h, deadline=deadline)
        if observed.get('status') != 'ok' or any(observed[k]['status'] != 'ok' for k in ('put', 'alternative')):
            return 'unknown_replay', rows
        rows.append(dict(arguments=repr(args), put=observed['put']['output'], alternative=observed['alternative']['output']))
    return ('already_distinguished_by_public_inputs' if any(r['put'] != r['alternative'] for r in rows)
            else 'not_distinguished_by_public_inputs'), rows


def canonical_evidence(records):
    return [dict(rank=i + 1, hypothesis=r['hypothesis'], base_status=r['base_status'],
                 base_observations=r['base_observations'], construction_status=r['status'],
                 limitations=r['issues'], inputs=r['inputs']) for i, r in enumerate(records)]


def prompts(request, records):
    # Same evidence object/order in the concept and raw arms. The framing alone differs.
    evidence = canonical_evidence(records)
    common = dict(source=request['source'], entry=request['entry'], public_examples=request['public_examples'],
                  spec=request.get('spec', ast.get_docstring(next(n for n in ast.parse(request['source']).body if isinstance(n, ast.FunctionDef) and n.name == request['entry']), clean=False) or ''),
                  oracle_instruction='Derive expected outputs from the specification. Tool outputs are observations, not oracle values.')
    concepts = dict(common, instruction=(
        'Use each source-bound fault concept as a test obligation: reach its AST site, activate the local distinction '
        'and propagate it to output, while satisfying the specification domain. These are unverified hypotheses. '
        'Propose valid new tests and say which obligation they exercise.'), evidence=evidence)
    raw = dict(common, instruction=(
        'Inspect the complete raw tool evidence and produce valid new tests with expected outputs from the specification. '
        'Tool observations and candidate edits do not establish correct behavior.'), evidence=evidence)
    inputs = [x['arguments'] for r in records for x in r['inputs']]
    return dict(plain=dict(common, instruction='Generate valid bug-revealing tests with spec-derived expected outputs.'),
                concept=concepts, equal_evidence_raw=raw,
                inputs_only=dict(common, inputs=list(dict.fromkeys(inputs)),
                                 instruction='Consider these candidate inputs and generate valid tests; inputs were screened against the specification by a model and may still be invalid.'),
                witness_only=dict(arguments=[r['arguments'] for r in request['public_examples']], uses_llm=False))


def prepare(request, config):
    fn, seeds = validate_request(request)
    rows, issues = hypotheses.catalog(request['source'], request['entry'], config['max_hypotheses'])
    imported = hypotheses.import_proposals(request['source'], request['entry'], request.get('proposals', []), config['max_hypotheses'], spec=request.get('spec'))
    # Explicit writer hypotheses take priority; never silently discard all new proposals behind the catalogue cap.
    by_id = {r['id']: r for r in imported}
    for r in rows:
        if r['id'] not in by_id: by_id[r['id']] = r
    selected = list(by_id.values())[:config['max_hypotheses']]
    if len(by_id) > len(selected): issues.append('combined_hypothesis_cap')
    results = []
    for h in selected:  # v68: CrossHair backend, fixed per-hypothesis budget, full catalogue in the denominator
        try:
            r = construct(request['source'], request['entry'], seeds, h, config)
        except Exception as exc:
            r = dict(hypothesis=h, status='harness_error', inputs=[], issues=[type(exc).__name__ + ':' + str(exc)[:160]])
        r['base_status'], r['base_observations'] = base_status(request['source'], request['entry'], seeds, h,
                                                              deadline=time.monotonic() + 60)
        results.append(r)
    # These are uncertainty/adequacy priorities, not estimated fault probabilities.
    results.sort(key=lambda r: (not bool(r['inputs']), r['base_status'] != 'not_distinguished_by_public_inputs',
                                -len(r['inputs']), len(r['issues']), r['hypothesis']['span'], r['hypothesis']['id']))
    all_prompts = prompts(request, results)
    if all_prompts['concept']['evidence'] != all_prompts['equal_evidence_raw']['evidence']:
        raise AssertionError('evidence_parity')
    legacy_consts = sorted({n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and type(n.value) is int and abs(n.value) <= config['int_bound']})
    from .legacy_templates import templates
    legacy = templates(seeds, {'BOUNDARY': legacy_consts}, domain=False)
    return dict(case_id=request['case_id'], hypotheses=results, issues=issues,
                catalog_count=len(rows), imported_count=len(imported), processed_count=len(results),
                status_counts=dict(collections.Counter(r['status'] for r in results)),
                family_registry=hypotheses.FAMILIES,
                missing_case_scope='legacy low-cardinality transforms and symbolic shape enumeration; not a synthesized missing branch',
                legacy_control_inputs=[repr(r['args']) for r in legacy],
                prompts=all_prompts, expected_output_source='none; observation-only preparation')


def manifest(request, config):
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}
    return dict(request_sha256=digest(request), config=config, source_files_sha256=files,
                solver_version=z3.get_full_version(), python=sys.version,
                request_visibility='caller attests all examples are public; unknown/evaluator fields rejected',
                scope='engineering preparation, no independent bug labels or model calls')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['export-hypotheses', 'prepare'])
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text()); validate_request(request)
    if args.command == 'export-hypotheses':
        with args.out.open('x') as stream: json.dump(proposal_request(request), stream, indent=2)
        return
    config = json.loads((HERE / 'config.json').read_text())['pathfault']
    identity = manifest(request, config)
    if args.out.exists():
        old = json.loads(args.out.read_text())
        if old.get('manifest') != identity: raise SystemExit('existing artifact manifest differs; choose a fresh output')
        print('Existing identical preparation preserved:', args.out); return
    result = prepare(request, config)
    with args.out.open('x') as stream: json.dump(dict(manifest=identity, result=result), stream, indent=2, ensure_ascii=True)
    print(json.dumps(dict(case_id=result['case_id'], statuses=result['status_counts'], processed=result['processed_count'])))


if __name__ == '__main__':
    main()
