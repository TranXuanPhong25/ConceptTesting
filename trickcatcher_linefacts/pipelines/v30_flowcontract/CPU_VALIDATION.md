# CPU validation — 2026-10-19

**54/54 checks pass** with the dedicated V4 interpreter: existing27 flow regressions and27 contract/transport/feedback checks.
Command in README.md. Last run:54 passed in5.87s. No model/GPU request or new benchmark generation.

Evidence covered:

-4 IDs accepted/5 rejected for inspect_flow, inspect_data and replay_input; path sequence64/65,4 names and64-char names.
-Mixed valid/invalid sibling actions survive outer reply validation; each action charged, invalid action returns field/limit,
  next-round4-ID correction works. Exact int versus float/bool distinguished.
-Recognizable invalid replay reserves exactly1 logical execution slot; generic invalid tool/field/hypothesis reserves0.
  No physical execution on validation failure; native execution budgets and round caps unchanged.
-Identical JSON actions reproduce immutable logs/charges on resume; changed requests reject drift. Unrepresentable
  non-JSON host inputs get static rejection markers rather than raw repr; different rejected host objects may share a marker.
-Deep/nested/oversize/non-JSON action inputs produce bounded logged errors. Unicode input under character cap but over
  UTF8-byte cap reports the correct bound. Missing/unknown fields and unsupported trace/source IDs get safe metadata.
-Omitted error after slot3 remains in compact corrective digest. Prompt schemas/whitelist/dispatcher derive from the same
  contract. Default radius does not modify logged requests.
-execution_cache_drift propagates as integrity failure, never normalized into action_serialization. No error result replaces
  a fatal cache drift. Ordinary/traced execution semantics retain existing flow tests.
-Both online transports and all inherited generation CLIs reject before model transport construction. Explicit authored
  fixture client can exercise the pipeline locally; those canned responses are not Qwen/model evidence.

Review: flow_plan_audit and flow_trial_audit performed independent read-only design/code reviews. Must-fix items resolved:
per-action rather than whole-reply rejection; reservation precedence; exact integer types; safe generic error bounds;
literal-limit disclosure; malformed JSON robustness; error digest; narrow integrity-preserving catches. Final reviewers
report no remaining must-fix within this CPU scope.

Limitations: no new model diagnostic/benchmark result; no repaired semantic extraction, formal trigger solving or explicit
hypothesis revision. The legacy feedback projector still caps detailed results, while errors are retained. Action schema
disclosure cannot establish that the model will choose replay/check_path or learn from feedback. No semantic gate passed,
no pipeline promotion. Any next model experiment needs a separately frozen protocol.
