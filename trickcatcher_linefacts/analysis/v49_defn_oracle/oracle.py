"""v49 definitional oracle (PREREG + Amendment 1). References enter only score.
PYTHONPATH=. $V4_PYTHON .../oracle.py status|execute|score [execute --tasks 3,46]
Full execute/score require complete generation; --tasks is a partial-record engineering smoke.
"""
import argparse
import ast
import collections
import difflib
import hashlib
import io
import itertools
import json
import sys
import tokenize
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v48_e2e_oracle import e2e as E
from trickcatcher_linefacts.analysis.v49_defn_oracle import gen
from trickcatcher_linefacts.pipelines.v7.oracle_b01 import code_block
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import digest, immutable

HERE = Path(__file__).resolve().parent
OUT = gen.OUT
ARMS = gen.ARMS
FAMILIES = (*ARMS, 'tc')
RULES = ('primary', 'finishing', 'tc_full', 'consensus')
REASONS = ('skipped-crash', 'load', 'timeout', 'MemoryError', 'RecursionError', 'exception', 'mismatch')
MARKERS = ('# ENUMERATE:', '# CHECK:', '# AGGREGATE:')


class Inventory(E.Inventory):
    def finish(self):
        for path in (HERE / 'PREREG.md', Path(__file__), Path(gen.__file__)):
            self.add(path)
        return super().finish()


def status(inv=None):
    inv = inv or Inventory()
    cohort, tc_tasks = E.planned(inv)
    bad = []

    def count(arm, tasks, n):
        root = E.oracle.OUT if arm == 'tc' else OUT
        present, finishes = 0, collections.Counter(length=0, context_overflow=0)
        for cid in tasks:
            for i in range(n):
                p = root / 'programs' / arm / cid / f'{i}.json'
                if not p.is_file():
                    continue
                present += 1
                try:
                    rec = inv.read(p)
                    if not isinstance(rec.get('text'), str) or not isinstance(rec.get('finish_reason'), str) or not rec.get('digest'):
                        raise ValueError('program record schema')
                    finishes[rec['finish_reason']] += 1
                except (ValueError, TypeError, AttributeError) as exc:
                    bad.append(dict(path=E.rel(p), error=str(exc)))
        return dict(tasks=len(tasks), programs_per_task=n, planned=len(tasks) * n, present=present,
                    missing=len(tasks) * n - present, finish_reason=dict(finishes))

    arms = {arm: count(arm, cohort, gen.NPROG) for arm in ARMS}
    tc = count('tc', sorted(tc_tasks, key=int), E.oracle.NPROG)
    return dict(tasks=len(cohort), arms=arms, v49_planned=sum(a['planned'] for a in arms.values()),
                v49_present=sum(a['present'] for a in arms.values()), v46_tc=tc,
                tc_unplanned_tasks=sorted(set(cohort) - tc_tasks, key=int), bad_records=bad,
                complete=not bad and not any(a['missing'] for a in (*arms.values(), tc)))


CHUNK, SUBCHUNK, WORKERS = 200, 25, 8


def batch(directory, sources, order, entry, inputs, per_call_timeout=1):
    """v46 batch with a configurable call limit; no source is skipped after a timeout. The process limit scales with
    the job (a C-level loop the per-call alarm cannot stop only costs its chunk)."""
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / 'job.json', directory / 'result.json'
    job = dict(sources={n: sources[n] for n in order}, order=order, entry=entry, inputs=inputs,
               per_call_timeout=per_call_timeout, max_timeouts=len(inputs) + 1)
    if op.exists() and jp.exists() and json.loads(jp.read_text()) == job:
        return json.loads(op.read_text())
    op.unlink(missing_ok=True)
    jp.write_text(json.dumps(job))
    limit = len(order) * len(inputs) * per_call_timeout * 1.2 + 120
    return E.oracle.sandbox(E.CONFIG['V4_PYTHON'], E.iorel.WORKER, jp, op, limit)


