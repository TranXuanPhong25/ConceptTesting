"""v53: v34 fault-template loop with Claude Sonnet subagents as the LLM (see PREREG.md).

The v34 pipeline is used unchanged; only the client is swapped for a file client. Each LLM call becomes a request file;
one fresh Sonnet subagent per request writes the raw answer file; `wave` is rerun until no request is pending
(the FlowSession ledgers replay earlier rounds deterministically).

Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_sonnet_tester/run.py wave    # writes pending.json
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_sonnet_tester/run.py score   # after freeze
"""
import collections
import hashlib
import json
import shutil
import sys
from pathlib import Path

from trickcatcher_linefacts.pipelines.v34_ftplacebo import flow_tools, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, parse_expected, put_observation, same, validate

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'trickcatcher_linefacts/out/analysis/v53_sonnet_tester'
V34 = ft_run.DATA_OUT / 'faulttemplate' / 'openrouter' / 'vibepass_half'
TASKS = ('141', '39', '56', '36', '132', '70')  # PREREG rule
ARMS = ('plain', 'fault-template', 'template-placebo')
STAGES = ('round1', 'round2', 'final')
# Verbatim prompt given to every Sonnet subagent ({request}/{response} = absolute paths); identical for all arms.
WRAPPER = ('You are acting as a JSON-only chat model inside a research pipeline. Use the Read tool on exactly this file:\n{request}\n'
           'It contains a SYSTEM MESSAGE and a USER MESSAGE exactly as they are sent to a chat model. Answer the USER MESSAGE as '
           'that model, obeying the SYSTEM MESSAGE: the answer is exactly one JSON object matching the schema given in the user '
           'message. Then use the Write tool to write ONLY that JSON object (no prose, no Markdown fences) to:\n{response}\n'
           'Rules: use only Read on that one request file and Write on that one response path. Do not read, list or search any '
           'other file; do not run commands or execute code; reason in your head. Reply with just "done".')


class Pending(Exception):
    pass


class FileClient:
    """complete() returns the subagent's answer if its file exists; otherwise writes the request and raises Pending."""

    def complete(self, req):
        name = req['slot'].split('/', 1)[1].replace('/', '_')  # <task>_<arm>_<round1|round2|final>-<prompt digest16>
        resp = OUT / 'responses' / f'{name}.txt'
        if resp.exists():
            return dict(text=resp.read_text(encoding='utf-8'), input_tokens=0, output_tokens=0, cost_usd=0.0, finish_reason='stop')
        reqp = OUT / 'requests' / f'{name}.txt'
        if not reqp.exists():
            reqp.parent.mkdir(parents=True, exist_ok=True)
            system, user = req['messages']
            reqp.write_text(f"=== SYSTEM MESSAGE ===\n{system['content']}\n\n=== USER MESSAGE ===\n{user['content']}\n", encoding='utf-8')
        raise Pending(dict(request=str(reqp), response=str(resp)))


class SonnetRun(ft_run.FTRun):
    def __init__(self):
        super().__init__('vibepass_half', client=FileClient(), model='sonnet')
        self.root = OUT / 'run'
        self.cases = [c for c in self.cases if c['case_id'] in TASKS]
        assert sorted(c['case_id'] for c in self.cases) == sorted(TASKS)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def copy_tools(run):
    for cid in TASKS:
        src, dst = V34 / 'cases' / cid / 'tool.json', run.root / 'cases' / cid / 'tool.json'
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        if sha(src) != sha(dst):
            raise SystemExit(f'tool.json differs from v34 for {cid}')


