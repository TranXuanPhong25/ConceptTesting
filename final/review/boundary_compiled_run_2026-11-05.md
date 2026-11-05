# Repaired plain + compiled BVA — boundary/all44 live run

Terminal update2026-11-05:COMPLETE at09:51:35UTC (16:51:35Vietnam),controller
199379exited;44/44input and result records. Plain840valid novel inputs/2detected
PUTs(HumanEval99/PUT0,124/PUT0);BVA67valid novel inputs/0detectedPUTs. Independent
read-only aggregation of all44result files matches the summary. All44inputfreeze
hashes and77source/datahashes match. No new model/native calls for this audit.

Tester99received/1unknown physicalattempt,178554known tokens;unknownhistory
preserved. BVA44selection/11contextlogicalcalls,30selectedboundaries,68retained
inputs before the oracle,67valid novelafterwards. Taskstatuses:18no_applicable,
15generated,3uncertain_binding,2no_inputs,3invalid_selection,2already_covered,
1invalid_generation. Cache40hits/3582executions of3622records;keepalive2received,
28known tokens separate. Writerusage in summary is historical sharedcohortcost,
not freshgenerationcost. No call/inputmatched efficacyclaim or posthocretuning.

Earlier launch/progress snapshots below are historical and superseded.

User supplied the current endpoint and requested running the repaired methods.
Run directory:`final/out/boundary_all_plain_bva_compiled_20261105`.

Dataset is the actual development_groups.py boundary/tierall export:44tasks,
one original saved base-passing representative PUT/task,cohort hash
437c5af3e92d4fcbeb9c2c408ad537adbbbd6971a2d68666cba090f72de70885.
All44task inputs regenerate because both methods now use the shared named-value
encoder and BVA uses compiled targets/context completion. No literal-generation
checkpoints are imported as outcomes of this changed method.

Arms plain,boundary;input cap20perarm/task;max4boundaries;selection temperature0,
context/plain temperature0.7,max2048completiontokens/call,context8192. Maximum
132logicalcalls;code-only/scalar/no-applicable paths can reduce this. Unchanged
bounded transport retries and separately recorded20minute keepalive.

Corrected pinned HumanEval+v0.1.10reference provider,full all-task generation
freeze before scoring,two independent stability repeats,timeout3seconds. Shared
execution cache reuses only compatible runtime/source/input/expected identities.
No generation use of hidden plus inputs,reference source or evaluation outcomes.
Call counts differ between methods;do not interpret equal input caps as matched
request cost. Unknown binding/construction/resource outcomes remain explicit.

Prelaunch:165engineeringchecks pass;44reference/spec/domain and type/template
checks pass;servedQwen3.5-27B-AWQ/context8192and tokenizer13verified.77source/data
hashes frozen before calls. Prior runs/source cohorts preserved.

Detached controller199379is running. First fresh plain response onHumanEval0
received,finishstop,20records with arguments/concept_id fields,1959known tokens.
BVA selection request for the same task started. No scored result yet.
Use output/status.json,stage_events.jsonl,calls receipts and controller.pid for
live state;this is launch evidence,not successful completion of44tasks.

Progress snapshot2026-11-05 09:07UTC (16:07Vietnam):controller199379alive and
statusrunning;7/44tasks have saved input batches,task20(the eighth task)is in
BVA selection.15fresh responses received;one physical plain/task10 attempt lost
connection(RemoteDisconnected,0partial characters,usage unknown),then succeeded
under the existing bounded retry policy. The unknown receipt remains archived;
do not report zero unknown usage or count it as another successful response.
No engineering crash observed;all77frozen source/data hashes match.

Completed-task input counts before the shared oracle:plain138,BVA2. BVA task
statuses are4no_applicable_boundary,2generated,1uncertain_binding. Both generated
cases use compiled scalar targets without a context call. These are generation
observations,not valid-input or bug-detection results;all44task generation must
finish and freeze before reference/PUT evaluation. No method tuning or duplicate
launch performed.
