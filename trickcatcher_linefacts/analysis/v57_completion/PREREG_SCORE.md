# v57 frozen-generation score registration

Date: 2026-10-24. Registered after P1 source-only inventory/budgets froze and before this scorer reads private canonical/contract outcomes.

Scope: label the existing `generation_v2` only. Generation remains immutable; no model calls, new test generation, task replacement, re-ranking or source change.

Primary unit: first six raw entries in each final response for every case/arm. A truncated/missing/malformed response produces explicit unresolved slots. The scorer normalizes positional literal arguments, executes the original PUT, evaluator-only `is_valid_test` contract and canonical reference in isolated workers, then labels `confirmed`, `input_discrepancy_wrong_expected`, `passing_test`, `false_alarm`, `invalid_input` or `unresolved`.

If a contract/reference/PUT worker times out or fails, label unresolved. Do not count this as invalid input, passing behavior or a false alarm. Typed equality follows exact Python type/value equality, with the dataset's `atol` for floats. Report all raw-slot denominators and valid/resolved conditional metrics separately.

This is retrospective evaluation of a six-case development diagnostic. It cannot establish concept efficacy, solver coverage or held-out performance.
