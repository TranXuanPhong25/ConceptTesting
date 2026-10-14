"""B4 hypothesis proposal: prompt, robust parsing, frozen ranking and the per-task cache.

No PUT, mutant or trigger code executes here; every execution is in hyp_worker (isolated v4 worker).
One logical proposal call per task (fixed seed, temperature 0), shared by all K samples and all hyp arms.
It is accounted separately from the per-sample caps (8 calls / 20 assertions).
"""
import ast
import difflib
import fcntl
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import preconditions, v4_runtime
from .llm_client import atomic_json
from .paths import CONFIG

VERSION = 'spec-violation-v1'
ARMS = ('hyp-hybrid', 'hyp-witness-only')
MAX_PROPOSALS = 6
SHOWN = 3
SEARCH_DRAWS = 200
MUTANT_WITNESSES = 20   # witnesses (of the 200-draw search) checked against surviving mutants
SYSTEM = 'You are an expert software tester. Reply with JSON only.'
INSTRUCTION = '''The Python function below passes its existing tests, but it may still violate its specification.
Propose up to 6 hypotheses about how it may violate the specification, most likely first. Consider ALL code
sites listed below, including sites the existing tests already execute (a bug can sit on a covered line and
show only for particular values). Each hypothesis links:
- R: a clause of the specification, quoted exactly from the docstring;
- chain: the code path, value from line A -> condition at line B -> line C (line numbers as in the listing);
- T: a trigger, a pure Python predicate over the function's arguments that holds exactly for the inputs
  that should expose the violation, written as "def trigger(<parameters>):\\n    return <boolean expression>";
  use only builtins and string methods; no imports, I/O, mutation, or calls to the function under test;
- expected_violation: how the output breaks R when T holds.
The tool relations below are observed facts; a missing edge means unknown. Do not give concrete test calls.
Reply with a JSON array of objects with keys "R", "chain" ({"lines": [A, B, C], "explanation": "..."}),
"T" and "expected_violation".'''


def proposal_seed(task):
    return CONFIG['seeds']['hypotheses'] + int(task['task'])


def numbered(put):
    return '\n'.join(f'{i:>3}| {line}' for i, line in enumerate(put.splitlines(), 1))


def proposal_messages(task, candidates):
    sites = '\n'.join(f"- {r['chain']} [{'executed' if r['covered'] else 'NOT executed'} by existing tests]"
                      for r in candidates['sites'])
    user = (INSTRUCTION + '\n\nSPECIFICATION:\n' + preconditions.specification(task)[0] +
            '\n\nCODE (line numbers):\n' + numbered(task['put']) +
            '\n\nEXISTING TESTS:\n' + task['base'].strip() +
            '\n\nCODE SITES AND RELATIONS (computed by a tool; no inputs shown):\n' + sites + '\n')
    return [dict(role='system', content=SYSTEM), dict(role='user', content=user)]


