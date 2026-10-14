"""Summarize the frozen v14/v15 GPU smoke, including proposal failure and actual request accounting."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def summarize(version):
    base=ROOT/'pipelines'/version
    cfg=read(base/'config.json')
    out=base/'out/humaneval/experiment_smoke'
    report=read(out/'report.json')
    proposals=[read(out/'proposals'/str(t)/'summary.json') for t in cfg['experiment']['task_ids']]
    rows=[json.loads(line) for line in (out/'generation/gen.jsonl').read_text().splitlines()]
    expected={(t,a,s) for t in cfg['experiment']['task_ids'] for a in cfg['arms'] for s in range(cfg['experiment']['k'])}
    assert {(r['task'],r['arm'],r['sample']) for r in rows}==expected and len(rows)==len(expected)
    records=[json.loads(line) for line in (out/'generation/cache/calls.jsonl').read_text().splitlines()]
    successful=[r for r in records if r.get('cache_hit') is False and not r.get('error')]
    proposal_metrics=dict(tasks=len(proposals),parsed=sum(p['parsed'] for p in proposals),
        shown=sum(len(p['shown']) for p in proposals),tasks_with_shown=sum(bool(p['shown']) for p in proposals),
        witnessed=sum(h['witnessed'] for p in proposals for h in p['shown']),
        rejected=dict(collections.Counter(x.get('error',x.get('reason')) for p in proposals for x in p['rejections'])))
    arm_counts={}
    for arm in cfg['arms']:
        rs=[r for r in rows if r['arm']==arm]
        attempts=[a for r in rs for a in r['attempts']]
        arm_counts[arm]=dict(samples=len(rs),logical_calls=sum(r['llm_calls'] for r in rs),
            input_calls=sum(r['input_calls'] for r in rs),mean_input_calls=sum(r['input_calls'] for r in rs)/len(rs),
            slots_with_card=sum(a.get('has_card',False) for a in attempts),
            errors=dict(collections.Counter(a['error'] for a in attempts if a.get('error'))),
            prompt_tokens=sum(q.get('input_tokens',0) for r in rs for q in r['request_ledger']),
            completion_tokens=sum(q.get('output_tokens',0) for r in rs for q in r['request_ledger']))
    first,second=report['primary']
    comparisons=[c for c in report['comparisons'] if c['first']==first and c['second']==second]
    return dict(version=version,scope=report['scope'],proposal=proposal_metrics,
        proposals_sha256=hashlib.sha256(json.dumps(proposals,sort_keys=True).encode()).hexdigest(),
        generation_sha256=hashlib.sha256((out/'generation/gen.jsonl').read_bytes()).hexdigest(),
        reference_provenance=read(out/'oracle/reference_provenance.json'),arms=report['arms'],costs=arm_counts,
        primary=comparisons,comparisons=report['comparisons'],property_oracle=report['property_oracle'],
        physical_requests=dict(successful=len(successful),unique_success_keys=len({r['key'] for r in successful}),
            cache_hits=sum(r.get('cache_hit') is True for r in records),
            failed_attempts=sum(bool(r.get('error')) for r in records),
            prompt_tokens=sum(r.get('n_in',0) for r in successful),
            completion_tokens=sum(r.get('n_out',0) for r in successful)))


def main():
    data={v:summarize(v) for v in ('v14_obgraph','v15_mrconcept')}
    output=ROOT/'analysis/v14_v15_gpu_smoke.json'
    output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    lines=['# v14/v15 GPU exploratory smoke','',
           '2026-10-14. Frozen 20 dev tasks, K=1, Qwen2.5-Coder-7B-Instruct; common saved spec-only ref oracle.',
           'No held-out run. Samples and tasks coincide at K=1; the sign tests are exploratory/nominal.','']
    for ver,r in data.items():
        lines += ['## '+ver,'',
            f"Proposal stage: {r['proposal']['shown']} shown cards across {r['proposal']['tasks_with_shown']}/20 tasks; "
            f"{r['proposal']['witnessed']} witnessed cards.",'',
            '| Arm | D_I tasks | D_IO tasks | Precision | Inputs/task | Generation calls/task |',
            '|---|---:|---:|---:|---:|---:|']
        for a,m in r['arms'].items():
            c=r['costs'][a];precision='n/a' if m['precision'] is None else f"{m['precision']:.3f}"
            lines.append(f"| {a} | {m['D_I_samples']} | {m['D_IO_samples']} | {precision} | "
                         f"{c['mean_input_calls']:.2f} | {c['logical_calls']/c['samples']:.2f} |")
        lines += ['','Primary comparisons:']
        for c in r['primary']:
            lines.append(f"- {c['first']} vs {c['second']}, matched={c['matched']}: "
                         f"{c['detecting_samples'][0]:.2f}/{c['detecting_samples'][1]:.2f}; "
                         f"wins/losses {c['wins']}/{c['losses']}; nominal p={c['sign_p']:.4f}.")
        if not r['proposal']['shown']:
            lines += ['','**No accepted semantic cards.** The concept arms use their registered generic fallback slots.',
                      'Their results do not test the usefulness of a grounded graph or conditional MR reasoning.',
                      'new-toolinput/new-witness-only have no discovered card witnesses.']
        lines += ['','Proposal rejection census:', '```json',json.dumps(r['proposal']['rejected'],indent=2,ensure_ascii=False),'```','',
                  'Physical request accounting (includes proposals; excludes model-list keepalive):',
                  '```json',json.dumps(r['physical_requests'],indent=2),'```','']
    lines += ['## Interpretation limits','',
        'Graph/cards and MR/blind primary contrasts require accepted cards to exercise the intended mechanism.',
        'Schema/purity acceptance is not semantic correctness; finite canonical property checks are reported separately.',
        'toolinput here is the fixed three-strategy-slot adapter, not historical one-call toolinput. Original witness-only',
        'and new witness-pool controls remain distinct. Requests/token usage and generated input counts differ across',
        'comparators; paired random-subset sensitivity is in the JSON. Missing/disagreeing reference outputs abstain.',
        'Raw artifacts stay in each version folder; this tracked summary preserves scope, counts, costs and hashes.','']
    (ROOT/'analysis/v14_v15_gpu_smoke.md').write_text('\n'.join(lines))
    print('Saved tracked v14/v15 summary; no endpoint or credentials.')

if __name__=='__main__':main()