def run_programs(case, arm, srcs, inputs, tag, per_call_timeout=1):
    """v46 loading, one process per (program, chunk of 200 inputs), 8 in parallel; a crashed or hung chunk is rerun in
    chunks of 25 and a failing sub-chunk is `skipped` (abstention on those inputs only)."""
    names = [f'p{i}' for i in range(len(srcs))]
    if not names:
        return {}
    sources = {n: E.oracle.program_module(case, src) for n, src in zip(names, srcs)}
    directory = E.oracle.OUT / 'exec' / case['case_id'] / arm / tag

    def chunk(job):
        n, s = job
        part = inputs[s:s + CHUNK]
        try:
            return n, s, batch(directory / n / f'c{s}', sources, [n], case['entry'], part, per_call_timeout)[n]
        except RuntimeError:
            vals = []
            for t in range(0, len(part), SUBCHUNK):
                sub = part[t:t + SUBCHUNK]
                try:
                    vals += batch(directory / n / f'c{s}_{t}', sources, [n], case['entry'], sub, per_call_timeout)[n]
                except RuntimeError:
                    vals += [['skipped']] * len(sub)
            return n, s, vals
    out = {n: [None] * len(inputs) for n in names}
    with ThreadPoolExecutor(WORKERS) as pool:
        for n, s, vals in pool.map(chunk, [(n, s) for n in names for s in range(0, len(inputs), CHUNK)]):
            out[n][s:s + len(vals)] = vals
    return out


def rejection(put, outputs):
    """Every public input must finish normally and match; do not filter out PUT timeouts."""
    reasons = set()
    if not put or len(put) != len(outputs):
        reasons.add('load')
    for p, out in zip(put, outputs):
        if not out or out[0] == 'skipped':
            reasons.add('skipped-crash')
        elif out[0] == 'timeout':
            reasons.add('timeout')
        elif out[0] == 'exception':
            detail = out[1]
            reasons.add('load' if detail.startswith('load:') else detail if detail in ('MemoryError', 'RecursionError') else 'exception')
        elif out[0] != 'ok' or E.iorel.value(out) is None:
            reasons.add('exception')
        elif not p or p[0] != 'ok' or E.iorel.value(p) is None or not E.same(E.iorel.value(p), E.iorel.value(out)):
            reasons.add('mismatch')
    return [r for r in REASONS if r in reasons]


def resource_only(reasons, outputs):
    failures = [o for o in outputs if o and o[0] != 'ok']
    return bool(reasons) and not set(reasons) - {'load', 'timeout', 'MemoryError', 'RecursionError'} and bool(failures) and all(
        o[0] == 'timeout' or o[0] == 'exception' and o[1] in ('MemoryError', 'RecursionError', 'load:MemoryError', 'load:RecursionError')
        for o in failures)


def votes(put_raw, program_raw):
    """Worker reprs stay raw across JSON. Failures remain in V for the primary quorum."""
    result = dict.fromkeys(RULES)
    if not E.put_ok(dict(put=put_raw)):
        return result
    largest, consensus = E.raw_votes(put_raw, program_raw)
    result.update(tc_full=largest, consensus=consensus)
    if largest is None:
        return result
    val = E.iorel.value(largest)
    finishing = [E.iorel.value(o) for o in program_raw if o and o[0] == 'ok']
    count = sum(v is not None and E.same(v, val) for v in finishing)
    if count >= 2:
        if count * 2 > len(program_raw):
            result['primary'] = largest
        if count * 2 > len(finishing):
            result['finishing'] = largest
    return result


def problem_id(case):
    return hashlib.sha256(E.task_view(case)['spec'].encode()).hexdigest()


def entry_dump(source, entry, implementation=False):
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry)
    if implementation:
        # VibePass's public entry is a wrapper around Solution().method(...).
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Call) and isinstance(n.func.value.func, ast.Name)
                 and n.func.value.func.id == 'Solution']
        if calls:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Solution')
            fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == calls[0].func.attr)
    return ast.dump(fn, include_attributes=False)


def audit(case, source):
    comments = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                comments.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    result = dict(concept_comments={m: any(c.startswith(m) for c in comments) for m in MARKERS})
    for key, impl in (('entry_ast_similarity', False), ('implementation_ast_similarity', True)):
        try:
            a = entry_dump(case['source'], case['entry'], impl)
            b = entry_dump(E.oracle.program_module(case, source), case['entry'], impl)
            result[key] = difflib.SequenceMatcher(None, a, b).ratio()
        except (SyntaxError, ValueError, StopIteration, RecursionError):
            result[key] = None
    return result