def trigger_source(raw, task):
    """Reuse the B5 AST purity checker/wrapper; accept a function, a lambda or a bare expression."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('T must be Python source')
    raw = re.sub(r'^```(?:python|py)?\s*\n|\n```\s*$', '', raw.strip())
    params = preconditions.specification(task)[2]
    tree = ast.parse(raw)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(tree.body) == 1 and functions:
        fn = functions[0]
    else:
        expr = ast.parse(raw, mode='eval').body
        if isinstance(expr, ast.Lambda):
            fn = ast.FunctionDef(name='trigger', args=expr.args, body=[ast.Return(expr.body)], decorator_list=[])
        else:
            fn = ast.FunctionDef(name='trigger', args=params, body=[ast.Return(expr)], decorator_list=[])
    return preconditions.predicate(fn, 'trigger', params)


def _rows(raw):
    """First JSON array (or {"hypotheses": [...]}) in the reply; fences and prose around it are ignored."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r'[\[{]', raw):
        try:
            value, _ = decoder.raw_decode(raw[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict) and isinstance(value.get('hypotheses'), list):
            return value['hypotheses']
        if isinstance(value, list) and any(isinstance(v, dict) for v in value):
            return value
    return None


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def quotation(r, doc):
    """'exact' if R's words occur contiguously in the docstring (case/punctuation ignored); 'near' if some
    docstring window of the same length matches with difflib ratio >= 0.9 (typo fixes, e.g. 'fallls'); else None."""
    rw, dw = _words(r), _words(doc)
    if not rw: return None
    phrase, text = ' '.join(rw), ' '.join(dw)
    if f' {phrase} ' in f' {text} ': return 'exact'
    for i in range(max(1, len(dw)-len(rw)+1)):
        if difflib.SequenceMatcher(None, phrase, ' '.join(dw[i:i+len(rw)])).ratio() >= 0.9: return 'near'
    return None


def _lines(chain):
    if isinstance(chain, dict):
        lines = chain.get('lines')
        if lines is None and all(k in chain for k in ('A', 'C')):
            lines = [chain[k] for k in ('A', 'B', 'C') if chain.get(k) is not None]
        explanation = chain.get('explanation') or chain.get('description')
    elif isinstance(chain, str):
        lines, explanation = [int(n) for n in re.findall(r'\blines?\s+(\d+)', chain)], chain
    else:
        raise ValueError('missing code chain')
    if isinstance(lines, list):
        lines = [int(n) if isinstance(n, str) and n.strip().isdigit() else n for n in lines]
    return lines, explanation


def parse_proposals(raw, task, candidates):
    """Reject bad rows individually (recorded with a reason); code is never repaired."""
    value = _rows(raw or '')
    if value is None:
        return [], [dict(reason='proposal_parse_failed')]
    kept, failures = [], []
    doc = preconditions.specification(task)[1]
    allowed = {s['line'] for s in candidates['sites']}
    covered = {s['line'] for s in candidates['sites'] if s['covered']}
    for order, row in enumerate(value):
        try:
            if order >= MAX_PROPOSALS:
                raise ValueError('proposal cap exceeded')
            if not isinstance(row, dict):
                raise ValueError('hypothesis must be an object')
            r = row.get('R', row.get('spec_clause'))
            t = row.get('T', row.get('trigger'))
            violation = row.get('expected_violation', row.get('violation'))
            quoted = quotation(r, doc) if isinstance(r, str) else None
            if not quoted:
                raise ValueError('R is not a specification quotation')
            lines, explanation = _lines(row.get('chain', row.get('code_chain')))
            if (not isinstance(lines, list) or not lines or any(type(n) is not int or n not in allowed for n in lines)
                    or not isinstance(explanation, str) or not explanation.strip()):
                raise ValueError('chain must reference candidate code lines with an explanation')
            if not isinstance(violation, str) or not violation.strip():
                raise ValueError('missing expected violation')
            source = trigger_source(t, task)
            kept.append(dict(kind='HYP', order=order, R=r.strip(), R_quotation=quoted, chain=' -> '.join(f'line {n}' for n in lines)
                             + ': ' + ' '.join(explanation.split()), chain_lines=lines, T=t.strip(),
                             trigger_src=source, expected_violation=violation.strip(),
                             covered_site=lines[-1] in covered, covered_lines=sorted(set(lines) & covered)))
        except (SyntaxError, ValueError, TypeError) as exc:
            failures.append(dict(order=order, reason='proposal_rejected', error=f'{type(exc).__name__}: {exc}'))
    return kept, failures


def rank(rows):
    """Witnessed + PUT differs from a surviving mutant on the witness, then witnessed, then unwitnessed.
    Ties: the task-level frozen order (the proposal order of the single cached reply)."""
    return sorted(rows, key=lambda h: (0 if h.get('witness') and h.get('mutant_diff') else
                                      1 if h.get('witness') else 2, h['order']))


def cache_key(task, model):
    # Sources = this module and its worker only: unrelated edits must not invalidate proposals.
    sources = {p: preconditions.sha((v4_runtime.HERE/p).read_bytes())
               for p in ('hypotheses.py', 'hyp_worker.py', 'relations.py', 'tracer.py', 'v4_worker.py', 'v4_tools.py')}
    return preconditions.sha(json.dumps(dict(task=task, model=model, seed=proposal_seed(task), version=VERSION,
                                             tools=v4_runtime.VERSIONS, sources=sources), sort_keys=True))


def prepare(task, client, directory, python):
    """One logical proposal call per task, no repair call; the summary is shared by all K samples."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    key = cache_key(task, client.model)
    with (directory/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = directory/'summary.json'
        if saved.exists():
            result = json.loads(saved.read_text())
            if result['cache_key'] != key:
                raise ValueError('hypothesis cache changed; use a fresh directory')
            return result
        candidates = v4_runtime.isolated('hyp_candidates', dict(task=task), directory/'candidates', python, 3600)
        messages = proposal_messages(task, candidates)
        atomic_json(directory/'proposal_prompt.json', messages)
        # Transport errors propagate: an offline cache miss must never masquerade as a proposal failure.
        response = client.chat(messages, proposal_seed(task), temperature=0, top_p=1, max_tokens=4096)
        atomic_json(directory/'proposal_response.json', response)
        rows, failures = parse_proposals(response['text'], task, candidates)
        if rows:
            try:
                checked = v4_runtime.isolated('hyp_check', dict(task=task, hypotheses=rows, candidates=candidates,
                                              seed=proposal_seed(task)), directory/'checks', python, 3600)
            except RuntimeError as exc:
                checked = dict(hypotheses=[], failures=[dict(reason='tool_check_failed', error=str(exc)[:500])])
        else:
            checked = dict(hypotheses=[], failures=[])
        ranked = rank(checked['hypotheses'])
        result = dict(task=task['task'], version=VERSION, cache_key=key, seed=proposal_seed(task),
                      hypotheses=ranked, shown=ranked[:SHOWN], failures=failures+checked['failures'],
                      proposed=len(rows)+sum(f.get('reason') == 'proposal_rejected' for f in failures),
                      parsed=len(rows), candidate_sites=len(candidates['sites']),
                      covered_sites=sum(s['covered'] for s in candidates['sites']), base_ok=candidates['base_ok'],
                      survivor_mutants=len(candidates['survivor_mutants']),
                      proposal_calls=1, proposal_cache_hit=bool(response.get('cache_hit', False)),
                      n_in=response.get('n_in', 0), n_out=response.get('n_out', 0), seconds=response.get('seconds', 0))
        atomic_json(saved, result)
        return result


def prepare_tasks(tasks, client, root, python, workers=1):
    root = Path(root)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(lambda t: prepare(t, client, root/str(t['task']), python), tasks))
    summary = dict(version=VERSION, tasks=len(results), proposal_calls=sum(r['proposal_calls'] for r in results),
                   n_in=sum(r['n_in'] for r in results), n_out=sum(r['n_out'] for r in results),
                   parsed=sum(r['parsed'] for r in results), kept=sum(len(r['hypotheses']) for r in results),
                   witnessed=sum(h['witnessed'] for r in results for h in r['hypotheses']),
                   accounting='one task-level proposal call per task, shared by K samples and both hyp arms; '
                              'not counted in any per-sample generation cap')
    atomic_json(root/'proposal_accounting.json', summary)
    return results, summary


def slim(result):
    """What generation needs; per-draw search records stay in the cache directory only."""
    keep = ('order', 'R', 'R_quotation', 'chain', 'chain_lines', 'T', 'trigger_src', 'expected_violation', 'covered_site',
            'covered_lines', 'witness', 'witnessed', 'unwitnessed', 'mutant_diff', 'differing_mutants', 'filter_usable')
    rows = [{k: h[k] for k in keep if k in h} for h in result['hypotheses']]
    return dict(version=result['version'], cache_key=result['cache_key'], hypotheses=rows, shown=rows[:SHOWN],
                failures=result['failures'], proposal_calls=result['proposal_calls'],
                n_in=result['n_in'], n_out=result['n_out'])
