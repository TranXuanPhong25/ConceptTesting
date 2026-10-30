# Addendum: RESULTS reproduces exactly in the pinned runtime

2026-10-30 08:10 Vietnam, after the user's request to continue. This supersedes
the unresolved FA/abstention discrepancy in AUDIT_RESULT.md; original reports
and all frozen experiment files remain unchanged.

The experiment ran Python3.11.14, Unicode14.0.0. The audit reconstructs call keys
using `ast.unparse`, which can format string constants differently across Python
Unicode databases. Both shell Python3.12.2/Unicode15 and system
Python3.14.7/Unicode16 reproduce the prior discrepancy; the pinned Python3.11.14
reproduces **every arm/oracle field of the original RESULTS exactly**.
The original scheduled audit did not record its interpreter, so this does not
establish which of the two unpinned interpreters that audit actually used.

Only task27 retain/applicable is affected. Its call contains U+32093: represented
as an escape under the pinned Unicode14 database, but a literal character under
the newer databases. All four missing-key occurrences (two modes × ref/o0)
have exactly one saved key with an identical parsed AST. Newer-runtime string
serialization therefore misses an existing execution record; this is not a
different input or an additional PUT/reference execution failure.

| Field, retain/applicable | Unpinned audit | Pinned recomputation / RESULTS |
| --- | ---: | ---: |
| Ref abstained calls | 11 | 10 |
| o0 false-alarm tasks | 10 | 9 |
| Missing serialized call-key occurrences across both oracles | 4 total | 0 |

Confirmed-task sets do not change. The earlier discrepancy is an audit runtime
artifact, not evidence that frozen RESULTS was inconsistent with pinned scoring.
It does expose a general tooling constraint: serialized Python expressions are
not cross-runtime-stable identities. Future audits must use the pinned runtime;
a future identity-schema change would need its own version, not an edit here.

Verification also confirms79source/input+64parent hashes/review approval,
1,542generation hashes,39uniqueattempts/39receivedresponses, COMPLETE and a free
run lock; no active controller. No generation, target/reference execution,
endpoint probe, model call, reset or new timer was performed during this check.

See RUNTIME_AUDIT.json and verify_runtime_audit.py. The supplementary shell-runtime
probe used the same worker and compared parsed ASTs only; it did not eval source.
Historical AUDIT_CHECKS.json/AUDIT_RESULT.md retain their pre-correction bytes.