def programs(inv, case, arm, tc_tasks):
    cid = case['case_id']
    n = E.oracle.NPROG if arm == 'tc' and cid in tc_tasks else gen.NPROG if arm in ARMS else 0
    root = E.oracle.OUT if arm == 'tc' else OUT
    srcs, records, missing, overflow = {}, {}, [], []
    task = E.task_view(case)
    if arm == 'tc' and n:
        templates = E.tc_full.templates()
        for name in E.tc_full.SHA:
            inv.add(E.tc_full.HERE / 'tc_templates' / name)
        msgs = E.oracle.tc_messages(case, 'tc', [], templates)
    else:
        msgs = gen.messages(task, arm) if n else []
    for i in range(n):
        path = root / 'programs' / arm / cid / f'{i}.json'
        if not path.is_file():
            missing.append(i)
            continue
        rec = inv.read(path)
        seed = int(hashlib.sha256(f"{'v46' if arm == 'tc' else 'v49'}/{cid}/{arm}/{i}".encode()).hexdigest()[:8], 16)
        params = dict(seed=seed, **E.tc_full.PARAMS) if arm == 'tc' else dict(seed=seed, temperature=0.8, top_p=0.95, max_tokens=1024)
        if not isinstance(rec.get('text'), str) or not isinstance(rec.get('finish_reason'), str) or rec.get('digest') != E.oracle.digest(msgs, params):
            raise ValueError(f'program schema/prompt digest differs: {cid}/{arm}/{i}')
        records[str(i)] = rec['finish_reason']
        if rec['finish_reason'] == 'context_overflow':
            overflow.append(i)
        else:
            srcs[i] = E.tc_full.source(rec['text']) if arm == 'tc' else code_block(rec['text'])  # tc: as v46/v48
    return dict(planned=n, present=len(records), missing=missing, context_overflow=overflow,
                finish_reason=records, sources=srcs)


def execute_case(inv, case, prep, loaded, root):
    cid = case['case_id']
    inputs = E.ordered(E.all_inputs(prep) | set(E.pool_subset(E.pool_inputs(inv, cid), cid)))
    seeds = [repr(x) for x in E.ft_run.base_inputs(case, 'vibepass_half')]
    families, outputs = {}, {}
    with E.execution_root(root):
        base_put = run_programs(case, 'put', [case['source']], seeds, 'base', 2)['p0']
        put = run_programs(case, 'put', [case['source']], inputs, 'inputs')['p0']
        for arm in FAMILIES:
            data = loaded[arm]
            ids = list(data['sources'])
            srcs = list(data['sources'].values())
            base = run_programs(case, arm, srcs, seeds, 'base', 2)
            validation, valid = {}, []
            for j, i in enumerate(ids):
                reasons = rejection(base_put, base[f'p{j}'])
                validation[str(i)] = dict(valid=not reasons, reason=reasons[0] if reasons else None, reasons=reasons,
                                          resource_only=resource_only(reasons, base[f'p{j}']),
                                          **audit(case, srcs[j]))
                if not reasons:
                    valid.append(i)
            for i in data['context_overflow']:
                validation[str(i)] = dict(valid=False, reason='no_program', reasons=['context_overflow'], resource_only=False)
            ran = run_programs(case, arm + '_valid', [data['sources'][i] for i in valid], inputs, 'inputs')
            outputs[arm] = {str(i): ran[f'p{j}'] for j, i in enumerate(valid)}
            families[arm] = {k: v for k, v in data.items() if k != 'sources'} | dict(
                valid_programs=valid, validation=validation,
                base_programs={str(i): base[f'p{j}'] for j, i in enumerate(ids)},
                crashed_base=[i for j, i in enumerate(ids) if any(o[0] == 'skipped' for o in base[f'p{j}'])],
                crashed_universe=[i for i in valid if any(o[0] == 'skipped' for o in outputs[arm][str(i)])])
    rows = {lit: dict(put=put[j], programs={a: {i: outs[j] for i, outs in outputs[a].items()} for a in FAMILIES})
            for j, lit in enumerate(inputs)}
    inv.tree(root / 'exec' / cid)
    record = dict(case_id=cid, problem_id=problem_id(case), families=families, base_inputs=seeds, base_put=base_put,
                  inputs=rows, input_sha256=digest(inputs), artifact_sha256=inv.finish())
    immutable(root / 'tasks' / f'{cid}.json', record)
    return dict(case_id=cid, inputs=len(inputs), public_inputs=len(seeds),
                put_failed_public=sum(not E.put_ok(dict(put=o)) for o in base_put),
                put_no_test_inputs=sum(not E.put_ok(row) for row in rows.values()),
                families={a: dict(present=f['present'], planned=f['planned'], valid=len(f['valid_programs']),
                                  context_overflow=len(f['context_overflow']),
                                  rejected=dict(collections.Counter(v['reason'] for v in f['validation'].values() if not v['valid'])),
                                  crashed_programs=len(set(f['crashed_base']) | set(f['crashed_universe'])),
                                  primary_tests=sum(votes(r['put'], list(r['programs'][a].values()))['primary'] is not None for r in rows.values()))
                          for a, f in families.items()})


