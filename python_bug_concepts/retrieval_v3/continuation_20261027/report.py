"""Completion-aware supplement; leaves the original metric definitions unchanged."""
import json
from pathlib import Path
from ..client import atomic
from ..report import report as original_report
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'out/run_20261026'

def report(out=OUT):
    original_report(out)
    path=out/'QUALITY_SUMMARY.json'
    summary=json.loads(path.read_text())
    jobs=list((out/'utility').glob('*.json'))
    records=[json.loads(p.read_text()) for p in jobs]
    received=sum(r['response'].get('status')=='received' for r in records)
    unique=len({r['response'].get('request_sha256') for r in records})
    grading=(out/'utility_grading.json').exists()
    complete=len(jobs)==120 and grading
    summary['utility_completeness']={'expected_requests':120,'saved_request_results':len(jobs),'received_responses':received,'unique_response_requests':unique,'identical_request_reused_slots':len(jobs)-unique,'native_grading_present':grading,'status':'complete' if complete else 'partial' if jobs else 'not_started'}
    if not complete:
        for arm in ['plain','v2','v3']:
            summary['native_utility'][arm]['status']='provisional' if grading else 'pending_native_grading'
            if not grading:
                for key in summary['native_utility'][arm]:
                    if key != 'tasks' and key != 'status':summary['native_utility'][arm][key]=None
        if not grading:summary['native_utility']['paired']=None
    atomic(path,summary)
    return summary

if __name__=='__main__':
    summary=report()
    print(json.dumps(summary['utility_completeness']))
