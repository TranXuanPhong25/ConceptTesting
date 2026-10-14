"""CPU-only B4 machinery. Called exclusively inside the inherited isolated v4 worker (v4_runtime.isolated)."""
import ast
import random
from . import hypotheses, preconditions, relations, scorer, tracer, v4_worker, v4_tools
from .facts import SEED as FACTS_SEED


def candidates(task, directory):
    """Relation chains for ALL executable lines of the PUT (covered sites included) and the v4c survivors."""
    sites, base, witnesses, ok = relations.collect_traces(task)
    coverage = v4_tools.Coverage(task['put'], task['entry'], directory)
    pg = tracer.load_module(task['put'])
    base_args, base_ok = tracer.run_base(pg[task['entry']], task['base'], ns=pg)
    base_lines = set().union(*(coverage.measure(a)[0] for a in base_args)) if base_args else set()
    tree = ast.parse(task['put'])
    lines = sorted(coverage.statements | {n.lineno for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)})
    all_task = dict(task, concept_meta=[dict(kind='STMT', line=n, text=f'Candidate line {n}') for n in lines])
    # Same evidence as v12_rel chains (base + selected-hint witness traces); witness values are never rendered.
    meta = relations.extract(all_task, sites=sites, base_traces=base, witness_traces=witnesses)
    # A def line counts as covered when the base tests execute any line of that function.
    defs = {n.lineno: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    covered = lambda line: line in base_lines or (line in defs and any(
        defs[line].lineno < x <= defs[line].end_lineno for x in base_lines))
    rows = [dict(row, covered=covered(row['line']), chain=relations.render(row)) for row in meta['hints']]
    # Same frozen v4c mutation pool as v4_facts.build: mutmut points, 80 basic + 80 extended, facts SEED.
    mutants = v4_tools.enumerate_mutants(task['put'], directory)
    basic = [m['k'] for m in mutants if not m['extended']]
    extra = [m['k'] for m in mutants if m['extended']]
    random.Random(FACTS_SEED).shuffle(basic); random.Random(FACTS_SEED).shuffle(extra)
    survivors, errors = [], []
    for k in sorted(basic[:80] + extra[:80]):
        m = mutants[k]
        try:
            ns = tracer.load_module(m['mutant_src'])
            _, alive = tracer.run_base(ns[task['entry']], task['base'], record=False, ns=ns)
        except BaseException as exc:
            errors.append(dict(mutant=k, error=type(exc).__name__)); continue
        if alive is True:
            survivors.append(dict(k=k, line=m['line'], family=m['family'], mutant_src=m['mutant_src']))
    return dict(sites=rows, base_ok=ok is True and base_ok is True,
                base_trace_statuses=meta['base_trace_statuses'], survivor_mutants=survivors,
                mutation_errors=errors, mutation_pool='v4c frozen 80 basic + 80 extended')


def _args(literal):
    return (ast.literal_eval(literal), {})


def check(job):
    """Per hypothesis: T parses and is pure; no base input satisfies T; witness search; mutant difference."""
    task = job['task']
    pg = tracer.load_module(task['put']); put = pg[task['entry']]
    base, ok = tracer.run_base(put, task['base'], ns=pg)
    if ok is not True:
        return dict(hypotheses=[], failures=[dict(reason='base_tests_failed', status=ok)])
    mutants = []
    for m in job['candidates']['survivor_mutants']:
        try:
            mutants.append((m['k'], tracer.load_module(m['mutant_src'])[task['entry']]))
        except BaseException:
            pass
    kept, failures = [], []
    for h in job['hypotheses']:
        try:
            # Recheck syntax/purity inside the sandbox instead of trusting serialized source.
            src = hypotheses.trigger_source(h['T'], task)
            predicate = preconditions.load_predicate(src, 'trigger')
        except BaseException as exc:
            failures.append(dict(order=h['order'], reason='trigger_rejected', error=f'{type(exc).__name__}: {exc}'))
            continue
        satisfied, base_errors = None, []
        for i, args in enumerate(base):
            status, value = tracer.call(predicate, args, T=1)
            if status != 'ok': base_errors.append(status)
            elif value is True:
                satisfied = i; break
        if satisfied is not None:
            failures.append(dict(order=h['order'], reason='already tested', base_input=satisfied))
            continue
        if base and len(base_errors) == len(base):
            # T raises on every base input: it cannot be evaluated, so it is not a usable predicate.
            failures.append(dict(order=h['order'], reason='trigger_errors_on_all_base_inputs', errors=base_errors[:5]))
            continue
        try:
            search = v4_worker.draw(dict(task=task, code=task['strategy_src'], trigger_src=src,
                                         seed=job['seed']*100+h['order'], n=hypotheses.SEARCH_DRAWS,
                                         cap=hypotheses.SEARCH_DRAWS))
        except BaseException as exc:
            search = dict(candidates=[], trigger_errors=[], errors=[f'{type(exc).__name__}: {exc}'[:300]])
        found = search['candidates']
        witness, diff = None, []
        for row in found[:hypotheses.MUTANT_WITNESSES]:
            args = _args(row['input_repr'])
            pout = tracer.call(put, args)
            differing = [k for k, fn in mutants if not scorer.outcome_equal(pout, tracer.call(fn, args))]
            if differing:
                witness, diff = row, differing; break
        if witness is None and found:
            witness = found[0]
        if witness:
            witness = dict(input_repr=witness['input_repr'],
                           call=task['entry']+'('+', '.join(repr(a) for a in ast.literal_eval(witness['input_repr']))+')')
        kept.append(dict(h, trigger_src=src, witness=witness, witnessed=bool(witness), unwitnessed=not witness,
                         mutant_diff=bool(diff), differing_mutants=diff, satisfying_draws=len(found),
                         filter_usable=bool(found), base_trigger_errors=base_errors[:5],
                         search={k: v for k, v in search.items() if k != 'candidates'}))
    return dict(hypotheses=kept, failures=failures)


def hits(task, rows, records):
    """T satisfaction of each record (valid or not), with bounded execution; a raising T counts as False."""
    predicates = [preconditions.load_predicate(h['trigger_src'], 'trigger') for h in rows]
    for row in records:
        try:
            args = _args(row['input_repr'])
        except (ValueError, SyntaxError):
            row['hypothesis_hits'] = [False]*len(predicates); continue
        row['hypothesis_hits'] = []
        for predicate in predicates:
            status, value = tracer.call(predicate, args, T=1)
            row['hypothesis_hits'].append(status == 'ok' and value is True)
    return records


def classify(job, directory):
    """Inherited classification (B5 validity, call text) plus T hits; shown_hit_counts count valid inputs only."""
    rows = job['hypotheses']
    payload = dict(task=job['task'], shown=[])
    if 'assertions' in job: payload['assertions'] = job['assertions']
    else: payload['candidates'] = job.get('candidates', [])
    if 'requested_draws' in job: payload['requested_draws'] = job['requested_draws']
    result = v4_worker.classify(payload, directory)
    hits(job['task'], rows, result['records'])
    counts = [sum(r['valid'] and r['hypothesis_hits'][i] for r in result['records']) for i in range(len(rows))]
    result['summary'].update(shown_hit_counts=counts, hypothesis_hit_counts=counts)
    return result


def filtered_draw(job):
    """Round two: the task's domain strategy filtered by T (same draw machinery and budget as strategy requests)."""
    return v4_worker.draw(dict(task=job['task'], code=job['task']['strategy_src'],
                               trigger_src=job['hypothesis']['trigger_src'], seed=job['seed'],
                               n=job.get('n', 100), cap=job.get('cap', 500)))


def attribution(job):
    """Per final assertion: its call (oracle_b01.call_of form) and which shown T it satisfies. No oracle labels."""
    from .oracle_b01 import call_of
    task, rows = job['task'], job['hypotheses']
    out = []
    for src in job['assertions']:
        records, errors = v4_worker.capture(task, [src])
        hits(task, rows, records)
        out.append(dict(src=src, call=call_of(src, task['entry']), capture_errors=errors,
                        hypothesis_hits=[any(r['hypothesis_hits'][i] for r in records) for i in range(len(rows))]))
    return dict(records=out)