def execute(tasks=None):
    inv = Inventory()
    state = status(inv)
    if tasks is None and not state['complete']:
        print(json.dumps(dict(status=state, refused='planned records incomplete; use --tasks for partial-record smoke'), indent=2))
        return 1
    cohort, tc_tasks = E.planned(inv)
    if tasks is not None and (not tasks or not set(tasks) <= set(cohort)):
        raise ValueError('unknown or empty --tasks selection')
    wanted = cohort if tasks is None else [cid for cid in cohort if cid in tasks]
    prep = inv.read(E.select.OUT / 'prepared.json')
    cases = E.tool_cases(inv, wanted)
    loaded = {cid: {a: programs(inv, cases[cid], a, tc_tasks) for a in FAMILIES} for cid in wanted}
    # Snapshot names include present records, so generation can continue while smokes remain immutable.
    root = OUT if tasks is None else OUT / 'smoke' / digest(inv.finish())[:16]
    summaries = []
    for cid in wanted:
        task_inv = Inventory()
        for path in (E.SPLIT, E.oracle.QUESTIONS, E.select.OUT / 'prepared.json'):
            task_inv.add(path)
        case = E.tool_cases(task_inv, [cid])[cid]
        task_loaded = {a: programs(task_inv, case, a, tc_tasks) for a in FAMILIES}
        # Detect a generation arrival between the snapshot selection and execution.
        if task_loaded != loaded[cid]:
            raise ValueError('program records changed while selecting execution snapshot; rerun')
        summaries.append(execute_case(task_inv, case, prep[cid], task_loaded, root))
        print(json.dumps(summaries[-1]), flush=True)
    result = dict(tasks=wanted, smoke=tasks is not None, rows=summaries)
    immutable(root / ('execution.json' if tasks is None else 'execution_' + '_'.join(wanted) + '.json'), result)
    print(json.dumps(dict(output=E.rel(root), smoke=tasks is not None)), flush=True)
    return 0


def oracle_rows(record, family, subset=None):
    chosen = None if subset is None else {str(i) for i in subset}
    rows = {}
    for lit, row in record['inputs'].items():
        progs = [o for i, o in row['programs'][family].items() if chosen is None or i in chosen]
        rows[lit] = dict(put=row['put'], programs=progs, **votes(row['put'], progs))
    return rows


def labels_for(rows, truth):
    return {lit: {rule: E.judge(E.iorel.value(row[rule]), ['ok'] if truth[lit]['valid'] else ['exception'],
                               truth[lit]['ref'], E.iorel.value(row['put']),
                               truth[lit].get('exposes', lambda lit=lit: truth[lit]['exposing'] is True))
                  for rule in RULES} for lit, row in rows.items()}


def metrics(inputs, rows, truth, valid_count):
    inputs = set(inputs)
    labels = labels_for({lit: rows[lit] for lit in inputs}, truth)
    result = {}
    for rule in RULES:
        eligible = 0
        for lit in set(inputs):
            row = rows[lit]
            finishing = sum(bool(o and o[0] == 'ok') for o in row['programs'])
            enough = valid_count >= (1 if rule == 'tc_full' else 3 if rule == 'consensus' else 2)
            if rule == 'finishing':
                enough = finishing >= 2
            eligible += E.put_ok(row) and enough
        result[rule] = {}
        for mode, cap in (('capped', 20), ('uncapped', None)):
            m = E.metric(inputs, rows, labels, rule, cap)
            m.update(eligible_inputs=eligible, confirmed_tests=m['correct_assertions'],
                     reference_skipped_tests=sum(bool(truth[lit].get('reference_skipped')) for lit in E.emitted(inputs, rows, rule, cap)),
                     precision=m['correct_assertions'] / m['tests'] if m['tests'] else None)
            result[rule][mode] = m
    return result


def subset_mean(record, inputs, truth, k=5, n=10):
    """Exact expectation over GENERATED slots (invalid/overflow slots stay in the sample)."""
    totals, count, cache = {}, 0, {}
    valid = set(record['families']['tc']['valid_programs'])
    scoped = dict(record, inputs={lit: record['inputs'][lit] for lit in set(inputs)})
    for subset in itertools.combinations(range(n), k):
        key = tuple(sorted(valid & set(subset)))
        if key not in cache:
            rows = oracle_rows(scoped, 'tc', key)
            cache[key] = metrics(inputs, rows, truth, len(key))
        m = cache[key]
        count += 1
        for rule in RULES:
            for mode in ('capped', 'uncapped'):
                s = totals.setdefault(rule, {}).setdefault(mode, collections.Counter())
                s.update({key: value for key, value in m[rule][mode].items() if key != 'precision'})
    if not count:
        raise ValueError('empty program subset enumeration')
    means = {r: {mode: {key: value / count for key, value in values.items()} for mode, values in modes.items()}
             for r, modes in totals.items()}
    for modes in means.values():
        for m in modes.values():
            m['precision'] = m['correct_assertions'] / m['tests'] if m['tests'] else None
    return dict(method='exact', generated_slots=n, planned_programs=record['families']['tc'].get('planned', n),
                k=k, subsets=count), means