def wave():
    run = SonnetRun()
    copy_tools(run)
    immutable(OUT / 'protocol.json', dict(tasks=list(TASKS), arms=list(ARMS), pipeline_sources=ft_run.source_hashes(),
                                          tool_sha256={cid: sha(V34 / 'cases' / cid / 'tool.json') for cid in TASKS},
                                          writer='Claude Sonnet subagent (Claude Code model: sonnet), one per call'))
    immutable(OUT / 'subagent_prompt.json', dict(wrapper=WRAPPER, model='sonnet', resume_note=(
        'after a rate-limit interruption the same subagent was resumed with: "Your run was interrupted by a rate limit; please '
        'continue the same task now: Read your request file, write only the JSON answer to your response path (same rules as '
        'before), reply \\"done\\"."')))
    pending, done = [], 0
    for case in run.cases:
        task = run.task(case)
        common = flow_tools.FlowSession(task, run.root / 'cases' / case['case_id'] / 'common', arm='common')
        views = common.discover(case['witnesses'])
        tool = json.loads((run.root / 'cases' / case['case_id'] / 'tool.json').read_text())
        for arm in ARMS:
            try:
                run.ft_arm(case, task, tool, common, views, arm)
                done += 1
            except Pending as p:
                pending.append(p.args[0])
    (OUT / 'pending.json').write_text(json.dumps(pending, indent=1))
    print(f'arms done {done}/{len(TASKS) * len(ARMS)}, pending requests {len(pending)}')
    if not pending:
        files = sorted([*(OUT / 'responses').glob('*.txt'), *(run.root / 'cases').glob('*/arms/*/result.json'),
                        *(run.root / 'cases').glob('*/tool.json'), OUT / 'protocol.json', OUT / 'subagent_prompt.json'])
        immutable(OUT / 'frozen.json', {str(p.relative_to(OUT)): sha(p) for p in files})
        print('frozen')


def guidance_inputs(tool):
    return {r['input'] for con in tool['concepts'] for r in con['inputs']}


def confirmed_inputs(ref, case, rec):
    """Inputs of confirmed tests, with exactly the confirmed branch of v34 score_record."""
    arity = ft_run.source_view.prepare(case['source'], case['entry'])['arity']
    expected = {}
    for t in (rec.get('final') or {}).get('tests', []):
        try:
            lit = ft_run.literal_for_transport(flow_tools.parse_call(t['arguments'], arity))
        except (ValueError, TypeError):
            continue
        expected.setdefault(lit, t['expected'])
    out = []
    for ex in rec.get('final_executions') or []:
        if ex.get('status') != 'ok' or ex.get('domain_filter') != 'accepted' or not ref.contract_valid(case, ex['input']):
            continue
        put, truth = put_observation(ex), ref(case, ex['input'])
        exp = parse_expected(expected.get(ex['input'], ''))
        if put is not None and truth is not None and exp is not None and not same(put, truth) and same(exp, truth):
            out.append(ex['input'])
    return out


def check_recorded(run):
    """Amendment 1 (review M1): each recorded value must equal the validated response file (no partial read)."""
    by_stage = collections.defaultdict(list)
    for p in (OUT / 'responses').glob('*.txt'):
        cid, arm, rest = p.stem.split('_', 2)
        by_stage[(cid, arm, rest.split('-')[0])].append(p)
    for cid in TASKS:
        for arm in ARMS:
            rec = json.loads((run.root / 'cases' / cid / 'arms' / arm / 'result.json').read_text())
            recorded = [rec['rounds'][0]['value'], rec['rounds'][1]['value'], rec['final']]
            for stage, value in zip(STAGES, recorded):
                files = by_stage[(cid, arm, stage)]
                if len(files) != 1:
                    raise SystemExit(f'{cid}/{arm}/{stage}: {len(files)} response files')
                try:
                    fresh = validate('final' if stage == 'final' else 'probe', files[0].read_text(encoding='utf-8'))
                except ValueError:
                    fresh = None
                if fresh != value:
                    raise SystemExit(f'{cid}/{arm}/{stage}: recorded value differs from the response file')


