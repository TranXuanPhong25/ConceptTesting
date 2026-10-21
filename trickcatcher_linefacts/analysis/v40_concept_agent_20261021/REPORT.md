# v40 Astra concept-agent D1 — implemented, audited, waiting for endpoint

**Superseding terminal disposition2026-10-21:** scheduled run attempted1completion,
received0responses, stopped transport after180.101s;71slotsnotattempted. Current
metadata did succeed at launch; earlier404 below is historical. No model semantic
result. Read [TERMINAL.md](TERMINAL.md) and incomplete_status.json.

User authorized Astra improved catalog + new mechanism tests, then exact
qwen2.5-coder-32b-instruct on their supplied endpoint. User resumed2026-10-21; live
Codex5h quota100% at first check, stop threshold15% retained. Old scheduled CLI wake
did fire but exited on active-writer thread conflict; no model task was launched.
This turn continued manually from preserved checkpoint, without resetting attempts.

Astra completed DESIGN.md and7-concept catalog in analysis/astra_concept_design_20261020.
Concept vocabulary, input dimension, spec binding, empirical measured gap and falsifiable
implementation hypothesis are distinct. Catalog scope: occurrence conservation,
membership inclusion, quantified decision, eligible contribution, order policy,
eligible selection, defined outcome. This is proposed operational clarity, not proven
improved bug detection. Prior art matrix includes v7/v13/v17–19/v21/v28/v30/v32/v33/v35/v36;
active replay already occurred in v28, so enabling tools is not novelty.

Fresh best-v7 copy v40_concept_agent + explicit v30 tools/v23 fixture ports implements
8 seen authored episodes ×3 arms ×3 turns =72 task slots. Compare concept_adaptive,
generic_adaptive and concept_committed. Same original spec/code/base/fallible H/raw
observations; concept arms add allowlisted relation/binding/recomputed finite gap.
No catalog example/expected answer or evaluator labels enter model packets. Deliberate
false/correct/ambiguous claims test calibration and selective revision. Native tool
output contains observations/limitations, never oracle verdicts. Claim status never
hard-gates final input; predictions are durable before executing queries.

At most6 actions/4 in-round replays/2 final inputs per arm;16 shared +96 query +48 final
native requests <=320 ordinary/traced launches. Single attempt/no retry per Qwen slot;
prompt<=6144/output<=1536/context8192, usage-bound tokenizer count and exact model checks.
Source/prepared/dependency/worker-binary/guard hashes freeze; controller lock and durable
worker/transport ledgers preserve unknown attempts. Model response raw hashes and
redacted raw text retained even on protocol rejection. Resource/domain errors unknown.

Independent reviewer withheld approval, required concrete feedback/raw/accounting/
contract fixes, then conditionally approved final frozen preparation. Final CPU12/12
passed, including full72 scripted control responses and resume (not actual model turns).
Main CPU preparation16 native observations/32 durable worker launches, all completed.
Source and frozen prepared rows verify. No original frozen version/vendor/Kaggle edits.

**Current blocker:** today's prelaunch metadata GET /v1/models returned HTTP404. No
response body was exposed or saved (endpoint secrecy);404 alone does not establish
whether the tunnel is offline or route unavailable. Yesterday's separate metadata check
did identify exact model/context8192, but does not certify today's availability. Current
main status prepared_waiting_endpoint; task attempts0/responses0/unknown task usage0,
all72 slots not_attempted, not72 failed generations. Prelaunch metadata attempts1 today,
0 task transport/tokenizer requests. No Qwen token usage or dollar cost from this run.
Actual semantic revision, query adaptation, discovery, novelty and false claims are
unmeasured. We have requested a live endpoint asynchronously; no automatic retry,
substitute provider, training, benchmark, held-out or efficacy promotion.

E3/E6 already have supplied exposing rows; E1/E2/E4/E5 form the no-supplied-witness
discovery subset. Novelty subtracts all task-shared base/injection rows; stricter global
literal union also reported. No historical new-input/task claim unless separately
audited. Capability alone is insufficient: generic parity => no incremental concept
signal; committed parity/no actual feedback opportunities => no adaptivity claim. No
larger n/K to rescue failure. These remain seen toy fixtures, not generalization.

Next authorized action once endpoint is live: unchanged source verification, quota
check, exact metadata/tokenizer checks and one detached `d1 run --online`; inspect
status/attempt ledger first. Approval and preparation under
out/pipelines/v40_concept_agent/humaneval/d1; endpoint only in environment. Independent
actual-output review and post-freeze oracle scoring are required after any task output.

See prepared_status.json for all24episode-arm rows/72slots, CODE_REVIEW.md,
CPU_TESTS.log, and source PREREG.md. This report records readiness and a transport
availability blocker, not completion of the model experiment.
