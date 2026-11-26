"""Stable coverage selection with DT priority, rare targets and spec-only diversity."""
from collections import Counter


def hits(row):
    return {key for key, value in (row['membership'] or {}).items() if value['hit']}


def vector(row):
    return tuple((key, value['context'], value['target']) for key, value in sorted((row['membership'] or {}).items()))


def uncertain(row, ignored=()):
    return any(value['target'] in {'unknown', 'error'} or value['context'] in {'unknown', 'error'}
               for key,value in (row['membership'] or {}).items() if key not in ignored)


def select_suite(ledger, cap):
    pool = ledger.pool()
    counts = Counter(key for row in pool for key in hits(row))
    targets = {target['id']: target for target in ledger.model['targets']}
    unsupported = {key for key,target in targets.items() if target.get('support')=='unsupported'}
    mandatory = {key for key, count in counts.items() if count == 1
                 and targets.get(key, {}).get('kind') == 'rule'
                 and targets[key].get('status') == 'feasible'}
    chosen, covered, vectors, sides = [], set(), set(), set()
    remaining = list(pool)
    while remaining and len(chosen) < cap:
        def rank(row):
            unknown = uncertain(row,unsupported)
            new = hits(row) - covered if not unknown else set()
            rare = min((counts[key] for key in new), default=float('inf'))
            rationale = sum(bool(targets.get(key, {}).get('fault_rationale')) for key in new)
            side = {targets[key].get('boundary_side') for key in hits(row) if key in targets}
            return (unknown, -len(new & mandatory), -len(new), rare, -rationale,
                    -(vector(row) not in vectors) if not new else 0,
                    -len(side - sides) if not new else 0, row['dedup_group'])
        row = min(remaining, key=rank)
        new = hits(row) - covered if not uncertain(row,unsupported) else set()
        row['selected'] = True
        row['selection_reason'] = {'rank': len(chosen), 'new_targets': sorted(new),
                                   'membership_unknown': uncertain(row), 'unsupported_targets':sorted(unsupported),
                                   'tie_break': 'rare_target,fault_rationale,spec_diversity,standard_hash'}
        chosen.append(row)
        covered.update(hits(row))
        vectors.add(vector(row))
        sides.update(targets[key].get('boundary_side') for key in hits(row) if key in targets)
        remaining.remove(row)
    for row in remaining:
        if row['errors']:
            row['selection_reason'] = 'membership_unknown'
        else:
            row['selection_reason'] = 'over_cap' if hits(row) - covered else 'no_new_coverage'
    return [dict(row['standard_args'], candidate_id=row['candidate_id']) for row in chosen]
