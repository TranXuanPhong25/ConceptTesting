"""B4 visible blocks: R, chain and T only. Witnesses, search and mutant metadata are never rendered.

Input budget = v12_rel rule, per unit: the round-one block is fitted to the task's rel-hybrid round-one block
length; a round-two block for shown hypothesis i is fitted to the rel rendering of hint i (the same unit as a
rel-hybrid round-two request), or to the whole rel block when the task has no hint i.
"""
from . import gen_prompts, prompts, rel_prompts, v4_prompts

HEAD = ('\n## Hypotheses about how the code may violate its specification\n'
        'Each links a specification clause (R) to a code path (chain) and gives a trigger predicate T over the '
        'arguments; inputs satisfying T should expose the violation.\n')
TAIL = 'Use these hypotheses when choosing inputs.\n'


def render(h):
    return f'R: "{h["R"]}"\n  chain: {h["chain"]}\n  T:\n' + ''.join(f'    {line}\n' for line in h['T'].splitlines())


def raw_block(task, index=None):
    shown = task['hypothesis_meta']['shown']
    if not shown: return ''
    if index is not None: return render(shown[index])
    return HEAD + ''.join(f'- {render(h)}' for h in shown) + TAIL


def block(task, index=None):
    ref_index = index if index is not None and index < len(task['concept_meta']) else None
    target = rel_prompts.unit_target(task, index)   # B4 amendment 1: never truncates the hypothesis block
    raw = raw_block(task, index)
    normalized = rel_prompts.fit(raw, target)
    return normalized, dict(proxy=rel_prompts.PROXY, target=target, raw=rel_prompts.tokens(raw),
                            actual=rel_prompts.tokens(normalized), padded=max(0, target-rel_prompts.tokens(raw)),
                            truncated=max(0, rel_prompts.tokens(raw)-target), hint_index=ref_index,
                            hypothesis_index=index)


def round1(task):
    system, user = prompts.build('plain', task)
    extra, record = block(task)
    at = len(prompts.HEAD.format(put=task['put'].rstrip(), base=task['base'].strip()))
    return gen_prompts.messages(system, user[:at] + extra + user[at:]), record


def hybrid(task, index, assertions=()):
    """LLM strategy request for one hypothesis (only when T is unusable as a filter); same template as rel."""
    messages = v4_prompts.hybrid_messages(task, dict(text=''), assertions)
    extra, record = block(task, index)
    body = messages[-1]['content']
    assert body.endswith('\n\nFACT:\n')
    messages[-1]['content'] = body + extra
    return messages, record