def score():
    run = SonnetRun()
    frozen = OUT / 'frozen.json'
    if not frozen.exists():
        raise SystemExit('not frozen: run wave until no request is pending')
    for rel, h in json.loads(frozen.read_text()).items():
        if sha(OUT / rel) != h:
            raise SystemExit('frozen artifact changed: ' + rel)
    if json.loads((OUT / 'protocol.json').read_text())['pipeline_sources'] != ft_run.source_hashes():
        raise SystemExit('v34 pipeline sources changed')
    copy_tools(run)  # re-checks every tool.json against v34 (sha256)
    check_recorded(run)
    ref = Reference(run)
    v34 = {(r['case_id'], r['arm']): r for r in json.loads((V34 / 'score.json').read_text())['rows']}
    rows = []
    for case in run.cases:
        tool = json.loads((run.root / 'cases' / case['case_id'] / 'tool.json').read_text())
        gin = guidance_inputs(tool)
        for arm in ARMS:
            rec = json.loads((run.root / 'cases' / case['case_id'] / 'arms' / arm / 'result.json').read_text())
            stats = ft_run.score_record(ref, case, arm, rec)
            conf = confirmed_inputs(ref, case, rec)
            assert len(conf) == stats.get('confirmed_detection', 0), (case['case_id'], arm)
            q = v34[(case['case_id'], arm)]
            rows.append(dict(case_id=case['case_id'], arm=arm, **stats,
                             schema_errors=sum(1 for c in rec['calls'] if c['error']), errors=rec['errors'],
                             final_tests=len((rec.get('final') or {}).get('tests', [])),
                             confirmed_from_guidance_inputs=sum(i in gin for i in conf),
                             qwen=dict(confirmed=q.get('confirmed_detection', 0), false_alarm=q.get('false_alarm', 0),
                                       input_discrepancy=q.get('input_discrepancy', 0), schema_errors=q.get('schema_errors', 0))))
    summary = {}
    for arm in ARMS:
        rs = [r for r in rows if r['arm'] == arm]
        summary[arm] = dict(tasks_confirmed=sum(1 for r in rs if r.get('confirmed_detection')),
                            confirmed_tests=sum(r.get('confirmed_detection', 0) for r in rs),
                            false_alarms=sum(r.get('false_alarm', 0) for r in rs),
                            tasks_with_false_alarm=sum(1 for r in rs if r.get('false_alarm')),
                            tasks_input_discrepancy=sum(1 for r in rs if r.get('input_discrepancy')),
                            schema_errors=sum(r['schema_errors'] for r in rs),
                            confirmed_from_guidance_inputs=sum(r['confirmed_from_guidance_inputs'] for r in rs),
                            share_from_guidance_inputs=round(sum(r['confirmed_from_guidance_inputs'] for r in rs)
                                                             / max(1, sum(r.get('confirmed_detection', 0) for r in rs)), 3),
                            qwen=dict(tasks_confirmed=sum(1 for r in rs if r['qwen']['confirmed']),
                                      confirmed_tests=sum(r['qwen']['confirmed'] for r in rs),
                                      false_alarms=sum(r['qwen']['false_alarm'] for r in rs),
                                      tasks_with_false_alarm=sum(1 for r in rs if r['qwen']['false_alarm']),
                                      tasks_input_discrepancy=sum(1 for r in rs if r['qwen']['input_discrepancy']),
                                      schema_errors=sum(r['qwen']['schema_errors'] for r in rs)))
    det = {a: {r['case_id'] for r in rows if r['arm'] == a and r.get('confirmed_detection')} for a in ARMS}
    pairs = {f'{a} vs {b}': dict(wins=sorted(det[a] - det[b]), losses=sorted(det[b] - det[a]))
             for a, b in (('fault-template', 'plain'), ('fault-template', 'template-placebo'), ('template-placebo', 'plain'))}
    s = summary
    signal = (s['fault-template']['tasks_confirmed'] >= s['plain']['tasks_confirmed'] + 2
              and s['fault-template']['tasks_confirmed'] >= s['template-placebo']['tasks_confirmed'] + 2
              and s['fault-template']['false_alarms'] <= s['plain']['false_alarms'])
    report = dict(summary=summary, pairs=pairs, signal='concept-help signal' if signal else 'no signal', rows=rows)
    immutable(OUT / 'score.json', report)
    print(json.dumps(dict(summary=summary, pairs=pairs, signal=report['signal']), indent=1))


if __name__ == '__main__':
    {'wave': wave, 'score': score}[sys.argv[1]]()
