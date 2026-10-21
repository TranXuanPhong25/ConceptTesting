# v40 explicit retry — stopped at model/context preflight

At2026-10-21 12:22:33–34UTC (19:22Vietnam), the new user-authorized retry
received `/models`, then stopped with
`TransportStop: requested_model_or_context_unavailable`. The unchanged frozen
client requires an entry with exact ID `qwen2.5-coder-32b-instruct` and
`max_model_len == 8192`. That combined check failed. The metadata response body
is not retained by this frozen client; evidence cannot distinguish absent model
alias from absent/mismatched context metadata or identify the actually served model.
This was not another completion timeout, JSON/schema failure, or semantic failure.

No tokenizer or completion request was sent; all72slots are not_attempted. No
Qwen concepts, behavior, hypotheses, predictions, tool choices, revisions, final
inputs or abstentions exist in this retry. Capability, concept utility, adaptivity,
input/assertion yield, false alarms, calibration and novelty remain unmeasured.
No model-authored expected outputs are evaluated.

|Episode / fixture|concept_adaptive|generic_adaptive|concept_committed|
|---|---|---|---|
|E1 /f02|3 not_attempted|3 not_attempted|3 not_attempted|
|E2 /f04|3 not_attempted|3 not_attempted|3 not_attempted|
|E3 /f06|3 not_attempted|3 not_attempted|3 not_attempted|
|E4 /f08|3 not_attempted|3 not_attempted|3 not_attempted|
|E5 /f12|3 not_attempted|3 not_attempted|3 not_attempted|
|E6 /f16|3 not_attempted|3 not_attempted|3 not_attempted|
|E7 /f14 correct/masked|3 not_attempted|3 not_attempted|3 not_attempted|
|E8 /f13 ambiguous|3 not_attempted|3 not_attempted|3 not_attempted|

New run:1received metadata request,0tokenizer/0completions/0model tokens attributable
to completion requests/0new unknown-usage attempts. Original delayed run remains
1failed completion with unknown actual usage,0responses. Cumulative completions
still1attempt/0received/1unknown; cumulative tokens/cost remain unknown, not zero.
The original2received metadata requests and this1received request total3; the
older prelaunch404 stays separate. Original tokenizer2359 is size, not billing.
No new native workers, model-requested workers or actual observed inputs. The136
copied shared files describe16historical CPU observations/32completed launches;
count them once across runs, not as32additional workers. Explicit PUT counter is
absent;32entry calls are inferred from worker source/status, not emitted counts.

Quota93% atlaunch, stop threshold15%; quota did not block. Prelaunch clean-context
audit PASS verified89source/8prepared, approval/dependencies/guard and old162-file
inventory. Old artifacts/source/attempts unchanged. New151-file terminal inventory
matches exactly, SHA256
`3c3474d5ae6f6ec8dbfabbb5c16edf8f79d3f646c59178b9ff6a569043bd3398`.
No generation_frozen.json because generation never started. Source/prompts/schema/
180s timeout unchanged; no repair, retry, extra model probe, fallback, benchmark,
training, held-out or paid calls. No active controller or automatic relaunch.

Saved-data scoring reused the old scorer with an explicit new root and analysis
output directory in a separate Python process; no frozen file edit or PUT/model
calls. All24rows/72slots appear in incomplete_status.json. Shared-worker totals in
that file describe historical copies, not newly launched processes. Raw Qwen origin
is preserved; there is no Luna probe/result in this retry. Independent terminal
audit PASS in TERMINAL_AUDIT.md. Terminal reviewed in this foreground turn;
callback queue returned0, which alone does not establish callback receipt.


Callback received and reverified at12:25:23UTC: already handled in the foreground.
Old162/new151 inventory files,89source/8prepared/approval/dependencies verified
again. All72notattempted unchanged; no repeated scoring, Qwen or worker call.
Quota91%>15%. Callback receipt is now directly observed, independently of the
queue returncode. See callback_reverification.json; no duplicate launch.
