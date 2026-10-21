# Second explicit v40 retry — 2026-10-21, before requests

User says “thế thử đi” after the model/context preflight stop. First perform one
read-only GET /models and preserve a secret-safe response plus raw body hash in
a fresh metadata_probe namespace. No canary/token generation. Identify exact
alias and max_model_len separately. Stop on HTTP/transport/parse error or frozen
model/context mismatch; never alter the old treatment or silently accept another
model/context. Do not retry this metadata attempt automatically.

If metadata matches exact qwen2.5-coder-32b-instruct/context8192, one fresh
d1_retry2_20261021 may run the unchanged frozen8episode/3arm/3turn diagnostic
after explicit-root launcher audit. Up to72fresh single-attempt completion calls;
original1unknown attempt plus first retry0 gives cumulative ceiling73. Reuse
byte-identical historical prepared/shared/approval data, not new shared workers.
Frozen source, prompt, schema, decoder, timeout180s, seed, order and caps unchanged.
Extra one metadata GET is separate from the frozen client's own metadata request.

Codex quota<=15 stops. No automatic retry, output repair, unknown reset, paid
fallback, training, benchmark or held-out. Preserve all prior inventories. If the
preliminary metadata gate fails, no diagnostic controller is launched, all72 new
slots are not_attempted, and report actual server metadata without efficacy claims.
Endpoint only in process environment, never files/logs. Report new/cumulative
requests/tokens/unknown usage and historical vs fresh native workers. Clean-context
audit and saved-data scoring as applicable; commit/push own analysis/memory main.
