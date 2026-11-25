"""Adaptive concept discovery with bounded, domain-checked coverage feedback."""
import ast
import copy
import time
from dataclasses import asdict, dataclass
from functools import wraps

from .base import InputGenerationMethod
from ..call_builder import CallBuilder, input_identity
from ..control_flow.analysis import analyze, hit
from ..control_flow.prompts import INSTRUCTION, messages
from ..control_flow.schema import parse_response
from ..control_flow.tool_inputs import (
    DEFAULT_MAX_PRIOR_INPUTS,
    DEFAULT_MAX_PROMPT_PRIOR_INPUTS,
    FOUR_TOOLS,
    compact_prompt_prior_inputs,
    default_tool_runs_dir,
    is_sandbox_infrastructure_error,
    load_four_tool_prior_inputs,
)
from ..input_prompts import compact_source
from ..response_json import load_response_json
from final.src.runtime.artifacts import digest
from final.src.runtime.execution import ExecutionError, execute


HYPOTHESIS_INPUT_LIMIT = 40
SUITE_TARGET_OFFSET = 10


def _measure_generation_time(discover):
    @wraps(discover)
    def measured(self, context):
        started = time.monotonic()
        result = discover(self, context)
        result["generation_seconds"] = time.monotonic() - started
        return result

    return measured


def _round_log(round_index, family, targets, *, errors, repairs, sampling,
               concept_checks, ledger_rows, llm_count, sampled_count):
    return {
        "round": round_index,  # Vị trí trong plan, đếm từ 0.
        "target_family": family,  # Nhóm CFG.
        "target_ids": [target['id'] for target in targets],  # ID gửi trong prompt.
        "errors": errors,  # Lỗi response của riêng round này.
        "response_repairs": repairs,  # Các sửa chữa khi đọc JSON.
        "sampling": sampling,  # Receipt lấy mẫu và số draw của Hypothesis.
        "concept_checks": concept_checks,  # Predicate và hit của từng concept.
        "candidate_count": llm_count + sampled_count,  # Số input đưa vào hàng chờ.
        "llm_candidate_count": llm_count,
        "sampled_candidate_count": sampled_count,
        "candidate_ledger": ledger_rows,  # Gồm cả record bị loại.
    }


