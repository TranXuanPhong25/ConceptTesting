# V85 context-fit continuation — 2026-10-28

Registered before new completion calls, after observing an execution failure,
without loading target references or scoring either arm.

Parent: v85_retrievalhybrid/comparison_live_1. All113 preparations completed;
509 completions received,6 complete task pairs,7 v11/6 retrieval hybrid rows.
Task125 retrieval strategy correction failed preflight:4964 prompt tokens plus
4096 requested output exceeds8192. The preceding strategy was truncated at4096.
Parent is terminal; its source, outputs and failure receipt remain unchanged.

Single protocol change, applied to both arms and shared oracle requests:
effective_max_tokens = min(requested_max_tokens,8192-prompt_tokens), where the
server tokenizer counts the complete unchanged messages with thinking disabled.
A prompt leaving no output space still stops the run. Record requested/effective
caps and hash the actual transmitted body. No input truncation, model change,
extra strategy attempts, transport retry, task exclusion or reference feedback.
This can shorten output on long requests; report every adjusted request by arm.

Continue the same113/K1 comparison by importing the frozen prepared tasks,
generation checkpoints and all509 successful transport receipts from this run.
Only exact request identities are reused. The preflight-failed request had no
completion attempt and is not imported as a successful response. The inherited
509 attempts count toward the original3503 cumulative cap. No historical run
responses, paid fallback or extra keepalive completions. Preserve original seeds,
arm order, gates, max8 logical calls/20assertions and10 shared oracle programs/task.

The child copies the parent's chat transport and delegates the unchanged hybrid
and scoring code to the frozen parent. Output lives at parent/out/humaneval/
comparison_contextfit_1 to satisfy its existing sandbox output boundary. New code
has a separate freeze; imported source files and parent outputs are hash-checked
before launch and after generation. Final scoring starts only after generation
and shared oracle freeze. This is an amended continuation, not a completed run of
the original fixed-output-cap protocol. All113 remain the denominator.
