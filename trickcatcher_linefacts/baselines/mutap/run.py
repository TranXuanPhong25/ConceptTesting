"""MuTAP (Dakhel et al., IST 2024; arXiv 2308.16557) in the TrickCatcher setting, budgeted.

Prompts and chat dialogs are the authors' own functions, compiled from the vendored repository
(`vendor/mutap`, unmodified): `initalPromptGenerator`, `synxPromptGenerator`, `synxtaxfixer`
(MuTAP/generate_test_oracle.py), `mutatePromptGenerator` (MuTAP/augmented_prompt.py) and the chat-model
dialog builder `generate_dialag` (llama_util/chat_utils.py, used for Llama-2-chat). The driver follows
the paper: initial prompt -> syntax fix -> functional (semantic) repair -> mutation testing -> one
augmented prompt per surviving mutant (re-screening after each). Greedy minimization is recorded
as a diagnostic; comparison output retains generation order to obey the registered cap.

  python -m trickcatcher_linefacts.baselines.mutap.run --tasks <bundle.json> --out <dir> --k 3 [--online]
"""
import ast
import os
from pathlib import Path

from ..common import cli, code_block, digest, extract_assertions, helper_functions, original_definitions, specification, worker

VENDOR = Path(__file__).resolve().parent/'vendor/mutap'
PIN = '57c38c0c13df2c4d2b5714491e2c67a6d0463928'
SOURCES = ['MuTAP/generate_test_oracle.py', 'MuTAP/augmented_prompt.py', 'MuTAP/Sematic_err_correction.py',
           'MuTAP/greedy_test_generator.py', 'llama_util/chat_utils.py']
SYNTAX_ATTEMPTS = 10    # generate_test_oracle: "up to 10 attempts"
DIALOG_DATASET = 'HumanEval'   # only used by the authors' few-shot branch, which is not selected


def provenance():
    if not (VENDOR/SOURCES[0]).exists():
        raise FileNotFoundError('restore baselines/mutap/vendor/mutap at '+PIN+' (see README)')
    return dict(paper='MuTAP (Dakhel et al., IST 2024)', commit=PIN,
                source_sha256={f: digest((VENDOR/f).read_text()) for f in SOURCES},
                prompt='normal (zero-shot), chat dialogs of llama_util/chat_utils.generate_dialag',
                mutation='mutmut 3 source API (vendored artifact uses MutPy); no fallback',
                syntax_attempts=SYNTAX_ATTEMPTS, selection='generation order; greedy selection recorded separately')


def load_prompts():
    ns = original_definitions(VENDOR/'MuTAP/generate_test_oracle.py',
                              ['initalPromptGenerator', 'synxPromptGenerator', 'synxtaxfixer'], dict(ast=ast))
    ns.update(original_definitions(VENDOR/'MuTAP/augmented_prompt.py', ['mutatePromptGenerator']))
    ns.update(original_definitions(VENDOR/'llama_util/chat_utils.py', ['generate_dialag'], dict(os=os)))
    return ns


def dialog(prompts, kind, prompt, code='', test=''):
    """The authors' chat dialog for one prompt ('normal', 'syn_fix' or 'mutant')."""
    return prompts['generate_dialag'](kind, DIALOG_DATASET, [prompt], code, test)[0]


def greedy(order, kills):
    """greedy_test_generator.run_asserts_on_scripts/filter_greedily: drop assertions killing no mutant, sort by
    kills (descending, stable), add an assertion when the accumulated suite then fails on more mutants."""
    ranked = sorted((a for a in order if kills.get(a)), key=lambda a: -len(kills[a]))
    chosen, covered = [], set()
    for a in ranked:
        if len(covered | set(kills[a])) > len(covered):
            chosen.append(a)
            covered |= set(kills[a])
    return chosen, covered