def paired_k5(record, inputs, truth, peer):
    """Pair with tc_k5 on V>=2 within EACH generated-program subset, before applying the cap."""
    valid = set(record['families']['tc']['valid_programs'])
    peer_v = len(record['families'][peer]['valid_programs'])
    normal = {lit for lit in inputs if E.put_ok(record['inputs'][lit])}
    peer_rows = oracle_rows(record, peer)
    weights = collections.Counter(tuple(sorted(valid & set(s))) for s in itertools.combinations(range(10), 5))
    sums = {a: {r: {m: collections.Counter() for m in ('capped', 'uncapped')} for r in RULES} for a in (peer, 'tc_k5')}
    eligible_mean = 0
    for key, weight in weights.items():
        eligible = normal if peer_v >= 2 and len(key) >= 2 else set()
        eligible_mean += len(eligible) * weight / 252
        tc_rows = oracle_rows(dict(record, inputs={lit: record['inputs'][lit] for lit in eligible}), 'tc', key)
        for a, rr, v in ((peer, peer_rows, peer_v), ('tc_k5', tc_rows, len(key))):
            mm = metrics(eligible, rr, truth, v)
            for rule in RULES:
                for mode in ('capped', 'uncapped'):
                    sums[a][rule][mode].update({k: value * weight for k, value in mm[rule][mode].items() if k != 'precision'})
    families = {a: {r: {mode: {k: v / 252 for k, v in counts.items()} for mode, counts in modes.items()}
                   for r, modes in rules.items()} for a, rules in sums.items()}
    for rules in families.values():
        for modes in rules.values():
            for m in modes.values():
                m['precision'] = m['correct_assertions'] / m['tests'] if m['tests'] else None
    return dict(inputs=eligible_mean, families=families, method='exact', subsets=252)


def diagnostics(record, family, rows, truth):
    exposing = [lit for lit in rows if truth[lit]['exposing'] is True]
    uncomputed = [lit for lit in rows if truth[lit]['exposing'] is None]
    skipped = [lit for lit in rows if truth[lit].get('reference_skipped')]
    common, no_finishing = [], []
    for lit in exposing:
        finishing = [E.iorel.value(o) for o in rows[lit]['programs'] if o and o[0] == 'ok']
        if not finishing:
            no_finishing.append(lit)
        elif all(v is not None and E.same(v, E.iorel.value(rows[lit]['put'])) for v in finishing):
            common.append(lit)
    f = record['families'][family]
    values = list(f['validation'].values())
    outcomes = [o for row in rows.values() for o in row['programs']]
    return dict(valid_programs=len(f['valid_programs']), rejection_reasons=dict(collections.Counter(
                    reason for v in values for reason in v['reasons'])),
                rejected_resource_only=sum(v['resource_only'] for v in values),
                crashed_programs=sorted(set(f['crashed_base']) | set(f['crashed_universe'])),
                exposing_inputs=len(exposing), exposure_evaluated_inputs=len(rows) - len(uncomputed),
                exposure_uncomputed_inputs=E.ordered(uncomputed), reference_skipped_inputs=E.ordered(skipped),
                common_mode_inputs=E.ordered(common),
                common_mode_share=len(common) / len(exposing) if exposing else None,
                exposing_no_finishing=E.ordered(no_finishing),
                exposing_abstentions={rule: E.ordered(lit for lit in exposing if rows[lit][rule] is None) for rule in RULES},
                abstentions=sum(not o or o[0] != 'ok' or E.iorel.value(o) is None for o in outcomes),
                program_input_calls=len(outcomes),
                abstention_rate=sum(not o or o[0] != 'ok' or E.iorel.value(o) is None for o in outcomes) / len(outcomes) if outcomes else None,
                concept_comments={m: sum(v.get('concept_comments', {}).get(m, False) for v in values) for m in MARKERS},
                ast_similarity={i: {k: v.get(k) for k in ('entry_ast_similarity', 'implementation_ast_similarity')}
                                for i, v in f['validation'].items()},
                finish_reason=dict(collections.Counter(f['finish_reason'].values())))


