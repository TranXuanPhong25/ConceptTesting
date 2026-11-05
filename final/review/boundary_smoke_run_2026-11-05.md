# Plain + BVA: boundary smoke run — complete

Update2026-11-05: run completed6/6tasks with the supplied Qwen27endpoint and the
new execution cache. Controller156764completed;all inputs frozen before scoring.
112engineeringchecks pass. Registration/source/config and original readiness
artifacts preserved. The readiness notes farther below describe the prelaunch
state; the results immediately below are authoritative.

## Kết quả actual run

| Arm | Logical calls | Known total tokens | Valid novel inputs | Detected PUTs |
|---|---:|---:|---:|---:|
| plain | 6 | 9,043 | 80 | 0/6 |
| boundary (BVA) | 10 | 23,742 | 19 | 0/6 |

16requests/16responses,0unknown,0retries. Total32,785tokens:20,982prompt+
11,803completion. BVA selection6calls/11,382tokens;construction4calls/12,360tokens.
Two no-boundary cases skip construction. No paid fallback/backend substitution.
Elapsed controller time approximately738seconds,including generation/evaluation.

| Task | Plain valid | BVA valid | BVA generation status | Main observation |
|---|---:|---:|---|---|
| HumanEval/0 | 20 | 0 | no_inputs |20records fail exact boundary target |
| HumanEval/5 | 20 | 0 | no_boundary |No selected supported boundary |
| HumanEval/18 | 20 | 4 | generated |16records fail boundary target |
| HumanEval/81 | 0 | 9 | generated |Plain passes a scalar to a list parameter;20TypeErrors |
| HumanEval/99 | 0 | 0 | no_boundary |Plain emits singleton strings without tuple comma;20invalid literals |
| HumanEval/120 | 20 | 6 | generated |Other BVA records rejected for shape/ID,target,side or duplicates |

Both arms detect0additional failures. This does not establish that all6PUTs are
correct,or that BVA is ineffective: it is a tiny development smoke and two plain
tasks have no valid generated input. No matched-call efficacy claim is possible;
BVA uses10calls while plain uses6and their valid yields differ substantially.

The main observed BVA construction issue is HumanEval0: selection chooses the
positive-float boundary at0with float_adjacent/above,but all20proposals miss the
exact adjacent representable value. Task99 has only string-length candidates in
the current template support,not a numeric-value characteristic of parsed text.
These are method/interface limitations recorded as outcomes;no posthoc prompt
repair,threshold relaxation,semantic reinterpretation or extra generation was
silently applied to this frozen run.

## Execution cache và audit

Cold run:432input/repeat records,428native executions,4cache hits;0uncached
timeouts,0corrupt entries,0missing receipts. Repeat0and1retain separate observations.
Generations and method statuses are not changed by cache hits.

Warm-cache audit reconstructed all24reference/PUTrepeat jobs from the frozen
inputs and forbade subprocess creation. Result: **432hits,0native executions,
0model requests,in0.1202seconds**,with exact equality to original execution
artifacts. This measures native execution reuse,not generation latency.
Receipt:output/cache_reuse_audit.json.

Full read-only pipeline replay also reproduces the entire saved summary (including
original cold-run cache receipts). All68sourcehashes and6inputfreezehashes verified;
no reference/plus outputs entered generation and no native/model execution was
needed for read-only replay.

Outputs: `final/out/boundary_smoke_plain_bva_20261105/REPORT.md`,
`modular_summary.json`, `generation_frozen.json`, per-task input/oracle/result
artifacts and per-job cache receipts. Source cohort and representatives unchanged.

User yêu cầu chạy hai arm trên dataset đã tách theo hướng boundary, ngày2026-11-05.
Theo protocol phát triển theo nhóm đã có, bắt đầu từ smoke6PUT, chưa mở rộng lên
development/check/full và chưa tạo PUT mới.

## Cấu hình đã khóa trước inference

- Cohort: `final/out/development_groups/boundary/smoke/cohort.json`.
- Task order: HumanEval/0,5,18,81,99,120; mỗi task PUT0, saved base-pass.
- Subset cohort hash: `3dce7e980e164f6e161febc08455f0ade571a921297e1755d61a42563cdbccfa`.
- Arms: `plain`, `boundary` (BVA); target_programs1; input budget20/arm/task.
- Model: user-supplied `qwen3.5-27b-awq`, context8192; backend config ngoài repo.
- Plain và BVA construction: temperature0.7, max2048tokens, seed314159+tasknumber.
- BVA selection: temperature0, max2048tokens, tối đa4boundaries/PUT.
- Tối đa18logicalcalls:6plain+6selection+6construction; skip có thể giảm số calls.
- Reference oracle/PUT evaluation: timeout3seconds/call,2repeats, trusted contract;
  all-task generation freeze trước bất kỳ reference outcome nào.
- Output: `final/out/boundary_smoke_plain_bva_20261105/`.

Registration: [PREREG](../modular/PREREG.md), amendment2026-11-05.
Output đã có `run_config.json`, `modular_manifest.json` khóa67sourcefiles,
`readiness.json` và `launch.sh`; không chứa endpoint/keys.

## Kiểm tra trước launch

60targeted checks pass (BVA module, arm integration và generator injection).
Subset checksum/task membership/PUT0/base-pass/generated count đều được verify.
Same-agent read-only review đã kiểm shared schema, prompt data separation,
context/input budgets, early skip, immutable checkpoints, transport retry history,
generation freeze và repeated reference/PUT evaluation. Không claim independent
review trong lần kiểm tra này.

Modern flow của cả hai arm không có classical concept mining/CFG/DFG/witness
sampling. BVA prose constraints vẫn là proposals; chỉ trusted contract/reference
outcomes được dùng cho validity/scoring. Tất cả generated/rejected/skip cases
được giữ lại; không sửa prompt/method theo outputs rồi overwrite run cũ.

## Trạng thái ban đầu trước launch (lịch sử)

Stored endpoint `/models` trả **HTTP404**. Chưa tokenize thành công, chưa gửi
completion, chưa launch controller và chưa có task inputs/reference/results.
Đã hỏi user endpoint hiện đang hoạt động. Không dùng paid router thay thế.

Sau khi nhận endpoint: cập nhật private env bên ngoài repo, kiểm expected model/
context/tokenizer, xác minh source hashes rồi launch `launch.sh` detached với
keepalive20minutes. Theo dõi `status.json`, `stage_events.jsonl` và call receipts;
chỉ báo running sau khi thấy controller và request thực tế.

Kết quả sẽ report theo6task: valid novel inputs, detected PUTs, boundary selection/
construction/validation failures, known/unknown calls/tokens. Đây là development
smoke với equal input caps và unequal LLM calls; không claim matched-call efficacy.
