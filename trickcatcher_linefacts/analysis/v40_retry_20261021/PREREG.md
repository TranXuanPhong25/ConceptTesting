# Explicit v40 retry — 2026-10-21, before new calls

User says “thuwr lai di” after the first terminal transport failure. This
authorizes one new run namespace, not resetting or overwriting the failed run.
Reuse byte-identical frozen v40 source, prepared packets, shared CPU evidence,
and prior code-audit approval. No fresh shared workers; the copied evidence is
reused historical preparation, not an independent sample. No prompt, schema,
timeout, serialization, seed, model, arm, order, cap, or decoder changes.

Root: out/pipelines/v40_concept_agent/humaneval/d1_retry_20261021.
Up to72 fresh single-attempt completion slots; original1unknown completion
remains separately consumed, so cumulative ceiling73, not72. New metadata and
tokenizer requests are recorded separately. Original inventory is verified
before and after; no original request/ledger/cache is edited or reset.

Exact qwen2.5-coder-32b-instruct/context8192, frozen tokenizer binding and180s
timeout. Stop immediately on transport/protocol failure. Stop at Codex5h
remaining<=15%; no automatic retry, reset, fallback, repair, or expansion.
No paid calls, benchmark, held-out, training, or additional canary calls.
All8episodes/3arms/72slots remain in the denominator, including not attempted.
Saved-data scoring and independent review only after terminal status. Compare
concept_adaptive/generic_adaptive/concept_committed; distinguish supplied
exposure, novel input discovery, correct/masked and ambiguous controls. No
model-authored expected-output claims. Retain actual usage plus unknowns and
CPU/tool worker provenance. Endpoint only in process environment.

The external launcher passes an explicit root to unchanged d1.run; this is run
orchestration, not a new treatment. A clean-context read-only audit precedes calls.
