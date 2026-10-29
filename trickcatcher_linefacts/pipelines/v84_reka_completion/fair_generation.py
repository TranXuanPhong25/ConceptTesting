"""Generation constraints, enabled only by the corresponding config flags."""
import ast
from . import oracle_b01

MAX_CALLS = 8
MAX_ASSERTIONS = 20


def cap_assertions(assertions):
    return assertions[:MAX_ASSERTIONS], max(0, len(assertions) - MAX_ASSERTIONS)


def unseen_inputs(selected, round1, entry):
    seen = {oracle_b01.call_of(a, entry) for a in round1}
    kept = []
    for row in selected:
        if row['call'] not in seen:
            seen.add(row['call'])
            kept.append(row)
    return kept


def strict_assertions(round1, selected, generated, entry):
    # Same construction/order as v8_strict_est.strict, including recorded missing
    # expected-value placeholders. Unrequested calls are never admitted.
    by_call = {}
    for assertion in generated:
        try:
            node = ast.parse(assertion).body[0].test
            calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == entry]
            if (not isinstance(node, ast.Compare) or len(node.ops) != 1
                    or not isinstance(node.ops[0], ast.Eq) or len(calls) != 1
                    or node.left is not calls[0]):
                continue
        except (SyntaxError, AttributeError, IndexError):
            continue
        call = oracle_b01.call_of(assertion, entry)
        if call is not None:
            by_call.setdefault(call, assertion)
    kept = unseen_inputs(selected, round1, entry)
    missing = sum(r['call'] not in by_call for r in kept)
    return round1 + [by_call.get(r['call'], f"assert {r['call']} == None") for r in kept], missing
