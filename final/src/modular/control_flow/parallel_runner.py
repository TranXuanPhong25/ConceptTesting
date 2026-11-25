"""Parallel runner for ControlFlow + 4-tool tracing on HumanEval and MBPP+ with Prefect sync."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from final.src.benchmarks.datasets import DatasetLoader
from final.src.benchmarks.language_runtime import execute_program
from final.src.benchmarks.pipeline import (
    _generate_control_flow_arms,
    _trace_mbpp_base,
    adapter_task,
    load_candidates,
    run_benchmark,
)
from final.src.models import create_model
from final.src.modular.arms.control_flow import ControlFlowFourToolArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.catalogue_reporting import usage_by_arm
from final.src.modular.cohort import call_usage, load_cohort
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.control_flow.tool_inputs import default_tool_runs_dir
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.generators.methods import MethodInputGenerator
from final.src.modular.pipeline import BenchmarkPipeline, generate_task_inputs
from final.src.runtime.artifacts import save

ROOT = Path(__file__).resolve().parents[4]
ORCH_PYTHON = ROOT / "final/.venv_orchestration/bin/python"
NATIVE_LOCK = ROOT / "final/out/.boundary_native.lock"
DEFAULT_HE_COHORT = ROOT / "final/out/cohorts/qwen35_27b_humaneval164/cohort.json"
DEFAULT_MBPP_CANDIDATES = ROOT / "final/out/gemini_mbppplus_20261117_081625/candidates.jsonl"
DEFAULT_EXECUTION_CACHE = ROOT / "final/out/execution_cache"


def _sync_prefect(output_dir: Path, enabled: bool) -> None:
    if not enabled or not ORCH_PYTHON.is_file():
        return
    try:
        subprocess.run(
            [str(ORCH_PYTHON), "-m", "final.src.modular.control_flow.publish_run", str(output_dir)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        print(f"[prefect-sync warning] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def _saved_tools4_detected_puts(tool_runs_dir: Path, dataset: str) -> set[tuple[str, str]]:
    """Read post-evaluation saved 4-tool confirmed detections ONLY for final comparison reporting."""
    detected: set[tuple[str, str]] = set()
    four_tools = {"crosshair", "pynguin", "utbot", "ghostwriter"}
    fail_statuses = {"fail", "error", "timeout"}
    prefix = "HumanEval" if dataset == "humaneval" else "MBPP"
    tasks_root = tool_runs_dir / "tasks"
    if not tasks_root.is_dir():
        return detected
    for task_dir in tasks_root.iterdir():
        replay_path = task_dir / "oracle_replay.json"
        if not task_dir.is_dir() or not replay_path.is_file():
            continue
        try:
            doc = json.loads(replay_path.read_text())
        except (OSError, ValueError):
            continue
        task_id = doc.get("task_id") or f"{prefix}/{task_dir.name}"
        inputs = doc.get("inputs", [])
        four_indices = {
            index
            for index, item in enumerate(inputs)
            if any(source.get("tool") in four_tools for source in item.get("sources", []))
        }
        if not four_indices:
            continue
        for put_id, row in doc.get("put_results", {}).items():
            if not isinstance(row, dict) or row.get("base") != "pass":
                continue
            first = row.get("first", [])
            confirmation = row.get("confirmation", {})
            for index in four_indices:
                if index < len(first) and first[index].get("status") in fail_statuses:
                    confirm_row = confirmation.get(str(index))
                    if isinstance(confirm_row, dict) and confirm_row.get("status") in fail_statuses:
                        detected.add((task_id, str(put_id)))
                        break
    return detected


def _cf4tool_detected_puts_he(output_dir: Path) -> tuple[set[tuple[str, str]], set[str]]:
    found: set[tuple[str, str]] = set()
    scored_task_ids: set[str] = set()
    for result_path in sorted(output_dir.glob("tasks/*/result.json")):
        doc = json.loads(result_path.read_text())
        if "skip" in doc:
            continue
        task_id = doc["task_id"]
        scored_task_ids.add(task_id)
        arm_row = doc.get("arms", {}).get("control_flow_4tool", {})
        if isinstance(arm_row.get("detected_put_ids"), list):
            for put_id in arm_row["detected_put_ids"]:
                found.add((task_id, str(put_id)))
            continue
        arm_indices = set(doc.get("arm_indices", {}).get("control_flow_4tool", []))
        for put_id, row in doc.get("outcomes", {}).items():
            failing = row.get("failing", []) if isinstance(row, dict) else row
            if arm_indices & set(failing):
                found.add((task_id, str(put_id)))
    return found, scored_task_ids


def _cf4tool_detected_puts_mbpp(output_dir: Path) -> tuple[set[tuple[str, str]], set[str]]:
    found: set[tuple[str, str]] = set()
    scored_task_ids: set[str] = set()
    for result_path in sorted(output_dir.glob("tasks/*/result.json")):
        doc = json.loads(result_path.read_text())
        if "skip" in doc:
            continue
        task_id = doc["task_id"]
        scored_task_ids.add(task_id)
        arm_indices = set(doc.get("arm_indices", {}).get("control_flow_4tool", []))
        for put_id, failing in doc.get("outcomes", {}).items():
            if arm_indices & set(failing):
                found.add((task_id, str(put_id)))
    return found, scored_task_ids


def _make_thread_calls(backend: str, model_name: str, context_tokens: int, store: ArtifactStore):
    local = threading.local()

    def get_calls() -> RecordedModelCalls:
        if not hasattr(local, "calls"):
            model = create_model(backend=backend, model_name=model_name, context=context_tokens)
            local.calls = RecordedModelCalls(model, store)
        return local.calls

    return get_calls


def _render_vietnamese_report(dataset: str, digest_obj: dict) -> str:
    label = "HumanEval" if dataset == "humaneval" else "MBPP+"
    arm = digest_obj["arms"]["control_flow_4tool"]
    cf = digest_obj.get("control_flow_4tool", {})
    union = digest_obj.get("tools4_union", {})
    usage = digest_obj.get("tester_calls", {})
    cfg = digest_obj["config"]
    lines = [
        f"# Kết quả Control-flow + 4-tool trace · {label}",
        "",
        (
            f"**Kết luận ngắn**: `control_flow_4tool` phát hiện **{arm['detected']}/{digest_obj['evaluated_base_pass']}** "
            f"base-pass PUTs lệch oracle trên **{arm['tasks_detected']}/{digest_obj['eligible_tasks']}** eligible task "
            f"(từ **{arm['valid_inputs']}** novel valid inputs). "
            f"4 tool đã cắt target C1/C2 từ **{cf.get('base_targets_before_4tool')} → {cf.get('residual_targets_after_4tool')}** "
            f"(loại **{cf.get('targets_eliminated_by_4tool')}** target, đóng trọn **{cf.get('tasks_closed_by_4tool')}** task với 0 call LLM)."
        ),
        "",
        (
            "**Giới hạn kết luận**: kết quả đo trên frozen cohort hiện có; với MBPP+ chỉ kiểm reference disagreement "
            "(chưa có executable domain contract chung, spec validity còn `pending`). "
            "Số liệu `detected` đếm unique PUT, không phải số input."
        ),
        "",
        "## Cấu hình & chi phí",
        f"- Dataset: `{label}` ({cfg['requested_task_count']} requested tasks, {digest_obj['eligible_tasks']} eligible tasks, {digest_obj['evaluated_base_pass']} base-pass PUTs)",
        f"- Model: `{cfg['model_name']}` (backend `{cfg['model_backend']}`), `context_tokens={cfg['context_tokens']}`, `completion_tokens={cfg['completion_tokens']}`, `inputs_per_task={cfg['inputs_per_task']}`, `timeout_seconds={cfg['timeout_seconds']}`, `workers={cfg['workers']}`",
        f"- 4-tool prior source (oracle-free): `{cfg['tool_runs_dir']}` (4 tool: CrossHair, Pynguin, UTBot, Ghostwriter; loại Klara)",
        f"- Model calls: `{usage.get('received', 0)}/{usage.get('invocations', 0)}` responses/attempts (unknown `{usage.get('unknown', 0)}`), known tokens: `{usage.get('known_usage', {}).get('total_tokens', 0)}`",
        "",
        "## So sánh union với bộ 4 tool đã lưu",
        f"- Saved 4-tool detected PUTs (trên tập task chạy): `{union.get('tools4_base_pass_detected')}`",
        f"- `control_flow_4tool` standalone: `{arm['detected']}` PUTs",
        f"- `Tools4 ∪ control_flow_4tool`: `{union.get('union_detected')}` PUTs (tăng ròng ngoài 4 tool: **+{union.get('cf4tool_unique_over_tools4')}** PUTs)",
        "",
        "## Chi tiết JSON",
        "```json",
        json.dumps(digest_obj, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


def run_humaneval(options, output_dir: Path) -> dict:
    dataset = DatasetLoader("HE-py")
    tasks = dataset.load_tasks()
    if options.task_numbers:
        wanted = set(options.task_numbers)
        tasks = [t for t in tasks if int(t["task_id"].split("/")[1]) in wanted]
        if len(tasks) != len(wanted):
            raise ValueError("Some requested HumanEval task numbers were not found")
    metadata = dataset.load_metadata()
    cohort_path = Path(options.he_cohort).resolve()
    tool_runs_dir = Path(options.tool_runs_dir).resolve() if options.tool_runs_dir else default_tool_runs_dir("HumanEval/0")

    config = {
        "dataset": "humaneval",
        "arm": "control_flow_4tool",
        "cohort_path": str(cohort_path.relative_to(ROOT)) if cohort_path.is_relative_to(ROOT) else str(cohort_path),
        "tool_runs_dir": str(tool_runs_dir.relative_to(ROOT)) if tool_runs_dir.is_relative_to(ROOT) else str(tool_runs_dir),
        "output_directory": str(output_dir.relative_to(ROOT)) if output_dir.is_relative_to(ROOT) else str(output_dir),
        "requested_task_count": len(tasks),
        "task_numbers": [int(t["task_id"].split("/")[1]) for t in tasks] if options.task_numbers else [],
        "model_backend": options.model_backend,
        "model_name": options.model_name,
        "context_tokens": options.context_tokens,
        "completion_tokens": options.completion_tokens,
        "inputs_per_task": options.input_budget,
        "temperature": options.temperature,
        "input_seed": options.seed,
        "reference_seed": options.reference_seed,
        "timeout_seconds": options.timeout_seconds,
        "workers": options.workers,
        "scorer": "confirm_first_failures",
    }
    if options.dry_run:
        return {"dry_run": True, "config": config}

    output_dir.mkdir(parents=True, exist_ok=True)
    save(output_dir / "config_snapshot.json", config)
    save(output_dir / "progress.json", {
        "state": "running", "phase": "preflight", "generated_tasks": 0,
        "total_tasks": len(tasks), "detected_puts": "pending",
        "message": "Preflight endpoint trước khi sinh input HumanEval control_flow_4tool.",
    })
    save(output_dir / "status.json", {"state": "preflight", "pid": os.getpid(), "updated_utc": time.time()})

    preflight_model = create_model(
        backend=options.model_backend, model_name=options.model_name, context=options.context_tokens,
    )
    readiness = preflight_model.check_endpoint()
    save(output_dir / "endpoint_readiness.json", {"checked_utc": time.time(), **readiness})
    _sync_prefect(output_dir, options.publish_prefect)

    store = ArtifactStore(output_dir)
    settings = PipelineSettings(
        input_budget=options.input_budget,
        input_tokens=options.completion_tokens,
        input_temperature=options.temperature,
        input_seed=options.seed,
        reference_seed=options.reference_seed,
        context_tokens=options.context_tokens,
        timeout_seconds=options.timeout_seconds,
        target_programs=10,
        scorer="confirm_first_failures",
    )
    cohort = load_cohort(cohort_path)
    cohort_tasks = {row["task_id"]: row for row in cohort["tasks"]}
    get_calls = _make_thread_calls(options.model_backend, options.model_name, options.context_tokens, store)

    lock = threading.Lock()
    done_count = 0
    closed_count = 0
    residual_task_count = 0
    started = time.monotonic()

    def run_one_task(task: dict) -> str:
        nonlocal done_count, closed_count, residual_task_count
        arm = ControlFlowFourToolArm(tool_runs_dir=tool_runs_dir)
        generator = MethodInputGenerator((arm,), empty_context_on_overflow=True)
        ctx = TaskContext(task, metadata[task["task_id"]], store, settings, get_calls())
        ctx.cohort_task = cohort_tasks[task["task_id"]]
        generator.prepare_context(ctx)
        result = generate_task_inputs(ctx, generator)
        batch = result.get("arms", {}).get("control_flow_4tool", {})
        prior_summary = batch.get("tool4_prior_summary", {})
        with lock:
            done_count += 1
            if prior_summary.get("closed_by_4tool"):
                closed_count += 1
            if (prior_summary.get("residual_targets_after_4tool") or 0) > 0:
                residual_task_count += 1
            prog = {
                "state": "running",
                "phase": "generation",
                "generated_tasks": done_count,
                "total_tasks": len(tasks),
                "tasks_closed_by_4tool": closed_count,
                "tasks_with_residual_gaps": residual_task_count,
                "elapsed_seconds": round(time.monotonic() - started, 1),
                "detected_puts": "pending",
                "message": f"Generation {done_count}/{len(tasks)} HumanEval tasks ({options.workers} workers).",
            }
            save(output_dir / "progress.json", prog)
            save(output_dir / "status.json", {"state": "running", "phase": "generation", "pid": os.getpid(), "generated_tasks": done_count, "updated_utc": time.time()})
            if done_count % 15 == 0 or done_count == len(tasks):
                print(f"[HE gen] {done_count}/{len(tasks)} (closed4={closed_count}, residual={residual_task_count}, {prog['elapsed_seconds']}s)", flush=True)
                _sync_prefect(output_dir, options.publish_prefect)
        return task["task_id"]

    try:
        with ThreadPoolExecutor(max_workers=options.workers) as pool:
            futures = [pool.submit(run_one_task, task) for task in tasks]
            for future in as_completed(futures):
                future.result()

        save(output_dir / "progress.json", {
            "state": "running", "phase": "waiting_native_lock",
            "generated_tasks": len(tasks), "total_tasks": len(tasks),
            "detected_puts": "pending", "message": "Generation xong; chờ native lock để evaluation HumanEval.",
        })
        save(output_dir / "status.json", {"state": "waiting_native_lock", "pid": os.getpid(), "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)

        NATIVE_LOCK.parent.mkdir(parents=True, exist_ok=True)
        with NATIVE_LOCK.open("a+") as native_handle:
            fcntl.flock(native_handle, fcntl.LOCK_EX)
            save(output_dir / "progress.json", {
                "state": "running", "phase": "evaluation",
                "generated_tasks": len(tasks), "total_tasks": len(tasks),
                "detected_puts": "pending", "message": "Đang chấm reference oracle và PUT evaluation HumanEval.",
            })
            save(output_dir / "status.json", {"state": "running", "phase": "evaluation", "pid": os.getpid(), "updated_utc": time.time()})
            arm = ControlFlowFourToolArm(tool_runs_dir=tool_runs_dir)
            generator = MethodInputGenerator((arm,), empty_context_on_overflow=True)
            pipeline = BenchmarkPipeline(
                cohort_path,
                store,
                input_generator=generator,
                settings=settings,
                calls=None,
                execution_cache=InputExecutionCache(DEFAULT_EXECUTION_CACHE),
                dataset=dataset,
            )
            summary = pipeline.run(tasks, metadata)

        cf_det, scored_task_ids = _cf4tool_detected_puts_he(output_dir)
        tools4_det = {pair for pair in _saved_tools4_detected_puts(tool_runs_dir, "humaneval") if pair[0] in scored_task_ids}
        union_det = tools4_det | cf_det

        digest_obj = {
            "dataset": "humaneval",
            "config": config,
            "eligible_tasks": summary["expected_tasks"] - len(summary.get("skips", {})),
            "scored_tasks": summary["scored_tasks"],
            "evaluated_base_pass": summary["evaluated_base_pass"],
            "arms": summary["arms"],
            "control_flow_4tool": summary.get("control_flow_4tool", {}),
            "tester_calls": call_usage(output_dir),
            "tester_calls_by_arm": usage_by_arm(output_dir, ["control_flow_4tool"]),
            "skips": summary.get("skips", {}),
            "tools4_union": {
                "tools4_base_pass_detected": len(tools4_det),
                "cf4tool_detected": len(cf_det),
                "union_detected": len(union_det),
                "cf4tool_unique_over_tools4": len(cf_det - tools4_det),
                "cf4tool_unique_put_ids": sorted(f"{tid}#{pid}" for tid, pid in (cf_det - tools4_det)),
            },
            "elapsed_seconds": round(time.monotonic() - started, 1),
        }
        save(output_dir / "result_digest.json", digest_obj)
        (output_dir / "REPORT.md").write_text(_render_vietnamese_report("humaneval", digest_obj), encoding="utf-8")
        save(output_dir / "progress.json", {
            "state": "complete", "phase": "complete",
            "generated_tasks": len(tasks), "evaluated_tasks": len(tasks), "total_tasks": len(tasks),
            "detected_puts": digest_obj["arms"]["control_flow_4tool"]["detected"],
            "evaluated_base_pass": digest_obj["evaluated_base_pass"],
            "elapsed_seconds": digest_obj["elapsed_seconds"],
            "message": f"Hoàn tất HumanEval control_flow_4tool: {digest_obj['arms']['control_flow_4tool']['detected']}/{digest_obj['evaluated_base_pass']} PUTs.",
        })
        save(output_dir / "status.json", {"state": "complete", "pid": os.getpid(), "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)
        return digest_obj
    except BaseException as exc:
        save(output_dir / "progress.json", {
            "state": "failed", "phase": "error", "generated_tasks": done_count, "total_tasks": len(tasks),
            "detected_puts": "pending", "error_type": type(exc).__name__, "error": str(exc)[:400],
            "message": f"Dừng do lỗi {type(exc).__name__}; các checkpoint đã lưu vẫn được giữ nguyên.",
        })
        save(output_dir / "status.json", {"state": "failed", "pid": os.getpid(), "error_type": type(exc).__name__, "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)
        raise


def run_mbpp(options, output_dir: Path) -> dict:
    raw_tasks = DatasetLoader("MBPP-py").load_tasks()
    tasks = [adapter_task(row) for row in raw_tasks]
    if options.task_numbers:
        wanted = set(options.task_numbers)
        tasks = [t for t in tasks if int(t["task_id"].split("/")[1]) in wanted]
        if len(tasks) != len(wanted):
            raise ValueError("Some requested MBPP task numbers were not found")
    candidates_path = Path(options.mbpp_candidates).resolve()
    cohort = load_candidates(candidates_path, tasks)
    # Keep only tasks present in the supplied candidate cohort.
    tasks = [t for t in tasks if t["task_id"] in cohort]
    tool_runs_dir = Path(options.tool_runs_dir).resolve() if options.tool_runs_dir else default_tool_runs_dir("MBPP/2")

    adapter_cfg = {
        "dataset": "mbpp",
        "candidate_path": str(candidates_path),
        "task_numbers": [int(t["task_id"].split("/")[1]) for t in tasks],
        "arms": ["control_flow_4tool"],
        "backend": options.model_backend,
        "model_name": options.model_name,
        "inputs_per_task": options.input_budget,
        "completion_tokens": options.completion_tokens,
        "context_tokens": options.context_tokens,
        "temperature": options.temperature,
        "seed": options.seed,
        "timeout_seconds": options.timeout_seconds,
        "tool_runs_dir": str(tool_runs_dir),
    }
    config = {
        "dataset": "mbpp",
        "arm": "control_flow_4tool",
        "candidate_path": str(candidates_path.relative_to(ROOT)) if candidates_path.is_relative_to(ROOT) else str(candidates_path),
        "tool_runs_dir": str(tool_runs_dir.relative_to(ROOT)) if tool_runs_dir.is_relative_to(ROOT) else str(tool_runs_dir),
        "output_directory": str(output_dir.relative_to(ROOT)) if output_dir.is_relative_to(ROOT) else str(output_dir),
        "requested_task_count": len(tasks),
        "candidate_put_count": sum(len(v) for v in cohort.values()),
        "model_backend": options.model_backend,
        "model_name": options.model_name,
        "context_tokens": options.context_tokens,
        "completion_tokens": options.completion_tokens,
        "inputs_per_task": options.input_budget,
        "temperature": options.temperature,
        "seed": options.seed,
        "timeout_seconds": options.timeout_seconds,
        "workers": options.workers,
    }
    if options.dry_run:
        return {"dry_run": True, "config": config}

    output_dir.mkdir(parents=True, exist_ok=True)
    save(output_dir / "config_snapshot.json", config)
    save(output_dir / "progress.json", {
        "state": "running", "phase": "preflight", "generated_tasks": 0,
        "total_tasks": len(tasks), "detected_puts": "pending",
        "message": "Preflight endpoint trước khi sinh input MBPP+ control_flow_4tool.",
    })
    save(output_dir / "status.json", {"state": "preflight", "pid": os.getpid(), "updated_utc": time.time()})

    preflight_model = create_model(
        backend=options.model_backend, model_name=options.model_name, context=options.context_tokens,
    )
    readiness = preflight_model.check_endpoint()
    save(output_dir / "endpoint_readiness.json", {"checked_utc": time.time(), **readiness})
    _sync_prefect(output_dir, options.publish_prefect)

    store = ArtifactStore(output_dir)
    get_calls = _make_thread_calls(options.model_backend, options.model_name, options.context_tokens, store)

    lock = threading.Lock()
    done_count = 0
    base_pass_tasks = 0
    closed_count = 0
    residual_task_count = 0
    started = time.monotonic()

    def run_one_mbpp_task(task: dict) -> str:
        nonlocal done_count, base_pass_tasks, closed_count, residual_task_count
        number = int(task["task_id"].split("/")[1])
        prefix = f"tasks/{number}"
        programs = cohort.get(task["task_id"], [])
        passing = []
        for program in programs:
            baseline = store.load_or_compute(
                f"{prefix}/base/{program['id']}.json",
                lambda program=program: execute_program(task, program["code"], [], timeout=options.timeout_seconds, base=True),
            )
            if baseline["status"] in ("unsupported_environment", "infrastructure_error"):
                raise RuntimeError(baseline["status"] + ": " + task["task_id"])
            if baseline["status"] == "ok" and baseline["tests"] == [{"status": "ok"}]:
                passing.append(program)

        prior_summary = {}
        if passing:
            if store.exists(prefix + "/inputs.json"):
                batches = store.read(prefix + "/inputs.json")
            else:
                batches = _generate_control_flow_arms(
                    task,
                    passing,
                    store,
                    adapter_cfg,
                    ["control_flow_4tool"],
                    calls=get_calls(),
                    base_tracer=_trace_mbpp_base,
                    default_tool_runs_dir=str(tool_runs_dir),
                )
                store.write(prefix + "/inputs.json", batches)
            prior_summary = batches.get("control_flow_4tool", {}).get("tool4_prior_summary", {})

        with lock:
            done_count += 1
            if passing:
                base_pass_tasks += 1
            if prior_summary.get("closed_by_4tool"):
                closed_count += 1
            if (prior_summary.get("residual_targets_after_4tool") or 0) > 0:
                residual_task_count += 1
            prog = {
                "state": "running",
                "phase": "generation",
                "generated_tasks": done_count,
                "total_tasks": len(tasks),
                "base_pass_tasks": base_pass_tasks,
                "tasks_closed_by_4tool": closed_count,
                "tasks_with_residual_gaps": residual_task_count,
                "elapsed_seconds": round(time.monotonic() - started, 1),
                "detected_puts": "pending",
                "message": f"Generation {done_count}/{len(tasks)} MBPP+ tasks ({options.workers} workers).",
            }
            save(output_dir / "progress.json", prog)
            save(output_dir / "status.json", {"state": "running", "phase": "generation", "pid": os.getpid(), "generated_tasks": done_count, "updated_utc": time.time()})
            if done_count % 25 == 0 or done_count == len(tasks):
                print(f"[MBPP gen] {done_count}/{len(tasks)} (base_pass_tasks={base_pass_tasks}, closed4={closed_count}, residual={residual_task_count}, {prog['elapsed_seconds']}s)", flush=True)
                _sync_prefect(output_dir, options.publish_prefect)
        return task["task_id"]

    try:
        with ThreadPoolExecutor(max_workers=options.workers) as pool:
            futures = [pool.submit(run_one_mbpp_task, task) for task in tasks]
            for future in as_completed(futures):
                future.result()

        save(output_dir / "progress.json", {
            "state": "running", "phase": "waiting_native_lock",
            "generated_tasks": len(tasks), "total_tasks": len(tasks),
            "detected_puts": "pending", "message": "Generation MBPP+ xong; chờ native lock để evaluation.",
        })
        save(output_dir / "status.json", {"state": "waiting_native_lock", "pid": os.getpid(), "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)

        NATIVE_LOCK.parent.mkdir(parents=True, exist_ok=True)
        with NATIVE_LOCK.open("a+") as native_handle:
            fcntl.flock(native_handle, fcntl.LOCK_EX)
            save(output_dir / "progress.json", {
                "state": "running", "phase": "evaluation",
                "generated_tasks": len(tasks), "total_tasks": len(tasks),
                "detected_puts": "pending", "message": "Đang chấm reference và PUT evaluation MBPP+.",
            })
            save(output_dir / "status.json", {"state": "running", "phase": "evaluation", "pid": os.getpid(), "updated_utc": time.time()})
            summary = run_benchmark(
                tasks, cohort, store, adapter_cfg,
                calls=None,
                executor=execute_program,
                default_tool_runs_dir=str(tool_runs_dir),
            )

        cf_det, scored_task_ids = _cf4tool_detected_puts_mbpp(output_dir)
        tools4_det = {pair for pair in _saved_tools4_detected_puts(tool_runs_dir, "mbpp") if pair[0] in scored_task_ids}
        union_det = tools4_det | cf_det

        digest_obj = {
            **summary,
            "config": config,
            "eligible_tasks": len(tasks) - len(summary.get("skips", [])),
            "tools4_union": {
                "tools4_base_pass_detected": len(tools4_det),
                "cf4tool_detected": len(cf_det),
                "union_detected": len(union_det),
                "cf4tool_unique_over_tools4": len(cf_det - tools4_det),
                "cf4tool_unique_put_ids": sorted(f"{tid}#{pid}" for tid, pid in (cf_det - tools4_det)),
            },
            "elapsed_seconds": round(time.monotonic() - started, 1),
        }
        save(output_dir / "result_digest.json", digest_obj)
        (output_dir / "REPORT.md").write_text(_render_vietnamese_report("mbpp", digest_obj), encoding="utf-8")
        save(output_dir / "progress.json", {
            "state": "complete", "phase": "complete",
            "generated_tasks": len(tasks), "evaluated_tasks": len(tasks), "total_tasks": len(tasks),
            "detected_puts": digest_obj["arms"]["control_flow_4tool"]["detected"],
            "evaluated_base_pass": digest_obj["evaluated_base_pass"],
            "elapsed_seconds": digest_obj["elapsed_seconds"],
            "message": f"Hoàn tất MBPP+ control_flow_4tool: {digest_obj['arms']['control_flow_4tool']['detected']}/{digest_obj['evaluated_base_pass']} PUTs.",
        })
        save(output_dir / "status.json", {"state": "complete", "pid": os.getpid(), "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)
        return digest_obj
    except BaseException as exc:
        save(output_dir / "progress.json", {
            "state": "failed", "phase": "error", "generated_tasks": done_count, "total_tasks": len(tasks),
            "detected_puts": "pending", "error_type": type(exc).__name__, "error": str(exc)[:400],
            "message": f"Dừng do lỗi {type(exc).__name__}; các checkpoint đã lưu vẫn được giữ nguyên.",
        })
        save(output_dir / "status.json", {"state": "failed", "pid": os.getpid(), "error_type": type(exc).__name__, "updated_utc": time.time()})
        _sync_prefect(output_dir, options.publish_prefect)
        raise


def parse_args(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("humaneval", "mbpp", "both"), default="both")
    parser.add_argument("--output-dir", type=Path, help="Output directory (single dataset) or base prefix (both)")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent task workers (match vLLM --max-num-seqs)")
    parser.add_argument("--context-tokens", type=int, default=20480)
    parser.add_argument("--completion-tokens", type=int, default=4096)
    parser.add_argument("--input-budget", type=int, default=20)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--reference-seed", type=int, default=271828)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--model-backend", choices=("qwen", "vertex", "openrouter"), default="qwen")
    parser.add_argument("--model-name", default="qwen3.5-27b-awq")
    parser.add_argument("--task-numbers", nargs="+", type=int, default=[])
    parser.add_argument("--he-cohort", type=Path, default=DEFAULT_HE_COHORT)
    parser.add_argument("--mbpp-candidates", type=Path, default=DEFAULT_MBPP_CANDIDATES)
    parser.add_argument("--tool-runs-dir", type=Path, default=None)
    parser.add_argument("--no-publish-prefect", dest="publish_prefect", action="store_false", default=True)
    parser.add_argument("--dry-run", action="store_true", help="Print resolved plan without model/native/Prefect calls")
    return parser.parse_args(arguments)


def main(arguments=None) -> int:
    options = parse_args(arguments)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    results = {}
    if options.dataset in ("humaneval", "both"):
        he_out = (
            options.output_dir
            if options.output_dir and options.dataset == "humaneval"
            else (
                Path(str(options.output_dir) + "_humaneval")
                if options.output_dir
                else ROOT / f"final/out/cf_4tool_qwen_{stamp}_humaneval"
            )
        )
        results["humaneval"] = run_humaneval(options, he_out)
    if options.dataset in ("mbpp", "both"):
        mbpp_out = (
            options.output_dir
            if options.output_dir and options.dataset == "mbpp"
            else (
                Path(str(options.output_dir) + "_mbpp")
                if options.output_dir
                else ROOT / f"final/out/cf_4tool_qwen_{stamp}_mbpp"
            )
        )
        results["mbpp"] = run_mbpp(options, mbpp_out)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
