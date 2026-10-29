"""Run only the two unfinished V83 quarter tasks as a separately capped addendum."""
from __future__ import annotations
import fcntl
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from .paths import HERE, CONFIG, select_model
from . import combined_generation, provenance, scoring, v4_runtime
from .llm_client import atomic_json

OLD = HERE.parents[0] / 'v83_reka_fullquarter' / 'out' / 'reka_quarter_final2'
ROOT = HERE / 'out' / 'reka_completion_154_158'
TASK_IDS = (154, 158)
CAP = Decimal('0.50')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_old():
    from ..v83_reka_fullquarter import prepared as old_prepared, provenance as old_provenance
    old_prepared.verify()
    old_protocol = json.loads((OLD / 'protocol.json').read_text())
    if old_protocol.get('sources') != old_provenance.sources():
        raise ValueError('v83_source_identity_drift')
    if old_protocol.get('prepared_sha256') != sha(OLD / 'humaneval/prepared.json'):
        raise ValueError('v83_prepared_input_drift')
    terminal = json.loads((OLD / 'terminal.json').read_text())
    if terminal['status'] != 'partial' or terminal['scored_tasks'] != 0:
        raise ValueError('unexpected_v83_terminal')
    frozen = json.loads((OLD / 'generation_frozen.json').read_text())
    for rel, expected in frozen.items():
        if sha(OLD / rel) != expected:
            raise ValueError('v83_generation_freeze_drift:' + rel)
    tasks = json.loads((OLD / 'humaneval/generation/tasks.json').read_text())['tasks']
    if [t['task'] for t in tasks] != json.loads((HERE / 'COHORT.json').read_text())['task_ids']:
        raise ValueError('v83_task_order_drift')
    done = set(json.loads((OLD / 'humaneval/generation/completed_tasks.json').read_text()))
    missing = [t['task'] for t in tasks if t['task'] not in done]
    if missing != list(TASK_IDS):
        raise ValueError('unexpected_missing_tasks:' + repr(missing))
    return terminal, tasks


def prepare():
    select_model('deepseek-v4-flash')
    from .prepared import verify
    verify()
    terminal, tasks = verify_old()
    old_prepared = json.loads((OLD / 'humaneval/prepared.json').read_text())
    rows = [r for r in old_prepared if r['baseline']['task'] in TASK_IDS]
    if [r['baseline']['task'] for r in rows] != list(TASK_IDS):
        raise ValueError('completion_bundle_missing_or_reordered')
    v4_runtime.immutable(ROOT / 'humaneval/prepared.json', rows)
    old_context = json.loads((OLD / 'context_preflight.json').read_text())
    context_rows = [r for r in old_context['rows'] if r['task'] in TASK_IDS]
    context = dict(old_context, requests=len(context_rows), rows=context_rows,
                   scope='subset of the frozen V83 conservative UTF-8 preflight; runtime exact gate remains active')
    atomic_json(ROOT / 'context_preflight.json', context)
    protocol = dict(
        status='exploratory_completion_addendum',
        sources=provenance.sources(),
        prepared_sha256=sha(ROOT / 'humaneval/prepared.json'),
        task_ids=list(TASK_IDS), arms=CONFIG['combined']['arms'], K=1,
        model=CONFIG['openrouter']['model'], provider='reka', max_output_tokens=CONFIG['openrouter']['max_tokens'],
        hard_cap_usd=str(CAP), cumulative_cap_usd='4.20',
        prior_exposure_usd='1.49336991', cumulative_headroom_before_addendum_usd='2.70663009',
        preserved_v83_unknown_reserve_usd='0.0642930',
        v83_terminal_sha256=sha(OLD / 'terminal.json'),
        v83_generation_freeze_sha256=sha(OLD / 'generation_frozen.json'),
        v83_completed_tasks=json.loads((OLD / 'humaneval/generation/completed_tasks.json').read_text()),
        generation_lookup=dict(finish_reason='stop', provider='Reka', cost_usd='0.0051955',
                              content_available=False, http_status_content=404),
        task154_policy='fresh paired rerun; do not reuse its incomplete V83 arm output',
        task158_policy='first generation attempt',
        user_instruction='continue after the V83 terminal partial was disclosed',
        efficacy='exploratory only; do not restore V83 confirmatory status')
    v4_runtime.immutable(ROOT / 'protocol.json', protocol)
    return rows


def freeze(root, relpaths):
    target = root / 'generation_frozen.json'
    files = json.loads(target.read_text()) if target.exists() else {}
    for rel in relpaths:
        for path in (root / rel).rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.jsonl', '.py'):
                key = str(path.relative_to(root)); value = sha(path)
                if key in files and files[key] != value:
                    raise ValueError('generation_freeze_drift:' + key)
                files[key] = value
    atomic_json(target, files)


