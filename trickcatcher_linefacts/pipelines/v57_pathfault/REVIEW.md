# Independent Codex review

2026-10-24. Reviewer: separate read-only `v57_review` agent. No benchmark outcomes, model calls or artifact edits by reviewer. Review was authorized by the repository's independent-review working rule; Codex-review exception in the Sonnet subagent policy applies.

Plan review produced six must-fixes, recorded before implementation in PREREG_V57 Amendment1: executable facets, behavioral-versus-normative status, exact AST/path replay, fail-closed support, equal evidence and complete manifest identity.

Code review requested changes and supplied authored reproductions. All were fixed before any real benchmark evaluation:

1. Local infection now preserves int/bool type changes, consistently with typed propagation.
2. Query cap and remaining deadline checked before every solver check, timeout refreshed after replay.
3. Every sequence length0..bound is enumerated; Cartesian cap remains explicitly incomplete.
4. Adapter preserves direct assertion order and excludes controlled/nested assertions and invalid wrappers; returns/rebinding cannot be ignored.
5. Writer replacements are pure allowlisted ASTs/builtins; an accumulator replacement preserves its target.
6. Absolute deadline propagates into symbolic work and concrete/base replay; symbolic sequence growth capped.
7. Replay preserves actual AugAssign operations and observes afterward. Symbolic in-place sequence mutation remains unsupported. Alias public observations are tested independently of construction.

Additional regressions cover shadowed builtins, imported-proposal priority and bidirectional multiplicity. Reviewer independently ran the final34 tests (all pass,1.35s) and cleared code blockers. Final README corrections specify all0..bound lengths, true replay alias semantics and unsupported symbolic sequence AugAssign.

Reviewer assessment: substantive engineering depth from joint path/local/output constraints replacing fixed transforms. Still bounded behavioral differential construction; semantic writer is an unexecuted import interface. Raw/concept prompts share concept descriptors, so their comparison measures obligation framing/instruction, not presence/absence of all semantic information. No effectiveness or general-Python claim.

## Ngrok/integration follow-up before live model calls

User requested ngrok execution after the CPU commit; saved endpoint returned404, user restarting notebook. Independent review covered normalized Solution-wrapper binding, known public comparator extraction, original-only feedback replay, serial hosted generation and queued v58 design.

Launch blockers fixed before any model call: bounded pre-dispatch attempt ledger (78slots/156maxchatattempts), pinned request before dispatch, atomic/no-overwrite writes with interrupted-response recovery, exact input-control witness parity, redirect refusal, sanitized HTTPException/IncompleteRead, and actual context-token preflight. Exact-class replay initially exposed Python double-underscore name mangling; instrumentation now uses a reserved single-underscore prefix and the regression passes.

Reviewer independently reproduced47tests, then reviewed/tokenization additions and independently reproduced49tests. Production interrupted-publication recovery was separately exercised without a network/model. A test-injection failure from importing the runner under a second package name was fixed to use its actual package; the interruption test now exercises the intended module. No remaining launch blocker within the documented bounded pilot/generation-only scope. Live endpoint and private-score validation remain unperformed.
