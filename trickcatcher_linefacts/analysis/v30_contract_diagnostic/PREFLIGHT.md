# Prepared paired diagnostic — 2026-10-19

User explicitly requested a run. Preparation completed without any model/HTTP/native/reference execution.

-10 frozen, previously seen pilot cases;2 contemporaneous arms;60 fixed completion slots;180 completion-attempt ceiling.
-Source packets, concepts, hypotheses, ordered witnesses and adopted traces frozen under
  `out/v30_contract_diagnostic/paired10/protocol.json` and `packets/`. No canonical/reference labels in packets.
-352/437 earlier generation hashes were checked during the preceding audit; this runner rechecks all437 pilot hashes
  and current frozen v21 source hashes, then validates prepared task hashes against old ledgers.
-Old/new CFGs compared structurally (networkx graph object identity is intentionally excluded); projection code equal.
  All original context/package sections match except disclosed contract treatment. Same stage seeds and alternating
  paired arm order are pinned.
-9/9 offline runner checks pass: stable slots/seeds, paired contexts, independent history, typed reply failures,
  unchanged resume, fatal context stop/partial snapshots, raw-response freeze before report, durable native cap,
  exact cap-error metric and CFG equivalence. Hand-authored fake responses only;0 model/native calls in those checks.
-Two independent read-only protocol/code reviews resolved slot drift, integrity stop, raw-freeze timing,
  cumulative accounting and cap-metric specificity. No remaining reviewed launch blocker once a live endpoint exists.

Current status: prepared_waiting_endpoint,0 completions. QWEN_BASE_URL absent both before and after sourcing
scripts/research_env.sh; no models/metadata/tokenizer/completion request was attempted. No substitution model or
paid API used. The asynchronous user question requests the current endpoint.

Once the endpoint is supplied, unchanged launch command (with its value held only in the environment):

```
PYTHONPATH=. <V4_PYTHON> -B -m trickcatcher_linefacts.analysis.v30_contract_diagnostic.run run
```

Run detached with a PID and pipeline log; controller locks prevent duplication, and a20-minute keepalive is built in.
No automatic benchmark promotion or larger sweep. Resume verifies the same protocol; finished raw generation is
verified before any reporting or new client construction. Never edit frozen packets/prompts after observing responses.
