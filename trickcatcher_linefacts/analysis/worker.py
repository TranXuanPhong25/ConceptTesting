import json, sys, signal, copy, math, ast
job = json.load(open(sys.argv[1]))
class TO(Exception): pass
def al(*a): raise TO()
signal.signal(signal.SIGALRM, al)
def load(src):
    ns = {}; exec(src, ns); return ns[job['entry']]
def run(f, a, s=3):
    signal.alarm(s)
    try: return 'ok', f(*copy.deepcopy(a))
    except TO: return 'timeout', None
    except BaseException as e: return type(e).__name__, None
    finally: signal.alarm(0)
def same(x, y):
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    if num(x) and num(y) and (isinstance(x, float) or isinstance(y, float)):
        return math.isclose(x, y, rel_tol=1e-6, abs_tol=job['atol'] or 1e-6)
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)) and len(x) == len(y):
        return type(x) == type(y) and all(same(a, b) for a, b in zip(x, y))
    return x == y
put, can, con = load(job['put']), load(job['canon']), load(job['contract'])
out = {}
for call in job['calls']:
    try:
        node = ast.parse(call, mode='eval').body
        args = [eval(compile(ast.Expression(a), '<a>', 'eval'), {}) for a in node.args]
        if node.keywords: out[call] = 'args'; continue
    except BaseException:
        out[call] = 'args'; continue
    if run(con, args)[0] != 'ok': out[call] = 'invalid'; continue
    cs, cv = run(can, args)
    if cs != 'ok': out[call] = 'canon_err'; continue
    ps, pv = run(put, args)
    out[call] = 'reveal' if (ps != 'ok' or not same(cv, pv)) else 'same'
json.dump(out, open(sys.argv[2], 'w'))
