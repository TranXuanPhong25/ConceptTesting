"""v36 LLM localization probe (see PREREG.md). Qwen2.5-Coder-32B on the GPU endpoint, one call per task per arm.
  source <env with QWEN_BASE_URL>; PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v36_llm_localize/probe.py sizes|generate|score
The endpoint URL comes from the environment only and is never written to disk or printed.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import openai

from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run, flow_tools, source_view
from trickcatcher_linefacts.pipelines.v34_ftplacebo.chain_inputs import literal_for_transport
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, numbered, original_context, structure, put_observation, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v36_llm_localize'
CEILING = HERE.parents[1] / 'out' / 'analysis' / 'v35_concept_ceiling' / 'ceiling.json'
MODEL = 'qwen2.5-coder-32b-instruct'
ARMS = ('code', 'cfg')
TYPES = ('BOUNDARY', 'OPERATOR', 'VALUE', 'CALL', 'MISSING_CASE')
SYSTEM = 'Return exactly one JSON object matching the schema. No Markdown.'
INSTR = ('The code below passes its public tests but may still be wrong on other inputs. Find where it is most likely wrong. '
         'Give at most 3 suspect lines, most likely first. For each: the line number in the numbered code, the fault type '
         '(BOUNDARY: off-by-one or wrong comparison bound; OPERATOR: wrong operator; VALUE: wrong constant or variable; '
         'CALL: wrong call or argument; MISSING_CASE: an input class not handled), a short reason, and up to 3 inputs that '
         'satisfy the spec constraints and would make the code return a wrong result because of that line. '
         'Each input is a JSON array of the positional arguments.')
CFG_NOTE = ('structure: the static control-flow structure of the entry function. Each statement id is L<line>; depends_on '
            'lists the branch (condition statement and outcome) that must hold for the statement to run.')
SCHEMA = {'suspects': [{'line': 'int', 'fault_type': '|'.join(TYPES), 'reason': 'str', 'inputs': ['[arg1, arg2, ...]']}]}


def compact(st):
    """One line per statement: `L12 if | x > 0 | <- L10:True`. Same content as flow_run.structure, without limits."""
    if st.get('status') != 'ok':
        return st
    rows = []
    for r in st['statements']:
        dep = r['depends_on'] if isinstance(r['depends_on'], str) else ', '.join(f"{d['source']}:{d['branch']}" for d in r['depends_on'])
        rows.append(f"{r['id']} {r['kind']} | {r['code']}" + (f" | <- {dep}" if dep else '') + ('' if r['reachable'] else ' | unreachable'))
    return rows


def prompt(run, case, arm):
    task = run.task(case)
    ctx = original_context(task)
    if arm == 'cfg':
        session = flow_tools.FlowSession(task, OUT / 'sessions' / case['case_id'], arm='v36')
        ctx = dict(ctx, structure=compact(structure(session)), structure_note=CFG_NOTE)
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps(dict(instruction=INSTR, context=ctx, schema=SCHEMA), ensure_ascii=False)}]


def call(client, case, arm, messages):
    path = OUT / 'calls' / case['case_id'] / f'{arm}.json'
    if path.exists():
        return json.loads(path.read_text())
    r = client.chat.completions.create(model=MODEL, messages=messages, temperature=0, max_tokens=1024, seed=20261020,
                                       response_format={'type': 'json_object'})
    rec = dict(text=r.choices[0].message.content or '', finish_reason=r.choices[0].finish_reason,
               input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens)
    immutable(path, rec)
    return rec


def parse(text):
    try:
        v = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        try:
            v = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            v = {}
    out = []
    for s in (v.get('suspects') or [])[:3] if isinstance(v, dict) else []:
        if not isinstance(s, dict):
            continue
        try:
            line = int(s.get('line'))
        except (TypeError, ValueError):
            line = None
        inputs = [x for x in (s.get('inputs') or [])[:3] if isinstance(x, (list, str))]
        out.append(dict(line=line, fault_type=s.get('fault_type'), inputs=inputs))
    return out


def normalize(item, arity):
    """Arm-neutral: a JSON array is first read as the argument list, then as one value; a string goes to parse_call."""
    for text in ([repr(tuple(item)), repr(item)] if isinstance(item, list) else [item]):
        try:
            return literal_for_transport(flow_tools.parse_call(text, arity))
        except (ValueError, TypeError, SyntaxError, RecursionError):
            continue
    return None


def main():
    cmd = sys.argv[1]
    run = ft_run.FTRun('vibepass_half')
    if cmd == 'sizes':
        for case in run.cases:
            print(case['case_id'], *[len(json.dumps(prompt(run, case, a))) for a in ARMS])
        return
    if cmd == 'generate':
        client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=600, max_retries=3,
                               default_headers={'ngrok-skip-browser-warning': '1'})
        jobs = [(c, a) for c in run.cases for a in ARMS]
        with ThreadPoolExecutor(4) as pool:
            for (c, a), rec in zip(jobs, pool.map(lambda j: call(client, j[0], j[1], prompt(run, j[0], j[1])), jobs)):
                print(c['case_id'], a, rec['finish_reason'], rec['input_tokens'], rec['output_tokens'])
        return
    # score (references enter only here)
    ref = Reference(run)
    ref.root = OUT / 'reference'
    locating = {r['case_id']: set(r['locating_mutant_lines']) for r in json.loads(CEILING.read_text())['rows'] if r['ceiling']}
    pool = {r['case_id']: r['exposing_inputs'] > 0 for r in json.loads(CEILING.read_text())['rows']}
    rows = []
    for case in run.cases:
        cid = case['case_id']
        supported = isinstance(json.loads(prompt(run, case, 'cfg')[1]['content'])['context']['structure'], list)
        for arm in ARMS:
            rec = json.loads((OUT / 'calls' / cid / f'{arm}.json').read_text())
            sus = parse(rec['text'])
            arity = source_view.prepare(case['source'], case['entry'])['arity']
            lits = sorted({lit for s in sus for x in s['inputs'] if (lit := normalize(x, arity))})
            outs = ft_run.execute(OUT / 'exec' / cid / arm, {'put': case['source']}, ['put'], case['entry'],
                                  [eval(x) for x in lits])['put'] if lits else []
            valid = exposing = 0
            for lit, o in zip(lits, outs):
                if not ref.contract_valid(case, lit):
                    continue
                valid += 1
                put = put_observation(dict(status='ok', native_checked=True, execution_status=o[0], output=o[1] if o[0] == 'ok' else None,
                                           exception_type=o[1] if o[0] == 'exception' else 'None')) if o[0] in ('ok', 'exception') else None
                truth = ref(case, lit)
                exposing += put is not None and truth is not None and not same(put, truth)
            lines = [s['line'] for s in sus]
            loc = locating.get(cid)
            rows.append(dict(case_id=cid, arm=arm, cfg_supported=supported, template_pool_exposes=pool[cid], parsed=bool(sus), finish=rec['finish_reason'], inputs=len(lits), valid_inputs=valid,
                             exposing_inputs=exposing, locatable=loc is not None,
                             hit1=bool(loc) and bool(lines) and lines[0] in loc, hit3=bool(loc) and any(l in loc for l in lines)))
    summary = {a: dict(parsed=sum(r['parsed'] for r in rows if r['arm'] == a),
                       exposure_tasks=sum(r['exposing_inputs'] > 0 for r in rows if r['arm'] == a),
                       valid_inputs=sum(r['valid_inputs'] for r in rows if r['arm'] == a),
                       inputs=sum(r['inputs'] for r in rows if r['arm'] == a),
                       hit1=sum(r['hit1'] for r in rows if r['arm'] == a), hit3=sum(r['hit3'] for r in rows if r['arm'] == a),
                       locatable=sum(r['locatable'] for r in rows if r['arm'] == a)) for a in ARMS}
    sup = [r for r in rows if r['cfg_supported']]
    exp = {a: {r['case_id'] for r in sup if r['arm'] == a and r['exposing_inputs']} for a in ARMS}
    hit3 = {a: sum(r['hit3'] for r in sup if r['arm'] == a) for a in ARMS}
    pool_sup = sum(r['template_pool_exposes'] for r in sup if r['arm'] == 'code')
    paired = dict(wins=sorted(exp['cfg'] - exp['code']), losses=sorted(exp['code'] - exp['cfg']))
    promising = len(paired['wins']) > len(paired['losses']) and hit3['cfg'] >= hit3['code'] and len(exp['cfg']) >= pool_sup
    report = dict(summary=summary, cfg_supported=len(sup) // len(ARMS),
                  gate=dict(paired_exposure_cfg_vs_code=paired, exposure_tasks={a: len(v) for a, v in exp.items()},
                            template_pool_exposure_tasks=pool_sup, hit3=hit3),
                  verdict='promising' if promising else 'no-go', rows=rows)
    immutable(OUT / 'score.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=1))


if __name__ == '__main__':
    main()
