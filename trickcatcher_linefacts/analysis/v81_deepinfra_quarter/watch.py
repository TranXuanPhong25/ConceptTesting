"""Local-only lifecycle/cost monitor; never dispatch or resume model calls."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import json,hashlib,os,time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def main():
    current=json.loads((HERE/'CURRENT_RUN.json').read_text());root=Path(current['run_root'])
    while True:
        ledger=json.loads((root/'transport/cost.json').read_text()) if (root/'transport/cost.json').exists() else {'entries':{}}
        entries=list(ledger['entries'].values())
        paired=[]
        for n in json.loads((root/'protocol.json').read_text())['cohort']['task_ids']:
            paths=[root/'humaneval/generation/artifacts'/str(n)/'0'/arm/'result.json' for arm in current['arms']]
            if not all(p.exists() for p in paths):break
            paired.append(n)
        status={'updated_utc':datetime.now(timezone.utc).isoformat(),'planned_tasks':28,'complete_paired_tasks':paired,
                'physical_attempts':len(entries),'known_responses':sum(e['state']=='received' for e in entries),
                'known_cost_usd':str(sum((Decimal(e['cost_usd']) for e in entries if e.get('cost_usd') is not None),Decimal(0))),
                'unresolved_reservation_usd':str(sum((Decimal(e['reserved_usd']) for e in entries if e.get('cost_usd') is None),Decimal(0))),
                'generation_or_scoring_active':not (root/'terminal.json').exists()}
        write(HERE/'STATUS.json',status)
        if (root/'terminal.json').exists():
            terminal=json.loads((root/'terminal.json').read_text());protocol=json.loads((root/'protocol.json').read_text())
            frozen=json.loads((root/'generation_frozen.json').read_text())
            source=root.parents[1]
            assert all(hashlib.sha256((source/p).read_bytes()).hexdigest()==h for p,h in protocol['sources'].items())
            assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in frozen.items())
            scoring=root/'humaneval'/('generation' if terminal['generation_complete'] else 'paired_subset')
            results={'terminal':terminal,'status':status,'source_and_generation_freeze_verified':True,
                     'scores':json.loads((scoring/'score.json').read_text()) if (scoring/'score.json').exists() else None}
            write(HERE/'RESULTS.json',results)
            paragraphs=['# v81 terminal results','',f"Generation status: {terminal['status']}; complete paired tasks {len(paired)}/28.",
                        f"Stop reason: {terminal['stop_reason']}; scoring error: {terminal['score_error']}.",
                        f"Known cost ${status['known_cost_usd']}; unresolved reservation ${status['unresolved_reservation_usd']}; cap $4.20.",
                        '','Two arms: concept-hybrid original versus concept-hybrid-ft combined, K1, DeepInfra/fp8.',
                        'Primary ref replaces expected values with frozen reference-program outputs; secondary o0 keeps model assertions.']
            if results['scores']:
                for name,report in results['scores'].items():
                    paragraphs+=['',f"{name}: {json.dumps(report['primary'])}"]
            if not terminal['generation_complete']:paragraphs+=['','Incomplete run: paired prefix only, descriptive; no efficacy GO/NO-GO.']
            paragraphs+=['','See RESULTS.json for all rows and paired denominators. No automatic retry, new tasks, seeds or paid judges.']
            (HERE/'RESULTS.md').write_text('\n'.join(paragraphs)+'\n');break
        try:os.kill(current['pid'],0)
        except ProcessLookupError:
            write(HERE/'MONITOR_FAILURE.json',{'reason':'runner_exited_without_terminal','status':status});break
        time.sleep(30)


if __name__=='__main__':main()
