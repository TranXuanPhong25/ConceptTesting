"""v51 step 1: build labelled (spec, call, observed result) examples. See PREREG.md. Run from the repo root:

    PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v51_latent_concept/build.py

Train: EvalPlus MBPP+ canonical solutions and mutmut 3.8 mutants run in the v34 sandbox worker; each wrong example gets
one discrepancy concept computed from (correct output, wrong output). Eval: the saved v41 VibePass pool (no new
execution); labels follow v41 exposure(). Writes out/analysis/v51_latent_concept/{train,eval}.jsonl.
"""
import ast
import warnings
import gzip
import json
import math
import os
import random
from pathlib import Path

import libcst as cst
from mutmut.configuration import config as mutmut_config
from mutmut.mutation.file_mutation import create_mutations

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import same

HOME = Path(__file__).resolve().parents[2]
OUT = HOME / 'out' / 'analysis' / 'v51_latent_concept'
MBPP = HOME / 'out' / 'heldout_mbpp' / 'raw' / 'MbppPlus.jsonl.gz'
V41 = HOME / 'out' / 'analysis' / 'v41_iorel' / 'cases'
SEED = 20261023
MAX_LITERAL = 300
INPUTS_PER_TASK = 30
MUTANTS_PER_TASK = 8
WRONG_PER_INPUT = 2
PER_CLASS_PER_TASK = 25
EVAL_EXPOSING, EVAL_OTHER = 40, 120
CONCEPTS = ('TYPE', 'BOOL_FLIP', 'ORDER', 'SIZE', 'NUM_NEAR', 'NUM_FAR', 'CONTENT')


def literal(o):
    """Python value of an 'ok' outcome, or None when the repr is not a literal."""
    try:
        return True, ast.literal_eval(o[1])
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False, None


def is_num(v):
    return type(v) in (int, float)


def concept(right, wrong):
    """First matching discrepancy concept for a wrong value outcome (ft_worker 'ok' outcomes, both parseable)."""
    ok_r, r = literal(right)
    ok_w, w = literal(wrong)
    if not (ok_r and ok_w):
        return 'CONTENT'
    if type(r) is not type(w):
        return 'TYPE'
    if type(r) is bool:
        return 'BOOL_FLIP'
    if isinstance(r, (list, tuple, str)) and len(r) == len(w):
        try:
            if sorted(r) == sorted(w):
                return 'ORDER'
        except TypeError:
            pass
    if hasattr(r, '__len__') and len(r) != len(w):
        return 'SIZE'
    if is_num(r):
        if any(isinstance(x, float) and not math.isfinite(x) for x in (r, w)):
            return 'NUM_FAR'
        return 'NUM_NEAR' if 10 * abs(w - r) <= max(10, abs(r)) else 'NUM_FAR'  # exact for big ints
    return 'CONTENT'


def observed(o):
    """Text shown to the model for one outcome."""
    if o[0] == 'exception':
        return f'raised {o[1]}'
    text = o[1] if len(o[1]) <= MAX_LITERAL else o[1][:MAX_LITERAL] + '...'
    return f'returned {text}'


def mbpp_spec(prompt):
    return prompt.strip().strip('"').strip()


def load_mutmut_config():
    """mutmut reads its config from setup.cfg in the cwd; load it once from a minimal default config, then cache."""
    directory = OUT / 'mutmut_cfg'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'setup.cfg').write_text('[mutmut]\nsource_paths=.\n')
    cwd = os.getcwd()
    os.chdir(directory)
    try:
        mutmut_config()
    finally:
        os.chdir(cwd)


def mutant_sources(code, rng):
    module, mutations, _, _ = create_mutations('canonical.py', code)
    sources = []
    for m in mutations:
        if isinstance(m.original_node, cst.BaseString):  # mutmut's 'XX...XX' string mutants: an artifact absent in eval
            continue
        text = module.deep_replace(m.original_node, m.mutated_node).code
        try:
            compile(text, '<mutant>', 'exec')
        except (SyntaxError, ValueError):
            continue
        if text != code:
            sources.append(text)
    sources = sorted(set(sources))
    rng.shuffle(sources)
    return sources[:MUTANTS_PER_TASK]


def call_literal(args):
    text = repr(tuple(args))
    if len(text) > MAX_LITERAL:
        return None
    try:
        ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    return text


def example_calls(prompt, entry):
    """Argument tuples of the calls shown in the MBPP prompt's assert example (excluded from training)."""
    out = []
    for node in ast.walk(ast.parse(prompt)):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == entry:
            try:
                out.append(tuple(ast.literal_eval(a) for a in node.args))
            except (ValueError, SyntaxError, TypeError):
                pass
    return out


