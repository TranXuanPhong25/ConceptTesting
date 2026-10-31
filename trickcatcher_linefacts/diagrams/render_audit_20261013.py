"""Documentation diagrams only; no research pipeline execution."""
from render_pipelines import canvas, node, arrow, save


def render(name, title, subtitle, columns, footer):
    fig, ax = canvas(title, subtitle, 19, 12)
    xs, w, h, step = [.4, 6.8, 13.2], 5.4, 1.6, 2.03
    for col, (heading, boxes) in enumerate(columns):
        x = xs[col]
        ax.text(x, 1.85, heading, fontsize=13, fontweight='bold', color='#172338')
        for row, (label, fn, lines, kind) in enumerate(boxes):
            y = 2.1 + row*step
            node(ax, x, y, w, h, label, fn, lines, kind)
            if row:
                arrow(ax, [(x+w/2, y-step+h), (x+w/2, y)])
    # Snake between columns, leaving a gutter and no crossing of boxes.
    for col in (0, 1):
        x = xs[col]+w; nextx = xs[col+1]
        lasty = 2.1 + 3*step + h/2
        mid = (x+nextx)/2
        arrow(ax, [(x,lasty), (mid,lasty), (mid,2.9), (nextx,2.9)])
    for i, line in enumerate(footer):
        ax.text(.45, 10.35+i*.34, line, fontsize=11, color='#344358')
    save(fig, name)


render('audit_execution_20261013', 'LINEFACTS — verified execution and scoring',
       'Observed method: v7 | Strict result: CPU reconstruction of v7 | Audit 2026-10-13', [
    ('1. Build facts from method-visible inputs', [
        ('Specification + PUT + base tests', '139 HumanEval PUTs; exclude 6 design tasks',
         ['113 DEV + 20 historical pilot tasks', 'Canonical / plus labels are reserved for scoring'], 'CUSTOM'),
        ('Mine input validity and domain strategy', 'preconditions.mine + run_v4.mine',
         ['B5: observe, confirm, code, verify on base tests', 'Spec -> valid.py and Hypothesis domain strategy'], 'LLM'),
        ('Trace, fuzz, mutate, rank top 3', 'facts.py / tracer.py; v6 recipe',
         ['Base-derived fuzz uses B5; custom mutants', 'Reached facts only; gates, G-prime, block diversity'], 'CONCEPT'),
        ('SPEC fallback and task bundle', 'spec_facts.build / run_v6.bundle',
         ['Only when no code hint: LARGE / DUP / text classes', 'Bundle: hint text, metadata, witnesses, placebo'], 'CONCEPT'),
    ]),
    ('2. Generate inputs / assertions', [
        ('Round 1: plain, concept, placebo', 'run_v4.run / prompts.build',
         ['LLM sees spec, PUT, base tests; <=10 assertions', 'Hybrid reuses corresponding round-1 assertions'], 'LLM'),
        ('Round 2: target missing shown facts', 'v4_prompts.hybrid_messages / v4_worker',
         ['Hypothesis strategy -> 100 draws -> validate + hit', 'Up to 2 inputs/request; targeted retry <=1'], 'LIB'),
        ('Control and witness comparisons', 'plain-hybrid / placebo-hybrid / toolinput',
         ['Plain matches strategy calls, but has no retry loop', 'Placebo has its own budget; toolinput uses witnesses'], 'CUSTOM'),
        ('Expected values and merge', 'gen_prompts.oracle_messages / v8_strict_est.strict',
         ['v7 allows extra assertions, even with empty input set', 'v8 keeps round 1 + selected inputs; None if missing'], 'LLM'),
    ]),
    ('3. Oracle and independent measurement', [
        ('Collect distinct generated calls', 'oracle_b01.collect',
         ['Other path: gen-plain writes a sample_one generator', 'All arms use the same scoring rules'], 'CUSTOM'),
        ('Operational oracle: ref / optional full', 'oracle_b01.llm / worker / decide',
         ['10 spec-only programs; keep base-pass programs', 'ref: >=3 survivors, unanimous successful output'], 'LLM'),
        ('Canonical + contract evaluate outputs', 'oracle_b01.score / analysis worker',
         ['Valid input + correct oracle + failing PUT -> detect', 'Separate input discovery, oracle error, abstention'], 'SCORE'),
        ('Task-level aggregation, K = 3', 'analysis/audit_20261013.py',
         ['Raw + budget sensitivities + per-task sign test', 'DEV / pilot / MBPP12 reported separately'], 'SCORE'),
    ]),
], ['v8 is not a fresh strict generation run: original LLM costs remain in its rows; hybrid o0 is not interpretable.',
    'v8 has no judge responses: its full column is ref + postconditions. No supervised concept-learning stage exists.',
    'DEV labels informed gates/ranking across versions. This is development feedback, not independent confirmation.'])

