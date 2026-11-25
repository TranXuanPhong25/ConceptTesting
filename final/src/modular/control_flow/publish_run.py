"""Publish ControlFlow + 4-tool run artifacts to local Prefect (run with .venv_orchestration)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import urlopen
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactCreate, ArtifactUpdate
from prefect.states import Completed, Failed, Running

from final.src.orchestration.history import clean, historical_record
from final.src.runtime.artifacts import save


def publish_directory(output_dir: Path, *, port: int = 4200) -> dict:
    output_dir = output_dir.resolve()
    os.environ.setdefault("PREFECT_API_URL", f"http://127.0.0.1:{port}/api")
    os.environ.setdefault("PREFECT_HOME", str(ROOT / "final/out/run_console/prefect_home"))

    record_file = output_dir / "prefect_record.json"
    config = clean(json.loads((output_dir / "config_snapshot.json").read_text()))
    progress = clean(json.loads((output_dir / "progress.json").read_text()))
    state_name = progress.get("state", "running")
    stage = {"complete": Completed, "failed": Failed, "interrupted": Failed}.get(state_name, Running)
    message = progress.get("message") or f"ControlFlow + 4-tool ({config.get('dataset', 'unknown')}): {state_name}"
    state = stage(message=str(message)[:400])

    dataset_label = "HumanEval" if config.get("dataset") == "humaneval" else "MBPP+"
    scope = f"{config.get('requested_task_count', '?')} task"
    run_title = config.get("run_title") or (
        f"Control-flow + 4-tool trace · {dataset_label} · {scope} · {config.get('model_name', 'qwen')}"
    )

    artifacts: dict[str, tuple[str, object, str]] = {
        "cf4tool-config": (
            "markdown",
            "```json\n" + json.dumps(config, ensure_ascii=False, indent=2) + "\n```",
            "Cấu hình thực tế, budget, source/output directory (không chứa secret/URL ngrok).",
        ),
        "cf4tool-progress": (
            "markdown",
            "```json\n" + json.dumps(progress, ensure_ascii=False, indent=2) + "\n```",
            "Tiến độ generation / evaluation; metric chưa có được giữ là pending.",
        ),
    }

    digest_path = output_dir / "result_digest.json"
    if digest_path.is_file():
        digest_obj = clean(json.loads(digest_path.read_text()))
        cf_stats = digest_obj.get("control_flow_4tool", {})
        arm_metrics = digest_obj.get("arms", {}).get("control_flow_4tool", {})
        union_info = digest_obj.get("tools4_union", {})
        rows = [
            {
                "arm": "control_flow_4tool",
                "dataset": dataset_label,
                "evaluated_base_pass_puts": digest_obj.get("evaluated_base_pass"),
                "valid_inputs": arm_metrics.get("valid_inputs"),
                "detected_puts": arm_metrics.get("detected"),
                "tasks_detected": arm_metrics.get("tasks_detected"),
                "model_calls": cf_stats.get("model_calls"),
                "base_targets_before_4tool": cf_stats.get("base_targets_before_4tool"),
                "residual_targets_after_4tool": cf_stats.get("residual_targets_after_4tool"),
                "tasks_closed_by_4tool": cf_stats.get("tasks_closed_by_4tool"),
                "tools4_saved_detected": union_info.get("tools4_base_pass_detected"),
                "union_tools4_plus_cf4tool": union_info.get("union_detected"),
                "marginal_gain_over_tools4": union_info.get("cf4tool_unique_over_tools4"),
            }
        ]
        artifacts["cf4tool-results"] = (
            "table",
            rows,
            "Kết quả đo sau evaluation hoàn tất (đơn vị detected là số PUT base-pass lệch oracle).",
        )

    report_path = output_dir / "REPORT.md"
    if report_path.is_file():
        artifacts["cf4tool-report"] = (
            "markdown",
            clean(report_path.read_text(encoding="utf-8"))[:80000],
            "Báo cáo tiếng Việt đầy đủ kết quả, giới hạn kết luận, budget, token và union với 4 tool.",
        )

    tags = ["ConceptTester", "control_flow_4tool", config.get("dataset", "unknown"), config.get("model_backend", "qwen")]
    with get_client(sync_client=True) as client:
        if record_file.is_file():
            receipt = json.loads(record_file.read_text())
            rid = UUID(receipt["flow_run_id"])
        else:
            run = client.create_flow_run(
                historical_record,
                name=run_title,
                parameters=clean(config),
                tags=tags,
                state=Running(message="Đã tạo bản ghi Prefect; chuẩn bị chạy control_flow_4tool."),
            )
            rid = run.id
            receipt = {
                "flow_run_id": str(rid),
                "url": f"http://127.0.0.1:{port}/runs/flow-run/{rid}",
                "artifact_ids": {},
            }
            save(record_file, receipt)

        for key, (kind, data, description) in clean(artifacts).items():
            if key in receipt["artifact_ids"]:
                client.update_artifact(
                    UUID(receipt["artifact_ids"][key]),
                    ArtifactUpdate(data=data, description=description),
                )
            else:
                artifact = client.create_artifact(
                    ArtifactCreate(
                        key=key,
                        type=kind,
                        data=data,
                        description=description,
                        flow_run_id=rid,
                    )
                )
                receipt["artifact_ids"][key] = str(artifact.id)
                save(record_file, receipt)

        observed = client.read_flow_run(rid)
        if observed.state.type != state.type or observed.state.message != state.message:
            client.set_flow_run_state(rid, state, force=True)
        receipt["verified_state"] = client.read_flow_run(rid).state.type.value
        for key, aid in receipt["artifact_ids"].items():
            with urlopen(f"http://127.0.0.1:{port}/api/artifacts/{aid}", timeout=10) as response:
                artifact = json.load(response)
            assert artifact["flow_run_id"] == str(rid) and artifact["key"] == key
        receipt["verified_artifact_count"] = len(receipt["artifact_ids"])
        save(record_file, receipt)
        return receipt


def main(arguments=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--port", type=int, default=4200)
    args = parser.parse_args(arguments)
    receipt = publish_directory(args.output_dir, port=args.port)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
