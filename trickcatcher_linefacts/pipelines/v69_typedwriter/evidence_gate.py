"""Public-consistency checks and the exact evidence delivered to generation.

No check here establishes full spec truth or uses a private reference.
"""
import ast
import hashlib
import json
import time

from .construction import replay
from .literal_contract import parse_arguments, parse_expected
from .replay_worker import encode


def alternative_source(request, hypothesis):
    tree = ast.parse(request['source'])
    span = hypothesis['site']['span']
    matches = 0

    class Replace(ast.NodeTransformer):
        def visit(self, node):
            nonlocal matches
            if isinstance(node, ast.expr) and [node.lineno, node.col_offset,
                                               node.end_lineno, node.end_col_offset] == span:
                matches += 1
                return ast.copy_location(ast.parse(hypothesis['alternative'], mode='eval').body, node)
            return super().visit(node)

    tree = Replace().visit(tree)
    if matches != 1:
        raise ValueError('alternative_site_binding')
    return ast.unparse(ast.fix_missing_locations(tree))


def check_public_examples(request, hypothesis, config, deadline, execution_budget):
    """All examples, both programs, repeated uninstrumented replay, typed equality."""
    from .semantic_contract import admit
    fields = ('site_id', 'family', 'required_relation', 'observed_relation', 'spec_quote',
              'trigger', 'priority', 'alternative', 'event_predicate', 'alternative_rationale')
    checked, errors = admit(request, [{key: hypothesis[key] for key in fields if key in hypothesis}])
    if errors or checked != [hypothesis]:
        raise ValueError('hypothesis_integrity')
    if (not config['repeat_seeds'] or type(config['repeats_per_program_seed']) is not int
            or config['repeats_per_program_seed'] < 1):
        raise ValueError('public_check_repeat_config')
    rows = []
    executions = 0
    if hypothesis['alternative'] is None:
        return dict(status='no_alternative', rows=rows, native_executions=0,
                    semantic_truth='unverified')
    sources = {'put': request['source'], 'alternative': alternative_source(request, hypothesis)}
    if not request['public_examples']:
        return dict(status='no_public_examples', rows=rows, native_executions=0,
                    semantic_truth='unverified')
    for index, example in enumerate(request['public_examples']):
        try:
            args = parse_arguments(example['arguments'])
            expected = encode(parse_expected(example['expected']))
        except (ValueError, TypeError, KeyError, SyntaxError):
            return dict(status='unsupported_public_example', rows=rows,
                        native_executions=executions, semantic_truth='unverified')
        for seed in config['repeat_seeds']:
            for repeat in range(config['repeats_per_program_seed']):
                for name, source in sources.items():
                    if executions >= execution_budget or time.monotonic() >= deadline:
                        return dict(status='public_check_budget', rows=rows,
                                    native_executions=executions, semantic_truth='unverified')
                    observed = replay(source, request['entry'], args, None, deadline=deadline, seed=seed)
                    executions += 1
                    program = observed.get('put', {})
                    normal = observed.get('status') == 'ok' and program.get('status') == 'ok'
                    matches = normal and program.get('output') == expected
                    rows.append(dict(example=index, program=name, seed=seed, repeat=repeat,
                                     normal=normal, matches=matches, observation=observed))
                    if not matches:
                        return dict(status='public_regression' if normal else 'public_check_unknown',
                                    rows=rows, native_executions=executions, semantic_truth='unverified')
    return dict(status='passed', rows=rows, native_executions=executions,
                semantic_truth='unverified', scope='finite_public_examples_only')


def realized(run):
    return (all(run.get(key) is True for key in
                ('stable', 'normal', 'site_realized', 'predicate_realized', 'event_realized'))
            and run.get('event_unknown') is False)


def public_arguments(request):
    return {repr(parse_arguments(row['arguments'])) for row in request['public_examples']}


def select_evidence(request, construction):
    public = public_arguments(request)
    evidence, inputs, receipts = [], [], []
    for record in construction['records']:
        hypothesis = record['hypothesis']
        consistency = record.get('public_consistency', {})
        eligible = [r for r in record['runs'] if realized(r)]
        # Stable sort preserves source run order among equal categories.
        eligible.sort(key=lambda r: (not (r.get('output_sensitivity') is True and r['arguments'] not in public),
                                     r.get('output_sensitivity') is not True))
        selected, seen = [], set()
        if consistency.get('status') == 'passed' and hypothesis.get('alternative') is not None:
            for run in eligible:
                if run['arguments'] not in seen:
                    selected.append(run)
                    seen.add(run['arguments'])
                if len(selected) == 2:
                    break
        shown = []
        for run in selected:
            observations = run.get('observations', [])
            if not observations:
                raise ValueError('missing_selected_witness_observations')
            shown.append(dict({k: v for k, v in run.items() if k != 'observations'},
                              observed_outputs={name: obs.get('output') for name, obs in observations[0].items()
                                                if isinstance(obs, dict)}))
        if shown:
            evidence.append(dict(hypothesis=hypothesis, construction=record['construction'],
                                 public_consistency={k: v for k, v in consistency.items() if k != 'rows'},
                                 witnesses=shown))
            inputs.extend(run['arguments'] for run in shown)
        receipts.append(dict(hypothesis_id=hypothesis['id'], eligible=len(eligible),
                             selected_arguments=[r['arguments'] for r in shown],
                             omitted=max(0, len(eligible)-len(shown)),
                             public_status=consistency.get('status', 'missing')))
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return dict(evidence=evidence, inputs=list(dict.fromkeys(inputs)), receipts=receipts,
                evidence_sha256=digest, policy='nonpublic_sensitive_then_sensitive_then_realized')


def assess_context(request, context):
    """Assess exactly the displayed concept payload, not the undisplayed search pool."""
    public = public_arguments(request)
    useful = []
    for row in context['evidence']:
        if row.get('public_consistency', {}).get('status') != 'passed':
            continue
        if row['hypothesis'].get('alternative') is None:
            continue
        for witness in row['witnesses']:
            if realized(witness) and witness.get('output_sensitivity') is True and witness['arguments'] not in public:
                useful.append(dict(hypothesis_id=row['hypothesis']['id'], arguments=witness['arguments']))
    return dict(case_id=request['case_id'], passed=bool(useful), delivered_sensitive=useful,
                reason='delivered_public_consistent_sensitive_witness' if useful else 'no_usable_delivered_evidence',
                evidence_sha256=hashlib.sha256(json.dumps(context['evidence'], sort_keys=True).encode()).hexdigest(),
                semantic_truth='unverified', input_validity='unverified', private_data_used=False)
