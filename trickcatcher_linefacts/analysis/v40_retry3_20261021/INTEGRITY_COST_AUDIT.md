# Independent terminal integrity and cost audit — PASS

Checked 2026-10-21T14:11:47.143659+00:00. Clean-context read-only reviewer; dedicated configured V4 Python, stdlib hashing/JSON/AST/importlib metadata only. No project imports, model/network/PUT/scorer/tests/quota calls. Only this Markdown and its JSON companion were written. Semantic scoring belongs to the parent audit.

## Frozen and prior artifact integrity

Exact inventories exclude only their own terminal_inventory.json. No missing, extra or changed entry:

|Root|Saved / actual entries|Exact|
|---|---:|---|
|d1|162 / 162|PASS|
|d1_retry_20261021|151 / 151|PASS|
|d1_retry2_20261021|4 / 4|PASS|
|d1_retry3_20261021|1404 / 1404|PASS|

generation_frozen.json exactly matches its complete intended prepared/requests/artifacts/events/arms/native/transport namespace: 1,258 entries. Terminal inventory covers 1,404 entries. These namespaces have different intended scope; neither count is a task/model-call count.

All 89 frozen source files, 8 prepared rows, Python 3.12.2 worker binary SHA, dependency metadata (networkx 3.4.2, jsonschema 4.23.0, httpx 0.27.2, jinja2 3.1.4), quota-guard SHA and approval sources/preparation canonical digest/file SHA match. preparation.json and approval.json are byte-identical to original d1. All 136 copied shared files match the historical originals. No frozen artifact was repaired or edited.

## Completion attempts, tokens, latency and raw origin

New retry3: all 72 expected slots have exactly one completion attempt, received response, raw HTTP envelope, artifact and event; all attempts received, all 72 HTTP200 and finish_reason=stop. No new unknown completion usage, transport failures, protocol failures or unattempted slots. No retries are evidenced.

|Arm|Attempts / responses|Known prompt tokens|Known completion tokens|Accepted / rejected|
|---|---:|---:|---:|---:|
|concept_adaptive|24 / 24|75,682|6,273|24 / 0|
|generic_adaptive|24 / 24|70,202|7,069|23 / 1|
|concept_committed|24 / 24|74,708|7,855|18 / 6|

New known usage = **220,592 prompt + 21,197 completion = 241,789 total tokens** from actual received usage fields. Every response binds to its stored raw body, identical text/finish/model/usage and request/wire input-token count. All 72 redacted body bytes hash exactly to raw_body_sha256, so these bodies needed no byte-changing redaction. Each saved origin is user_authorized_Qwen32B_endpoint and actual returned model label is qwen2.5-coder-32b-instruct. This establishes consistency with the authorized HTTP transport and recorded server labels; there is no independent server attestation or loaded-weight verification.

Completion latency sum 2,687.491s; mean 37.326s, median 36.328s, min 19.941s, max 75.107s. Controller started 13:20:19.468720UTC and ended complete 14:07:31.783595UTC. Latencies are client elapsed times, not GPU kernel time. Actual dollar billing is not emitted; do not invent a dollar cost.

Cumulative scope is original d1 + retry1 + retry2 + retry3, and original separate prelaunch metadata404. There are **73 consumed completion attempts, 72 responses, 72 known-usage attempts and 1 original unknown-usage attempt**. Known subtotal remains 241,789 tokens **plus the old unknown actual token usage**. Original failed attempt lasted 180.101s with generic transport_or_JSON_failure and no received saved body. Its tokenizer2359 is request size, not actual usage. Do not report cumulative total as zero, or as exactly241789; never reset the old unknown. Earlier20Oct readiness is historical outside this four-root ledger, so this is not an all-time API total.

## Decoder failures, preserving raw versus admitted output

All72 raw texts are parseable JSON; a stdlib structural check of every constraint present in the frozen reply schema finds71 schema-valid and1 schema-invalid. Recorded controller admission is65 valid/7 failed. No semantic correctness is implied by acceptance.

