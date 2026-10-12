"""Standard mutation and C1/C2 measurement; called only inside isolated workers."""
import ast
import contextlib
import io
import os
import tempfile
from pathlib import Path


def enumerate_mutants(src, directory=None):
    import libcst as cst
    from libcst.metadata import MetadataWrapper, PositionProvider
    from mutmut.mutation.file_mutation import create_mutations
    from mutmut.mutation.mutators import mutation_operators
    # mutmut reads configuration even for its source-string API. Give it a task-local
    # source path rather than letting it discover project settings or run its CLI.
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='v4-mutmut-', dir=directory or Path(__file__).resolve().parent) as temporary:
        Path(temporary, 'setup.cfg').write_text('[mutmut]\nsource_paths=v4_put.py\n')
        try:
            os.chdir(temporary)
            module, mutations, _, _ = create_mutations('v4_put.py', src)
        finally:
            os.chdir(previous)
    positions = MetadataWrapper(module, unsafe_skip_copy=True).resolve(PositionProvider)
    result = []
    for mutation in mutations:
        node, new = mutation.original_node, mutation.mutated_node
        # Exclude top-level module mutations; PUT function bodies (including helpers) are the target.
        if mutation.contained_by_top_level_function is None:
            continue
        operators = [op.__name__ for typ, op in mutation_operators if isinstance(node, typ)
                     and any(candidate.deep_equals(new) for candidate in op(node))]
        if not operators:
            raise ValueError('unmapped mutmut operator')
        operator = operators[0]
        before, after = module.code_for_node(node).strip(), module.code_for_node(new).strip()
        changed = module.deep_replace(node, new).code
        try:
            ast.parse(changed)
        except SyntaxError:
            continue
        boundary = False
        if operator == 'operator_swap_op':
            if isinstance(node, cst.ComparisonTarget):
                family = 'ROR'
                boundary = isinstance(node.operator, (cst.LessThan,cst.LessThanEqual,cst.GreaterThan,cst.GreaterThanEqual))
            elif isinstance(node, cst.BooleanOperation): family = 'COR'
            elif isinstance(node, cst.UnaryOperation): family = 'UOI/negation'
            else: family = 'AOR'
        elif operator == 'operator_keywords':
            family = 'BCR' if isinstance(node, (cst.Break,cst.Continue)) else 'ROR'
        elif operator == 'operator_remove_unary_ops': family = 'UOI/negation'
        elif operator in ('operator_number','operator_string'): family = 'CRP constant'
        elif operator == 'operator_name':
            family = 'CRP constant' if before in ('True','False') else 'name replacement'
        else:
            family = {'operator_lambda':'lambda-result replacement', 'operator_dict_arguments':'dictionary-key replacement',
                      'operator_arg_removal':'argument replacement/removal', 'operator_symmetric_string_methods_swap':'string-method replacement',
                      'operator_unsymmetrical_string_methods_swap':'string-method replacement',
                      'operator_augmented_assignment':'AOR', 'operator_assignment':'assignment replacement',
                      'operator_match':'case deletion', 'operator_if_exp':'COR'}[operator]
        if operator == 'operator_number':
            pos = positions[node]
            boundary = any(isinstance(n, ast.Compare) and n.lineno <= pos.start.line <= n.end_lineno
                           and n.col_offset <= pos.start.column for n in ast.walk(ast.parse(src)))
        result.append(dict(k=len(result), mutant_src=changed, line=positions[node].start.line,
                           before=before, after=after, family=family, operator=operator, boundary=boundary,
                           extended=family not in ('ROR','AOR','COR','UOI/negation','CRP constant')))
    return result


class Coverage:
    def __init__(self, src, entry, directory):
        import coverage
        from coverage.parser import PythonParser
        from tracer import load_module
        self.path = str((Path(directory)/'coverage_put.py').resolve())
        Path(self.path).write_text(src)
        self.cov = coverage.Coverage(data_file=None, branch=True, config_file=False, include=[self.path])
        parser = PythonParser(text=src, filename=self.path); parser.parse_source()
        self.statements = parser.statements
        functions = [n for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.statements = {line for line in self.statements
                           if any(fn.lineno < line <= fn.end_lineno for fn in functions)}
        exits = {}
        for a,b in parser.arcs():
            if a > 0: exits.setdefault(a,set()).add(b)
        self.branches = {a:sorted(bs) for a,bs in exits.items() if len(bs)>1}
        self.fn = load_module(src, filename=self.path)[entry]
        self.sources = src.splitlines()

    def measure(self, args):
        from tracer import alarm, dcopy
        self.cov.erase(); self.cov.start()
        try:
            with contextlib.redirect_stdout(io.StringIO()), alarm(1):
                self.fn(*dcopy(args[0]), **dcopy(args[1]))
        except BaseException:
            pass
        finally:
            self.cov.stop()
        data = self.cov.get_data()
        return set(data.lines(self.path) or ()), set(data.arcs(self.path) or ())

    def trace(self, iput, args):
        from tracer import trace
        cells, _, st, value = trace(iput, args)
        lines, arcs = self.measure(args)
        return cells | {(-3, f'arc|{a}|{b}') for a,b in arcs}, lines, st, value

    def branch_facts(self, base, fuzz):
        from facts import t_outcome, t_outcome_placebo
        src = '\n'.join(self.sources)
        nodes = {n.lineno:n for n in ast.walk(ast.parse(src)) if isinstance(n,(ast.If,ast.While))}
        bc = set().union(*(t[0] for t in base)) if base else set()
        facts, placebo = [], []
        for line, targets in sorted(self.branches.items()):
            cells = [[-3,f'arc|{line}|{b}'] for b in targets]
            seen = [c for c in cells if tuple(c) in bc]
            node = nodes.get(line)
            def label(b):
                return 'T' if node and b == node.body[0].lineno else 'F'
            text = ast.unparse(node.test) if node else self.sources[line-1].strip()
            if len(seen) == len(cells):
                placebo.append(dict(kind='OUTCOME', line=line, cells=cells, coverage='coverage.py arcs',
                                    text=t_outcome_placebo(line,text) if node else
                                    f'Branch coverage (C2): all exits of `{text}` (line {line}) are taken by the existing tests.'))
            elif seen:
                for b,c in zip(targets,cells):
                    if c in seen: continue
                    witness = next((i for i,tr in enumerate(fuzz) if tuple(c) in tr[0]), None)
                    facts.append(dict(kind='OUTCOME', line=line, cell=c, witness=witness, coverage='coverage.py arcs',
                                      text=t_outcome(line,text,label(b)) if node else
                                      f'Branch coverage (C2): the exit from line {line} to {b} of `{text}` is never taken by the existing tests.'))
        return facts, placebo
