# Preparation review — 2026-10-25

Status: **PREPARED, NOT RUN.** Owner source/engineering review only; no
independent agent review claimed. No paid SDK invocation, network completion,
new tool search on the experiment cohort, or v76 efficacy score was produced.
The sole launcher smoke check omitted --launch and exited 2 before env source.

Validation: **52 tests passed in 51.66 s: 40 inherited + 12 new.** Full suite:
`/tmp/concepttester-v74-venv/bin/python -B -m pytest -q -p no:cacheprovider trickcatcher_linefacts/pipelines/v76_ossmodel`.
Mock tests patch the SDK or inject FakeClient; the 3-case end-to-end blocks
socket connections, makes 27 fake calls, runs real native replay, freezes and
scores in a temporary directory, then confirms a second generate reuses the
freeze without new calls. No mock numbers are scientific findings.

Exact context preflight passes 297/297 actual historical saved messages, with
matched reconstruction and SHA-verified official Harmony tokenizer/template:
1,331,291 input tokens, max 9229 + 16384 = 25613 <=131072. Runtime check covers
all actual new requests. This does not claim knowledge of future feedback or
provider-specific billing/system wrappers before they exist.

Read-only checks: inherited prompt/schema/arm/loop/scorer source bytes match
v34; all parent file hashes recorded; assets match ASSETS.json. Model-independent
seed manifest has 264 verified files and excludes all LLM arm results. Production
output root does not exist. bash syntax check passes; launcher guard works.
Thesis outline cites existing reports with their version/denominator caveats.

Budget review: SDK retries=0; persisted per-attempt worst-case reservation
precedes dispatch; thread lock serializes paid calls, process lock rejects
competing clients, environment cap is clamped at $3. Known incomplete retries
are all charged (max 3). Missing usage/unknown transport charge retains the
reservation and blocks new paid calls, including after client restart. 403
settles as explicit pre-generation rejection at $0, pauses immediately; launcher
maintenance archives 403 logs and partial-arm ledgers outside the fingerprinted
pipeline while retaining charged attempts, requests, responses and cost ledger.
No source changes on resume. Supplementary reporting uses every receipt and
separates valid empty-final abstention from malformed-final/schema failures.

Limits/deviations from literal instructions: v34's unused global K=3 is set to
1 to make the already-K=1 fault-template protocol explicit. Transport/accounting,
seeding and launch wrappers necessarily change for the specified hard cap,
fresh LLM arms and safe resume; protocol/scorer code is untouched. Exact future
feedback requests cannot be materialized without model outputs, so preflight
uses all 297 frozen matched requests and every actual new dispatch has an exact
local token guard. Historical tool/ subfiles were not in historical freezes;
these are newly pinned after v31/v34 byte equality, not falsely described as
historically frozen hashes. Price estimate is a current snapshot, not a promise
of future provider availability. No cohort enlargement or automatic paid rerun.

Git whitespace check flags only byte-identical inherited whitespace in PREREG.md,
evaluate.py, gen_inputs.py, offline.py, v4_facts.py, v8_strict_est.py and one
historical tc_templates file; retained to satisfy the exact-copy requirement.
No new authored-file whitespace error. Normal staging is blocked by read-only
`.git`; delivery metadata uses writable `/tmp` and stages only the authorized
new files plus the one-line memory index addition.
