"""B4 sample flow (hyp-hybrid, hyp-witness-only) on the inherited strict round two and caps.

hyp-hybrid: round 1 shows the top-3 hypotheses (R, chain, T). Round 2 targets every shown hypothesis whose T no
valid round-1 input satisfies: the task's domain strategy filtered by T (100 inputs, cap 500 draws, seeded per
sample), at most 2 verified inputs kept. Only when that T-filter yields no valid T-satisfying input (T unusable
as a filter) is the LLM asked for a strategy (at most one retry), verified by T. Then the inherited strict
expected-value request for exactly the kept inputs. hyp-witness-only: the witnesses of the shown hypotheses, no LLM.
"""
import json
import random
from . import fair_generation as fair, gen_prompts, hyp_prompts, rel_prompts
from . import v4_prompts, v4_runtime, v4_strategies


def classify(task, directory, python, hypotheses, **payload):
    try:
        return v4_runtime.isolated('hyp_classify', dict(task=task, hypotheses=hypotheses, **payload), directory, python)
    except RuntimeError as exc:
        n = len(payload.get('assertions', payload.get('candidates', [])))
        return dict(records=[], summary=dict(candidates=n, valid=0, removed=n, shown_hit_counts=[0]*len(hypotheses),
                                             classification_error=str(exc)[:500]))


def _pick(records, seed):
    good = [r for r in records if r['valid'] and r['hypothesis_hits'][0]]
    return good, random.Random(seed).sample(good, min(2, len(good)))


def generate(task, arm, sample, directory, python, query, n_calls, parse):
    """query(messages, stage, request, retry, label, strategy) -> text (enforces the call cap);
    n_calls() -> calls so far in this sample; parse(text) -> assertions."""
    shown = task['hypothesis_meta']['shown']
    out = dict(round1=[], selected=[], attempts=[], stage1_summaries=[], hint_budgets=[], count=0, dropped=0,
               strict_missing=0, dropped_round2_inputs=0, missed=[], r1=dict(summary=dict(shown_hit_counts=[])),
               t_filter_requests=0)
    if arm == 'hyp-witness-only':
        candidates = [dict(input_repr=h['witness']['input_repr']) for h in shown if h.get('witness')]
        flagged = classify(task, directory/'witnesses', python, shown, candidates=candidates)
        out['stage1_summaries'].append(flagged['summary'])
        out['selected'] = [r for r in flagged['records'] if r['valid']][:3]
        out['final'] = [f"assert {r['call']} == None" for r in out['selected']]
        return out
    messages, record = hyp_prompts.round1(task)
    out['hint_budgets'].append(dict(label='round1', **record))
    round1, out['dropped'] = fair.cap_assertions(parse(query(messages, 0, label='round1')))
    out['round1'] = round1
    r1 = classify(task, directory/'round1_inputs', python, shown, assertions=round1)
    out['r1'] = r1
    missed = [i for i, n in enumerate(r1['summary']['shown_hit_counts']) if not n]
    out['missed'] = missed
    selected = []
    for request, index in enumerate(missed):
        h = shown[index]
        seed = v4_prompts.seed(task['task'], arm, sample, 3, request)
        try:
            generated = v4_runtime.isolated('hyp_draw', dict(task=task, hypothesis=h, seed=seed),
                                            directory/f'filter_{request}', python, 180)
        except RuntimeError as exc:
            generated = dict(candidates=[], errors=[str(exc)[:500]])
        out['t_filter_requests'] += 1
        flagged = classify(task, directory/f'filter_classify_{request}', python, [h],
                           candidates=generated['candidates'], requested_draws=100)
        out['stage1_summaries'].append(flagged['summary'])
        good, picked = _pick(flagged['records'], seed)
        out['attempts'].append(dict(request=request, hypothesis_index=index, fact_index=None, method='T-filter',
                                    generated={k: v for k, v in generated.items() if k != 'candidates'},
                                    usable=bool(good), selected=picked))
        if good:
            selected += picked
            continue
        # T unusable as a filter: one LLM strategy request for this hypothesis, at most one retry, verified by T.
        messages, record = hyp_prompts.hybrid(task, index, round1)
        for retry in range(2):
            if n_calls() >= fair.MAX_CALLS-1: break
            out['hint_budgets'].append(dict(label=f'strategy_{request}_{retry}', **record))
            raw = query(messages, 1, request, retry, f'strategy_{request}_{retry}', True)
            out['count'] += 1
            error, generated, picked = None, None, []
            d = directory/f'request_{request}_{retry}'
            try:
                code = v4_strategies.checked(raw)
                generated = v4_strategies.draws(code, task, d, python, v4_prompts.seed(task['task'], arm, sample, 3, request, retry))
                flagged = classify(task, d/'classify', python, [h], candidates=generated['candidates'], requested_draws=100)
                out['stage1_summaries'].append(flagged['summary'])
                good, _ = _pick(flagged['records'], 0)
                if not good: error = 'No valid input satisfies the trigger T.'
                if generated['nonliteral'] or generated['wrong_arity'] or generated['errors']:
                    error = json.dumps({k: generated[k] for k in ('nonliteral', 'wrong_arity', 'errors')})
                if not error:
                    _, picked = _pick(flagged['records'], v4_prompts.seed(task['task'], arm, sample, 3, request, retry))
            except (SyntaxError, ValueError, RuntimeError) as exc:
                error = f'{type(exc).__name__}: {exc}'
            selected += picked
            out['attempts'].append(dict(request=request, retry=retry, hypothesis_index=index, fact_index=None,
                                        method='LLM-strategy', error=error, selected=picked,
                                        generated={k: v for k, v in (generated or {}).items() if k != 'candidates'}))
            if not error or retry == 1: break
            messages = messages + [dict(role='assistant', content=raw),
                                   dict(role='user', content=v4_prompts.RETRY.format(error=error))]
    selected = list({r['input_repr']: r for r in selected}.values())
    selected = fair.unseen_inputs(selected, round1, task['entry'])
    capacity = max(0, fair.MAX_ASSERTIONS-len(round1))
    out['dropped_round2_inputs'] = max(0, len(selected)-capacity)
    selected = selected[:capacity]
    expected = []
    if selected:
        messages, record = rel_prompts.normalize_extra(gen_prompts.strict_oracle_messages(task, selected), task, 'plain-hybrid')
        out['hint_budgets'].append(dict(label='oracle', **record))
        expected = parse(query(messages, 2, label='oracle'))
    out['final'], out['strict_missing'] = fair.strict_assertions(round1, selected, expected, task['entry'])
    out['selected'] = selected
    return out


def attribution(task, final, directory, python):
    shown = task['hypothesis_meta']['shown']
    try:
        return v4_runtime.isolated('hyp_attribution', dict(task=task, hypotheses=shown, assertions=final),
                                   directory/'hypothesis_attribution', python)['records']
    except RuntimeError as exc:
        return [dict(error=str(exc)[:500])]
