---
name: langchain-transport
description: Qwen completion now uses LangChain with runtime guards and raw usage preservation; offline verification only
metadata:
  type: project
---

2026-11-05 (Codex): user requested trying LangChain as a replacement for model.py,
at least serialization/SSE decoding. Offline probe/report at
`final/review/langchain_transport_2026-11-05.md` records feasibility and behavior
differences. User subsequently authorized replacement. Active Qwen completion now
uses LangChain/OpenAI SDK; see `final/review/langchain_adapter_2026-11-05.md`.
Endpoint/tokenizer/context/checkpoint policy retained; small decoded-chunk hook
also preserves raw provider usage and choice index zero. Transport dependencies
installed into `final/.venv`, pinned in runtime/requirements.txt. Migration was
verified offline first; historical artifacts preserved.
Verification in pipeline `final/.venv`: 258 tests pass; separate offline probe
passes 12 fixtures/12 checks. See migration report for versions and limitations.

2026-11-05 user supplied endpoint and authorized a live smoke. `/models` and
`/tokenize` passed; exactly one LangChain completion returned correct Unicode JSON,
finish=stop, complete usage footer, 42 prompt + 12 completion tokens in 2.885s.
Evidence: `final/review/langchain_live_smoke_2026-11-05.json`. No benchmark run;
endpoint passed only through process environment, not stored in repository.

**Why:** avoid claiming drop-in equivalence when stream acceptance and usage
accounting differ. **How to apply:** read the report before migrating; preserve
runtime/checkpoint policy and historical artifacts. See [[runtime-refactor]].
