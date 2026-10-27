"""Local-only v83 progress and terminal integrity monitor."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import json,hashlib,os,time

HERE=Path(__file__).resolve().parent
RUN=HERE/'RUN_V83.json'


def write(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)


def main():
    rec=json.loads(RUN.read_text());root=Path(rec['root']);pipe=root.parents[1]
    while True:
        ledger=json.loads((root/'transport/cost.json').read_text())['entries'] if (root/'transport/cost.json').exists() else {}
        ids=json.loads((root/'protocol.json').read_text())['cohort']['task_ids'];completed=[]
        for task in ids:
            if all((root/'humaneval/generation/artifacts'/str(task)/'0'/arm/'result.json').exists() for arm in rec['arms']):completed.append(task)
            else:break
        status={'status':'terminal' if (root/'terminal.json').exists() else 'running',
                'planned_tasks':28,'complete_paired_tasks':completed,'attempts':len(ledger),
                'received_responses':sum(v.get('state')=='received' for v in ledger.values()),
                '429_attempts':sum(v.get('state')=='upstream_rejected_unbilled' for v in ledger.values()),
                'unknown_attempts':sum(v.get('state')=='unknown' for v in ledger.values()),
                'known_new_run_bill_usd':str(sum((Decimal(v['cost_usd']) for v in ledger.values() if v.get('cost_usd') is not None),Decimal(0))),
                'unresolved_new_run_reserve_usd':str(sum((Decimal(v['reserved_usd']) for v in ledger.values() if v.get('cost_usd') is None),Decimal(0))),
                'hard_new_run_cap_usd':rec['new_cap_usd'],'updated_utc':datetime.now(timezone.utc).isoformat()}
        write(HERE/'STATUS_V83.json',status)
        if (root/'terminal.json').exists():
            protocol=json.loads((root/'protocol.json').read_text());frozen=json.loads((root/'generation_frozen.json').read_text())
            assert all(hashlib.sha256((pipe/n).read_bytes()).hexdigest()==h for n,h in protocol['sources'].items())
            assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
            terminal=json.loads((root/'terminal.json').read_text());scores=None
            scorepath=root/'humaneval'/('generation' if terminal['generation_complete'] else 'paired_subset')/'score.json'
            if scorepath.exists():scores=json.loads(scorepath.read_text())
            report={'terminal':terminal,'status':status,'source_and_generation_freeze':'PASS',
                    'generation_freeze_entries':len(frozen),'scores':scores,
                    'prior_benchmark_known_plus_reserves_usd':'0.74708916',
                    'cumulative_cap_usd':'4.20'}
            write(HERE/'RESULTS_V83.json',report)
            (HERE/'RESULTS_V83.md').write_text(
                '# v83 full Reka HumanEval quarter\n\n'
                f"Terminal status: {terminal['status']}; complete paired prefix {len(completed)}/28.\n\n"
                f"Stop reason: {terminal['stop_reason']}; known new-run bill ${status['known_new_run_bill_usd']}; unresolved reserve ${status['unresolved_new_run_reserve_usd']}.\n\n"
                'Two arms: concept-hybrid and concept-hybrid-ft; K1; Reka; output cap24k.\n'
                'Partial outputs are descriptive and receive no efficacy verdict. Prior v81/v82 exposure remains included under cumulative $4.20 cap.\n')
            break
        try:os.kill(rec['pid'],0)
        except ProcessLookupError:write(HERE/'WATCH_ERROR_V83.json',{'status':status,'reason':'runner exited without terminal'});break
        time.sleep(30)


if __name__=='__main__':main()