@dataclass(frozen=True)
class ControlFlowSettings:
    rounds: int = 2
    target_limit: int = 6
    draws_per_concept: int = 32
    candidate_limit: int = 64
    sampling_seconds: float = 2

    def __post_init__(self):
        for name, upper in (('rounds', 3), ('target_limit', 6), ('draws_per_concept', 128), ('candidate_limit', 128)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError('Invalid control-flow budget: ' + name)
        if type(self.sampling_seconds) not in (int, float) or not 0 < self.sampling_seconds <= 10:
            raise ValueError('Invalid sampling_seconds')


class ControlFlowArm(InputGenerationMethod):
    name = 'control_flow'
    uses_shared_prompt = False
    default_input_tokens = 4096
    instruction = INSTRUCTION

    max_prompt_prior_inputs = DEFAULT_MAX_PROMPT_PRIOR_INPUTS

    def __init__(self, settings=None, *, max_prompt_prior_inputs=DEFAULT_MAX_PROMPT_PRIOR_INPUTS):
        self.settings = settings or ControlFlowSettings()
        self.max_prompt_prior_inputs = max_prompt_prior_inputs

    def configuration(self):
        return {
            "budgets": asdict(self.settings),
            "suite_input_budget": f"max(input_budget, {SUITE_TARGET_OFFSET} + selected_targets)",
            "instruction": self.instruction,
            "tool_input_limits": {"hypothesis": HYPOTHESIS_INPUT_LIMIT},
            "trace_timeout_cap_seconds": 1,
            "baseline_call_limit": 300,
        }

    def runtime_dependencies(self):
        return ('coverage', 'hypothesis', 'pydantic')

    def build_guidance(self, packet):
        return self.instruction

    def run(self, context):
        return context.artifacts.load_or_compute(
            f"{context.task_directory}/{self.name}/generation.json",
            lambda: self.discover(context),
        )

    @staticmethod
    def trace(context, program, records):
        observations = []
        for record in records:
            result = execute(
                {
                    "mode": "control_flow",
                    "source": program["code"],
                    "entry": context.task["entry_point"],
                    "context": context.task["prompt"],
                    "contract": context.metadata.get("contract", ""),
                    "tests": [record],
                    "timeout": min(context.extensions.get("trace_timeout_cap", 1), context.settings.timeout_seconds),
                    "seed": context.settings.input_seed,
                }
            )
            observations.extend(result['tests'])
        return observations

    def trace_prior(self, context, program, records, *, chunk_size=16):
        """Batch prior-stage traces with binary-split fallback; respects monkeypatched trace()."""
        if not records:
            return []
        if "trace" in self.__dict__ or type(self).trace is not ControlFlowArm.trace:
            return self.trace(context, program, records)

        def run_chunk(chunk):
            if len(chunk) == 1:
                try:
                    return self.trace(context, program, chunk)
                except ExecutionError as error:
                    if is_sandbox_infrastructure_error(error):
                        raise
                    return [{"domain": "unknown", "status": "error", "exception": "SandboxCrash"}]
            try:
                result = execute(
                    {
                        "mode": "control_flow",
                        "source": program["code"],
                        "entry": context.task["entry_point"],
                        "context": context.task["prompt"],
                        "contract": context.metadata.get("contract", ""),
                        "tests": chunk,
                        "timeout": min(context.extensions.get("trace_timeout_cap", 1), context.settings.timeout_seconds),
                        "seed": context.settings.input_seed,
                    }
                )
                tests = result.get("tests")
                if not isinstance(tests, list) or len(tests) != len(chunk):
                    raise ExecutionError("Malformed control_flow trace batch")
                return tests
            except ExecutionError as error:
                if is_sandbox_infrastructure_error(error):
                    raise
                mid = len(chunk) // 2
                return run_chunk(chunk[:mid]) + run_chunk(chunk[mid:])

        observations = []
        for offset in range(0, len(records), chunk_size):
            observations.extend(run_chunk(records[offset : offset + chunk_size]))
        return observations

    def _prompt_prior_context(self, context, prior_inputs):
        if prior_inputs is None:
            return None, None
        explicit_summary = context.extensions.get("prior_stage_summary")
        if explicit_summary is None and len(prior_inputs) <= self.max_prompt_prior_inputs:
            return prior_inputs, None
        compact, auto_summary = compact_prompt_prior_inputs(
            prior_inputs, limit=self.max_prompt_prior_inputs,
        )
        return compact, explicit_summary or auto_summary

    @_measure_generation_time
    def discover(self, context):
        # Tìm target chưa phủ của một task, sinh và trace candidate, rồi chọn bộ input trả về cho oracle chung.
        # Cần cả client gọi model và packet đã chọn PUT để dựng prompt.
        if context.calls is None or context.packet is None:
            raise RuntimeError('Control-flow discovery requires prepared context and model calls')
        # Dùng chữ ký của task để kiểm tra và chuyển input có tên thành args/kwargs.
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        # Input kế thừa từ các stage trước. None là luồng chạy không có stage trước.
        prior_inputs = context.extensions.get('prior_stage_inputs')
        prompt_prior_inputs, prior_stage_summary = self._prompt_prior_context(context, prior_inputs)
        programs = [
            # Analysis có thể cập nhật base coverage, nên sửa trên bản sao của PUT.
            copy.deepcopy(program)
            for program in context.cohort_task["programs"]
            # ControlFlow tự chia prompt từ toàn bộ PUT đã pass base tests.
            if program["base"]["status"] == "pass"
        ]
        # Phân tích coverage từng PUT và thu lỗi analysis riêng để lưu vào artifact.
        analyses, analysis_errors = self._analyze_programs(context, programs, prior_inputs)
        # Lần lượt là target đã xếp batch, ID target không vừa prompt riêng và kế hoạch các round.
        selected_targets, dropped_target_ids, round_plan = [], [], []
        # Mỗi nhóm khai báo loại target, system prompt, danh sách target và số round dự kiến.
        for family, instruction, family_analyses, repeats in self._target_batches(analyses):
            batches, dropped_ids = self._prepare_target_rounds(
                context, programs, analyses, prompt_prior_inputs, family_analyses, instruction,
                prior_stage_summary=prior_stage_summary,
            )
            for targets, _, _ in batches:
                selected_targets.extend(targets)
            dropped_target_ids.extend(dropped_ids)
            if batches:
                planned = [(family, instruction, *batch) for batch in batches]
                round_plan.extend(planned)
                round_plan.extend([planned[-1]] * max(0, repeats - len(planned)))
        aimed_puts = {row['program_id'] for row in analyses if row['targets']}
        unpromptable_puts = aimed_puts - {row['program_id'] for row in selected_targets}
        # Ghi kết quả phân tích và lựa chọn target trước khi gửi request đầu tiên.
        context.artifacts.write(
            f"{context.task_directory}/{self.name}/analysis.json",
            {
                "programs": analyses,  # Kết quả analysis theo PUT.
                "errors": analysis_errors,  # Lỗi lúc phân tích PUT.
                "selected_targets": selected_targets,  # Target đủ chỗ trong prompt dự kiến.
                "context_dropped_target_ids": dropped_target_ids,  # ID không vừa ngay cả khi gửi riêng.
                "context_blocked_put_ids": sorted(unpromptable_puts, key=repr),
            },
        )
        # Khi không có round, trả lý do và trạng thái coverage để caller biết task dừng ở đâu.
        if not round_plan:
            # Chưa đủ evidence nếu thiếu analysis hoặc thiếu CFG coverage.
            unknown = not analyses or any(
                row["coverage_status"] == "unknown" for row in analyses
            )
            return {
                "inputs": [],  # Bộ input mới rỗng vì chưa có round.
                "concepts": [],  # Chưa có response để đọc concept.
                "target_puts_without_trace": sorted(aimed_puts, key=repr),
                "status": (
                    # Ưu tiên báo prompt quá dài nếu đã có target nhưng bị cắt hết.
                    "prompt_too_large"
                    if dropped_target_ids
                    else "coverage_unknown" if unknown else "no_measured_gaps"
                ),
                # None là chưa xác định được, còn 0 là đã đo và không tìm thấy gap.
                "target_coverage": {
                    "covered": None if unknown or dropped_target_ids else 0,
                    "total": None if unknown or dropped_target_ids else 0,
                },
                "candidate_receipts": [],  # Chưa trace candidate mới.
                "rounds": [],  # Chưa gọi model.
                "native_trace_seconds": 0,  # Chỉ đếm trace candidate mới.
            }
        # Khóa nhận diện của base inputs và input kế thừa dùng để loại trùng.
        base_keys = self._base_and_prior_input_keys(builder, programs, prior_inputs)
        # Tích lũy concept đã parse, quan sát trace, log theo round và lỗi generation.
        concepts, trace_observations, round_logs, errors = [], [], [], []
        # Map candidate theo khóa input và set target đã được trace hit trong task.
        candidates, covered = {}, set()
        # Reserve a first trace for every PUT in each new batch.
        first_round_checks = []
        for index, plan in enumerate(round_plan):
            groups = {target['program_id'] for target in plan[2]}
            first_round_checks.append(len(groups) if index == 0 or plan != round_plan[index - 1] else 0)
        reserved_checks = sum(first_round_checks)
        llm_checks_left = max(self.settings.candidate_limit, reserved_checks)
        checks_per_round = llm_checks_left // len(round_plan)
        # Quota số lượt lấy mẫu Hypothesis còn lại, tính độc lập với trace proposal LLM.
        hypothesis_draws_left = HYPOTHESIS_INPUT_LIMIT
        # Dữ liệu trả cho model ở round sau nếu tiếp tục cùng nhóm target.
        feedback = None
        # Tích lũy thời gian trace candidate qua các round.
        native_trace_seconds = 0.0
        # Mỗi phần tử trong plan mang prompt và evidence riêng của round đó.
        for round_index, (family, instruction, targets, source, evidence) in enumerate(round_plan):
            change_batch = round_index > 0 and round_plan[round_index] != round_plan[round_index - 1]
            if change_batch:
                feedback = None
            if feedback is not None and not feedback['remaining_target_ids'] and not feedback['errors']:
                continue
            request = messages(
                context.task,
                context.metadata.get("contract", ""),
                source,
                evidence,
                targets,
                context.settings.input_budget,
                feedback,
                prior_stage_inputs=prompt_prior_inputs,
                prior_stage_summary=prior_stage_summary,
                max_prompt_prior_inputs=self.max_prompt_prior_inputs,
                instruction=instruction,
            )
            if context.calls.token_count(request) + context.settings.input_tokens + 128 > context.settings.context_tokens:
                errors.append('prompt_too_large')
                reserved_checks -= first_round_checks[round_index]
                continue
            # Mỗi PUT cần một lượt kiểm riêng cho mỗi input.
            trace_groups = {target['program_id'] for target in targets}
            reserved_checks -= first_round_checks[round_index]
            available_checks = min(llm_checks_left - reserved_checks,
                                   max(first_round_checks[round_index], len(trace_groups), checks_per_round))
            candidates_per_round = available_checks // len(trace_groups)
            # Gửi request, lưu response gốc, parse concept/input và ghi nhận thao tác sửa JSON.
            parsed, repairs = self._request_round(context, builder, request, targets, round_index)
            # Lỗi parse của round được cộng vào danh sách chung.
            errors.extend(parsed['errors'])
            # Gắn nguồn round và giữ concept ở mức giả thuyết dù model đã đề xuất.
            concepts.extend(
                {**concept, "round": round_index, "semantic_status": "hypothesis"}
                for concept in parsed["concepts"]
            )
            # Đếm số round còn lại, tính luôn round hiện tại.
            rounds_left = len(round_plan) - round_index
            # Chia lượt draw còn lại cho các round và làm tròn lên.
            draw_budget = (hypothesis_draws_left + rounds_left - 1) // rounds_left
            # Ledger giữ proposal LLM, mẫu Hypothesis và thông tin kiểm tra từng candidate.
            ledger, sampling = self._build_candidate_ledger(context, builder, parsed, round_index, draw_budget)
            # Chỉ trừ số draw đã ghi trong receipt của Hypothesis.
            hypothesis_draws_left -= sum(receipt['draws'] for receipt in sampling)
            # Lấy candidate hợp lệ từ ledger, loại base duplicates và chia theo nguồn LLM/Hypothesis.
            direct, sampled = self._queue_candidates(
                builder, ledger.pool(), candidates, base_keys, candidates_per_round,
                # Input đã thấy vẫn có thể chưa được trace trên các PUT của batch mới.
                retrace_existing=change_batch,
            )
            if first_round_checks[round_index] and not direct and not sampled:
                # A prior novel input is still a probe for owners in a new batch.
                fallback = next(((key, row['call']) for key, row in candidates.items()
                                 if row.get('domain') == 'valid'), None)
                if fallback is not None:
                    direct = [fallback]
            # Bắt đầu đo thời gian trace candidate của round.
            trace_started = time.monotonic()
            # Chạy proposal trực tiếp trong sandbox và cập nhật hit theo input và theo target.
            round_trace_observations = self._trace_candidates(
                context, programs, targets, direct, candidates, covered, available_checks,
            )
            # Mỗi quan sát tương ứng một lượt trace input–PUT.
            llm_checks_left -= len(round_trace_observations)
            # Mẫu Hypothesis có quota riêng. Mỗi mẫu có thể cần một trace trên mỗi nhóm.
            round_trace_observations.extend(
                self._trace_candidates(
                    context, programs, targets, sampled, candidates, covered, len(sampled) * len(trace_groups),
                )
            )
            # Tính thời gian cả hai lượt trace, rồi gộp quan sát của round vào kết quả task.
            native_trace_seconds += time.monotonic() - trace_started
            trace_observations.extend(round_trace_observations)
            # Kiểm tra predicate trên input đã có và xem input gắn với concept có hit target không.
            concept_checks = self._check_concepts(builder, parsed['concepts'], candidates, round_index)
            # Lưu những gì round đã thử để có thể đối chiếu response, candidate và target.
            round_logs.append(
                _round_log(
                    round_index,
                    family,
                    targets,
                    errors=parsed["errors"],
                    repairs=repairs,
                    sampling=sampling,
                    concept_checks=concept_checks,
                    ledger_rows=ledger.rows,
                    llm_count=len(direct),
                    sampled_count=len(sampled),
                )
            )
            # Gom evidence ngắn gọn để model sửa concept ở round sau của cùng nhóm.
            feedback = {
                'remaining_target_ids': [target['id'] for target in targets if target['id'] not in covered],
                'concepts': parsed['concepts'],
                'concept_checks': concept_checks,
                "errors": parsed["errors"],  # Lỗi để model có thể sửa.
                "candidate_observations_total": len(round_trace_observations),  # Tổng lượt trace trong round.
                # Cho model xem tối đa 12 quan sát trace với các field cần cho feedback.
                "candidates": [
                    {
                        key: row[key]
                        for key in (
                            "candidate_key",  # Hash nhận diện input.
                            "program_id",  # PUT nhận lời gọi này.
                            "call",  # Args và kwargs đã dựng.
                            "domain",  # Input có qua contract trong trace không.
                            "status",  # Trạng thái thực thi trong sandbox.
                            "hit_targets",  # ID target có witness ở lượt trace này.
                        )
                    }
                    for row in round_trace_observations[:12]
                ],
            }
            if reserved_checks:
                continue
            # Chỉ dừng sớm sau khi đã gửi prompt cho mọi batch đầu tiên.
            if llm_checks_left == 0 and hypothesis_draws_left == 0:
                break

        # Giữ input đã qua domain, ưu tiên input đóng góp target mới và cắt theo budget cuối mở rộng theo số target.
        suite_input_budget = max(context.settings.input_budget, SUITE_TARGET_OFFSET + len(selected_targets))
        selected, selected_coverage = self._select_inputs(candidates, suite_input_budget)
        return {
            # Giữ provenance trong luồng kế thừa để stage sau biết nguồn input.
            "inputs": [
                (
                    {**row["call"], "sources": row["sources"]}
                    if prior_inputs is not None
                    else row["call"]
                )
                for row in selected
            ],
            "suite_input_budget": suite_input_budget,
            "concepts": concepts,  # Concept đã parse từ các round.
            "status": "generated" if round_logs else "prompt_too_large",  # Đã xử lý round hay hết chỗ.
            "errors": errors,  # Lỗi generation đã tích lũy.
            "candidate_receipts": trace_observations,  # Tất cả quan sát trace candidate.
            "rounds": round_logs,  # Log theo round gồm target IDs, parser, sampler và ledger.
            "target_coverage": {
                "covered": len(covered),  # Target hit bởi bất kỳ candidate đã trace nào.
                "total": len(selected_targets),  # Target đã xếp vào các batch vừa context.
                "selected_covered": len(selected_coverage),  # Target hit bởi input được giữ cuối.
            },
            "selected_targets": selected_targets,  # Chi tiết các target còn trong plan.
            "target_puts_without_trace": sorted(
                aimed_puts - {row['program_id'] for row in trace_observations}, key=repr),
            "candidate_count": len(candidates),  # Số input khác nhau đã đưa vào pool.
            "native_trace_seconds": native_trace_seconds,  # Thời gian trace candidate mới.
        }

    def _analyze_programs(self, context, programs, prior_inputs):
        analyses, analysis_errors = [], []
        for program in programs:
            try:
                had_coverage = program['base'].get('coverage') is not None
                base_calls = program['base'].get('calls', [])
                if not had_coverage and len(base_calls) > 300:
                    analysis_errors.append({'program_id': program['id'], 'reason': 'baseline_call_budget_exceeded'})
                elif not had_coverage and base_calls:
                    observations = context.artifacts.load_or_compute(
                        f"{context.task_directory}/{self.name}/base_{digest(program['id'])[:16]}.json",
                        lambda: self.trace(context, program, program['base']['calls'])
                    )
                    measured = [row['coverage'] for row in observations if row.get('domain') == 'valid' and 'coverage' in row]
                    # Only a complete recorded-call replay supports missing-gap claims.
                    if measured and len(measured) == len(observations):
                        program["base"]["coverage"] = {
                            "lines": sorted(
                                {line for row in measured for line in row["lines"]}
                            ),
                            "arcs": [
                                list(arc)
                                for arc in sorted(
                                    {
                                        tuple(arc)
                                        for row in measured
                                        for arc in row["arcs"]
                                    }
                                )
                            ],
                        }
                targets_before_prior = None
                if prior_inputs is not None and program['base'].get('coverage') is not None:
                    targets_before_prior = len(analyze(program, context.task['entry_point'])['targets'])
                added_coverage = []
                if prior_inputs and (targets_before_prior is None or targets_before_prior > 0):
                    observations = context.artifacts.load_or_compute(
                        f"{context.task_directory}/{self.name}/prior_{digest(program['id'])[:16]}.json",
                        lambda: [
                            {'input_id': row['input_id'], 'source_stage': row['source_stage'], **observation}
                            for row, observation in zip(prior_inputs, self.trace_prior(context, program, prior_inputs), strict=True)
                        ])
                    added_coverage = [row['coverage'] for row in observations
                                      if row.get('domain') == 'valid' and 'coverage' in row]
                    # Missing original evidence cannot establish that any target is uncovered.
                    if program['base'].get('coverage') is not None:
                        measurements = [program['base']['coverage'], *added_coverage]
                        program['base']['coverage'] = {
                            'lines': sorted({line for row in measurements for line in row['lines']}),
                            'arcs': [list(arc) for arc in sorted({tuple(arc) for row in measurements for arc in row['arcs']})],
                        }
                analysis = analyze(program, context.task['entry_point'])
                analysis["baseline"] = {
                    "source": (
                        "cached_coverage" if had_coverage else "recorded_call_replay"
                    ),
                    "recorded_calls": len(program["base"].get("calls", [])),
                }
                if prior_inputs is not None:
                    analysis["baseline"].update(
                        prior_stage_calls=len(prior_inputs),
                        prior_stage_calls_with_coverage=len(added_coverage),
                        targets_before_prior=targets_before_prior,
                    )
                analyses.append(analysis)
            except (ValueError, SyntaxError) as error:
                analysis_errors.append({'program_id': program['id'], 'reason': str(error)})
        return analyses, analysis_errors

    def _target_batches(self, analyses):
        return [('cfg', self.instruction, analyses, self.settings.rounds)]

    def _prepare_target_rounds(
        self, context, programs, analyses, prior_inputs, family_analyses, instruction, *,
        prior_stage_summary=None,
    ):
        pending = [target for row in family_analyses for target in row['targets']]
        if not pending:
            return [], []
        evidence = [
            {
                "program_id": row["program_id"],
                "source_sha256": row["source_sha256"],
                "coverage_status": row["coverage_status"],
            }
            for row in analyses
        ]
        source = [
            {
                "id": p["id"],
                "code": compact_source(p["code"]),
                "base_inputs": [
                    {key: call[key] for key in ("args", "kwargs") if key in call}
                    for call in p["base"].get("calls", [])[:12]
                ],
            }
            for p in programs
        ]

        def fit(targets):
            used = {target['program_id'] for target in targets}
            selected_source = [row for row in source if row['id'] in used]
            selected_evidence = [row for row in evidence if row['program_id'] in used]
            request = messages(
                context.task,
                context.metadata.get("contract", ""),
                selected_source,
                selected_evidence,
                targets,
                context.settings.input_budget,
                prior_stage_inputs=prior_inputs,
                prior_stage_summary=prior_stage_summary,
                max_prompt_prior_inputs=self.max_prompt_prior_inputs,
                instruction=instruction,
            )
            if context.calls.token_count(request) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
                return targets, selected_source, selected_evidence
            return None

        batches, dropped_ids = [], []
        offset = 0
        while offset < len(pending):
            # Fit the longest prefix, leaving its suffix for a later prompt.
            for size in range(min(len(pending) - offset, self.settings.target_limit), 0, -1):
                batch = fit(pending[offset:offset + size])
                if batch:
                    batches.append(batch)
                    offset += size
                    break
            else:
                dropped_ids.append(pending[offset]['id'])
                offset += 1
        return batches, dropped_ids

    @staticmethod
    def _base_and_prior_input_keys(builder, programs, prior_inputs):
        base_keys = set()
        base_calls = [call for program in programs for call in program['base'].get('calls', [])]
        for call in [*base_calls, *(prior_inputs or ())]:
            try:
                base_keys.add(repr(input_identity(builder.signature, call)))
            except (ValueError, TypeError, SyntaxError):
                pass
        return base_keys

    def _request_round(self, context, builder, request, targets, round_index):
        response = context.calls.complete(
            context.task_number,
            f"{self.name}_round_{round_index}",
            request,
            temperature=context.settings.input_temperature,
            max_tokens=context.settings.input_tokens,
            seed=context.settings.input_seed + context.task_number + round_index,
        )
        raw_path = f"{context.task_directory}/{self.name}/response_{round_index}.json"
        context.artifacts.write(
            raw_path,
            {
                "text": response.text,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "request_sha256": digest(request),
            },
        )
        try:
            raw, repairs = load_response_json(response.text)
            parsed = parse_response(raw, targets, builder.signature.parameters)
        except (ValueError, TypeError) as error:
            parsed, repairs = {'inputs': [], 'concepts': [], 'errors': [str(error)]}, []
        if response.finish_reason != 'stop':
            parsed['errors'].append('incomplete_response:' + str(response.finish_reason))
            parsed['concepts'] = []
        return parsed, repairs

    def _build_candidate_ledger(self, context, builder, parsed, round_index, draw_budget):
        from ..tool_sampling.constructors import sample_hypothesis
        from ..tool_sampling.ledger import CandidateLedger

        sampling = []
        model = {
            "types": {name: "any" for name in builder.signature.parameters},
            "domain": "True",
            "targets": [],
            "factors": [],
            "strategies": {},
        }
        ledger = CandidateLedger(context.task['task_id'], self.name, builder, model)
        for index, record in enumerate(parsed['inputs'][:context.settings.input_budget]):
            if not isinstance(record, dict):
                continue
            ledger.add(
                {"arguments": record.get("arguments")},
                {
                    "tool": "llm",
                    "round": round_index,
                    "draw_index": index,
                    "concept_id": record.get("concept_id"),
                },
            )
        concepts = [concept for concept in parsed['concepts'] if concept['strategies']]
        for index, concept in enumerate(concepts):
            if draw_budget == 0:
                break
            concepts_left = len(concepts) - index
            draws = min(self.settings.draws_per_concept, (draw_budget + concepts_left - 1) // concepts_left)
            ledger.model['strategies'] = concept['strategies']
            receipt = sample_hypothesis(
                ledger,
                draws=draws,
                seed=context.settings.input_seed + round_index * 1009 + index,
                seconds=self.settings.sampling_seconds,
                source={"concept_id": concept["id"], "round": round_index},
            )
            sampling.append(receipt)
            draw_budget -= receipt['draws']
        return ledger, sampling

    @staticmethod
    def _queue_candidates(builder, pool, candidates, base_keys, candidates_per_round, *, retrace_existing=False):
        direct, sampled = [], []
        for row in pool:
            call = row['canonical_args']
            key = repr(input_identity(builder.signature, call))
            if key in candidates:
                for source_item in row['sources']:
                    if source_item not in candidates[key]['sources']:
                        candidates[key]['sources'].append(source_item)
                if not retrace_existing:
                    continue
            if key in base_keys:
                continue
            tools = {source['tool'] for source in row['sources']}
            if 'llm' in tools and len(direct) < candidates_per_round:
                direct.append((key, call))
            elif tools - {'llm'}:
                sampled.append((key, call))
            else:
                continue
            candidates.setdefault(key, {'call': call, 'sources': row['sources'], 'hit_targets': []})
        return direct, sampled

    def _trace_candidates(self, context, programs, targets, pending, candidates, covered, check_budget):
        trace_observations = []
        for program in programs:
            relevant = [target for target in targets if target['program_id'] == program['id']]
            if not relevant:
                continue
            remaining_checks = check_budget - len(trace_observations)
            attempted = pending[:max(0, remaining_checks)]
            if not attempted:
                break
            observations = self.trace(context, program, [call for _, call in attempted])
            for (key, call), observation in zip(attempted, observations):
                hits = [target['id'] for target in relevant if hit(target, observation)]
                covered.update(hits)
                candidates[key]['hit_targets'].extend(hits)
                candidates[key].setdefault('domain', observation.get('domain'))
                trace_record = {
                    "candidate_key": digest(key),
                    "program_id": program["id"],
                    "call": call,
                    "hit_targets": hits,
                    **observation,
                }
                trace_observations.append(trace_record)
        return trace_observations

    @staticmethod
    def _check_concepts(builder, concepts, candidates, round_index):
        from ..tool_sampling.ledger import predicate_status

        concept_checks = []
        for concept in concepts:
            target_hits, predicate_checks = [], []
            for key, candidate in candidates.items():
                if not any(
                    s.get('concept_id') == concept['id'] and s.get('round') == round_index
                    for s in candidate['sources']
                ):
                    continue
                bound = builder.signature.bind(
                    *ast.literal_eval(candidate["call"]["args"]),
                    **ast.literal_eval(candidate["call"]["kwargs"]),
                )
                bound.apply_defaults()
                status, detail = (
                    predicate_status(concept["predicate"], dict(bound.arguments))
                    if concept["predicate"]
                    else ("unknown", "predicate_not_supplied")
                )
                predicate_checks.append({'candidate_key': digest(key), 'predicate': status, 'detail': detail})
                if concept['target_id'] in candidate['hit_targets']:
                    target_hits.append(digest(key))
            concept_checks.append(
                {
                    "concept_id": concept["id"],
                    "target_id": concept["target_id"],
                    "realized_candidate_keys": target_hits,
                    "predicate_checks": predicate_checks,
                    "status": "observed" if target_hits else "pending",
                    "semantic_status": "hypothesis",
                }
            )
        return concept_checks

    @staticmethod
    def _select_inputs(candidates, input_budget):
        valid = [row for row in candidates.values() if row.get('domain') == 'valid']
        selected, selected_coverage = [], set()
        for row in sorted(valid, key=lambda item: -len(set(item['hit_targets']))):
            if len(selected) >= input_budget:
                break
            if set(row['hit_targets']) - selected_coverage:
                selected.append(row)
                selected_coverage.update(row['hit_targets'])
        for row in valid:
            if len(selected) >= input_budget:
                break
            if row not in selected:
                selected.append(row)
        return selected, selected_coverage

    def extend_summary(self, contexts, summary, reporting):
        batches = [context.inputs['arms'][self.name] for context in contexts if not context.inputs.get('skip')]
        coverage = [batch.get('target_coverage', {}) for batch in batches]
        summary[self.name] = {
            "concepts": sum(len(batch.get("concepts", [])) for batch in batches),
            "model_calls": sum(len(batch.get("rounds", [])) for batch in batches),
            "observed_targets": sum(
                row.get("covered") or 0 for row in coverage
            ),
            "selected_targets": sum(
                row.get("total") or 0 for row in coverage
            ),
            "coverage_pending_tasks": sum(
                row.get("total") is None for row in coverage
            ),
        }


class ControlFlowFourToolArm(ControlFlowArm):
    """ControlFlow seeded with strictly oracle-free 4-tool inputs and residual C1/C2 tracing."""

    name = 'control_flow_4tool'
    # Tool inputs (huge ints, long strings) need more time than LLM-written inputs.
    trace_timeout_cap_seconds = 2

    def __init__(
        self,
        settings=None,
        *,
        tool_runs_dir=None,
        max_prior_inputs=DEFAULT_MAX_PRIOR_INPUTS,
        max_prompt_prior_inputs=DEFAULT_MAX_PROMPT_PRIOR_INPUTS,
    ):
        super().__init__(settings, max_prompt_prior_inputs=max_prompt_prior_inputs)
        self.tool_runs_dir = str(tool_runs_dir) if tool_runs_dir else None
        self.max_prior_inputs = max_prior_inputs

    def configuration(self):
        return {
            **super().configuration(),
            "prior_source": "4tool_pytest_receipts",
            "prior_tools": list(FOUR_TOOLS),
            "max_prior_inputs": self.max_prior_inputs,
            "max_prompt_prior_inputs": self.max_prompt_prior_inputs,
            "tool_runs_dir": self.tool_runs_dir or "auto",
            "trace_timeout_cap_seconds": self.trace_timeout_cap_seconds,
        }

    def _resolve_tool_runs_dir(self, context):
        explicit = self.tool_runs_dir or context.extensions.get("tool_runs_dir")
        return explicit if explicit else str(default_tool_runs_dir(context.task["task_id"]))

    def _load_prior_inputs(self, context, programs):
        runs_dir = self._resolve_tool_runs_dir(context)
        return context.artifacts.load_or_compute(
            f"{context.task_directory}/{self.name}/tool4_prior_inputs.json",
            lambda: load_four_tool_prior_inputs(
                context.task,
                context.metadata,
                programs,
                tool_runs_dir=runs_dir,
                max_prior_inputs=self.max_prior_inputs,
                validate_timeout=min(2.0, context.settings.timeout_seconds),
                seed=context.settings.reference_seed,
            ),
        )

    @_measure_generation_time
    def discover(self, context):
        if context.calls is None or context.packet is None:
            raise RuntimeError('Control-flow discovery requires prepared context and model calls')
        base_pass_programs = [
            program for program in context.cohort_task["programs"]
            if program["base"]["status"] == "pass"
        ]
        loaded = self._load_prior_inputs(context, base_pass_programs)
        upstream = context.extensions.get("prior_stage_inputs")
        prior_inputs = [*(upstream or ()), *loaded["inputs"]]
        _, prompt_summary = compact_prompt_prior_inputs(
            prior_inputs, limit=self.max_prompt_prior_inputs,
        )
        run_context = copy.copy(context)
        run_context.extensions = {
            **context.extensions,
            "prior_stage_inputs": prior_inputs,
            "prior_stage_summary": prompt_summary,
            "trace_timeout_cap": self.trace_timeout_cap_seconds,
        }
        result = super().discover(run_context)
        analysis = context.artifacts.read(f"{context.task_directory}/{self.name}/analysis.json")
        analyzed = analysis.get("programs", [])
        if analyzed and all(
            row.get("coverage_status") == "measured"
            and row.get("baseline", {}).get("targets_before_prior") is not None
            for row in analyzed
        ):
            before_total = sum(row["baseline"]["targets_before_prior"] for row in analyzed)
            residual_total = sum(len(row["targets"]) for row in analyzed)
            eliminated_total = max(0, before_total - residual_total)
            closed_by_4tool = before_total > 0 and residual_total == 0
        else:
            before_total = None
            residual_total = None
            eliminated_total = None
            closed_by_4tool = False

        result["tool4_prior_summary"] = {
            "loaded_stats": loaded["stats"],
            "prior_inputs_traced": len(prior_inputs),
            "prompt_prior_examples_shown": prompt_summary["shown_examples"],
            "base_targets_before_4tool": before_total,
            "residual_targets_after_4tool": residual_total,
            "targets_eliminated_by_4tool": eliminated_total,
            "closed_by_4tool": closed_by_4tool,
            "analysis_error_count": len(analysis.get("errors", [])),
        }
        return result

    def extend_summary(self, contexts, summary, reporting):
        super().extend_summary(contexts, summary, reporting)
        batches = [context.inputs['arms'][self.name] for context in contexts if not context.inputs.get('skip')]
        prior_rows = [batch.get("tool4_prior_summary", {}) for batch in batches]
        before_values = [row.get("base_targets_before_4tool") for row in prior_rows]
        residual_values = [row.get("residual_targets_after_4tool") for row in prior_rows]
        known_before = all(type(value) is int for value in before_values) and bool(before_values)
        known_residual = all(type(value) is int for value in residual_values) and bool(residual_values)
        summary[self.name].update(
            prior_inputs_loaded=sum(row.get("prior_inputs_traced", 0) for row in prior_rows),
            base_targets_before_4tool=sum(before_values) if known_before else None,
            residual_targets_after_4tool=sum(residual_values) if known_residual else None,
            targets_eliminated_by_4tool=(
                sum(row.get("targets_eliminated_by_4tool") or 0 for row in prior_rows)
                if known_before and known_residual
                else None
            ),
            tasks_closed_by_4tool=sum(bool(row.get("closed_by_4tool")) for row in prior_rows),
            tasks_with_residual_gaps=sum(
                type(row.get("residual_targets_after_4tool")) is int
                and row["residual_targets_after_4tool"] > 0
                for row in prior_rows
            ),
        )
