# Delayed v25 transport probe —2026-10-17

User authorized "10 nữa thử lại" after the two-call transport proposal. Fixed due
2026-10-17T14:08:06UTC (21:08:06Vietnam). New probe namespace, original v25 source/
serialization/attempts untouched. Tool imports frozen interfaces read-only; no paper
reimplementation or vendor edits. Prereg before freeze/network in central PREREG.

Exact original f02 metadata prompt/seed/model/temp/top_p/max_tokens768. Plain then
same payload with guided_json. Max2 completion requests,1 attempt each; metadata
models/tokenize once each, no retries or repeated liveness calls. Plain transport/
protocol failure blocks guided. Schema-invalid but usage-valid received plain text
can proceed to guided because this is transport diagnosis. No diagnostic5 chaining,
full comparison/benchmark/real20/held-out/paid calls. Fixed sequential order cannot
isolate a causal guided-decoding effect; no internal server logs are available.

Clean-context code audit confirmed lock/reservation cap, no retry of interrupted
attempts, no network before deadline and frozen script/source verification at due.
Found/fixed deadline race and JSON-escaped/nested content secret leakage before
freeze. Redaction handles decoded JSON strings/keys and scans encoded nested strings;
conservative omission when necessary, original body SHA retained and bounded body
stored only after sanitization. Actual text normal form is preserved when no secret
redaction is needed. HTTP status/latency/type and known/unknown usage remain separate.

**5 authored CPU httpx controls pass in0.19s**: same payload except guided flag;
plain error blocks guided and keeps sanitized body/status; interrupted reservation
never resends; tokenizer metadata mismatch blocks completion; direct/nested escaped
secrets suppressed. These are local HTTP fixtures, not Qwen performance. Final
read-only audit reports no remaining blocker for this tiny transport scope.

Detached controller PID1277567 scheduled with exclusive lock, endpoint env-only,
self/source/protocol hashes frozen. Same-thread terminal callback queued by controller
after probe; old v25 callback remains handled. Runtime status under
out/transport_probes/v25_20261017_140806/status.json. No network performed at schedule
verification; all actual results pending due time. If deadline metadata unavailable,
record failure and stop; never reset or retry automatically.
