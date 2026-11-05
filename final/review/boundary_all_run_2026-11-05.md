# Plain + BVA on the complete boundary group

**Corrected rescore complete:**same44taskinputs scored with HumanEval+v0.1.10
references give0PUTdetections for both arms (valid inputs595/121unchanged).
0newmodelcalls;original1,336artifactfilesunchanged. The old raw3vs3numbers below
are from the original HumanEval oracle and must not be reported as true bug counts.
See [rescore report](boundary_evalplus_rescore_2026-11-05.md).

**Postrun oracle audit:** unique detections97(plain-only)and140(BVA-only)are
false alarms from original HumanEval canonical solutions. Corrected HumanEval+
references agree with PUT outputs in both cases/two repeats. Task140plain also
proposed the same case but all20records had malformed singleton args. Raw3vs3
counts below remain artifact observations,not3confirmedbugs per arm. Shared44/
122not audited here. See [unique-task audit](boundary_unique_task_audit_2026-11-05.md).

## Terminal result — 44/44 complete

Controller170173and supervisor168654finished successfully(exit0). All44task input
and result checkpoints exist.44generation-freeze hashes and all68source hashes
verified;no source drift. The running/waiting snapshots below are historical.

| Arm | Valid novel inputs | Detected PUTs/tasks | Logical calls |
|---|---:|---:|---:|
| plain |595|3/44|44|
| boundary (BVA) |121|3/44|70|

Both detect HumanEval44and122. Plain-only:HumanEval97. BVA-only:HumanEval140.
Each task has one representative PUT,so total union is4PUTs. Equal raw counts do
not establish equivalent effectiveness;the valid yields and model-call budgets
differ. This is development data including all script tiers,not heldout efficacy.

BVA statuses:21generated,17no_boundary,5no_inputs,1invalid_selection. There are
114requests/114responses,0unknown;16received requests are imported from smoke,
98are fresh. Total187,202known tokens includes32,785historical imported tokens;
fresh generation cost154,417known tokens. Keepalive is recorded separately.

Execution cache:3,178input/repeat records,486hits,2,692native executions;
0uncached outcomes,0corrupt entries,0missing receipts. Both stability repeats
remain represented. Source cohort,selected representatives and run settings are
unchanged;no failed method case was repaired or silently replaced after scoring.

Detailed artifacts:final/out/boundary_all_plain_bva_20261105/REPORT.md,
modular_summary.json,generation_frozen.json and per-task result/oracle/input files.

Latest2026-11-05: user supplied a refreshed private endpoint and explicitly
requested background execution of the boundary group. Modelqwen27/context8192
and tokenizer13verified;all68sourcehashes match. Existing supervisor168654started
detachedcontroller170173. Both schedule_status/status say running;controlleralive
and freshHumanEval2/plainattemptstarted verified. The6savedinputtaskfiles at
launch are reused smoke checkpoints,not6newcompletions. No all44score yet.
Earlier waiting/404 lifecycle paragraphs below are historical.

User corrected the earlier smoke-only scope and pointed to
`final/development_groups.py`. Use that script's boundary selection with tier
`all`, rather than the6PUTsmoke subset. The earlier smoke remains a separate run.

Actual export command:

```bash
final/.venv/bin/python -m final.development_groups export \
  --group boundary --tier all \
  --output final/out/development_groups/boundary/all
```

## Frozen dataset

-47primaryboundarytasks;44have ready representatives according to the existing
  inventory/selector. HumanEval65,127,163have no ready representative.
-44tasks,one saved base-passing representative PUT/task. PUT2for task83,PUT1for
  task103,PUT0for the remaining42tasks. No new PUT generation or substitutions.
-Subset hash:437c5af3e92d4fcbeb9c2c408ad537adbbbd6971a2d68666cba090f72de70885.
-Parent hash:2a32bae531c339f2e403d748984ce5775734bdd8fd0fc9a02620392fbc23c7ed.
-Exact task IDs and owner IDs:output development_groups/boundary/all/selection.json.
-This selection includes all script tiers,including check;it is development data,
  not untouched validation after this run.

## Execution configuration

Output:`final/out/boundary_all_plain_bva_20261105/`. Same plain+BVA methods,
Qwen3.5-27B-AWQ/context8192,inputbudget20/arm/task,default seeds/tokens/temperatures
and2reference/PUT repeats. Shared native cache:`final/out/execution_cache/`.
Reference execution follows the new all44taskgeneration freeze.

The6smoke task records exactly match corresponding all-group records. Their
generation-only checkpoints and16complete requests were imported after verifying
source/model/settings/task/cohort/inputfreeze integrity:122files with recorded
hashes. No reference/evaluation artifacts were copied into the generation flow.
Do not call these16requests fresh or charge their32,785tokens twice;record them
as historical reused generation.38tasks still need generation,with at most114
fresh logicalcalls. Shared native results are reused only after the global freeze.

No method/template/parser changes are made based on the negative smoke result.
This is the user's scope correction,not automatic sample expansion for efficacy.
The6tasksmoke and its observed format/target failures remain preserved.

## Current lifecycle

Stored supplied endpoint currently returns HTTP404on/models. Frozen manifest,
run_config,readiness,launch command and imported checkpoints are prepared.
Detached supervisor PID168654is alive,statewaiting_for_endpoint;checks metadata
every60seconds,then verifies model/context/tokenizer and source hashes before
launching the frozen command. It reads the private endpoint config outside repo;
URL/keys are never copied into this report,run metadata or logs.

No all-group benchmark controller or fresh completion has started yet. Existing
6inputtaskfiles are imported checkpoints,not progress on38newtasks. Lifecycle:
output/schedule_status.json;controller status will appear in output/status.json.
The user has been asked to restore the notebook or provide a current endpoint.
