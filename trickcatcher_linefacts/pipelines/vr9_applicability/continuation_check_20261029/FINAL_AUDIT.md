# VR9 completed-run independent audit

Audit passes for integrity, replay, call budget and terminal lifecycle. The
registered engineering repair works, but the completed diagnostic provides no
bug-detection gain. No model/API calls or PUT execution were made by this audit;
all checks read frozen source, saved requests, receipts and native outputs.

## Integrity and replay

All **80 source, 63 parent and 788 generation file hashes** match. Forty-eight
strategy invocations have the exact inherited request-body key, response,
strategy source and candidate pool for the registered routing. Twelve
strict/generic controls exactly match the archived assertions, receipts and
selected inputs. Round1 assertions remain present in every hybrid output.
Selected inputs are valid, unique and absent from round1, with at most two per
strategy and four per task; the 20-assertion cap is preserved.

The controller has completed all six tasks. PID 49687 is absent from `/proc`,
and the existing exclusive run lock can be acquired without blocking. Five
unique attempts have received receipts, with zero failed/unresolved attempts,
under the cap of 12. Every fresh request is a repaired-arm expected-output
request with max_tokens 1024 for `qwen3.5-27b-awq`, within context 8192.

## Physical calls and historical cost

Fresh cost is **5 completions / 3,742 tokens**: 2,918 prompt + 824 completion,
with no unknown usage. Nine logical repaired-arm uses share those five physical
receipts because four retain/applicable requests are identical. There were no
new strategy completions. The 71 logical round2 calls include replay and must
not be counted as 71 newly paid calls.

Historical reuse is reported separately: six round1 and sixty reference calls
account for 30,099 inherited tokens; twenty reused physical round2 receipts
account for another 18,108 historical tokens. These inherited subtotals do not
include every earlier shared preparation cost. Independent summation from
receipts reproduces every reported subtotal.

## Native delivery and actual outcome

| Arm | Novel valid selected inputs | Selected bug-exposing calls | Ref bugs / false-alarm tasks |
|---|---:|---:|---:|
| strict | 19 | 2 | 6 / 0 |
| retain | 24 | 1 | 6 / 0 |
| applicable | 24 | 1 | 6 / 0 |
| generic | 23 | 2 | 6 / 0 |

All selected inputs survive into the final valid-input classifications, and no
arm has missing expected outputs. Forty-eight round1/final classification
artifacts show zero trace errors. Their 144 recorded capture errors are all
`AssertionError`: the capture worker executes assertions against the buggy PUT,
records the call, then records assertion failure. These are neither transport
failures nor tracing failures.

Only applicable skips task51's locally refuted membership-disagreement target
and routes to the registered generic strategy pool. Retain preserves the old
semantic pool and retains four valid non-hits. However, **none of task51's four
selected calls exposes its bug**, in either repaired arm. Literal inspection of
the sealed pools finds space-bearing strings in 22/200 semantic and 6/200 generic
candidate occurrences; no new oracle labels or candidate execution were needed
for this observation. The four-input selection still loses relevant variation.

There is also a registered selection downside: task101 has two selected exposing
calls under strict/generic and one under retain/applicable. Thus the added valid
inputs do not imply better bug-targeted input selection.

Scores independently reconstructed from saved native grading match RESULTS.json:
all ref arms confirm six tasks with zero false-alarm tasks. Round1 already
confirms all six, so this is the documented ceiling. Under the own-output o0
oracle every arm confirms five tasks; strict/retain have false alarms on tasks
98 and 101, while applicable/generic additionally have a false alarm on task51.
Ref abstentions decrease from two to one for the repaired arms; that is not an
additional detected task.

This development-informed replay verifies routing and retention, with no evidence
to promote the method or expand automatically to a larger run. Detailed counts,
receipt accounting and immutable output hashes are in FINAL_AUDIT.json.
