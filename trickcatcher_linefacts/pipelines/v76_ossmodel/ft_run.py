"""v34 placebo for v31: does the fault concept add anything over its template inputs?

v34 adds `template-placebo`: the same LLM loop and the same template inputs as fault-template, each with put_output,
sorted by input text, with no site, fault type, alternative, alternative_output, hypothesis, evidence, rank or template
name. All other arm records are copied from the frozen v31 run (seed_from_v31.py); only template-placebo is generated.

v31 fault-template run: explicit tool steps instead of implicit LLM reasoning, compared with plain only.

Per task (tool, no LLM, no reference):
  a1  mutants of the PUT (mutmut via v4_tools) -> site line + fault type (ft_concepts.fault_type)
  a2  survivors = mutants with the same outcome as the PUT on every public base input (the public tests cannot tell
      them apart: plausible fixed versions under the competent-programmer assumption)
  b   task-agnostic input templates per fault type applied to the public base inputs (ft_concepts.templates)
  a3  rank concepts (line, fault type) by surviving alternatives that a template input distinguishes; pick <= 3
      concepts x <= 2 inputs, fill to 6 with MISSING_CASE template inputs
Arms: plain and fault-template (same 3 LLM calls: 2 probe rounds with PUT replay + final; fault-template adds the
ranked concepts as guidance), template-only (the <= 6 selected inputs, no LLM, discrepancy only), witness-only.
Scoring after the generation freeze, with the v29 scorer (independent references, contract-invalid = false alarm).

Usage (repo root, PYTHONPATH=., `source scripts/openrouter_env.sh`):
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v34_ftplacebo.ft_run tools --cohort vibepass_half|vibepass|pilot20
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v34_ftplacebo.ft_run generate --cohort vibepass_half|vibepass|pilot20
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v34_ftplacebo.ft_run score --cohort vibepass_half|vibepass|pilot20
"""
import argparse
import ast
import random
import collections
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

from . import flow_run, flow_tools, ft_concepts, source_view
from .chain_inputs import literal_for_transport
from .flow_common import digest, immutable
from .flow_run import INSTR, Reference, message, numbered, original_context, parse_expected, put_observation, same
from .gen_inputs import sandbox
from .paths import CONFIG, DATA_OUT, REPO

FT = CONFIG['faulttemplate']
R = CONFIG['flowrun']
HERE = Path(__file__).resolve().parent
ARMS = tuple(FT['arms'])
LLM_ARMS = tuple(FT['llm_arms'])
PAIRS = (('fault-template', 'template-placebo'), ('template-placebo', 'plain'), ('fault-template', 'plain'))
MUTMUT_LOCK = threading.Lock()
GUIDE_NOTE = ('Tool-derived fault concepts, ranked by tool evidence only (no spec, reference or model involved). Each concept '
              'is a code site and a fault type; an alternative is a small edit of that line that the public tests cannot tell '
              'apart from the code. put_output is what the code returns; alternative_output is what the edited line would '
              'return. Neither is an expected value: decide expected values from the spec only. Template inputs are edits of '
              'the public examples and may violate the spec constraints; do not use inputs outside the constraints.')


def base_inputs(case, name):
    """Public example inputs, parsed from the prompt-visible public asserts (never the evaluator file)."""
    out = [ast.literal_eval(lit) for lit in flow_run.calls_in(case['base'], {case['entry'], 'candidate'})]
    return out[:FT['max_base_inputs']]


