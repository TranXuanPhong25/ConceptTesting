"""Read saved JSON/caches only; never invoke a runner, PUT, model, or reference.

Usage: python trickcatcher_linefacts/analysis/concept_mechanism_20261024/HISTORICAL_build.py
"""
import ast
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
L = REPO / 'trickcatcher_linefacts'
OUT = L / 'out'


def read(path):
    return json.loads(path.read_text())


def relative(path):
    return str(path.relative_to(REPO))


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


v34 = OUT / 'pipelines/v34_ftplacebo/humaneval/faulttemplate/openrouter/vibepass_half'
v35 = OUT / 'analysis/v35_concept_ceiling'
v47 = OUT / 'analysis/v47_concept_select'
v49 = OUT / 'analysis/v49_defn_oracle'
score34, score35, score47, score49 = [read(p / f) for p, f in [(v34, 'score.json'), (v35, 'ceiling.json'), (v47, 'score.json'), (v49, 'score.json')]]
problem_of = {r['case_id']: r['problem_id'] for r in score49['rows']}
config = read(L / 'pipelines/v34_ftplacebo/config.json')
dataset = {str(int(r['task_id'].split('/')[1])): r for r in map(json.loads, (REPO / config['vibepass']['root'] / 'humaneval_mbpp_plus.jsonl').read_text().splitlines())}

# Execute only selected parsing/equality helper definitions from the audited source.
ns = dict(ast=ast, math=math, C=config['chain'])
for rel, names in [('chain_inputs.py', {'check_topology', 'parse_literal', 'typed_value', 'parse_arguments', 'literal_for_transport'}), ('flow_tools.py', {'parse_call'}), ('flow_run.py', {'same', '_same_typed', 'parse_expected', 'put_observation'})]:
    tree = ast.parse((L / 'pipelines/v34_ftplacebo' / rel).read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=selected, type_ignores=[]), rel, 'exec'), ns)

cache_missing = []


def cached(source, entry, literal):
    key = digest(dict(source=source, entry=entry, input=literal))
    for root in [v34 / 'reference', v35 / 'reference']:
        p = root / key / 'result.json'
        if p.exists():
            return read(p)
    cache_missing.append(key)
    return None


def truth(cid, literal):
    r = dataset[cid]
    contract = cached(r['prompt'] + r['contract'] + '\n    pass\n', r['entry_point'], literal)
    if contract is None:
        return None, None
    if contract.get('status') != 'ok':
        return False, None
    result = cached(r['prompt'] + r['canonical_solution'], r['entry_point'], literal)
    if result is None:
        return True, None
    if result.get('status') == 'exception':
        return True, ('exception', result['exception_type'])
    if result.get('status') == 'ok' and result.get('output_repr') is not None:
        return True, ('ok', ns['typed_value'](ns['parse_literal'](result['output_repr'], output=True)))
    return True, None


rows34 = {(r['case_id'], r['arm']): r for r in score34['rows']}
discord34 = score34['pairs']['fault-template vs template-placebo']['detection']
discord34_ids = set(discord34['wins'] + discord34['losses'])
mechanism34 = []
for cid in sorted({r['case_id'] for r in score34['rows']}, key=int):
    case = v34 / 'cases' / cid
    tool = read(case / 'tool.json')
    phase_job, phase_result = [read(case / 'tool/phase2' / p) for p in ['job.json', 'result.json']]
    fn = next(n for n in ast.walk(ast.parse(phase_job['sources']['put'])) if isinstance(n, ast.FunctionDef) and n.name == dataset[cid]['entry_point'])
    arity = dict(positional=len(fn.args.posonlyargs) + len(fn.args.args), required=len(fn.args.posonlyargs) + len(fn.args.args) - len(fn.args.defaults),
                 varargs=fn.args.vararg is not None, required_keyword_only=any(x is None for x in fn.args.kw_defaults))
    pool_put = dict(zip(phase_job['inputs'], phase_result['put']))
    selected = set(tool['selected_inputs'])
    exposing, unresolved = [], []
    for lit in sorted(selected):
        valid, expected = truth(cid, lit)
        out = pool_put.get(lit)
        actual = ns['parse_expected'](out[1] if out[0] == 'ok' else 'exception:' + out[1]) if out and out[0] in ('ok', 'exception') else None
        if valid is None or (valid and (actual is None or expected is None)):
            unresolved.append(lit)
        elif valid and not ns['same'](actual, expected):
            exposing.append(lit)
    record = dict(version='v34', case_id=cid, problem_id=problem_of[cid], unit='task x arm; selected-input audit',
                  concept_selected_inputs=len(selected), selected_exposing=len(exposing), selected_unresolved=len(unresolved),
                  obligation_realization='unknown: no semantic obligation checker logged',
                  evidence_parity='confounded: fault-template has alternative_output/site/type/hypothesis, placebo has input+put_output',
                  discordance='concept_win' if cid in discord34['wins'] else 'concept_loss' if cid in discord34['losses'] else 'tie',
                  provenance=[relative(v34 / 'score.json'), relative(case / 'tool.json')], arms={})
    arms = ['fault-template', 'template-placebo'] if cid in discord34_ids else ['fault-template']
    for arm in arms:
        path = case / 'arms' / arm / 'result.json'
        rec = read(path)
        expected_by_input = {}
        for t in (rec.get('final') or {}).get('tests', []):
            try:
                literal = ns['literal_for_transport'](ns['parse_call'](t['arguments'], arity))
            except (ValueError, TypeError):
                continue
            expected_by_input.setdefault(literal, ns['parse_expected'](t['expected']))
        confirmed = []
        unknown = []
        for ex in rec.get('final_executions') or []:
            if ex.get('status') != 'ok' or ex.get('domain_filter') != 'accepted':
                continue
            lit = ex['input']
            valid, target = truth(cid, lit)
            actual, predicted = ns['put_observation'](ex), expected_by_input.get(lit)
            if valid is None or (valid and (actual is None or target is None)):
                unknown.append(lit)
            elif valid and predicted is not None and not ns['same'](actual, target) and ns['same'](predicted, target):
                confirmed.append(lit)
        saved = rows34[cid, arm]
        record['arms'][arm] = dict(confirmed_tests_saved=saved.get('confirmed_detection', 0), confirmed_tests_cache_rechecked=len(confirmed),
                                   confirmed_reusing_selected_inputs=sum(lit in selected for lit in confirmed), unresolved_final=len(unknown),
                                   false_alarm_tests=saved.get('false_alarm', 0), incomplete_calls=saved['incomplete_calls'],
                                   schema_errors=saved['schema_errors'], calls=saved['calls'], input_tokens=saved['input_tokens'],
                                   output_tokens=saved['output_tokens'], cost_usd=saved['cost_usd'], provenance=relative(path))
    mechanism34.append(record)

