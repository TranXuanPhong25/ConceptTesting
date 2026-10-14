"""B4 secondary analysis (ref only): which detections come from inputs satisfying a shown hypothesis's T,
from unwitnessed hypotheses and from hypotheses at base-covered sites. Run after rel_report (same executions)."""
import json
from pathlib import Path
from . import hypotheses
from .llm_client import atomic_json


def detects(record):
    ref = record.get('ref', {})
    return bool(record.get('valid') and record.get('d_i') and ref.get('emit') and ref.get('canon_ok'))


def summarize(rows, executions):
    out = {}
    for arm in hypotheses.ARMS:
        group = [r for r in rows if r['arm'] == arm]
        if not group: continue
        c = dict(samples=len(group), d_io_inputs=0, with_t_hit=0, from_unwitnessed=0, from_covered_site=0,
                 from_witnessed_mutant_diff=0, shown=0, shown_unwitnessed=0, shown_covered_site=0)
        for r in group:
            shown = r.get('shown_hypotheses', [])
            c['shown'] += len(shown)
            c['shown_unwitnessed'] += sum(not h['witnessed'] for h in shown)
            c['shown_covered_site'] += sum(h['covered_site'] for h in shown)
            calls = executions.get(str(r['task']), {}).get('calls', {})
            seen = set()
            for rec in r.get('hypothesis_input_records', []):
                call = rec.get('call')
                if call is None or call in seen or call not in calls: continue
                seen.add(call)
                if not detects(calls[call]): continue
                c['d_io_inputs'] += 1
                hit = [shown[i] for i, x in enumerate(rec.get('hypothesis_hits', [])) if x and i < len(shown)]
                c['with_t_hit'] += bool(hit)
                c['from_unwitnessed'] += any(not h['witnessed'] for h in hit)
                c['from_covered_site'] += any(h['covered_site'] for h in hit)
                c['from_witnessed_mutant_diff'] += any(h['witnessed'] and h['mutant_diff'] for h in hit)
        out[arm] = c
    return out


def report(run, oracle):
    run, oracle = Path(run), Path(oracle)
    rows = [json.loads(l) for l in (run/'gen.jsonl').read_text().splitlines()]
    work = oracle/'exec'
    executions = {p.stem: json.loads(p.read_text()) for p in work.glob('*.json') if not p.name.endswith('.job.json')}
    accounting = json.loads((run/'hypotheses'/'proposal_accounting.json').read_text())
    result = dict(oracle='ref', proposal=accounting, attribution=summarize(rows, executions))
    atomic_json(oracle/'hyp_attribution.json', result)
    print(json.dumps(result, indent=2))
    return result
