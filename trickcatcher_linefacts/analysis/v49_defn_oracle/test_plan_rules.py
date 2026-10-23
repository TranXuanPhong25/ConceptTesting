"""Synthetic checks for plan_rules.py (no records, no references)."""
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v49_defn_oracle import plan_rules as P


def ok(value):
    return ['ok', repr(value)]


def v(raw):
    return O.E.iorel.value(raw)


def test_exposing_uses_official_where_computed_else_proxy():
    assert P.exposing(dict(exposing=False, valid=True, ref=v(ok(1))), v(ok(0))) is False
    assert P.exposing(dict(exposing=None, valid=True, ref=v(ok(1))), v(ok(0))) is True
    assert P.exposing(dict(exposing=None, valid=False, ref=v(ok(1))), v(ok(0))) is False
    assert P.exposing(dict(exposing=None, valid=True, ref=v(ok(0))), v(ok(0))) is False


def record(outs_by_input, valid=('0', '1', '2')):
    return dict(families=dict(defn=dict(valid_programs=list(valid))),
                inputs={lit: dict(put=ok(0), programs=dict(defn=dict(zip(valid, outs)))) for lit, outs in outs_by_input.items()})


def test_task_view_classes_and_fa_split():
    rec = record({'(1,)': [ok(0), ok(0), ok(0)],          # exposing, all equal PUT: common-mode
                  '(2,)': [ok(0), ['timeout'], ['timeout']],  # exposing, one finisher equals PUT: abstention, not common
                  '(3,)': [ok(1), ok(1), ok(0)]})          # PUT right: majority emits a wrong test
    truth = {'(1,)': dict(exposing=None, valid=True, ref=v(ok(5))),
             '(2,)': dict(exposing=None, valid=True, ref=v(ok(5))),
             '(3,)': dict(exposing=None, valid=True, ref=v(ok(0)))}
    labels = {lit: {'primary': 'fa'} for lit in truth}
    d, tests = P.task_view(rec, truth, labels)
    assert d['exposing_classes'] == {'common_mode': 1, 'variants_failed': 1}
    assert d['primary'] == 'b_common_mode' and tests == 1 and d['fa_split']['capped'] == {'put_right': 1}


def v49(verdict='NO-GO', margin=False, span=False, fa_ok=True, sec='NO-GO', vs_tc='NO-GO', attribution='no_defn_only_wins'):
    primary = dict(verdict=verdict, checks=dict(confirmed_task_margin=margin, extra_problem_span=span, fa_no_worse=fa_ok))
    return dict(summary=dict(concept_attribution=attribution, decision=dict(
        primary=primary, secondary=dict(verdict=sec), defn_vs_tc=dict(verdict=vs_tc))))


def task(pid, primary, valid=5, fa=None, tests=0, resource_only=0):
    return dict(problem_id=pid, valid=valid, resource_only=resource_only, primary=primary, fa_split=fa or {}, tests=tests)


def test_r1_waits_for_the_manual_audit():
    out = P.rules(v49('GO', True, True, attribution='pending_manual_audit'), {'1': task('p1', 'confirmed')})
    assert out['fired'] == 'R1' and out['status'] == 'pending_manual_audit'


def test_near_go_fa_failure_and_family_effect_precede_closing():
    tasks = {str(i): task(f'p{i}', 'confirmed') for i in range(12)}
    assert P.rules(v49(margin=True, span=True, fa_ok=False), tasks)['fired'] == 'R1b'
    assert P.rules(v49(sec='GO'), tasks)['fired'] == 'R6'
    assert P.rules(v49(vs_tc='GO'), tasks)['fired'] == 'R6'


def test_r3_capability_counts_problems_and_resource_only_rejections():
    tasks = {str(i): task(f'p{i % 11}', 'confirmed') for i in range(30)}  # 11 problems < 12
    assert P.rules(v49(), tasks)['fired'] == 'R3'
    tasks['99'] = task('p99', 'b2_variants_failed', valid=0, resource_only=2)  # slow but writable: capable
    assert P.rules(v49(), tasks)['why']['R3']['capable_problems'] == 12


def test_r3_wrong_value_share_ignores_invalid_and_unresolved_tests():
    fa = dict(invalid_input=50, unresolved_output=5, put_right=2)
    tasks = {str(i): task(f'p{i}', 'confirmed', fa=fa, tests=60) for i in range(12)}  # 3 confirmed per task
    out = P.rules(v49(), tasks)
    assert out['why']['R3']['wrong_value_share_valid_resolved'] == 0.4 and out['fired'] == 'R5'


def test_plurality_needs_three_problems_and_breaks_ties_by_order():
    tasks = {str(i): task(f'p{i}', 'confirmed') for i in range(12)}
    tasks.update({'20': task('q1', 'b_common_mode'), '21': task('q1', 'b_common_mode'), '22': task('q1', 'b_common_mode')})
    assert P.rules(v49(), tasks)['fired'] is None  # three tasks but one problem
    tasks.update({'30': task('r1', 'b2_variants_failed'), '31': task('r2', 'b2_variants_failed'),
                  '32': task('r3', 'b2_variants_failed'), '33': task('r4', 'b_common_mode'), '34': task('r5', 'b_common_mode')})
    out = P.rules(v49(), tasks)
    assert out['plurality'] == 'R4' and out['fired'] == 'R4'  # R4 has 5 tasks on 3 problems vs R2 3 tasks
    tasks['35'] = task('r6', 'b2_variants_failed'); tasks['36'] = task('r7', 'b2_variants_failed')
    assert P.rules(v49(), tasks)['fired'] == 'R2'  # 5 vs 5: R2 wins the fixed tie-break