def execute(directory, sources, order, entry, inputs):
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / 'job.json', directory / 'result.json'
    if op.exists():
        return json.loads(op.read_text())
    immutable(jp, dict(sources=sources, order=order, entry=entry, inputs=[repr(x) for x in inputs],
                       per_call_timeout=FT['per_call_timeout'], max_timeouts=FT['max_timeouts']))
    try:
        return sandbox(CONFIG['V4_PYTHON'], HERE / 'ft_worker.py', jp, op, FT['phase_timeout'])
    except RuntimeError as exc:  # one bad source must not wipe the phase: retry one process per source
        result = {'_error': str(exc)}
        for name in order:
            sub = directory / 'per_source' / name
            sub.mkdir(parents=True, exist_ok=True)
            sj, so = sub / 'job.json', sub / 'result.json'
            immutable(sj, dict(sources={name: sources[name]}, order=[name], entry=entry, inputs=[repr(x) for x in inputs],
                               per_call_timeout=FT['per_call_timeout'], max_timeouts=FT['max_timeouts']))
            try:
                result[name] = sandbox(CONFIG['V4_PYTHON'], HERE / 'ft_worker.py', sj, so, FT['phase_timeout'])[name]
            except RuntimeError:
                result[name] = [['skipped']] * len(inputs)
        op.write_text(json.dumps(result) + '\n')
        return result


def tool_stage(case, name, root):
    """Deterministic (a)+(b) for one case; cached in tool.json. Uses the PUT and public base inputs only."""
    out = root / 'cases' / case['case_id'] / 'tool.json'
    if out.exists():
        return json.loads(out.read_text())
    from .v4_tools import enumerate_mutants
    work = root / 'cases' / case['case_id'] / 'tool'
    source = case['source']
    lines = source.split('\n')
    masked = source_view.prepare(source, case['entry'])['source_masked'].split('\n')  # what both arms see (no comments)
    seeds = base_inputs(case, name)
    work.mkdir(parents=True, exist_ok=True)
    try:
        with MUTMUT_LOCK:  # enumerate_mutants changes the process cwd: one at a time
            mutants = enumerate_mutants(source, directory=work)
    except Exception as exc:  # unsupported source for mutmut: no site concepts, templates still apply
        mutants = []
        mutant_error = f'{type(exc).__name__}:{str(exc)[:120]}'
    else:
        mutant_error = None
    for m in mutants:
        m['type'] = ft_concepts.fault_type(m, lines[m['line'] - 1] if m['line'] <= len(lines) else '')
    sources = {'put': source, **{f"m{m['k']}": m['mutant_src'] for m in mutants}}
    order = ['put'] + [f"m{m['k']}" for m in mutants]
    phase1 = execute(work / 'phase1', sources, order, case['entry'], seeds) if seeds else {k: [] for k in order}
    put1 = phase1['put']
    survivors = []
    for m in mutants:
        rows = phase1[f"m{m['k']}"]
        comparable = [(a, b) for a, b in zip(put1, rows) if a[0] in ('ok', 'exception')]
        if comparable and all(a == b for a, b in comparable):
            survivors.append(m)
    n_survivors = len(survivors)
    survivors = survivors[:FT['max_survivors']]
    consts = sorted({c for m in survivors if m['type'] == 'BOUNDARY' for c in ft_concepts.site_constants(source, m['line'])},
                    key=lambda c: (abs(c), c))[:8] or [0, 1]
    candidates = []
    for c in ft_concepts.templates(seeds, {'BOUNDARY': consts}):
        try:
            c['literal'] = literal_for_transport(c['args'])
        except (ValueError, TypeError, RecursionError):
            continue
        candidates.append(c)
    order2 = ['put'] + [f"m{m['k']}" for m in survivors]
    phase2 = execute(work / 'phase2', {k: sources[k] for k in order2}, order2, case['entry'], [c['args'] for c in candidates]) \
        if candidates else {k: [] for k in order2}
    put2 = phase2['put']
    mout = {m['k']: phase2[f"m{m['k']}"] for m in survivors}
    groups = ft_concepts.rank(survivors, candidates, put2, mout, masked)
    concepts = ft_concepts.select(groups, candidates, put2, mout, max_concepts=FT['max_concepts'],
                                  per_concept=FT['inputs_per_concept'], max_inputs=FT['max_inputs'])
    for con in concepts:
        for row in con['inputs']:
            c = candidates[row['index']]
            row.update(input=c['literal'], template=c['template'], template_type=c['type'], put_output=put2[row['index']])
    ok_pool = [i for i, o in enumerate(put2) if o and o[0] == 'ok']
    rng = random.Random(f"{FT['random_seed']}/{case['case_id']}")
    random_inputs = [candidates[i]['literal'] for i in sorted(rng.sample(ok_pool, min(FT['max_inputs'], len(ok_pool))))]
    site_rows = [r for con in concepts if con['type'] != 'MISSING_CASE' for r in con['inputs']]
    type_match = sum(r['template_type'] == con['type'] for con in concepts if con['type'] != 'MISSING_CASE' for r in con['inputs'])
    record = dict(case_id=case['case_id'], seeds=len(seeds), random_inputs=random_inputs,
                  concept_template_type_match=[type_match, len(site_rows)], survivors_before_cap=n_survivors, mutants=len(mutants), mutant_error=mutant_error,
                  mutant_types=dict(collections.Counter(m['type'] for m in mutants)), survivors=len(survivors),
                  survivor_types=dict(collections.Counter(m['type'] for m in survivors)), boundary_constants=consts,
                  candidates=len(candidates), candidate_types=dict(collections.Counter(c['type'] for c in candidates)),
                  ranked=[dict(line=g['line'], type=g['type'], survivors=len(g['survivors']), distinguished=g['distinguished'])
                          for g in groups[:12]],
                  concepts=concepts, selected_inputs=[r['input'] for con in concepts for r in con['inputs']],
                  phase_errors=[p.get('_error') for p in (phase1, phase2) if isinstance(p, dict) and p.get('_error')])
    immutable(out, record)
    return record