def diagnostic_totals(rows):
    result = {}
    for family in FAMILIES:
        dd = [r['diagnostics'][family] for r in rows]
        exposing = sum(d['exposing_inputs'] for d in dd)
        common = sum(len(d['common_mode_inputs']) for d in dd)
        calls, abstentions = sum(d['program_input_calls'] for d in dd), sum(d['abstentions'] for d in dd)
        result[family] = dict(valid_programs_by_task={r['case_id']: r['diagnostics'][family]['valid_programs'] for r in rows},
            rejected_resource_only=sum(d['rejected_resource_only'] for d in dd),
            rejection_reasons=dict(sum((collections.Counter(d['rejection_reasons']) for d in dd), collections.Counter())),
            crashed_programs=sum(len(d['crashed_programs']) for d in dd), exposing_inputs=exposing,
            exposure_evaluated_inputs=sum(d['exposure_evaluated_inputs'] for d in dd),
            exposure_uncomputed_inputs=sum(len(d['exposure_uncomputed_inputs']) for d in dd),
            reference_skipped_inputs=sum(len(d['reference_skipped_inputs']) for d in dd),
            common_mode_inputs=common, common_mode_share=common / exposing if exposing else None,
            exposing_no_finishing=sum(len(d['exposing_no_finishing']) for d in dd),
            exposing_abstentions={rule: sum(len(d['exposing_abstentions'][rule]) for d in dd) for rule in RULES},
            abstention_rate=abstentions / calls if calls else None, abstentions=abstentions, program_input_calls=calls,
            concept_comments={m: sum(d['concept_comments'][m] for d in dd) for m in MARKERS},
            finish_reason=dict(sum((collections.Counter(d['finish_reason']) for d in dd), collections.Counter())))
    return result


def aggregate(rows, common):
    """Adapt v48's task aggregation, retaining its 33/common-31 counts and precision."""
    result = {}
    for input_set in ('decisive', 'llm_code'):
        result[input_set] = {}
        for first, second in (('primary', 'finishing'), ('tc_full', 'consensus')):
            adapted = [dict(case_id=r['case_id'], arms={a: dict(vote=m[first], consensus=m[second])
                       for a, m in r['input_sets'][input_set].items()}) for r in rows]
            totals = E.aggregate(adapted, common)
            for arm, rules in totals.items():
                target = result[input_set].setdefault(arm, {})
                for old, rule in (('vote', first), ('consensus', second)):
                    target[rule] = rules[old]
                    for mode, m in target[rule].items():
                        m['confirmed_tests'] = m['correct_assertions']
                        m['eligible_inputs'] = sum(r['input_sets'][input_set][arm][rule][mode]['eligible_inputs'] for r in rows)
                        m['reference_skipped_tests'] = sum(r['input_sets'][input_set][arm][rule][mode]['reference_skipped_tests'] for r in rows)
    return result


def comparison(rows, a, b, input_set='decisive'):
    def m(r, arm):
        return r['input_sets'][input_set][arm]['primary']['capped']
    awins = [r for r in rows if m(r, a)['confirmed_tasks'] and not m(r, b)['confirmed_tasks']]
    bwins = [r['case_id'] for r in rows if m(r, b)['confirmed_tasks'] and not m(r, a)['confirmed_tasks']]
    margin = sum(m(r, a)['confirmed_tasks'] - m(r, b)['confirmed_tasks'] for r in rows)
    net = collections.Counter()
    for r in rows:  # per-problem net, so one problem's tasks cannot supply the whole margin
        net[r['problem_id']] += m(r, a)['confirmed_tasks'] - m(r, b)['confirmed_tasks']
    spans = sorted(pid for pid, v in net.items() if v > 0)
    checks = dict(confirmed_task_margin=margin >= 3, extra_problem_span=len(spans) >= 3,
                  fa_no_worse=sum(m(r, a)['fa_tests'] for r in rows) <= sum(m(r, b)['fa_tests'] for r in rows))
    return dict(verdict='GO' if all(checks.values()) else 'NO-GO', checks=checks, task_margin=margin,
                a_only_tasks=[r['case_id'] for r in awins], b_only_tasks=bwins, extra_problems=spans,
                extra_problem_count=len(spans))


@contextmanager
def reference_root(root):
    old = E.OUT
    E.OUT = root
    try:
        yield
    finally:
        E.OUT = old


