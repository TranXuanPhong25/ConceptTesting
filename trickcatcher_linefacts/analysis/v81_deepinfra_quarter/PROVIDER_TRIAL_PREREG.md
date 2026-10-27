# One-prompt DeepSeek provider trial — 2026-10-27

User asks to try alternative DeepSeek providers, prioritizing low price, after
v81's task19 strategy completion was cancelled. That slot is terminal under
PREREG_V81's explicit no-resend rule, and remains unscored. This is a separate
transport/capability diagnostic using the exact frozen two-message prompt from
that canceled slot; it is NOT part of v81 HumanEval, does not fill task19, and
cannot be pooled into v81 scores.

Try only two current advertised providers, independently and in price order:
Relace/fp4 then Reka. Exact model deepseek/deepseek-v4-flash-0731, same frozen
messages, reasoning enabled, text response format, max_tokens131072 including
reasoning, temp.6/top_p.95, no seed, no provider fallback. One physical attempt
per provider; no retries/resends even on429, timeout, empty or incomplete output.
An explicit provider-shared-pool rejection may still be followed by the other
explicitly authorized provider, under the combined cap. 401/402/403 stops both.
Other generation/timeout failure is recorded unknown and the independent second
route may proceed. Preserve each unresolved reservation in total cap.

Live metadata captured 2026-10-27. Reka $0.05/$0.28 per M input/output, context
262144, max output131072, Reka quantization unverified. Relace $0.0475/$0.1568,
context1048576, max output943718, fp4 advertised. Exact provider payload must
match; require parameters. Conservative prompt envelope is 2*UTF8 bytes+4096:
total worstcase reserves below $0.061 for both calls. Combined hard cap $0.12,
no transfer from the existing v81 budget; prior unknown reservations separate.
No fresh transport smoke/hello call.

Record attempt receipt before each dispatch, then full raw SSE/finish/model/
provider/usage/cost receipt. Known bill required where usage exists; otherwise
retain reservation. Never represent absent usage as free. No source/scorer/task
change, public/native probes, private oracle, judge, v81 resume, or follow-on call.
Report provider/model package only; one selected prompt cannot establish quality
or rank providers scientifically. Freeze both prompts, payloads, endpoint
metadata and imported transport/config source before paid calls; independent
read-only review required.

Amendment A: freeze runner/PREREG/review/endpoint/old-v81 protocol hashes in the
plan and verify all before dispatch. Global 401/402/403 authentication/credit/
permission failures stop both routes. A provider-specific429 without generation/
usage may proceed to the second explicitly requested route while retaining the
reservation. Per-call reservations must remain under combined $0.12 cap.