- E1__generic_adaptive__1: reply_schema; /queries/2/claim is missing. That claim was nested inside action, rather than at query level. Entire reply was rejected by the unchanged decoder.
- E3/E4/E5/E6/E8__concept_committed__2: replacement_commitment (5). These raw replies satisfy the JSON schema but submit disallowed replacement queries/later_queries.
- E7__concept_committed__2: premature_final_inputs (1). Schema-valid raw reply submits final inputs at turn2.

No incomplete_response, invalid_JSON, duplicate_JSON_key, nonfinite_JSON, claim_ids, queries_in_final, unexpected_commitment or other recorded decoder failure occurs. Raw rejected replies remain saved; admitted event reply is empty for failures. Importantly, a rejected committed turn2 reply does not erase previously committed turn1 later_queries: unchanged source executes the saved committed batch. Raw response counts and semantic opportunity counts must keep this distinction.

Raw texts contain118 queries,4 later_queries and50 final_inputs. These are raw proposal object counts; they are not physical native worker launches or all accepted actions.

|Episode|concept_adaptive T1/T2/T3|generic_adaptive T1/T2/T3|concept_committed T1/T2/T3|
|---|---|---|---|
|E1|valid / valid / valid|reply_schema / valid / valid|valid / valid / valid|
|E2|valid / valid / valid|valid / valid / valid|valid / valid / valid|
|E3|valid / valid / valid|valid / valid / valid|valid / replacement_commitment / valid|
|E4|valid / valid / valid|valid / valid / valid|valid / replacement_commitment / valid|
|E5|valid / valid / valid|valid / valid / valid|valid / replacement_commitment / valid|
|E6|valid / valid / valid|valid / valid / valid|valid / replacement_commitment / valid|
|E7|valid / valid / valid|valid / valid / valid|valid / premature_final_inputs / valid|
|E8|valid / valid / valid|valid / valid / valid|valid / replacement_commitment / valid|

All24episode-arm rows and all72turns are represented above; no row was dropped.

## Metadata and tokenizer accounting

|Owned root|Client GET /models|Separate preliminary GET /models|POST /tokenize received|Completion attempts|
|---|---:|---:|---:|---:|
|original d1|1|0|1|1 unknown|
|retry1|1|0|0|0|
|retry2|0|1|0|0|
|retry3|1|1|72|72 received|

Original separate metadata_prelaunch.json records1 additional failed HTTP404 GET. Within this explicit scope: 6 model-metadata GETs including that404,73 tokenizer POSTs,73completion attempts =152 recorded/request-attempt HTTP operations. Metadata/tokenizer requests total79, with preliminary retry2/retry3 GETs kept separate from frozen client metadata.jsonl. New retry3 alone has2model GETs +72tokenizer POSTs +72completion attempts =146 operations. This does not claim all requests across prior sessions or readiness probes.

Retry3 preliminary GET passed at13:18:10UTC (0.647592s), advertising exact alias qwen2.5-coder-32b-instruct, root Qwen/Qwen2.5-Coder-32B-Instruct-AWQ, context8192. Its saved body/hash and analysis evidence agree. Frozen client server.json records alias/context only; its received metadata log does not retain a second raw models body. Prior retry1 received metadata body was not saved, so alias versus context rejection cannot be reconstructed. Retry2 saved advertisement was7B/context16384, not retrospective proof about any other request. Model metadata is server advertisement, not independent verification of loaded weights.

All72 tokenizer reservations have durable result.json and received metadata entries, counts1971–4609 (sum220592). attempt.json remains reserved by design; that reservation state does not turn a completed tokenizer request into an unknown completion. Tokenizer counts alone are not billed/model usage; here received completion usage separately agrees.

## Native workers, reuse and request semantics