def task_truth(inv, case, record, official, diag):
    """Score-only v48 adapter: official reach only on `diag` (menu ∪ llm_code inputs, as v48 Amendment 2); emitted
    tests of every family are still judged on the official path."""
    view = dict(inputs={lit: dict(put=r['put'], vote=None, consensus=None) for lit, r in record['inputs'].items()})
    with reference_root(OUT):
        truth = E.reference_truth(inv, case, view, official, diag)
    for lit, t in truth.items():  # lazy official check for emitted tests outside `diag` (never serialized)
        put = E.iorel.value(record['inputs'][lit]['put'])
        cache = [] if t['exposing'] is None else [t['exposing']]

        def exposes(lit=lit, t=t, put=put, cache=cache):
            if not cache:
                cache.append(bool(t['valid'] and put is not None and t['ref'] is not None and not E.same(put, t['ref'])
                                  and E.iorel.official_exposes(official, case, lit)))
            return cache[0]
        t['exposes'] = exposes
    return truth


def score_inputs(inv):
    """Preflight every record, execution hash and input/pick digest before any reference load."""
    state = status(inv)
    cohort, tc_tasks = E.planned(inv)
    missing = [cid for cid in cohort if not (OUT / 'tasks' / f'{cid}.json').is_file()]
    if not state['complete'] or missing:
        return dict(verdict='incomplete', status=state, missing_execution=missing), None
    prep = inv.read(E.select.OUT / 'prepared.json')
    cases = E.tool_cases(inv, cohort)
    records, picks = {}, {}
    for cid in cohort:
        record = inv.read(OUT / 'tasks' / f'{cid}.json')
        for name, sha in record['artifact_sha256'].items():
            p = inv.add(E.REPO / name)
            if inv.files[E.rel(p)] != sha:
                raise ValueError('execution input changed: ' + name)
        expected = E.ordered(E.all_inputs(prep[cid]) | set(E.pool_subset(E.pool_inputs(inv, cid), cid)))
        if record['input_sha256'] != digest(expected) or set(record['inputs']) != set(expected) or record['problem_id'] != problem_id(cases[cid]):
            raise ValueError('execution input universe/problem differs: ' + cid)
        for arm in FAMILIES:
            loaded = programs(inv, cases[cid], arm, tc_tasks)
            family = record['families'][arm]
            for key in ('planned', 'present', 'missing', 'context_overflow', 'finish_reason'):
                if loaded[key] != family[key]:
                    raise ValueError('execution program coverage differs: ' + cid + '/' + arm)
            if family['missing']:
                raise ValueError('incomplete execution programs: ' + cid + '/' + arm)
        choices, _ = E.selections(inv, cases[cid], prep[cid], E.pool_subset(E.pool_inputs(inv, cid), cid))
        picks[cid] = next(choices['llm_code'][1])
        if not picks[cid] <= set(expected):
            raise ValueError('report inputs outside universe: ' + cid)
        records[cid] = record
    if len({r['problem_id'] for r in records.values()}) != 24:
        raise ValueError('registered 24 distinct problem statements differ')
    return None, (cohort, tc_tasks, records, picks)


