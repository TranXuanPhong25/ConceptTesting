"""Bounded tool dispatcher for model-chosen or fixed-schedule structural/replay queries.

Actions are structured JSON (no native function calling, shell or evaluator). Every action, valid or not, consumes one
slot and is logged with its typed result and hypothesis link. Logs are append-only: resuming replays the logged
results and rejects any drift. Tools report evidence inside their scope; spec interpretation stays unverified.
"""
import copy
import hashlib
import json
from pathlib import Path
from . import flow_cfg, flow_trace, tool_contract
from .chain_inputs import parse_arguments, parse_literal, literal_for_transport
from .chain_protocol import fingerprint
from .gen_inputs import sandbox
from .llm_client import atomic_json
from .paths import CONFIG
from .prompt_aliases import maps

F = CONFIG['flowtools']
HERE = Path(__file__).resolve().parent
TOOLS = {name: set(schema['properties']) for name, schema in tool_contract.SCHEMAS.items()}


def parse_call(text, arity):
    """Arm-neutral transport normalization of a positional argument literal, applied identically everywhere.

    Accepted in order: a full tuple of the right arity; for a one-parameter function, any literal value wrapped as
    (value,); a comma-separated argument list without parentheses, wrapped in parentheses. Otherwise rejected.
    """
    try:
        return parse_arguments(text, arity)
    except ValueError as first:
        if type(text) is not str:
            raise
        attempts = []
        if arity['positional'] == 1 and not arity['varargs']:
            attempts.append(lambda: literal_for_transport((parse_literal(text),)))
        attempts.append(lambda: '(' + text + ',)' if not text.rstrip().endswith(',') else '(' + text + ')')
        for make in attempts:
            try:
                return parse_arguments(make(), arity)
            except (ValueError, TypeError, RecursionError):
                continue
        raise first


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class ToolError(Exception):
    pass


def worker_limits():
    return dict(max_events=F['max_events'], max_names=F['max_names'], snapshot_bytes=F['snapshot_bytes'],
                max_output_bytes=CONFIG['chain']['max_output_bytes'], worker_timeout=F['worker_timeout'],
                address_space_bytes=F['address_space_mib'] * 1024 * 1024)


def native_checked(ordinary, traced):
    keys = ('status', 'exception_type', 'exception_module', 'output_capture', 'output_signature', 'input_before', 'input_after', 'output_aliases')
    ok = ordinary.get('status') in ('ok', 'exception') and all(ordinary.get(k) == traced.get(k) for k in keys)
    ok = ok and ordinary.get('input_before') is not None and ordinary.get('input_after') is not None
    if ordinary.get('status') == 'ok' and (ordinary.get('output_capture') != 'literal' or ordinary.get('output_signature') is None):
        ok = False
    return ok


class Executor:
    """Ordinary + traced isolated processes per request; immutable on-disk records shared across arms of one task."""

    def __init__(self, task, directory):
        self.task, self.root = task, Path(directory)
        self.physical = 0
        self.cache_hits = 0

    def run(self, literal, snapshot_lines=(), names=()):
        results = {}
        for mode in ('ordinary', 'traced'):
            job = dict(source=self.task['source_original'], entry=self.task['entry'], input_repr=literal, mode=mode,
                       valid_code=self.task.get('valid_code'), limits=worker_limits())
            if mode == 'traced':
                job.update(snapshot_lines=sorted(set(snapshot_lines)), snapshot_names=list(names))
            key = sha(dict(job=job, protocol=fingerprint()))
            root = self.root / key
            jp, op = root / 'job.json', root / 'result.json'
            if op.exists():
                if json.loads(jp.read_text()) != job:
                    raise ValueError('execution_cache_drift')
                self.cache_hits += 1
                results[mode] = json.loads(op.read_text())
                continue
            atomic_json(jp, job)
            self.physical += 1
            try:
                results[mode] = sandbox(CONFIG['V4_PYTHON'], HERE / 'flow_worker.py', jp, op, F['outer_timeout'])
            except RuntimeError:
                results[mode] = dict(status='unresolved', reason='isolated_worker_failed', events=[])
                atomic_json(op, results[mode])
        return results['ordinary'], results['traced']