mechanism49 = []
for r in score49['rows']:
    a = {arm: r['input_sets']['decisive'][arm]['primary']['capped'] for arm in ['defn', 'brute']}
    win = a['defn']['confirmed_tasks'] > a['brute']['confirmed_tasks']
    loss = a['defn']['confirmed_tasks'] < a['brute']['confirmed_tasks']
    mechanism49.append(dict(version='v49', case_id=r['case_id'], problem_id=r['problem_id'], unit='task x oracle family',
                            discordance='concept_win' if win else 'concept_loss' if loss else 'tie',
                            obligation_realization='not measured: oracle-program experiment, not guided input generation',
                            arms={arm: dict(confirmed_tasks=a[arm]['confirmed_tasks'], confirmed_tests=a[arm]['confirmed_tests'],
                                            fa_tests=a[arm]['fa_tests'], valid_programs=r['diagnostics'][arm]['valid_programs']) for arm in a},
                            provenance=[relative(v49 / 'score.json'), relative(v49 / 'tasks' / (r['case_id'] + '.json'))]))

mechanism47 = [dict(version='v47', case_id=r['case_id'], problem_id=problem_of[r['case_id']], unit='task x selector arm',
                    obligation_realization='not measured: fixed menu selection, no generation',
                    arms={a: {k:r[a][k] for k in ['covered3', 'perfect', 'random3', 'first3', 'picks', 'pick_kinds', 'finish']} for a in ['spec+code','spec-only']},
                    provenance=[relative(v47/'score.json'), relative(v47/'prepared.json')]) for r in score47['rows']]

sources = [v34/'score.json', v35/'ceiling.json', v47/'score.json', v47/'prepared.json', v49/'score.json',
           OUT/'analysis/v52_sonnet_defn/score.json', OUT/'analysis/v54_sonnet_mutconcept/score.json']
output = dict(scope='Read-only saved-data audit; no generated-code execution, no model calls, no historical rescore',
              sources={relative(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              denominators=dict(puts=33, unique_put_source_hashes_v34=score34['unique_puts']['n'], distinct_problems=len(set(problem_of.values()))),
              missing_cache_keys=sorted(set(cache_missing)), v34=mechanism34, v47=mechanism47, v49=mechanism49)
(HERE/'HISTORICAL_MECHANISM_ROWS.json').write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n')
print(json.dumps(dict(denominators=output['denominators'], missing_cache_keys=len(output['missing_cache_keys']),
                      v34_discordants=[r['case_id'] for r in mechanism34 if r['discordance']!='tie'],
                      v34_recheck_mismatches=[(r['case_id'],a) for r in mechanism34 for a,x in r['arms'].items() if x['confirmed_tests_saved'] != x['confirmed_tests_cache_rechecked']],
                      v49_discordants=[r['case_id'] for r in mechanism49 if r['discordance']!='tie']), indent=1))