def outcome_text(o):
    if not o:
        return None
    return o[1] if o[0] == 'ok' else (f'exception:{o[1]}' if o[0] == 'exception' else o[0])


def guidance(tool):
    rows = []
    for rank, con in enumerate(tool['concepts'], 1):
        site = f"L{con['line']}" if con['line'] else None
        if con['type'] == 'MISSING_CASE':
            hyp = 'The code may not handle this input class correctly; check these inputs against the spec.'
        else:
            hyp = (f"If line {con['line']} were written slightly differently (see alternatives), the outputs would differ "
                   f"on these inputs, and the public tests could not tell which version is right.")
        rows.append(dict(rank=rank, fault_type=con['type'], meaning=ft_concepts.TYPE_TEXT[con['type']], site=site, code=con['code'],
                         hypothesis=hyp, alternatives=con['alternatives'],
                         evidence=dict(surviving_alternatives_at_site=con['survivors'], distinguished_by_template_inputs=con['distinguished']),
                         inputs=[dict(input=r['input'], template=r['template'], put_output=outcome_text(r['put_output']),
                                      alternative=r['alternative'], alternative_output=outcome_text(r['alternative_output']))
                                 for r in con['inputs']],
                         provenance='tool_derived'))
    return dict(note=GUIDE_NOTE, fault_concepts=rows)


PLACEBO_NOTE = ('Inputs made by small edits of the public examples. put_output is what the code returns on each input; it is '
                'not an expected value: decide expected values from the spec only. The inputs may violate the spec constraints; '
                'do not use inputs outside the constraints.')


def placebo_guidance(tool):
    """The fault-template inputs without any concept content (no site, type, alternative, hypothesis, rank, template)."""
    rows = {r['input']: dict(input=r['input'], put_output=outcome_text(r['put_output'])) for con in tool['concepts'] for r in con['inputs']}
    return dict(note=PLACEBO_NOTE, inputs=[rows[k] for k in sorted(rows)])


def source_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
            if p.is_file() and p.suffix in ('.py', '.json', '.jinja', '.md') and p.name != 'CHANGELOG.md'}