class FlowSession:
    def __init__(self, task, directory, *, arm, executor=None):
        self.task = copy.deepcopy(task)
        self.arm = arm
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cfg = flow_cfg.build(self.task)
        forward, _ = maps(self.task, {})
        forward.update({e['id']: e['id'] for e in self.cfg['edges']})
        # Statement nodes alone on their header line get a line alias (L<n>), easier for small models.
        starts = {}
        for n, rec in self.cfg['nodes'].items():
            starts.setdefault(rec['header_lines'][0], []).append(n)
        for line, ids in starts.items():
            if len(ids) == 1:
                forward[ids[0]] = f'L{line}'
        self.forward = forward
        self.back = {v: k for k, v in forward.items()}
        self.executor = executor or Executor(self.task, self.directory.parent / 'executions')
        self.context = dict(task_hash=self.task['task_hash'], arm=arm, flowtools=F, protocol=fingerprint())
        self.path = self.directory / 'ledger.json'
        if self.path.exists():
            saved = json.loads(self.path.read_text())
            if saved['context'] != self.context:
                raise ValueError('ledger_context_drift')
            self.log = saved['events']
        else:
            self.log = []
        self.cursor = 0
        self.round = 0
        self.actions_in_round = 0
        self.actions = 0
        self.executions = 0
        self.common_executions = 0
        self.finals = 0
        self.traces = {}

    # ---- immutable append-only log -------------------------------------------------------------------------
    def _event(self, kind, request, compute):
        if self.cursor < len(self.log):
            logged = self.log[self.cursor]
            if logged['type'] != kind or logged['request'] != request:
                raise ValueError('ledger_replay_drift')
            self.cursor += 1
            result = logged['result']
        else:
            result = compute()
            self.log.append(dict(type=kind, request=request, result=result))
            self.cursor += 1
            atomic_json(self.path, dict(context=self.context, events=self.log))
        for key, value in result.get('charges', {}).items():
            setattr(self, key, getattr(self, key) + value)
        if result.get('internal', {}).get('trace_id'):
            self.traces[result['internal']['trace_id']] = result['internal']
        return result

    def begin_round(self):
        if self.round >= F['rounds']:
            raise ValueError('round_budget')
        self._event('round', dict(number=self.round + 1), lambda: dict(started=self.round + 1))
        self.round += 1
        self.actions_in_round = 0

    # ---- id handling ------------------------------------------------------------------------------------------
    def resolve(self, value):
        if type(value) is int and not isinstance(value, bool):
            value = f'L{value}'
        if type(value) is not str:
            raise ToolError('id_shape')
        if value in flow_cfg.SYNTHETIC:
            return value
        full = self.back.get(value, value)
        if full in self.cfg['nodes'] or full in {e['id'] for e in self.cfg['edges']}:
            return full
        if full in self.forward:
            raise ToolError('not_a_cfg_statement')
        raise ToolError('unknown_id')

    def alias(self, obj):
        if isinstance(obj, str):
            return self.forward.get(obj, obj)
        if isinstance(obj, list):
            return [self.alias(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.alias(v) for k, v in obj.items() if k not in ('internal', 'charges')}
        return obj

    # ---- model/fixed actions ----------------------------------------------------------------------------------
    def act(self, action):
        """One API invocation; invalid calls consume the slot and return a typed error."""
        if self.round == 0:
            raise ValueError('begin_round_first')
        if self.actions_in_round >= F['actions_per_round'] or self.actions >= F['max_actions']:
            return dict(status='refused', error='action_budget_exhausted',
                        error_details=dict(code='action_budget_exhausted', round=self.round,
                                           max_actions=F['max_actions'], actions_per_round=F['actions_per_round']))
        self.actions_in_round += 1
        self.actions += 1
        number = self.actions
        action = tool_contract.logged_action(action)
        request = dict(number=number, round=self.round, action=action)
        result = self._event('action', request, lambda: self._dispatch(action, number))
        return result

    def _dispatch(self, action, number):
        hypothesis = None
        self._charge = {}
        try:
            if isinstance(action, str):
                if len(action) > F['max_action_chars']:
                    raise ToolError('action_too_long')
                try:
                    action = json.loads(action)
                except (json.JSONDecodeError, RecursionError):
                    raise ToolError('action_not_json') from None
            if type(action) is not dict:
                raise ToolError('action_shape')
            if tool_contract.logged_action(action) is not action:
                raise ToolError('action_serialization')
            try:
                action_size = len(json.dumps(action, ensure_ascii=False))
            except (ValueError, TypeError, RecursionError, OverflowError):
                raise ToolError('action_serialization') from None
            if action_size > F['max_action_chars']:
                raise ToolError('action_too_long')
            tool = action.get('tool')
            if type(tool) is not str or tool not in TOOLS:
                raise ToolError('unknown_tool')
            extra = set(action) - TOOLS[tool]
            if extra:
                raise ToolError('unknown_field')
            hypothesis = action.get('hypothesis')
            if hypothesis is not None and type(hypothesis) is not str:
                raise ToolError('hypothesis_shape')
            # Preserve v21: recognizable replay reserves an execution slot before ids/names/input checks.
            # Generic unknown-key/tool/hypothesis failures above do not reserve an execution slot.
            if tool == 'replay_input':
                if self.executions >= F['max_execution_requests']:
                    raise ToolError('execution_budget_exhausted')
                self._charge = dict(executions=1)
            tool_contract.validate(action)
            body = getattr(self, '_' + tool)(action, number)
            return dict(status='ok', tool=tool, hypothesis=hypothesis, charges=self._charge, **body)
        except tool_contract.ActionError as exc:
            return dict(status='error', error=str(exc), hypothesis=hypothesis if type(hypothesis) is str and len(hypothesis) <= 64 else None, charges=self._charge,
                        error_details=tool_contract.error_details(str(exc), action, number, self.round, exc.details))
        except ToolError as exc:
            return dict(status='error', error=str(exc), hypothesis=hypothesis if type(hypothesis) is str and len(hypothesis) <= 64 else None, charges=self._charge,
                        error_details=tool_contract.error_details(str(exc), action if isinstance(action, dict) else {}, number, self.round))

    def _ids(self, action, field='ids', required=True, cap=None):
        ids = action.get(field)
        if (ids is None or ids == []) and not required:
            return []
        if type(ids) is not list or not ids or len(ids) > (cap or F['max_names']):
            raise ToolError(field + '_shape_or_count')
        return [self.resolve(x) for x in ids]

    def _require_cfg(self):
        if not self.cfg['supported']:
            raise ToolError('cfg_unsupported:' + ','.join(self.cfg['unsupported']))

    def _header(self, node):
        lo, hi = node['header_lines']
        text = '\n'.join(self.task['source_masked'].split('\n')[lo - 1:hi]).strip()
        return text[:160] + ('...' if len(text) > 160 else '')

    def _inspect_flow(self, action, number):
        self._require_cfg()
        ids = [x for x in self._ids(action) if x in self.cfg['nodes'] or x in flow_cfg.SYNTHETIC]
        radius = action.get('radius', 1)
        if type(radius) is not int or not 0 <= radius <= 3:
            raise ToolError('radius_range')
        keep, omitted = flow_cfg.neighborhood(self.cfg, ids, radius, F['max_nodes'])
        cd = self.cfg['control_dependence']
        nodes = []
        for n in keep:
            if n in flow_cfg.SYNTHETIC:
                nodes.append(dict(id=n, kind='synthetic'))
                continue
            rec = self.cfg['nodes'][n]
            nodes.append(dict(id=n, kind=rec['kind'], lines=rec['header_lines'], code=self._header(rec), reachable=rec['reachable'],
                              limits=rec['limits'], control_dependence=cd.get(n, []) if cd is not None else 'unknown'))
        kept = set(keep)
        edges = [dict(e) for e in self.cfg['edges'] if e['source'] in kept and e['target'] in kept]
        return dict(nodes=nodes, edges=edges, omitted_nodes=omitted, control_dependence_scope=self.cfg['control_dependence_scope'],
                    scope='structural_normal_flow_only; enclosing guards are not complete semantics')

    def _inspect_data(self, action, number):
        self._require_cfg()
        ids = [x for x in self._ids(action, required=False) if x in self.cfg['nodes']]
        names = action.get('names') or []
        if type(names) is not list or len(names) > F['max_names'] or any(type(x) is not str or len(x) > 64 for x in names):
            raise ToolError('names_shape_or_count')
        if not ids and not names:
            raise ToolError('ids_or_names_required')
        facts = [dict(id=n, **self.cfg['nodes'][n]['data']) for n in ids]
        by_name = []
        for name in names:
            reads = [n for n, r in self.cfg['nodes'].items() if name in r['data']['reads']]
            writes = [n for n, r in self.cfg['nodes'].items() if name in r['data']['writes']]
            heap = [n for n, r in self.cfg['nodes'].items() if name in r['data']['heap_writes_through']]
            by_name.append(dict(name=name, parameter=name in self.cfg['parameters'], read_at=reads, written_at=writes,
                                heap_written_through_at=heap, provenance='static_syntactic'))
        return dict(statements=facts, names=by_name, reaching_definitions='unknown', observed_def_use='use replay_input snapshots')

    def _execute(self, literal, ids, names, prefix):
        lines = [self.cfg['nodes'][n]['header_lines'][0] for n in ids if n in self.cfg['nodes']]
        ordinary, traced = self.executor.run(literal, lines if names else (), names)
        checked = native_checked(ordinary, traced)
        projection = flow_trace.project(self.cfg, traced) if checked else dict(status='unknown', reason='execution_not_verified', invocations=[])
        trace_id = f'{prefix}{len(self.traces) + 1}'
        domain = ordinary.get('status') if ordinary.get('status') in ('filtered', 'unresolved') else 'accepted'
        reach = [dict(id=n, **{('reach' if k == 'status' else k): v for k, v in flow_trace.reached(projection, n).items()}) for n in ids]
        snaps = []
        for s in traced.get('snapshots', []) if checked else []:
            cands = self.cfg['line_candidates'].get(s['line'], []) if self.cfg['supported'] else []
            snaps.append(dict(id=cands[0] if len(cands) == 1 else None, inv=s['inv'], kind=s['kind'], values=s['values'],
                              mapping='unique_line' if len(cands) == 1 else 'ambiguous_or_unmapped_line'))
        omitted_snaps = max(0, len(snaps) - 8)
        visible = dict(trace=trace_id, input=literal, domain_filter=domain,
                       validity_provenance=ordinary.get('validity_provenance', 'no_filter'),
                       execution_status=ordinary.get('status'), exception_type=ordinary.get('exception_type'),
                       output=ordinary.get('output_repr'), output_capture=ordinary.get('output_capture'),
                       native_checked=checked, output_provenance='observed_PUT_output_not_expected_oracle',
                       reach=reach, edges_covered=flow_trace.covered_edges(projection)[:F['max_nodes']],
                       trace_summary=flow_trace.summary(projection, self.forward, F['summary_events']),
                       trace_complete=projection.get('trace_complete', False), all_invocations_proven=projection.get('all_invocations_proven', False),
                       snapshots=snaps[:8], omitted_snapshots=omitted_snaps)
        return visible, dict(trace_id=trace_id, projection=projection, input=literal)

    def _replay_input(self, action, number):
        if self.executions >= F['max_execution_requests']:
            raise ToolError('execution_budget_exhausted')
        self._charge = dict(executions=1)  # invalid or duplicate inputs still consume the execution slot
        ids = self._ids(action, required=False)
        names = action.get('names') or []
        if type(names) is not list or len(names) > F['max_names'] or any(type(x) is not str or len(x) > 64 for x in names):
            raise ToolError('names_shape_or_count')
        try:
            literal = literal_for_transport(parse_call(action.get('input'), self.task['arity']))
        except (ValueError, TypeError, RecursionError) as exc:
            raise ToolError('input:' + str(exc)) from None
        visible, internal = self._execute(literal, ids, names, 'T')
        return dict(visible, internal=internal)

    def _check_path(self, action, number):
        self._require_cfg()
        trace = self.traces.get(action.get('trace'))
        if trace is None:
            raise ToolError('unknown_trace')
        sequence = action.get('sequence')
        if type(sequence) is not list or not sequence or len(sequence) > 64:
            raise ToolError('sequence_shape')
        result = flow_trace.check_path(self.cfg, trace['projection'], [self.resolve(x) for x in sequence])
        if result['status'] == 'invalid':
            raise ToolError('path:' + result['error'])
        return dict(trace=action['trace'], path=result.pop('status'), **result)

    # ---- shared discovery and final inputs (no model revision) ------------------------------------------------
    def discover(self, witnesses):
        """Frozen common witnesses, replayed once per task; cost reported separately from arm budgets."""
        if len(witnesses) > F['common_inputs']:
            raise ValueError('common_input_budget')
        out = []
        for literal in witnesses:
            def compute(literal=literal):
                charges = dict(common_executions=1)
                try:
                    lit = literal_for_transport(parse_call(literal, self.task['arity']))
                except (ValueError, TypeError, RecursionError) as exc:
                    return dict(status='error', error='input:' + str(exc), charges=charges)
                visible, internal = self._execute(lit, [], [], 'C')
                return dict(status='ok', provenance='frozen_parent_fuzz_witness', charges=charges, **visible, internal=internal)
            out.append(self._event('common', dict(input=literal), compute))
        return [self.alias(x) for x in out]

    def final_inputs(self, inputs):
        unique = list(dict.fromkeys(inputs))
        if len(unique) > F['final_inputs']:
            raise ValueError('final_input_budget')
        out = []
        for literal in unique:
            def compute(literal=literal):
                if self.executions >= F['max_execution_requests']:
                    return dict(status='refused', error='execution_budget_exhausted')
                charges = dict(executions=1, finals=1)
                try:
                    lit = literal_for_transport(parse_call(literal, self.task['arity']))
                except (ValueError, TypeError, RecursionError) as exc:
                    return dict(status='error', error='input:' + str(exc), charges=charges)
                visible, internal = self._execute(lit, [], [], 'F')
                return dict(status='ok', provenance='final_stage_no_model_revision', charges=charges, **visible, internal=internal)
            out.append(self._event('final', dict(input=literal), compute))
        return [self.alias(x) for x in out]

    def adopt(self, traces):
        """Make shared common-discovery traces (C*) addressable by check_path without re-running them."""
        for key, value in traces.items():
            if key.startswith('C'):
                self.traces.setdefault(key, value)

    def view(self, result):
        return self.alias(result)

    def report(self):
        return dict(arm=self.arm, rounds=self.round, actions=self.actions, execution_requests=self.executions, final_inputs=self.finals,
                    common_executions=self.common_executions, physical_processes=self.executor.physical, cache_hits=self.executor.cache_hits,
                    errors=sum(1 for e in self.log if e['type'] == 'action' and e['result'].get('status') != 'ok'),
                    cfg_supported=self.cfg['supported'], unsupported=self.cfg['unsupported'], model_calls=0)


def fixed_schedule(hypotheses, proposals, round_number):
    """Predeclared query schedule independent of model tool choice: same caps, deterministic order."""
    top = [h for h in hypotheses if h.get('source_ids')][:2]
    actions = []
    for h in top:
        if round_number == 1:
            actions.append(dict(tool='inspect_flow', ids=h['source_ids'][:F['max_names']], radius=1, hypothesis=h['id']))
        else:
            actions.append(dict(tool='inspect_data', ids=h['source_ids'][:F['max_names']], hypothesis=h['id']))
    ids = list(dict.fromkeys(i for h in top for i in h['source_ids']))[:F['max_names']]
    for literal in proposals:
        if len(actions) >= F['actions_per_round']:
            break
        actions.append(dict(tool='replay_input', input=literal, ids=ids, hypothesis=top[0]['id'] if top else None))
    return actions
