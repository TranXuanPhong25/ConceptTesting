"""Offline tests for v11_fair_vp: class-method tracing works, module-level behaviour equals v11_fair exactly.

    python -B -m unittest trickcatcher_linefacts.pipelines.v11_fair_vp.test_vp -v
"""
import ast
import json
import unittest
import warnings
from pathlib import Path

from ..v11_fair import facts as facts7, oracle_b01 as ob7, tracer as tr7
from . import facts as factsvp, oracle_b01 as obvp, tracer as trvp
from .paths import REPO

PUTS = REPO / 'vendor/TrickCatcher/Datasets/EvalPlus/PUTs'
SELECTION = Path(__file__).resolve().parent / 'selection.json'
VP_ROOT = REPO / 'trickcatcher_linefacts/out/heldout_vibepass_real/he'
warnings.filterwarnings('ignore', category=SyntaxWarning)  # invalid escape sequences in some HumanEval PUTs
RENAME = {f'__{k}': f'__lf_{k}__' for k in ('v', 'c', 'it', 'p', 'd', 'u', 'named', 'del', 'loop', 'tick')}

CLASS_PUT = '''
import copy
class Solution:
    def f(self, xs: list, k: int) -> int:
        total = 0
        for i, x in enumerate(xs):
            if x > k and i % 2 == 0:
                total += x
            elif x == k:
                total -= 1
        j = 0
        while j < len(xs) and xs[j] != k:
            j += 1
        ys = [y for y in xs if y < k]
        if (n := len(ys)) > 2:
            total += n
        return total + j

def f(xs: list, k: int) -> int:
    return Solution().f(*copy.deepcopy((xs, k)))
'''

MODULE_PUTS = [
    '''
def g(xs, k=3, *rest, **kw):
    "doc"
    out = []
    for i, x in enumerate(xs):
        if x > k or (x < 0 and not i):
            out.append(x)
        else:
            del i
    while k > 0:
        k -= 1
        if k == 1: break
    try:
        z = 1 // (len(xs) - 2)
    except ZeroDivisionError as e:
        z = -1
    with memoryview(b"") as m:
        pass
    return [y * 2 for y in out if y != 5], z, (w := k + 1), (lambda q: q + 1)(w)
''',
    '''
def h(s: str, n: int):
    def inner(a):
        return a.upper() if a.isalpha() else a
    acc = ""
    for c in s:
        acc += inner(c)
    n += len(acc)
    return acc[: n // 2], {c: i for i, c in enumerate(acc)}, sum(1 for c in acc if c == "A")
''',
]


def instrumented_dump(tracer, src, rename=None):
    tree = tracer.Inst().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    if rename:
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id in rename:
                n.id = rename[n.id]
    return ast.dump(tree, include_attributes=True)


def trace_all(tracer, src, entry, calls):
    code, sites = tracer.instrument(src)
    fn = tracer.load_module(code, tracer.HOOKS)[entry]
    return sites, [tracer.trace(fn, (a, {})) for a in calls]


