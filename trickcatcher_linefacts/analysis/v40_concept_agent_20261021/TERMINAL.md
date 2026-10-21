# v40 Astra D1 terminal disposition — incomplete transport, no model output

2026-10-21 user-authorized delayed launch, exact requested
qwen2.5-coder-32b-instruct. **One completion attempted, no response received;
71 remaining slots not attempted.** No concept, hypothesis, tool-selection or
selective-revision result is available. No relaunch, retry, output recovery, timeout
change, prompt/schema repair, paid fallback, training or benchmark expansion.

## Exact observed execution boundary

- Scheduled not before05:23:50UTC /12:23:50Vietnam; actual controller launch
05:23:51.190827UTC,1.190827s later. Saved quota54%, above stop15%; parent callback
fresh quota53%. Quota did not stop this attempt.
- Live `/v1/models` succeeded and matched exact served alias/context8192; root `/tokenize`
succeeded. The earlier prelaunch404 was no longer the blocker at scheduled launch.
- First slot `E3__concept_adaptive__1` had tokenizer count2359, below6144 prompt cap;
max output1536, total requested ceiling3895 within8192. This is preflight request size,
not observed received/billed input usage. Actual server weights/quantization unverified.
- One completion attempt reserved and failed after180.10103203100152seconds, recorded
`TransportStop: transport_or_JSON_failure`. No raw_response.json, response.json,
artifact or event exists. No completed body was persisted; HTTP status, socket exception
class, server receipt/queue/generation progress and actual tokens are unobserved.
- Client configured timeout180s and elapsed time is consistent with a timeout, but
the frozen client collapses httpx.HTTPError/ValueError/UnicodeError into one reason.
We cannot establish ReadTimeout versus connection reset/other transport subtype.
Raw persistence precedes JSON decoding in source; absence of raw is not a saved
malformed-model-JSON result. No schema or semantic decoder ran on a model reply.
- No server logs are available. It is possible the server processed the request despite
client failure; we do not claim zero server computation or zero token usage. Unknown
attempt remains consumed, never reset. No rejected model code/output exists to repair.

## All episodes and arms, full72-slot denominator

CA=concept_adaptive, GA=generic_adaptive, CC=concept_committed. Each has3turns.
`not_attempted` means no completion attempt, not abstention or failed input synthesis.

|Episode / authored fixture|CA|GA|CC|
|---|---|---|---|
|E1 /f02|3 not_attempted|3 not_attempted|3 not_attempted|
|E2 /f04|3 not_attempted|3 not_attempted|3 not_attempted|
|E3 /f06|T1 transport failed;T2–3 not_attempted|3 not_attempted|3 not_attempted|
|E4 /f08|3 not_attempted|3 not_attempted|3 not_attempted|
|E5 /f12|3 not_attempted|3 not_attempted|3 not_attempted|
|E6 /f16|3 not_attempted|3 not_attempted|3 not_attempted|
|E7 /f14|3 not_attempted|3 not_attempted|3 not_attempted|
|E8 /f13|3 not_attempted|3 not_attempted|3 not_attempted|

Totals24episode-arm rows,1 failed transport attempt,71 not_attempted,0 received
responses/parsed artifacts/events,0 model queries/observed replays/final inputs.
All concept content and hypotheses remain authored inputs to the diagnostic; none
is a Qwen-produced finding. No model abstention, prediction, revision, contrast or
counterexample can be reviewed. E7 correct/masked control and E8 ambiguous control
were never attempted. Only the E3 initial packet was placed in the attempted request; server receipt remains unknown;
the injected revealing row J0 is prepared but is not delivered until turn2, which
never occurred. Shared rows for E1/E2/E4/E5/E6/E7/E8 were never placed in a model request; E3 B0 was in the attempted packet, delivery unknown.

Raw/gated input yields, correctness/false flags, novel inputs/tasks, concept vs generic
utility and adaptive vs committed effects are unmeasured. Do not interpret0 observations
as0% precision/recall, a negative semantic finding or failure of all8episodes.
Supplied-concept capability gates cannot be evaluated; no efficacy/promotion claim.

## Requests, usage and workers

- Task completion attempts1; received0; known-usage attempts0; unknown-usage attempts1.
Recorded known token subtotal0/0 **plus one unknown attempt**, not actual total0/0.
Tokenizer2359 and output cap1536 are not usage. Actual dollar cost unobserved.
- During delayed run:2 received metadata requests (`/models`, `/tokenize`). Separate
prelaunch metadata request1 failed404. Earlier20Oct readiness metadata is historical,
not included as a received task response. Tokenizer reservation ledger stays reserved
but durable result/count and metadata-received record exist; no bookkeeping repair.
- Model-requested native workers0. Shared CPU preparation32ordinary/traced launches,
all32 completed/ok,16native-agreement observations. Explicit PUT-call counter absent;
32entry calls inferred from worker source/status, not an emitted counter. Regression
tests are additional CPU controls outside the main task ledger. No worker failures
or unresolved reservations in shared preparation. CPU12/12 does not establish model success.

## Integrity and independent audit

Independent clean-context read-only v40_terminal_audit PASS:89source hashes,8prepared
hashes, approval source/canonical preparation/fileSHA, configured Python3.12.2 binary,
dependency METADATA, quota guard and delayed launcher hashes all match. Dedicated
versions networkx3.4.2/jsonschema4.23.0/httpx0.27.2/jinja2 3.1.4. No tests/workers/network
or model calls by audit. Parent source verification also passed before saved-data scoring.

No generation_frozen.json exists because generation did not complete. Separate
terminal_inventory.json captures162files and matches exactly, no additions/removals/drift.
InventorySHA2567046515ee6c05cc2ad8f2c355e44bc5a554f92b4a27466898d5e74016f32bcad.
Native raw artifacts, source/prompts/schema and one unknown completion attempt unchanged.
External scorer corrected transport-attempt-without-artifact labeling to distinguish
1failed from71unattempted, and no-received-output semantics to “not measured”. This is
analysis-only labeling, not recovery or rescoring of a model output.

Delayed controller exited after diagnostic status stopped. Its process returncode0
does NOT mean experiment completed: d1 controller catches TransportStop and records
status. Callback `codex queue` returned0; this owned callback was received in the
original conversation. Old CLI active-writer resume failure did not recur as launch
mechanism; the actual scheduled Qwen attempt happened. No active controller or auto retry.

See incomplete_status.json, TERMINAL_AUDIT.md and unchanged runtime status/attempt
ledger. Earlier REPORT.md/prepared_status.json/SCHEDULE.md describe readiness/history.
Future changes to timeout/error detail/transport require separate authorization and
prospective protocol; nothing was repaired or relaunched in this callback.