def build_train():
    load_mutmut_config()
    rows = [json.loads(line) for line in gzip.open(MBPP, 'rt')]
    examples, stats = [], dict(tasks=0, no_mutant=0, no_input=0)
    for row in rows:
        rng = random.Random(f"{SEED}-{row['task_id']}")
        code, entry = row['canonical_solution'], row['entry_point']
        shown = example_calls(row['prompt'], entry)
        calls = list(dict.fromkeys(c for part in ('base_input', 'plus_input') if isinstance(row[part], list)
                                   for args in row[part] if (c := call_literal(args))
                                   and ast.literal_eval(c) not in shown))
        rng.shuffle(calls)
        calls = calls[:INPUTS_PER_TASK]
        if not calls:
            stats['no_input'] += 1
            continue
        try:
            mutants = mutant_sources(code, rng)
        except cst.ParserSyntaxError:
            mutants = []
        if not mutants:
            stats['no_mutant'] += 1
            continue
        sources = {'canon': code, **{f'm{i}': s for i, s in enumerate(mutants)}}
        tid = row['task_id'].replace('/', '_')
        res = iorel.run_batch(OUT / 'exec' / tid, sources, entry, calls)
        right, wrong = [], []
        for k, call in enumerate(calls):
            r = res['canon'][k]
            vr = iorel.value(r)
            if vr is None or r[0] == 'exception':  # only inputs where the canonical solution returns a value
                continue
            base = dict(task=row['task_id'], spec=mbpp_spec(row['prompt']), entry=entry, call=call)
            right.append(dict(base, observed=observed(r), wrong=0, concept=None))
            # Amendment 1: value outcomes only (the eval pool has no exceptions); drop rows whose truncated text
            # equals the correct one
            diffs = [res[m][k] for m in sources if m != 'canon' and res[m][k][0] == 'ok'
                     if (v := iorel.value(res[m][k])) is not None and not same(v, vr)
                     and observed(res[m][k]) != observed(r)]
            rng.shuffle(diffs)
            seen = set()
            for d in diffs:
                if len(seen) == WRONG_PER_INPUT or observed(d) in seen:
                    continue
                seen.add(observed(d))
                wrong.append(dict(base, observed=observed(d), wrong=1, concept=concept(r, d)))
        rng.shuffle(right)
        rng.shuffle(wrong)
        if right and wrong:
            stats['tasks'] += 1
            examples += right[:PER_CLASS_PER_TASK] + wrong[:PER_CLASS_PER_TASK]
    return examples, stats


def docstring(source, entry):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry:
            return ast.get_docstring(node)
    return None


def build_eval():
    run = ft_run.FTRun('vibepass_half')
    examples, stats = [], dict(cases=0, evaluable=0)
    for case in run.cases:
        cid = case['case_id']
        stats['cases'] += 1
        put = json.loads((V41 / cid / 'put' / 'result.json').read_text())['put']
        ref = json.loads((V41 / cid / 'ref' / 'result.json').read_text())
        inputs = json.loads((V41 / cid / 'put' / 'job.json').read_text())['inputs']
        if json.loads((V41 / cid / 'ref' / 'job.json').read_text())['inputs'] != inputs:
            raise ValueError(f'v41 put/ref inputs differ for case {cid}')
        spec = docstring(case['reference']['source'], case['reference']['entry'])
        exposing, other = [], []
        for k, call in enumerate(inputs):  # same labels as v41 exposure()
            if ref['contract'][k][0] != 'ok' or len(call) > MAX_LITERAL:
                continue
            a, b = iorel.value(put[k]), iorel.value(ref['ref'][k])
            if a is None or b is None:
                continue
            row = dict(task=f'vp{cid}', problem=spec, spec=spec, entry=case['entry'], call=call,
                       observed=observed(put[k]), wrong=int(not same(a, b)),
                       concept=concept(ref['ref'][k], put[k]) if not same(a, b) else None)
            (exposing if row['wrong'] else other).append(row)
        rng = random.Random(f'{SEED}-vp{cid}')
        rng.shuffle(exposing)
        rng.shuffle(other)
        chosen = exposing[:EVAL_EXPOSING] + other[:EVAL_OTHER]
        stats['evaluable'] += bool(exposing) and bool(other)
        stats[f'vp{cid}'] = dict(exposing_pool=len(exposing), other_pool=len(other))
        examples += chosen
    return examples, stats


def main():
    warnings.simplefilter('ignore', SyntaxWarning)  # mutants of regex string literals
    OUT.mkdir(parents=True, exist_ok=True)
    train, s1 = build_train()
    test, s2 = build_eval()
    for name, rows in (('train', train), ('eval', test)):
        (OUT / f'{name}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    counts = {c: sum(r['concept'] == c for r in train) for c in CONCEPTS}
    summary = dict(train=dict(s1, examples=len(train), wrong=sum(r['wrong'] for r in train), concepts=counts),
                   eval=dict(cases=s2['cases'], evaluable=s2['evaluable'], examples=len(test)))
    (OUT / 'build_summary.json').write_text(json.dumps(dict(summary, eval_pools=s2), indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
