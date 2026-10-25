# Pre-dispatch review — 2026-10-25

Scope: six-case public-only prepare diagnostic explicitly requested by user.
Review method: owner source/protocol audit and CPU regressions; no independent
subagent review. Current orchestration instructions prohibit spawning agents
without an explicit user/AGENTS.md delegation request. This deviation from the
stored independent-review preference is disclosed; no independent PASS claimed.

Reviewed v65/v67 admission, predicate, native replay, construction budget,
selection/context parity, per-case/cohort gate, dispatch/cache/attempt accounting,
readiness/locking and standalone diagnostic harness. Public checks never load
private labels. v67 differs in writer JSON whitespace only; parsed packets for
ALL six cases match v65 exactly. Source/spec/site/grammar content is preserved.

Preflight v65 blocked case66 at8291total tokens, zero completions. v67 exact
server tokenizer now fits all six with1536output: prompt counts5273,6218,4440,
5497,5699,4076 in frozen cohort order61,66,124,58,131,85. Model32B/context8192.
89 authored offline regressions passed in16.39s, including real prepare_case
request capture showing compact encoding preserves the entire decoded packet.
No model completion or real-case construction outcomes were inspected.

Run constraints: six logical writers, at most12transport dispatches; no rewrite
of invalid responses, retry controller, provider fallback, arm calls or private
scoring. Child process is detached; parent waits for terminal state without a
poll loop. Diagnostic freezes all terminal JSON and records source/request
identities and actual attempt receipts. Prepared contexts are not dispatched
prompts. Unknown execution/public output cannot count as evidence. Every case
must have a selected non-public sensitive witness for the gate to pass; this
still does not prove full spec/input correctness.

Owner review outcome: ready for the bounded diagnostic under the disclosed
review limitation; efficacy, independent audit and general semantic truth are
not established by this readiness.
