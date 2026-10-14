r"""B3 prompt blocks; raw flat builders preserve the v11 bytes.

Budget proxy = number of non-whitespace runs (re.findall(r'\S+', text)).
Normalize only the extra hint block, never code/spec/base/strategy/assertions.
Pad with semantically inert `.` tokens; truncation keeps the original prefix.
Zero hints => zero budget, including review. Equalization is enabled only when
at least one new arm is selected, so legacy requests and cache keys are stable.
"""
import re
from . import prompts, gen_prompts, v4_prompts, relations

NEW_ARMS = ('review-hybrid', 'flat-hybrid', 'rel-hybrid', 'rel-nospec-hybrid')
REFERENCES = ('plain-hybrid', 'toolinput', 'witness-only', 'placebo-hybrid')
REVIEW = ('\n## Review checklist\n'
          'Check boundaries, off-by-one, empty and singleton inputs, ordering/ties, types, and large values.\n')
PROXY = 'non-whitespace-runs-v1'


def tokens(text):
    return len(re.findall(r'\S+', text))


def fit(block, budget):
    spans = list(re.finditer(r'\S+', block))
    if len(spans) > budget:
        return block[:spans[budget-1].end()] + '\n' if budget else ''
    if len(spans) < budget:
        return block + '\n' + ' '.join('.' for _ in range(budget-len(spans))) + '\n'
    return block


def raw_block(arm, task, hint_index=None):
    if arm == 'review-hybrid': return REVIEW
    if arm in ('rel-hybrid', 'rel-nospec-hybrid'):
        rows = task['relation_meta']['hints']
        indices = range(len(rows)) if hint_index is None else (hint_index,)
        if not rows: return ''
        texts = [task['concept_meta'][i]['text'] + '\n  ' +
                 relations.render(rows[i], include_spec=arm != 'rel-nospec-hybrid') for i in indices]
        if hint_index is not None: return texts[0]
        return prompts.FACTS_HEAD + ''.join(f'- {t}\n' for t in texts) + prompts.FACTS_TAIL
    if arm in ('flat-hybrid', 'concept-hybrid'):
        return (task['concept_meta'][hint_index]['text'] if hint_index is not None
                else prompts.section('concept', task))
    if arm == 'placebo-hybrid': return prompts.section('placebo', task)
    if arm == 'toolinput': return prompts.section('toolinput', task)
    return ''


def unit_target(task, index=None):
    """Token budget of one unit (round-one block, or round-two unit i). v13 amendment (PREREG B4 amendment 1): when the
    task carries hypotheses, the budget is the longer of the rel rendering and the hypothesis rendering of the same
    unit, so the hypothesis block is never truncated; every other arm is padded to it. Without hypotheses = v12_rel."""
    target = tokens(raw_block('rel-hybrid', task, index if index is not None and index < len(task.get('concept_meta', [])) else None))
    if task.get('hypothesis_meta', {}).get('shown'):
        from . import hyp_prompts
        shown = task['hypothesis_meta']['shown']
        if index is None or index < len(shown):
            target = max(target, tokens(hyp_prompts.raw_block(task, index)))
    return target


def block(arm, task, hint_index=None):
    # Budget = the rel arm's block for the same unit: the complete three-hint block in round one, and the rel
    # rendering of the same single hint for a round-two target (Claude 2026-10-14: a single hint used to be padded
    # to the three-hint length, adding hundreds of filler tokens to round-two prompts).
    target = unit_target(task, hint_index)
    raw = raw_block(arm, task, hint_index)
    normalized = fit(raw, target)
    return normalized, dict(proxy=PROXY, target=target, raw=tokens(raw), actual=tokens(normalized),
                            padded=max(0,target-tokens(raw)), truncated=max(0,tokens(raw)-target),
                            hint_index=hint_index)


def round1(arm, task, *, equalize=True):
    kind = 'concept' if arm in ('flat-hybrid', 'concept-hybrid') else 'placebo' if arm == 'placebo-hybrid' else 'plain'
    system, user = prompts.build(kind, task)
    old = prompts.section(kind, task)
    if equalize:
        extra, record = block(arm, task)
    else:
        extra, record = raw_block(arm, task), None
    # Replace by offset, not str.replace: identical text may occur in a docstring.
    at = len(prompts.HEAD.format(put=task['put'].rstrip(), base=task['base'].strip()))
    user = user[:at] + extra + user[at+len(old):]
    return gen_prompts.messages(system, user), record


def hybrid(arm, task, hint_index, assertions=(), *, equalize=True):
    fact = task['concept_meta'][hint_index]
    hidden = arm in ('review-hybrid', 'plain-hybrid')
    messages = v4_prompts.hybrid_messages(task, None if hidden else fact, assertions)
    raw = raw_block(arm, task, hint_index)
    if equalize:
        extra, record = block(arm, task, hint_index)
    else:
        extra, record = raw, None
    body = messages[-1]['content']
    if not hidden:
        body = body[:-len('\n\nFACT:\n'+fact['text'])]
    messages[-1]['content'] = body + ('\n\nFACT:\n' if not hidden else '\n\nGUIDANCE:\n') + extra
    return messages, record


def normalize_extra(messages, task, arm, original=''):
    """Reference/oracle requests use the whole-task rel budget, with no new facts."""
    extra, record = block(arm, task)
    user = messages[-1]['content']
    if original:
        at = len(prompts.HEAD.format(put=task['put'].rstrip(), base=task['base'].strip()))
        user = user[:at] + extra + user[at+len(original):]
    else:
        user += '\n\n' + extra
    return messages[:-1] + [dict(messages[-1], content=user)], record
