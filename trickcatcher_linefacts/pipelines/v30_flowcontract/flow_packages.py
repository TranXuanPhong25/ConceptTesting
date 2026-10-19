"""Arm guidance packages built from frozen artifacts; every item carries provenance, nothing is reranked by evidence.

Model-authored hypotheses keep their rank, references, alternatives and uncertainty. Tool evidence is attached, never
used to filter or reorder. concept+hyp carries no concrete witness/trace/output values.
"""
import copy
import json
from .flow_trace import reached
from . import tool_contract

ARMS = ('concept+hyp', 'input+hyp', 'concept+input+hyp', 'agent-tools', 'fixed-tools', 'flow+input', 'toolinput', 'plain',
        'placebo+input', 'witness-only')
LLM_ARMS = ARMS[:-1]
PARTS = {
    'concept+hyp': {'concepts', 'hypotheses', 'structure'},
    'input+hyp': {'hypotheses', 'structure', 'inputs', 'traces'},
    'concept+input+hyp': {'concepts', 'hypotheses', 'structure', 'inputs', 'traces'},
    'agent-tools': {'concepts', 'hypotheses', 'structure', 'inputs', 'traces', 'tools'},
    'fixed-tools': {'concepts', 'hypotheses', 'structure', 'inputs', 'traces', 'tool_feedback_fixed'},
    'flow+input': {'structure', 'inputs', 'traces'},
    'toolinput': {'inputs'},
    'plain': set(),
    'placebo+input': {'placebo', 'inputs'},
}
HYP_FIELDS = ('statement', 'required_relation', 'actual_relation', 'source_ids', 'obligation_ids', 'condition', 'effect', 'alternative',
              'uncertainty')
TOOL_PROTOCOL = tool_contract.protocol()


def structural_evidence(session, ids):
    """Static facts for referenced statements only (same IDs for hypothesis and flow arms)."""
    cfg = session.cfg
    if not cfg['supported']:
        return dict(status='unsupported', reasons=cfg['unsupported'])
    cd = cfg['control_dependence']
    rows = []
    for n in ids:
        if n not in cfg['nodes']:
            continue
        rec = cfg['nodes'][n]
        rows.append(dict(id=n, kind=rec['kind'], code=session._header(rec), reachable=rec['reachable'], limits=rec['limits'],
                         control_dependence=cd.get(n, []) if cd is not None else 'unknown', data=rec['data'],
                         provenance='static_structural'))
    return dict(status='ok', statements=rows, control_dependence_scope=cfg['control_dependence_scope'])


def referenced_ids(hypotheses):
    return list(dict.fromkeys(i for h in hypotheses for i in h.get('source_ids', [])))


def build(arm, session, *, concepts, hypotheses, witnesses, placebo=None, fixed_feedback=None):
    """concepts: S1 items; hypotheses: S3 items in model rank; witnesses: session.discover(...) views."""
    if arm not in ARMS:
        raise ValueError('unknown_arm')
    if arm == 'witness-only':
        return None
    parts = PARTS[arm]
    hyps = [dict({k: copy.deepcopy(h.get(k)) for k in HYP_FIELDS if h.get(k) is not None}, id=h['id'], rank=i + 1, provenance='model_authored_unverified')
            for i, h in enumerate(hypotheses)]
    package = dict(arm=arm, sections={})
    sec = package['sections']
    if 'concepts' in parts:
        linked = {o for h in hypotheses for o in h.get('obligation_ids', [])}
        sec['concepts'] = [dict({k: c.get(k) for k in ('statement', 'relation', 'domain', 'quote', 'uncertainty') if c.get(k) is not None},
                                id=c['id'], provenance='model_authored_from_spec') for c in concepts if c['id'] in linked]
    if 'hypotheses' in parts:
        sec['hypotheses'] = hyps
    if 'structure' in parts:
        sec['structure'] = structural_evidence(session, referenced_ids(hypotheses))
    if 'inputs' in parts:
        sec['inputs'] = [dict(trace=w.get('trace'), input=w.get('input'), domain_filter=w.get('domain_filter'), execution_status=w.get('execution_status'),
                              exception_type=w.get('exception_type'), output=w.get('output'), output_provenance='observed_PUT_output_not_expected_oracle',
                              provenance='frozen_parent_fuzz_witness') for w in witnesses if w.get('status') == 'ok']
    if 'traces' in parts:
        ids = referenced_ids(hypotheses) or list(session.cfg['nodes'])[:8]
        sec['traces'] = []
        for w in witnesses:
            if w.get('status') != 'ok':
                continue
            internal = session.traces.get(w['trace'])
            reach = [dict(id=n, reach=reached(internal['projection'], n)['status']) for n in ids] if internal else []
            sec['traces'].append(dict(trace=w['trace'], summary=w.get('trace_summary'), reach=reach, provenance='tool_observed'))
    if 'placebo' in parts:
        sec['placebo'] = [dict(p, provenance='truthful_base_covered_fact') for p in (placebo or [])]
    if 'tools' in parts:
        sec['tools'] = TOOL_PROTOCOL
    if 'tool_feedback_fixed' in parts:
        sec['tool_feedback'] = dict(schedule='predeclared_fixed', results=fixed_feedback or [])
    return session.alias(package)


def render(package):
    if package is None:
        return None
    header = ('Guidance package (' + package['arm'] + '). Items marked model_authored are unverified claims; '
              'tool_observed items hold only within their scope.')
    return header + '\n' + json.dumps(package['sections'], ensure_ascii=False, indent=1)