class FTRun(flow_run.Run):
    def __init__(self, cohort_name, client=None, model='openrouter'):
        self.name = cohort_name
        self.model = model
        self.root = DATA_OUT / 'faulttemplate' / model / cohort_name
        if cohort_name == 'vibepass_half':  # MVP: frozen stratified half (half_split.py, vibepass_half.json)
            keep = set(json.loads((HERE / 'vibepass_half.json').read_text())['tasks'])
            self.cases = [c for c in flow_run.cohort('vibepass') if int(c['case_id']) in keep]
            if len(self.cases) != 33:
                raise ValueError('vibepass_half_size')
        else:
            self.cases = flow_run.cohort(cohort_name)
        self.client = client
        self.lock = threading.Lock()

    def protocol(self):
        import subprocess
        freeze = subprocess.run([CONFIG['V4_PYTHON'], '-m', 'pip', 'freeze'], capture_output=True, text=True).stdout
        refs = {k: hashlib.sha256((REPO / CONFIG['vibepass']['root'] / k).read_bytes()).hexdigest()
                for k in ('humaneval_mbpp.jsonl', 'humaneval_mbpp_plus.jsonl', 'manifest.json')}
        return immutable(self.root / 'protocol.json', dict(
            environment_sha256=hashlib.sha256(freeze.encode()).hexdigest(), evaluator_files_sha256=refs,
            cohort=self.name, arms=list(ARMS), sources=source_hashes(), cases=[c['case_id'] for c in self.cases],
            case_inputs_sha256=digest([{k: c[k] for k in ('case_id', 'source', 'entry', 'base', 'witnesses')} for c in self.cases]),
            model=CONFIG['openrouter'], faulttemplate=FT, flowrun=R, scope='references enter only `score`, after generation_frozen.json'))

    def call(self, slot, stage, messages, seed):
        try:
            return super().call(slot, stage, messages, seed)
        except RuntimeError as exc:  # registered: an exhausted call is an arm error; the arm continues
            if str(exc) != 'openrouter_attempts_exhausted':
                raise
            return None, 'transport_exhausted', dict(input_tokens=0, output_tokens=0)

    def tools(self, workers):
        recs = {}
        with ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(tool_stage, case, self.name, self.root): case['case_id'] for case in self.cases}
            for f in as_completed(futures):
                recs[futures[f]] = f.result()
        return recs

    def ft_arm(self, case, task, tool, common, common_views, arm):
        base = self.root / 'cases' / case['case_id'] / 'arms' / arm
        done = base / 'result.json'
        if done.exists():
            return json.loads(done.read_text())
        session = flow_tools.FlowSession(task, base / 'tools', arm=arm)
        session.adopt(common.traces)
        record = dict(case_id=case['case_id'], arm=arm, calls=[], rounds=[], final=None, errors=[])
        if arm == 'witness-only':
            record['final_executions'] = [c for c in common_views if c.get('status') == 'ok']
            immutable(done, record)
            return record
        if arm in ('template-only', 'template-random'):
            inputs = tool['selected_inputs'] if arm == 'template-only' else tool['random_inputs']
            record['final_executions'] = [c for c in session.discover(inputs) if c.get('status') == 'ok']
            immutable(done, record)
            return record
        seed = R['seed'] + int(hashlib.sha256((case['case_id'] + arm).encode()).hexdigest()[:6], 16)
        slot = f"{self.name}/{case['case_id']}/{arm}"
        ctx = original_context(task)
        if arm == 'fault-template':
            ctx['guidance'] = guidance(tool)
        elif arm == 'template-placebo':
            ctx['guidance'] = placebo_guidance(tool)
        history = []
        for r in (1, 2):  # identical loop for both LLM arms (= v29 plain path: probe, replay without observation ids)
            session.begin_round()
            value, error, response = self.call(f'{slot}/round{r}', 'probe', message(INSTR['probe'], dict(ctx, earlier_feedback=history), 'probe'), seed + r)
            record['calls'].append(dict(empty_answer=not response.get('text','nonempty').strip(), stage='probe', round=r, error=error, input_tokens=response['input_tokens'], output_tokens=response['output_tokens'],
                                        cost_usd=response.get('cost_usd', 0.0), finish_reason=response.get('finish_reason')))
            feedback = []
            if value is None:
                record['errors'].append(f'round{r}:{error}')
            else:
                predictions = {p['arguments']: p for p in value['inputs']}
                for p in value['inputs']:
                    result = session.view(session.act(dict(tool='replay_input', input=p['arguments'])))
                    if p['arguments'] in predictions:
                        result = dict(result, model_expected=p['expected'], model_predicted_actual=p['predicted_actual'])
                    feedback.append(result)
            history.append(dict(round=r, feedback=feedback))
            record['rounds'].append(dict(round=r, value=value, feedback=feedback))
            if len(json.dumps(history, ensure_ascii=False)) > 12000:
                history = [dict(round=h['round'], feedback=h['feedback'][:3], omitted=max(0, len(h['feedback']) - 3)) for h in history]
        value, error, response = self.call(f'{slot}/final', 'final', message(INSTR['final'], dict(ctx, earlier_feedback=history), 'final'), seed + 3)
        record['calls'].append(dict(empty_answer=not response.get('text','nonempty').strip(), stage='final', error=error, input_tokens=response['input_tokens'], output_tokens=response['output_tokens'],
                                    cost_usd=response.get('cost_usd', 0.0), finish_reason=response.get('finish_reason')))
        record['empty_answer_count']=sum(c['empty_answer'] for c in record['calls'])
        if record['empty_answer_count']:
            value,error=None,'empty_answer_arm_failure'
        record['final'] = value
        if value is None:
            record['errors'].append(f'final:{error}')
            record['final_executions'] = []
        else:
            record['final_executions'] = session.final_inputs([t['arguments'] for t in value['tests']][:R['final_tests']])
        record['tool_report'] = session.report()
        if any(c['error'] == 'transport_exhausted' for c in record['calls']):
            raise RuntimeError('transport_exhausted: not recorded; rerun to resume (cached slots are reused)')
        immutable(done, record)
        return record

    def generate(self, workers):
        self.protocol()
        if (self.root / 'generation_frozen.json').exists():
            print('generation already frozen')
            return
        tools = self.tools(FT['tool_workers'])
        prepared, failures = {}, []
        for case in self.cases:
            task = self.task(case)
            common = flow_tools.FlowSession(task, self.root / 'cases' / case['case_id'] / 'common', arm='common')
            views = common.discover(case['witnesses'])
            prepared[case['case_id']] = (case, task, common, views)
        # Finish every arm of one case before beginning the next.
        for cid in prepared:
            for arm in ARMS:
                rec = self.ft_arm(prepared[cid][0], prepared[cid][1], tools[cid], prepared[cid][2], prepared[cid][3], arm)
                print('arm',cid,arm,'errors',rec['errors'],flush=True)
        if failures:
            immutable(self.root / f'failures_{digest(failures)[:8]}.json', failures)
            raise SystemExit(f'{len(failures)} arm jobs failed; rerun to resume; not frozen')
        files = sorted(p for p in (self.root / 'cases').rglob('*.json') if '/executions/' not in str(p) and '/tool/' not in str(p))
        immutable(self.root / 'generation_frozen.json', {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        print('generation frozen')


def score_record(ref, case, arm, rec):
    """Per-execution scoring, identical to v29 flow_run.score."""
    arity = source_view.prepare(case['source'], case['entry'])['arity']
    expected = {}
    if rec.get('final'):
        for t in rec['final']['tests']:
            try:
                lit = literal_for_transport(flow_tools.parse_call(t['arguments'], arity))
            except (ValueError, TypeError):
                continue
            expected.setdefault(lit, t['expected'])
    llm = arm in LLM_ARMS
    stats = collections.Counter()
    for ex in rec.get('final_executions') or []:
        if ex.get('status') != 'ok':
            stats['invalid_inputs'] += 1
            continue
        stats['executed'] += 1
        if ex.get('domain_filter') != 'accepted':
            stats['inadmissible'] += 1
            continue
        if not ref.contract_valid(case, ex['input']):
            stats['contract_invalid'] += 1
            exp = parse_expected(expected.get(ex['input'], '')) if llm else None
            put = put_observation(ex)
            if exp is not None and put is not None and not same(exp, put):
                stats['false_alarm'] += 1
            continue
        stats['admissible'] += 1
        put = put_observation(ex)
        truth = ref(case, ex['input'])
        if put is None or truth is None:
            stats['unscored'] += 1
            continue
        disc = not same(put, truth)
        stats['input_discrepancy'] += disc
        if not llm:
            continue
        exp = parse_expected(expected.get(ex['input'], ''))
        if exp is None:
            stats['unparseable_expected'] += 1
        elif disc and same(exp, truth):
            stats['confirmed_detection'] += 1
        elif disc:
            stats['discrepancy_wrong_expected'] += 1
        elif not same(exp, put):
            stats['false_alarm'] += 1
        else:
            stats['passing_test'] += 1
    return stats


def score(run):
    if not (run.root / 'generation_frozen.json').exists():
        raise SystemExit('generation not frozen')
    for rel, h in json.loads((run.root / 'generation_frozen.json').read_text()).items():
        if hashlib.sha256((run.root / rel).read_bytes()).hexdigest() != h:
            raise SystemExit('frozen artifact changed: ' + rel)
    if json.loads((run.root / 'protocol.json').read_text())['sources'] != source_hashes():
        raise SystemExit('pipeline sources changed since protocol.json (scorer must be the registered one)')
    ref = Reference(run)
    rows = []
    for case in run.cases:
        for arm in ARMS:
            rec = json.loads((run.root / 'cases' / case['case_id'] / 'arms' / arm / 'result.json').read_text())
            stats = score_record(ref, case, arm, rec)
            calls = rec.get('calls', [])
            rows.append(dict(case_id=case['case_id'], arm=arm, **stats, calls=len(calls), schema_errors=sum(1 for c in calls if c['error']),
                             input_tokens=sum(c['input_tokens'] for c in calls), output_tokens=sum(c['output_tokens'] for c in calls),
                             cost_usd=sum(c.get('cost_usd', 0.0) for c in calls),
                             incomplete_calls=sum(1 for c in calls if c.get('finish_reason') not in (None, 'stop'))))
    summary = {}
    for arm in ARMS:
        rs = [r for r in rows if r['arm'] == arm]
        summary[arm] = dict(cases=len(rs), tasks_confirmed=sum(1 for r in rs if r.get('confirmed_detection')),
                            tasks_input_discrepancy=sum(1 for r in rs if r.get('input_discrepancy')),
                            confirmed_tests=sum(r.get('confirmed_detection', 0) for r in rs),
                            false_alarms=sum(r.get('false_alarm', 0) for r in rs),
                            tasks_with_false_alarm=sum(1 for r in rs if r.get('false_alarm')),
                            admissible=sum(r.get('admissible', 0) for r in rs), contract_invalid=sum(r.get('contract_invalid', 0) for r in rs),
                            discrepancy_wrong_expected=sum(r.get('discrepancy_wrong_expected', 0) for r in rs),
                            schema_errors=sum(r['schema_errors'] for r in rs), calls=sum(r['calls'] for r in rs),
                            input_tokens=sum(r['input_tokens'] for r in rs), output_tokens=sum(r['output_tokens'] for r in rs),
                            cost_usd=round(sum(r['cost_usd'] for r in rs), 4), incomplete_calls=sum(r['incomplete_calls'] for r in rs))
    detected = {a: {r['case_id'] for r in rows if r['arm'] == a and r.get('confirmed_detection')} for a in LLM_ARMS}
    discovered = {a: {r['case_id'] for r in rows if r['arm'] == a and r.get('input_discrepancy')} for a in ARMS}
    # Duplicate PUTs (same source sha) count once in the unique-PUT view: keep the first case per sha.
    sha = {c['case_id']: hashlib.sha256(c['source'].encode()).hexdigest() for c in run.cases}
    first = {}
    for c in run.cases:
        first.setdefault(sha[c['case_id']], c['case_id'])
    unique = set(first.values())
    tools = [json.loads((run.root / 'cases' / c['case_id'] / 'tool.json').read_text()) for c in run.cases]
    match = [sum(t['concept_template_type_match'][i] for t in tools) for i in (0, 1)]
    report_unique = dict(n=len(unique), wins=sorted((detected['fault-template'] - detected['plain']) & unique),
                         losses=sorted((detected['plain'] - detected['fault-template']) & unique),
                         confirmed={a: len(detected[a] & unique) for a in LLM_ARMS})
    pairs = {f'{a} vs {b}': dict(detection=dict(wins=sorted(detected[a] - detected[b]), losses=sorted(detected[b] - detected[a])),
                                  discovery=dict(wins=sorted(discovered[a] - discovered[b]), losses=sorted(discovered[b] - discovered[a])),
                                  unique_detection=dict(wins=sorted((detected[a] - detected[b]) & unique), losses=sorted((detected[b] - detected[a]) & unique)))
             for a, b in PAIRS}
    report = dict(cohort=run.name, pairs=pairs, unique_puts=report_unique, concept_template_type_match=match, scope='frozen generation scored with independent references; descriptive, K=1',
                  arms=summary,
                  paired_task_detection=dict(wins=sorted(detected['fault-template'] - detected['plain']),
                                             losses=sorted(detected['plain'] - detected['fault-template'])),
                  paired_task_discovery=dict(wins=sorted(discovered['fault-template'] - discovered['plain']),
                                             losses=sorted(discovered['plain'] - discovered['fault-template'])),
                  detected=dict((a, sorted(v)) for a, v in detected.items()), rows=rows)
    immutable(run.root / 'score.json', report)
    print(json.dumps(dict(arms=summary, pairs=pairs, paired=report['paired_task_detection'], discovery=report['paired_task_discovery'],
                          unique=report_unique, type_match=match), indent=1))
    return report


def tool_summary(run):
    recs = [json.loads((run.root / 'cases' / c['case_id'] / 'tool.json').read_text()) for c in run.cases]
    s = collections.Counter()
    for r in recs:
        s['cases'] += 1
        s['mutant_errors'] += bool(r['mutant_error'])
        s['mutants'] += r['mutants']
        s['survivors'] += r['survivors']
        s['cases_with_site_concept'] += any(c['type'] != 'MISSING_CASE' for c in r['concepts'])
        s['site_concepts'] += sum(c['type'] != 'MISSING_CASE' for c in r['concepts'])
        s['selected_inputs'] += len(r['selected_inputs'])
        s['phase_errors'] += len(r['phase_errors'])
        for c in r['concepts']:
            s['concept_' + c['type']] += 1
    return dict(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=('tools', 'generate', 'score'))
    ap.add_argument('--cohort', choices=('vibepass_half', 'vibepass', 'pilot20'), required=True)
    ap.add_argument('--workers', type=int)
    args = ap.parse_args()
    run = FTRun(args.cohort)
    if args.command == 'tools':
        run.protocol()
        run.tools(args.workers or FT['tool_workers'])
        print(json.dumps(tool_summary(run), indent=1))
    elif args.command == 'generate':
        from .openrouter_client import OpenRouterClient
        run.client = OpenRouterClient(run.root / 'transport')
        try:
            run.generate(args.workers or CONFIG['openrouter']['workers'])
        finally:
            run.client.close()
        print('spent_usd', round(run.client.spent(), 4))
    else:
        score(run)


if __name__ == '__main__':
    main()
