"""Native observation scheduling helpers for saved coverage audits."""
from collections import deque


def interleave(groups):
    queues = deque(deque(group) for group in groups if group)
    while queues:
        queue = queues.popleft()
        yield queue.popleft()
        if queue:
            queues.append(queue)


def observation_pairs(candidates, priority, targets, obligations, owner_by_label, fallback_owners, scenario,
                      suspected_targets=()):
    """Yield input–PUT pairs; the caller stores each observation before requesting the next pair."""
    owners = list(dict.fromkeys([t['program_id'] for t in targets] + [o['program_id'] for o in obligations])) or list(fallback_owners)
    covered = {identifier for row in candidates.values() for identifier in row['target_hits']}
    met = {o['id'] for o in obligations if any(scenario(o, row['call'], row['observations'].get(o['program_id']))[0] is True
                                              for row in candidates.values())}
    for _ in owners:
        for index, key in enumerate(priority):
            row = candidates[key]
            preferred = list(dict.fromkeys(owner_by_label[label] for origin in row['sources']
                for field in ('concept_id', 'obligation_id') if (label := origin.get(field)) in owner_by_label))
            rotated = owners[index % len(owners):] + owners[:index % len(owners)]
            order = preferred + [owner for owner in rotated if owner not in preferred]
            unmet = {t['program_id'] for t in targets if t['id'] not in covered}
            active = {t['program_id'] for t in targets if t['id'] not in covered and t['id'] not in suspected_targets}
            missing_scenarios = {o['program_id'] for o in obligations if o['id'] not in met}
            order = sorted((owner for owner in order if owner not in row['observations']),
                           key=lambda owner: (owner not in active | missing_scenarios, owner not in unmet))
            if not order:
                continue
            owner = order[0]
            yield row, owner
            covered.update(row['target_hits'])
            met.update(o['id'] for o in obligations if o['program_id'] == owner and
                       scenario(o, row['call'], row['observations'].get(owner))[0] is True)
