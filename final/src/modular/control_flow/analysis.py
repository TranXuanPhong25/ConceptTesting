"""Library C1/C2 obligations and static may-flow evidence, without executing source."""
import ast
from collections import defaultdict, deque
import hashlib

from coverage.parser import PythonParser

from ..call_builder import entry_function


def analyze(program, entry):
    source = program['code']
    function = entry_function(source, entry)
    parser = PythonParser(text=source)
    parser.parse_source()
    arcs = sorted(parser.arcs())
    coverage = program['base'].get('coverage')
    result = {'program_id': program['id'], 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'coverage_status': 'measured' if coverage is not None else 'unknown',
              'targets': [], 'def_use': [], 'data_flow_status': 'static_may_flow',
              'cfg_arcs': [list(arc) for arc in arcs]}
    try:
        from python_graphs import program_graph, program_graph_dataclasses as graph_types
        graph = program_graph.get_program_graph(source)
        pairs = set()
        for edge in graph.edges:
            if edge.type != graph_types.EdgeType.LAST_WRITE:
                continue
            use, definition = graph.nodes[edge.id1].ast_node, graph.nodes[edge.id2].ast_node
            # python-graphs stores gast nodes, not stdlib ast nodes.
            if (type(use).__name__ == 'Name' and type(use.ctx).__name__ == 'Load'
                    and getattr(definition, 'lineno', None) is not None):
                pairs.add((use.id, definition.lineno, use.lineno))
        result['def_use'] = [{'variable': variable, 'definition': definition, 'use': use}
                             for variable, definition, use in sorted(pairs)]
    except Exception as error:
        result.update(data_flow_status='unsupported', graph_error=type(error).__name__)
    if coverage is None:
        return result
    seen_arcs = {tuple(arc) for arc in coverage['arcs']}
    seen_lines = set(coverage['lines'])
    adjacency = defaultdict(list)
    for start, end in arcs:
        adjacency[start].append(end)
    # A structural path is guidance only: it does not prove joint feasibility.
    first = function.body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str) and len(function.body) > 1):
        first = function.body[1]
    paths = {first.lineno: []}
    queue = deque([first.lineno])
    while queue:
        start = queue.popleft()
        for end in adjacency[start]:
            if function.lineno < end <= function.end_lineno and end not in paths:
                paths[end] = [*paths[start], [start, end]]
                queue.append(end)
    source_lines = source.splitlines()
    allowed_lines = set(range(function.lineno, function.end_lineno + 1))

    def target(criterion, line, arc=None):
        route = list(paths.get(line, [])) + ([arc] if arc else [])
        identifier = f"{program['id']}:{criterion}:" + (f'{arc[0]}:{arc[1]}' if arc else str(line))
        return {'id': identifier, 'program_id': program['id'], 'criterion': criterion,
                'line': line, **({'arc': arc} if arc else {}),
                'source': source_lines[line - 1].strip(),
                'evidence_lines': sorted(allowed_lines),
                'path_status': 'structural_approximation',
                'path': [{'arc': step, 'source': source_lines[step[0] - 1].strip()} for step in route]}

    for line, exits in sorted(parser.exit_counts().items()):
        if exits > 1 and line in paths:
            for end in adjacency[line]:
                if (line, end) not in seen_arcs:
                    result['targets'].append(target('C2', line, [line, end]))
    for line in sorted(parser.statements - seen_lines):
        if line in paths:
            result['targets'].append(target('C1', line))
    return result


def hit(target, observation):
    """A partial trace can witness a branch even when execution later raises."""
    if observation.get('domain') != 'valid':
        return False
    coverage = observation.get('coverage', {})
    if target['criterion'] == 'C2':
        return target['arc'] in coverage.get('arcs', [])
    return target['line'] in coverage.get('lines', [])
