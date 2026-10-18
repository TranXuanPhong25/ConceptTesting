# Fresh transport retry —2026-10-18

User explicitly requested another attempt. Fresh run v25_20261018_040624 started
04:08:10UTC/11:08:10Vietnam, original run/probe kept immutable. Same original f02
plain/guided payloads, max2 single-attempt completions and max2 single-attempt metadata
requests. Code audit found no blocker;7 local HTTP/privacy controls passed. A small
new persistence adapter masks bare/encoded tunnel hostnames; frozen old utility and
semantic interfaces/prompts remain untouched. No automatic new run-id after failure.

**Actual result:** only GET /v1/models attempted, HTTP404/ERR_NGROK_3200. Sanitized
body reports endpoint offline. Latency0.194394049s, total probe0.197042s. Preflight
stopped before tokenizer, plain or guided; no results.json/completion artifacts.

|Measure|Actual|
|---|---:|
|Metadata HTTP attempts|1|
|Tokenizer requests|0|
|Plain/guided completion attempts|0/0|
|Unknown-usage completion attempts|0|
|Model usage records|0; no completion sent|
|PUT/predicate workers|0|

There is no model/schema/semantic evidence and no paired comparison. The generic
metadata state http_error_usage_unknown is not an uncertain generation request.
Earlier diagnostic5 eight unknown completion usages remain separate. Gateway reports
endpoint offline; server logs are unavailable, so GPU/model/backend cause is unknown.

Read-only verifier confirms frozen old script+new wrapper hashes, unchanged74 v25
sources/prepared-data identity/770 frozen artifacts, both old runs' analysis-time
transport/status/report hashes, exact payload pair and single-attempt stopping. New
error record contains no bare tunnel hostname. Body was not copied into analysis;
only gateway code and sanitized offline message are used. No endpoint/hostname/key
in tracked output. No worker/model/network calls during analysis. Old raw/source
files were neither repaired nor reset.

Callback handled, no active retry or diagnostic5/comparison/benchmark/paid expansion.
Endpoint must be online again or replaced before another authorized attempt.
[Verifier](v25_transport_retry_results.py), [safe evidence](v25_transport_retry_results.json).

Independent clean-context terminal audit by v25_probe_audit confirms coverage/cost
interpretation, new-artifact privacy guard and unchanged hashes of both old runs.
Reviewer read-only; no endpoint/workers or source edits.
