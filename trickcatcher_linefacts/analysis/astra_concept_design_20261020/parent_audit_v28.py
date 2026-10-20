"""Read frozen v28 ledgers only. Never import/run a model or PUT worker."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO / 'trickcatcher_linefacts/out/pipelines/v28_codexflow/humaneval/flowrun/codex/pilot20'


def audit():
    frozen = json.loads((ROOT / 'generation_frozen.json').read_text())
    rows, hashes, counts = [], {}, Counter()
    for path in sorted(ROOT.glob('cases/*/arms/agent-tools/tools/ledger.json')):
        relative = str(path.relative_to(ROOT))
        raw = path.read_bytes()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
        assert frozen[relative] == hashes[relative], 'frozen_ledger_drift'
        actions = [e for e in json.loads(raw)['events'] if e['type'] == 'action']
        rounds = {i: [e['request']['action'] for e in actions if e['request']['round'] == i] for i in (1, 2)}
        row = {'task': int(path.parts[-5]), 'actions': len(actions),
               'queries_repeated': bool(rounds[1]) and rounds[1] == rounds[2],
               'calls': Counter(), 'errors': Counter(), 'accepted_replays': 0,
               'native_checked_replays': 0, 'accepted_paths': 0, 'hypothesis_links': 0}
        for event in actions:
            action, result = event['request']['action'], event['result']
            tool = action.get('tool')
            row['calls'][tool] += 1
            counts[tool] += 1
            counts['actions'] += 1
            if action.get('hypothesis'):
                row['hypothesis_links'] += 1
                counts['hypothesis_links'] += 1
            if result['status'] == 'error':
                row['errors'][result.get('error')] += 1
                counts['error_actions'] += 1
            elif tool == 'replay_input':
                row['accepted_replays'] += 1
                counts['accepted_replays'] += 1
                if result.get('native_checked') is True:
                    row['native_checked_replays'] += 1
                    counts['native_checked_replays'] += 1
            elif tool == 'check_path':
                row['accepted_paths'] += 1
                counts['accepted_paths'] += 1
        counts['cases_repeated'] += row['queries_repeated']
        counts['cases_with_accepted_replay'] += row['accepted_replays'] > 0
        counts['cases_with_native_checked_replay'] += row['native_checked_replays'] > 0
        rows.append(row)
    assert len(rows) == 20 and counts['actions'] == 69
    assert counts['replay_input'] == 58 and counts['accepted_replays'] == 35
    assert counts['native_checked_replays'] == 33
    return {'scope': 'post-hoc existing v28 agent JSON action ledgers only; no model/PUT/reference calls',
            'count_scope': 'action events incl repeated inputs/cache reuse, not unique input or physical execution counts',
            'summary': dict(counts), 'cases': rows, 'frozen_ledger_sha256': hashes,
            'limits': 'successful replay does not by itself certify claim revision, concept correctness or adaptive benefit'}


if __name__ == '__main__':
    result = audit()
    (HERE / 'parent_v28_action_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2))
