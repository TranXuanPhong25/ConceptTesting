# Scheduled matched prompt-style diagnostic

Terminal update: run đã hoàn tất19:57ngày6/11; [results/audit](boundary_prompt_style_results_2026-11-07.md).
Direct2tasks/60valid,soft2/58,worksheet1/54;9calls/0unknown. Nội dung bên dưới là
frozen schedule/plan lịch sử, không phải job vẫn chờ chạy.

User đồng ý kiểm tra hypothesis prompt scaffolding giới hạn exploration và yêu
cầu dùng endpoint cũ sau20phút. Controller đã được schedule cho
**2026-11-06 19:51:15 Asia/Ho_Chi_Minh (12:51:15UTC)**, dựa trên clock check
12:31:15UTCkhi nhận yêu cầu schedule. Đây là detached local process, không phải
một entry trong ChatGPT Scheduled Tasks UI.

Output:final/out/boundary_prompt_style3_20261106. SchedulerPID68463;
đọc `scheduler_status.json` trước mọi thao tác, không launch duplicate. PID của
runner chỉ được tạo sau readiness đạt yêu cầu; hiện chưa có model completions.

## Cấu hình đã freeze

-3tasks2/11/157, exactPUTs6/1/3; mỗi task chỉ có một PUT giống nhau cho3arms.
- Arms: direct, soft_bva, internally applied adapted five-step worksheet.
- Same spec/contract/base calls/system/output schema; only guidance block differs.
- Sameqwen3.5-27b-awq,temperature0.7,seed314159+task,completion2048/context8192,
  cap20inputs/task/arm.9logical requests; normal bounded transport attempts.
- No templates, fixed target compiler, applicability gate, failure feedback,
  known witness or reference output in any arm. No model tools.
- Balanced order across3tasks. All9outputs freeze before corrected-reference/PUT
  evaluation,2repeat slots. Values only encoded, not adjusted to boundaries.

Worksheet arm is adapted to the common direct-input schema, not exact2-stagev5.
This tests instruction-style bundles, not isolated prompt length or hard-gating.
Tasks were chosen after reviewing failures; no general efficacy/detection-rate
claim. Historical9/10PUTnaive prompts are not reused as matched controls; these
3fresh direct calls do not replace/regenerate the fixed44task baseline.

## Readiness / one-shot safeguards

At due time, scheduler verifies92frozen source/data/request/controller files and
1,205prior output files, exact model metadata/context, then tokenizes all9requests.
It launches once only if all checks pass; otherwise stores blocked state and
stops. No automatic reschedule/model substitution/source repair. Private endpoint
config remains outside repo/logs. Before due time there are0completion attempts.

Exclusive persistent schedule/launch reservations prevent a crash/restart from
resetting readiness/launch allowances. Process lock prevents concurrent schedulers.
Independent review cleared matched packets, common parser, internal-only
worksheet adaptations and durable one-shot guards. Offline parser/comparability
checks pass; no outcome has been computed for this diagnostic.

On terminal success the controller writes `result_digest.json`,
`PROMPT_STYLE_RESULT.md`, generation accounting, replay receipt and integrity
summary. If it blocks, use `scheduler_status.json`/`prelaunch_readiness.json` and
logs; do not infer a semantic outcome from a transport/readiness failure.

Core pipeline/current default v5and sealed baseline are unchanged by scheduling.
All experimental records remain uncommitted for review. PREREG latest entries
contain scope, review amendments and explicit user scheduling authorization.
