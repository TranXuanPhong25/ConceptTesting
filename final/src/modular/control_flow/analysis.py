"""Library C1/C2 obligations and structural paths, without executing source."""
import ast
from collections import defaultdict, deque
import hashlib

from coverage.parser import PythonParser

from ..call_builder import entry_function


def _uncovered_c1_lines(statements, seen_lines, reachable_lines):
    return sorted((statements - seen_lines) & reachable_lines)


def _uncovered_c2_arcs(exit_counts, adjacency, seen_arcs, reachable_lines):
    for line, exits in sorted(exit_counts.items()):
        if exits <= 1 or line not in reachable_lines:
            continue
        for end in adjacency[line]:
            if (line, end) not in seen_arcs:
                yield line, end


def analyze(program, entry):
    source = program['code']
    function = entry_function(source, entry)
    parser = PythonParser(text=source)
    parser.parse_source()
    arcs = sorted(parser.arcs())
    coverage = program['base'].get('coverage')
    program_id = program['id']
    source_sha256 = hashlib.sha256(source.encode()).hexdigest()
    coverage_status = 'measured' if coverage is not None else 'unknown'
    cfg_arcs = [list(arc) for arc in arcs]
    result = {
        'program_id': program_id,
        'source_sha256': source_sha256,
        'coverage_status': coverage_status,
        'targets': [],
        'cfg_arcs': cfg_arcs,
    }
    if coverage is None:
        return result

    seen_arcs = {tuple(arc) for arc in coverage['arcs']}
    seen_lines = set(coverage['lines'])
    adjacency = defaultdict(list)
    for start, end in arcs:
        adjacency[start].append(end)
    # A structural path is guidance only: it does not prove joint feasibility.
    first = function.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and len(function.body) > 1
    ):
        first = function.body[1]
    paths = {first.lineno: []}
    queue = deque([first.lineno])
    # Keep one shortest structural path per reachable line.
    while queue:
        start = queue.popleft()
        for end in adjacency[start]:
            if function.lineno < end <= function.end_lineno and end not in paths:
                paths[end] = [*paths[start], [start, end]]
                queue.append(end)
    source_lines = source.splitlines()
    evidence_lines = list(range(function.lineno, function.end_lineno + 1))

    def target(criterion, line, arc=None):
        route = list(paths.get(line, []))
        if arc:
            route.append(arc)
        location = f'{arc[0]}:{arc[1]}' if arc else str(line)
        identifier = f'{program_id}:{criterion}:{location}'
        arc_field = {'arc': arc} if arc else {}
        target_source = source_lines[line - 1].strip()
        path = [
            {'arc': step, 'source': source_lines[step[0] - 1].strip()}
            for step in route
        ]
        return {
            'id': identifier,
            'program_id': program_id,
            'criterion': criterion,
            'line': line,
            **arc_field,
            'source': target_source,
            'evidence_lines': evidence_lines.copy(),
            'path_status': 'structural_approximation',
            'path': path,
        }

    reachable_lines = paths.keys()

    c1_lines = _uncovered_c1_lines(
            parser.statements,
            seen_lines,
            reachable_lines,
        )
    for line in c1_lines:
        result['targets'].append(target('C1', line))

    c2_arcs = _uncovered_c2_arcs(
        parser.exit_counts(),
        adjacency,
        seen_arcs,
        reachable_lines,
    )
    for line, end in c2_arcs:
        result['targets'].append(target('C2', line, arc=[line, end]))
    
    return result


def hit(target, observation):
    """A partial trace can witness a target even when execution later raises."""
    if observation.get('domain') != 'valid':
        return False
    coverage = observation.get('coverage', {})
    if target['criterion'] == 'C2':
        return target['arc'] in coverage.get('arcs', [])
    return target['line'] in coverage.get('lines', [])


def measure_targets(targets, observations, rounds):
    """A witnessed miss is not an infeasibility proof; absent/partial traces stay unknown."""
    rows = []
    for target in targets:
        target_id = target['id']
        measured = [
            row for row in observations
            if row['program_id'] == target['program_id']
        ]
        witnessed = any(hit(target, row) for row in measured)
        complete = sum(
            row.get('domain') == 'valid'
            and row.get('status') == 'executed'
            and 'coverage' in row
            for row in measured
        )
        unknown = sum(
            row.get('domain') not in ('valid', 'invalid')
            or (
                row.get('domain') == 'valid'
                and (row.get('status') != 'executed' or 'coverage' not in row)
            )
            for row in measured
        )
        prompt_rounds = [
            record['round'] for record in rounds
            if target_id in record['supplied_target_ids']
        ]
        observation_count = len(measured)
        if witnessed:
            status = 'hit'
        elif unknown or not complete:
            status = 'unknown'
        else:
            status = 'miss'
        feasibility = 'witnessed' if witnessed else 'unproven'
        measurement = {
            'target_id': target_id,
            'prompt_rounds': prompt_rounds,
            'observations': observation_count,
            'complete_observations': complete,
            'unknown_observations': unknown,
            'status': status,
            'feasibility': feasibility,
        }
        rows.append(measurement)
    return rows


def target_feedback(target, observation, expected_opcodes=None):
    """Report measured path mismatches without inferring order from a coverage set."""
    target_hit = hit(target, observation)
    result = {
        'target_id': target['id'],
        'target_hit': target_hit,
        'semantic_status': 'hypothesis',
    }
    if observation.get('domain') != 'valid' or 'coverage' not in observation:
        reason = observation.get('status', 'missing_trace')
        return {**result, 'status': 'unknown', 'reason': reason}

    arcs = observation['coverage'].get('arcs', [])
    for step in target.get('path', []):
        expected_arc = step['arc']
        if expected_arc not in arcs:
            expected_source = step.get('source', '')
            observed_exits = [arc for arc in arcs if arc[0] == expected_arc[0]]
            result.update(
                first_unobserved_arc=expected_arc,
                expected_source=expected_source,
                observed_exits=observed_exits,
                path_scope='unordered_arc_membership;not_ordered_prefix_proof',
            )
            break

    actual = observation.get('opcode_path')
    if expected_opcodes is not None and actual is not None:
        result['ordered_path_scope'] = 'comparison_to_verified_path;different_valid_paths_allowed'
        prefix_length = 0
        shared_length = min(len(actual), len(expected_opcodes))
        while (
            prefix_length < shared_length
            and actual[prefix_length] == expected_opcodes[prefix_length]
        ):
            prefix_length += 1
        if prefix_length < max(len(actual), len(expected_opcodes)):
            expected_opcode = (
                expected_opcodes[prefix_length] if prefix_length < len(expected_opcodes) else None
            )
            observed_opcode = actual[prefix_length] if prefix_length < len(actual) else None
            result['first_divergence'] = {
                'event_index': prefix_length,
                'expected_opcode': expected_opcode,
                'observed_opcode': observed_opcode,
            }
        result['ordered_prefix_events'] = prefix_length
        result['path_matches'] = actual == expected_opcodes
    status = 'observed' if observation.get('status') == 'executed' else 'partial_trace'
    result['status'] = status
    return result
