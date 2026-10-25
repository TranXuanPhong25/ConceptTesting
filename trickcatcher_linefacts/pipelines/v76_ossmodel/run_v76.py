"""Registered v76 harness. No paid call unless --launch is supplied after approval."""
import argparse
import collections
import fcntl
import hashlib
import json
import shutil
from pathlib import Path

from . import ft_run
from .context_preflight import preflight
from .flow_common import immutable
from .paths import CONFIG, REPO, select_model
from .seed_from_v31 import seed, sha

HERE = Path(__file__).resolve().parent


def verify_assets():
    from .prepared import verify
    verify()
    manifest = json.loads((HERE / 'ASSETS.json').read_text())
    for rel, expected in manifest.items():
        if sha(HERE / rel) != expected:
            raise ValueError('asset_drift:' + rel)


class V76Run(ft_run.FTRun):
    def __init__(self, cohort_name='vibepass_half', client=None, model=None):
        model=model or CONFIG['model_choice']
        if cohort_name != 'vibepass_half':
            raise ValueError('only_registered_33_case_cohort')
        super().__init__(cohort_name, client, model)

    def tools(self, workers):
        # No fallback to a freshly recomputed tool stage.
        seed(self)
        return {c['case_id']: json.loads((self.root / 'cases' / c['case_id'] / 'tool.json').read_text()) for c in self.cases}

    def protocol(self):
        verify_assets()
        return super().protocol()


def decision(report):
    primary = report['pairs']['fault-template vs template-placebo']['detection']
    wins, losses = len(primary['wins']), len(primary['losses'])
    fa = report['arms']['fault-template']['false_alarms']
    fp = report['arms']['template-placebo']['false_alarms']
    met = wins > losses and fa <= fp
    ceiling = report['arms']['plain']['tasks_confirmed'] >= 28
    verdict = 'ceiling, uninformative about concepts' if ceiling else 'concept adds value' if met else 'rule not met'
    return dict(verdict=verdict, primary_rule_met=met, wins=wins, losses=losses,
                fault_template_false_positive_tests=fa, template_placebo_false_positive_tests=fp)


def supplementary(run, report):
    arms = {}
    for arm in ft_run.ARMS:
        records = [json.loads((run.root / 'cases' / c['case_id'] / 'arms' / arm / 'result.json').read_text()) for c in run.cases]
        arms[arm] = dict(valid_empty_final_tests=sum(r.get('final') is not None and r['final']['tests'] == [] for r in records),
                         invalid_final=sum(bool(r.get('calls')) and r.get('final') is None for r in records),
                         schema_errors=report['arms'][arm]['schema_errors'],
                         transport_input_tokens=0, transport_output_tokens=0, reasoning_tokens=0, transport_cost_usd=0.)
    cost_path = run.root / 'transport/cost.json'
    if cost_path.exists():
        from decimal import Decimal
        ledger = json.loads(cost_path.read_text())
        costs = collections.defaultdict(lambda: Decimal(0))
        for key, entry in ledger['entries'].items():
            arm = key.split('/')[2]
            usage = entry.get('usage') or {}
            arms[arm]['transport_input_tokens'] += usage.get('prompt_tokens', 0)
            arms[arm]['transport_output_tokens'] += usage.get('completion_tokens', 0)
            arms[arm]['reasoning_tokens'] += (usage.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
            if entry.get('cost_usd') is not None:
                costs[arm] += Decimal(entry['cost_usd'])
        for arm, cost in costs.items():
            arms[arm]['transport_cost_usd'] = str(cost)
    return dict(decision=decision(report), arms=arms, scope='supplementary; unchanged v34 score.json remains authoritative')


def finalize_partial(model):
    select_model(model)
    run=V76Run();source=run.root
    if (source/'generation_frozen.json').exists():raise ValueError('complete_run_cannot_finalize_partial')
    complete=[]
    for case in run.cases:
        if not all((source/'cases'/case['case_id']/'arms'/a/'result.json').exists() for a in ft_run.ARMS):break
        complete.append(case)
    status=dict(status='partial; descriptive only, no efficacy verdict',model=model,
                completed_cases=[c['case_id'] for c in complete],planned=33)
    immutable(source/'partial_status.json',status)
    if not complete:return status
    root=source.parent/'paired_subset'
    if root.exists():raise ValueError('partial_already_finalized')
    root.mkdir(parents=True)
    shutil.copy2(source/'protocol.json',root/'protocol.json')
    for case in complete:shutil.copytree(source/'cases'/case['case_id'],root/'cases'/case['case_id'])
    immutable(root/'partial_status.json',status)
    files={str(p.relative_to(root)):sha(p) for p in root.rglob('*.json')}
    immutable(root/'generation_frozen.json',files)
    run.root=root;run.cases=complete
    return ft_run.score(run)


def launch(model='gpt-oss-120b'):
    select_model(model)
    run = V76Run()
    if (run.root/'partial_status.json').exists():raise ValueError('terminal_partial_cannot_resume')
    run.root.mkdir(parents=True, exist_ok=True)
    with (run.root / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_assets()
        check = preflight()
        seed(run)
        immutable(run.root / 'context_preflight.json', check)
        run.protocol()
        from .openrouter_client import OpenRouterClient
        run.client = OpenRouterClient(run.root / 'transport')
        try:
            run.generate(CONFIG['openrouter']['workers'])
        finally:
            run.client.close()
        report = ft_run.score(run)
        immutable(run.root / 'decision_v76.json', supplementary(run, report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true', help='paid execution; requires separate user go-ahead')
    parser.add_argument('--model',choices=tuple(CONFIG['models']),default='gpt-oss-120b')
    parser.add_argument('--finalize-partial',action='store_true',help='CPU-only terminal paired-prefix scoring')
    args = parser.parse_args()
    if args.finalize_partial:
        if args.launch:parser.error('mutually exclusive actions')
        finalize_partial(args.model)
        raise SystemExit(0)
    if not args.launch:
        parser.error('preparation only; no paid execution without --launch and user go-ahead')
    launch(args.model)
