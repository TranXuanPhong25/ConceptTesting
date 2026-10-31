"""Read-only v82 lifecycle and generation-freeze monitor."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import json,hashlib,os,time

HERE=Path(__file__).resolve().parent
RUNREC=HERE/'CURRENT_RUN_V82.json'


def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def main():
    run=json.loads(RUNREC.read_text());root=Path(run['run_root'])
    while True:
        ledger=json.loads((root/'transport/cost.json').read_text()) if (root/'transport/cost.json').exists() else {'entries':{}}
        entries=list(ledger['entries'].values());completed=[]
        cohort=json.loads((root/'protocol.json').read_text())['cohort']['task_ids']
        for task in cohort:
            if all((root/'humaneval/generation/artifacts'/str(task)/'0'/arm/'result.json').exists() for arm in run['arms']):completed.append(task)
            else:break
        status={'status':'terminal' if (root/'terminal.json').exists() else 'running',
                'updated_utc':datetime.now(timezone.utc).isoformat(),'planned_tasks':28,
                'complete_paired_tasks':completed,'attempts':len(entries),
                'received_responses':sum(e['state']=='received' for e in entries),
                'upstream429_attempts':sum(e['state']=='upstream_rejected_unbilled' for e in entries),
                'unknown_attempts':sum(e['state']=='unknown' for e in entries),
                'known_cost_usd':str(sum((Decimal(e['cost_usd']) for e in entries if e.get('cost_usd') is not None),Decimal(0))),
                'unresolved_reservation_usd':str(sum((Decimal(e['reserved_usd']) for e in entries if e.get('cost_usd') is None),Decimal(0))),
                'new_cap_usd':run['new_budget_usd']}
        write(HERE/'STATUS_V82.json',status)
        if (root/'terminal.json').exists():
            protocol=json.loads((root/'protocol.json').read_text());frozen=json.loads((root/'generation_frozen.json').read_text())
            source=root.parents[1]
            assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in protocol['sources'].items())
            assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
            scorepath=root/'humaneval'/('generation' if json.loads((root/'terminal.json').read_text())['generation_complete'] else 'paired_subset')/'score.json'
            result={'terminal':json.loads((root/'terminal.json').read_text()),'status':status,
                    'source_and_generation_freeze_verified':True,'generation_freeze_entries':len(frozen),
                    'scores':json.loads(scorepath.read_text()) if scorepath.exists() else None}
            write(HERE/'RESULTS_V82.json',result)
            (HERE/'RESULTS_V82.md').write_text(
                '# v82 full HumanEval quarter\n\n'
                f"Status: {result['terminal']['status']}; complete paired tasks {len(completed)}/28.\n\n"
                f"Known new-run bill ${status['known_cost_usd']}; unresolved reservation ${status['unresolved_reservation_usd']}; new cap $3.47684946.\n\n"
                f"Stop reason: {result['terminal']['stop_reason']}.\n\n"
                'Two arms: concept-hybrid and concept-hybrid-ft; K1; DeepInfra/fp8; max output32768.\n'
                'Primary ref uses fixed reference-program replacement outputs; secondary o0 uses model-written expected values.\n'
                'Incomplete paired-prefix result is descriptive and has no efficacy verdict.\n')
            break
        try:os.kill(run['pid'],0)
        except ProcessLookupError:
            write(HERE/'MONITOR_V82_ERROR.json',{'reason':'runner exited without terminal','status':status});break
        time.sleep(30)


if __name__=='__main__':main()
