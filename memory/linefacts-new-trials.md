---
name: linefacts-new-trials
description: B3/B4 and repaired v14/v15 complete; B4 lost to flat/toolinput, no promotion; new FSM/spec-mutation work remains planning
metadata:
  type: project
---

(2026-10-14) User: “thử hai cái này trước, nhớ làm trong folder khác”, referring to grounded obligation graphs
and conditional metamorphic concepts. This supersedes the research report's suggested waiting for B3/B4 before
trying new variants. Each is in a separate self-contained copy from v13_hyp, with its own CHANGELOG and runner.

User initially reported exhausted quota/no endpoint, then supplied the private endpoint and explicitly requested
GPU execution (2026-10-14 ~12:52 local). Frozen source commit 4ff245d; sequential detached chain starts v14 then v15,
20 dev tasks/K=1, four workers, own keepalive, shared saved v11 refs. No paid API/held-out run.
GPU smoke completed: 0 accepted cards in both methods; treatment was not exercised. See RESULTS §11.44 and
analysis/v14_v15_gpu_smoke.md/json. User corrected priority to **resume B3 → B4 first**, then return to v14/v15.
Queue: trickcatcher_linefacts/out/runlogs_resume_b3_b4/{pid,steps.txt,chain.sh}. B3 uses the exact frozen relation
replay adapter (root PREREG) to preserve its manifest and avoid repeated CPU extraction. No held-out run.

**Where:** [v14 README](../trickcatcher_linefacts/pipelines/v14_obgraph/README.md),
[v15 README](../trickcatcher_linefacts/pipelines/v15_mrconcept/README.md), RESULTS §11.43, PREREG exploratory
v14/v15 entry and local [version tree](../trickcatcher_linefacts/pipelines/EXPERIMENTS-2026-10-14.md).
CPU evidence and scope limits are recorded in each folder's CPU_VALIDATION.md/json, not duplicated here.

**How to apply:** use the new `experiment.py`/run_experiment.sh entrypoints, not the inherited legacy run.py.
Frozen 20 dev tasks/K=1 and fixed strategy slots; reuse v11 mining and spec-only refs. Require the user's private
Qwen endpoint before online stages; never turn CPU fixture checks into effectiveness claims. Existing v12/v13
runs and held-out remain separate. Related: [[linefacts-relational-research]], [[research-state]].

**Queue checkpoint (2026-10-14):** B3 complete; exact original task-44 worker retry succeeded and score
finished. Result is recorded in RESULTS §11.45 and analysis/b3_v12_rel_results.md/json; relation-vs-flat
inconclusive, no held-out promotion. B4 bundle/proposal stages complete and sample generation running under
`out/runlogs_resume_b3_b4/chain_score_resume.sh` (PID file in same folder). Separate v14_obgraph_py/v15_mrconcept_py copies
repair Python/JSON guidance and gate generation on accepted cards. User subsequently authorized GPU use during B4 CPU-heavy work (~19:05 local). The old dormant score-gated
waiter was replaced with `out/runlogs_v14_v15_py/chain_overlap.sh` (PID file same folder); v14 then v15,
two workers each, alongside unchanged B4. Registration appended before outputs. 30 CPU tests pass.
Exact queue/readiness details: [GPU_QUEUE-2026-10-14.md](../trickcatcher_linefacts/GPU_QUEUE-2026-10-14.md).

**GPU restart (~19:28 local):** user restarted GPU after both chains failed with HTTP 404. Resumed B4 from
2,783/2,793 exported samples via exact frozen relation replay and native verified hypothesis caches (all 133
tasks verified). Resumed v14 from 15/20 saved proposals, then v15. Current PID files remain in the same folders;
B4 script is chain_gpu_restart.sh. Protocol and queue document contain exact provenance, without secrets.

**Post-restart v14_py milestone:** 20 proposals complete, 5 shown cards on 3/20 tasks, gate opened;
generation running. Sparse coverage limits treatment interpretation; no scoring conclusion yet.

**Latest status:** v14_py/v15_py completed. B4 has two task-160 plain-hybrid samples in CPU sandbox
classification; no active Qwen request observed at check time, endpoint responds. B4 scoring remains.

**Latest checkpoint (~20:41 local):** B4 generation finished all 2,793 rows; original chain now evaluates on
CPU, then refs/score remain. Repaired v14/v15 analysis completed and committed in RESULTS §11.46 and
analysis/v14_v15_format_repair.md/json. Acceptance improved but neither primary comparison shows an advantage;
see tracked report for sparse graph exposure and false MR property reports. No held-out promotion.

**Final run closure (2026-10-14 23:56:47 local):** all B3/B4/repaired v14/v15 runs complete. B4 score initially
failed on missing task44, unchanged single-worker retry succeeded; full report at RESULTS §11.47 and
analysis/b4_v13_hyp_results.md/json (counts/costs/native attribution/provenance). B4 primary comparisons
favor controls; no promotion. Main queues have ended. New abstract FSM/spec-mutation direction remains a plan.