render('proposed_relations_20261013', 'PROPOSED — concepts and relations to bug hypotheses',
       'Design proposal, not implemented or evaluated | Extends linefacts | No canonical or hidden tests in reasoning', [
    ('1. Ground the representation', [
        ('Specification obligations', 'signature + original docstring + public tests',
         ['Domain D(x); relation R(x, output); evidence quote', 'Ambiguous or inferred rules retain uncertainty'], 'CONCEPT'),
        ('Statement concepts', 'extend existing AST sites and tracer',
         ['Guards, initialization, updates, normalization, return', 'Keep both covered and uncovered code'], 'CONCEPT'),
        ('Control and data relations', 'CFG + def-use + control dependencies',
         ['Branch polarity, reaching definition, loop-carried use', 'Observed traces are not universal path proofs'], 'LIB'),
        ('Small slices linked to obligations', 'typed node / edge IDs + source spans',
         ['One obligation and its relevant code slice per item', 'Missing implementation can also be a candidate'], 'CONCEPT'),
    ]),
    ('2. Hypothesize and verify a bug', [
        ('Explicit bug hypothesis', 'LLM consumes obligation + concept relation slice',
         ['State mismatch, implicated nodes, predicted symptom', 'Store cited relations; reject unsupported edge claims'], 'LLM'),
        ('Derive trigger conditions', 'domain AND reach AND divergence AND propagation',
         ['Account for overwrites, early exits and loop order', 'Do not require an existing fuzz witness to enqueue'], 'CONCEPT'),
        ('Search for a witness', 'Hypothesis strategy; bounded constraint solving',
         ['Reuse base/fuzz seeds, shrink successful inputs', 'Try limited symbolic support; timeout means unknown'], 'LIB'),
        ('Verify and feed back evidence', 'existing sandbox + extended relation tracing',
         ['Check validity, path, local effect, observable effect', 'Retry within fixed budget; no proof -> unconfirmed'], 'LIB'),
    ]),
    ('3. Confirm and evaluate', [
        ('Confirm a counterexample', 'spec property or independent operational oracle',
         ['If ref used in search, account for it in all controls', 'A killed mutant alone does not prove a PUT bug'], 'SCORE'),
        ('Produce a compact bug report', 'rule + locations + trigger + input + evidence',
         ['Label confirmed, ref-supported, or ambiguous', 'Keep unsupported hypotheses out of confirmed count'], 'CUSTOM'),
        ('Controlled ablations', 'fixed model, tool access, calls, tokens, final tests',
         ['Generic review / flat concepts / typed relations', 'Remove edges or spec links; add witness baseline'], 'SCORE'),
        ('Fresh task-level confirmation', 'frozen protocol on a new held-out set',
         ['D_I, D_IO, report precision, localization, total cost', 'Report wrong-output and crash/timeout separately'], 'SCORE'),
    ]),
], ['Example: max_word=None -> zero unique characters -> equality branch -> compare string with None -> TypeError.',
    'Business rule connects the slice to the expected result: maximize distinct characters, then lexicographic order.',
    'This is concept-and-relation-guided inference. Claiming ConceptCoder-style learning would additionally require supervision.'])