def generate(task, session, config):
    P = load_prompts()
    entry, put, base = task['entry'], task['put'], task['base']
    helpers = helper_functions(base)
    passing, raising, raw_tests, details, rejected, history = [], [], [], [], [], []
    generation_order = []
    baseline = worker('screen', dict(task, assertions=[], mutants=[]), session.directory/'base_check')
    if not baseline['ok']:
        return dict(assertions=[], stop_reason='base_failed', diagnostics=baseline)
    if not session.remaining:
        return dict(assertions=[], stop_reason='llm_budget', raw_tests=[])
    # Preserve the authors' prompt template, embedding external spec text as Python comments.
    spec = specification(task)
    spec_context = ('\n\n# Specification:\n' + '\n'.join('# ' + line for line in spec.splitlines())) if spec else ''
    program = put.rstrip() + spec_context + '\n\n' + base.strip() + '\n'

    def refine(raw, stage):
        """Syntax fix (authors' prompt, then their truncation) and functional repair of one test script."""
        code = code_block(raw)
        raw_tests.append(dict(stage=stage, code=code))
        for _ in range(SYNTAX_ATTEMPTS):
            try:
                ast.parse(code)
                break
            except SyntaxError:
                if not session.remaining:
                    break
                code = code_block(session.query(dialog(P, 'syn_fix', P['synxPromptGenerator'](code)), 'syntax_fix'))
                raw_tests.append(dict(stage=stage + '/syntax_fix', code=code))
        try:
            code = P['synxtaxfixer'](code)
        except RecursionError:
            code = ''
        found, dropped = extract_assertions(code, entry, put, helpers)
        rejected.extend(dict(d, stage=stage) for d in dropped)
        result = worker('repair', dict(put=put, base=base, assertions=found), session.directory/f'repair_{stage}')
        if not result['ok']:
            history.append(dict(stage=stage, repair=result))
            return
        for d in result['details']:
            details.append(dict(d, stage=stage))
            target = passing if d['status'] in ('pass', 'repaired') else raising if d['status'] == 'raises' else None
            if target is not None and d['assertion'] not in passing + raising:
                target.append(d['assertion'])
                generation_order.append(d['assertion'])

    def suite_text():
        # The IUT shown to the model: program + `def test():` with the current (refined) assertions.
        return program + '\n\ndef test():\n    ' + '\n    '.join([f'check({entry})'] + passing) + '\n'

    pool = worker('mutants', dict(put=put, max_mutants=config.max_mutants), session.directory/'mutants')
    if not pool['ok']:
        return dict(assertions=[], stop_reason='mutation_failed', diagnostics=pool,
                    raw_tests=raw_tests, semantic_repairs=details, extraction_rejected=rejected)
    mutants = pool['mutants']
    base_screen = worker('screen', dict(task, assertions=[], mutants=mutants), session.directory/'screen_base', timeout=150)
    if not base_screen['ok']:
        return dict(assertions=[], stop_reason='base_screen_failed', diagnostics=base_screen)
    statuses = {m['id']: m['status'] for m in base_screen['mutants']}
    base_live = [m for m in mutants if statuses[m['id']] == 'survived']
    live = base_live[:config.max_surviving_mutants]
    refine(session.query(dialog(P, 'normal', P['initalPromptGenerator'](program)), 'initial'), 'initial')
    targeted, stop = [], 'llm_budget'
    while True:
        screening = worker('screen', dict(task, assertions=passing, mutants=live), session.directory/f'screen_{len(targeted)}', timeout=150)
        history.append(dict(targeted=list(targeted), screen=screening))
        if not screening['ok']:
            stop = 'suite_failed'
            break
        status = {m['id']: m['status'] for m in screening['mutants']}
        surviving = [m for m in live if status[m['id']] == 'survived' and m['id'] not in targeted]
        if not surviving:
            stop = 'surviving_mutant_limit' if len(base_live) > len(live) else 'survivors_exhausted'
            break
        if not session.remaining:
            break
        mutant = surviving[0]
        targeted.append(mutant['id'])
        current = '\n    '.join([f'check({entry})'] + passing)
        messages = dialog(P, 'mutant', P['mutatePromptGenerator'](suite_text(), mutant['source']), program, current)
        refine(session.query(messages, f'augment_{mutant["id"]}'), f'augment_{mutant["id"]}')
    # Greedy minimization over mutants that survive the base tests (kills by base are not the tests' merit).
    matrix = worker('matrix', dict(assertions=passing, mutants=live, cpu_seconds=600), session.directory/'matrix', timeout=650) \
        if passing and live else dict(ok=True, kills={a: [] for a in passing})
    kills = matrix.get('kills', {}) if matrix['ok'] else {}
    chosen, covered = greedy(passing, kills)
    survived_all = [m['id'] for m in live if all(m['id'] not in kills.get(a, []) for a in passing)]
    return dict(assertions=generation_order, raw_assertions=generation_order,
                greedy_selected=chosen, refined_passing=passing,
                kept_raising=raising, raw_tests=raw_tests, extraction_rejected=rejected, semantic_repairs=details,
                mutation_backend=pool['backend'],
                n_mutants_generated=pool['n_generated'], n_mutants=len(mutants), n_live_after_base=len(base_live),
                n_live_selected=len(live), max_surviving_mutants=config.max_surviving_mutants,
                base_mutant_statuses=base_screen['mutants'],
                live_mutants=[m['id'] for m in live], targeted_mutants=targeted,
                killed_by_refined=sorted(covered), surviving_after_refined=survived_all,
                kill_matrix=kills, matrix_diagnostics={k: v for k, v in matrix.items() if k != 'kills'},
                mutation_history=history, stop_reason=stop)


if __name__ == '__main__':
    cli('mutap', generate, provenance)