def score_mixed_full28(rows):
    from . import oracle_b01
    old_run = OLD / 'humaneval/paired_subset'
    add_run = ROOT / 'humaneval/generation'
    consolidated = ROOT / 'humaneval/paired_subset'
    all_prepared = json.loads((OLD / 'humaneval/prepared.json').read_text())
    tasks = [r['baseline'] for r in all_prepared]
    combined = [r['combined'] for r in all_prepared]
    v4_runtime.immutable(consolidated / 'tasks.json',
                         dict(facts_version='v4', tasks=tasks, combined_tasks=combined))
    old_rows = [json.loads(line) for line in (old_run / 'gen.jsonl').read_text().splitlines() if line]
    new_rows = [json.loads(line) for line in (add_run / 'gen.jsonl').read_text().splitlines() if line]
    ids = [r['baseline']['task'] for r in rows]
    if len(new_rows) != len(ids) * 2 or {r['task'] for r in new_rows} != set(ids):
        raise ValueError('addendum_generation_not_complete')
    gen = consolidated / 'gen.jsonl'
    gen.parent.mkdir(parents=True, exist_ok=True)
    gen.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in old_rows + new_rows))
    partial = dict(status='mixed-run exploratory descriptive scoring; no efficacy verdict',
                   complete_tasks=[t['task'] for t in json.loads((OLD / 'humaneval/paired_subset/tasks.json').read_text())['tasks']] + ids,
                   expected_tasks=28, original_v83_tasks=26, addendum_tasks=ids)
    v4_runtime.immutable(ROOT / 'partial_status.json', partial)
    freeze(ROOT, ['humaneval/paired_subset'])
    # The unchanged executor omits tasks with no parseable calls. Treat them as
    # empty maps, which correctly yields no detection for those generated rows.
    execute = oracle_b01.execute
    def include_no_call_tasks(run=oracle_b01.RUN, out=oracle_b01.OUT, workers=12):
        result = execute(run, out, workers)
        bundles, _ = oracle_b01.load_run(run)
        calls = json.loads((out / 'calls.json').read_text())
        for task_id in bundles:
            if str(task_id) not in calls:
                result[str(task_id)] = {'calls': {}}
        return result
    oracle_b01.execute = include_no_call_tasks
    reports = scoring.humaneval(consolidated, ROOT, client=None, k=1)
    atomic_json(ROOT / 'mixed_28_score_summary.json', {
        name: {'tasks': value['tasks'], 'partial': value['partial'], 'primary': value['primary']}
        for name, value in reports.items()})
    return reports


def launch():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / '.completion.lock').open('a') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _launch_locked()

def _launch_locked():
    select_model('deepseek-v4-flash')
    from .prepared import verify
    verify()
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    if protocol.get('sources') != provenance.sources():
        raise ValueError('addendum_source_identity_drift')
    if protocol.get('prepared_sha256') != sha(ROOT / 'humaneval/prepared.json'):
        raise ValueError('addendum_prepared_input_drift')
    old_terminal, _ = verify_old()
    if protocol.get('v83_terminal_sha256') != sha(OLD / 'terminal.json'):
        raise ValueError('v83_terminal_identity_drift')
    if protocol.get('v83_generation_freeze_sha256') != sha(OLD / 'generation_frozen.json'):
        raise ValueError('v83_generation_freeze_identity_drift')
    rows = json.loads((ROOT / 'humaneval/prepared.json').read_text())
    if [r['baseline']['task'] for r in rows] != list(TASK_IDS):
        raise ValueError('prepared_addendum_order_drift')
    if protocol.get('task_ids') != list(TASK_IDS) or protocol.get('hard_cap_usd') != str(CAP):
        raise ValueError('addendum_protocol_scope_or_cap_drift')
    if (ROOT / 'terminal.json').exists() or (ROOT / 'generation_frozen.json').exists():
        raise ValueError('addendum_root_terminal')
    from .stream_client import OpenRouterClient
    from .transport import Client
    transport = OpenRouterClient(ROOT / 'transport', budget_limit=CAP)
    stop = None
    complete = False
    try:
        combined_generation.run(rows, ROOT / 'humaneval/generation', v4_runtime.interpreter(),
                                client=Client(transport), k=1, workers=1)
        complete = True
    except Exception as exc:
        stop = type(exc).__name__ + ':' + str(exc)[:240]
    finally:
        transport.close()
    generation = ROOT / 'humaneval/generation'
    freeze(ROOT, ['humaneval/generation'])
    ledger = transport.ledger()
    record = dict(status='complete' if complete else 'partial', task_ids=list(TASK_IDS), arms=CONFIG['combined']['arms'], K=1,
                  generation_complete=complete, stop_reason=stop, known_cost_usd=transport.spent(),
                  physical_attempts=len(ledger['entries']),
                  unresolved_attempts=sum(e.get('cost_usd') is None for e in ledger['entries'].values()),
                  finished_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(ROOT / 'terminal.json', record)
    print(json.dumps(record), flush=True)
    if complete:
        return score_mixed_full28(rows)
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'launch'))
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    else:
        launch()

if __name__ == '__main__':
    main()