class ClassTracing(unittest.TestCase):
    def test_v7_fails_v7_vp_traces_methods(self):
        calls = [([1, 5, 3, 7], 3), ([], 0), ([-1, -2, -3, 9], -2)]
        _, old = trace_all(tr7, CLASS_PUT, 'f', calls)
        self.assertEqual({t[2] for t in old}, {'NameError'})
        sites, new = trace_all(trvp, CLASS_PUT, 'f', calls)
        self.assertEqual({t[2] for t in new}, {'ok'})
        method_lines = set(range(4, 18))
        cells = set().union(*(t[0] for t in new))
        kinds = {sites[sid]['kind'] for sid, _ in cells if sid >= 0 and sites[sid]['line'] in method_lines}
        self.assertTrue({'cond', 'subcond', 'loop', 'assign', 'return', 'entry'} <= kinds, kinds)
        self.assertTrue(any(sid == -2 and c.startswith('du|') for sid, c in cells))  # def-use cells
        self.assertTrue(set(range(5, 17)) & set().union(*(t[1] for t in new)))
        ref = trvp.load_module(CLASS_PUT)['f']
        self.assertEqual([t[3] for t in new], [ref(*copy_args) for copy_args in calls])

    def test_class_loop_mutants_and_forcing(self):
        tree = ast.parse(CLASS_PUT)
        points = factsvp.mutation_points(tree)
        loop = [k for k, (n, m) in enumerate(points) if m[0] in ('OIL', 'RIL') and isinstance(n, ast.For)]
        self.assertTrue(loop)
        for k in loop:
            new = trvp.load_module(factsvp.make_mutant(CLASS_PUT, k)[0])['f']
            self.assertEqual(trvp.call(new, (([1, 5, 3, 7], 3), {}))[0], 'ok')
            old = tr7.load_module(facts7.make_mutant(CLASS_PUT, k)[0])['f']
            self.assertEqual(tr7.call(old, (([1, 5, 3, 7], 3), {}))[0], 'NameError')
            self.assertIn('__mut_', obvp.mutant_source(CLASS_PUT, k))
        cond = next(n for n in ast.walk(tree) if isinstance(n, ast.If)).test
        fn, changed = factsvp.make_forced(CLASS_PUT, 'f', cond, True)
        self.assertEqual(trvp.call(fn, (([1, 5, 3, 7], 3), {}))[0], 'ok')
        self.assertTrue(changed[0])


class ModuleLevelEquivalence(unittest.TestCase):
    def test_synthetic_traces_equal(self):
        calls = {'g': [[[1, -2, 5, 7]], [[], 0], [[0, 0, 9], 9, 1]], 'h': [['abc', 2], ['', 0], ['A1a', -5]]}
        for src in MODULE_PUTS:
            entry = ast.parse(src).body[0].name
            self.assertEqual(trace_all(tr7, src, entry, calls[entry]), trace_all(trvp, src, entry, calls[entry]))

    def test_all_humaneval_puts_instrument_identically(self):
        tasks = [t['task'] for t in json.loads(SELECTION.read_text())['tasks']]
        for n in tasks:
            src = (PUTS / f'HumanEval_{n}/put0.py').read_text()
            self.assertFalse(any(isinstance(x, ast.ClassDef) for x in ast.walk(ast.parse(src))), n)
            self.assertEqual(instrumented_dump(tr7, src, RENAME), instrumented_dump(trvp, src), n)
            self.assertEqual(tr7.instrument(src)[1], trvp.instrument(src)[1], n)
            for k in range(len(facts7.mutation_points(ast.parse(src)))):
                self.assertEqual(ob7.mutant_source(src, k), obvp.mutant_source(src, k), (n, k))


@unittest.skipUnless(VP_ROOT.is_dir(), 'VibePass held-out root not built')
class VibePassTracing(unittest.TestCase):
    def test_public_inputs_trace_inside_class(self):
        rows = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, (VP_ROOT / 'humaneval_mbpp.jsonl').read_text().splitlines())}
        for n in (3, 103, 120):
            src = (VP_ROOT / f'PUTs/HumanEval_{n}/put0.py').read_text()
            entry = rows[n]['entry_point']
            pg = trvp.load_module(src)
            args, ok = trvp.run_base(pg[entry], rows[n]['test'], ns=pg)
            self.assertIs(ok, True)
            code, sites = trvp.instrument(src)
            fn = trvp.load_module(code, trvp.HOOKS)[entry]
            traces = [trvp.trace(fn, a) for a in args]
            self.assertEqual({t[2] for t in traces}, {'ok'}, n)
            cls = next(x for x in ast.parse(src).body if isinstance(x, ast.ClassDef))
            lines = set(range(cls.lineno, cls.end_lineno + 1))
            cells = set().union(*(t[0] for t in traces))
            self.assertTrue(any(sid >= 0 and sites[sid]['line'] in lines for sid, _ in cells), n)
            self.assertEqual([t[3] for t in traces], [trvp.call(pg[entry], a)[1] for a in args])


if __name__ == '__main__':
    unittest.main()
