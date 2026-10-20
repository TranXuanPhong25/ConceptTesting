"""Project worker line events onto CFG nodes/edges; proof segments break on ambiguity, never guess.

An edge is observed only when two consecutive mapped events of one entry invocation have exactly one CFG edge between
them. Same-line statements, unmapped lines, truncation and unexplained transitions break the segment. Absence claims
(not_observed) require complete, unbroken traces of every entry invocation; otherwise the answer is unknown.
"""
from .flow_cfg import ENTRY, EXIT, RAISE_EXIT, edge_lookup


def project(cfg, execution):
    if not cfg['supported']:
        return dict(status='unsupported', reason='cfg_unsupported', invocations=[])
    if execution.get('status') not in ('ok', 'exception') or not execution.get('events'):
        return dict(status='unknown', reason='no_trace', invocations=[])
    edges = edge_lookup(cfg)
    code = cfg['code_identity']
    runs, order = {}, []
    for row in execution['events']:
        if row['code'] != code:
            continue
        if row['inv'] not in runs:
            runs[row['inv']] = []
            order.append(row['inv'])
        runs[row['inv']].append(row)
    invocations = [_invocation(cfg, edges, inv, runs[inv]) for inv in order]
    complete = bool(execution.get('trace_complete')) and all(r['complete'] for r in invocations)
    return dict(status='projected', trace_complete=bool(execution.get('trace_complete')), all_invocations_proven=complete,
                invocations=invocations, truncated=bool(execution.get('trace_truncated')), omitted_events=execution.get('omitted_events', 0))


def _invocation(cfg, edges, inv, rows):
    segments, breaks, current = [], [], None
    previous = None
    ended, exception = False, None

    def close():
        nonlocal current
        if current and current['nodes']:
            segments.append(current)
        current = None

    def start(node, seq):
        nonlocal current
        close()
        current = dict(nodes=[node], edges=[], event_seqs=[seq])

    for row in rows:
        event = row['event']
        if event == 'call':
            previous = ENTRY
            current = dict(nodes=[], edges=[], event_seqs=[])
            continue
        if event == 'exception':
            exception = row.get('exception_type')
            continue
        if event == 'return':
            ended = True
            if previous not in (None, 'BROKEN') and current is not None:
                if exception is None:
                    edge = edges.get((previous, EXIT))
                else:
                    edge = edges.get((previous, RAISE_EXIT))
                if edge:
                    current['edges'].append(edge['id'])
                    current['nodes'].append(edge['target'])
                else:
                    breaks.append(dict(seq=row['seq'], reason='termination_without_matching_exit_edge' if exception is None else 'implicit_exception_termination'))
            close()
            continue
        candidates = cfg['line_candidates'].get(row['line'], [])
        if len(candidates) != 1:
            breaks.append(dict(seq=row['seq'], reason='same_line_ambiguity' if candidates else 'unmapped_line', line=row['line'], candidates=candidates))
            close()
            previous = 'BROKEN'
            continue
        node = candidates[0]
        if node == previous:
            current['event_seqs'].append(row['seq'])
            continue  # multi-line statements emit several line events; the CFG has no self-loops
        if previous in (None, 'BROKEN'):
            start(node, row['seq'])
        else:
            edge = edges.get((previous, node))
            if edge is None:
                breaks.append(dict(seq=row['seq'], reason='unexplained_transition', source=previous, target=node))
                start(node, row['seq'])
            else:
                if previous == ENTRY:
                    current = dict(nodes=[ENTRY], edges=[], event_seqs=[None])
                current['edges'].append(edge['id'])
                current['nodes'].append(node)
                current['event_seqs'].append(row['seq'])
        previous = node
        exception = None
    close()
    if not ended:
        breaks.append(dict(seq=None, reason='invocation_not_finished_in_trace'))
    return dict(inv=inv, segments=segments, breaks=breaks, complete=not breaks, terminated_by_exception=exception)


def reached(projection, node):
    if projection.get('status') != 'projected':
        return dict(status='unknown', reason=projection.get('reason'))
    hits = sum(seg['nodes'].count(node) for r in projection['invocations'] for seg in r['segments'])
    if hits:
        return dict(status='observed', count=hits, scope='mapped_statement_events')
    if projection['all_invocations_proven']:
        return dict(status='not_observed', scope='complete_unambiguous_trace_this_input_only')
    return dict(status='unknown', reason='incomplete_or_ambiguous_trace')


def covered_edges(projection):
    out = []
    for r in projection.get('invocations', []):
        for seg in r['segments']:
            out += seg['edges']
    return sorted(set(out), key=lambda e: int(e[1:]))


def check_path(cfg, projection, sequence):
    """Contiguous ordered node sequence (as node IDs or chained edge IDs) inside one invocation's proof segment."""
    by_id = {e['id']: e for e in cfg['edges']}
    lookup = edge_lookup(cfg)
    if not sequence or len(sequence) > 64:
        return dict(status='invalid', error='sequence_length')
    if all(x in by_id for x in sequence):
        chain = [by_id[x] for x in sequence]
        if any(a['target'] != b['source'] for a, b in zip(chain, chain[1:])):
            return dict(status='invalid', error='edges_not_chained')
        nodes = [chain[0]['source']] + [e['target'] for e in chain]
    elif all(x in cfg['nodes'] or x in (ENTRY, EXIT, RAISE_EXIT) for x in sequence):
        nodes = list(sequence)
        if len(nodes) < 2:
            return dict(status='invalid', error='need_two_nodes_or_one_edge')
    else:
        return dict(status='invalid', error='unknown_or_mixed_ids')
    missing = [[a, b] for a, b in zip(nodes, nodes[1:]) if (a, b) not in lookup]
    if missing:
        return dict(status='invalid', error='not_a_cfg_edge_sequence', missing=missing)
    if projection.get('status') != 'projected':
        return dict(status='unknown', reason=projection.get('reason'))
    k = len(nodes)
    for r in projection['invocations']:
        for seg in r['segments']:
            seq = seg['nodes']
            for i in range(len(seq) - k + 1):
                if seq[i:i + k] == nodes:
                    return dict(status='observed', inv=r['inv'], occurrence_index=i, scope='contiguous_within_one_invocation')
    if projection['all_invocations_proven']:
        return dict(status='not_observed', scope='this_trace_only; no global infeasibility claim')
    return dict(status='unknown', reason='incomplete_or_ambiguous_trace; no global infeasibility claim')


def summary(projection, aliases, cap):
    """Prompt-visible node sequence, capped with explicit omission counts."""
    rows, omitted = [], 0
    for r in projection.get('invocations', []):
        for seg in r['segments']:
            for node in seg['nodes']:
                if len(rows) < cap:
                    rows.append(aliases.get(node, node))
                else:
                    omitted += 1
            if len(rows) < cap:
                rows.append('|')
    return dict(sequence=rows, omitted=omitted, breaks=sum(len(r['breaks']) for r in projection.get('invocations', [])))
