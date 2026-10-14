"""Archive completed format-repair results without invoking models or scorers."""
import hashlib
import json
from v14_v15_gpu_smoke import ROOT, summarize


def main():
    versions = ('v14_obgraph_py', 'v15_mrconcept_py')
    data = {version: summarize(version) for version in versions}
    lines = [
        '# v14/v15 Python-format repair: completed exploratory results', '',
        '2026-10-14. Frozen 20 dev tasks, K=1, common saved v11 spec-only ref oracle.',
        'These runs are separate from the original zero-card smoke. No held-out evaluation.',
        'Execution overlapped CPU-heavy B4, was interrupted by HTTP 404, and resumed from cache.', '',
    ]
    for version, result in data.items():
        out = ROOT / 'pipelines' / version / 'out/humaneval/experiment_smoke'
        proposals = [json.loads(p.read_text()) for p in (out / 'proposals').glob('*/summary.json')]
        result['proposal']['accepted_before_top3'] = sum(len(p['cards']) for p in proposals)
        result['report_sha256'] = hashlib.sha256((out / 'report.json').read_bytes()).hexdigest()
        result['protocol_sha256'] = hashlib.sha256((out / 'protocol.json').read_bytes()).hexdigest()
        p = result['proposal']
        lines += [f'## {version}', '',
                  f"{p['accepted_before_top3']} accepted cards; {p['shown']} shown cards on "
                  f"{p['tasks_with_shown']}/20 tasks; {p['witnessed']} shown cards with eligible witnesses.", '',
                  '| Arm | D_IO tasks/20 | Precision | Slots with card | Inputs/task |',
                  '|---|---:|---:|---:|---:|']
        for arm, metrics in result['arms'].items():
            cost = result['costs'][arm]
            precision = 'n/a' if metrics['precision'] is None else f"{metrics['precision']:.3f}"
            lines.append(f"| {arm} | {metrics['D_IO_samples']} | {precision} | "
                         f"{cost['slots_with_card']} | {cost['mean_input_calls']:.2f} |")
        lines += ['', 'Primary comparisons (nominal exploratory p-values):']
        for c in result['primary']:
            lines.append(f"- matched={c['matched']}: {c['first']} vs {c['second']}; "
                         f"wins/losses {c['wins']}/{c['losses']}, p={c['sign_p']:.4f}; "
                         f"detection means {c['detecting_samples'][0]:.2f}/{c['detecting_samples'][1]:.2f}.")
        lines += ['', 'Property checks, distinct from the common-ref detection endpoint:', '',
                  '| Arm | Checked records | Candidate reports | Confirmed | False alarms | Abstentions |',
                  '|---|---:|---:|---:|---:|---:|']
        for arm, prop in result['property_oracle'].items():
            lines.append(f"| {arm} | {prop['records']} | {prop['candidate_reports']} | "
                         f"{prop['confirmed_reports']} | {prop['false_alarms']} | {prop['abstains']} |")
        lines += ['', 'Recorded physical requests/tokens (keepalive excluded):',
                  '```json', json.dumps(result['physical_requests'], indent=2), '```', '']
    lines += [
        '## Interpretation', '',
        'Format guidance enabled some structurally accepted proposals. Neither primary contrast shows a',
        'detection advantage in this small exploratory cohort. Graph treatment coverage is sparse (3/20 tasks).',
        'MR coverage is broader (16/20), but candidate property violations produced no confirmed reports on',
        'the selected inputs; some were false alarms against the canonical program. Common-ref detections',
        'remain separate from these property-oracle results. Acceptance is not semantic correctness.',
        'Zero-card slots still use the registered generic fallback; card-slot counts describe availability, including controls that hide guidance.',
        'No promotion or claim of universal graph/MR failure follows from this K=1 smoke.',
        'The JSON includes all comparisons, rejection reasons, costs and artifact hashes.', '',
    ]
    stem = ROOT / 'analysis/v14_v15_format_repair'
    stem.with_suffix('.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    stem.with_suffix('.md').write_text('\n'.join(lines))
    for version, result in data.items():
        print(version, 'cards', result['proposal'], 'requests', result['physical_requests'])


if __name__ == '__main__':
    main()
