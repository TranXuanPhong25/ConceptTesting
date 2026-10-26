"""Offline terminal integrity/cost review; never dispatch models/native workers."""
import json,hashlib
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=REPO/'trickcatcher_linefacts/out/pipelines/v80_deepseekproviders'


def main():
    if not (HERE/'controller_terminal.json').exists():raise ValueError('wait_for_both_terminal')
    if (HERE/'DEEPINFRA_RUN.json').exists() and not (BASE/'deepinfra_fp8/frozen.json').exists():
        raise ValueError('wait_for_independent_deepinfra_terminal')
    providers=[]
    for route,slug in [('reka','reka'),('deepinfra/fp8','deepinfra_fp8')]:
        root=BASE/slug
        plan=json.loads((root/'plan.json').read_text())
        if not (root/'frozen.json').exists():
            providers.append({'route':route,'status':'unattempted'});continue
        frozen=json.loads((root/'frozen.json').read_text())
        assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==h for name,h in frozen.items())
        summary=json.loads((root/'summary.json').read_text())
        receipts=[json.loads(p.read_text()) for p in root.glob('*/*/cost_receipt.json')]
        attempts=list(root.glob('*/*/attempt.json'))
        unresolved=sum((Decimal(json.loads(p.read_text())['worstcase_reserved_usd']) for p in attempts
                        if not (p.parent/'cost_receipt.json').exists()),Decimal(0))
        answers=[];tokens_in=0;tokens_out=0;reasoning=0
        for p in sorted(root.glob('*/*/response.json')):
            response=json.loads(p.read_text());record=response['response'];usage=record.get('usage') or {}
            tokens_in+=usage.get('prompt_tokens',0);tokens_out+=usage.get('completion_tokens',0)
            reasoning+=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0
            answers.append({'case_id':p.parent.parent.name,'arm':p.parent.name,'value':response['value'],
                            'error':response['error'],'finish_reason':record['finish_reason']})
        cost=sum((Decimal(r['actual_cost_usd']) for r in receipts),Decimal(0))
        assert str(cost)==summary['actual_known_cost_usd']
        assert len(attempts)<=4 and len(receipts)==summary['known_cost_receipts']
        providers.append({'route':route,'summary':{k:v for k,v in summary.items() if k!='rows'},
                          'verified_freeze_entries':len(frozen),'actual_known_cost_usd':str(cost),
                          'unresolved_reservation_usd':str(unresolved),'input_tokens':tokens_in,
                          'output_tokens_including_reasoning':tokens_out,'reasoning_tokens':reasoning,
                          'answers':answers})
    report={'providers':providers,'prior_relace_unknown_reservation_usd':'0.04898572',
            'audited_utc':datetime.now(timezone.utc).isoformat(),'new_native_or_private_calls':0}
    (HERE/'terminal_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
