# Independent code/contract audit and CPU verification

Clean-context reviewer v40_code_audit, read-only: no tests/native/model/network calls.
Final conditional PASS for preparation file SHA256
89fb756eda3d472dc12afd1cb924c7581e6a0da897ae64b67802cacc248e4af0.
Condition: live exact Qwen32B/model/context/tokenizer plus quota>15%; no efficacy claim.

Initial audit withheld approval and identified MUSTFIX:
- compact feedback dropped inspect_data facts and scope/limit metadata;
- unrepresentable action normalization could yield string and crash dispatcher;
- usage/model-rejected completions lost raw response content;
- cached valid response could leave usage reservation unknown after crash;
- published tools included check_path while D1 forbids it;
- failed reply did not expose its typed error on the next turn.

All resolved before model calls/freeze. Raw response persists with secret redaction and
raw-body hash before protocol checks. Durable worker reservations prevent unknown
reexecution; successful cached responses reconcile usage without resending. Three-tool
protocol retains FULL literal/action/type/size bounds, including UTF8 bytes, nodes,
depth, items and integer limits. Approval binds exact source/preparation hashes;
runtime verifies source/dependencies/guard before every turn.

Stable final CPU suite:12/12 passed4.02s (see CPU_TESTS.log). Tests include public/private
projection, independent fixture oracle values, injected actual native outcomes, all
72 authored response slots, identical raw controls, committed query replay, completed
resume/no duplicate requests, data feedback, invalid siblings, unknown worker attempts,
usage mismatch raw retention and cached usage recovery. No actual model calls in tests.
CoverUp venv lacked networkx; dedicated configured V4_PYTHON has required dependencies
and was used for final tests/preparation. No package installation or vendor changes.

Main prepared observations:16 shared base/injection rows,32 ordinary/traced durable
worker launches. All32 completed,16 usable native agreements. Regression workers in
temporary test directories are additional CPU-only work outside that task ledger.

Prepared data and source are frozen. Endpoint metadata GET /v1/models returns404;
task attempts/responses0, all72 model slots not_attempted. No model/tokenizer readiness
or semantic performance inferred from CPU tests. Actual replay/revision/novelty/false
claim metrics remain unmeasured; no next-stage automatic expansion.