New native:126 durable worker attempts/126 launched=True/126 completed,63ordinary +63traced. All result hashes match;116 result statuses ok and10 exception. No failed launch, unresolved result, unknown launch reservation, filtered result or worker timeout. Exception results are completed PUT observations, not worker transport failures. Historical shared:32 launched/completed/ok,16ordinary +16traced, copied byte-identically. Those32 launches happened once in original preparation, not once per retry. Retry3 creates0 new shared workers; across original preparation plus new native there are158 distinct recorded physical launches.

The 24 arm ledgers record48round markers,103actions,48final entries. Actions:69 replay_input ok,13 replay_input refused by D1_tool_or_round_replay_cap,18 inspect_flow ok,3 inspect_data ok. The13 refused replay calls consume action slots but have no execution charge or worker. Successful replays69 +final requests48 =**117 semantic execution requests**. Every one yields native_checked=True;102 observed execution statuses ok and15 exception, with repetition through the cache. All48 final entries are accepted and string-deduplicated by the source.

Each execution request looks up ordinary and traced results:234 inferred worker-cache lookups,126 distinct worker jobs,108 cache hits. There are63 distinct source/input job pairs. Job identity includes source, entry, input literal, mode, validity code, limits, traced snapshot selections and protocol; ordinary/traced are separate jobs. Cache is shared across arms in the native namespace, separate from copied historical shared. Repeated/cached execution requests still consume logical execution slots. The code also charges recognizable malformed replay requests after early validation, but none is recorded here; D1 replay-cap refusals occur before this charge.

Following the frozen episode/arm order reconstructs all126 native keys exactly:

|Arm|Execution requests (replay + final)|Worker lookups|New launches attributed by order|Cache hits|Distinct jobs accessed|
|---|---:|---:|---:|---:|---:|
|concept_adaptive|44 (28 + 16)|88|58|30|76|
|generic_adaptive|43 (27 + 16)|86|44|42|64|
|concept_committed|30 (14 + 16)|60|24|36|52|

Cache-hit subcounts: CA12 same-arm repeats +18 first access already run by another arm; GA22+20; CC8+28. These numbers are source/ledger reconstructions, not emitted cache-hit counters; physical attribution depends on the fixed execution order and is not an arm-normalized cost comparison.

Explicit PUT-entry-call counter is absent. Frozen worker source calls the selected entry once after successful validity filtering/module load; all126new and32historical results are ok/exception with validity_checks=1, consistent with126new +32historical =158 inferred entry calls. Label this inference; do not relabel117 semantic execution requests,234 lookups or copied32 historical records as fresh physical PUT calls. Audit/scoring/regression activity outside these owned ledgers is outside this count.

## Prediction-before-tool ordering and launcher provenance

Frozen d1.py writes immutable raw+parsed artifact before session.act or final_inputs; committed round2 queries are copied from the already-saved turn1 artifact. All126 launched native jobs match an execution source/input with an earlier local artifact mtime. This supports prediction-before-new-tool-execution. Ledger results match post-action events and raw predictions remain frozen. A cache hit can reuse a worker whose timestamp predates that arm; this is expected reuse, not evidence of that arm predicting an already-seen result honestly.

Limits: artifacts use write-to-temp then atomic rename, with no fsync or signed/external timestamp. Local mtimes and immutable hashes establish retained file consistency and support source ordering, not crash/power-loss durability or an external clock proof. Structural queries have no native job timestamps; their ordering is established by frozen source and ledger/event consistency. No stronger timestamp or semantic prediction-accuracy claim is made.

registration.json launcher/prereg SHA values match run.py, PREREG.md and prelaunch audit.json. Registered old inventory SHA matches original terminal inventory. Launcher uses explicit retry3 root, lock, already-consumed status guard, old/frozen verification, approval binding, bounded72 single attempts and transport no-retry guard. Captured terminal state is complete; callback points to this owned retry3 namespace and callback.json records codex_queue returncode0. Queue returncode alone proves successful queue submission, not delivery/handling; parent independently handles the owned terminal callback. No new callback or controller was launched by this audit.

No MUSTFIX found in retained integrity or cost bookkeeping. Efficacy and concept utility require the separate saved-data semantic audit.
