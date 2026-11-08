---
name: run-console
description: User-operated local Prefect console for immutable presets, run history, preview-only budget checks and resumable checkpoints
metadata:
  type: project
---

2026-11-08 user yêu cầu tên run/deployment dễ đọc. Đã đổi7run tại chỗ,giữ ID,
source/artifacts/results. Tên chính:Full164·Naive cũ+packaging repair·82PUT;
Full164·Direct vs Soft BVA·batch·68vs73PUT;Full164·Soft BVA·per-PUT,shared20·61PUT.
Preset nguồn dùng tên human-readable trong final/presets/run_console.json;
names.py dùng cho historical/futuremanaged run labels,preview có prefixPreview.
Prefect3.9.2DeploymentUpdate không cho đổi name:đã đăng ký5deployment mới,
kiểm tra parameters/flowID giống bản cũ rồi gỡ5olddeployments,0workload launched.
NewdeploymentIDs/name mapping và metadata backup nằm trong final/out/run_console/
display_names_applied_20261108.json và display_names_backup_20261108.json.
Listener mới PID334867polls5newdeployments;17offlineconsolechecksPASS.
Thay tên nguồn xong đã reloadpresets;không restart hoặc thay đổi external worker.

User requests a local web UI to store configs/runs,edit settings and decide when to
launch future model runs. Implemented using Prefect3.9.2local self-hosted UI/server,
SQLite,Apache2open-source package;benchmark Python remains in final/.venv and
orchestration in final/.venv_orchestration. Never start fresh inference as an agent
action just because a preset/server exists. User presses Run.

User nhắc lại2026-11-08:việc chạy do người dùng quyết định;AGENTS.md rule9.
Mặc định agent chuẩn bị preset/config để người dùng bấm Run. Lệnh rõ ràng như
“sửa và chạy đi” chỉ cấp quyền cho đúng run/scope đó. “Check” là đọc trạng thái,
không tự launch/schedule/resume/rerun thêm. Currentbatch158735đã được user cho
phép trước lời nhắc;statuscheck108/164tasks,không khởi chạy workload mới.

Start/open/status/stop: `./final/run_console.sh start` then
<http://127.0.0.1:4200/deployments>;status/stop through same script. UI,
history importer and preset listener bind to127.0.0.1.
Latest PIDs:server36897,presets83876,history42656. SQLite/artifacts/logs under
final/out/run_console/;database survives service restart. Latest deployment source
revision `src-370f527b99e09ab84083`. 18historical runs indexed read-only,0new
inference.0managed Prefect flows active at latest audit.

Four presets:full-batch-direct-soft(max314calls),known10-batch-direct-soft(max20),
smoke3-batch-direct-soft(max6),full-soft-per-put-shared20(max1454).
Forms label inputs/task/arm;per_put divides20/task across visible PUTs.
preview_only is a visible checkbox:checked saves resolved config/budget with
0model/tokenizer/native calls. Prefect Run with preview_only=false is the user's
authorization. Each real job gets config/cohort/source snapshot+progress/retries/
input freeze/native checkpoints/report in final/out/console_<flow-id>/run.
Endpoint/key only in unique private600 profile outside repo;never in Prefect
parameters/config/logs. Source revision hash recorded in deployments.

Refresh preset defaults via `./final/run_console.sh reload-presets`;it refuses
while managed flows are active. Do not use generic Prefect Retry. The resume
deployment checks the worker lock, preserves request/retry history and creates a
new output. Imported historical runs are read-only and cannot stop external jobs.

Scorer,timeout,cache,base example scope and native flock are explicit. Batch and
per-PUT budget units are different and shown in fields. Historical provenance is
separate from any new user-launched run. Existing external PID28517 is untouched.

444full-suite checks passed before final field-title/doc updates;17targeted offline
console checks passed before final docs/revision refinements;independent review
PASS. Browser form screenshot stored at final/out/run_console/ui_config_form.png.
Preview form was inspected;an attempted automation to check its hidden HTML input
timed out before form submit,so it launched no flow and made0model/native calls.
End-to-end offline worker smoke also used dummy writer responses/empty native input;
it is a wiring smoke,not an experiment/result.

See final/src/orchestration/README.md. No commit requested.

2026-11-08 user requires agents to publish authorized runs to Prefect and write
reports in Vietnamese, keeping technical terms/schema fields in English.
AGENTS.md rules7–8 specify required artifacts, one flow ID per source, true states,
pending metrics, direct run links and metadata-only cleanup with backups.

2026-11-08 full matched batch evaluation resume published as one Running record,
flow5319cd2e-fdd0-4296-ad51-7a6b93579fc1/sourcebva_batch_matched164_evaluation_20261108_140053.
PID158735,314saved responses/60task checkpoints,0newmodelcalls. Existing importer
updates progress/finalresults automatically;Vietnamese recovery report artifact
47a6c592-4343-4f9e-a76e-9b7be96f0ce5. Final Vietnamese REPORT.md is published at
completion. Keep historical stopped-source suppression intact. See [[bva-batch-comparison]].

2026-11-08 cleanup theo yêu cầu: xóa27Prefect rows từ32còn5run Completed duy nhất.
Giữ style3/style10, fullBVA corrected evaluation, naive packaging audit và bucket
observer64c28b68. Gỡ orphan duplicates, stopped/prepared rows, old-oracle v11 và
comparison61/44 đã được packaging audit61/82 thay thế. Backup toàn bộ row/artifact
metadata tại final/out/run_console/history_cleanup_full_20261108_133913.json;
0source files deleted. Suppression cập nhật, sync/API readback xác nhận không
reimport và mỗi source chỉ1record. Cleanup trước chỉ duyệt ID trong mapping nên
bỏ sót các duplicate/orphan rows trên server; lần này duyệt actual server rows.

2026-11-08 user explicitly requests current bucket queue results on Prefect.
Read-only external observer added without changing server/listener/history code
or launching inference. Run64c28b68-68bf-4825-b745-f927b8ef063b, four task nodes,
results table/Markdown artifacts, auto-update15s by detached136739untilqueuecomplete.
Publisher in research/boundary-input-generation-2026-11-07/prefect_observer.py;
mapping under final/out/run_console/bucket_observers/. LISP34/44atpublish,
valid/detectionmetrics pending,other3queued. Observer cannot control worker via
generic PrefectRetry/Cancel. See research folder PREFECT_PUBLICATION.md.

Latest bucket observer142838 reuses samePrefectflow64c28b68/mapping, follows
verified ISLa-only continuation after preserving first3completed candidates.
No duplicate flow or workload rerun. LISP15valid/10detected,CrossHair2/1,DSpec3/2,
ISLa active. See research ISLA_CONTINUATION_STATUS.md and live artifacts.

2026-11-08 bucket results CORRECTED:all4complete,validinputs15/2/3/8,detected0all.
Old10/1/2/2were sandbox NumPy ModuleNotFoundError falsepositives;zero-model
rescore exactinputs/byte-identicalscorer+reference/freshcache verifiedallPASS.
Sameflow64c28b68nowpoints corrected_evaluation_20261108;API table0all.
Oldartifactskept,nonewmodelcalls. See research VERIFIED_RESULTS.md.