def score():
    inv = Inventory()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        incomplete, ready = score_inputs(inv)
        if incomplete:
            incomplete['artifact_sha256'] = inv.finish()
            (OUT / 'score_incomplete.json').write_text(json.dumps(incomplete, indent=2) + '\n')
            print(json.dumps(incomplete, indent=2))
            return 1
        cohort, tc_tasks, records, picks = ready
        # This is the only evaluator loader in v49. Its caches and new references are v49-owned.
        run = E.ft_run.FTRun('vibepass_half')
        for name in ('humaneval_mbpp_plus.jsonl', 'humaneval_mbpp.jsonl', 'tasks.json'):
            inv.add(E.DATA / name)
        official = E.Reference(run)
        official.root = OUT / 'references' / 'official'
        cases = {c['case_id']: c for c in run.cases}
        prep = inv.read(E.select.OUT / 'prepared.json')
        rows = []
        for cid in cohort:
            rec = records[cid]
            truth = task_truth(inv, cases[cid], rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
            family_rows = {a: oracle_rows(rec, a) for a in FAMILIES}
            sets, paired, subset_meta, cross = {}, {}, {}, {}
            for input_set, inputs in (('decisive', set(rec['inputs'])), ('llm_code', picks[cid])):
                sets[input_set] = {a: metrics(inputs, family_rows[a], truth, len(rec['families'][a]['valid_programs'])) for a in FAMILIES}
                subset_meta[input_set], sets[input_set]['tc_k5'] = subset_mean(rec, inputs, truth)
                paired[input_set] = {}
                for a, b in itertools.combinations(FAMILIES, 2):
                    eligible = inputs if all(len(rec['families'][f]['valid_programs']) >= 2 for f in (a, b)) else set()
                    eligible = {lit for lit in eligible if E.put_ok(rec['inputs'][lit])}
                    paired[input_set][a + '_vs_' + b] = dict(inputs=len(eligible), families={
                        f: metrics(eligible, family_rows[f], truth, len(rec['families'][f]['valid_programs'])) for f in (a, b)})
                for peer in ARMS:
                    paired[input_set][peer + '_vs_tc_k5'] = paired_k5(rec, inputs, truth, peer)
                # Original prereg's defn∧tc report: the primary defn value must match some valid tc output.
                cross_rows = {lit: dict(r) for lit, r in family_rows['defn'].items()}
                for lit, r in cross_rows.items():
                    if r['primary'] is not None and not any(E.iorel.value(o) is not None and E.same(E.iorel.value(r['primary']), E.iorel.value(o))
                                                            for o in family_rows['tc'][lit]['programs']):
                        r['primary'] = None
                cross[input_set] = metrics(inputs, cross_rows, truth, len(rec['families']['defn']['valid_programs']))['primary']
            candidates = []
            if sets['decisive']['defn']['primary']['capped']['confirmed_tasks'] and not sets['decisive']['brute']['primary']['capped']['confirmed_tasks']:
                labels = labels_for(family_rows['defn'], truth)
                for lit in E.emitted(rec['inputs'], family_rows['defn'], 'primary', 20):
                    if labels[lit]['primary'] == 'confirmed':
                        expected = family_rows['defn'][lit]['primary']
                        supporters = [i for i, o in rec['inputs'][lit]['programs']['defn'].items()
                                      if E.iorel.value(o) is not None and E.same(E.iorel.value(o), E.iorel.value(expected))]
                        candidates.append(dict(input=lit, expected=expected, majority_programs=supporters,
                                               enumeration_audit='pending', concept_correctness_audit='pending'))
            rows.append(dict(case_id=cid, problem_id=rec['problem_id'], input_sets=sets, paired=paired,
                             tc_k5=subset_meta, defn_and_tc=cross,
                             manual_audit_candidates=candidates,
                             diagnostics={a: diagnostics(rec, a, family_rows[a], truth) for a in FAMILIES}))
        totals = aggregate(rows, tc_tasks)
        paired_totals = {}
        for input_set in ('decisive', 'llm_code'):
            paired_totals[input_set] = {}
            for pair in rows[0]['paired'][input_set]:
                adapted = [dict(case_id=r['case_id'], input_sets={s: r['paired'][input_set][pair]['families']
                           for s in ('decisive', 'llm_code')}) for r in rows]
                paired_totals[input_set][pair] = aggregate(adapted, tc_tasks)['decisive']
        decisions = dict(primary=comparison(rows, 'defn', 'brute'), secondary=comparison(rows, 'brute', 'plain'),
                         defn_vs_tc=dict(comparison(rows, 'defn', 'tc'), report_only=True))
        summary = dict(tasks=len(rows), distinct_problems=len({r['problem_id'] for r in rows}), families=totals,
                       decision=decisions, paired=paired_totals, generation=status(inv),
                       diagnostics=diagnostic_totals(rows),
                       manual_audit_required=decisions['primary']['a_only_tasks'],
                       concept_attribution='pending_manual_audit' if decisions['primary']['a_only_tasks'] else 'no_defn_only_wins',
                       attribution='A defn-only win needs manual enumeration and concept-comment correctness audit.',
                       common_mode_definition='Nonempty finishing valid programs all equal PUT; denominator is all exposing inputs.',
                       tc_k5_precision='Ratio of expected confirmed tests to expected tests; task metrics are exact subset means.')
        inv.tree(OUT / 'exec')
        inv.tree(OUT / 'references')
        inventory = inv.finish()
        immutable(OUT / 'inventory.json', inventory)
        immutable(OUT / 'score.json', dict(summary=summary, rows=rows, artifact_sha256=inventory))
        print(json.dumps(summary, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        result = dict(verdict='incomplete', error=f'{type(exc).__name__}: {exc}', artifact_sha256=dict(sorted(inv.files.items())))
        (OUT / 'score_incomplete.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=('status', 'execute', 'score'))
    ap.add_argument('--tasks', help='execute smoke only, e.g. 3,46 (partial records allowed)')
    args = ap.parse_args()
    if args.tasks is not None and args.command != 'execute':
        ap.error('--tasks is restricted to execute smoke')
    if args.command == 'status':
        print(json.dumps(status(), indent=2))
        return 0
    if args.command == 'execute':
        return execute(args.tasks.split(',') if args.tasks is not None else None)
    return score()


if __name__ == '__main__':
    raise SystemExit(main())
