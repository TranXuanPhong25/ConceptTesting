# v62 — 2026-10-25

Copied v61_pathfault_integrated as an isolated successor to fix demonstrated implementation failures. Vendor code and v61 source/results untouched.

- semantic_contract.py: exact predicate grammar/examples and integer priorities; model selects verbatim clause IDs bound to source/spec hashes; canonical admission retains semantic uncertainty.
- replay_worker.py/joint_constructor.py: no instrumentation for ordinary output probes; bounded targeted trace capture no longer raises cap errors into programs; capture loss prevents certification; unsupported construction profile explicitly recorded.
- joint_constructor.py: public-example-derived finite character categories replace universal lowercase alphabet, allowing digit-string inputs; per-argument search profiles recorded, bounds unchanged.
- literal_contract.py/pipeline.py/frozen_score.py: one type-preserving literal policy across probes/final audit/scoring, accepting native JSON nonstring expected values. External scorer fork records its literal parser hash.
- pipeline.py: six shared writer slots and public construction checkpointed before arm generation; gate requires admission in3cases, native realization in2, output sensitivity in1. Completed writer calls reused exactly.
- ngrok_run.py:64kcharacter safety ceiling; exact server tokenizer/context budget still controls dispatch. All generation arms receive the same concise-output instruction.
- analysis/v62_completion/: isolated scorer/lifecycle scripts,15min observer with terminal callback.
- test_contractfix.py: regressions for observed admission, trace overflow, JSON type handling, gate and cache reuse failures. Existing lifecycle/compositional/evaluator regressions retained.

No effectiveness result is implied by engineering tests. Earlier CHANGELOG.md entries are inherited history.
