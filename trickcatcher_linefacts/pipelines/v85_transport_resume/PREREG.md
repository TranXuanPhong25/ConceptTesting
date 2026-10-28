# V85 restored-endpoint continuation — 2026-10-28

User explicitly restored the endpoint and requested execution after the prior
transport stop. GET/models at15:00:55UTC confirms qwen3.5-27b-awq/context8192.
Registered before any new completion call; no target scoring has occurred.

Continue the SAME v85_contextfit method from25/113 completed pairs,113prepared
tasks and574successful responses. Preserve both rounds,10shared spec-only ref
programs/task, original seeds/order, concept binding, caps and context allocation.
The user has clarified that a cleaner replacement of fuzz-derived concepts is
desired; that change is NOT mixed into this partly generated comparison. This
run still binds retrieved cards to v11 execution facts, as previously disclosed.

Parent comparison_contextfit_1 is terminal and immutable. One request timed out
after240seconds: task78 retrieval round1, c1bcf735fd22e9e6e0571c0f98ffa6c543ed7b0a0ca31a16c527a49ebd7a0f3f.
It has unknown usage and may have been processed remotely. User's instruction to
continue authorizes one fresh attempt at this unresolved request. No automatic
transport retry, model substitution, paid fallback or extra keepalive completion.

New root: v85_retrievalhybrid/out/humaneval/comparison_contextfit_2. Import exact
successful receipts and generation checkpoints only. Preserve the failed attempt
separately in HISTORICAL_UNKNOWN.json, including its original ledger row and
response. The active ledger starts with574successful attempts, while cumulative
usage starts at575attempts. Limit the active ledger to3502, giving the same3503
cumulative cap and2928new attempts remaining. Never turn the earlier unknown
usage into zero when a later response succeeds. Report known token sums and the
unknown prior attempt separately. All113tasks remain the denominator.

Copy the parent's continuation runner; reuse its unchanged context-fit transport
and frozen generation/scoring modules. Validate original source/output hashes,
imported request identities and checkpoint hashes before launch. Freeze child
source/protocol and inherited outputs before inference. Canonical/contracts stay
grading-only after generation+oracle freeze. No method efficacy claim yet.
