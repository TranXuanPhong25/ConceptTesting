"""Controlled authored cases; evaluator labels never enter Qwen contexts."""
import random


def cases():
    rows=[]
    def add(spec,body,base,critical,*,probe=False,witness=None,expected=None,actual=None,ambiguous=False):
        uid='f'+str(len(rows)+1).zfill(2)
        source='def f('+('xs, limit' if 'limit' in body else 'container, required' if 'required' in body else 'xs')+'):\n    '+repr(spec)+'\n'+''.join('    '+line+'\n' for line in body.splitlines())
        # Generic original-domain filter: exact argument types, not eligibility/fault constraints.
        if 'required' in body:valid='def valid(container, required):\n return type(container) is list and type(required) is list and all(type(v) is int for v in container+required)\n'
        elif 'limit' in body:valid='def valid(xs, limit):\n return type(xs) is list and all(type(v) is int for v in xs) and type(limit) is int\n'
        else:valid='def valid(xs):\n return type(xs) is list and all(type(v) is int for v in xs)\n'
        rows.append(dict(fixture_id=uid,source=source,entry='f',base=base,valid_code=valid,
            evaluator=dict(probe_applicable=probe,ambiguous=ambiguous,critical_items=critical,witness=witness,required_output=expected,actual_output=actual,authority='authored_fixture_expectations; Qwen free-text labels need independent human adjudication')))
    spec='Return a sorted list containing every integer from xs. Preserve the number of occurrences of each value, including duplicates. xs is a list of integers.'
    add(spec,'return sorted(xs)','assert f([2, 1]) == [1, 2]',['preserve duplicate counts','sorting preserves every occurrence'])
    add(spec,'return sorted(set(xs))','assert f([2, 1]) == [1, 2]',['preserve duplicate counts','set collapses duplicates before returned list'],probe=True,witness='([1, 1],)',expected='[1, 1]',actual='[1]')
    spec='Return the number of integers in xs that are greater than or equal to limit. xs is a list of integers and limit is an integer.'
    add(spec,'return sum(1 for x in xs if x >= limit)','assert f([1, 3], 2) == 1',['boundary includes equality','comparison is greater-or-equal'])
    add(spec,'return sum(1 for x in xs if x > limit)','assert f([1, 3], 2) == 1',['boundary includes equality','strict comparison excludes equality'],probe=True,witness='([2], 2)',expected='1',actual='0')
    spec='Return True exactly when every value in required is present in container. Extra values in container are allowed. Both arguments are lists of integers; duplicate values do not affect membership.'
    add(spec,'return set(required) <= set(container)','assert f([1], [1]) is True',['required subset of container','extra container values allowed','implementation uses subset'])
    add(spec,'return set(required) == set(container)','assert f([1], [1]) is True',['required subset of container','implementation requires set equality'],probe=True,witness='([1, 2], [1])',expected='True',actual='False')
    spec='Return the smallest strictly positive integer in xs, or None if no strictly positive integer exists. xs may be any list of integers, including an empty list.'
    add(spec,'ys = [x for x in xs if x > 0]\nreturn min(ys) if ys else None','assert f([-1, 2, 3]) == 2',['domain includes nonpositive/empty lists','positive eligibility','empty eligible group returns None'])
    add(spec,'ys = [x for x in xs if x > 0]\nreturn min(ys)','assert f([-1, 2, 3]) == 2',['domain includes nonpositive/empty lists','min on empty eligible group raises'],probe=True,witness='([0, -1],)',expected='None',actual='exception:ValueError')
    spec='Return True exactly when every integer in xs is even. For an empty list return True. xs is a list of integers.'
    add(spec,'return all(x % 2 == 0 for x in xs)','assert f([2, 4]) is True',['universal quantifier','empty True','all implements every'])
    add(spec,'return any(x % 2 == 0 for x in xs)','assert f([2, 4]) is True',['universal quantifier','any is existential and empty False'],probe=True,witness='([2, 3],)',expected='False',actual='True')
    spec='Return True exactly when the sum of xs is at most limit. xs is any list of integers; no restriction is imposed on its length. limit is an integer.'
    add(spec,'return sum(xs) <= limit','assert f([1], 2) is True',['sum inclusive bound','no length restriction'])
    add(spec,'if len(xs) > 2:\n    return False\nreturn sum(xs) <= limit','assert f([1], 2) is True',['no length restriction','guard returns False for length above2 before sum'],probe=True,witness='([0, 0, 0], 1)',expected='True',actual='False')
    add('Return the first suitable value from xs. xs is a list of integers.','return xs[0] if xs else None','assert f([]) is None',['suitable is undefined','implementation returns first item or None; intended eligibility unknown'],ambiguous=True)
    spec='Return a sorted copy of xs, preserving every duplicate occurrence. xs is a list of integers.'
    add(spec,'temporary = set(xs)\nreturn sorted(xs)','assert f([2, 1]) == [1, 2]',['unused local set loses counts locally','returned sorted original preserves counts'])
    add(spec,'if False:\n    return sorted(set(xs))\nreturn sorted(xs)','assert f([2, 1]) == [1, 2]',['dedup return is unreachable','active return preserves occurrences'])
    add('Return the sum of all strictly positive integers in xs. Exclude zero and negative integers. Include repeated positive occurrences. xs is any list of integers.','return sum(set(x for x in xs if x > 1))','assert f([2]) == 2',['positive1 incorrectly excluded','repeated positive values deduplicated','multiple distinguishable hypotheses'],probe=True,witness='([1, 2, 2],)',expected='5',actual='2')
    assert len(rows)==16 and sum(r['evaluator']['probe_applicable'] for r in rows)==7
    return rows


def order():
    rows=cases();random.Random(20261016).shuffle(rows);return rows
